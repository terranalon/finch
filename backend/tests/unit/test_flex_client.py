"""Tests for IBKRFlexClient error handling."""

from unittest.mock import MagicMock, patch

from app.services.brokers.ibkr.flex_client import IBKRFlexClient

FAKE_TOKEN = "test-token"
FAKE_REF = "ref123"

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
    "<Status>"
    "<ErrorCode>1009</ErrorCode>"
    "<ErrorMessage>Overloaded</ErrorMessage>"
    "</Status>"
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
    with patch("app.services.brokers.ibkr.flex_client.requests.get") as mock_get:
        mock_get.return_value = _mock_response(xml)
        return IBKRFlexClient.get_flex_query_status(FAKE_TOKEN, FAKE_REF)


def _download(xml: str) -> bytes | None:
    """Call download_flex_query with fake credentials and the given XML."""
    with patch("app.services.brokers.ibkr.flex_client.requests.get") as mock_get:
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
