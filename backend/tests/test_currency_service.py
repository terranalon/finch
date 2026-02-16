"""Tests for CurrencyService historical rate fetching."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.exchange_rate import ExchangeRate
from app.services.market_data.yfinance_client import OHLCVRow
from app.services.shared.currency_service import CurrencyService


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

    @patch("app.services.shared.currency_service.YFinanceClient")
    def test_fetches_rates_for_date_range(self, mock_client_cls, db_session):
        """Should fetch and store historical exchange rates."""
        mock_client = mock_client_cls.return_value
        mock_client.get_forex_history.return_value = [
            OHLCVRow(
                date=date(2024, 1, 2),
                open=Decimal("3.69"),
                high=Decimal("3.75"),
                low=Decimal("3.68"),
                close=Decimal("3.70"),
                volume=Decimal("0"),
            ),
            OHLCVRow(
                date=date(2024, 1, 3),
                open=Decimal("3.70"),
                high=Decimal("3.76"),
                low=Decimal("3.69"),
                close=Decimal("3.71"),
                volume=Decimal("0"),
            ),
            OHLCVRow(
                date=date(2024, 1, 4),
                open=Decimal("3.71"),
                high=Decimal("3.77"),
                low=Decimal("3.70"),
                close=Decimal("3.72"),
                volume=Decimal("0"),
            ),
        ]

        count = CurrencyService(db_session).fetch_and_store_historical_rates(
            "USD", "ILS", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 3

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
        assert rates[0].rate == Decimal("3.70")

    @patch("app.services.shared.currency_service.YFinanceClient")
    def test_skips_existing_rates(self, mock_client_cls, db_session):
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

        mock_client = mock_client_cls.return_value
        mock_client.get_forex_history.return_value = [
            OHLCVRow(
                date=date(2024, 1, 2),
                open=Decimal("3.69"),
                high=Decimal("3.75"),
                low=Decimal("3.68"),
                close=Decimal("3.70"),
                volume=Decimal("0"),
            ),
            OHLCVRow(
                date=date(2024, 1, 3),
                open=Decimal("3.70"),
                high=Decimal("3.76"),
                low=Decimal("3.69"),
                close=Decimal("3.71"),
                volume=Decimal("0"),
            ),
            OHLCVRow(
                date=date(2024, 1, 4),
                open=Decimal("3.71"),
                high=Decimal("3.77"),
                low=Decimal("3.70"),
                close=Decimal("3.72"),
                volume=Decimal("0"),
            ),
        ]

        count = CurrencyService(db_session).fetch_and_store_historical_rates(
            "USD", "ILS", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 2  # Skipped Jan 3

        db_session.refresh(existing)
        assert float(existing.rate) == 999.00  # Unchanged

    def test_returns_zero_for_same_currency(self, db_session):
        """Should return 0 when from_currency equals to_currency."""
        count = CurrencyService(db_session).fetch_and_store_historical_rates(
            "USD", "USD", date(2024, 1, 2), date(2024, 1, 4)
        )
        assert count == 0

    @patch("app.services.shared.currency_service.YFinanceClient")
    def test_handles_empty_history(self, mock_client_cls, db_session):
        """Should handle empty history gracefully."""
        mock_client = mock_client_cls.return_value
        mock_client.get_forex_history.return_value = []

        count = CurrencyService(db_session).fetch_and_store_historical_rates(
            "USD", "EUR", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0

    @patch("app.services.shared.currency_service.YFinanceClient")
    def test_handles_yfinance_exception(self, mock_client_cls, db_session):
        """Should handle yfinance exceptions gracefully."""
        mock_client = mock_client_cls.return_value
        mock_client.get_forex_history.return_value = []

        count = CurrencyService(db_session).fetch_and_store_historical_rates(
            "USD", "CAD", date(2024, 1, 2), date(2024, 1, 4)
        )

        assert count == 0
