"""Tests for SnapshotService.generate_account_snapshots."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, HistoricalSnapshot, Portfolio
from app.models.user import User
from app.services.auth import AuthService
from app.services.portfolio.snapshot_service import SnapshotService


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
                "DELETE FROM historical_snapshots WHERE account_id IN (SELECT id FROM accounts WHERE name LIKE 'Test Snap Gen%')"
            )
        )
        conn.execute(text("DELETE FROM accounts WHERE name LIKE 'Test Snap Gen%'"))
        conn.execute(text("DELETE FROM portfolios WHERE name LIKE 'Test Snap Gen%'"))
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_snap_gen%'"))
        conn.commit()


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    test_session_maker = sessionmaker(bind=test_db)
    session = test_session_maker()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_account(db_session):
    """Create a test account."""
    user = User(
        email="test_snap_gen@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    portfolio = Portfolio(user_id=user.id, name="Test Snap Gen Portfolio")
    db_session.add(portfolio)
    db_session.flush()

    account = Account(
        portfolio_id=portfolio.id,
        name="Test Snap Gen Account",
        account_type="brokerage",
        currency="USD",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    return account


class TestGenerateAccountSnapshots:
    """Tests for unified snapshot generation."""

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    @patch("app.services.portfolio.snapshot_service.PriceFetcher")
    @patch("app.services.portfolio.snapshot_service.CurrencyService")
    def test_generates_snapshots_for_date_range(
        self, mock_currency, mock_price, mock_recon, mock_fetcher, db_session, test_account
    ):
        """Should generate HistoricalSnapshot for each date in range."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)

        # Mock streaming reconstruction
        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (
                    date(2024, 1, 1),
                    [
                        {
                            "asset_id": 1,
                            "quantity": Decimal("10"),
                            "currency": "USD",
                            "asset_class": "Stock",
                            "symbol": "AAPL",
                        }
                    ],
                ),
                (
                    date(2024, 1, 2),
                    [
                        {
                            "asset_id": 1,
                            "quantity": Decimal("10"),
                            "currency": "USD",
                            "asset_class": "Stock",
                            "symbol": "AAPL",
                        }
                    ],
                ),
                (
                    date(2024, 1, 3),
                    [
                        {
                            "asset_id": 1,
                            "quantity": Decimal("10"),
                            "currency": "USD",
                            "asset_class": "Stock",
                            "symbol": "AAPL",
                        }
                    ],
                ),
            ]
        )

        mock_price.get_price_for_date.return_value = Decimal("150")
        mock_currency.get_exchange_rate.return_value = Decimal("3.70")
        mock_fetcher.ensure_historical_data.return_value = {
            "prices_fetched": 3,
            "rates_fetched": 3,
        }

        stats = SnapshotService.generate_account_snapshots(db_session, test_account.id, start, end)

        assert stats["created"] == 3

        snapshots = (
            db_session.query(HistoricalSnapshot)
            .filter(HistoricalSnapshot.account_id == test_account.id)
            .order_by(HistoricalSnapshot.date)
            .all()
        )
        assert len(snapshots) == 3
        assert snapshots[0].date == date(2024, 1, 1)
        assert snapshots[0].total_value_usd > 0

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    def test_invalidate_existing_deletes_old_snapshots(
        self, mock_recon, mock_fetcher, db_session, test_account
    ):
        """Should delete existing snapshots when invalidate_existing=True."""
        # Pre-existing snapshot
        old_snapshot = HistoricalSnapshot(
            account_id=test_account.id,
            date=date(2024, 1, 2),
            total_value_usd=Decimal("9999"),
            total_value_ils=Decimal("36000"),
        )
        db_session.add(old_snapshot)
        db_session.commit()
        old_id = old_snapshot.id

        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (date(2024, 1, 2), []),  # Empty holdings
            ]
        )
        mock_fetcher.ensure_historical_data.return_value = {}

        SnapshotService.generate_account_snapshots(
            db_session,
            test_account.id,
            date(2024, 1, 2),
            date(2024, 1, 2),
            invalidate_existing=True,
        )

        # Old snapshot should be deleted
        assert db_session.get(HistoricalSnapshot, old_id) is None

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    def test_skips_existing_snapshots_when_not_invalidating(
        self, mock_recon, mock_fetcher, db_session, test_account
    ):
        """Should skip dates that already have snapshots when not invalidating."""
        # Pre-existing snapshot
        old_snapshot = HistoricalSnapshot(
            account_id=test_account.id,
            date=date(2024, 1, 2),
            total_value_usd=Decimal("9999"),
            total_value_ils=Decimal("36000"),
        )
        db_session.add(old_snapshot)
        db_session.commit()

        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (date(2024, 1, 1), []),
                (date(2024, 1, 2), []),  # Already exists
                (date(2024, 1, 3), []),
            ]
        )
        mock_fetcher.ensure_historical_data.return_value = {}

        stats = SnapshotService.generate_account_snapshots(
            db_session,
            test_account.id,
            date(2024, 1, 1),
            date(2024, 1, 3),
            invalidate_existing=False,
        )

        assert stats["created"] == 2  # Only 2 new (Jan 1 and Jan 3)
        assert stats["skipped"] == 1  # Jan 2 skipped

        # Old snapshot unchanged
        db_session.refresh(old_snapshot)
        assert float(old_snapshot.total_value_usd) == 9999
