# Backend API Structure Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the backend API to follow clean architecture with proper separation of concerns, typed response schemas, standardized pagination, and comprehensive test coverage.

**Architecture:** 4-layer architecture (Router -> Service -> Repository -> Model). Routers handle HTTP only (~50 lines max), services contain business logic, repositories handle data access with semantic naming (`find_*`, `get_*`, `create_*`), models define SQLAlchemy ORM.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest, PostgreSQL

---

## Phase 0: Integration Tests (Safety Net)

Write integration tests BEFORE refactoring to ensure we don't break existing behavior.

---

### Task 0.1: Set Up Integration Test Infrastructure

**Files:**
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/conftest.py`

**Step 1: Create integration test directory**

```bash
mkdir -p backend/tests/integration
touch backend/tests/integration/__init__.py
```

**Step 2: Write test fixtures**

```python
# backend/tests/integration/conftest.py
"""Integration test fixtures for API testing."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import User, Account, Portfolio, Asset, Holding, AssetPrice
from app.services.auth.auth_service import AuthService


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    # Use test database URL from environment or default
    import os
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/portfolio_tracker_test"
    )
    engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(engine):
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=AuthService.hash_password("testpassword123"),
        is_active=True,
        is_verified=True,
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
    """Seed database with holdings for testing positions endpoint."""
    # Add asset price for day change calculation
    from datetime import date, timedelta

    yesterday = date.today() - timedelta(days=1)
    price = AssetPrice(
        asset_id=test_asset.id,
        date=yesterday,
        closing_price=Decimal("148.00"),
    )
    db.add(price)
    db.commit()

    return {"holdings": [test_holding], "assets": [test_asset]}
```

**Step 3: Verify fixtures work**

Run: `pytest backend/tests/integration/conftest.py --collect-only`
Expected: No import errors

**Step 4: Commit**

```bash
git add backend/tests/integration/
git commit -m "test: add integration test infrastructure and fixtures"
```

---

### Task 0.2: Write Positions API Integration Tests

**Files:**
- Create: `backend/tests/integration/test_positions_api.py`

**Step 1: Write the failing tests**

```python
# backend/tests/integration/test_positions_api.py
"""Integration tests for positions API endpoint."""

import pytest
from decimal import Decimal


class TestPositionsAPI:
    """Test /api/positions endpoint."""

    def test_list_positions_requires_auth(self, client):
        """Positions endpoint requires authentication."""
        response = client.get("/api/positions")
        assert response.status_code == 401

    def test_list_positions_returns_empty_for_new_user(self, auth_client):
        """Returns empty list when user has no holdings."""
        response = auth_client.get("/api/positions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_positions_returns_aggregated_holdings(
        self, auth_client, seed_holdings
    ):
        """Returns holdings aggregated by asset."""
        response = auth_client.get("/api/positions")
        assert response.status_code == 200

        positions = response.json()
        assert len(positions) >= 1

        # Check required fields
        position = positions[0]
        assert "asset_id" in position
        assert "symbol" in position
        assert "total_quantity" in position
        assert "total_cost_basis" in position
        assert "total_market_value" in position
        assert "accounts" in position

        # Verify aggregation
        assert position["symbol"] == "AAPL"
        assert position["total_quantity"] == 10.0

    def test_list_positions_includes_pnl_calculations(
        self, auth_client, seed_holdings
    ):
        """Positions include P&L calculations."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        # P&L should be calculated (current price 150 * 10 qty - 1400 cost = 100)
        assert position["total_pnl"] is not None
        assert position["total_pnl_pct"] is not None

    def test_list_positions_includes_day_change(
        self, auth_client, seed_holdings
    ):
        """Positions include day change from previous close."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        # Day change should be calculated (150 current - 148 previous = 2)
        assert "day_change" in position
        assert "day_change_pct" in position

    def test_list_positions_filters_by_portfolio(
        self, auth_client, test_portfolio, seed_holdings
    ):
        """Can filter positions by portfolio ID."""
        response = auth_client.get(
            f"/api/positions?portfolio_id={test_portfolio.id}"
        )
        assert response.status_code == 200
        positions = response.json()
        assert len(positions) >= 1

    def test_list_positions_converts_currency(
        self, auth_client, seed_holdings, db
    ):
        """Can convert positions to different display currency."""
        # Add exchange rate for ILS
        from app.models import ExchangeRate
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="ILS",
            rate=Decimal("3.70"),
        )
        db.add(rate)
        db.commit()

        response = auth_client.get("/api/positions?display_currency=ILS")
        assert response.status_code == 200
        positions = response.json()

        if positions:
            # Values should be converted
            assert positions[0].get("display_currency") == "ILS"

    def test_list_positions_includes_account_breakdown(
        self, auth_client, seed_holdings
    ):
        """Each position includes breakdown by account."""
        response = auth_client.get("/api/positions")
        positions = response.json()
        position = positions[0]

        assert "accounts" in position
        assert len(position["accounts"]) >= 1

        account = position["accounts"][0]
        assert "account_id" in account
        assert "account_name" in account
        assert "quantity" in account
        assert "cost_basis" in account
```

**Step 2: Run tests**

Run: `pytest backend/tests/integration/test_positions_api.py -v`
Expected: Tests pass (we're testing existing behavior)

**Step 3: Commit**

```bash
git add backend/tests/integration/test_positions_api.py
git commit -m "test: add integration tests for positions API"
```

---

### Task 0.3: Write Dashboard API Integration Tests

**Files:**
- Create: `backend/tests/integration/test_dashboard_api.py`

**Step 1: Write the tests**

```python
# backend/tests/integration/test_dashboard_api.py
"""Integration tests for dashboard API endpoint."""

import pytest


class TestDashboardAPI:
    """Test /api/dashboard endpoints."""

    def test_dashboard_summary_requires_auth(self, client):
        """Dashboard endpoint requires authentication."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 401

    def test_dashboard_summary_returns_structure(self, auth_client):
        """Returns expected dashboard structure."""
        response = auth_client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = response.json()
        assert "total_value" in data
        assert "display_currency" in data
        assert "accounts" in data
        assert "asset_allocation" in data
        assert "top_holdings" in data
        assert "historical_performance" in data

    def test_dashboard_summary_with_holdings(
        self, auth_client, seed_holdings
    ):
        """Dashboard shows correct totals with holdings."""
        response = auth_client.get("/api/dashboard/summary")
        data = response.json()

        # Should have positive total value
        assert data["total_value"] > 0

        # Should have accounts
        assert len(data["accounts"]) >= 1

        # Should have asset allocation
        assert len(data["asset_allocation"]) >= 1

    def test_dashboard_summary_filters_by_portfolio(
        self, auth_client, test_portfolio, seed_holdings
    ):
        """Can filter dashboard by portfolio."""
        response = auth_client.get(
            f"/api/dashboard/summary?portfolio_id={test_portfolio.id}"
        )
        assert response.status_code == 200

    def test_dashboard_summary_converts_currency(
        self, auth_client, seed_holdings
    ):
        """Can convert dashboard values to different currency."""
        response = auth_client.get("/api/dashboard/summary?display_currency=ILS")
        assert response.status_code == 200
        data = response.json()
        assert data["display_currency"] == "ILS"

    def test_benchmark_returns_data(self, auth_client):
        """Benchmark endpoint returns historical data."""
        response = auth_client.get("/api/dashboard/benchmark?symbol=SPY&period=1mo")
        assert response.status_code == 200

        data = response.json()
        assert "symbol" in data
        assert "data" in data
