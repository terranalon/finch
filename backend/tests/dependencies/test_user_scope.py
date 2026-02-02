"""Tests for user_scope authorization helpers with many-to-many relationships."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies.user_scope import get_user_account, get_user_account_ids
from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database."""
    db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)

    yield engine

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM portfolio_accounts"))
        conn.execute(text("DELETE FROM accounts"))
        conn.execute(text("DELETE FROM portfolios"))
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
    """Create a test user with portfolios."""
    user = User(
        email="test_user_scope@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_user_account_ids_with_shared_account(db_session, test_user):
    """Account in multiple portfolios should appear once in results."""
    portfolio1 = Portfolio(name="All", user_id=test_user.id)
    portfolio2 = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    # Force user.portfolios to be updated
    test_user.portfolios = [portfolio1, portfolio2]

    account = Account(
        name="Kraken",
        institution="Kraken",
        account_type="CryptoExchange",
        currency="USD",
    )
    account.portfolios = [portfolio1, portfolio2]
    db_session.add(account)
    db_session.commit()

    result = get_user_account_ids(test_user, db_session)

    # Should return account once, not twice
    assert len(result) == 1
    assert account.id in result


def test_get_user_account_ids_filtered_by_portfolio(db_session, test_user):
    """Filtering by portfolio_id should only return accounts in that portfolio."""
    portfolio1 = Portfolio(name="All", user_id=test_user.id)
    portfolio2 = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    test_user.portfolios = [portfolio1, portfolio2]

    account1 = Account(
        name="Kraken",
        institution="Kraken",
        account_type="CryptoExchange",
        currency="USD",
    )
    account1.portfolios = [portfolio1, portfolio2]

    account2 = Account(
        name="IBKR",
        institution="Interactive Brokers",
        account_type="Brokerage",
        currency="USD",
    )
    account2.portfolios = [portfolio1]  # Only in "All"

    db_session.add_all([account1, account2])
    db_session.commit()

    # Filter by Crypto - should only get Kraken
    result = get_user_account_ids(test_user, db_session, portfolio_id=portfolio2.id)
    assert result == [account1.id]


def test_get_user_account_service_account_bypass(db_session, test_user):
    """Service accounts should access any active account directly."""
    test_user.is_service_account = True
    db_session.commit()

    account = Account(
        name="Orphan",
        institution="Test",
        account_type="Brokerage",
        currency="USD",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()

    # Service account should access account without portfolio
    result = get_user_account(test_user, db_session, account.id)
    assert result is not None
    assert result.id == account.id
