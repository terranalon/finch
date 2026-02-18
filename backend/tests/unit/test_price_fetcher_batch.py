"""Tests for PriceFetcher batch pricing integration."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models import Asset
from app.services.market_data.coingecko_client import CryptoMarketData
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.market_data.yfinance_client import OHLCVRow, TickerMarketData


def _make_ohlcv(close: float, row_date: date = date(2024, 1, 15)) -> OHLCVRow:
    d = Decimal(str(close))
    return OHLCVRow(date=row_date, open=d, high=d, low=d, close=d, volume=Decimal("1000000"))


def _make_asset(symbol: str | None, asset_class: str = "Stock", currency: str = "USD") -> Asset:
    asset = MagicMock(spec=Asset)
    asset.symbol = symbol
    asset.asset_class = asset_class
    asset.currency = currency
    asset.last_fetched_price = None
    asset.last_fetched_at = None
    return asset


def _make_ticker_market_data(symbol: str, price: float) -> TickerMarketData:
    d = Decimal(str(price))
    return TickerMarketData(
        symbol=symbol,
        price=d,
        open=d,
        high=d,
        low=d,
        close=d,
        volume=1000000,
        market_cap=Decimal("1000000000"),
        pe_ratio=Decimal("25"),
        forward_pe=Decimal("22"),
        eps=Decimal("6"),
        dividend_rate=Decimal("1"),
        dividend_yield=Decimal("0.005"),
        payout_ratio=Decimal("0.15"),
        description="Test",
        exchange="NMS",
        website="https://test.com",
        ceo="Test CEO",
        employees=10000,
        beta=Decimal("1.2"),
        avg_volume=5000000,
        earnings_date=None,
        ex_dividend_date=None,
        target_est=Decimal("200"),
        week_52_high=Decimal("190"),
        week_52_low=Decimal("140"),
        peg_ratio=Decimal("1.5"),
        expense_ratio=None,
        fund_family=None,
        nav=None,
    )


def _make_crypto_market_data(symbol: str, price: float) -> CryptoMarketData:
    d = Decimal(str(price))
    return CryptoMarketData(
        symbol=symbol,
        price=d,
        high_24h=d,
        low_24h=d,
        volume=Decimal("1000000000"),
        market_cap=Decimal("500000000000"),
        market_cap_rank=1,
        circulating_supply=Decimal("19000000"),
        max_supply=Decimal("21000000"),
        ath=d,
        ath_date=None,
        atl=Decimal("1"),
        atl_date=None,
    )


class TestUpdateAllAssetPricesBatch:
    """Tests for batch pricing in update_all_asset_prices."""

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_uses_batch_for_non_crypto(self, mock_cg, mock_yf_cls, mock_metrics):
        """Should call get_batch_ticker_info once with all non-crypto symbols."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        msft = _make_asset("MSFT")
        db.execute.return_value.scalars.return_value.all.return_value = [aapl, msft]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_ticker_info.return_value = {
            "AAPL": _make_ticker_market_data("AAPL", 175.50),
            "MSFT": _make_ticker_market_data("MSFT", 380.00),
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        mock_client.get_batch_ticker_info.assert_called_once()
        call_symbols = mock_client.get_batch_ticker_info.call_args[0][0]
        assert set(call_symbols) == {"AAPL", "MSFT"}
        assert stats["updated"] == 2
        assert aapl.last_fetched_price == Decimal("175.5")
        assert msft.last_fetched_price == Decimal("380.0")

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_agorot_conversion_in_batch(self, mock_cg, mock_yf_cls, mock_metrics):
        """Should divide .TA symbol prices by 100 (Agorot to ILS) for all OHLC fields."""
        db = MagicMock()
        teva = _make_asset("TEVA.TA", currency="ILS")
        db.execute.return_value.scalars.return_value.all.return_value = [teva]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_ticker_info.return_value = {
            "TEVA.TA": _make_ticker_market_data("TEVA.TA", 5678.0),
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["updated"] == 1
        assert teva.last_fetched_price == Decimal("56.78")
        # All OHLC fields must be converted from Agorot to ILS (divided by 100)
        call_kwargs = mock_metrics.upsert_daily_metrics.call_args.kwargs
        assert call_kwargs["close"] == Decimal("56.78")
        assert call_kwargs["open"] == Decimal("56.78")
        assert call_kwargs["high"] == Decimal("56.78")
        assert call_kwargs["low"] == Decimal("56.78")

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_partial_batch_failure(self, mock_cg, mock_yf_cls, mock_metrics):
        """Some symbols returning None should count as failed, others succeed."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        bad = _make_asset("BADSTOCK")
        db.execute.return_value.scalars.return_value.all.return_value = [aapl, bad]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_ticker_info.return_value = {
            "AAPL": _make_ticker_market_data("AAPL", 175.50),
            "BADSTOCK": None,
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["updated"] == 1
        assert stats["failed"] == 1

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_crypto_still_uses_coingecko(self, mock_cg_fn, mock_yf_cls, mock_metrics):
        """Crypto assets should still use CoinGecko batch, not YFinance."""
        db = MagicMock()
        btc = _make_asset("BTC", asset_class="Crypto")
        db.execute.return_value.scalars.return_value.all.return_value = [btc]

        mock_cg = MagicMock()
        mock_cg.get_market_data.return_value = {
            "BTC": _make_crypto_market_data("BTC", 50000),
        }
        mock_cg_fn.return_value = mock_cg

        PriceFetcher.update_all_asset_prices(db)

        mock_cg.get_market_data.assert_called_once()
        mock_yf_cls.return_value.get_batch_ticker_info.assert_not_called()

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_exception_does_not_double_count_failed(self, mock_cg, mock_yf_cls, mock_metrics):
        """Exception after partial loop should not double-count already-tallied assets."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        bad = _make_asset("BADSTOCK")
        msft = _make_asset("MSFT")
        db.execute.return_value.scalars.return_value.all.return_value = [aapl, bad, msft]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_ticker_info.return_value = {
            "AAPL": _make_ticker_market_data("AAPL", 175.50),
            "BADSTOCK": None,
            "MSFT": _make_ticker_market_data("MSFT", 380.00),
        }
        # commit() raises after the loop finishes (metrics calls are patched so no inner commits)
        db.commit.side_effect = Exception("DB error")

        stats = PriceFetcher.update_all_asset_prices(db)

        # 2 updated + 1 failed (None) in the loop, then exception adds 0 more
        assert stats["updated"] + stats["failed"] == 3

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_skips_cash_and_empty_symbols(self, mock_cg, mock_yf_cls, mock_metrics):
        """Cash assets and assets without symbols should be skipped."""
        db = MagicMock()
        cash = _make_asset("USD", asset_class="Cash")
        empty = _make_asset(None, asset_class="Stock")
        db.execute.return_value.scalars.return_value.all.return_value = [cash, empty]

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["skipped"] == 2
        mock_yf_cls.return_value.get_batch_ticker_info.assert_not_called()


class TestFetchPricesBatch:
    """Tests for the fetch_prices_batch static method."""

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    def test_returns_prices_from_batch(self, mock_yf_cls):
        """Should return dict of (price, timestamp) from batch results."""
        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50),
            "MSFT": _make_ohlcv(380.00),
        }

        results = PriceFetcher.fetch_prices_batch(["AAPL", "MSFT"])

        assert len(results) == 2
        assert results["AAPL"][0] == Decimal("175.5")
        assert isinstance(results["AAPL"][1], datetime)

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    def test_agorot_conversion(self, mock_yf_cls):
        """Should apply Agorot conversion for .TA symbols."""
        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "TEVA.TA": _make_ohlcv(5678.0),
        }

        results = PriceFetcher.fetch_prices_batch(["TEVA.TA"])

        assert results["TEVA.TA"][0] == Decimal("56.78")

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    def test_skips_none_results(self, mock_yf_cls):
        """Should omit symbols that returned None from batch."""
        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50),
            "BAD": None,
        }

        results = PriceFetcher.fetch_prices_batch(["AAPL", "BAD"])

        assert len(results) == 1
        assert "AAPL" in results

    def test_empty_input_returns_empty(self):
        """Should return empty dict for empty input without calling API."""
        results = PriceFetcher.fetch_prices_batch([])
        assert results == {}