```

**Step 2: Run tests**

Run: `pytest backend/tests/integration/test_dashboard_api.py -v`
Expected: Tests pass

**Step 3: Commit**

```bash
git add backend/tests/integration/test_dashboard_api.py
git commit -m "test: add integration tests for dashboard API"
```

---

### Task 0.4: Write Auth API Integration Tests

**Files:**
- Create: `backend/tests/integration/test_auth_api.py`

**Step 1: Write the tests**

```python
# backend/tests/integration/test_auth_api.py
"""Integration tests for auth API endpoints.

These are critical for Airflow DAG authentication.
"""

import pytest


class TestAuthAPI:
    """Test /api/auth endpoints."""

    def test_login_with_valid_credentials(self, client, test_user):
        """Login returns tokens with valid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_password(self, client, test_user):
        """Login fails with invalid password."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_with_nonexistent_user(self, client):
        """Login fails with nonexistent user."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "password"},
        )
        assert response.status_code == 401

    def test_access_token_grants_access(self, client, test_user):
        """Access token can be used to access protected endpoints."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/portfolios",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_refresh_token_flow(self, client, test_user):
        """Can refresh access token using refresh token."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
```

**Step 2: Run tests**

Run: `pytest backend/tests/integration/test_auth_api.py -v`
Expected: Tests pass

**Step 3: Commit**

```bash
git add backend/tests/integration/test_auth_api.py
git commit -m "test: add integration tests for auth API (critical for Airflow)"
```

---

## Phase 1: Common Schemas and Response Standards

---

### Task 1.1: Create Common Response Schemas

**Files:**
- Create: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/__init__.py`

**Step 1: Write the common schemas**

```python
# backend/app/schemas/common.py
"""Common response schemas used across the API."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: list[T]
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether more items exist")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: str | None = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str = Field(..., description="Error code (e.g., 'NotFound', 'ValidationError')")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: str | None = Field(None, description="Request path that caused the error")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
```

**Step 2: Export from schemas package**

```python
# backend/app/schemas/__init__.py
# Add to existing imports:
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
)

__all__ = [
    # ... existing exports ...
    "ErrorDetail",
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
]
```

**Step 3: Write tests for schemas**

```python
# backend/tests/unit/test_common_schemas.py
"""Tests for common response schemas."""

import pytest
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import PaginatedResponse, ErrorResponse


class ItemSchema(BaseModel):
    id: int
    name: str


class TestPaginatedResponse:
    def test_paginated_response_structure(self):
        items = [ItemSchema(id=1, name="test")]
        response = PaginatedResponse[ItemSchema](
            items=items,
            total=100,
            skip=0,
            limit=10,
            has_more=True,
        )
        assert response.items == items
        assert response.total == 100
        assert response.has_more is True

    def test_paginated_response_serialization(self):
        response = PaginatedResponse[ItemSchema](
            items=[ItemSchema(id=1, name="test")],
            total=1,
            skip=0,
            limit=10,
            has_more=False,
        )
        data = response.model_dump()
        assert "items" in data
        assert "total" in data
        assert "has_more" in data


