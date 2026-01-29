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
