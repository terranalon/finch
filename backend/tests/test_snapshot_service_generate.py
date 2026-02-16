"""Tests for SnapshotService.generate_account_snapshots."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, HistoricalSnapshot, Holding, Transaction
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

    # Clean up test data in dependency order
    with engine.connect() as conn:
        account_filter = "name LIKE 'Test Snap Gen%'"
        holding_subquery = f"SELECT id FROM holdings WHERE account_id IN (SELECT id FROM accounts WHERE {account_filter})"

        conn.execute(text(f"DELETE FROM transactions WHERE holding_id IN ({holding_subquery})"))
        conn.execute(
            text(
                f"DELETE FROM holdings WHERE account_id IN (SELECT id FROM accounts WHERE {account_filter})"
            )
        )
        conn.execute(
            text(
                f"DELETE FROM historical_snapshots WHERE account_id IN (SELECT id FROM accounts WHERE {account_filter})"
            )
        )
        conn.execute(text(f"DELETE FROM accounts WHERE {account_filter}"))
        conn.execute(text("DELETE FROM assets WHERE symbol LIKE '%.JOINTEST'"))
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
    account = Account(
        name="Test Snap Gen Account",
        account_type="brokerage",
        currency="USD",
    )
    db_session.add(account)
    db_session.commit()
    return account


class TestGenerateAccountSnapshots:
    """Tests for unified snapshot generation."""

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    @patch("app.services.portfolio.holding_valuation_service.PriceFetcher")
    @patch("app.services.portfolio.holding_valuation_service.CurrencyService")
    def test_generates_snapshots_for_date_range(
        self, mock_currency, mock_price, mock_recon, mock_fetcher, db_session, test_account
    ):
        """Should generate HistoricalSnapshot for each date in range."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)

        holding = {
            "asset_id": 1,
            "quantity": Decimal("10"),
            "currency": "USD",
            "asset_class": "Stock",
            "symbol": "AAPL",
        }
        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (date(2024, 1, 1), [holding]),
                (date(2024, 1, 2), [holding]),
                (date(2024, 1, 3), [holding]),
            ]
        )

        mock_price.get_price_for_date.return_value = Decimal("150")
        mock_currency.return_value.get_exchange_rate.return_value = Decimal("3.70")
        mock_fetcher.ensure_historical_data.return_value = {
            "prices_fetched": 3,
            "rates_fetched": 3,
        }

        stats = SnapshotService(db_session).generate_account_snapshots(test_account.id, start, end)

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

        SnapshotService(db_session).generate_account_snapshots(
            test_account.id,
            date(2024, 1, 2),
            date(2024, 1, 2),
            invalidate_existing=True,
        )

        # Old snapshot should be deleted
        assert db_session.get(HistoricalSnapshot, old_id) is None

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    @patch("app.services.portfolio.holding_valuation_service.PriceFetcher")
    @patch("app.services.portfolio.holding_valuation_service.CurrencyService")
    def test_skips_existing_snapshots_when_not_invalidating(
        self, mock_currency, mock_price, mock_recon, mock_fetcher, db_session, test_account
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

        holding = {
            "asset_id": 1,
            "quantity": Decimal("10"),
            "currency": "USD",
            "asset_class": "Stock",
            "symbol": "AAPL",
        }
        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (date(2024, 1, 1), [holding]),
                (date(2024, 1, 2), [holding]),  # Already exists
                (date(2024, 1, 3), [holding]),
            ]
        )
        mock_fetcher.ensure_historical_data.return_value = {}
        mock_price.get_price_for_date.return_value = Decimal("150")
        mock_currency.return_value.get_exchange_rate.return_value = Decimal("3.70")

        stats = SnapshotService(db_session).generate_account_snapshots(
            test_account.id,
            date(2024, 1, 1),
            date(2024, 1, 3),
            invalidate_existing=False,
        )

        assert stats["created"] == 2  # Only 2 new (Jan 1 and Jan 3)
        assert stats["skipped"] == 1  # Jan 2 skipped

        # Old snapshot unchanged
        db_session.refresh(old_snapshot)
        assert old_snapshot.total_value_usd is not None
        assert float(old_snapshot.total_value_usd) == 9999

    @patch("app.services.portfolio.snapshot_service.HistoricalDataFetcher")
    @patch("app.services.portfolio.snapshot_service.PortfolioReconstructionService")
    def test_skips_dates_with_empty_holdings(
        self, mock_recon, mock_fetcher, db_session, test_account
    ):
        """Should skip dates with empty holdings (no $0 snapshots)."""
        mock_recon.reconstruct_holdings_timeline.return_value = iter(
            [
                (date(2024, 1, 1), []),  # No holdings yet
                (date(2024, 1, 2), []),  # Still empty
                (date(2024, 1, 3), []),  # Still empty
            ]
        )
        mock_fetcher.ensure_historical_data.return_value = {}

        stats = SnapshotService(db_session).generate_account_snapshots(
            test_account.id,
            date(2024, 1, 1),
            date(2024, 1, 3),
        )

        assert stats["created"] == 0
        assert stats["skipped"] == 3

        snapshots = (
            db_session.query(HistoricalSnapshot)
            .filter(HistoricalSnapshot.account_id == test_account.id)
            .all()
        )
        assert len(snapshots) == 0


class TestAmbiguousJoinRegression:
    """Regression test for GitHub issue #34.

    Transaction has two FKs to Holding (holding_id and to_holding_id).
    Implicit .join(Holding) is ambiguous and crashes with
    AmbiguousForeignKeysError when to_holding_id is populated.
    """

    def test_transaction_join_with_forex_conversion(self, db_session, test_account):
        """Query joining Transaction->Holding should work when to_holding_id is set."""
        usd_asset = Asset(
            symbol="USD.CASH.JOINTEST",
            name="US Dollar Cash",
            asset_class="Cash",
            currency="USD",
        )
        ils_asset = Asset(
            symbol="ILS.CASH.JOINTEST",
            name="Israeli Shekel Cash",
            asset_class="Cash",
            currency="ILS",
        )
        db_session.add_all([usd_asset, ils_asset])
        db_session.flush()

        usd_holding = Holding(
            account_id=test_account.id,
            asset_id=usd_asset.id,
            quantity=Decimal("1000"),
            cost_basis=Decimal("1000"),
        )
        ils_holding = Holding(
            account_id=test_account.id,
            asset_id=ils_asset.id,
            quantity=Decimal("3700"),
            cost_basis=Decimal("3700"),
        )
        db_session.add_all([usd_holding, ils_holding])
        db_session.flush()

        forex_txn = Transaction(
            holding_id=usd_holding.id,
            to_holding_id=ils_holding.id,
            date=date(2024, 6, 1),
            type="Forex Conversion",
            quantity=Decimal("1000"),
            price_per_unit=Decimal("3.70"),
            amount=Decimal("1000"),
            to_amount=Decimal("3700"),
            exchange_rate=Decimal("3.70"),
            fees=Decimal("0"),
        )
        db_session.add(forex_txn)
        db_session.flush()

        # This is the exact query pattern from snapshot_service.py:61-67.
        # Before the fix, this raises AmbiguousForeignKeysError.
        result = (
            db_session.query(Transaction)
            .join(Transaction.holding)
            .filter(Holding.account_id == test_account.id)
            .first()
        )
        assert result is not None
        assert result.id == forex_txn.id
