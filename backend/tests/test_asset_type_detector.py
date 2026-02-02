"""Tests for AssetTypeDetector service."""

from unittest.mock import patch

from app.services.shared.asset_type_detector import AssetTypeDetector, AssetTypeResult


class TestAssetTypeDetector:
    """Tests for asset type detection using Yahoo Finance."""

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_detect_etf(self, mock_ticker):
        """Test detection of ETF."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 450.0,
            "quoteType": "ETF",
        }

        result = AssetTypeDetector.detect_asset_type("SPY")

        assert result.detected_type == "ETF"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_detect_mutual_fund(self, mock_ticker):
        """Test detection of Mutual Fund."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 300.0,
            "quoteType": "MUTUALFUND",
        }

        result = AssetTypeDetector.detect_asset_type("VFIAX")

        assert result.detected_type == "MutualFund"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_detect_stock(self, mock_ticker):
        """Test detection of Stock (EQUITY)."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 180.0,
            "quoteType": "EQUITY",
        }

        result = AssetTypeDetector.detect_asset_type("AAPL")

        assert result.detected_type == "Stock"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_detect_money_market(self, mock_ticker):
        """Test detection of Money Market fund."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 1.0,
            "quoteType": "MONEYMARKET",
        }

        result = AssetTypeDetector.detect_asset_type("SPAXX")

        assert result.detected_type == "MoneyMarket"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_symbol_not_found(self, mock_ticker):
        """Test handling of symbol not found in Yahoo Finance."""
        mock_ticker.return_value.info = {}

        result = AssetTypeDetector.detect_asset_type("INVALID")

        assert result.detected_type is None
        assert result.source == "not_found"
        assert result.error is not None
        assert "not found" in result.error.lower()

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_symbol_not_found_none_price(self, mock_ticker):
        """Test handling when regularMarketPrice is None."""
        mock_ticker.return_value.info = {"quoteType": "ETF", "regularMarketPrice": None}

        result = AssetTypeDetector.detect_asset_type("DELISTED")

        assert result.detected_type is None
        assert result.source == "not_found"

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_unknown_quote_type(self, mock_ticker):
        """Test handling of unknown quoteType."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "CRYPTOCURRENCY",  # Not in our mapping
        }

        result = AssetTypeDetector.detect_asset_type("BTC-USD")

        assert result.detected_type is None
        assert result.source == "yfinance"
        assert result.error is not None
        assert "Unknown quoteType" in result.error

    @patch("app.services.shared.asset_type_detector.yf.Ticker")
    def test_api_error(self, mock_ticker):
        """Test handling of API errors."""
        mock_ticker.side_effect = Exception("Network error")

        result = AssetTypeDetector.detect_asset_type("TEST")

        assert result.detected_type is None
        assert result.source == "error"
        assert result.error is not None

    def test_quote_type_map_values(self):
        """Test that QUOTE_TYPE_MAP contains expected mappings."""
        assert AssetTypeDetector.QUOTE_TYPE_MAP["ETF"] == "ETF"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["MUTUALFUND"] == "MutualFund"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["MONEYMARKET"] == "MoneyMarket"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["EQUITY"] == "Stock"


class TestAssetTypeResult:
    """Tests for AssetTypeResult dataclass."""

    def test_result_with_detected_type(self):
        """Test creating result with detected type."""
        result = AssetTypeResult(
            symbol="SPY",
            detected_type="ETF",
            source="yfinance",
        )

        assert result.symbol == "SPY"
        assert result.detected_type == "ETF"
        assert result.source == "yfinance"
        assert result.error is None

    def test_result_with_error(self):
        """Test creating result with error."""
        result = AssetTypeResult(
            symbol="INVALID",
            detected_type=None,
            source="error",
            error="Symbol not found",
        )

        assert result.symbol == "INVALID"
        assert result.detected_type is None
        assert result.source == "error"
        assert result.error == "Symbol not found"
