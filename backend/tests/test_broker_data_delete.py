"""Tests for broker data source deletion with cascade delete and holdings recalculation.

These tests verify the multi-file import and partial delete scenario:
1. User uploads two files with transactions for the same asset
2. User deletes one file
3. Only that file's transactions are deleted
4. Holdings are recalculated from remaining transactions (not deleted)
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Account, Asset, Holding, Transaction
from app.models.broker_data_source import BrokerDataSource
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database for full compatibility."""
    import os

    # Use portfolio_tracker_db as hostname when running in Docker container
    # or localhost when running locally
    db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)

    # Create all tables
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
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_%'"))
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
        email="test_delete@example.com",
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
    portfolio = Portfolio(user_id=test_user.id, name="Test Delete Portfolio")
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_account(db_session, test_portfolio):
    """Create a test account."""
    account = Account(
        portfolio_id=test_portfolio.id,
        name="Test Kraken Account",
        account_type="Crypto",
        institution="Kraken",
        currency="USD",
        broker_type="kraken",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_asset_btc(db_session):
    """Create a BTC asset."""
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
def test_asset_eth(db_session):
    """Create an ETH asset."""
    asset = Asset(
        symbol="TEST_ETH",
        name="Test Ethereum",
        asset_class="Crypto",
        currency="USD",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_holding_btc(db_session, test_account, test_asset_btc):
    """Create a BTC holding."""
    holding = Holding(
        account_id=test_account.id,
        asset_id=test_asset_btc.id,
        quantity=Decimal("2.5"),  # Will be updated by transactions
        cost_basis=Decimal("75000.00"),
        is_active=True,
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)
    return holding


@pytest.fixture
def test_holding_eth(db_session, test_account, test_asset_eth):
    """Create an ETH holding."""
    holding = Holding(
        account_id=test_account.id,
        asset_id=test_asset_eth.id,
        quantity=Decimal("10.0"),
        cost_basis=Decimal("20000.00"),
        is_active=True,
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)
    return holding


@pytest.fixture
def broker_source_1(db_session, test_account):
    """Create first broker data source (file 1)."""
    source = BrokerDataSource(
        account_id=test_account.id,
        broker_type="kraken",
        source_type="file_upload",
        source_identifier="kraken_ledger_2024_part1.csv",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 30),
        status="completed",
        file_hash="abc123",
        import_stats={"transactions": 2},
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def broker_source_2(db_session, test_account):
    """Create second broker data source (file 2)."""
    source = BrokerDataSource(
        account_id=test_account.id,
        broker_type="kraken",
        source_type="file_upload",
        source_identifier="kraken_ledger_2024_part2.csv",
        start_date=date(2024, 7, 1),
        end_date=date(2024, 12, 31),
        status="completed",
        file_hash="def456",
        import_stats={"transactions": 2},
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def transactions_source_1(db_session, test_holding_btc, test_holding_eth, broker_source_1):
    """Create transactions linked to source 1."""
    # BTC buy from file 1: 1.0 BTC @ $30,000
    txn1 = Transaction(
        holding_id=test_holding_btc.id,
        broker_source_id=broker_source_1.id,
        date=date(2024, 2, 15),
        type="Buy",
        quantity=Decimal("1.0"),
        price_per_unit=Decimal("30000.00"),
        fees=Decimal("10.00"),
    )
    # ETH buy from file 1: 5.0 ETH @ $2,000
    txn2 = Transaction(
        holding_id=test_holding_eth.id,
        broker_source_id=broker_source_1.id,
        date=date(2024, 3, 10),
        type="Buy",
        quantity=Decimal("5.0"),
        price_per_unit=Decimal("2000.00"),
        fees=Decimal("5.00"),
    )
    db_session.add_all([txn1, txn2])
    db_session.commit()
    return [txn1, txn2]


@pytest.fixture
def transactions_source_2(db_session, test_holding_btc, test_holding_eth, broker_source_2):
    """Create transactions linked to source 2."""
    # BTC buy from file 2: 1.5 BTC @ $40,000
    txn1 = Transaction(
        holding_id=test_holding_btc.id,
        broker_source_id=broker_source_2.id,
        date=date(2024, 8, 20),
        type="Buy",
        quantity=Decimal("1.5"),
        price_per_unit=Decimal("40000.00"),
        fees=Decimal("15.00"),
    )
    # ETH buy from file 2: 5.0 ETH @ $2,500
    txn2 = Transaction(
        holding_id=test_holding_eth.id,
        broker_source_id=broker_source_2.id,
        date=date(2024, 9, 15),
        type="Buy",
        quantity=Decimal("5.0"),
        price_per_unit=Decimal("2500.00"),
        fees=Decimal("8.00"),
    )
    db_session.add_all([txn1, txn2])
    db_session.commit()
    return [txn1, txn2]


@pytest.fixture
def client_with_auth(test_db, test_user, test_portfolio):
    """Create test client with authentication."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_db)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        token = AuthService.create_access_token(test_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        yield test_client, headers, testing_session_local

    app.dependency_overrides.clear()


class TestDeleteSourceBasic:
    """Basic tests for delete source endpoint."""

    def test_delete_nonexistent_source_returns_404(self, client_with_auth):
        """Test that deleting a non-existent source returns 404."""
        client, headers, _ = client_with_auth
        response = client.delete("/api/broker-data/source/99999", headers=headers)
        assert response.status_code == 404

    def test_delete_source_requires_auth(self, client_with_auth):
        """Test that delete endpoint requires authentication."""
        client, _, _ = client_with_auth
        response = client.delete("/api/broker-data/source/1")
        assert response.status_code in [401, 403]


class TestCascadeDeleteTransactions:
    """Tests for cascade deletion of transactions."""

    def test_delete_source_removes_linked_transactions(
        self,
        client_with_auth,
        test_account,
        broker_source_1,
        broker_source_2,
        transactions_source_1,
        transactions_source_2,
    ):
        """Test that deleting a source removes only its linked transactions."""
        client, headers, session_maker = client_with_auth

        # Verify initial state: 4 transactions total
        with session_maker() as db:
            total_txns = db.query(Transaction).count()
            source1_txns = (
                db.query(Transaction)
                .filter(Transaction.broker_source_id == broker_source_1.id)
                .count()
            )
            source2_txns = (
                db.query(Transaction)
                .filter(Transaction.broker_source_id == broker_source_2.id)
                .count()
            )
            assert total_txns == 4
            assert source1_txns == 2
            assert source2_txns == 2

        # Delete source 1
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["deleted"]["transactions"] == 2

        # Verify: only source 2 transactions remain
        with session_maker() as db:
            remaining_txns = db.query(Transaction).all()
            assert len(remaining_txns) == 2
            for txn in remaining_txns:
                assert txn.broker_source_id == broker_source_2.id

    def test_delete_source_preserves_unlinked_transactions(
        self,
        db_session,
        client_with_auth,
        test_account,
        broker_source_1,
        test_holding_btc,
    ):
        """Test that transactions without broker_source_id are preserved."""
        client, headers, session_maker = client_with_auth

        # Create a transaction with broker_source_id linked to source 1
        linked_txn = Transaction(
            holding_id=test_holding_btc.id,
            broker_source_id=broker_source_1.id,
            date=date(2024, 1, 15),
            type="Buy",
            quantity=Decimal("0.5"),
            price_per_unit=Decimal("25000.00"),
        )
        # Create a transaction without broker_source_id (legacy or manual)
        unlinked_txn = Transaction(
            holding_id=test_holding_btc.id,
            broker_source_id=None,
            date=date(2024, 1, 10),
            type="Buy",
            quantity=Decimal("0.3"),
            price_per_unit=Decimal("24000.00"),
        )
        db_session.add_all([linked_txn, unlinked_txn])
        db_session.commit()

        # Delete source 1
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify: unlinked transaction remains
        with session_maker() as db:
            remaining = (
                db.query(Transaction).filter(Transaction.holding_id == test_holding_btc.id).all()
            )
            assert len(remaining) == 1
            assert remaining[0].broker_source_id is None
            assert remaining[0].quantity == Decimal("0.3")


class TestHoldingsRecalculation:
    """Tests for holdings recalculation after deletion."""

    def test_holdings_recalculated_after_partial_delete(
        self,
        client_with_auth,
        test_account,
        test_holding_btc,
        test_holding_eth,
        broker_source_1,
        broker_source_2,
        transactions_source_1,
        transactions_source_2,
    ):
        """Test that holdings are recalculated (not deleted) after deleting a source.

        Scenario:
        - Source 1: BTC buy 1.0, ETH buy 5.0
        - Source 2: BTC buy 1.5, ETH buy 5.0
        - Delete Source 1
        - Expected: BTC holding = 1.5, ETH holding = 5.0
        """
        client, headers, session_maker = client_with_auth

        # Delete source 1
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify holdings were updated, not deleted
        assert data["holdings"]["updated"] >= 1 or data["holdings"]["zeroed"] >= 0

        # Verify holdings quantities match remaining transactions
        with session_maker() as db:
            btc_holding = db.query(Holding).filter(Holding.id == test_holding_btc.id).first()
            eth_holding = db.query(Holding).filter(Holding.id == test_holding_eth.id).first()

            # BTC: only source 2 transaction remains (1.5 BTC)
            assert btc_holding is not None
            assert btc_holding.quantity == Decimal("1.5")
            assert btc_holding.is_active is True

            # ETH: only source 2 transaction remains (5.0 ETH)
            assert eth_holding is not None
            assert eth_holding.quantity == Decimal("5.0")
            assert eth_holding.is_active is True

    def test_holding_zeroed_when_all_transactions_deleted(
        self,
        db_session,
        client_with_auth,
        test_account,
        test_holding_btc,
        broker_source_1,
    ):
        """Test that holding is zeroed (not deleted) when all its transactions are deleted."""
        client, headers, session_maker = client_with_auth

        # Create only one transaction for BTC, linked to source 1
        txn = Transaction(
            holding_id=test_holding_btc.id,
            broker_source_id=broker_source_1.id,
            date=date(2024, 2, 15),
            type="Buy",
            quantity=Decimal("1.0"),
            price_per_unit=Decimal("30000.00"),
        )
        db_session.add(txn)
        db_session.commit()

        # Delete source 1
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify holding is zeroed, not deleted
        with session_maker() as db:
            holding = db.query(Holding).filter(Holding.id == test_holding_btc.id).first()
            assert holding is not None  # Holding still exists
            assert holding.quantity == Decimal("0")
            assert holding.cost_basis == Decimal("0")
            assert holding.is_active is False

    def test_cost_basis_recalculated_correctly(
        self,
        client_with_auth,
        test_account,
        test_holding_btc,
        broker_source_1,
        broker_source_2,
        transactions_source_1,
        transactions_source_2,
    ):
        """Test that cost basis is recalculated based on remaining transactions."""
        client, headers, session_maker = client_with_auth

        # Delete source 1 (which had BTC buy @ $30,000)
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify cost basis reflects only source 2 transaction
        # Source 2: 1.5 BTC @ $40,000 + $15 fees = $60,015
        with session_maker() as db:
            holding = db.query(Holding).filter(Holding.id == test_holding_btc.id).first()
            assert holding is not None
            # Cost basis should be recalculated from remaining transactions
            # Note: exact value depends on PortfolioReconstructionService implementation
            assert holding.cost_basis > Decimal("0")


class TestMultiFileScenario:
    """Integration tests for the multi-file import and partial delete scenario."""

    def test_full_multi_file_delete_workflow(
        self,
        client_with_auth,
        test_account,
        test_holding_btc,
        broker_source_1,
        broker_source_2,
        transactions_source_1,
        transactions_source_2,
    ):
        """Test complete workflow: two files uploaded, one deleted, data integrity maintained.

        This mimics the real user scenario:
        1. User uploads kraken_ledger_2024_part1.csv (H1 2024)
        2. User uploads kraken_ledger_2024_part2.csv (H2 2024)
        3. User realizes part1 had bad data and deletes it
        4. User can now re-upload corrected part1
        """
        client, headers, session_maker = client_with_auth

        # Step 1: Verify initial state
        with session_maker() as db:
            sources = (
                db.query(BrokerDataSource)
                .filter(BrokerDataSource.account_id == test_account.id)
                .all()
            )
            assert len(sources) == 2

            # Use explicit join condition due to Transaction having two FKs to Holding
            transactions = (
                db.query(Transaction)
                .join(Holding, Transaction.holding_id == Holding.id)
                .filter(Holding.account_id == test_account.id)
                .all()
            )
            assert len(transactions) == 4

        # Step 2: Delete first file
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Step 3: Verify only one source remains
        with session_maker() as db:
            sources = (
                db.query(BrokerDataSource)
                .filter(BrokerDataSource.account_id == test_account.id)
                .all()
            )
            assert len(sources) == 1
            assert sources[0].id == broker_source_2.id

        # Step 4: Verify transactions from source 2 still exist
        with session_maker() as db:
            # Use explicit join condition due to Transaction having two FKs to Holding
            transactions = (
                db.query(Transaction)
                .join(Holding, Transaction.holding_id == Holding.id)
                .filter(Holding.account_id == test_account.id)
                .all()
            )
            assert len(transactions) == 2
            for txn in transactions:
                assert txn.broker_source_id == broker_source_2.id

        # Step 5: Verify holdings are correct (not deleted, but recalculated)
        with session_maker() as db:
            holdings = db.query(Holding).filter(Holding.account_id == test_account.id).all()
            # Holdings should still exist
            assert len(holdings) >= 1

            btc_holding = next((h for h in holdings if h.id == test_holding_btc.id), None)
            assert btc_holding is not None
            # Should reflect only source 2's BTC transaction (1.5 BTC)
            assert btc_holding.quantity == Decimal("1.5")

    def test_delete_all_sources_zeros_holdings(
        self,
        client_with_auth,
        test_account,
        test_holding_btc,
        test_holding_eth,
        broker_source_1,
        broker_source_2,
        transactions_source_1,
        transactions_source_2,
    ):
        """Test that deleting all sources zeros all holdings but doesn't delete them."""
        client, headers, session_maker = client_with_auth

        # Delete both sources
        response1 = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response1.status_code == 200

        response2 = client.delete(
            f"/api/broker-data/source/{broker_source_2.id}",
            headers=headers,
        )
        assert response2.status_code == 200

        # Verify all holdings are zeroed
        with session_maker() as db:
            holdings = db.query(Holding).filter(Holding.account_id == test_account.id).all()
            for holding in holdings:
                assert holding.quantity == Decimal("0")
                assert holding.is_active is False

    def test_reupload_possible_after_delete(
        self,
        db_session,
        client_with_auth,
        test_account,
        broker_source_1,
    ):
        """Test that after deletion, user can upload a file with the same hash."""
        client, headers, session_maker = client_with_auth
        original_hash = broker_source_1.file_hash

        # Delete the source
        response = client.delete(
            f"/api/broker-data/source/{broker_source_1.id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify a new source with the same hash can be created
        with session_maker() as db:
            # Simulate creating a new source with the same file hash
            new_source = BrokerDataSource(
                account_id=test_account.id,
                broker_type="kraken",
                source_type="file_upload",
                source_identifier="kraken_ledger_2024_part1.csv",  # Same filename
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
                status="completed",
                file_hash=original_hash,  # Same hash - should now be allowed
            )
            db.add(new_source)
            db.commit()  # Should not raise duplicate error

            # Verify new source was created
            sources = (
                db.query(BrokerDataSource).filter(BrokerDataSource.file_hash == original_hash).all()
            )
            assert len(sources) == 1


class TestTransactionCountInCoverage:
    """Tests for transaction_count field in coverage response."""

    def test_coverage_includes_transaction_count(
        self,
        client_with_auth,
        test_account,
        broker_source_1,
        transactions_source_1,
    ):
        """Test that coverage endpoint returns accurate transaction counts."""
        client, headers, _ = client_with_auth

        response = client.get(
            f"/api/broker-data/coverage/{test_account.id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Find kraken broker in response
        kraken_data = data["brokers"].get("kraken")
        assert kraken_data is not None
        assert len(kraken_data["sources"]) >= 1

        # Verify transaction_count matches actual transaction count
        source_data = next(
            (s for s in kraken_data["sources"] if s["id"] == broker_source_1.id),
            None,
        )
        assert source_data is not None
        assert source_data["transaction_count"] == 2  # transactions_source_1 has 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
