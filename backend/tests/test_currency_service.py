"""Tests for CurrencyService historical rate fetching."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.exchange_rate import ExchangeRate
from app.services.currency_service import CurrencyService


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

    # Clean up before test to avoid interference from previous runs
    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM exchange_rates WHERE date IN ('2024-01-02', '2024-01-03', '2024-01-04')"
            )
        )
        conn.commit()

    yield engine

    # Clean up test data
    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM exchange_rates WHERE date IN ('2024-01-02', '2024-01-03', '2024-01-04')"
            )
        )
        conn.commit()


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    test_session_maker = sessionmaker(bind=test_db)
    session = test_session_maker()
    yield session
    session.rollback()
    session.close()


class TestFetchAndStoreHistoricalRates:
    """Tests for bulk historical exchange rate fetching."""

    @patch("app.services.currency_service.yf")
    def test_fetches_rates_for_date_range(self, mock_yf, db_session):
        """Should fetch and store historical exchange rates."""
        mock_history = pd.DataFrame(
            {"Close": [3.70, 3.71, 3.72]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_yf.Ticker.return_value = mock_ticker

        count = CurrencyService.fetch_and_store_historical_rates(
            db_session, "USD", "ILS", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 3
        mock_yf.Ticker.assert_called_once_with("USDILS=X")

        rates = (
            db_session.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == "USD",
                ExchangeRate.to_currency == "ILS",
            )
            .order_by(ExchangeRate.date)
            .all()
        )
        assert len(rates) == 3
        assert float(rates[0].rate) == 3.70

    @patch("app.services.currency_service.yf")
    def test_skips_existing_rates(self, mock_yf, db_session):
        """Should skip dates that already have rates."""
        # Pre-existing rate
        existing = ExchangeRate(
            from_currency="USD",
            to_currency="ILS",
            date=date(2024, 1, 3),
            rate=Decimal("999.00"),
        )
        db_session.add(existing)
        db_session.commit()

        mock_history = pd.DataFrame(
            {"Close": [3.70, 3.71, 3.72]},
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        mock_yf.Ticker.return_value = mock_ticker

        count = CurrencyService.fetch_and_store_historical_rates(
            db_session, "USD", "ILS", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 2  # Skipped Jan 3

        db_session.refresh(existing)
        assert float(existing.rate) == 999.00  # Unchanged

    def test_returns_zero_for_same_currency(self, db_session):
        """Should return 0 when from_currency equals to_currency."""
        count = CurrencyService.fetch_and_store_historical_rates(
            db_session, "USD", "USD", date(2024, 1, 2), date(2024, 1, 4)
        )
        assert count == 0

    @patch("app.services.currency_service.yf")
    def test_handles_empty_history(self, mock_yf, db_session):
        """Should handle empty history gracefully."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        count = CurrencyService.fetch_and_store_historical_rates(
            db_session, "USD", "EUR", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0

    @patch("app.services.currency_service.yf")
    def test_handles_yfinance_exception(self, mock_yf, db_session):
        """Should handle yfinance exceptions gracefully."""
        mock_yf.Ticker.side_effect = Exception("API error")

        count = CurrencyService.fetch_and_store_historical_rates(
            db_session, "USD", "CAD", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0
