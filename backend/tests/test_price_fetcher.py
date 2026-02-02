"""Tests for PriceFetcher historical price fetching."""

import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset
from app.models.asset_price import AssetPrice
from app.services.market_data.price_fetcher import PriceFetcher


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database for full compatibility."""
    db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)

    yield engine

    # Clean up test data
    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM asset_prices WHERE asset_id IN (SELECT id FROM assets WHERE symbol LIKE 'TEST_%')"
            )
        )
        conn.execute(text("DELETE FROM assets WHERE symbol LIKE 'TEST_%'"))
        conn.commit()


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    test_session_maker = sessionmaker(bind=test_db)
    session = test_session_maker()
    yield session
    session.rollback()
    session.close()


class TestFetchAndStoreHistoricalPrices:
    """Tests for bulk historical price fetching."""

    @patch("app.services.market_data.price_fetcher.yf")
    def test_fetches_stock_prices_for_date_range(self, mock_yf, db_session):
        """Should fetch and store historical prices for a stock."""
        # Setup: create a stock asset
        asset = Asset(
            symbol="TEST_AAPL",
            name="Apple Inc Test",
            asset_class="Stock",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        # Mock yfinance response
        mock_history = pd.DataFrame(
            {
                "Close": [150.0, 151.0, 152.0],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_yf.Ticker.return_value = mock_ticker

        # Act
        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session,
            asset.id,
            date(2024, 1, 2),
            date(2024, 1, 4),
        )

        # Assert
        assert count == 3
        mock_yf.Ticker.assert_called_once_with("TEST_AAPL")

        # Verify prices stored in DB
        prices = (
            db_session.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset.id)
            .order_by(AssetPrice.date)
            .all()
        )
        assert len(prices) == 3
        assert float(prices[0].closing_price) == 150.0
        assert prices[0].date == date(2024, 1, 2)

    @patch("app.services.market_data.price_fetcher.yf")
    def test_skips_dates_already_in_db(self, mock_yf, db_session):
        """Should skip dates that already have prices."""
        asset = Asset(
            symbol="TEST_AAPL2",
            name="Apple Test 2",
            asset_class="Stock",
            currency="USD",
        )
        db_session.add(asset)
        db_session.flush()

        # Pre-existing price
        existing = AssetPrice(
            asset_id=asset.id,
            date=date(2024, 1, 3),
            closing_price=Decimal("999.00"),
            currency="USD",
            source="existing",
        )
        db_session.add(existing)
        db_session.commit()

        # Mock returns all 3 days
        mock_history = pd.DataFrame(
            {"Close": [150.0, 151.0, 152.0]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_yf.Ticker.return_value = mock_ticker

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, date(2024, 1, 2), date(2024, 1, 4)
        )

        # Only 2 new prices inserted (skipped Jan 3)
        assert count == 2

        # Existing price unchanged
        db_session.refresh(existing)
        assert float(existing.closing_price) == 999.00

    @patch("app.services.market_data.price_fetcher.yf")
    def test_handles_israeli_stock_agorot_conversion(self, mock_yf, db_session):
        """Should convert .TA stocks from Agorot to ILS (divide by 100)."""
        asset = Asset(
            symbol="TEST_TEVA.TA",
            name="Teva Test",
            asset_class="Stock",
            currency="ILS",
        )
        db_session.add(asset)
        db_session.commit()

        # Yahoo returns Agorot (1234 = 12.34 ILS)
        mock_history = pd.DataFrame(
            {"Close": [1234.0]},
            index=pd.to_datetime(["2024-01-02"]),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_yf.Ticker.return_value = mock_ticker

        PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, date(2024, 1, 2), date(2024, 1, 2)
        )

        price = db_session.query(AssetPrice).filter(AssetPrice.asset_id == asset.id).first()
        assert float(price.closing_price) == 12.34  # Converted from Agorot

    @patch("app.services.market_data.price_fetcher.yf")
    def test_skips_cash_assets(self, mock_yf, db_session):
        """Should skip cash assets entirely."""
        asset = Asset(
            symbol="TEST_USD",
            name="US Dollar Test",
            asset_class="Cash",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0
        mock_yf.Ticker.assert_not_called()

    @patch("app.services.market_data.price_fetcher.yf")
    def test_handles_empty_history(self, mock_yf, db_session):
        """Should handle empty history gracefully."""
        asset = Asset(
            symbol="TEST_EMPTY",
            name="Empty Test",
            asset_class="Stock",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0

    @patch("app.services.market_data.price_fetcher.yf")
    def test_handles_yfinance_exception(self, mock_yf, db_session):
        """Should handle yfinance exceptions gracefully."""
        asset = Asset(
            symbol="TEST_ERROR",
            name="Error Test",
            asset_class="Stock",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        mock_yf.Ticker.side_effect = Exception("API error")

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0

    def test_returns_zero_for_nonexistent_asset(self, db_session):
        """Should return 0 for asset that doesn't exist."""
        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, 999999, date(2024, 1, 2), date(2024, 1, 4)
        )
        assert count == 0


