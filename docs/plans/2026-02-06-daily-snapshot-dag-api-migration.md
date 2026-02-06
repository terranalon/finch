# Daily Snapshot DAG API Migration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. After completing each coding task, use the `code-simplifier` agent to review and simplify the code.

**Goal:** Fix the failing `daily_snapshot_pipeline` DAG by migrating from direct database access to HTTP API calls, making Airflow a pure orchestrator.

**Architecture:** Create three new backend endpoints (`/api/market-data/{exchange-rates,stock-prices,crypto-prices}/refresh`) that encapsulate all price-fetching logic. The DAG will call these endpoints via HTTP using the existing service account authentication. This eliminates the SQLAlchemy version mismatch (Airflow 1.4 vs Backend 2.0) that causes the current import failures.

**Tech Stack:** FastAPI, SQLAlchemy, yfinance, CoinGecko/CryptoCompare clients, pytest

---

## Task 0: Create Git Worktree for Isolated Development

**Step 1: Create a new worktree and branch**

```bash
cd /Users/alonsamocha/PycharmProjects/portofolio_tracker
git worktree add .worktrees/fix-dag-api-migration -b fix/daily-snapshot-dag-api-migration
```

**Step 2: Navigate to the worktree**

```bash
cd .worktrees/fix-dag-api-migration
```

**Step 3: Verify you're on the correct branch**

```bash
git branch --show-current
```

Expected: `fix/daily-snapshot-dag-api-migration`

All subsequent tasks should be executed from within this worktree directory.

---

## Task 1: Create Response Schemas for Market Data Endpoints

**Files:**
- Create: `backend/app/schemas/market_data.py`

**Step 1: Write the schema file**

```python
"""Schemas for market data refresh endpoints."""

from datetime import date

from pydantic import BaseModel, Field


class RefreshStats(BaseModel):
    """Base statistics for refresh operations."""

    date: date = Field(..., description="The date prices were fetched for")
    updated: int = Field(..., description="Number of records inserted/updated")
    skipped: int = Field(..., description="Number of records skipped (already exist)")
    failed: int = Field(0, description="Number of failed fetches")


class ExchangeRateRefreshResponse(RefreshStats):
    """Response for exchange rate refresh endpoint."""

    pairs: list[str] = Field(default_factory=list, description="Currency pairs updated")


class PriceRefreshError(BaseModel):
    """Details about a failed price fetch."""

    symbol: str
    error: str


class PriceRefreshResponse(RefreshStats):
    """Response for stock/crypto price refresh endpoints."""

    source: str = Field(..., description="Data source used (yfinance, coingecko, cryptocompare)")
    errors: list[PriceRefreshError] = Field(default_factory=list)
```

**Step 2: Run linting**

```bash
cd backend && ruff check --fix app/schemas/market_data.py && ruff format app/schemas/market_data.py
```

**Step 3: Commit**

```bash
git add backend/app/schemas/market_data.py
git commit -m "feat(schemas): add market data refresh response schemas

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 4: Run code-simplifier agent**

Use the `code-simplifier` agent to review `backend/app/schemas/market_data.py`.

---

## Task 2: Create Exchange Rate Service

**Files:**
- Create: `backend/app/services/market_data/exchange_rate_service.py`
- Reference: `airflow/dags/daily_snapshot_pipeline.py:77-144` (current implementation)

**Step 1: Write the service**

```python
"""Service for fetching and storing exchange rates."""

import logging
from datetime import date, timedelta

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Currency pairs to fetch (matches current DAG)
CURRENCY_PAIRS = [
    ("USD", "ILS"),
    ("USD", "CAD"),
    ("USD", "EUR"),
    ("USD", "GBP"),
    ("CAD", "USD"),
    ("EUR", "USD"),
    ("GBP", "USD"),
    ("ILS", "USD"),
]

CHECK_EXCHANGE_RATE_EXISTS = """
SELECT 1 FROM exchange_rates
WHERE from_currency = :from_curr
AND to_currency = :to_curr
AND rate_date = :date
"""

INSERT_EXCHANGE_RATE = """
INSERT INTO exchange_rates (from_currency, to_currency, rate, rate_date)
VALUES (:from_curr, :to_curr, :rate, :date)
"""