class TestErrorResponse:
    def test_error_response_structure(self):
        error = ErrorResponse(
            error="NotFound",
            message="User not found",
            path="/api/users/123",
        )
        assert error.error == "NotFound"
        assert isinstance(error.timestamp, datetime)
```

**Step 4: Run tests**

Run: `pytest backend/tests/unit/test_common_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/schemas/common.py backend/app/schemas/__init__.py backend/tests/unit/test_common_schemas.py
git commit -m "feat: add common response schemas (PaginatedResponse, ErrorResponse)"
```

---

### Task 1.2: Create Position Response Schemas

**Files:**
- Create: `backend/app/schemas/position.py`
- Modify: `backend/app/schemas/__init__.py`

**Step 1: Write the position schemas**

```python
# backend/app/schemas/position.py
"""Position response schemas."""

from pydantic import BaseModel, Field


class PositionAccountDetail(BaseModel):
    """Account-level breakdown within a position."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None = None
    institution: str | None = None
    quantity: float
    cost_basis_native: float = Field(..., description="Cost basis in asset's native currency")
    market_value_native: float | None = Field(None, description="Market value in native currency")
    pnl_native: float | None = Field(None, description="P&L in native currency")
    cost_basis: float = Field(..., description="Cost basis in USD")
    market_value: float | None = Field(None, description="Market value in USD")
    pnl: float | None = Field(None, description="P&L in USD")
    pnl_pct: float | None = Field(None, description="P&L percentage")
    strategy_horizon: str | None = None


class PositionResponse(BaseModel):
    """Aggregated position for an asset across accounts."""

    asset_id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    category: str | None = None
    industry: str | None = None
    currency: str = "USD"
    is_favorite: bool = False

    # Price data
    current_price: float | None = None
    current_price_display: float | None = Field(None, description="Current price in display currency")
    previous_close_price: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    day_change_date: str | None = None
    is_market_closed: bool = False

    # Aggregated values (native currency)
    total_quantity: float
    total_cost_basis_native: float
    total_market_value_native: float | None = None
    total_pnl_native: float | None = None
    avg_cost_per_unit_native: float = 0

    # Aggregated values (display currency, usually USD)
    total_cost_basis: float
    total_market_value: float | None = None
    current_value: float | None = Field(None, description="Alias for total_market_value")
    total_pnl: float | None = None
    total_pnl_pct: float | None = None
    avg_cost_per_unit: float = 0

    display_currency: str = "USD"
    account_count: int = 0
    accounts: list[PositionAccountDetail] = []
```

**Step 2: Export from schemas package**

Add to `backend/app/schemas/__init__.py`:
```python
from app.schemas.position import PositionAccountDetail, PositionResponse

__all__ = [
    # ... existing ...
    "PositionAccountDetail",
    "PositionResponse",
]
```

**Step 3: Write schema tests**

```python
# backend/tests/unit/test_position_schemas.py
"""Tests for position schemas."""

from app.schemas.position import PositionResponse, PositionAccountDetail


class TestPositionSchemas:
    def test_position_response_minimal(self):
        """Position with minimal required fields."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
        )
        assert position.symbol == "AAPL"
        assert position.total_quantity == 10.0

    def test_position_response_full(self):
        """Position with all fields."""
        account = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=10.0,
            cost_basis_native=1400.0,
            cost_basis=1400.0,
        )
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Equity",
            currency="USD",
            current_price=150.0,
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_market_value_native=1500.0,
            total_pnl_native=100.0,
            total_cost_basis=1400.0,
            total_market_value=1500.0,
            total_pnl=100.0,
            total_pnl_pct=7.14,
            accounts=[account],
            account_count=1,
        )
        assert len(position.accounts) == 1
        assert position.total_pnl == 100.0
```

**Step 4: Run tests**

Run: `pytest backend/tests/unit/test_position_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/schemas/position.py backend/app/schemas/__init__.py backend/tests/unit/test_position_schemas.py
git commit -m "feat: add position response schemas"
```

---

## Phase 2: Repository Layer

---

### Task 2.1: Create UserRepository

**Files:**
- Create: `backend/app/services/repositories/user_repository.py`
- Modify: `backend/app/services/repositories/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/repositories/test_user_repository.py
"""Tests for UserRepository."""

import pytest
from app.services.repositories.user_repository import UserRepository
from app.models import User


class TestUserRepository:
    def test_find_by_id_returns_user(self, db, test_user):
        repo = UserRepository(db)
        user = repo.find_by_id(test_user.id)
        assert user is not None
        assert user.id == test_user.id

    def test_find_by_id_returns_none_for_missing(self, db):
        repo = UserRepository(db)
        user = repo.find_by_id(99999)
        assert user is None

    def test_find_by_email_returns_user(self, db, test_user):
        repo = UserRepository(db)
        user = repo.find_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    def test_find_by_email_returns_none_for_missing(self, db):
        repo = UserRepository(db)
        user = repo.find_by_email("nonexistent@example.com")
        assert user is None

    def test_find_by_email_is_case_insensitive(self, db, test_user):
        repo = UserRepository(db)
        user = repo.find_by_email("TEST@EXAMPLE.COM")
        assert user is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/repositories/test_user_repository.py -v`
Expected: FAIL (import error - module doesn't exist)

**Step 3: Write the implementation**

```python
# backend/app/services/repositories/user_repository.py
"""User data access layer."""