class TestFetchAndStoreHistoricalCryptoPrices:
    """Tests for crypto historical price fetching."""

    @patch("app.services.market_data.price_fetcher.CryptoCompareClient")
    def test_uses_cryptocompare_for_old_dates(self, mock_cc_class, db_session):
        """Should use CryptoCompare for dates older than 365 days."""
        asset = Asset(
            symbol="TEST_BTC",
            name="Bitcoin Test",
            asset_class="Crypto",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        # Dates more than 365 days ago
        old_start = date.today() - timedelta(days=400)
        old_end = date.today() - timedelta(days=390)

        # Mock CryptoCompare response
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = [
            (old_start, Decimal("40000")),
            (old_start + timedelta(days=1), Decimal("40100")),
        ]
        mock_cc_class.return_value = mock_client

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, old_start, old_end
        )

        assert count >= 2
        mock_client.get_price_history.assert_called()

        # Verify prices stored in DB
        prices = (
            db_session.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset.id)
            .order_by(AssetPrice.date)
            .all()
        )
        assert len(prices) >= 2
        assert prices[0].date == old_start

    @patch("app.services.market_data.price_fetcher.CoinGeckoClient")
    def test_uses_coingecko_for_recent_dates(self, mock_cg_class, db_session):
        """Should use CoinGecko for dates within 365 days."""
        asset = Asset(
            symbol="TEST_ETH",
            name="Ethereum Test",
            asset_class="Crypto",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        # Recent dates (within 365 days)
        recent_start = date.today() - timedelta(days=30)
        recent_end = date.today() - timedelta(days=25)

        mock_client = MagicMock()
        mock_client.get_price_history.return_value = [
            (recent_start, Decimal("3000")),
            (recent_start + timedelta(days=1), Decimal("3050")),
        ]
        mock_cg_class.return_value = mock_client

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, recent_start, recent_end
        )

        assert count >= 2
        mock_client.get_price_history.assert_called()

    @patch("app.services.market_data.price_fetcher.CryptoCompareClient")
    @patch("app.services.market_data.price_fetcher.CoinGeckoClient")
    def test_uses_both_for_spanning_dates(self, mock_cg_class, mock_cc_class, db_session):
        """Should use both CryptoCompare and CoinGecko for date ranges spanning the 365-day boundary."""
        asset = Asset(
            symbol="TEST_SOL",
            name="Solana Test",
            asset_class="Crypto",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        # Date range that spans the 365-day boundary
        old_date = date.today() - timedelta(days=400)
        recent_date = date.today() - timedelta(days=30)

        mock_cc_client = MagicMock()
        mock_cc_client.get_price_history.return_value = [
            (old_date, Decimal("100")),
        ]
        mock_cc_class.return_value = mock_cc_client

        mock_cg_client = MagicMock()
        mock_cg_client.get_price_history.return_value = [
            (recent_date, Decimal("150")),
        ]
        mock_cg_class.return_value = mock_cg_client

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, old_date, recent_date
        )

        # Both clients should be called
        mock_cc_client.get_price_history.assert_called()
        mock_cg_client.get_price_history.assert_called()
        assert count >= 2

    @patch("app.services.market_data.price_fetcher.CoinGeckoClient")
    def test_skips_existing_crypto_prices(self, mock_cg_class, db_session):
        """Should skip dates that already have prices for crypto."""
        asset = Asset(
            symbol="TEST_DOGE",
            name="Dogecoin Test",
            asset_class="Crypto",
            currency="USD",
        )
        db_session.add(asset)
        db_session.flush()

        recent_start = date.today() - timedelta(days=30)
        recent_end = date.today() - timedelta(days=28)

        # Pre-existing price
        existing = AssetPrice(
            asset_id=asset.id,
            date=recent_start + timedelta(days=1),
            closing_price=Decimal("0.999"),
            currency="USD",
            source="existing",
        )
        db_session.add(existing)
        db_session.commit()

        mock_client = MagicMock()
        mock_client.get_price_history.return_value = [
            (recent_start, Decimal("0.10")),
            (recent_start + timedelta(days=1), Decimal("0.11")),  # Already exists
            (recent_start + timedelta(days=2), Decimal("0.12")),
        ]
        mock_cg_class.return_value = mock_client

        count = PriceFetcher.fetch_and_store_historical_prices(
            db_session, asset.id, recent_start, recent_end
        )

        # Only 2 new prices inserted (skipped the existing one)
        assert count == 2

        # Existing price unchanged
        db_session.refresh(existing)
        assert float(existing.closing_price) == 0.999
