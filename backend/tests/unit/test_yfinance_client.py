"""Tests for YFinanceClient rate limiting, batch resolution, and TickerInfo."""

from datetime import datetime
from decimal import Decimal

from app.services.market_data.yfinance_client import (
    QUOTE_TYPE_MAP,
    TickerInfo,
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