import logging
from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Centralized user data access.

    Naming conventions:
    - find_* : Query that may return None
    - get_* : Query that raises exception if missing
    - create_* : Insert new record
    - update_* : Modify existing record
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, user_id: int) -> User | None:
        """Find user by primary key."""
        return self._db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> User | None:
        """Find user by email (case-insensitive)."""
        return self._db.query(User).filter(User.email.ilike(email)).first()

    def find_active_by_id(self, user_id: int) -> User | None:
        """Find active user by ID."""
        return (
            self._db.query(User)
            .filter(User.id == user_id, User.is_active.is_(True))
            .first()
        )

    def find_verified_by_email(self, email: str) -> User | None:
        """Find verified user by email."""
        return (
            self._db.query(User)
            .filter(
                User.email.ilike(email),
                User.is_active.is_(True),
                User.is_verified.is_(True),
            )
            .first()
        )
```

**Step 4: Export from repositories package**

```python
# backend/app/services/repositories/__init__.py
from app.services.repositories.asset_repository import AssetRepository
from app.services.repositories.holding_repository import HoldingRepository
from app.services.repositories.user_repository import UserRepository

__all__ = ["AssetRepository", "HoldingRepository", "UserRepository"]
```

**Step 5: Run tests**

Run: `pytest backend/tests/unit/repositories/test_user_repository.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/repositories/user_repository.py backend/app/services/repositories/__init__.py backend/tests/unit/repositories/
git commit -m "feat: add UserRepository for user data access"
```

---

### Task 2.2: Create AccountRepository

**Files:**
- Create: `backend/app/services/repositories/account_repository.py`
- Modify: `backend/app/services/repositories/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/repositories/test_account_repository.py
"""Tests for AccountRepository."""

import pytest
from app.services.repositories.account_repository import AccountRepository