class ExchangeRateService:
    """Service for refreshing exchange rates from yfinance."""

    @staticmethod
    def refresh(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store exchange rates for the given date.

        Args:
            db: Database session
            target_date: Date to fetch rates for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        stats = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "pairs": [],
        }

        for from_curr, to_curr in CURRENCY_PAIRS:
            try:
                # Check if rate already exists
                existing = db.execute(
                    text(CHECK_EXCHANGE_RATE_EXISTS),
                    {"from_curr": from_curr, "to_curr": to_curr, "date": target_date},
                ).first()

                if existing:
                    logger.info(f"Rate {from_curr}/{to_curr} already exists for {target_date}")
                    stats["skipped"] += 1
                    continue

                # Fetch rate using yfinance
                ticker_symbol = f"{from_curr}{to_curr}=X"
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="5d")

                if not hist.empty and "Close" in hist.columns:
                    rate = float(hist["Close"].iloc[-1])

                    db.execute(
                        text(INSERT_EXCHANGE_RATE),
                        {
                            "from_curr": from_curr,
                            "to_curr": to_curr,
                            "rate": rate,
                            "date": target_date,
                        },
                    )
                    db.commit()

                    logger.info(f"Updated {from_curr}/{to_curr} = {rate}")
                    stats["updated"] += 1
                    stats["pairs"].append(f"{from_curr}/{to_curr}")
                else:
                    logger.warning(f"No data for {from_curr}/{to_curr}")
                    stats["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to fetch {from_curr}/{to_curr}: {e}")
                stats["failed"] += 1
                db.rollback()

        return stats
```

**Step 2: Run linting**

```bash
cd backend && ruff check --fix app/services/market_data/exchange_rate_service.py && ruff format app/services/market_data/exchange_rate_service.py
```

**Step 3: Commit**

```bash
git add backend/app/services/market_data/exchange_rate_service.py
git commit -m "feat(market-data): add exchange rate refresh service

Extracts exchange rate fetching logic from Airflow DAG into a reusable
backend service. Uses yfinance for forex data.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 4: Run code-simplifier agent**

Use the `code-simplifier` agent to review `backend/app/services/market_data/exchange_rate_service.py`.

---

## Task 3: Create Daily Price Service

**Files:**
- Create: `backend/app/services/market_data/daily_price_service.py`
- Reference: `airflow/dags/daily_snapshot_pipeline.py:146-354` (current implementation)
- Reference: `backend/app/services/market_data/price_fetcher.py` (existing price fetcher)

**Step 1: Write the service**

