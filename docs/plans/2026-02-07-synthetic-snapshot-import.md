# Synthetic Snapshot Import & Batch Upload Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable instant IBKR onboarding via synthetic position snapshots, with optional batch historical backfill that replaces the synthetic data.

**Architecture:** Introduce a `source_type="synthetic"` for BrokerDataSource that represents auto-generated transactions from current IBKR positions. Add batch upload sessions that defer reconstruction until all files are uploaded. When real history is uploaded, synthetic data is auto-deleted and reconstruction validates against the original snapshot.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL, pytest

---

## Context for Implementer

### Current Architecture

- **BrokerDataSource** (`backend/app/models/broker_data_source.py`) tracks every import event with `source_type` field: `'file_upload'`, `'api_fetch'`, `'legacy'`
- **Transactions** link to their source via `broker_source_id` FK (SET NULL on delete)
- **Holdings** are ALWAYS rebuilt from ALL transactions via `reconstruct_and_update_holdings()` (`backend/app/services/portfolio/holdings_reconstruction.py`)
- **IBKR API import** (`POST /api/brokers/ibkr/import/{account_id}`) fetches Flex Query data, imports transactions, reconstructs holdings
- **File upload** (`POST /api/broker-data/upload/{account_id}`) parses file, imports data, reconstructs holdings -- each upload triggers its own reconstruction
- **Delete source** (`DELETE /api/broker-data/source/{source_id}`) cascade-deletes linked transactions and cash balances, then reconstructs from remaining data

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/models/broker_data_source.py` | BrokerDataSource model (lines 13-97) |
| `backend/app/services/brokers/ibkr/flex_import_service.py` | IBKR Flex Query import orchestrator |
| `backend/app/services/brokers/ibkr/import_service.py` | IBKR import helpers (_import_transactions, _find_or_create_asset) |
| `backend/app/services/brokers/ibkr/parser.py` | XML parser (extract_positions at line 97) |
| `backend/app/services/portfolio/holdings_reconstruction.py` | reconstruct_and_update_holdings() |
| `backend/app/routers/brokers.py` | API import endpoints (import at line 385) |
| `backend/app/routers/broker_data.py` | File upload (line 269), delete source (line 657) |
| `backend/app/services/shared/transaction_hash_service.py` | Dedup via compute_transaction_hash() |
| `backend/app/services/shared/broker_overlap_detector.py` | analyze_overlap() at line 256 |
| `backend/tests/test_ibkr_flex_import_date_range.py` | Existing IBKR import tests |

### Test Commands

```bash
# Run all backend tests locally
DATABASE_HOST=localhost uv run --extra dev python -m pytest

# Run a specific test file
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/test_file.py -v

# Run a specific test
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/test_file.py::TestClass::test_name -v

# Lint
cd backend && ruff check --fix . && ruff format .
```

---

## Task 1: Add `source_type="synthetic"` Support to BrokerDataSource

**Files:**
- Modify: `backend/app/models/broker_data_source.py:49` (update docstring)
- Create: `backend/tests/unit/test_synthetic_source_type.py`

### Step 1: Write the failing test

```python
# backend/tests/unit/test_synthetic_source_type.py
"""Tests for synthetic source type support."""

from datetime import date

from app.models.broker_data_source import BrokerDataSource


class TestSyntheticSourceType:
    """Verify BrokerDataSource accepts 'synthetic' source_type."""

    def test_create_synthetic_source(self, db):
        """BrokerDataSource should accept source_type='synthetic'."""
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="synthetic",
            source_identifier="Synthetic Snapshot 2026-02-07",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="completed",
        )
        db.add(source)
        db.flush()

        assert source.id is not None
        assert source.source_type == "synthetic"

    def test_synthetic_source_has_no_file(self, db):
        """Synthetic sources should have no file_path or file_hash."""
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="synthetic",
            source_identifier="Synthetic Snapshot 2026-02-07",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="completed",
        )
        db.add(source)
        db.flush()

        assert source.file_path is None
        assert source.file_hash is None
```

### Step 2: Run test to verify it passes (model already supports arbitrary strings)

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_synthetic_source_type.py -v
```

Expected: PASS (the String(20) column accepts any string up to 20 chars; "synthetic" is 9 chars).

### Step 3: Update the docstring to document the new source type

In `backend/app/models/broker_data_source.py`, line 49, change:

```python
source_type: Mapped[str] = mapped_column(String(20))  # 'file_upload', 'api_fetch', 'legacy'
```

to:

```python
source_type: Mapped[str] = mapped_column(String(20))  # 'file_upload', 'api_fetch', 'synthetic', 'legacy'
```

Also update the class docstring (line 14-24) to add:

```
- synthetic: Auto-generated from current broker positions (snapshot onboarding)
```

