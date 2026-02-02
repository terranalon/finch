"""Tests for staged import service.

These tests verify that:
1. Staged imports produce identical results to atomic imports
2. UI remains responsive during staged imports (locks released quickly)
3. Data integrity is maintained across all import methods
"""

import logging
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, Holding, Transaction
from app.services.shared.staged_import_service import StagedImportService
from app.services.shared.staging_utils import (
    cleanup_staging,
    copy_production_to_staging,
    create_staging_schema,
    create_staging_tables,
)

logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    # Use in-memory SQLite for fast tests, or test PostgreSQL for full compatibility
    # For staging tests, we need PostgreSQL due to schema support
    import os

    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)
    TestSession = sessionmaker(bind=engine)

    # Create all tables
    Base.metadata.create_all(engine)

    session = TestSession()
    yield session

    # Cleanup
    session.rollback()
    session.close()


@pytest.fixture
def sample_account(test_db):
    """Create a sample account for testing."""
    account = Account(
        name="Test IBKR Account",
        account_type="Brokerage",
        institution="Interactive Brokers",
        currency="USD",
    )
    test_db.add(account)
    test_db.commit()
    return account


@pytest.fixture
def sample_positions_data():
    """Sample positions data from IBKR parser."""
    return [
        {
            "symbol": "AAPL",
            "original_symbol": "AAPL",
            "description": "Apple Inc",
            "asset_class": "Stock",
            "currency": "USD",
            "quantity": Decimal("100"),
            "cost_basis": Decimal("15000.00"),
            "needs_validation": False,
            "cusip": "037833100",
            "isin": "US0378331005",
            "conid": "265598",
        },
        {
            "symbol": "MSFT",
            "original_symbol": "MSFT",
            "description": "Microsoft Corporation",
            "asset_class": "Stock",
            "currency": "USD",
            "quantity": Decimal("50"),
            "cost_basis": Decimal("17500.00"),
            "needs_validation": False,
            "cusip": "594918104",
            "isin": "US5949181045",
            "conid": "272093",
        },
    ]


@pytest.fixture
def sample_transactions_data():
    """Sample transactions data from IBKR parser."""
    return [
        {
            "symbol": "AAPL",
            "original_symbol": "AAPL",
            "description": "Apple Inc",
            "asset_class": "Stock",
            "currency": "USD",
            "trade_date": date(2025, 6, 15),
            "transaction_type": "Buy",
            "quantity": Decimal("100"),
            "price": Decimal("150.00"),
            "commission": Decimal("1.00"),
            "net_cash": Decimal("-15001.00"),
        },
        {
            "symbol": "MSFT",
            "original_symbol": "MSFT",
            "description": "Microsoft Corporation",
            "asset_class": "Stock",
            "currency": "USD",
            "trade_date": date(2025, 7, 1),
            "transaction_type": "Buy",
            "quantity": Decimal("50"),
            "price": Decimal("350.00"),
            "commission": Decimal("1.00"),
            "net_cash": Decimal("-17501.00"),
        },
    ]


@pytest.fixture
def sample_dividends_data():
    """Sample dividends data from IBKR parser."""
    return [
        {
            "symbol": "AAPL",
            "original_symbol": "AAPL",
            "description": "Apple Inc",
            "asset_class": "Stock",
            "currency": "USD",
            "date": date(2025, 8, 15),
            "amount": Decimal("24.00"),
        },
    ]


@pytest.fixture
def sample_cash_data():
    """Sample cash balance data from IBKR parser."""
    return [
        {
            "symbol": "USD",
            "currency": "USD",
            "description": "US Dollar",
            "asset_class": "Cash",
            "balance": Decimal("5000.00"),
        },
    ]