```python
"""Service for fetching and storing daily asset prices."""

import logging
from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient

logger = logging.getLogger(__name__)

# Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
AGOROT_DIVISOR = Decimal("100")

# CoinGecko only has ~1 year of historical data
COINGECKO_HISTORY_LIMIT_DAYS = 365

GET_NON_CRYPTO_ASSETS = """
SELECT a.id, a.symbol, a.currency
FROM assets a
WHERE a.asset_class != 'Crypto'
AND EXISTS (SELECT 1 FROM holdings h WHERE h.asset_id = a.id AND h.is_active = true)
"""

GET_CRYPTO_ASSETS = """
SELECT a.id, a.symbol, a.currency
FROM assets a
WHERE a.asset_class = 'Crypto'
AND EXISTS (SELECT 1 FROM holdings h WHERE h.asset_id = a.id AND h.is_active = true)
"""

CHECK_ASSET_PRICE_EXISTS = """
SELECT 1 FROM asset_prices
WHERE asset_id = :asset_id AND price_date = :date
"""

INSERT_ASSET_PRICE = """
INSERT INTO asset_prices (asset_id, price_date, closing_price, currency, source)
VALUES (:asset_id, :date, :closing_price, :currency, :source)
"""


class DailyPriceService:
    """Service for refreshing daily asset prices."""

    @staticmethod
    def refresh_stock_prices(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store closing prices for non-crypto assets.

        Args:
            db: Database session
            target_date: Date to fetch prices for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        stats = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "source": "yfinance",
            "errors": [],
        }

        assets = db.execute(text(GET_NON_CRYPTO_ASSETS)).fetchall()
        stats["total"] = len(assets)

        for asset_id, symbol, currency in assets:
            try:
                # Check if price already exists
                existing = db.execute(
                    text(CHECK_ASSET_PRICE_EXISTS),
                    {"asset_id": asset_id, "date": target_date},
                ).first()

                if existing:
                    logger.info(f"Price for {symbol} already exists for {target_date}")
                    stats["skipped"] += 1
                    continue

                # Fetch price using yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty and "Close" in hist.columns:
                    price = Decimal(str(hist["Close"].iloc[-1]))

                    # Convert Israeli stocks from Agorot to ILS
                    if symbol.endswith(".TA"):
                        price = price / AGOROT_DIVISOR

                    db.execute(
                        text(INSERT_ASSET_PRICE),
                        {
                            "asset_id": asset_id,
                            "date": target_date,
                            "closing_price": float(price),
                            "currency": currency or "USD",
                            "source": "Yahoo Finance",
                        },
                    )
                    db.commit()

                    logger.info(f"Updated {symbol}: {price}")
                    stats["updated"] += 1
                else:
                    error_msg = f"No data available"
                    logger.warning(f"No data for {symbol}")
                    stats["failed"] += 1
                    stats["errors"].append({"symbol": symbol, "error": error_msg})

            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                stats["failed"] += 1
                stats["errors"].append({"symbol": symbol, "error": str(e)})
                db.rollback()

        return stats

    @staticmethod
    def refresh_crypto_prices(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store prices for crypto assets.

        Uses CoinGecko for recent dates (<1 year), CryptoCompare for older dates.

        Args:
            db: Database session
            target_date: Date to fetch prices for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # Determine which source to use based on date age
        days_ago = (date.today() - target_date).days
        use_coingecko = days_ago <= COINGECKO_HISTORY_LIMIT_DAYS

        stats = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "source": "coingecko" if use_coingecko else "cryptocompare",
            "errors": [],
        }

        assets = db.execute(text(GET_CRYPTO_ASSETS)).fetchall()
        stats["total"] = len(assets)

        if not assets:
            logger.info("No crypto assets found")
            return stats

        # Collect assets needing prices
        assets_needing_prices = []
        for asset_id, symbol, currency in assets:
            existing = db.execute(
                text(CHECK_ASSET_PRICE_EXISTS),
                {"asset_id": asset_id, "date": target_date},
            ).first()

            if existing:
                logger.info(f"Price for {symbol} already exists for {target_date}")
                stats["skipped"] += 1
            else:
                assets_needing_prices.append((asset_id, symbol))

        if not assets_needing_prices:
            logger.info("All crypto prices already up to date")
            return stats

        # Batch fetch prices
        symbols = [symbol for _, symbol in assets_needing_prices]

        if use_coingecko:
            prices = DailyPriceService._fetch_coingecko_prices(symbols)
        else:
            prices = DailyPriceService._fetch_cryptocompare_prices(symbols, target_date)

        # Store prices
        for asset_id, symbol in assets_needing_prices:
            try:
                price = prices.get(symbol)
                if price is not None:
                    db.execute(
                        text(INSERT_ASSET_PRICE),
                        {
                            "asset_id": asset_id,
                            "date": target_date,
                            "closing_price": float(price),
                            "currency": "USD",
                            "source": "CoinGecko" if use_coingecko else "CryptoCompare",
                        },
                    )
                    db.commit()

                    logger.info(f"Updated {symbol}: {price}")
                    stats["updated"] += 1
                else:
                    error_msg = "No price returned from API"
                    logger.warning(f"{symbol}: {error_msg}")
                    stats["failed"] += 1
                    stats["errors"].append({"symbol": symbol, "error": error_msg})

            except Exception as e:
                logger.error(f"Failed to store {symbol}: {e}")
                stats["failed"] += 1
                stats["errors"].append({"symbol": symbol, "error": str(e)})
                db.rollback()

        return stats

    @staticmethod
    def _fetch_coingecko_prices(symbols: list[str]) -> dict[str, Decimal]:
        """Fetch current prices from CoinGecko."""
        client = CoinGeckoClient()
        return client.get_current_prices(symbols, "usd")

    @staticmethod
    def _fetch_cryptocompare_prices(
        symbols: list[str], target_date: date
    ) -> dict[str, Decimal]:
        """Fetch historical prices from CryptoCompare."""
        client = CryptoCompareClient()
        prices = {}
        for symbol in symbols:
            price = client.get_historical_price(symbol, target_date)
            if price is not None:
                prices[symbol] = price
        return prices
```

