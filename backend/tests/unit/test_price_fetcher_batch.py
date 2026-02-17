"""Tests for PriceFetcher batch pricing integration."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models import Asset
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.market_data.yfinance_client import OHLCVRow


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


class TestUpdateAllAssetPricesBatch:
    """Tests for batch pricing in update_all_asset_prices."""

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_uses_batch_for_non_crypto(self, mock_cg, mock_yf_cls):
        """Should call get_batch_prices_threaded once with all non-crypto symbols."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        msft = _make_asset("MSFT")
        db.execute.return_value.scalars.return_value.all.return_value = [aapl, msft]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50),
            "MSFT": _make_ohlcv(380.00),
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        mock_client.get_batch_prices_threaded.assert_called_once()
        call_symbols = mock_client.get_batch_prices_threaded.call_args[0][0]
        assert set(call_symbols) == {"AAPL", "MSFT"}
        assert stats["updated"] == 2
        assert aapl.last_fetched_price == Decimal("175.5")
        assert msft.last_fetched_price == Decimal("380.0")

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_agorot_conversion_in_batch(self, mock_cg, mock_yf_cls):
        """Should divide .TA symbol prices by 100 (Agorot to ILS)."""
        db = MagicMock()
        teva = _make_asset("TEVA.TA", currency="ILS")
        db.execute.return_value.scalars.return_value.all.return_value = [teva]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "TEVA.TA": _make_ohlcv(5678.0),
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["updated"] == 1
        assert teva.last_fetched_price == Decimal("56.78")

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_partial_batch_failure(self, mock_cg, mock_yf_cls):
        """Some symbols returning None should count as failed, others succeed."""
        db = MagicMock()
        aapl = _make_asset("AAPL")
        bad = _make_asset("BADSTOCK")
        db.execute.return_value.scalars.return_value.all.return_value = [aapl, bad]

        mock_client = mock_yf_cls.return_value
        mock_client.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50),
            "BADSTOCK": None,
        }

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["updated"] == 1
        assert stats["failed"] == 1

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_crypto_still_uses_coingecko(self, mock_cg_fn, mock_yf_cls):
        """Crypto assets should still use CoinGecko batch, not YFinance."""
        db = MagicMock()
        btc = _make_asset("bitcoin", asset_class="Crypto")
        db.execute.return_value.scalars.return_value.all.return_value = [btc]

        mock_cg = MagicMock()
        mock_cg.get_current_prices.return_value = {"bitcoin": Decimal("50000")}
        mock_cg_fn.return_value = mock_cg

        PriceFetcher.update_all_asset_prices(db)

        mock_cg.get_current_prices.assert_called_once()
        mock_yf_cls.return_value.get_batch_prices_threaded.assert_not_called()

    @patch("app.services.market_data.price_fetcher.YFinanceClient")
    @patch("app.services.market_data.price_fetcher._get_coingecko_client")
    def test_skips_cash_and_empty_symbols(self, mock_cg, mock_yf_cls):
        """Cash assets and assets without symbols should be skipped."""
        db = MagicMock()
        cash = _make_asset("USD", asset_class="Cash")
        empty = _make_asset(None, asset_class="Stock")
        db.execute.return_value.scalars.return_value.all.return_value = [cash, empty]

        stats = PriceFetcher.update_all_asset_prices(db)

        assert stats["skipped"] == 2
        mock_yf_cls.return_value.get_batch_prices_threaded.assert_not_called()


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