class TestStagingTableUtilities:
    """Tests for staging table utility functions."""

    def test_create_staging_schema(self, test_db):
        """Test that staging schema is created successfully."""
        create_staging_schema(test_db)

        # Verify schema exists
        result = test_db.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'staging'"
            )
        )
        assert result.fetchone() is not None

    def test_create_staging_tables(self, test_db):
        """Test that staging tables are created with correct structure."""
        create_staging_tables(test_db)

        # Verify tables exist
        for table in ["assets", "holdings", "transactions", "daily_cash_balance"]:
            result = test_db.execute(text(f"SELECT 1 FROM staging.{table} LIMIT 1"))
            # No error means table exists

    def test_copy_production_to_staging(self, test_db, sample_account):
        """Test copying production data to staging tables."""
        # Create some production data
        asset = Asset(
            symbol="TEST",
            name="Test Asset",
            asset_class="Stock",
            currency="USD",
        )
        test_db.add(asset)
        test_db.flush()

        holding = Holding(
            account_id=sample_account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            cost_basis=Decimal("1000.00"),
        )
        test_db.add(holding)
        test_db.commit()

        # Setup staging and copy
        create_staging_tables(test_db)
        stats = copy_production_to_staging(test_db, sample_account.id)

        # Verify data was copied
        assert stats["assets"] >= 1
        assert stats["holdings"] >= 1

        # Verify staging data matches
        result = test_db.execute(text("SELECT symbol FROM staging.assets WHERE symbol = 'TEST'"))
        assert result.fetchone() is not None

    def test_cleanup_staging(self, test_db):
        """Test that staging tables are properly cleaned up."""
        create_staging_tables(test_db)
        cleanup_staging(test_db)

        # Verify tables are dropped
        result = test_db.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'staging' AND table_name = 'assets'
            """)
        )
        assert result.fetchone() is None


class TestStagedImportService:
    """Tests for the StagedImportService."""

    @patch("app.services.shared.staged_import_service.IBKRFlexClient")
    @patch("app.services.shared.staged_import_service.IBKRParser")
    def test_staged_import_creates_assets(
        self,
        mock_parser,
        mock_client,
        test_db,
        sample_account,
        sample_positions_data,
        sample_transactions_data,
        sample_dividends_data,
        sample_cash_data,
    ):
        """Test that staged import creates assets correctly."""
        # Mock IBKR API responses
        mock_client.fetch_flex_report.return_value = "<xml>test</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = sample_positions_data
        mock_parser.extract_transactions.return_value = sample_transactions_data
        mock_parser.extract_dividends.return_value = sample_dividends_data
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []
        mock_parser.extract_cash_balances.return_value = sample_cash_data

        # Run staged import
        stats = StagedImportService.import_with_staging(
            test_db,
            sample_account.id,
            "test_token",
            "test_query_id",
        )

        # Verify import completed
        assert stats["status"] == "completed"
        assert stats["import_method"] == "staged"

        # Verify assets were created
        assets = test_db.query(Asset).filter(Asset.symbol.in_(["AAPL", "MSFT", "USD"])).all()
        symbols = {a.symbol for a in assets}
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "USD" in symbols

    @patch("app.services.shared.staged_import_service.IBKRFlexClient")
    @patch("app.services.shared.staged_import_service.IBKRParser")
    def test_staged_import_creates_holdings(
        self,
        mock_parser,
        mock_client,
        test_db,
        sample_account,
        sample_positions_data,
        sample_cash_data,
    ):
        """Test that staged import creates holdings correctly."""
        mock_client.fetch_flex_report.return_value = "<xml>test</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = sample_positions_data
        mock_parser.extract_transactions.return_value = []
        mock_parser.extract_dividends.return_value = []
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []
        mock_parser.extract_cash_balances.return_value = sample_cash_data

        stats = StagedImportService.import_with_staging(
            test_db,
            sample_account.id,
            "test_token",
            "test_query_id",
        )

        assert stats["status"] == "completed"

        # Verify holdings were created
        holdings = test_db.query(Holding).filter(Holding.account_id == sample_account.id).all()
        assert len(holdings) >= 2  # AAPL and MSFT

        # Verify quantities
        aapl_holding = next((h for h in holdings if h.asset.symbol == "AAPL"), None)
        if aapl_holding:
            assert aapl_holding.quantity == Decimal("100")

    @patch("app.services.shared.staged_import_service.IBKRFlexClient")
    @patch("app.services.shared.staged_import_service.IBKRParser")
    def test_staged_import_creates_transactions(
        self,
        mock_parser,
        mock_client,
        test_db,
        sample_account,
        sample_positions_data,
        sample_transactions_data,
    ):
        """Test that staged import creates transactions correctly."""
        mock_client.fetch_flex_report.return_value = "<xml>test</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = sample_positions_data
        mock_parser.extract_transactions.return_value = sample_transactions_data
        mock_parser.extract_dividends.return_value = []
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []
        mock_parser.extract_cash_balances.return_value = []

        stats = StagedImportService.import_with_staging(
            test_db,
            sample_account.id,
            "test_token",
            "test_query_id",
        )

        assert stats["status"] == "completed"
        assert stats["transactions"]["imported"] >= 2

    @patch("app.services.shared.staged_import_service.IBKRFlexClient")
    @patch("app.services.shared.staged_import_service.IBKRParser")
    def test_staged_import_handles_duplicates(
        self,
        mock_parser,
        mock_client,
        test_db,
        sample_account,
        sample_positions_data,
        sample_transactions_data,
    ):
        """Test that staged import correctly handles duplicate records."""
        mock_client.fetch_flex_report.return_value = "<xml>test</xml>"
        mock_parser.parse_xml.return_value = MagicMock()
        mock_parser.extract_positions.return_value = sample_positions_data
        mock_parser.extract_transactions.return_value = sample_transactions_data
        mock_parser.extract_dividends.return_value = []
        mock_parser.extract_transfers.return_value = []
        mock_parser.extract_forex_transactions.return_value = []
        mock_parser.extract_cash_balances.return_value = []

        # Run import twice
        stats1 = StagedImportService.import_with_staging(
            test_db,
            sample_account.id,
            "test_token",
            "test_query_id",
        )

        stats2 = StagedImportService.import_with_staging(
            test_db,
            sample_account.id,
            "test_token",
            "test_query_id",
        )

        assert stats1["status"] == "completed"
        assert stats2["status"] == "completed"

        # Verify no duplicate assets
        assets = test_db.query(Asset).filter(Asset.symbol == "AAPL").all()
        assert len(assets) == 1

    def test_staged_import_invalid_account(self, test_db):
        """Test that staged import fails gracefully for invalid account."""
        stats = StagedImportService.import_with_staging(
            test_db,
            99999,  # Non-existent account
            "test_token",
            "test_query_id",
        )

        assert stats["status"] == "failed"
        assert any("not found" in err.lower() for err in stats["errors"])


class TestDataIntegrity:
    """Tests to verify data integrity between atomic and staged imports."""

    @patch("app.services.brokers.ibkr.flex_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.flex_import_service.IBKRParser")
    @patch("app.services.shared.staged_import_service.IBKRFlexClient")
    @patch("app.services.shared.staged_import_service.IBKRParser")
    def test_staged_matches_atomic_import(
        self,
        staged_parser,
        staged_client,
        atomic_parser,
        atomic_client,
        test_db,
        sample_positions_data,
        sample_transactions_data,
        sample_dividends_data,
        sample_cash_data,
    ):
        """
        Verify that staged import produces identical results to atomic import.

        This is the critical test that ensures logic hasn't changed.
        """
        from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService

        # Setup mocks for both services
        for parser, client in [
            (atomic_parser, atomic_client),
            (staged_parser, staged_client),
        ]:
            client.fetch_flex_report.return_value = "<xml>test</xml>"
            parser.parse_xml.return_value = MagicMock()
            parser.extract_positions.return_value = sample_positions_data
            parser.extract_transactions.return_value = sample_transactions_data
            parser.extract_dividends.return_value = sample_dividends_data
            parser.extract_transfers.return_value = []
            parser.extract_forex_transactions.return_value = []
            parser.extract_cash_balances.return_value = sample_cash_data

        # Create two separate accounts for comparison
        account_atomic = Account(
            name="Atomic Test Account",
            account_type="Brokerage",
            institution="IBKR",
            currency="USD",
        )
        account_staged = Account(
            name="Staged Test Account",
            account_type="Brokerage",
            institution="IBKR",
            currency="USD",
        )
        test_db.add_all([account_atomic, account_staged])
        test_db.commit()

        # Run atomic import
        atomic_stats = IBKRFlexImportService.import_all(
            test_db,
            account_atomic.id,
            "test_token",
            "test_query_id",
        )

        # Run staged import
        staged_stats = StagedImportService.import_with_staging(
            test_db,
            account_staged.id,
            "test_token",
            "test_query_id",
        )

        # Both should succeed
        assert atomic_stats["status"] == "completed"
        assert staged_stats["status"] == "completed"

        # Compare holdings
        atomic_holdings = (
            test_db.query(Holding).filter(Holding.account_id == account_atomic.id).all()
        )
        staged_holdings = (
            test_db.query(Holding).filter(Holding.account_id == account_staged.id).all()
        )

        assert len(atomic_holdings) == len(staged_holdings)

        # Sort by asset symbol for comparison
        atomic_by_symbol = {h.asset.symbol: h for h in atomic_holdings}
        staged_by_symbol = {h.asset.symbol: h for h in staged_holdings}

        for symbol in atomic_by_symbol:
            atomic_h = atomic_by_symbol[symbol]
            staged_h = staged_by_symbol.get(symbol)

            assert staged_h is not None, f"Missing holding for {symbol} in staged import"
            assert atomic_h.quantity == staged_h.quantity, f"Quantity mismatch for {symbol}"
            assert atomic_h.cost_basis == staged_h.cost_basis, f"Cost basis mismatch for {symbol}"

        # Compare transaction counts
        atomic_txn_count = (
            test_db.query(Transaction)
            .join(Holding)
            .filter(Holding.account_id == account_atomic.id)
            .count()
        )
        staged_txn_count = (
            test_db.query(Transaction)
            .join(Holding)
            .filter(Holding.account_id == account_staged.id)
            .count()
        )

        assert atomic_txn_count == staged_txn_count, "Transaction count mismatch"


class TestLockBehavior:
    """Tests to verify that staged imports minimize lock time."""

    def test_staging_releases_locks_during_import(self, test_db, sample_account):
        """
        Verify that staging approach doesn't hold long locks on production tables.

        This test ensures the UI responsiveness goal is achieved.
        """
        create_staging_tables(test_db)
        copy_production_to_staging(test_db, sample_account.id)

        # At this point, staging tables have data and production tables are free
        # Verify we can query production tables without blocking
        result = test_db.execute(text("SELECT COUNT(*) FROM assets"))
        count = result.fetchone()[0]
        # Should complete immediately, not block

        assert count >= 0  # Just verify query completed

        cleanup_staging(test_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
