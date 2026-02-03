"""Integration test fixtures for API testing."""

import os
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Account, Asset, AssetPrice, Holding, Portfolio, User
from app.services.auth.auth_service import AuthService


@pytest.fixture(scope="session")
def engine():
    """Create test database engine.

    Note: We don't drop_all() at teardown because:
    1. Each test uses transaction rollback for isolation (data is already clean)
    2. Tables can persist between runs (create_all is idempotent)
    3. drop_all fails with foreign key dependencies unless using CASCADE
    """
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://portfolio_user:dev_password@localhost:5432/portfolio_tracker_test",
    )
    engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture
def db(engine):
    """Create a fresh database session for each test with cleanup."""
    connection = engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(bind=connection)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    """Create test client with database override."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=AuthService.hash_password("testpassword123"),
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authorization headers for test user."""
    token = AuthService.create_access_token(user_id=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(client, auth_headers):
    """Client with authentication headers."""
    client.headers.update(auth_headers)
    return client


@pytest.fixture
def test_portfolio(db, test_user):
    """Create a test portfolio."""
    portfolio = Portfolio(
        name="Test Portfolio",
        user_id=str(test_user.id),
        default_currency="USD",
        is_default=True,
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_account(db, test_user, test_portfolio):
    """Create a test account linked to portfolio."""
    account = Account(
        name="Test Account",
        account_type="brokerage",
        institution="Test Broker",
        currency="USD",
        is_active=True,
    )
    account.portfolios.append(test_portfolio)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_asset(db):
    """Create a test asset."""
    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_class="Equity",
        currency="USD",
        last_fetched_price=Decimal("150.00"),
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
        quantity=Decimal("10.0"),
        cost_basis=Decimal("1400.00"),
        is_active=True,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@pytest.fixture
def seed_holdings(db, test_account, test_asset, test_holding):
    """Seed database with holdings and historical price for positions testing."""
    yesterday = date.today() - timedelta(days=1)
    price = AssetPrice(
        asset_id=test_asset.id,
        date=yesterday,
        closing_price=Decimal("148.00"),
        currency="USD",
    )
    db.add(price)
    db.commit()