class TestAccountRepository:
    def test_find_by_id_returns_account(self, db, test_account):
        repo = AccountRepository(db)
        account = repo.find_by_id(test_account.id)
        assert account is not None
        assert account.id == test_account.id

    def test_find_by_user_returns_accounts(self, db, test_user, test_account):
        repo = AccountRepository(db)
        accounts = repo.find_by_user(test_user.id)
        assert len(accounts) >= 1

    def test_find_active_by_ids_returns_only_active(self, db, test_account):
        repo = AccountRepository(db)
        accounts = repo.find_active_by_ids([test_account.id])
        assert len(accounts) == 1
        assert accounts[0].is_active is True

    def test_find_with_holdings_eager_loads(self, db, test_account, test_holding):
        repo = AccountRepository(db)
        accounts = repo.find_with_holdings([test_account.id])
        assert len(accounts) >= 1
        # Holdings should be loaded
        assert len(accounts[0].holdings) >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/repositories/test_account_repository.py -v`
Expected: FAIL (import error)

**Step 3: Write the implementation**

```python
# backend/app/services/repositories/account_repository.py
"""Account data access layer."""

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from app.models import Account, Portfolio

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class AccountRepository:
    """Centralized account data access.

    Naming conventions:
    - find_* : Query that may return None or empty list
    - get_* : Query that raises exception if missing
    - create_* : Insert new record
    - update_* : Modify existing record
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, account_id: int) -> Account | None:
        """Find account by primary key."""
        return self._db.query(Account).filter(Account.id == account_id).first()

    def find_by_ids(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find multiple accounts by IDs."""
        return self._db.query(Account).filter(Account.id.in_(account_ids)).all()

    def find_active_by_ids(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find active accounts by IDs."""
        return (
            self._db.query(Account)
            .filter(Account.id.in_(account_ids), Account.is_active.is_(True))
            .all()
        )

    def find_by_user(self, user_id: str) -> "Sequence[Account]":
        """Find all accounts belonging to a user (via portfolios)."""
        return (
            self._db.query(Account)
            .join(Account.portfolios)
            .filter(Portfolio.user_id == user_id)
            .distinct()
            .all()
        )

    def find_by_portfolio(self, portfolio_id: str) -> "Sequence[Account]":
        """Find accounts in a specific portfolio."""
        return (
            self._db.query(Account)
            .join(Account.portfolios)
            .filter(Portfolio.id == portfolio_id)
            .all()
        )

    def find_with_holdings(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find accounts with holdings eagerly loaded."""
        return (
            self._db.query(Account)
            .options(joinedload(Account.holdings))
            .filter(Account.id.in_(account_ids))
            .all()
        )

    def find_active_with_holdings(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find active accounts with active holdings eagerly loaded."""
        from app.models import Holding

        return (
            self._db.query(Account)
            .options(
                joinedload(Account.holdings.and_(Holding.is_active.is_(True)))
            )
            .filter(Account.id.in_(account_ids), Account.is_active.is_(True))
            .all()
        )
```

**Step 4: Export from repositories package**

Add to `backend/app/services/repositories/__init__.py`:
```python
from app.services.repositories.account_repository import AccountRepository

__all__ = ["AssetRepository", "HoldingRepository", "UserRepository", "AccountRepository"]
```

**Step 5: Run tests**

Run: `pytest backend/tests/unit/repositories/test_account_repository.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/repositories/account_repository.py backend/app/services/repositories/__init__.py backend/tests/unit/repositories/
git commit -m "feat: add AccountRepository for account data access"
```

---

### Task 2.3: Create PriceRepository

**Files:**
- Create: `backend/app/services/repositories/price_repository.py`
- Modify: `backend/app/services/repositories/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/repositories/test_price_repository.py
"""Tests for PriceRepository."""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.services.repositories.price_repository import PriceRepository
from app.models import AssetPrice


class TestPriceRepository:
    def test_find_latest_by_asset(self, db, test_asset):
        # Create price
        price = AssetPrice(
            asset_id=test_asset.id,
            date=date.today(),
            closing_price=Decimal("150.00"),
        )
        db.add(price)
        db.commit()

        repo = PriceRepository(db)
        latest = repo.find_latest_by_asset(test_asset.id)
        assert latest is not None
        assert latest.closing_price == Decimal("150.00")

    def test_find_latest_by_assets(self, db, test_asset):
        price = AssetPrice(
            asset_id=test_asset.id,
            date=date.today(),
            closing_price=Decimal("150.00"),
        )
        db.add(price)
        db.commit()

        repo = PriceRepository(db)
        prices = repo.find_latest_by_assets([test_asset.id], limit_per_asset=2)
        assert test_asset.id in prices
        assert len(prices[test_asset.id]) >= 1

    def test_find_previous_close(self, db, test_asset):
        yesterday = date.today() - timedelta(days=1)
        price = AssetPrice(
            asset_id=test_asset.id,
            date=yesterday,
            closing_price=Decimal("148.00"),
        )
        db.add(price)
        db.commit()

        repo = PriceRepository(db)
        prev_prices = repo.find_previous_close([test_asset.id], date.today())
        assert test_asset.id in prev_prices
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/repositories/test_price_repository.py -v`
Expected: FAIL (import error)

**Step 3: Write the implementation**

```python
# backend/app/services/repositories/price_repository.py
"""Price data access layer."""

import logging
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import AssetPrice

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class PriceRepository:
    """Centralized price data access."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_latest_by_asset(self, asset_id: int) -> AssetPrice | None:
        """Find most recent price for an asset."""
        return (
            self._db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id)
            .order_by(desc(AssetPrice.date))
            .first()
        )

    def find_latest_by_assets(
        self, asset_ids: list[int], limit_per_asset: int = 2
    ) -> dict[int, list[AssetPrice]]:
        """Find most recent N prices for multiple assets.

        Returns:
            Dict mapping asset_id to list of prices (most recent first).
        """
        result: dict[int, list[AssetPrice]] = {}

        for asset_id in asset_ids:
            prices = (
                self._db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset_id)
                .order_by(desc(AssetPrice.date))
                .limit(limit_per_asset)
                .all()
            )
            if prices:
                result[asset_id] = prices

        return result

    def find_previous_close(
        self, asset_ids: list[int], before_date: date
    ) -> dict[int, AssetPrice]:
        """Find the most recent closing price before a given date.

        Used for day change calculations (compare current vs previous close).
        """
        # Subquery to get max date before target date for each asset
        max_date_subquery = (
            self._db.query(
                AssetPrice.asset_id,
                func.max(AssetPrice.date).label("max_date"),
            )
            .filter(
                AssetPrice.asset_id.in_(asset_ids),
                AssetPrice.date < before_date,
            )
            .group_by(AssetPrice.asset_id)
            .subquery()
        )

        # Join to get the actual price records
        prices = (
            self._db.query(AssetPrice)
            .join(
                max_date_subquery,
                (AssetPrice.asset_id == max_date_subquery.c.asset_id)
                & (AssetPrice.date == max_date_subquery.c.max_date),
            )
            .all()
        )

        return {price.asset_id: price for price in prices}

    def find_by_date_range(
        self, asset_id: int, start_date: date, end_date: date
    ) -> "Sequence[AssetPrice]":
        """Find prices for an asset within a date range."""
        return (
            self._db.query(AssetPrice)
            .filter(
                AssetPrice.asset_id == asset_id,
                AssetPrice.date >= start_date,
                AssetPrice.date <= end_date,
            )
            .order_by(AssetPrice.date)
            .all()
        )
```

**Step 4: Export from repositories package**

Add to `backend/app/services/repositories/__init__.py`:
```python
from app.services.repositories.price_repository import PriceRepository

