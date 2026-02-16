"""Tests for AssetTypeDetector service."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app.services.market_data.yfinance_client import TickerInfo
from app.services.shared.asset_type_detector import AssetTypeDetector, AssetTypeResult


def _make_ticker_info(**overrides) -> TickerInfo:
    defaults = dict(
        symbol="TEST",
        name="Test Corp",
        quote_type="EQUITY",
        sector="Technology",
        category=None,
        industry="Consumer Electronics",
        currency="USD",
        exchange="NMS",
        price=Decimal("100.0"),
        price_timestamp=datetime(2026, 1, 15),
    )
    defaults.update(overrides)
    return TickerInfo(**defaults)  # ty: ignore[invalid-argument-type] — dict values are mixed types


class TestAssetTypeDetector:
    """Tests for asset type detection using Yahoo Finance."""

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_detect_etf(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = _make_ticker_info(
            symbol="SPY", quote_type="ETF"
        )
        result = AssetTypeDetector.detect_asset_type("SPY")
        assert result.detected_type == "ETF"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_detect_mutual_fund(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = _make_ticker_info(
            symbol="VFIAX", quote_type="MUTUALFUND"
        )
        result = AssetTypeDetector.detect_asset_type("VFIAX")
        assert result.detected_type == "MutualFund"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_detect_stock(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = _make_ticker_info(
            symbol="AAPL", quote_type="EQUITY"
        )
        result = AssetTypeDetector.detect_asset_type("AAPL")
        assert result.detected_type == "Stock"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_detect_money_market(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = _make_ticker_info(
            symbol="SPAXX", quote_type="MONEYMARKET"
        )
        result = AssetTypeDetector.detect_asset_type("SPAXX")
        assert result.detected_type == "MoneyMarket"
        assert result.source == "yfinance"
        assert result.error is None

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_symbol_not_found(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = None
        result = AssetTypeDetector.detect_asset_type("INVALID")
        assert result.detected_type is None
        assert result.source == "not_found"
        assert result.error is not None
        assert "not found" in result.error.lower()

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_symbol_not_found_none_price(self, mock_client_cls):
        # YFinanceClient returns None when regularMarketPrice is None
        mock_client_cls.return_value.get_ticker_info.return_value = None
        result = AssetTypeDetector.detect_asset_type("DELISTED")
        assert result.detected_type is None
        assert result.source == "not_found"

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_unknown_quote_type(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.return_value = _make_ticker_info(
            symbol="BTC-USD", quote_type="CRYPTOCURRENCY"
        )
        result = AssetTypeDetector.detect_asset_type("BTC-USD")
        assert result.detected_type is None
        assert result.source == "yfinance"
        assert result.error is not None
        assert "Unknown quoteType" in result.error

    @patch("app.services.shared.asset_type_detector.YFinanceClient")
    def test_api_error(self, mock_client_cls):
        mock_client_cls.return_value.get_ticker_info.side_effect = Exception("Network error")
        result = AssetTypeDetector.detect_asset_type("TEST")
        assert result.detected_type is None
        assert result.source == "error"
        assert result.error is not None

    def test_quote_type_map_values(self):
        assert AssetTypeDetector.QUOTE_TYPE_MAP["ETF"] == "ETF"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["MUTUALFUND"] == "MutualFund"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["MONEYMARKET"] == "MoneyMarket"
        assert AssetTypeDetector.QUOTE_TYPE_MAP["EQUITY"] == "Stock"


class TestDetectFromTickerInfo:
    """Tests for detect_from_ticker_info (pre-fetched TickerInfo path)."""

    def test_etf_from_ticker_info(self):
        info = _make_ticker_info(symbol="SPY", quote_type="ETF")
        result = AssetTypeDetector.detect_from_ticker_info("SPY", info)
        assert result.detected_type == "ETF"

    def test_none_ticker_info(self):
        result = AssetTypeDetector.detect_from_ticker_info("BAD", None)
        assert result.detected_type is None
        assert result.source == "not_found"


class TestAssetTypeResult:
    """Tests for AssetTypeResult dataclass."""

    def test_result_with_detected_type(self):
        result = AssetTypeResult(symbol="SPY", detected_type="ETF", source="yfinance")
        assert result.symbol == "SPY"
        assert result.detected_type == "ETF"
        assert result.source == "yfinance"
        assert result.error is None

    def test_result_with_error(self):
        result = AssetTypeResult(
            symbol="INVALID", detected_type=None, source="error", error="Symbol not found"
        )
        assert result.symbol == "INVALID"
        assert result.detected_type is None
        assert result.source == "error"
        assert result.error == "Symbol not found"
