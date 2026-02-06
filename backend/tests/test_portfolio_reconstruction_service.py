"""Tests for PortfolioReconstructionService streaming reconstruction."""

import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, Holding, Portfolio, Transaction
from app.models.user import User
from app.services.auth import AuthService
from app.services.portfolio.portfolio_reconstruction_service import (
    PortfolioReconstructionService,
)


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


class TestBuildCorporateActionMergeMap:
    """Tests for _build_corporate_action_merge_map helper method."""

    def test_returns_empty_map_for_no_actions(self):
        """Should return empty dict when no corporate actions provided."""
        result = PortfolioReconstructionService._build_corporate_action_merge_map(
            [], date(2024, 1, 1)
        )
        assert result == {}

    def test_filters_actions_by_effective_date(self):
        """Should only include actions on or before as_of_date."""
        action_before = MagicMock()
        action_before.effective_date = date(2024, 1, 1)
        action_before.old_asset_id = 100
        action_before.new_asset_id = 200

        action_after = MagicMock()
        action_after.effective_date = date(2024, 6, 1)
        action_after.old_asset_id = 300
        action_after.new_asset_id = 400

        result = PortfolioReconstructionService._build_corporate_action_merge_map(
            [action_before, action_after], date(2024, 3, 1)
        )

        assert result == {100: 200}
        assert 300 not in result

    def test_excludes_actions_without_new_asset(self):
        """Should skip corporate actions where new_asset_id is None."""
        action_with_new = MagicMock()
        action_with_new.effective_date = date(2024, 1, 1)
        action_with_new.old_asset_id = 100
        action_with_new.new_asset_id = 200

        action_without_new = MagicMock()
        action_without_new.effective_date = date(2024, 1, 1)
        action_without_new.old_asset_id = 300
        action_without_new.new_asset_id = None

        result = PortfolioReconstructionService._build_corporate_action_merge_map(
            [action_with_new, action_without_new], date(2024, 3, 1)
        )

        assert result == {100: 200}

    def test_builds_correct_mapping(self):
        """Should build old_asset_id -> new_asset_id mapping."""
        actions = []
        for old_id, new_id in [(1, 10), (2, 20), (3, 30)]:
            action = MagicMock()
            action.effective_date = date(2024, 1, 1)
            action.old_asset_id = old_id
            action.new_asset_id = new_id
            actions.append(action)

        result = PortfolioReconstructionService._build_corporate_action_merge_map(
            actions, date(2024, 12, 31)
        )

        assert result == {1: 10, 2: 20, 3: 30}


class TestAccumulateHolding:
    """Tests for _accumulate_holding helper method."""

    def test_adds_new_holding_to_empty_dict(self):
        """Should add holding when asset_id not present."""
        merged_holdings = {}
        holding = {
            "asset_id": 100,
            "quantity": Decimal("10"),
            "cost_basis": Decimal("1000"),
            "symbol": "AAPL",
        }

        PortfolioReconstructionService._accumulate_holding(merged_holdings, 100, holding)

        assert 100 in merged_holdings
        assert merged_holdings[100]["quantity"] == Decimal("10")
        assert merged_holdings[100]["cost_basis"] == Decimal("1000")

    def test_accumulates_into_existing_holding(self):
        """Should add quantities and cost_basis when asset_id already present."""
        merged_holdings = {
            100: {
                "asset_id": 100,
                "quantity": Decimal("10"),
                "cost_basis": Decimal("1000"),
                "symbol": "AAPL",
            }
        }
        holding = {
            "asset_id": 100,
            "quantity": Decimal("5"),
            "cost_basis": Decimal("600"),
            "symbol": "AAPL",
        }

        PortfolioReconstructionService._accumulate_holding(merged_holdings, 100, holding)

        assert merged_holdings[100]["quantity"] == Decimal("15")
        assert merged_holdings[100]["cost_basis"] == Decimal("1600")

    def test_creates_copy_when_adding_new(self):
        """Should create a copy to avoid mutating original holding."""
        merged_holdings = {}
        holding = {
            "asset_id": 100,
            "quantity": Decimal("10"),
            "cost_basis": Decimal("1000"),
        }

        PortfolioReconstructionService._accumulate_holding(merged_holdings, 100, holding)

        # Modify original
        holding["quantity"] = Decimal("99")

        # Should not affect merged_holdings
        assert merged_holdings[100]["quantity"] == Decimal("10")