__all__ = [
    "AssetRepository",
    "HoldingRepository",
    "UserRepository",
    "AccountRepository",
    "PriceRepository",
]
```

**Step 5: Run tests**

Run: `pytest backend/tests/unit/repositories/test_price_repository.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/repositories/price_repository.py backend/app/services/repositories/__init__.py backend/tests/unit/repositories/
git commit -m "feat: add PriceRepository for price data access"
```

---

## Phase 3: Valuation Service

---

### Task 3.1: Create PortfolioValuationService

**Files:**
- Create: `backend/app/services/portfolio/valuation_service.py`
- Create: `backend/app/services/portfolio/valuation_types.py`

**Step 1: Write the type definitions**

```python
# backend/app/services/portfolio/valuation_types.py
"""Value objects for portfolio valuation."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class HoldingValue:
    """Calculated values for a single holding."""

    holding_id: int
    account_id: int
    account_name: str
    account_type: str | None
    institution: str | None
    quantity: Decimal

    # Native currency values
    cost_basis_native: Decimal
    market_value_native: Decimal | None
    pnl_native: Decimal | None
    pnl_pct: Decimal | None

    # USD values
    cost_basis_usd: Decimal
    market_value_usd: Decimal | None
    pnl_usd: Decimal | None

    strategy_horizon: str | None = None


@dataclass
class DayChangeResult:
    """Day change calculation result."""

    day_change: Decimal | None
    day_change_pct: Decimal | None
    previous_close_price: Decimal | None
    day_change_date: str | None
    is_market_closed: bool


@dataclass
class PositionSummary:
    """Aggregated position across accounts."""

    asset_id: int
    symbol: str
    name: str | None
    asset_class: str | None
    category: str | None
    industry: str | None
    currency: str
    is_favorite: bool
    current_price: Decimal | None

    # Aggregated values
    total_quantity: Decimal
    total_cost_basis_native: Decimal
    total_cost_basis_usd: Decimal
    total_market_value_native: Decimal | None
    total_market_value_usd: Decimal | None
    total_pnl_native: Decimal | None
    total_pnl_usd: Decimal | None
    total_pnl_pct: Decimal | None

    # Day change
    day_change: DayChangeResult | None

    # Account breakdown
    holdings: list[HoldingValue]
```

**Step 2: Write the failing test**

```python
# backend/tests/unit/services/test_valuation_service.py
"""Tests for PortfolioValuationService."""

import pytest
from decimal import Decimal

from app.services.portfolio.valuation_service import PortfolioValuationService
from app.services.portfolio.valuation_types import HoldingValue


class TestValuationService:
    def test_calculate_holding_value_equity(self, db, test_holding, test_asset, test_account):
        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(test_holding, test_asset, test_account)

        assert value.quantity == Decimal("10.0")
        assert value.cost_basis_native == Decimal("1400.00")
        # Market value = 10 * 150 = 1500
        assert value.market_value_native == Decimal("1500.00")
        # P&L = 1500 - 1400 = 100
        assert value.pnl_native == Decimal("100.00")

    def test_calculate_holding_value_cash(self, db, test_account):
        """Cash holdings have value equal to quantity."""
        from app.models import Asset, Holding

        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class="Cash",
            currency="USD",
        )
        db.add(cash_asset)
        db.flush()

        cash_holding = Holding(
            account_id=test_account.id,
            asset_id=cash_asset.id,
            quantity=Decimal("1000.00"),
            cost_basis=Decimal("1000.00"),
            is_active=True,
        )
        db.add(cash_holding)
        db.commit()

        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(cash_holding, cash_asset, test_account)

        # Cash value = quantity
        assert value.market_value_native == Decimal("1000.00")

    def test_aggregate_positions(self, db, seed_holdings):
        service = PortfolioValuationService(db)
        # This would need the full holdings data
        # Simplified test for now
        assert service is not None
```

**Step 3: Run test to verify it fails**

Run: `pytest backend/tests/unit/services/test_valuation_service.py -v`
Expected: FAIL (import error)

**Step 4: Write the implementation**

```python
# backend/app/services/portfolio/valuation_service.py
"""Portfolio valuation service - single source of truth for value calculations."""

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import Account, Asset, Holding
from app.services.portfolio.valuation_types import (
    DayChangeResult,
    HoldingValue,
    PositionSummary,
)
from app.services.shared.currency_service import CurrencyService

if TYPE_CHECKING:
    from app.services.repositories.price_repository import PriceRepository

logger = logging.getLogger(__name__)


class PortfolioValuationService:
    """Calculates portfolio values, P&L, and day changes.

    This service centralizes all valuation logic that was previously
    duplicated across positions.py and dashboard.py.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._price_repo: "PriceRepository | None" = None

    @property
    def price_repo(self) -> "PriceRepository":
        """Lazy-load price repository to avoid circular imports."""
        if self._price_repo is None:
            from app.services.repositories.price_repository import PriceRepository
            self._price_repo = PriceRepository(self._db)
        return self._price_repo

    def calculate_holding_value(
        self,
        holding: Holding,
        asset: Asset,
        account: Account,
        to_currency: str = "USD",
    ) -> HoldingValue:
        """Calculate value for a single holding.

        Args:
            holding: The holding to value
            asset: The asset (must be pre-loaded)
            account: The account (must be pre-loaded)
            to_currency: Target currency for conversion (default: USD)

        Returns:
            HoldingValue with all calculated fields
        """
        asset_currency = asset.currency or "USD"

        # Calculate native currency values
        if asset.asset_class == "Cash":
            current_price = Decimal("1")
            market_value_native = holding.quantity
        else:
            current_price = asset.last_fetched_price or Decimal("0")
            market_value_native = (
                holding.quantity * current_price if current_price else None
            )

        cost_basis_native = holding.cost_basis

        # Calculate P&L in native currency
        if market_value_native is not None:
            pnl_native = market_value_native - cost_basis_native
            pnl_pct = (
                (pnl_native / cost_basis_native * 100)
                if cost_basis_native > 0
                else None
            )
        else:
            pnl_native = None
            pnl_pct = None

        # Convert to target currency (usually USD)
        if asset_currency != to_currency:
            rate = CurrencyService.get_exchange_rate(
                self._db, asset_currency, to_currency
            )
            if rate:
                cost_basis_converted = cost_basis_native * rate
                market_value_converted = (
                    market_value_native * rate if market_value_native else None
                )
            else:
                cost_basis_converted = cost_basis_native
                market_value_converted = market_value_native
        else:
            cost_basis_converted = cost_basis_native
            market_value_converted = market_value_native

        pnl_converted = (
            (market_value_converted - cost_basis_converted)
            if market_value_converted is not None
            else None
        )

        return HoldingValue(
            holding_id=holding.id,
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            institution=account.institution,
            quantity=holding.quantity,
            cost_basis_native=cost_basis_native,
            market_value_native=market_value_native,
            pnl_native=pnl_native,
            pnl_pct=pnl_pct,
            cost_basis_usd=cost_basis_converted,
            market_value_usd=market_value_converted,
            pnl_usd=pnl_converted,
            strategy_horizon=holding.strategy_horizon,
        )

    def calculate_day_change(
        self,
        asset: Asset,
        current_price: Decimal | None,
        today: date | None = None,
    ) -> DayChangeResult:
        """Calculate day change for an asset.

        Args:
            asset: The asset
            current_price: Current price (or latest close if market closed)
            today: Date to calculate from (default: today)

        Returns:
            DayChangeResult with day change values
        """
        from app.services.portfolio.trading_calendar_service import TradingCalendarService

        if today is None:
            today = date.today()

        # Cash has no day change
        if asset.asset_class == "Cash":
            return DayChangeResult(
                day_change=None,
                day_change_pct=None,
                previous_close_price=None,
                day_change_date=None,
                is_market_closed=False,
            )

        # Determine market status
        if asset.asset_class == "Crypto":
            is_market_closed = False
        else:
            market = TradingCalendarService.get_market_for_symbol(asset.symbol)
            is_market_closed = TradingCalendarService.is_market_closed(today, market)

        # Get price data
        prices = self.price_repo.find_latest_by_assets([asset.id], limit_per_asset=2)
        asset_prices = prices.get(asset.id, [])

        if is_market_closed:
            # Compare two most recent closes
            if len(asset_prices) >= 2:
                price_for_change = asset_prices[0].closing_price
                previous_close = asset_prices[1].closing_price
                change_date = asset_prices[0].date
            elif len(asset_prices) == 1:
                price_for_change = asset_prices[0].closing_price
                previous_close = None
                change_date = asset_prices[0].date
            else:
                return DayChangeResult(
                    day_change=None,
                    day_change_pct=None,
                    previous_close_price=None,
                    day_change_date=None,
                    is_market_closed=True,
                )
        else:
            # Market open: compare current vs previous close
            price_for_change = current_price
            prev_prices = self.price_repo.find_previous_close([asset.id], today)
            previous_close = (
                prev_prices[asset.id].closing_price
                if asset.id in prev_prices
                else None
            )
            change_date = today

        # Calculate change
        if previous_close and price_for_change:
            day_change = price_for_change - previous_close
            day_change_pct = (day_change / previous_close) * 100
        else:
            day_change = None
            day_change_pct = None

        return DayChangeResult(
            day_change=day_change,
            day_change_pct=day_change_pct,
            previous_close_price=previous_close,
            day_change_date=str(change_date) if change_date else None,
            is_market_closed=is_market_closed,
        )