**Step 2: Run linting**

```bash
cd backend && ruff check --fix app/services/market_data/daily_price_service.py && ruff format app/services/market_data/daily_price_service.py
```

**Step 3: Commit**

```bash
git add backend/app/services/market_data/daily_price_service.py
git commit -m "feat(market-data): add daily price refresh service

Extracts stock and crypto price fetching from Airflow DAG into a reusable
backend service. Uses yfinance for stocks, CoinGecko for recent crypto,
and CryptoCompare for historical crypto (>1 year).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 4: Run code-simplifier agent**

Use the `code-simplifier` agent to review `backend/app/services/market_data/daily_price_service.py`.

---

## Task 4: Create Market Data Router

**Files:**
- Create: `backend/app/routers/market_data.py`

**Step 1: Write the router**

```python
"""Market data refresh endpoints for Airflow DAG integration."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.market_data import (
    ExchangeRateRefreshResponse,
    PriceRefreshResponse,
)
from app.services.market_data.daily_price_service import DailyPriceService
from app.services.market_data.exchange_rate_service import ExchangeRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


def _get_target_date(date_param: date | None) -> date:
    """Get target date, defaulting to yesterday."""
    return date_param if date_param is not None else date.today() - timedelta(days=1)


def _require_service_account(current_user: User) -> None:
    """Verify the current user is a service account."""
    if not current_user.is_service_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires service account access",
        )


@router.post("/exchange-rates/refresh", response_model=ExchangeRateRefreshResponse)
def refresh_exchange_rates(
    date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExchangeRateRefreshResponse:
    """
    Refresh exchange rates for all supported currency pairs.

    Fetches rates from yfinance and stores them in the database.
    Idempotent: skips pairs that already have rates for the target date.

    Args:
        date: Target date (defaults to yesterday)

    Returns:
        Statistics about the refresh operation
    """
    _require_service_account(current_user)
    target_date = _get_target_date(date)

    logger.info(f"Refreshing exchange rates for {target_date}")
    result = ExchangeRateService.refresh(db, target_date)

    return ExchangeRateRefreshResponse(
        date=result["date"],
        updated=result["updated"],
        skipped=result["skipped"],
        failed=result["failed"],
        pairs=result["pairs"],
    )


@router.post("/stock-prices/refresh", response_model=PriceRefreshResponse)
def refresh_stock_prices(
    date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PriceRefreshResponse:
    """
    Refresh closing prices for non-crypto assets.

    Fetches prices from Yahoo Finance and stores them in the database.
    Idempotent: skips assets that already have prices for the target date.

    Args:
        date: Target date (defaults to yesterday)

    Returns:
        Statistics about the refresh operation
    """
    _require_service_account(current_user)
    target_date = _get_target_date(date)

    logger.info(f"Refreshing stock prices for {target_date}")
    result = DailyPriceService.refresh_stock_prices(db, target_date)

    return PriceRefreshResponse(
        date=result["date"],
        updated=result["updated"],
        skipped=result["skipped"],
        failed=result["failed"],
        source=result["source"],
        errors=[{"symbol": e["symbol"], "error": e["error"]} for e in result["errors"]],
    )


@router.post("/crypto-prices/refresh", response_model=PriceRefreshResponse)
def refresh_crypto_prices(
    date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PriceRefreshResponse:
    """
    Refresh prices for crypto assets.

    Uses CoinGecko for recent dates (<1 year), CryptoCompare for older dates.
    Idempotent: skips assets that already have prices for the target date.

    Args:
        date: Target date (defaults to yesterday)

    Returns:
        Statistics about the refresh operation
    """
    _require_service_account(current_user)
    target_date = _get_target_date(date)

    logger.info(f"Refreshing crypto prices for {target_date}")
    result = DailyPriceService.refresh_crypto_prices(db, target_date)

    return PriceRefreshResponse(
        date=result["date"],
        updated=result["updated"],
        skipped=result["skipped"],
        failed=result["failed"],
        source=result["source"],
        errors=[{"symbol": e["symbol"], "error": e["error"]} for e in result["errors"]],
    )
```

**Step 2: Run linting**

```bash
cd backend && ruff check --fix app/routers/market_data.py && ruff format app/routers/market_data.py
```

**Step 3: Commit**

```bash
git add backend/app/routers/market_data.py
git commit -m "feat(api): add market data refresh endpoints

Add three endpoints for Airflow DAG integration:
- POST /api/market-data/exchange-rates/refresh
- POST /api/market-data/stock-prices/refresh
- POST /api/market-data/crypto-prices/refresh

All endpoints require service account authentication and are idempotent.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 4: Run code-simplifier agent**

Use the `code-simplifier` agent to review `backend/app/routers/market_data.py`.

---

## Task 5: Register Market Data Router

**Files:**
- Modify: `backend/app/main.py:57-89`

**Step 1: Add import**

Add `market_data` to the imports at line 57:

```python
from app.routers import (
    accounts,
    admin,
    assets,
    auth,
    broker_data,
    brokers,
    dashboard,
    holdings,
    market_data,  # ADD THIS LINE
    mfa,
    portfolios,
    positions,
    prices,
    snapshots,
    transaction_views,
    transactions,
)
```

**Step 2: Register the router**

Add after line 86 (`app.include_router(prices.router)`):

```python
app.include_router(market_data.router)
```

**Step 3: Run linting**

```bash
cd backend && ruff check --fix app/main.py && ruff format app/main.py
```

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(api): register market data router

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Write Integration Tests for Market Data Endpoints

**Files:**
- Create: `backend/tests/integration/test_market_data_api.py`

**Step 1: Write the test file**

```python
"""Integration tests for market data refresh endpoints."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestMarketDataAPI:
    """Test /api/market-data endpoints."""

    def test_exchange_rates_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/exchange-rates/refresh")
        assert response.status_code == 401

    def test_exchange_rates_requires_service_account(self, auth_client):
        """Endpoint requires service account, not regular user."""
        response = auth_client.post("/api/market-data/exchange-rates/refresh")
        assert response.status_code == 403
        assert "service account" in response.json()["detail"].lower()

    def test_stock_prices_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/stock-prices/refresh")
        assert response.status_code == 401

    def test_stock_prices_requires_service_account(self, auth_client):
        """Endpoint requires service account, not regular user."""
        response = auth_client.post("/api/market-data/stock-prices/refresh")
        assert response.status_code == 403

    def test_crypto_prices_requires_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/market-data/crypto-prices/refresh")
        assert response.status_code == 401

    def test_crypto_prices_requires_service_account(self, auth_client):
        """Endpoint requires service account, not regular user."""
        response = auth_client.post("/api/market-data/crypto-prices/refresh")
        assert response.status_code == 403


