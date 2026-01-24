"""Tests for ownership transfer during overlapping broker file imports.

These tests verify the latest-wins ownership transfer policy:
1. Upload a file for 2024
2. Upload an overlapping file for 2024-2025
3. Verify duplicate transactions have ownership transferred to new source
4. Verify import stats show transferred vs new counts
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, Holding, Transaction
from app.models.broker_data_source import BrokerDataSource
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.transaction_hash_service import (
    DedupResult,
    compute_transaction_hash,
    create_or_transfer_transaction,
)


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database."""
    import os

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
        conn.execute(text("DELETE FROM transactions WHERE 1=1"))
        conn.execute(text("DELETE FROM broker_data_sources WHERE 1=1"))
        conn.execute(text("DELETE FROM holdings WHERE 1=1"))
        conn.execute(text("DELETE FROM assets WHERE symbol LIKE 'TEST_%'"))
        conn.execute(text("DELETE FROM accounts WHERE name LIKE 'Test %'"))
        conn.execute(text("DELETE FROM portfolios WHERE name LIKE 'Test %'"))
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_transfer%'"))
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
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test_transfer@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_portfolio(db_session, test_user):
    """Create a test portfolio."""
    portfolio = Portfolio(user_id=test_user.id, name="Test Transfer Portfolio")
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_account(db_session, test_portfolio):
    """Create a test account."""
    account = Account(
        portfolio_id=test_portfolio.id,
        name="Test Kraken Transfer Account",
        account_type="Crypto",
        institution="Kraken",
        broker_type="kraken",
        currency="USD",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_asset(db_session):
    """Create a test asset."""
    asset = Asset(
        symbol="TEST_BTC",
        name="Test Bitcoin",
        asset_class="Crypto",
        currency="USD",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_holding(db_session, test_account, test_asset):
    """Create a test holding."""
    holding = Holding(
        account_id=test_account.id,
        asset_id=test_asset.id,
        quantity=Decimal("0"),
        cost_basis=Decimal("0"),
        is_active=False,
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)
    return holding


class TestOwnershipTransfer:
    """Test ownership transfer for overlapping imports."""

    def test_new_transaction_returns_new_result(self, db_session, test_holding):
        """A transaction with no matching hash should return NEW."""
        result, txn = create_or_transfer_transaction(
            db=db_session,
            holding_id=test_holding.id,
            source_id=None,
            txn_date=date(2024, 1, 15),
            txn_type="Buy",
            symbol="TEST_BTC",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )

        assert result == DedupResult.NEW
        assert txn is not None
        assert txn.quantity == Decimal("1.5")
        assert txn.content_hash is not None

    def test_duplicate_same_source_returns_skipped(self, db_session, test_holding, test_account):
        """A duplicate transaction with same source should return SKIPPED."""
        # Create a source
        source = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="file_upload",
            source_identifier="test_file_1.csv",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status="completed",
        )
        db_session.add(source)
        db_session.flush()

        # Create first transaction
        result1, txn1 = create_or_transfer_transaction(
            db=db_session,
            holding_id=test_holding.id,
            source_id=source.id,
            txn_date=date(2024, 1, 15),
            txn_type="Buy",
            symbol="TEST_BTC",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
            external_txn_id="KRAKEN-TXN-001",
        )
        assert result1 == DedupResult.NEW
        db_session.flush()

        # Try to create same transaction with same source
        result2, txn2 = create_or_transfer_transaction(
            db=db_session,
            holding_id=test_holding.id,
            source_id=source.id,
            txn_date=date(2024, 1, 15),
            txn_type="Buy",
            symbol="TEST_BTC",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
            external_txn_id="KRAKEN-TXN-001",
        )

        assert result2 == DedupResult.SKIPPED
        assert txn2.id == txn1.id  # Same transaction

    def test_duplicate_different_source_transfers_ownership(
        self, db_session, test_holding, test_account
    ):
        """A duplicate transaction with different source should transfer ownership."""
        # Create source 1
        source1 = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="file_upload",
            source_identifier="test_file_2024.csv",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status="completed",
        )
        db_session.add(source1)
        db_session.flush()

        # Create transaction with source 1
        result1, txn1 = create_or_transfer_transaction(
            db=db_session,
            holding_id=test_holding.id,
            source_id=source1.id,
            txn_date=date(2024, 6, 15),
            txn_type="Buy",
            symbol="TEST_BTC",
            quantity=Decimal("2.0"),
            price=Decimal("50000.00"),
            fees=Decimal("15.00"),
            external_txn_id="KRAKEN-TXN-002",
        )
        assert result1 == DedupResult.NEW
        assert txn1.broker_source_id == source1.id
        db_session.flush()

        # Create source 2 (overlapping file)
        source2 = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="file_upload",
            source_identifier="test_file_2024_2025.csv",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 6, 30),
            status="completed",
        )
        db_session.add(source2)
        db_session.flush()

        # Create same transaction with source 2
        result2, txn2 = create_or_transfer_transaction(
            db=db_session,
            holding_id=test_holding.id,
            source_id=source2.id,
            txn_date=date(2024, 6, 15),
            txn_type="Buy",
            symbol="TEST_BTC",
            quantity=Decimal("2.0"),
            price=Decimal("50000.00"),
            fees=Decimal("15.00"),
            external_txn_id="KRAKEN-TXN-002",
        )

        assert result2 == DedupResult.TRANSFERRED
        assert txn2.id == txn1.id  # Same transaction
        assert txn2.broker_source_id == source2.id  # Ownership transferred

    def test_content_hash_includes_external_id(self, db_session, test_holding):
        """Two transactions differing only in external ID should have different hashes."""
        hash1 = compute_transaction_hash(
            external_txn_id="TXN-001",
            txn_date=date(2024, 1, 15),
            symbol="TEST_BTC",
            txn_type="Buy",
            quantity=Decimal("1.0"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )

        hash2 = compute_transaction_hash(
            external_txn_id="TXN-002",
            txn_date=date(2024, 1, 15),
            symbol="TEST_BTC",
            txn_type="Buy",
            quantity=Decimal("1.0"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )

        assert hash1 != hash2

    def test_overlapping_import_scenario(self, db_session, test_holding, test_account):
        """Full scenario: upload 2024 file, then 2024-2025 file with overlapping data."""
        # Create 2024 source
        source_2024 = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="file_upload",
            source_identifier="kraken_2024.csv",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status="completed",
        )
        db_session.add(source_2024)
        db_session.flush()

        # Import transactions for 2024
        transactions_2024 = [
            ("KRAKEN-001", date(2024, 3, 15), Decimal("1.0"), Decimal("45000.00")),
            ("KRAKEN-002", date(2024, 6, 20), Decimal("0.5"), Decimal("60000.00")),
            ("KRAKEN-003", date(2024, 9, 10), Decimal("2.0"), Decimal("55000.00")),
        ]

        stats_2024 = {"new": 0, "transferred": 0, "skipped": 0}
        for ext_id, txn_date, qty, price in transactions_2024:
            result, _ = create_or_transfer_transaction(
                db=db_session,
                holding_id=test_holding.id,
                source_id=source_2024.id,
                txn_date=txn_date,
                txn_type="Buy",
                symbol="TEST_BTC",
                quantity=qty,
                price=price,
                fees=Decimal("10.00"),
                external_txn_id=ext_id,
            )
            if result == DedupResult.NEW:
                stats_2024["new"] += 1
            elif result == DedupResult.TRANSFERRED:
                stats_2024["transferred"] += 1
            else:
                stats_2024["skipped"] += 1

        db_session.flush()

        # Verify 2024 import
        assert stats_2024["new"] == 3
        assert stats_2024["transferred"] == 0
        assert stats_2024["skipped"] == 0

        # Create 2024-2025 overlapping source
        source_overlap = BrokerDataSource(
            account_id=test_account.id,
            broker_type="kraken",
            source_type="file_upload",
            source_identifier="kraken_2024_2025.csv",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 6, 30),
            status="completed",
        )
        db_session.add(source_overlap)
        db_session.flush()

        # Import overlapping + new transactions
        transactions_overlap = [
            # Overlapping with 2024 (should transfer)
            ("KRAKEN-001", date(2024, 3, 15), Decimal("1.0"), Decimal("45000.00")),
            ("KRAKEN-002", date(2024, 6, 20), Decimal("0.5"), Decimal("60000.00")),
            # New for 2025
            ("KRAKEN-004", date(2025, 1, 5), Decimal("1.5"), Decimal("90000.00")),
            ("KRAKEN-005", date(2025, 3, 20), Decimal("0.25"), Decimal("85000.00")),
        ]

        stats_overlap = {"new": 0, "transferred": 0, "skipped": 0}
        for ext_id, txn_date, qty, price in transactions_overlap:
            result, _ = create_or_transfer_transaction(
                db=db_session,
                holding_id=test_holding.id,
                source_id=source_overlap.id,
                txn_date=txn_date,
                txn_type="Buy",
                symbol="TEST_BTC",
                quantity=qty,
                price=price,
                fees=Decimal("10.00"),
                external_txn_id=ext_id,
            )
            if result == DedupResult.NEW:
                stats_overlap["new"] += 1
            elif result == DedupResult.TRANSFERRED:
                stats_overlap["transferred"] += 1
            else:
                stats_overlap["skipped"] += 1

        db_session.flush()

        # Verify overlap import stats
        assert stats_overlap["new"] == 2  # 2025 transactions
        assert stats_overlap["transferred"] == 2  # Overlapping 2024 transactions
        assert stats_overlap["skipped"] == 0

        # Verify final state - all 5 unique transactions exist
        all_txns = (
            db_session.query(Transaction).filter(Transaction.holding_id == test_holding.id).all()
        )
        assert len(all_txns) == 5  # 3 from 2024 + 2 new from overlap

        # Verify transferred transactions belong to new source
        transferred_txns = (
            db_session.query(Transaction)
            .filter(
                Transaction.holding_id == test_holding.id,
                Transaction.broker_source_id == source_overlap.id,
            )
            .all()
        )
        assert len(transferred_txns) == 4  # 2 transferred + 2 new

        # KRAKEN-003 should still belong to old source
        old_source_txns = (
            db_session.query(Transaction)
            .filter(
                Transaction.holding_id == test_holding.id,
                Transaction.broker_source_id == source_2024.id,
            )
            .all()
        )
        assert len(old_source_txns) == 1
        assert old_source_txns[0].external_transaction_id == "KRAKEN-003"