```

**Step 5: Run tests**

Run: `pytest backend/tests/unit/services/test_valuation_service.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/portfolio/valuation_service.py backend/app/services/portfolio/valuation_types.py backend/tests/unit/services/
git commit -m "feat: add PortfolioValuationService for centralized valuation logic"
```

---

## Phase 4: Refactor Routers to Use Services

---

### Task 4.1: Update Auth Dependency to Use UserRepository

**Files:**
- Modify: `backend/app/dependencies/auth.py`

**Step 1: Find current usage**

```bash
grep -n "db.query(User)" backend/app/dependencies/auth.py
```

**Step 2: Update the implementation**

```python
# In backend/app/dependencies/auth.py
# Replace:
#   user = db.query(User).filter(User.id == user_id).first()
# With:
from app.services.repositories.user_repository import UserRepository

def get_current_user(...) -> User:
    # ... token validation ...

    user_repo = UserRepository(db)
    user = user_repo.find_by_id(user_id)

    if user is None:
        raise HTTPException(...)

    return user
```

**Step 3: Run integration tests to verify**

Run: `pytest backend/tests/integration/test_auth_api.py -v`
Expected: PASS (no behavior change)

**Step 4: Run code-simplifier agent**

Use the code-simplifier agent on `backend/app/dependencies/auth.py`

**Step 5: Commit**

```bash
git add backend/app/dependencies/auth.py
git commit -m "refactor: use UserRepository in auth dependency"
```

---

### Task 4.2: Refactor Positions Router (Part 1 - Extract Calculation)

**Files:**
- Modify: `backend/app/routers/positions.py`

This is a large refactor. Break into substeps:

**Step 1: Add service import and typed response**

At the top of `positions.py`, add:
```python
from app.schemas.position import PositionResponse
from app.services.portfolio.valuation_service import PortfolioValuationService
```

**Step 2: Change response type**

```python
@router.get("", response_model=list[PositionResponse])
async def list_positions(...) -> list[PositionResponse]:
```

**Step 3: Run integration tests**

Run: `pytest backend/tests/integration/test_positions_api.py -v`
Expected: May fail due to schema differences - fix as needed

**Step 4: Incrementally extract calculation logic**

Replace the inline P&L calculation loop with service calls:
```python
valuation_service = PortfolioValuationService(db)

