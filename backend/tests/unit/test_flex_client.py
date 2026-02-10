"""Tests for IBKRFlexClient error handling."""

from unittest.mock import MagicMock, patch

from app.services.brokers.ibkr.flex_client import (
    RATE_LIMIT_SLEEP_SECONDS,
    IBKRFlexClient,
)

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


def _poll_once(xml: str) -> tuple[str, bytes | None]:
    """Call _poll_once with fake credentials and the given XML."""
    with patch(f"{PATCH_PREFIX}.requests.get") as mock_get:
        mock_get.return_value = _mock_response(xml)
        return IBKRFlexClient._poll_once(FAKE_TOKEN, FAKE_REF)


class TestPollOnce:
    def test_rate_limit_returns_rate_limited(self):
        status, data = _poll_once(RATE_LIMIT_XML)
        assert status == "rate_limited"
        assert data is None

    def test_1019_in_flex_statement_response_returns_pending(self):
        status, data = _poll_once(PENDING_1019_FLEX_STMT_XML)
        assert status == "pending"
        assert data is None

    def test_1019_in_status_tag_returns_pending(self):
        status, data = _poll_once(PENDING_1019_STATUS_XML)
        assert status == "pending"
        assert data is None

    def test_fatal_error_returns_error(self):
        status, data = _poll_once(FATAL_ERROR_XML)
        assert status == "error"
        assert data is None

    def test_status_error_returns_error(self):
        status, data = _poll_once(STATUS_ERROR_XML)
        assert status == "error"
        assert data is None

    def test_flex_query_response_returns_success_with_data(self):
        status, data = _poll_once(FLEX_QUERY_RESPONSE_XML)
        assert status == "success"
        assert data is not None
        assert b"FlexQueryResponse" in data

    def test_makes_single_http_request(self):
        with patch(f"{PATCH_PREFIX}.requests.get") as mock_get:
            mock_get.return_value = _mock_response(FLEX_QUERY_RESPONSE_XML)
            IBKRFlexClient._poll_once(FAKE_TOKEN, FAKE_REF)
            assert mock_get.call_count == 1


class TestFetchFlexReportRateLimit:
    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient._poll_once")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_retries_on_rate_limit_then_succeeds(
        self, mock_request, mock_poll, mock_sleep
    ):
        mock_request.return_value = "ref123"
        mock_poll.side_effect = [
            ("rate_limited", None),
            ("success", FLEX_QUERY_RESPONSE_XML.encode()),
        ]

        result = IBKRFlexClient.fetch_flex_report("token", "query1")

        assert result is not None
        mock_sleep.assert_called_with(RATE_LIMIT_SLEEP_SECONDS)
        assert mock_poll.call_count == 2

    @patch(f"{PATCH_PREFIX}.time.time")
    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient._poll_once")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_times_out_after_sustained_rate_limiting(
        self, mock_request, mock_poll, mock_sleep, mock_time
    ):
        mock_request.return_value = "ref123"
        mock_poll.return_value = ("rate_limited", None)
        # Simulate time progressing past the 60s timeout
        mock_time.side_effect = [0, 0, 11, 22, 33, 44, 55, 66]

        result = IBKRFlexClient.fetch_flex_report("token", "query1", timeout=60)

        assert result is None

    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient._poll_once")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_rate_limit_backoff_independent_of_pending_backoff(
        self, mock_request, mock_poll, mock_sleep
    ):
        mock_request.return_value = "ref123"
        # pending (2s) -> rate_limited (10s) -> pending (3s) -> success
        mock_poll.side_effect = [
            ("pending", None),
            ("rate_limited", None),
            ("pending", None),
            ("success", FLEX_QUERY_RESPONSE_XML.encode()),
        ]

        result = IBKRFlexClient.fetch_flex_report("token", "query1")

        assert result is not None
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 2  # pending: initial interval
        assert sleep_calls[1] == RATE_LIMIT_SLEEP_SECONDS  # rate_limited: flat backoff
        assert sleep_calls[2] == 3.0  # pending: backoff continued (2 * 1.5)

    @patch(f"{PATCH_PREFIX}.time.sleep")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient._poll_once")
    @patch(f"{PATCH_PREFIX}.IBKRFlexClient.request_flex_query")
    def test_no_separate_download_after_success(
        self, mock_request, mock_poll, mock_sleep
    ):
        """Verify success returns data directly from poll without extra HTTP call."""
        mock_request.return_value = "ref123"
        expected_data = FLEX_QUERY_RESPONSE_XML.encode()
        mock_poll.return_value = ("success", expected_data)

        result = IBKRFlexClient.fetch_flex_report("token", "query1")

        assert result is expected_data
        assert mock_poll.call_count == 1
