"""Tests for IBKRFlexClient error handling."""

from unittest.mock import MagicMock, patch

from app.services.brokers.ibkr.flex_client import IBKRFlexClient

FAKE_TOKEN = "test-token"
FAKE_REF = "ref123"
PATCH_PREFIX = "app.services.brokers.ibkr.flex_client"

# -- XML fixtures ----------------------------------------------------------

RATE_LIMIT_XML = (
    "<FlexStatementResponse timestamp='09 February, 2026 05:03 PM EST'>"
    "<Status>Warn</Status>"
    "<ErrorCode>1018</ErrorCode>"
    "<ErrorMessage>Too many requests have been made from this token.</ErrorMessage>"
    "</FlexStatementResponse>"
)

PENDING_1019_FLEX_STMT_XML = (
    "<FlexStatementResponse>"
    "<Status>Warn</Status>"
    "<ErrorCode>1019</ErrorCode>"
    "<ErrorMessage>Statement generation in progress.</ErrorMessage>"
    "</FlexStatementResponse>"
)

PENDING_1019_STATUS_XML = (
    "<Status>"
    "<ErrorCode>1019</ErrorCode>"
    "<ErrorMessage>Statement generation in progress.</ErrorMessage>"
    "</Status>"
)

FATAL_ERROR_XML = (
    "<FlexStatementResponse>"
    "<Status>Fail</Status>"
    "<ErrorCode>1020</ErrorCode>"
    "<ErrorMessage>Invalid token.</ErrorMessage>"
    "</FlexStatementResponse>"
)

STATUS_ERROR_XML = (
    "<Status><ErrorCode>1009</ErrorCode><ErrorMessage>Overloaded</ErrorMessage></Status>"
)

FLEX_QUERY_RESPONSE_XML = (
    "<FlexQueryResponse queryName='Test' type='AF'>"
    "<FlexStatements count='1'>"
    "<FlexStatement accountId='U12345'>"
    "<OpenPositions>"
    '<OpenPosition symbol="AAPL" position="100" costBasisMoney="15000" '
    'currency="USD" assetCategory="STK" listingExchange="NASDAQ" />'
    "</OpenPositions>"
    "</FlexStatement>"
    "</FlexStatements>"
    "</FlexQueryResponse>"
)


def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response with the given XML content."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content.encode("utf-8")
    resp.text = content
    resp.raise_for_status = MagicMock()
    return resp


def _get_status(xml: str) -> str | None:
    """Call get_flex_query_status with fake credentials and the given XML."""
    with patch(f"{PATCH_PREFIX}.requests.get") as mock_get:
        mock_get.return_value = _mock_response(xml)
        return IBKRFlexClient.get_flex_query_status(FAKE_TOKEN, FAKE_REF)


def _download(xml: str) -> bytes | None:
    """Call download_flex_query with fake credentials and the given XML."""
    with patch(f"{PATCH_PREFIX}.requests.get") as mock_get:
        mock_get.return_value = _mock_response(xml)
        return IBKRFlexClient.download_flex_query(FAKE_TOKEN, FAKE_REF)


class TestGetFlexQueryStatus:
    def test_rate_limit_returns_rate_limited(self):
        assert _get_status(RATE_LIMIT_XML) == "rate_limited"

    def test_1019_in_flex_statement_response_returns_pending(self):
        assert _get_status(PENDING_1019_FLEX_STMT_XML) == "pending"

    def test_1019_in_status_tag_returns_pending(self):
        assert _get_status(PENDING_1019_STATUS_XML) == "pending"

    def test_fatal_error_returns_none(self):
        assert _get_status(FATAL_ERROR_XML) is None

    def test_flex_query_response_returns_success(self):
        assert _get_status(FLEX_QUERY_RESPONSE_XML) == "success"


class TestDownloadFlexQuery:
    def test_returns_data_for_flex_query_response(self):
        result = _download(FLEX_QUERY_RESPONSE_XML)
        assert result is not None
        assert b"FlexQueryResponse" in result

    def test_rejects_rate_limit_error(self):
        assert _download(RATE_LIMIT_XML) is None

    def test_rejects_status_error(self):
        assert _download(STATUS_ERROR_XML) is None


class TestFetchFlexReportRateLimit:
    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.download_flex_query")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.get_flex_query_status")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_retries_on_rate_limit_then_succeeds(
        self, mock_request, mock_status, mock_download, mock_sleep
    ):
        mock_request.return_value = "ref123"
        mock_status.side_effect = ["rate_limited", "success"]
        mock_download.return_value = FLEX_QUERY_RESPONSE_XML.encode()

        result = IBKRFlexClient.fetch_flex_report("token", "query1")

        assert result is not None
        # Rate-limit backoff should be 10 seconds
        mock_sleep.assert_called_with(10)
        assert mock_status.call_count == 2

    @patch(f"{PATCH_PREFIX}.time.time")
    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.get_flex_query_status")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_times_out_after_sustained_rate_limiting(
        self, mock_request, mock_status, mock_sleep, mock_time
    ):
        mock_request.return_value = "ref123"
        mock_status.return_value = "rate_limited"
        # Simulate time progressing past the 60s timeout
        mock_time.side_effect = [0, 0, 11, 22, 33, 44, 55, 66]

        result = IBKRFlexClient.fetch_flex_report("token", "query1", timeout=60)

        assert result is None

    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.download_flex_query")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.get_flex_query_status")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_rate_limit_backoff_independent_of_pending_backoff(
        self, mock_request, mock_status, mock_download, mock_sleep
    ):
        mock_request.return_value = "ref123"
        # pending (2s) -> rate_limited (10s) -> pending (3s) -> success
        mock_status.side_effect = ["pending", "rate_limited", "pending", "success"]
        mock_download.return_value = FLEX_QUERY_RESPONSE_XML.encode()

        result = IBKRFlexClient.fetch_flex_report("token", "query1")

        assert result is not None
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 2  # pending: initial interval
        assert sleep_calls[1] == 10  # rate_limited: flat 10s
        assert sleep_calls[2] == 3.0  # pending: backoff continued (2 * 1.5)
