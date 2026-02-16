"""Tests for YFinanceClient rate limiting, batch resolution, and TickerInfo."""

import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app.services.market_data.yfinance_client import (
    QUOTE_TYPE_MAP,
    TickerInfo,
    YFinanceClient,
)


def _make_ticker_info(**overrides) -> TickerInfo:
    defaults = dict(
        symbol="AAPL",
        name="Apple Inc.",
        quote_type="EQUITY",
        sector="Technology",
        category=None,
        industry="Consumer Electronics",
        currency="USD",
        exchange="NMS",
        price=Decimal("175.50"),
        price_timestamp=datetime(2026, 1, 15),
    )
    defaults.update(overrides)
    return TickerInfo(**defaults)


class TestQuoteTypeMap:
    def test_contains_all_expected_mappings(self):
        assert QUOTE_TYPE_MAP == {
            "ETF": "ETF",
            "MUTUALFUND": "MutualFund",
            "MONEYMARKET": "MoneyMarket",
            "EQUITY": "Stock",
        }


class TestTickerInfoAssetClass:
    def test_equity_maps_to_stock(self):
        info = _make_ticker_info(quote_type="EQUITY")
        assert info.asset_class == "Stock"

    def test_etf_maps_to_etf(self):
        info = _make_ticker_info(quote_type="ETF")
        assert info.asset_class == "ETF"

    def test_mutual_fund(self):
        info = _make_ticker_info(quote_type="MUTUALFUND")
        assert info.asset_class == "MutualFund"

    def test_money_market(self):
        info = _make_ticker_info(quote_type="MONEYMARKET")
        assert info.asset_class == "MoneyMarket"

    def test_unknown_quote_type_returns_none(self):
        info = _make_ticker_info(quote_type="CRYPTOCURRENCY")
        assert info.asset_class is None

    def test_none_quote_type_returns_none(self):
        info = _make_ticker_info(quote_type=None)
        assert info.asset_class is None


class TestRateLimiting:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_consecutive_calls_are_throttled(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        client = YFinanceClient()
        # Override interval for fast testing
        YFinanceClient._min_request_interval = 0.1

        start = time.time()
        client.get_ticker_info("AAPL")
        client.get_ticker_info("MSFT")
        elapsed = time.time() - start

        assert elapsed >= 0.1, f"Expected >= 0.1s, got {elapsed:.3f}s"
        # Restore default
        YFinanceClient._min_request_interval = 0.5

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_first_call_not_delayed(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        # Reset class-level state
        YFinanceClient._last_request_time = 0.0
        client = YFinanceClient()

        start = time.time()
        client.get_ticker_info("AAPL")
        elapsed = time.time() - start

        # First call should not be delayed (< 0.1s unless yf is slow)
        assert elapsed < 0.5


class TestResolveSymbols:
    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_deduplicates_symbols(self, mock_ticker):
        mock_ticker.return_value.info = {
            "regularMarketPrice": 100.0,
            "quoteType": "EQUITY",
            "longName": "Test Corp",
        }
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0  # skip delay in tests

        results = client.resolve_symbols(["AAPL", "MSFT", "AAPL"])

        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results
        # yf.Ticker called only twice (AAPL deduped)
        assert mock_ticker.call_count == 2

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_returns_none_for_failed_lookups(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

        results = client.resolve_symbols(["BAD"])

        assert results["BAD"] is None

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_empty_list_returns_empty_dict(self, mock_ticker):
        client = YFinanceClient()
        results = client.resolve_symbols([])
        assert results == {}
        mock_ticker.assert_not_called()

    @patch("app.services.market_data.yfinance_client.yf.Ticker")
    def test_preserves_order(self, mock_ticker):
        call_order = []

        def side_effect(symbol):
            call_order.append(symbol)
            mock = type(mock_ticker.return_value)()
            mock.info = {
                "regularMarketPrice": 100.0,
                "quoteType": "EQUITY",
                "longName": f"{symbol} Corp",
            }
            return mock

        mock_ticker.side_effect = side_effect
        client = YFinanceClient()
        YFinanceClient._min_request_interval = 0.0

        results = client.resolve_symbols(["MSFT", "AAPL", "GOOG"])

        assert call_order == ["MSFT", "AAPL", "GOOG"]
        assert list(results.keys()) == ["MSFT", "AAPL", "GOOG"]
