# IBKR Positions Import Fix - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove direct positions-to-holdings import from IBKR, ensuring holdings are always derived from transactions via reconstruction.

**Architecture:** IBKR import currently writes positions directly to holdings, bypassing the transaction-replay architecture. This fix removes that code path and adds a reconstruction call after importing transactions. The Israeli import service has dead positions code that should also be cleaned up.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest

**Branch:** `fix/ibkr-positions-import-bypass`

---

## Task 1: Remove `_import_positions` from IBKR Import Service

**Files:**
- Modify: `backend/app/services/brokers/ibkr/import_service.py`

**Step 1: Remove `_import_positions` method**

Delete the entire `_import_positions` method (lines 29-153). This method directly writes `quantity` and `cost_basis` to holdings from IBKR positions data, bypassing transaction replay.

**Step 2: Remove `_mark_stale_holdings_inactive` method**

Delete the entire `_mark_stale_holdings_inactive` method (lines 488-534). Reconstruction will handle marking holdings as inactive when they have zero quantity.

**Step 3: Run linting**

```bash
cd backend && ruff check --fix app/services/brokers/ibkr/import_service.py && ruff format app/services/brokers/ibkr/import_service.py
```

**Step 4: Verify no syntax errors**

```bash
cd backend && python -c "from app.services.brokers.ibkr.import_service import IBKRImportService; print('OK')"
```

Expected: `OK`

**Step 5: Run code-simplifier agent**

Use the code-simplifier agent on `backend/app/services/brokers/ibkr/import_service.py` to clean up any remaining issues.

**Step 6: Commit**

```bash
git add backend/app/services/brokers/ibkr/import_service.py
git commit -m "refactor(ibkr): remove _import_positions and _mark_stale_holdings_inactive

These methods directly wrote to holdings, bypassing transaction replay.
Holdings should be derived from transactions via reconstruction."
```

---

## Task 2: Update IBKR Flex Import Service

**Files:**
- Modify: `backend/app/services/brokers/ibkr/flex_import_service.py`

**Step 1: Remove positions import calls from `import_all` method**

In the `import_all` method, remove these lines (around lines 120-123):

```python
# Step 4: Import positions
logger.info("Importing positions...")
pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
stats["positions"] = pos_stats
```

**Step 2: Add reconstruction call to `import_all` method**

After all transaction imports and before the commit (around line 170), add:

```python
# Step 10: Reconstruct holdings from transactions
logger.info("Reconstructing holdings from transactions...")
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings
reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
stats["holdings_reconstruction"] = reconstruction_stats
```

**Step 3: Remove positions import calls from `import_historical` method**

In the `import_historical` method, remove these lines (around lines 314-316):

```python
# Step 5: Import positions
logger.info("Importing positions...")
pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
stats["positions"] = pos_stats
```

**Step 4: Add reconstruction call to `import_historical` method**

After all transaction imports and before the commit (around line 354), add:

```python
# Step 11: Reconstruct holdings from transactions
logger.info("Reconstructing holdings from transactions...")
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings
reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
stats["holdings_reconstruction"] = reconstruction_stats
```

**Step 5: Run linting**

```bash
cd backend && ruff check --fix app/services/brokers/ibkr/flex_import_service.py && ruff format app/services/brokers/ibkr/flex_import_service.py
```

**Step 6: Verify no syntax errors**

```bash
cd backend && python -c "from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService; print('OK')"
```

Expected: `OK`

**Step 7: Run code-simplifier agent**

Use the code-simplifier agent on `backend/app/services/brokers/ibkr/flex_import_service.py` to clean up any remaining issues.

**Step 8: Commit**

```bash
git add backend/app/services/brokers/ibkr/flex_import_service.py
git commit -m "refactor(ibkr): replace positions import with holdings reconstruction

- Remove direct positions import in import_all and import_historical
- Add reconstruction call to derive holdings from transactions
- Holdings are now always calculated from transaction history"
```

---

## Task 3: Update Broker Data Router (File Upload Endpoint)

**Files:**
- Modify: `backend/app/routers/broker_data.py`

**Step 1: Remove positions import and stale cleanup from IBKR upload section**

In the `upload_broker_file` function, find the IBKR section (around lines 413-450) and remove:

```python
pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)

# Mark stale holdings as inactive (positions we had before but not in current data)
stale_stats = IBKRImportService._mark_stale_holdings_inactive(
    db, account_id, current_symbols
)
```

Also remove `current_symbols` variable since it's no longer needed:

```python
# Get current position symbols for stale holdings cleanup
current_symbols = {pos["symbol"] for pos in positions_data}
```

**Step 2: Add reconstruction call after all transaction imports**

After all the transaction imports (after `div_cash_stats`) and before the validation section, add:

```python
# Reconstruct holdings from transactions
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings
reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
```

