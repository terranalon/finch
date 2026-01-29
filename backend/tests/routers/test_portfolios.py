"""Tests for portfolios router with many-to-many relationships."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.auth_service import AuthService


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
        conn.execute(text("DELETE FROM sessions"))
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
        email="test_portfolios_router@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    test_session_maker = sessionmaker(bind=test_db)

    def override_get_db():
        db = test_session_maker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user."""
    response = client.post(
        "/api/auth/login",
        json={"email": "test_portfolios_router@example.com", "password": "test123"},
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_portfolios_shows_account_count(client, auth_headers, test_user, db_session):
    """GET /portfolios shows correct account count using relationship."""
    portfolio = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.flush()

    account = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account.portfolios = [portfolio]
    db_session.add(account)
    db_session.commit()

    response = client.get("/api/portfolios", headers=auth_headers)

    assert response.status_code == 200
    portfolios = response.json()
    crypto_portfolio = next(p for p in portfolios if p["name"] == "Crypto")
    assert crypto_portfolio["account_count"] == 1


def test_link_account_to_portfolio(client, auth_headers, test_user, db_session):
    """POST /portfolios/{id}/accounts/{account_id}/link links existing account."""
    portfolio1 = Portfolio(name="Crypto", user_id=test_user.id)
    portfolio2 = Portfolio(name="All", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    account = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account.portfolios = [portfolio1]
    db_session.add(account)
    db_session.commit()

    response = client.post(
        f"/api/portfolios/{portfolio2.id}/accounts/{account.id}/link", headers=auth_headers
    )

    assert response.status_code == 200

    # Verify account is now in both portfolios
    db_session.refresh(account)
    portfolio_ids = [p.id for p in account.portfolios]
    assert portfolio1.id in portfolio_ids
    assert portfolio2.id in portfolio_ids


def test_link_account_already_linked(client, auth_headers, test_user, db_session):
    """POST /portfolios/{id}/accounts/{account_id}/link returns 400 if already linked."""
    portfolio = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.flush()

    account = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account.portfolios = [portfolio]
    db_session.add(account)
    db_session.commit()

    response = client.post(
        f"/api/portfolios/{portfolio.id}/accounts/{account.id}/link", headers=auth_headers
    )

    assert response.status_code == 400
    assert "already linked" in response.json()["detail"].lower()


def test_unlink_account_from_portfolio(client, auth_headers, test_user, db_session):
    """DELETE /portfolios/{id}/accounts/{account_id}/unlink removes link."""
    portfolio1 = Portfolio(name="Crypto", user_id=test_user.id)
    portfolio2 = Portfolio(name="All", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    account = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account.portfolios = [portfolio1, portfolio2]
    db_session.add(account)
    db_session.commit()

    response = client.delete(
        f"/api/portfolios/{portfolio2.id}/accounts/{account.id}/unlink", headers=auth_headers
    )

    assert response.status_code == 200

    # Verify account is now only in portfolio1
    db_session.refresh(account)
    portfolio_ids = [p.id for p in account.portfolios]
    assert portfolio1.id in portfolio_ids
    assert portfolio2.id not in portfolio_ids


def test_unlink_account_blocked_if_last_portfolio(client, auth_headers, test_user, db_session):
    """DELETE /portfolios/{id}/accounts/{account_id}/unlink blocked if only portfolio."""
    portfolio = Portfolio(name="Crypto", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.flush()

    account = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account.portfolios = [portfolio]
    db_session.add(account)
    db_session.commit()

    response = client.delete(
        f"/api/portfolios/{portfolio.id}/accounts/{account.id}/unlink", headers=auth_headers
    )

    assert response.status_code == 400
    assert "only portfolio" in response.json()["detail"].lower()


def test_get_linkable_accounts(client, auth_headers, test_user, db_session):
    """GET /portfolios/{id}/linkable-accounts returns accounts not in this portfolio."""
    portfolio1 = Portfolio(name="Crypto", user_id=test_user.id)
    portfolio2 = Portfolio(name="Stocks", user_id=test_user.id)
    db_session.add_all([portfolio1, portfolio2])
    db_session.flush()

    account1 = Account(
        name="Kraken", institution="Kraken", account_type="CryptoExchange", currency="USD"
    )
    account1.portfolios = [portfolio1]

    account2 = Account(
        name="IBKR", institution="Interactive Brokers", account_type="Brokerage", currency="USD"
    )
    account2.portfolios = [portfolio2]

    db_session.add_all([account1, account2])
    db_session.commit()

    response = client.get(
        f"/api/portfolios/{portfolio1.id}/linkable-accounts", headers=auth_headers
    )

    assert response.status_code == 200
    account_ids = [a["id"] for a in response.json()]

    # Kraken is already in Crypto, so only IBKR should be linkable
    assert account2.id in account_ids
    assert account1.id not in account_ids