class TestUpdateAllAssetPricesEnrichment:
    """Tests for daily metrics + slow-changing field updates."""

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_upserts_daily_metrics_for_stocks(
        self, mock_cg: object, mock_yf_cls: object, mock_metrics: object
    ) -> None:
        db = MagicMock()
        aapl = _make_asset("AAPL")
        aapl.id = 1
        db.execute.return_value.scalars.return_value.all.return_value = [aapl]

        mock_client = mock_yf_cls.return_value  # ty: ignore[unresolved-attribute]
        mock_client.get_batch_ticker_info.return_value = {
            "AAPL": _make_ticker_market_data("AAPL", 175.50),
        }

        PriceFetcher.update_all_asset_prices(db)

        mock_metrics.upsert_daily_metrics.assert_called_once()  # ty: ignore[unresolved-attribute]
        mock_metrics.update_slow_changing_fields.assert_called_once()  # ty: ignore[unresolved-attribute]

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_upserts_daily_metrics_for_crypto(
        self, mock_cg: object, mock_yf_cls: object, mock_metrics: object
    ) -> None:
        db = MagicMock()
        btc = _make_asset("BTC", asset_class="Crypto")
        btc.id = 42
        db.execute.return_value.scalars.return_value.all.return_value = [btc]

        mock_cg.return_value.get_market_data.return_value = {  # ty: ignore[unresolved-attribute]
            "BTC": _make_crypto_market_data("BTC", 97500),
        }

        PriceFetcher.update_all_asset_prices(db)

        mock_metrics.upsert_daily_metrics.assert_called_once()  # ty: ignore[unresolved-attribute]
        mock_metrics.update_slow_changing_fields.assert_called_once()  # ty: ignore[unresolved-attribute]

    @patch("app.services.market_data.price_fetcher.AssetMetricsService")
    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_metrics_error_does_not_block_price_update(
        self, mock_cg: object, mock_yf_cls: object, mock_metrics: object
    ) -> None:
        """If metrics upsert fails, price should still be updated."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        aapl.id = 1
        db.execute.return_value.scalars.return_value.all.return_value = [aapl]

        mock_client = mock_yf_cls.return_value  # ty: ignore[unresolved-attribute]
        mock_client.get_batch_ticker_info.return_value = {
            "AAPL": _make_ticker_market_data("AAPL", 175.50),
        }
        mock_metrics.upsert_daily_metrics.side_effect = Exception("DB error")  # ty: ignore[unresolved-attribute]

        stats = PriceFetcher.update_all_asset_prices(db)

        assert aapl.last_fetched_price == Decimal("175.5")
        assert stats["updated"] == 1
