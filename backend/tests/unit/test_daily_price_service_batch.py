"""Tests for DailyPriceService batch pricing integration."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.asset import Asset
from app.services.market_data.daily_price_service import DailyPriceService
from app.services.market_data.yfinance_client import OHLCVRow


def _make_ohlcv(close: float, row_date: date) -> OHLCVRow:
    d = Decimal(str(close))
    return OHLCVRow(date=row_date, open=d, high=d, low=d, close=d, volume=Decimal("1000000"))


def _make_asset(asset_id: int, symbol: str, currency: str = "USD") -> Asset:
    asset = MagicMock(spec=Asset)
    asset.id = asset_id
    asset.symbol = symbol
    asset.currency = currency
    asset.asset_class = "Stock"
    return asset


class TestRefreshStockPricesBatch:
    """Tests for batch pricing in refresh_stock_prices."""

    @patch("app.services.market_data.daily_price_service._price_exists")
    @patch("app.services.market_data.daily_price_service._get_active_assets")
    @patch("app.services.market_data.daily_price_service._store_price")
    def test_uses_batch_fetch_with_target_date(self, mock_store, mock_get_assets, mock_exists):
        """Should call get_batch_prices_threaded once with target_date."""
        target = date(2024, 6, 15)
        aapl = _make_asset(1, "AAPL")
        msft = _make_asset(2, "MSFT")
        mock_get_assets.return_value = [aapl, msft]
        mock_exists.return_value = False

        mock_yf = MagicMock()
        mock_yf.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50, target),
            "MSFT": _make_ohlcv(380.00, target),
        }

        db = MagicMock()
        service = DailyPriceService(yf_client=mock_yf)
        result = service.refresh_stock_prices(db, target_date=target)

        mock_yf.get_batch_prices_threaded.assert_called_once()
        call_kwargs = mock_yf.get_batch_prices_threaded.call_args
        assert call_kwargs.kwargs.get("target_date") == target
        assert result["updated"] == 2

    @patch("app.services.market_data.daily_price_service._price_exists")
    @patch("app.services.market_data.daily_price_service._get_active_assets")
    @patch("app.services.market_data.daily_price_service._store_price")
    def test_skips_existing_before_batch(self, mock_store, mock_get_assets, mock_exists):
        """Assets with existing prices should be skipped and excluded from batch call."""
        target = date(2024, 6, 15)
        aapl = _make_asset(1, "AAPL")
        msft = _make_asset(2, "MSFT")
        mock_get_assets.return_value = [aapl, msft]
        mock_exists.side_effect = lambda db, aid, d: aid == 1  # AAPL exists

        mock_yf = MagicMock()
        mock_yf.get_batch_prices_threaded.return_value = {
            "MSFT": _make_ohlcv(380.00, target),
        }

        db = MagicMock()
        service = DailyPriceService(yf_client=mock_yf)
        result = service.refresh_stock_prices(db, target_date=target)

        # Only MSFT should be in the batch call
        call_args = mock_yf.get_batch_prices_threaded.call_args
        call_symbols = call_args.args[0] if call_args else []
        assert call_symbols == ["MSFT"]
        assert result["skipped"] == 1
        assert result["updated"] == 1

    @patch("app.services.market_data.daily_price_service._price_exists")
    @patch("app.services.market_data.daily_price_service._get_active_assets")
    @patch("app.services.market_data.daily_price_service._store_price")
    def test_agorot_conversion(self, mock_store, mock_get_assets, mock_exists):
        """Should divide .TA symbol prices by 100."""
        target = date(2024, 6, 15)
        teva = _make_asset(1, "TEVA.TA", currency="ILS")
        mock_get_assets.return_value = [teva]
        mock_exists.return_value = False

        mock_yf = MagicMock()
        mock_yf.get_batch_prices_threaded.return_value = {
            "TEVA.TA": _make_ohlcv(5678.0, target),
        }

        db = MagicMock()
        service = DailyPriceService(yf_client=mock_yf)
        service.refresh_stock_prices(db, target_date=target)

        # Check _store_price was called with converted price
        store_call = mock_store.call_args
        assert store_call.kwargs["closing_price"] == Decimal("56.78")

    @patch("app.services.market_data.daily_price_service._price_exists")
    @patch("app.services.market_data.daily_price_service._get_active_assets")
    @patch("app.services.market_data.daily_price_service._store_price")
    def test_partial_failure_counts(self, mock_store, mock_get_assets, mock_exists):
        """Symbols returning None from batch should count as failed."""
        target = date(2024, 6, 15)
        aapl = _make_asset(1, "AAPL")
        bad = _make_asset(2, "BADSTOCK")
        mock_get_assets.return_value = [aapl, bad]
        mock_exists.return_value = False

        mock_yf = MagicMock()
        mock_yf.get_batch_prices_threaded.return_value = {
            "AAPL": _make_ohlcv(175.50, target),
            "BADSTOCK": None,
        }

        db = MagicMock()
        service = DailyPriceService(yf_client=mock_yf)
        result = service.refresh_stock_prices(db, target_date=target)

        assert result["updated"] == 1
        assert result["failed"] == 1

    @patch("app.services.market_data.daily_price_service._price_exists")
    @patch("app.services.market_data.daily_price_service._get_active_assets")
    def test_all_existing_skips_batch_call(self, mock_get_assets, mock_exists):
        """When all assets already have prices, batch should not be called."""
        target = date(2024, 6, 15)
        aapl = _make_asset(1, "AAPL")
        mock_get_assets.return_value = [aapl]
        mock_exists.return_value = True

        mock_yf = MagicMock()
        db = MagicMock()
        service = DailyPriceService(yf_client=mock_yf)
        result = service.refresh_stock_prices(db, target_date=target)

        mock_yf.get_batch_prices_threaded.assert_not_called()
        assert result["skipped"] == 1
