"""Tests for crypto historical price routing in PriceFetcher."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.market_data.price_fetcher import PriceFetcher


@pytest.fixture()
def mock_coingecko():
    """Mock CoinGeckoClient via _fetch_crypto_historical_prices."""
    with patch.object(
        PriceFetcher,
        "_fetch_crypto_historical_prices",
    ) as mock:
        yield mock


@pytest.fixture()
def mock_yfinance():
    """Mock YFinanceClient for non-crypto path."""
    with patch("app.services.market_data.price_fetcher.YFinanceClient") as cls:
        yield cls.return_value


class TestGetHistoricalPricesCryptoRouting:
    """Tests for the is_crypto routing in get_historical_prices."""

    def test_crypto_routes_to_coingecko(self, mock_coingecko: MagicMock) -> None:
        """When is_crypto=True, should route to _fetch_crypto_historical_prices."""
        today = date.today()
        mock_coingecko.return_value = [
            (today - timedelta(days=1), Decimal("95000")),
            (today, Decimal("96000")),
        ]

        result = PriceFetcher.get_historical_prices("BTC", "1mo", is_crypto=True)

        assert result is not None
        assert result["symbol"] == "BTC"
        assert result["period"] == "1mo"
        assert len(result["data"]) == 2
        assert result["data"][-1]["close"] == 96000.0
        mock_coingecko.assert_called_once()

    def test_non_crypto_routes_to_yfinance(
        self, mock_coingecko: MagicMock, mock_yfinance: MagicMock
    ) -> None:
        """When is_crypto=False (default), should route to YFinance."""
        from app.services.market_data.yfinance_client import OHLCVRow

        mock_yfinance.get_historical_data.return_value = [
            OHLCVRow(
                date=date(2024, 6, 1),
                open=Decimal("150"),
                high=Decimal("155"),
                low=Decimal("148"),
                close=Decimal("152"),
                volume=Decimal("1000000"),
            ),
        ]

        result = PriceFetcher.get_historical_prices("AAPL", "1mo", is_crypto=False)

        assert result is not None
        assert result["data"][0]["close"] == 152.0
        mock_coingecko.assert_not_called()
        mock_yfinance.get_historical_data.assert_called_once_with("AAPL", period="1mo")

    def test_crypto_default_is_false(self, mock_yfinance: MagicMock) -> None:
        """Default is_crypto should be False (YFinance path)."""
        mock_yfinance.get_historical_data.return_value = []

        result = PriceFetcher.get_historical_prices("AAPL", "1mo")

        assert result is None
        mock_yfinance.get_historical_data.assert_called_once()


class TestGetCryptoHistoricalPrices:
    """Tests for _get_crypto_historical_prices period-to-date conversion."""

    def test_1mo_period(self, mock_coingecko: MagicMock) -> None:
        """1mo should request ~30 days of data."""
        today = date.today()
        mock_coingecko.return_value = [
            (today - timedelta(days=15), Decimal("95000")),
        ]

        result = PriceFetcher._get_crypto_historical_prices("BTC", "1mo")

        assert result is not None
        args = mock_coingecko.call_args
        start_date = args[0][1]
        end_date = args[0][2]
        assert (end_date - start_date).days == 30

    def test_1y_period(self, mock_coingecko: MagicMock) -> None:
        """1y should request 365 days of data."""
        mock_coingecko.return_value = [
            (date.today() - timedelta(days=100), Decimal("60000")),
        ]

        PriceFetcher._get_crypto_historical_prices("BTC", "1y")

        args = mock_coingecko.call_args
        start_date = args[0][1]
        end_date = args[0][2]
        assert (end_date - start_date).days == 365

    def test_2y_period_delegates_to_dual_source(self, mock_coingecko: MagicMock) -> None:
        """2y (730 days) should delegate to _fetch_crypto_historical_prices
        which handles the CoinGecko/CryptoCompare split for >365 days."""
        mock_coingecko.return_value = [
            (date.today() - timedelta(days=500), Decimal("30000")),
            (date.today() - timedelta(days=100), Decimal("60000")),
        ]

        result = PriceFetcher._get_crypto_historical_prices("BTC", "2y")

        assert result is not None
        args = mock_coingecko.call_args
        start_date = args[0][1]
        end_date = args[0][2]
        assert (end_date - start_date).days == 730

    def test_empty_prices_returns_none(self, mock_coingecko: MagicMock) -> None:
        """Should return None when no prices are available."""
        mock_coingecko.return_value = []

        result = PriceFetcher._get_crypto_historical_prices("UNKNOWN", "1mo")

        assert result is None

    def test_response_format(self, mock_coingecko: MagicMock) -> None:
        """Response should have correct structure with OHLCV fields."""
        d = date(2024, 6, 15)
        mock_coingecko.return_value = [(d, Decimal("95123.45"))]

        result = PriceFetcher._get_crypto_historical_prices("BTC", "1mo")

        assert result is not None
        item = result["data"][0]
        assert item["date"] == "2024-06-15"
        assert item["close"] == 95123.45
        assert item["open"] == 95123.45
        assert item["high"] == 95123.45
        assert item["low"] == 95123.45
        assert item["volume"] == 0

    def test_ytd_period(self, mock_coingecko: MagicMock) -> None:
        """ytd should request from Jan 1 of current year."""
        today = date.today()
        expected_days = (today - date(today.year, 1, 1)).days or 1
        mock_coingecko.return_value = [
            (today - timedelta(days=10), Decimal("95000")),
        ]

        PriceFetcher._get_crypto_historical_prices("ETH", "ytd")

        args = mock_coingecko.call_args
        start_date = args[0][1]
        end_date = args[0][2]
        assert (end_date - start_date).days == expected_days

    def test_unknown_period_defaults_to_30_days(self, mock_coingecko: MagicMock) -> None:
        """Unknown period string should default to 30 days."""
        mock_coingecko.return_value = [
            (date.today(), Decimal("100")),
        ]

        PriceFetcher._get_crypto_historical_prices("ETH", "unknown_period")

        args = mock_coingecko.call_args
        start_date = args[0][1]
        end_date = args[0][2]
        assert (end_date - start_date).days == 30