### Step 4: Run tests to verify nothing breaks

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_synthetic_source_type.py -v
```

### Step 5: Commit

```bash
git add backend/app/models/broker_data_source.py backend/tests/unit/test_synthetic_source_type.py
git commit -m "feat: add synthetic source_type to BrokerDataSource model"
```

---

## Task 2: Create Synthetic Snapshot Import Service

This service takes IBKR position data (symbol, quantity, cost_basis) and creates synthetic "Buy" transactions that represent the current portfolio state.

**Files:**
- Create: `backend/app/services/brokers/ibkr/synthetic_import_service.py`
- Create: `backend/tests/unit/test_ibkr_synthetic_import.py`

### Step 1: Write the failing tests

```python
# backend/tests/unit/test_ibkr_synthetic_import.py
"""Tests for IBKR synthetic snapshot import service."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models import Account


class TestSyntheticImportService:
    """Tests for IBKRSyntheticImportService."""

    @patch("app.services.portfolio.holdings_reconstruction.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_synthetic_source(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """import_snapshot should create a BrokerDataSource with source_type='synthetic'."""
        from app.services.brokers.ibkr.synthetic_import_service import (
            IBKRSyntheticImportService,
        )

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = [
            {
                "symbol": "AAPL",
                "original_symbol": "AAPL",
                "description": "APPLE INC",
                "asset_category": "STK",
                "asset_class": "Stock",
                "listing_exchange": "NASDAQ",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
                "currency": "USD",
                "account_id": "U12345",
                "needs_validation": False,
                "cusip": "037833100",
                "isin": "US0378331005",
                "conid": "265598",
                "figi": None,
            }
        ]
        mock_parser.extract_cash_balances.return_value = [
            {
                "symbol": "USD",
                "currency": "USD",
                "balance": Decimal("5000"),
                "description": "US Dollar",
                "asset_class": "Cash",
            }
        ]

        mock_import_service._import_cash_balances.return_value = {"holdings_created": 1}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "completed"
        assert stats["source_type"] == "synthetic"

        # Verify BrokerDataSource was created with source_type="synthetic"
        add_calls = mock_db.add.call_args_list
        source_added = None
        for call in add_calls:
            obj = call[0][0]
            if hasattr(obj, "source_type") and obj.source_type == "synthetic":
                source_added = obj
                break
        assert source_added is not None
        assert source_added.source_type == "synthetic"

    @patch("app.services.portfolio.holdings_reconstruction.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_creates_buy_transactions_from_positions(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """Each position should generate a synthetic Buy transaction."""
        from app.services.brokers.ibkr.synthetic_import_service import (
            IBKRSyntheticImportService,
        )

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = [
            {
                "symbol": "AAPL",
                "original_symbol": "AAPL",
                "description": "APPLE INC",
                "asset_category": "STK",
                "asset_class": "Stock",
                "listing_exchange": "NASDAQ",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
                "currency": "USD",
                "account_id": "U12345",
                "needs_validation": False,
                "cusip": "037833100",
                "isin": "US0378331005",
                "conid": "265598",
                "figi": None,
            },
            {
                "symbol": "MSFT",
                "original_symbol": "MSFT",
                "description": "MICROSOFT CORP",
                "asset_category": "STK",
                "asset_class": "Stock",
                "listing_exchange": "NASDAQ",
                "quantity": Decimal("50"),
                "cost_basis": Decimal("20000"),
                "currency": "USD",
                "account_id": "U12345",
                "needs_validation": False,
                "cusip": None,
                "isin": None,
                "conid": None,
                "figi": None,
            },
        ]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_asset = MagicMock(id=10)
        mock_import_service._find_or_create_asset.return_value = (mock_asset, False)
        mock_reconstruct.return_value = {"holdings_updated": 2}

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["positions_imported"] == 2

    @patch("app.services.portfolio.holdings_reconstruction.reconstruct_and_update_holdings")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRImportService")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_stores_snapshot_data_for_validation(
        self, mock_client, mock_parser, mock_import_service, mock_reconstruct
    ):
        """Snapshot data should be stored in import_stats for later validation."""
        from app.services.brokers.ibkr.synthetic_import_service import (
            IBKRSyntheticImportService,
        )

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = b"<xml>data</xml>"
        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = [
            {
                "symbol": "AAPL",
                "original_symbol": "AAPL",
                "description": "APPLE INC",
                "asset_category": "STK",
                "asset_class": "Stock",
                "listing_exchange": "NASDAQ",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
                "currency": "USD",
                "account_id": "U12345",
                "needs_validation": False,
                "cusip": "037833100",
                "isin": None,
                "conid": None,
                "figi": None,
            }
        ]
        mock_parser.extract_cash_balances.return_value = []

        mock_import_service._import_cash_balances.return_value = {}
        mock_import_service._find_or_create_asset.return_value = (MagicMock(id=10), False)
        mock_reconstruct.return_value = {"holdings_updated": 1}

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        # Check BrokerDataSource has snapshot_positions in import_stats
        add_calls = mock_db.add.call_args_list
        source_added = None
        for call in add_calls:
            obj = call[0][0]
            if hasattr(obj, "source_type") and obj.source_type == "synthetic":
                source_added = obj
                break

        assert source_added is not None
        assert "snapshot_positions" in source_added.import_stats
        snapshot = source_added.import_stats["snapshot_positions"]
        assert len(snapshot) == 1
        assert snapshot[0]["symbol"] == "AAPL"
        assert snapshot[0]["quantity"] == "100"
        assert snapshot[0]["cost_basis"] == "15000"

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    def test_fails_gracefully_on_api_error(self, mock_client):
        """Should return failed status when Flex API returns no data."""
        from app.services.brokers.ibkr.synthetic_import_service import (
            IBKRSyntheticImportService,
        )

        mock_db = MagicMock(spec=Session)
        mock_account = MagicMock(spec=Account)
        mock_account.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        mock_client.fetch_flex_report.return_value = None

        stats = IBKRSyntheticImportService.import_snapshot(
            mock_db, account_id=1, flex_token="token", flex_query_id="query_id"
        )

        assert stats["status"] == "failed"
```

### Step 2: Run tests to verify they fail

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_ibkr_synthetic_import.py -v
```

Expected: FAIL (module not found)

### Step 3: Implement the synthetic import service

```python
# backend/app/services/brokers/ibkr/synthetic_import_service.py
"""IBKR synthetic snapshot import service.

