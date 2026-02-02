"""Tests for AccountRepository."""

from decimal import Decimal

import pytest
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Account, Asset, Holding, Portfolio, User, portfolio_accounts


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing.

    SQLite doesn't support JSONB, so we override the type compilation
    to use JSON instead for testing purposes.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Register JSONB as JSON for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        # Enable foreign keys
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Override JSONB to compile as JSON for SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    original_visit_json = SQLiteTypeCompiler.visit_JSON

    def visit_jsonb(self, type_, **kw):
        return original_visit_json(self, JSON(), **kw)

    SQLiteTypeCompiler.visit_JSONB = visit_jsonb

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine):
    """Create database session for testing."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        id="user-123",
        email="test@example.com",
        password_hash="hashed",
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_portfolio(db, test_user):
    """Create a test portfolio."""
    portfolio = Portfolio(
        id="portfolio-123",
        user_id=test_user.id,
        name="Test Portfolio",
        default_currency="USD",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_account(db, test_portfolio):
    """Create a test account linked to portfolio."""
    account = Account(
        name="Test Account",
        account_type="brokerage",
        currency="USD",
        is_active=True,
    )
    db.add(account)
    db.flush()

    # Link account to portfolio via association table
    db.execute(
        portfolio_accounts.insert().values(
            portfolio_id=test_portfolio.id,
            account_id=account.id,
        )
    )
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def inactive_account(db, test_portfolio):
    """Create an inactive test account."""
    account = Account(
        name="Inactive Account",
        account_type="brokerage",
        currency="USD",
        is_active=False,
    )
    db.add(account)
    db.flush()

    db.execute(
        portfolio_accounts.insert().values(
            portfolio_id=test_portfolio.id,
            account_id=account.id,
        )
    )
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_asset(db):
    """Create a test asset."""
    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        currency="USD",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@pytest.fixture
def test_holding(db, test_account, test_asset):
    """Create a test holding."""
    holding = Holding(
        account_id=test_account.id,
        asset_id=test_asset.id,
        quantity=Decimal("100"),
        cost_basis=Decimal("15000.00"),
        is_active=True,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


class TestAccountRepository:
    """Tests for AccountRepository."""

    def test_find_by_id_returns_account(self, db, test_account):
        """Test finding account by ID returns the correct account."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        account = repo.find_by_id(test_account.id)

        assert account is not None
        assert account.id == test_account.id
        assert account.name == "Test Account"

    def test_find_by_id_returns_none_for_nonexistent(self, db):
        """Test finding nonexistent account returns None."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        account = repo.find_by_id(99999)

        assert account is None

    def test_find_by_ids_returns_accounts(self, db, test_account):
        """Test finding multiple accounts by IDs."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_ids([test_account.id])

        assert len(accounts) == 1
        assert accounts[0].id == test_account.id

    def test_find_by_ids_returns_empty_for_no_matches(self, db):
        """Test finding accounts with no matching IDs returns empty list."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_ids([99999])

        assert len(accounts) == 0

    def test_find_active_by_ids_returns_only_active(self, db, test_account, inactive_account):
        """Test finding active accounts excludes inactive ones."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_active_by_ids([test_account.id, inactive_account.id])

        assert len(accounts) == 1
        assert accounts[0].id == test_account.id
        assert accounts[0].is_active is True

    def test_find_by_user_returns_accounts(self, db, test_user, test_account):
        """Test finding accounts by user ID."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_user(str(test_user.id))

        assert len(accounts) >= 1
        account_ids = [a.id for a in accounts]
        assert test_account.id in account_ids

    def test_find_by_user_returns_empty_for_unknown_user(self, db):
        """Test finding accounts for unknown user returns empty list."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_user("unknown-user-id")

        assert len(accounts) == 0

    def test_find_by_portfolio_returns_accounts(self, db, test_portfolio, test_account):
        """Test finding accounts by portfolio ID."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_portfolio(str(test_portfolio.id))

        assert len(accounts) >= 1
        account_ids = [a.id for a in accounts]
        assert test_account.id in account_ids

    def test_find_by_portfolio_returns_empty_for_unknown(self, db):
        """Test finding accounts for unknown portfolio returns empty list."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_by_portfolio("unknown-portfolio-id")

        assert len(accounts) == 0

    def test_find_with_holdings_eager_loads(self, db, test_account, test_holding):
        """Test finding accounts with holdings eagerly loaded."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_with_holdings([test_account.id])

        assert len(accounts) >= 1
        # Holdings should be loaded (no additional query needed)
        assert len(accounts[0].holdings) >= 1
        assert accounts[0].holdings[0].id == test_holding.id

    def test_find_with_holdings_empty_for_no_holdings(self, db, test_account):
        """Test finding accounts with no holdings returns empty holdings list."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_with_holdings([test_account.id])

        assert len(accounts) >= 1
        assert len(accounts[0].holdings) == 0

    def test_find_active_with_holdings_filters_inactive(
        self, db, test_account, inactive_account, test_holding
    ):
        """Test finding active accounts with holdings excludes inactive accounts."""
        from app.services.repositories.account_repository import AccountRepository

        repo = AccountRepository(db)
        accounts = repo.find_active_with_holdings([test_account.id, inactive_account.id])

        assert len(accounts) == 1
        assert accounts[0].id == test_account.id
        assert accounts[0].is_active is True