class TestApplyCorporateActionsToSnapshot:
    """Tests for _apply_corporate_actions_to_snapshot method."""

    def test_returns_unchanged_snapshot_when_no_applicable_actions(self):
        """Should return original snapshot when no corporate actions apply."""
        mock_db = MagicMock()
        snapshot = [
            {
                "asset_id": 100,
                "symbol": "AAPL",
                "name": "Apple",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("10"),
                "cost_basis": Decimal("1000"),
            }
        ]

        # No corporate actions
        result = PortfolioReconstructionService._apply_corporate_actions_to_snapshot(
            mock_db, snapshot, [], date(2024, 3, 1)
        )

        assert len(result) == 1
        assert result[0]["asset_id"] == 100
        assert result[0]["quantity"] == Decimal("10")

    def test_merges_old_asset_into_new_asset(self):
        """Should merge holding from old asset into new asset."""
        # Mock the database
        mock_db = MagicMock()
        mock_new_asset = MagicMock()
        mock_new_asset.symbol = "XXI"
        mock_new_asset.name = "New Corp"
        mock_new_asset.asset_class = "Stock"
        mock_new_asset.currency = "USD"
        mock_db.query.return_value.get.return_value = mock_new_asset

        # Create mock corporate action
        action = MagicMock()
        action.old_asset_id = 100
        action.new_asset_id = 200
        action.effective_date = date(2024, 2, 1)

        snapshot = [
            {
                "asset_id": 100,
                "symbol": "CEP",
                "name": "Old Corp",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("5000"),
            }
        ]

        result = PortfolioReconstructionService._apply_corporate_actions_to_snapshot(
            mock_db, snapshot, [action], date(2024, 3, 1)
        )

        # Should have single holding under new asset
        assert len(result) == 1
        assert result[0]["asset_id"] == 200
        assert result[0]["symbol"] == "XXI"
        assert result[0]["quantity"] == Decimal("100")
        assert result[0]["cost_basis"] == Decimal("5000")

    def test_accumulates_when_both_old_and_new_exist(self):
        """Should combine quantities when snapshot has both old and new asset."""
        mock_db = MagicMock()
        mock_new_asset = MagicMock()
        mock_new_asset.symbol = "NEW"
        mock_new_asset.name = "New Corp"
        mock_new_asset.asset_class = "Stock"
        mock_new_asset.currency = "USD"
        mock_db.query.return_value.get.return_value = mock_new_asset

        action = MagicMock()
        action.old_asset_id = 100
        action.new_asset_id = 200
        action.effective_date = date(2024, 2, 1)

        snapshot = [
            {
                "asset_id": 100,
                "symbol": "OLD",
                "name": "Old Corp",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("50"),
                "cost_basis": Decimal("2500"),
            },
            {
                "asset_id": 200,
                "symbol": "NEW",
                "name": "New Corp",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("30"),
                "cost_basis": Decimal("1500"),
            },
        ]

        result = PortfolioReconstructionService._apply_corporate_actions_to_snapshot(
            mock_db, snapshot, [action], date(2024, 3, 1)
        )

        # Should have single holding with combined values
        assert len(result) == 1
        assert result[0]["asset_id"] == 200
        assert result[0]["quantity"] == Decimal("80")  # 50 + 30
        assert result[0]["cost_basis"] == Decimal("4000")  # 2500 + 1500

    def test_skips_future_corporate_actions(self):
        """Should not apply corporate actions with future effective dates."""
        mock_db = MagicMock()

        # Action in the future
        action = MagicMock()
        action.old_asset_id = 100
        action.new_asset_id = 200
        action.effective_date = date(2024, 12, 1)  # Future date

        snapshot = [
            {
                "asset_id": 100,
                "symbol": "OLD",
                "name": "Old Corp",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("5000"),
            }
        ]

        # Reconstruct as of date before the action
        result = PortfolioReconstructionService._apply_corporate_actions_to_snapshot(
            mock_db, snapshot, [action], date(2024, 6, 1)
        )

        # Should still be under old asset (action not yet effective)
        assert len(result) == 1
        assert result[0]["asset_id"] == 100
        assert result[0]["symbol"] == "OLD"

    def test_preserves_unaffected_holdings(self):
        """Should preserve holdings not affected by corporate actions."""
        mock_db = MagicMock()
        mock_new_asset = MagicMock()
        mock_new_asset.symbol = "XXI"
        mock_new_asset.name = "New Corp"
        mock_new_asset.asset_class = "Stock"
        mock_new_asset.currency = "USD"
        mock_db.query.return_value.get.return_value = mock_new_asset

        # Action only affects asset 100
        action = MagicMock()
        action.old_asset_id = 100
        action.new_asset_id = 200
        action.effective_date = date(2024, 2, 1)

        snapshot = [
            {
                "asset_id": 100,
                "symbol": "CEP",
                "name": "Old Corp",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("50"),
                "cost_basis": Decimal("2500"),
            },
            {
                "asset_id": 300,  # Unaffected
                "symbol": "AAPL",
                "name": "Apple",
                "asset_class": "Stock",
                "currency": "USD",
                "quantity": Decimal("10"),
                "cost_basis": Decimal("1500"),
            },
        ]

        result = PortfolioReconstructionService._apply_corporate_actions_to_snapshot(
            mock_db, snapshot, [action], date(2024, 3, 1)
        )

        # Should have 2 holdings: merged (200) and unaffected (300)
        assert len(result) == 2
        result_by_id = {h["asset_id"]: h for h in result}
        assert 200 in result_by_id
        assert 300 in result_by_id
        assert result_by_id[300]["quantity"] == Decimal("10")