Creates synthetic transactions from current IBKR positions for instant onboarding.
These synthetic records are replaced when the user uploads full historical data.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, BrokerDataSource, Holding, Transaction
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.parser import IBKRParser

logger = logging.getLogger(__name__)


class IBKRSyntheticImportService:
    """Creates synthetic transactions from current IBKR positions."""

    @staticmethod
    def import_snapshot(
        db: Session, account_id: int, flex_token: str, flex_query_id: str
    ) -> dict:
        """Fetch current positions from IBKR and create synthetic transactions.

        This creates:
        1. A BrokerDataSource with source_type='synthetic'
        2. One synthetic 'Buy' transaction per position (quantity + cost_basis)
        3. Cash balance holdings from current cash report

        The snapshot_positions are stored in import_stats for later validation
        when the user uploads real historical data.

        Args:
            db: Database session
            account_id: Account to import into
            flex_token: IBKR Flex Web Service token
            flex_query_id: Flex Query ID

        Returns:
            Statistics dictionary
        """
        stats = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "source_type": "synthetic",
            "status": "in_progress",
            "positions_imported": 0,
            "cash_balances": {},
            "assets_created": 0,
            "errors": [],
        }

        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                stats["status"] = "failed"
                stats["errors"].append(f"Account {account_id} not found")
                return stats

            # Fetch current data from IBKR
            xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)
            if not xml_data:
                stats["status"] = "failed"
                stats["errors"].append(
                    "Failed to fetch Flex Query report. Check your token and query ID."
                )
                return stats

            root = IBKRParser.parse_xml(xml_data)
            if root is None:
                stats["status"] = "failed"
                stats["errors"].append("Failed to parse Flex Query XML response")
                return stats

            # Extract positions and cash balances only
            positions_data = IBKRParser.extract_positions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            today = date.today()

            # Create synthetic BrokerDataSource
            source = BrokerDataSource(
                account_id=account_id,
                broker_type="ibkr",
                source_type="synthetic",
                source_identifier=f"Synthetic Snapshot {today.isoformat()}",
                start_date=today,
                end_date=today,
                status="pending",
            )
            db.add(source)
            db.flush()

            # Import cash balances
            cash_stats = IBKRImportService._import_cash_balances(
                db, account_id, cash_data
            )
            stats["cash_balances"] = cash_stats

            # Create synthetic Buy transactions for each position
            for position in positions_data:
                symbol = position["symbol"]
                quantity = position["quantity"]
                cost_basis = position["cost_basis"]

                if quantity == 0:
                    continue

                # Find or create asset
                asset, created = IBKRImportService._find_or_create_asset(
                    db,
                    symbol=symbol,
                    name=position["description"],
                    asset_class=position["asset_class"],
                    currency=position.get("currency", "USD"),
                    ibkr_symbol=position["original_symbol"],
                    cusip=position.get("cusip"),
                    isin=position.get("isin"),
                    conid=position.get("conid"),
                    figi=position.get("figi"),
                )
                if created:
                    stats["assets_created"] += 1

                # Find or create holding
                holding = (
                    db.query(Holding)
                    .filter(
                        Holding.account_id == account_id,
                        Holding.asset_id == asset.id,
                    )
                    .first()
                )
                if not holding:
                    holding = Holding(
                        account_id=account_id,
                        asset_id=asset.id,
                        quantity=Decimal("0"),
                        cost_basis=Decimal("0"),
                        is_active=False,
                    )
                    db.add(holding)
                    db.flush()

                # Calculate price per unit from cost basis
                price_per_unit = (
                    abs(cost_basis / quantity) if quantity != 0 else Decimal("0")
                )

                # Create synthetic Buy transaction
                txn = Transaction(
                    holding_id=holding.id,
                    broker_source_id=source.id,
                    date=today,
                    type="Buy",
                    quantity=abs(quantity),
                    price_per_unit=price_per_unit,
                    amount=abs(cost_basis),
                    fees=Decimal("0"),
                    notes="Synthetic transaction from IBKR position snapshot",
                )
                db.add(txn)
                stats["positions_imported"] += 1

            # Store snapshot positions for later validation
            snapshot_positions = [
                {
                    "symbol": p["symbol"],
                    "quantity": str(p["quantity"]),
                    "cost_basis": str(p["cost_basis"]),
                    "currency": p.get("currency", "USD"),
                }
                for p in positions_data
                if p["quantity"] != 0
            ]

            source.import_stats = {
                "snapshot_positions": snapshot_positions,
                "positions_imported": stats["positions_imported"],
                "cash_balances": cash_stats,
                "assets_created": stats["assets_created"],
            }
            source.status = "completed"

            # Reconstruct holdings
            from app.services.portfolio.holdings_reconstruction import (
                reconstruct_and_update_holdings,
            )

            reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
            stats["holdings_reconstruction"] = reconstruction_stats

            db.commit()
            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            return stats

        except Exception as e:
            db.rollback()
            logger.error(f"Synthetic snapshot import failed: {e}", exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats
```

### Step 4: Run tests to verify they pass

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_ibkr_synthetic_import.py -v
```

### Step 5: Commit

```bash
git add backend/app/services/brokers/ibkr/synthetic_import_service.py backend/tests/unit/test_ibkr_synthetic_import.py
git commit -m "feat: add IBKR synthetic snapshot import service"
```

---

## Task 3: Add Snapshot Import API Endpoint

Expose the synthetic import as a new endpoint on the brokers router.

**Files:**
- Modify: `backend/app/routers/brokers.py` (add endpoint after line 480)
- Create: `backend/tests/unit/test_snapshot_endpoint.py`

### Step 1: Write the failing test

```python
# backend/tests/unit/test_snapshot_endpoint.py
"""Tests for the synthetic snapshot import endpoint."""

from unittest.mock import MagicMock, patch


class TestSnapshotEndpoint:
    """Tests for POST /api/brokers/ibkr/snapshot/{account_id}."""

    @patch("app.routers.brokers.IBKRSyntheticImportService")
    def test_snapshot_endpoint_calls_service(self, mock_service, auth_client, test_user, db):
        """Snapshot endpoint should call IBKRSyntheticImportService.import_snapshot."""
        from app.models import Account

        # Create test account with IBKR credentials
        account = Account(
            name="Test IBKR",
            institution="IBKR",
            account_type="Brokerage",
            currency="USD",
            broker_type="ibkr",
            meta_data={"ibkr": {"flex_token": "test_token", "flex_query_id": "12345"}},
        )
        db.add(account)
        db.flush()
        account.portfolios = test_user.portfolios
        db.commit()

        mock_service.import_snapshot.return_value = {
            "status": "completed",
            "source_type": "synthetic",
            "positions_imported": 3,
        }

        response = auth_client.post(f"/api/brokers/ibkr/snapshot/{account.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        mock_service.import_snapshot.assert_called_once()
```

### Step 2: Run test to verify it fails

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_snapshot_endpoint.py -v
```

Expected: FAIL (endpoint not found, 404)

### Step 3: Add the endpoint to brokers.py

Add this after the existing `import_broker_data` endpoint (after line 480 in `backend/app/routers/brokers.py`):

```python
@router.post("/ibkr/snapshot/{account_id}", response_model=dict[str, Any])
async def import_ibkr_snapshot(
    account_id: int,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a synthetic snapshot from current IBKR positions.

    This fetches the user's current IBKR positions and cash balances,
    then creates synthetic transactions representing the current state.
    Use this for instant onboarding -- the user can upload full history later.

    The synthetic data is automatically replaced when historical files are uploaded.

    Args:
        account_id: Account with stored IBKR credentials

    Returns:
        Snapshot import statistics
    """
    from app.services.brokers.ibkr.synthetic_import_service import (
        IBKRSyntheticImportService,
    )

    config = _get_broker_config(BrokerType.IBKR)
    account = _get_validated_account(account_id, current_user, db)

    flex_token, flex_query_id = _get_flex_query_credentials(
        account, config.key, config.name, config.env_fallback_prefix
    )

    stats = IBKRSyntheticImportService.import_snapshot(
        db, account_id, flex_token, flex_query_id
    )

    if stats.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Snapshot import failed: {stats.get('errors', ['Unknown error'])}",
        )

    _update_last_import(account, config.key, db)

    # Trigger background snapshot generation
    if background_tasks:
        from app.services.portfolio.snapshot_service import (
            generate_snapshots_background,
            update_snapshot_status,
        )

        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(
            generate_snapshots_background, account_id, date.today()
        )

    return {
        "status": "completed",
        "message": f"Synthetic snapshot created for account {account.name}",
        "account_id": account_id,
        "stats": stats,
    }
```

Also add the import at the top of the file:

```python
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService
```

### Step 4: Run tests

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_snapshot_endpoint.py -v
```

### Step 5: Commit

```bash
git add backend/app/routers/brokers.py backend/tests/unit/test_snapshot_endpoint.py
git commit -m "feat: add POST /api/brokers/ibkr/snapshot endpoint"
```

---

## Task 4: Auto-Delete Synthetic Sources on Historical Upload

When a user uploads real historical files for an account that has a synthetic source, automatically delete the synthetic source before importing.

**Files:**
- Modify: `backend/app/routers/broker_data.py` (upload endpoint, around line 388)
- Create: `backend/tests/unit/test_synthetic_auto_delete.py`

### Step 1: Write the failing test

```python
# backend/tests/unit/test_synthetic_auto_delete.py
"""Tests for auto-deleting synthetic sources on historical upload."""

from datetime import date
from unittest.mock import MagicMock, patch

from app.models.broker_data_source import BrokerDataSource


class TestSyntheticAutoDelete:
    """Synthetic sources should be auto-deleted when real data is uploaded."""

    def test_find_synthetic_sources(self, db):
        """Should find synthetic sources for a given account and broker."""
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="synthetic",
            source_identifier="Synthetic Snapshot 2026-02-07",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="completed",
            import_stats={
                "snapshot_positions": [
                    {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"}
                ]
            },
        )
        db.add(source)
        db.flush()

        synthetic_sources = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == 1,
                BrokerDataSource.broker_type == "ibkr",
                BrokerDataSource.source_type == "synthetic",
            )
            .all()
        )

        assert len(synthetic_sources) == 1
        assert synthetic_sources[0].import_stats["snapshot_positions"][0]["symbol"] == "AAPL"
```

### Step 2: Run test

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_synthetic_auto_delete.py -v
```

### Step 3: Add synthetic source detection and deletion to the upload endpoint

In `backend/app/routers/broker_data.py`, add a helper function before the upload endpoint:

```python
def _delete_synthetic_sources(db: Session, account_id: int, broker_type: str) -> dict:
    """Delete synthetic sources and their transactions for an account/broker.

    Returns stats about what was deleted.
    """
    synthetic_sources = (
        db.query(BrokerDataSource)
        .filter(
            BrokerDataSource.account_id == account_id,
            BrokerDataSource.broker_type == broker_type,
            BrokerDataSource.source_type == "synthetic",
        )
        .all()
    )

    if not synthetic_sources:
        return {"deleted_sources": 0, "deleted_transactions": 0}

    total_txns_deleted = 0
    total_cash_deleted = 0
    snapshot_positions = []

    for source in synthetic_sources:
        # Save snapshot data for validation
        if source.import_stats and "snapshot_positions" in source.import_stats:
            snapshot_positions = source.import_stats["snapshot_positions"]

        # Delete linked transactions
        txns_deleted = (
            db.query(Transaction)
            .filter(Transaction.broker_source_id == source.id)
            .delete(synchronize_session=False)
        )
        total_txns_deleted += txns_deleted

        # Delete linked cash balances
        cash_deleted = (
            db.query(DailyCashBalance)
            .filter(DailyCashBalance.broker_source_id == source.id)
            .delete(synchronize_session=False)
        )
        total_cash_deleted += cash_deleted

        db.delete(source)

    return {
        "deleted_sources": len(synthetic_sources),
        "deleted_transactions": total_txns_deleted,
        "deleted_cash_balances": total_cash_deleted,
        "snapshot_positions": snapshot_positions,
    }
```

Then in the upload endpoint (`upload_broker_file`), right before the `# Parse and import data` block (line 388), add:

```python
    # Auto-delete synthetic sources when uploading real historical data
    synthetic_cleanup = _delete_synthetic_sources(db, account_id, broker_type)
    if synthetic_cleanup["deleted_sources"] > 0:
        logger.info(
            "Auto-deleted %d synthetic source(s) for account %d: %d transactions removed",
            synthetic_cleanup["deleted_sources"],
            account_id,
            synthetic_cleanup["deleted_transactions"],
        )
```

### Step 4: Run tests

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_synthetic_auto_delete.py -v
```

### Step 5: Commit

```bash
git add backend/app/routers/broker_data.py backend/tests/unit/test_synthetic_auto_delete.py
git commit -m "feat: auto-delete synthetic sources on historical file upload"
```

---

## Task 5: Batch Upload Sessions (Deferred Reconstruction)

Add a batch upload mode that stages multiple files without reconstructing until finalized.

**Files:**
- Modify: `backend/app/routers/broker_data.py` (add `session_id` param to upload, add finalize endpoint)
- Create: `backend/tests/unit/test_batch_upload.py`

### Step 1: Write the failing tests

```python
# backend/tests/unit/test_batch_upload.py
"""Tests for batch upload sessions with deferred reconstruction."""

import uuid
from datetime import date
from unittest.mock import patch

from app.models.broker_data_source import BrokerDataSource


class TestBatchUpload:
    """Batch uploads should defer reconstruction until finalized."""

    def test_staged_upload_skips_reconstruction(self, db):
        """Uploads with a session_id should set status='staged' and skip reconstruction."""
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="file_upload",
            source_identifier="test.xml",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            status="staged",
        )
        db.add(source)
        db.flush()

        assert source.status == "staged"

    def test_finalize_finds_staged_sources(self, db):
        """Finalize should find all staged sources for a session."""
        session_id = str(uuid.uuid4())

        for year in [2022, 2023, 2024]:
            source = BrokerDataSource(
                account_id=1,
                broker_type="ibkr",
                source_type="file_upload",
                source_identifier=f"activity_{year}.xml",
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
                status="staged",
                import_stats={"session_id": session_id},
            )
            db.add(source)

        db.flush()

        staged = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == 1,
                BrokerDataSource.status == "staged",
            )
            .all()
        )

        matching = [
            s for s in staged
            if s.import_stats and s.import_stats.get("session_id") == session_id
        ]
        assert len(matching) == 3
```

### Step 2: Run tests to verify they fail

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_batch_upload.py -v
```

### Step 3: Modify the upload endpoint and add finalize endpoint

**Modify upload endpoint** in `backend/app/routers/broker_data.py`:

Add `session_id` parameter to the upload endpoint signature:

```python
async def upload_broker_file(
    account_id: int,
    broker_type: str = Form(...),
    file: UploadFile = File(...),
    confirm_overlap: bool = Form(False),
    session_id: str | None = Form(None),  # NEW: batch upload session
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
```

When `session_id` is provided:
- Set `source.status = "staged"` instead of `"pending"`
- Store `session_id` in `source.import_stats`
- Skip reconstruction and snapshot generation
- Still parse and import transactions (so dedup works across files in the session)

After the import completes (after `source.import_stats = {...}`), wrap the existing reconstruction + snapshot code:

```python
        if session_id:
            # Batch mode: stage the source, skip reconstruction
            source.status = "staged"
            if source.import_stats is None:
                source.import_stats = {}
            source.import_stats["session_id"] = session_id
            db.commit()

            return UploadResponse(
                status="staged",
                message=f"File staged for batch import ({source.import_stats.get('total_records', 0)} records). "
                        f"Call finalize when all files are uploaded.",
                source_id=source.id,
                date_range={"start_date": str(start_date), "end_date": str(end_date)},
                stats=source.import_stats or {},
            )
        else:
            # Single file mode: existing behavior
            source.status = "completed"
            db.commit()
            # ... existing reconstruction + snapshot code ...
```

**Add finalize endpoint:**

```python
@router.post("/finalize-batch/{account_id}")
async def finalize_batch_upload(
    account_id: int,
    session_id: str = Query(..., description="The batch session ID to finalize"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Finalize a batch upload session: reconstruct holdings and generate snapshots.

    This should be called after all files for a historical import have been uploaded.
    It triggers a single reconstruction from all transactions.

    Args:
        account_id: Account that owns the staged uploads
        session_id: The session ID used during uploads

    Returns:
        Finalization statistics including reconstruction results
    """
    _validate_account_access(account_id, current_user, db)

    # Find all staged sources for this session
    staged_sources = (
        db.query(BrokerDataSource)
        .filter(
            BrokerDataSource.account_id == account_id,
            BrokerDataSource.status == "staged",
        )
        .all()
    )

    matching = [
        s for s in staged_sources
        if s.import_stats and s.import_stats.get("session_id") == session_id
    ]

    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No staged uploads found for session {session_id}",
        )

    # Auto-delete synthetic sources before finalizing
    synthetic_cleanup = _delete_synthetic_sources(
        db, account_id, matching[0].broker_type
    )

    # Mark all staged sources as completed
    for source in matching:
        source.status = "completed"

    # Single reconstruction from all transactions
    reconstruction_stats = reconstruct_and_update_holdings(db, account_id)

    db.commit()

    # Calculate overall date range
    earliest = min(s.start_date for s in matching)
    latest = max(s.end_date for s in matching)

    # Trigger background snapshot generation
    if background_tasks:
        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(generate_snapshots_background, account_id, earliest)

    return {
        "status": "completed",
        "message": f"Finalized {len(matching)} files",
        "session_id": session_id,
        "sources_finalized": len(matching),
        "date_range": {
            "start_date": str(earliest),
            "end_date": str(latest),
        },
        "synthetic_cleanup": synthetic_cleanup,
        "holdings_reconstruction": reconstruction_stats,
    }
```

### Step 4: Run tests

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_batch_upload.py -v
```

### Step 5: Commit

```bash
git add backend/app/routers/broker_data.py backend/tests/unit/test_batch_upload.py
git commit -m "feat: add batch upload sessions with deferred reconstruction"
```

---

## Task 6: Validation Service -- Compare Reconstructed vs. Snapshot

**Files:**
- Create: `backend/app/services/brokers/ibkr/snapshot_validation_service.py`
- Create: `backend/tests/unit/test_snapshot_validation.py`

### Step 1: Write the failing tests

```python
# backend/tests/unit/test_snapshot_validation.py
"""Tests for snapshot validation service."""

from decimal import Decimal


class TestSnapshotValidation:
    """Validate reconstructed holdings against original snapshot data."""

    def test_perfect_match(self):
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )

        snapshot = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
        ]
        reconstructed = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
            {"symbol": "MSFT", "quantity": Decimal("50"), "cost_basis": Decimal("20000")},
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0

    def test_missing_position(self):
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )

        snapshot = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
            {"symbol": "MSFT", "quantity": "50", "cost_basis": "20000", "currency": "USD"},
        ]
        reconstructed = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        assert any(d["type"] == "missing_position" for d in result["discrepancies"])

    def test_quantity_mismatch(self):
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )

        snapshot = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        reconstructed = [
            {"symbol": "AAPL", "quantity": Decimal("85"), "cost_basis": Decimal("12750")},
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        assert any(d["type"] == "quantity_mismatch" for d in result["discrepancies"])

    def test_cost_basis_within_tolerance(self):
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )

        snapshot = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        # 1% difference in cost_basis should be tolerated
        reconstructed = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("14900")},
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True

    def test_extra_position_is_acceptable(self):
        """Positions closed between snapshot and history upload are fine."""
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )

        snapshot = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        reconstructed = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
            {"symbol": "TSLA", "quantity": Decimal("0"), "cost_basis": Decimal("0")},
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
```

### Step 2: Run tests to verify they fail

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_snapshot_validation.py -v
```

### Step 3: Implement the validation service

```python
# backend/app/services/brokers/ibkr/snapshot_validation_service.py
"""Validate reconstructed holdings against original IBKR snapshot data."""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

COST_BASIS_TOLERANCE = Decimal("0.02")  # 2% tolerance


def validate_against_snapshot(
    snapshot_positions: list[dict],
    reconstructed_holdings: list[dict],
) -> dict:
    """Compare reconstructed holdings against the original snapshot.

    Args:
        snapshot_positions: Original positions from synthetic import
            [{"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"}]
        reconstructed_holdings: Holdings from reconstruction
            [{"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")}]

    Returns:
        Validation result with is_valid flag and list of discrepancies
    """
    discrepancies = []

    # Build lookup from reconstructed holdings (skip zero-quantity)
    recon_map = {
        h["symbol"]: h
        for h in reconstructed_holdings
        if h.get("quantity", Decimal("0")) != Decimal("0")
    }

    for snap in snapshot_positions:
        symbol = snap["symbol"]
        snap_qty = Decimal(snap["quantity"])
        snap_cost = Decimal(snap["cost_basis"])

        if snap_qty == 0:
            continue

        recon = recon_map.get(symbol)

        if recon is None:
            discrepancies.append({
                "type": "missing_position",
                "symbol": symbol,
                "expected_quantity": str(snap_qty),
                "actual_quantity": "0",
                "message": f"{symbol}: position missing from reconstructed holdings "
                           f"(expected {snap_qty} shares). Likely missing historical files.",
            })
            continue

        recon_qty = recon["quantity"]
        recon_cost = recon["cost_basis"]

        # Quantity must match exactly
        if recon_qty != snap_qty:
            discrepancies.append({
                "type": "quantity_mismatch",
                "symbol": symbol,
                "expected_quantity": str(snap_qty),
                "actual_quantity": str(recon_qty),
                "message": f"{symbol}: expected {snap_qty} shares, "
                           f"reconstructed {recon_qty}. Likely missing historical files.",
            })
            continue

        # Cost basis should be within tolerance
        if snap_cost != Decimal("0"):
            diff_ratio = abs(recon_cost - snap_cost) / abs(snap_cost)
            if diff_ratio > COST_BASIS_TOLERANCE:
                discrepancies.append({
                    "type": "cost_basis_mismatch",
                    "symbol": symbol,
                    "expected_cost_basis": str(snap_cost),
                    "actual_cost_basis": str(recon_cost),
                    "diff_percent": str(round(diff_ratio * 100, 2)),
                    "message": f"{symbol}: cost basis differs by {round(diff_ratio * 100, 1)}% "
                               f"(expected {snap_cost}, got {recon_cost}).",
                })

    is_valid = not any(
        d["type"] in ("missing_position", "quantity_mismatch") for d in discrepancies
    )

    return {
        "is_valid": is_valid,
        "discrepancies": discrepancies,
        "positions_checked": len([s for s in snapshot_positions if Decimal(s["quantity"]) != 0]),
        "positions_matched": len([s for s in snapshot_positions if Decimal(s["quantity"]) != 0])
        - len([d for d in discrepancies if d["type"] in ("missing_position", "quantity_mismatch")]),
    }
```

### Step 4: Run tests

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_snapshot_validation.py -v
```

### Step 5: Commit

```bash
git add backend/app/services/brokers/ibkr/snapshot_validation_service.py backend/tests/unit/test_snapshot_validation.py
git commit -m "feat: add snapshot validation service for comparing reconstructed vs snapshot data"
```

---

## Task 7: Wire Validation into Finalize Endpoint

**Files:**
- Modify: `backend/app/routers/broker_data.py` (finalize endpoint)
- Modify: `backend/tests/unit/test_batch_upload.py` (add validation test)

### Step 1: Add validation to finalize endpoint

In the `finalize_batch_upload` endpoint, after reconstruction, add:

```python
    # Validate against snapshot data if available
    validation_result = None
    if synthetic_cleanup.get("snapshot_positions"):
        from app.services.brokers.ibkr.snapshot_validation_service import (
            validate_against_snapshot,
        )
        from app.services.portfolio.portfolio_reconstruction_service import (
            PortfolioReconstructionService,
        )

        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, latest, apply_ticker_changes=True
        )
        validation_result = validate_against_snapshot(
            synthetic_cleanup["snapshot_positions"], reconstructed
        )

        if not validation_result["is_valid"]:
            for d in validation_result["discrepancies"]:
                logger.warning("Snapshot validation: %s", d["message"])
```

Add `"validation": validation_result` to the response dict.

### Step 2: Run all tests

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/ -v
```

### Step 3: Commit

```bash
git add backend/app/routers/broker_data.py backend/tests/unit/test_batch_upload.py
git commit -m "feat: wire snapshot validation into batch finalize endpoint"
```

---

## Task 8: Integration Test -- Full API + Upload History Flow

Test the complete flow: API snapshot -> batch upload historical files -> validate.

**Files:**
- Create: `backend/tests/integration/test_synthetic_to_history_flow.py`

### Step 1: Write the integration test

```python
# backend/tests/integration/test_synthetic_to_history_flow.py
"""Integration test: synthetic snapshot -> historical upload -> validation."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models import Account, BrokerDataSource, Holding, Transaction


class TestSyntheticToHistoryFlow:
    """Full flow: snapshot import -> batch history upload -> synthetic cleanup -> validation."""

    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRFlexClient")
    @patch("app.services.brokers.ibkr.synthetic_import_service.IBKRParser")
    def test_snapshot_creates_synthetic_source_and_transactions(
        self, mock_parser, mock_client, db
    ):
        """Step 1: Snapshot import should create synthetic source and transactions."""
        from app.services.brokers.ibkr.synthetic_import_service import (
            IBKRSyntheticImportService,
        )

        # Create real account in DB
        account = Account(
            name="Test IBKR",
            institution="IBKR",
            account_type="Brokerage",
            currency="USD",
            broker_type="ibkr",
        )
        db.add(account)
        db.flush()

        mock_client.fetch_flex_report.return_value = b"<xml/>"
        mock_root = MagicMock()
        mock_parser.parse_xml.return_value = mock_root
        mock_parser.extract_positions.return_value = [
            {
                "symbol": "AAPL",
                "original_symbol": "AAPL",
                "description": "APPLE INC",
                "asset_category": "STK",
                "asset_class": "Stock",
                "listing_exchange": "NASDAQ",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
                "currency": "USD",
                "account_id": "U12345",
                "needs_validation": False,
                "cusip": None,
                "isin": None,
                "conid": None,
                "figi": None,
            },
        ]
        mock_parser.extract_cash_balances.return_value = []

        stats = IBKRSyntheticImportService.import_snapshot(
            db, account.id, "token", "query_id"
        )
        assert stats["status"] == "completed"

        # Verify synthetic source exists
        source = (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.account_id == account.id,
                BrokerDataSource.source_type == "synthetic",
            )
            .first()
        )
        assert source is not None
        assert source.import_stats["snapshot_positions"][0]["symbol"] == "AAPL"

        # Verify holding exists with correct quantity
        holding = (
            db.query(Holding)
            .filter(Holding.account_id == account.id)
            .first()
        )
        assert holding is not None
        assert holding.quantity == Decimal("100")

        # Verify synthetic transaction exists
        txn = (
            db.query(Transaction)
            .filter(Transaction.broker_source_id == source.id)
            .first()
        )
        assert txn is not None
        assert txn.type == "Buy"
        assert txn.quantity == Decimal("100")
        assert txn.notes == "Synthetic transaction from IBKR position snapshot"
```

### Step 2: Run integration test

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/integration/test_synthetic_to_history_flow.py -v
```

### Step 3: Commit

```bash
git add backend/tests/integration/test_synthetic_to_history_flow.py
git commit -m "test: add integration test for synthetic snapshot to history flow"
```

---

## Task 9: Lint and Run Full Test Suite

### Step 1: Lint

```bash
cd backend && ruff check --fix . && ruff format .
```

### Step 2: Run full test suite

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest -v
```

### Step 3: Fix any failures

Address any test failures or lint issues.

### Step 4: Commit fixes if any

```bash
git add -A
git commit -m "fix: lint and test fixes for synthetic snapshot feature"
```

---

## Summary of Changes

| Component | Change |
|-----------|--------|
| `BrokerDataSource` model | Document `source_type="synthetic"` |
| `IBKRSyntheticImportService` (new) | Create synthetic transactions from IBKR positions |
| `POST /api/brokers/ibkr/snapshot/{id}` (new) | Endpoint for synthetic snapshot import |
| Upload endpoint | `session_id` param for batch mode; auto-delete synthetic sources |
| `POST /api/broker-data/finalize-batch/{id}` (new) | Finalize batch upload with single reconstruction |
| `validate_against_snapshot()` (new) | Compare reconstructed holdings vs snapshot reference |
| Tests | Unit tests for each component + integration test for full flow |

## Frontend Tech Debt

The backend now supports synthetic snapshot import and batch uploads, but the frontend
still uses the old single-file-at-a-time flow. The following changes are needed.

### Key Frontend Files

| File | Role |
|------|------|
| `frontend/src/components/AccountWizard/index.jsx` | Main 5-step wizard orchestrator |
| `frontend/src/components/AccountWizard/steps/DataConnectionStep.jsx` | API connect / file upload tab |
| `frontend/src/components/AccountWizard/steps/FileUploadResultStep.jsx` | Import results display |
| `frontend/src/components/AccountWizard/constants/brokerConfig.js` | Broker config (credential fields, setup guides) |
| `frontend/src/pages/Accounts.jsx` | Account management page with import options |
| `frontend/src/lib/api.js` | Authenticated API client |

### FE-1: Add "Quick Start vs History" Choice to IBKR Wizard

**Where:** `DataConnectionStep.jsx` (or a new intermediate step in `index.jsx`)

After the user saves IBKR credentials (flex_token + flex_query_id), present a choice:

- **"Quick Start"** -- Calls `POST /api/brokers/ibkr/snapshot/{account_id}`. Creates synthetic
  transactions from current positions. User is immediately onboarded and can start tracking.
  Show a note: "You can upload historical files later from the account settings page."
- **"Upload History"** -- Existing file upload flow, but adapted for batch uploads (see FE-2).

This choice only appears for brokers that have API credentials configured. File-only users
skip straight to the upload flow.

**Backend endpoints involved:**
- `POST /api/brokers/ibkr/snapshot/{account_id}` (new -- calls synthetic import service)
- `POST /api/brokers/ibkr/test-credentials/{account_id}` (existing -- validate before snapshot)

### FE-2: Batch File Upload with Session ID

**Where:** `DataConnectionStep.jsx` file upload tab, `FileUploadResultStep.jsx`

Currently each file upload calls `POST /api/broker-data/upload/{account_id}` individually and
triggers reconstruction per file. The new flow:

1. Generate a `session_id` (UUID) client-side when the user starts uploading
2. Pass `session_id` as a form field with each upload -- the backend stages files without reconstruction
3. Show a running list of uploaded files with their date ranges and record counts
4. Display a combined coverage timeline so the user can see gaps
5. "Finalize Import" button calls `POST /api/broker-data/finalize-batch/{account_id}?session_id=...`
6. Show validation results if the user had a prior synthetic snapshot:
   - Green: "All positions match your current holdings"
   - Yellow: "Cost basis differs slightly for X positions (normal rounding differences)"
   - Red: "Missing data for Y positions -- you may need additional historical files"

**Backend endpoints involved:**
- `POST /api/broker-data/upload/{account_id}` (modified -- accepts `session_id` form field)
- `POST /api/broker-data/finalize-batch/{account_id}?session_id=...` (new)

**Response shape from finalize:**
```json
{
  "status": "completed",
  "sources_finalized": 3,
  "date_range": {"start_date": "2022-01-01", "end_date": "2024-12-31"},
  "synthetic_cleanup": {"deleted_sources": 1, "deleted_transactions": 5},
  "holdings_reconstruction": {"holdings_updated": 12},
  "validation": {
    "is_valid": true,
    "positions_checked": 8,
    "positions_matched": 8,
    "discrepancies": []
  }
}
```

### FE-3: "Upload History" Option on Existing Accounts

**Where:** `pages/Accounts.jsx` (the account card's import options)

For accounts that were onboarded via snapshot (synthetic data), show an "Upload History"
action on the account card. This opens the batch upload flow (FE-2) targeting that account.
After finalization, the synthetic data is auto-replaced by real historical data.

### FE-4: Broker Config Updates

**Where:** `brokerConfig.js`

Add a `supportsSnapshot: true` flag to the IBKR broker config. The wizard uses this to
conditionally show the Quick Start option. Other brokers remain unchanged.

```js
ibkr: {
  // ... existing fields ...
  supportsSnapshot: true,  // enables Quick Start flow
}
```

### FE-5: Coverage Visualization for Batch Uploads

**Where:** New component, used in FE-2 and `pages/Accounts.jsx`

A timeline bar showing date ranges covered by each uploaded file. Highlights gaps between
files so the user knows if they're missing a period. Uses the existing
`GET /api/broker-data/coverage/{account_id}` endpoint for data.

---

## Other Future Tasks

- Apply batch upload pattern to other brokers (Kraken, Binance, etc.)
- Airflow DAG changes to handle synthetic vs. real data
