"""Tests for PortfolioReconstructionService streaming reconstruction."""

import os
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, Holding, Portfolio, Transaction
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService


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
                "DELETE FROM transactions WHERE holding_id IN (SELECT id FROM holdings WHERE account_id IN (SELECT id FROM accounts WHERE name LIKE 'Test Recon%'))"
            )
        )
        conn.execute(
            text(
                "DELETE FROM holdings WHERE account_id IN (SELECT id FROM accounts WHERE name LIKE 'Test Recon%')"
            )
        )
        conn.execute(text("DELETE FROM accounts WHERE name LIKE 'Test Recon%'"))
        conn.execute(text("DELETE FROM portfolios WHERE name LIKE 'Test Recon%'"))
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_recon%'"))
        conn.execute(text("DELETE FROM assets WHERE symbol LIKE 'RECON_TEST_%'"))
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
def account_with_transactions(db_session):
    """Create an account with a buy transaction for testing."""
    # Create user
    user = User(
        email="test_recon_stream@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    # Create portfolio
    portfolio = Portfolio(user_id=user.id, name="Test Recon Portfolio")
    db_session.add(portfolio)
    db_session.flush()

    # Create account
    account = Account(
        name="Test Recon Account",
        portfolio_id=portfolio.id,
        account_type="brokerage",
        currency="USD",
    )
    db_session.add(account)
    db_session.flush()

    # Create asset
    asset = Asset(
        symbol="RECON_TEST_AAPL",
        name="Apple Test",
        asset_class="Stock",
        currency="USD",
    )
    db_session.add(asset)
    db_session.flush()

    # Create holding
    holding = Holding(
        account_id=account.id,
        asset_id=asset.id,
        quantity=Decimal("0"),
        cost_basis=Decimal("0"),
    )
    db_session.add(holding)
    db_session.flush()

    # Create buy transaction
    buy_date = date(2024, 1, 15)
    txn = Transaction(
        holding_id=holding.id,
        type="Buy",
        date=buy_date,
        quantity=Decimal("10"),
        price_per_unit=Decimal("150.00"),
        amount=Decimal("1500.00"),
    )
    db_session.add(txn)
    db_session.commit()

    return {
        "account_id": account.id,
        "asset_id": asset.id,
        "holding_id": holding.id,
        "buy_date": buy_date,
    }


class TestReconstructHoldingsTimeline:
    """Tests for streaming reconstruction."""

    def test_yields_holdings_at_each_date(self, db_session, account_with_transactions):
        """Should yield holdings state for each calendar day in range."""
        account_id = account_with_transactions["account_id"]
        buy_date = account_with_transactions["buy_date"]

        results = list(
            PortfolioReconstructionService.reconstruct_holdings_timeline(
                db_session, account_id, buy_date, buy_date + timedelta(days=2)
            )
        )

        # Should yield 3 days
        assert len(results) == 3

        # Each result is (date, holdings_list)
        dates = [r[0] for r in results]
        assert dates == [
            buy_date,
            buy_date + timedelta(days=1),
            buy_date + timedelta(days=2),
        ]

    def test_holdings_persist_between_transaction_dates(
        self, db_session, account_with_transactions
    ):
        """Holdings should forward-fill on days with no transactions."""
        account_id = account_with_transactions["account_id"]
        buy_date = account_with_transactions["buy_date"]

        results = list(
            PortfolioReconstructionService.reconstruct_holdings_timeline(
                db_session, account_id, buy_date, buy_date + timedelta(days=5)
            )
        )

        # All days should have the same holdings (no sell transaction)
        for snapshot_date, holdings in results:
            assert len(holdings) == 1
            assert holdings[0]["quantity"] == Decimal("10")

    def test_consistency_with_point_in_time_reconstruction(
        self, db_session, account_with_transactions
    ):
        """Streaming result should match point-in-time reconstruction for each date."""
        account_id = account_with_transactions["account_id"]
        buy_date = account_with_transactions["buy_date"]

        timeline_results = dict(
            PortfolioReconstructionService.reconstruct_holdings_timeline(
                db_session, account_id, buy_date, buy_date + timedelta(days=3)
            )
        )

        for check_date in [
            buy_date,
            buy_date + timedelta(days=1),
            buy_date + timedelta(days=2),
        ]:
            # Point-in-time reconstruction
            point_result = PortfolioReconstructionService.reconstruct_holdings(
                db_session, account_id, check_date, apply_ticker_changes=False
            )

            timeline_holdings = timeline_results[check_date]

            # Compare quantities
            point_map = {h["asset_id"]: h["quantity"] for h in point_result}
            timeline_map = {h["asset_id"]: h["quantity"] for h in timeline_holdings}

            assert point_map == timeline_map, f"Mismatch on {check_date}"

    def test_handles_date_range_before_any_transactions(
        self, db_session, account_with_transactions
    ):
        """Should yield empty holdings for dates before any transactions."""
        account_id = account_with_transactions["account_id"]
        buy_date = account_with_transactions["buy_date"]

        # Query dates before the buy date
        early_start = buy_date - timedelta(days=5)
        early_end = buy_date - timedelta(days=1)

        results = list(
            PortfolioReconstructionService.reconstruct_holdings_timeline(
                db_session, account_id, early_start, early_end
            )
        )

        # Should yield 5 days, all with empty holdings
        assert len(results) == 5
        for _, holdings in results:
            assert holdings == []