for holding, account, asset in holdings_query:
    value = valuation_service.calculate_holding_value(holding, asset, account)
    # Use value instead of inline calculation
```

**Step 5: Run tests after each change**

Run: `pytest backend/tests/integration/test_positions_api.py -v`
Expected: PASS

**Step 6: Run code-simplifier agent**

**Step 7: Commit**

```bash
git add backend/app/routers/positions.py
git commit -m "refactor: use PortfolioValuationService in positions router"
```

---

### Task 4.3: Add Pagination to Accounts Endpoint

**Files:**
- Modify: `backend/app/routers/accounts.py`

**Step 1: Write the test**

```python
# Add to backend/tests/integration/test_accounts_api.py
def test_list_accounts_pagination(self, auth_client, test_account):
    response = auth_client.get("/api/accounts?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()

    # Should have pagination metadata
    assert "items" in data
    assert "total" in data
    assert "has_more" in data
```

**Step 2: Update the router**

```python
from app.schemas.common import PaginatedResponse
from app.schemas import Account as AccountSchema

@router.get("", response_model=PaginatedResponse[AccountSchema])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    ...
):
    # Get total count
    total = query.count()

    # Get paginated items
    accounts = query.offset(skip).limit(limit).all()

    return PaginatedResponse(
        items=[AccountSchema.model_validate(a) for a in accounts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(accounts)) < total,
    )
```

**Step 3: Run tests**

Run: `pytest backend/tests/integration/test_accounts_api.py -v`

**Step 4: Commit**

```bash
git add backend/app/routers/accounts.py backend/tests/integration/
git commit -m "feat: add pagination metadata to accounts endpoint"
```

---

### Task 4.4: Fix DELETE Response Consistency

**Files:**
- Modify: `backend/app/routers/portfolios.py`

**Step 1: Find inconsistent DELETE**

```bash
grep -n "def delete_portfolio" backend/app/routers/portfolios.py
```

**Step 2: Update to return 204**

```python
@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(...) -> None:
    # ... deletion logic ...
    return None  # 204 No Content
```

**Step 3: Update any tests expecting JSON response**

**Step 4: Run tests**

Run: `pytest backend/tests/ -k "delete_portfolio" -v`

**Step 5: Commit**

```bash
git add backend/app/routers/portfolios.py
git commit -m "fix: standardize DELETE response to 204 No Content"
```

---

## Phase 5: Validation and Cleanup

---

### Task 5.1: Verify All Consumers Updated

**Step 1: Search for direct model queries that should use repos**

```bash
grep -rn "db.query(User)" backend/app/routers/ backend/app/dependencies/
grep -rn "db.query(Account)" backend/app/routers/
```

**Step 2: Update any remaining direct queries**

**Step 3: Run full test suite**

Run: `pytest backend/tests/ -v`
Expected: All pass

---

### Task 5.2: Verify Airflow DAGs Still Work

**Step 1: Check DAG imports**

```bash
cd airflow
python -c "from dags.auth_helper import get_auth_helper; print('Auth helper OK')"
python -c "from dags.hourly_broker_import import dag_instance; print('Broker import DAG OK')"
```

**Step 2: Test auth flow**

```bash
# Start backend
docker compose up -d

# Test login (what Airflow uses)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

**Step 3: Verify endpoints Airflow calls**

- `POST /api/auth/login` - Auth
- `POST /api/prices/update` - Price refresh
- `POST /api/snapshots/create` - Snapshots
- `POST /api/brokers/*/import/*` - Broker imports

---

### Task 5.3: Run Code Simplifier on All Modified Files

For each modified file, run the code-simplifier agent to clean up.

**Files to simplify:**
- `backend/app/routers/positions.py`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/accounts.py`
- `backend/app/dependencies/auth.py`

---

### Task 5.4: Final Verification

**Step 1: Run linting**

```bash
cd backend
ruff check --fix . && ruff format .
```

**Step 2: Run full test suite**

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

**Step 3: Check OpenAPI docs**

Visit `http://localhost:8000/docs` and verify:
- Position endpoints show `PositionResponse` schema
- Account list shows `PaginatedResponse` wrapper
- Error responses documented

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup after API structure overhaul"
```

---

## Summary

| Phase | Tasks | New Files | Modified Files |
|-------|-------|-----------|----------------|
| 0 | Integration tests | 4 | 0 |
| 1 | Common schemas | 3 | 1 |
| 2 | Repositories | 3 | 1 |
| 3 | Valuation service | 2 | 0 |
| 4 | Router refactoring | 0 | 4 |
| 5 | Validation | 0 | varies |

**Total new files:** ~12
**Total modified files:** ~6