class TestMarketDataAPIWithServiceAccount:
    """Test endpoints with service account authentication."""

    @pytest.fixture
    def service_account_client(self, client, db_session):
        """Create a service account and return authenticated client."""
        from app.models import User
        from app.services.auth.auth_service import AuthService

        # Create service account
        user = User(
            email="test-service@system.internal",
            hashed_password=AuthService.hash_password("test-password"),
            is_active=True,
            is_verified=True,
            is_service_account=True,
        )
        db_session.add(user)
        db_session.commit()

        # Login and get token
        response = client.post(
            "/api/auth/login",
            json={"email": "test-service@system.internal", "password": "test-password"},
        )
        token = response.json()["access_token"]

        # Return client with auth header
        client.headers["Authorization"] = f"Bearer {token}"
        return client

    @patch("app.services.market_data.exchange_rate_service.yf.Ticker")
    def test_exchange_rates_refresh_success(self, mock_ticker, service_account_client):
        """Service account can refresh exchange rates."""
        # Mock yfinance response
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.__getitem__ = lambda self, key: MagicMock(iloc=MagicMock(__getitem__=lambda s, i: 3.65))
        mock_ticker.return_value.history.return_value = mock_hist

        yesterday = date.today() - timedelta(days=1)
        response = service_account_client.post(
            "/api/market-data/exchange-rates/refresh",
            params={"date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert "updated" in data
        assert "skipped" in data
        assert "pairs" in data

    @patch("app.services.market_data.daily_price_service.yf.Ticker")
    def test_stock_prices_refresh_success(self, mock_ticker, service_account_client):
        """Service account can refresh stock prices."""
        # Mock yfinance response
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.__getitem__ = lambda self, key: MagicMock(iloc=MagicMock(__getitem__=lambda s, i: 150.0))
        mock_ticker.return_value.history.return_value = mock_hist

        yesterday = date.today() - timedelta(days=1)
        response = service_account_client.post(
            "/api/market-data/stock-prices/refresh",
            params={"date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert data["source"] == "yfinance"

    @patch("app.services.market_data.daily_price_service.CoinGeckoClient")
    def test_crypto_prices_refresh_success(self, mock_client_class, service_account_client):
        """Service account can refresh crypto prices."""
        # Mock CoinGecko response
        mock_client = MagicMock()
        mock_client.get_current_prices.return_value = {}
        mock_client_class.return_value = mock_client

        yesterday = date.today() - timedelta(days=1)
        response = service_account_client.post(
            "/api/market-data/crypto-prices/refresh",
            params={"date": str(yesterday)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == str(yesterday)
        assert data["source"] == "coingecko"

    def test_exchange_rates_defaults_to_yesterday(self, service_account_client):
        """Date defaults to yesterday when not provided."""
        with patch("app.services.market_data.exchange_rate_service.yf.Ticker") as mock_ticker:
            mock_hist = MagicMock()
            mock_hist.empty = True
            mock_ticker.return_value.history.return_value = mock_hist

            response = service_account_client.post("/api/market-data/exchange-rates/refresh")

            assert response.status_code == 200
            data = response.json()
            expected_date = date.today() - timedelta(days=1)
            assert data["date"] == str(expected_date)
```

**Step 2: Run the tests**

```bash
cd backend && python -m pytest tests/integration/test_market_data_api.py -v
```

Expected: All tests pass.

**Step 3: Run linting**

```bash
cd backend && ruff check --fix tests/integration/test_market_data_api.py && ruff format tests/integration/test_market_data_api.py
```

**Step 4: Commit**

```bash
git add backend/tests/integration/test_market_data_api.py
git commit -m "test(api): add integration tests for market data endpoints

Tests authentication, service account requirement, and basic functionality
for all three market data refresh endpoints.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 5: Run code-simplifier agent**

Use the `code-simplifier` agent to review `backend/tests/integration/test_market_data_api.py`.

---

## Task 7: Simplify Airflow DAG to Use API Calls

**Files:**
- Modify: `airflow/dags/daily_snapshot_pipeline.py`

**Step 1: Replace the entire DAG file**

The new DAG will be much simpler - just HTTP calls:

```python
"""Daily snapshot pipeline - fetches prices and creates portfolio snapshots.

This DAG runs at midnight UTC and:
1. Fetches exchange rates via backend API
2. Fetches stock prices via backend API
3. Fetches crypto prices via backend API
4. Creates portfolio snapshots via backend API

All data operations are handled by the backend - this DAG is a pure orchestrator.
"""

import logging
from datetime import date, datetime, timedelta

import requests
from airflow.decorators import dag, task

from auth_helper import get_auth_helper

logger = logging.getLogger(__name__)

# Backend API URL (Docker cross-network access)
BACKEND_URL = "http://host.docker.internal:8000"

# Default task arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


def _make_api_call(endpoint: str, params: dict | None = None) -> dict:
    """Make authenticated API call to backend."""
    auth = get_auth_helper()
    url = f"{BACKEND_URL}{endpoint}"

    response = requests.post(
        url,
        params=params,
        headers=auth.get_auth_headers(),
        timeout=120,
    )

    if response.status_code == 401:
        # Token expired, force refresh and retry
        auth.force_refresh()
        response = requests.post(
            url,
            params=params,
            headers=auth.get_auth_headers(),
            timeout=120,
        )

    if response.status_code != 200:
        logger.error(f"API error: {response.status_code} - {response.text}")
        raise RuntimeError(f"API call failed: {response.text}")

    return response.json()


@dag(
    dag_id="daily_snapshot_pipeline",
    default_args=default_args,
    description="Daily end-of-day snapshots with exchange rates and asset prices",
    schedule="0 0 * * *",  # Midnight UTC daily
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["portfolio", "daily", "snapshots"],
)
def daily_snapshot_pipeline():
    """Define the daily data pipeline DAG."""

    @task(task_id="fetch_exchange_rates")
    def fetch_exchange_rates() -> dict:
        """Fetch exchange rates via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info(f"Fetching exchange rates for {snapshot_date}")

        result = _make_api_call(
            "/api/market-data/exchange-rates/refresh",
            params={"date": str(snapshot_date)},
        )

        logger.info(
            f"Exchange rates: {result['updated']} updated, "
            f"{result['skipped']} skipped, {result['failed']} failed"
        )
        return result

    @task(task_id="fetch_asset_prices", pool="db_write_pool")
    def fetch_asset_prices() -> dict:
        """Fetch stock prices via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info(f"Fetching stock prices for {snapshot_date}")

        result = _make_api_call(
            "/api/market-data/stock-prices/refresh",
            params={"date": str(snapshot_date)},
        )

        logger.info(
            f"Stock prices: {result['updated']} updated, "
            f"{result['skipped']} skipped, {result['failed']} failed"
        )
        return result

    @task(task_id="fetch_crypto_prices", pool="db_write_pool")
    def fetch_crypto_prices() -> dict:
        """Fetch crypto prices via backend API."""
        snapshot_date = date.today() - timedelta(days=1)
        logger.info(f"Fetching crypto prices for {snapshot_date}")

        result = _make_api_call(
            "/api/market-data/crypto-prices/refresh",
            params={"date": str(snapshot_date)},
        )

        logger.info(
            f"Crypto prices ({result['source']}): {result['updated']} updated, "
            f"{result['skipped']} skipped, {result['failed']} failed"
        )
        return result

    @task(task_id="create_snapshots")
    def create_snapshots(
        exchange_rate_stats: dict,
        asset_price_stats: dict,
        crypto_price_stats: dict,
    ) -> dict:
        """Create portfolio snapshots via backend API."""
        snapshot_date = date.today() - timedelta(days=1)

        logger.info(f"Exchange rates: {exchange_rate_stats['updated']} updated")
        logger.info(f"Stock prices: {asset_price_stats['updated']} updated")
        logger.info(f"Crypto prices: {crypto_price_stats['updated']} updated")

        result = _make_api_call(
            "/api/snapshots/create",
            params={"snapshot_date": str(snapshot_date)},
        )

        logger.info(f"Snapshots created: {result.get('snapshots_created', 0)}")
        logger.info(f"Total value: ${result.get('total_value_usd', 0):,.2f}")

        return result

    # Define task dependencies
    exchange_rate_stats = fetch_exchange_rates()
    asset_price_stats = fetch_asset_prices()
    crypto_price_stats = fetch_crypto_prices()
    create_snapshots(exchange_rate_stats, asset_price_stats, crypto_price_stats)


# Instantiate the DAG
dag_instance = daily_snapshot_pipeline()
```

**Step 2: Run linting**

```bash
cd airflow && ruff check --fix dags/daily_snapshot_pipeline.py && ruff format dags/daily_snapshot_pipeline.py
```

**Step 3: Verify DAG loads**

```bash
astro dev run dags list | grep daily_snapshot
```

Expected: `daily_snapshot_pipeline` appears without import errors.

**Step 4: Commit**

```bash
git add airflow/dags/daily_snapshot_pipeline.py
git commit -m "refactor(airflow): migrate DAG to use backend API

Replace direct database access with HTTP API calls to backend endpoints:
- /api/market-data/exchange-rates/refresh
- /api/market-data/stock-prices/refresh
- /api/market-data/crypto-prices/refresh

This fixes the SQLAlchemy version mismatch (Airflow 1.4 vs Backend 2.0)
that was causing import failures for the CoinGecko client.

The DAG is now a pure orchestrator with no direct DB or external API access.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Step 5: Run code-simplifier agent**

Use the `code-simplifier` agent to review `airflow/dags/daily_snapshot_pipeline.py`.

---

## Task 8: Clean Up Unused Airflow Code

**Files:**
- Delete: `airflow/dags/shared_db.py` (if no other DAGs use it)

**Step 1: Check if other DAGs use shared_db**

```bash
grep -r "from shared_db import" airflow/dags/ --include="*.py" | grep -v daily_snapshot_pipeline
```

If output shows other DAGs using `shared_db`, skip this task.

**Step 2: Delete if unused**

```bash
rm airflow/dags/shared_db.py
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore(airflow): remove unused shared_db module

No longer needed after migrating to API-based DAG.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Manual Verification

**Step 1: Restart backend to pick up new endpoints**

```bash
docker compose restart backend
```

**Step 2: Test endpoints manually**

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"airflow-service@system.internal","password":"ARLf3qxLRR5zkcnduDd7NhEFCblqSqCfvhgl1MMT4wc"}' \
  | jq -r '.access_token')

# Test exchange rates endpoint
curl -X POST "http://localhost:8000/api/market-data/exchange-rates/refresh" \
  -H "Authorization: Bearer $TOKEN"

# Test stock prices endpoint
curl -X POST "http://localhost:8000/api/market-data/stock-prices/refresh" \
  -H "Authorization: Bearer $TOKEN"

# Test crypto prices endpoint
curl -X POST "http://localhost:8000/api/market-data/crypto-prices/refresh" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 3: Trigger DAG run**

```bash
astro dev run dags trigger daily_snapshot_pipeline
```

**Step 4: Monitor DAG run**

Check Airflow UI at http://localhost:8080 for task status.

---

## Task 10: Create Pull Request

**Step 1: Push branch**

```bash
git push -u origin fix/daily-snapshot-dag-api-migration
```

**Step 2: Create PR**

```bash
gh pr create --title "fix: migrate daily snapshot DAG to API-based architecture" --body "$(cat <<'EOF'
## Summary
- Fixes the failing `daily_snapshot_pipeline` DAG caused by SQLAlchemy version mismatch
- Creates three new backend endpoints for market data refresh
- Migrates DAG from direct DB access to HTTP API calls
- Makes Airflow a pure orchestrator with no backend code imports

## Root Cause
The DAG was importing `CoinGeckoClient` from the backend, which triggered imports of SQLAlchemy 2.0 models. Airflow uses SQLAlchemy 1.4, causing `ImportError: cannot import name 'mapped_column'`.

## Solution
Create backend API endpoints that encapsulate all market data logic:
- `POST /api/market-data/exchange-rates/refresh`
- `POST /api/market-data/stock-prices/refresh`
- `POST /api/market-data/crypto-prices/refresh`

The DAG now calls these endpoints via HTTP using the existing service account authentication.

## Test plan
- [ ] All backend unit tests pass
- [ ] Integration tests for new endpoints pass
- [ ] DAG loads without import errors
- [ ] Manual DAG trigger succeeds
- [ ] All four tasks complete successfully

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 0 | Create git worktree | - |
| 1 | Create response schemas | `backend/app/schemas/market_data.py` |
| 2 | Create exchange rate service | `backend/app/services/market_data/exchange_rate_service.py` |
| 3 | Create daily price service | `backend/app/services/market_data/daily_price_service.py` |
| 4 | Create market data router | `backend/app/routers/market_data.py` |
| 5 | Register router in main.py | `backend/app/main.py` |
| 6 | Write integration tests | `backend/tests/integration/test_market_data_api.py` |
| 7 | Simplify DAG to use API | `airflow/dags/daily_snapshot_pipeline.py` |
| 8 | Clean up unused code | `airflow/dags/shared_db.py` |
| 9 | Manual verification | - |
| 10 | Create PR | - |