**Step 3: Update import_stats to remove positions/stale_cleanup and add reconstruction**

Change the `source.import_stats` dictionary:

Remove:
```python
"positions": pos_stats,
"stale_cleanup": stale_stats,
```

Add:
```python
"holdings_reconstruction": reconstruction_stats,
```

**Step 4: Run linting**

```bash
cd backend && ruff check --fix app/routers/broker_data.py && ruff format app/routers/broker_data.py
```

**Step 5: Verify no syntax errors**

```bash
cd backend && python -c "from app.routers.broker_data import router; print('OK')"
```

Expected: `OK`

**Step 6: Run code-simplifier agent**

Use the code-simplifier agent on `backend/app/routers/broker_data.py` to clean up any remaining issues.

**Step 7: Commit**

```bash
git add backend/app/routers/broker_data.py
git commit -m "refactor(broker-data): use reconstruction for IBKR file uploads

- Remove positions import and stale holdings cleanup
- Add holdings reconstruction after transaction imports
- Validation still compares reconstructed vs IBKR positions"
```

---

## Task 4: Clean Up Israeli Import Service

**Files:**
- Modify: `backend/app/services/brokers/shared/israeli_import_service.py`

**Step 1: Remove `_import_positions` method**

Delete the entire `_import_positions` method (lines 152-236). This is dead code - never called because Meitav only uploads transaction files, not balance files.

**Step 2: Remove positions import call from `import_data` method**

Remove these lines from `import_data` (around lines 113-115):

```python
# Import positions
if data.positions:
    stats["positions"] = self._import_positions(account_id, data.positions)
```

**Step 3: Remove "positions" from stats initialization**

In the stats dictionary initialization (around line 99), remove:

```python
"positions": {},
```

**Step 4: Run linting**

```bash
cd backend && ruff check --fix app/services/brokers/shared/israeli_import_service.py && ruff format app/services/brokers/shared/israeli_import_service.py
```

**Step 5: Verify no syntax errors**

```bash
cd backend && python -c "from app.services.brokers.shared.israeli_import_service import IsraeliSecuritiesImportService; print('OK')"
```

Expected: `OK`

**Step 6: Run code-simplifier agent**

Use the code-simplifier agent on `backend/app/services/brokers/shared/israeli_import_service.py` to clean up any remaining issues.

**Step 7: Commit**

```bash
git add backend/app/services/brokers/shared/israeli_import_service.py
git commit -m "refactor(israeli): remove dead _import_positions code

Meitav only uploads transaction files, so positions import was never called.
Holdings are derived from transactions via reconstruction."
```

---

## Task 5: Run Tests and Verify

**Step 1: Run existing IBKR tests**

```bash
cd backend && python -m pytest tests/ -k "ibkr" -v
```

Expected: All tests pass (some may need updates if they test `_import_positions`)

**Step 2: Run broker data router tests**

```bash
cd backend && python -m pytest tests/ -k "broker" -v
```

**Step 3: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v --tb=short
```

**Step 4: Fix any failing tests**

If tests fail because they explicitly test `_import_positions`, update them to test reconstruction instead.

**Step 5: Run code-simplifier agent on any modified test files**

If tests were modified, run code-simplifier agent on those files.

**Step 6: Commit test fixes if any**

```bash
git add -A
git commit -m "test: update tests for positions import removal" --allow-empty
```

---

## Task 6: Integration Test - Manual Verification

**Step 1: Start the backend**

```bash
docker compose up -d
```

**Step 2: Check container health**

```bash
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

**Step 3: Verify reconstruction endpoint works**

Test that reconstruction can fix orphaned holdings (like SLV):

```bash
# Check current state of holdings for account with orphan
docker compose exec -T postgres psql -U portfolio_user -d portfolio_tracker -c "
SELECT h.id, h.quantity, a.symbol,
       (SELECT COUNT(*) FROM transactions t WHERE t.holding_id = h.id) as txn_count
FROM holdings h
JOIN assets a ON h.asset_id = a.id
WHERE h.quantity > 0 AND h.account_id = 45
ORDER BY a.symbol;
"
```

---

## Task 7: Final Commit and PR Preparation

**Step 1: Review all changes**

```bash
git diff main --stat
```

**Step 2: Final lint check**

```bash
cd backend && ruff check . && ruff format --check .
```

**Step 3: Create summary commit if needed**

If there are uncommitted changes:

```bash
git add -A
git commit -m "chore: final cleanup for IBKR positions fix"
```

**Step 4: Push branch**

```bash
git push -u origin fix/ibkr-positions-import-bypass
```

---

## Post-Implementation Notes

After merging this fix:

1. **Re-import IBKR files** for affected accounts to get correct transaction-based holdings
2. **Or run reconstruction** via API: `POST /api/holdings/reconstruct/{account_id}`
3. The orphaned SLV holding (and any similar cases) will be zeroed out since they have no backing transactions
