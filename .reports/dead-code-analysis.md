# Dead Code Cleanup Report

**Date:** 2026-01-26
**Branch:** `cleanup/dead-code-removal`

## Summary

Removed 19 dead code files totaling approximately **2,045 lines** of code, plus one unused npm dependency.

## Test Results

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Tests Passed | 367 | 367 | No regression |
| Tests Failed | 17 | 17 | Pre-existing |
| Test Errors | 27 | 27 | Pre-existing |

## Files Deleted

### Backend Service Files (2 files, ~409 lines)

| File | Description |
|------|-------------|
| `backend/app/services/ibkr_web_client.py` | Experimental IBKR web API client (never integrated) |
| `backend/app/services/ibkr_web_parser.py` | IBKR web response parser (never integrated) |

### Backend Obsolete Scripts (14 files, ~927 lines)

#### One-Time Data Fix Scripts (Already Executed)
| File | Description |
|------|-------------|
| `backend/delete_duplicate_forex.py` | Fixed duplicate forex transactions |
| `backend/delete_stk_forex.py` | Removed STK forex duplicates |
| `backend/reset_forex.py` | Deleted all forex for re-import |
| `backend/reset_kraken.py` | Reset Kraken account data |
| `backend/prepare_reimport.py` | Prep script for re-importing trades |

#### Asset-Specific Debug Scripts (Investigation Complete)
| File | Description |
|------|-------------|
| `backend/check_raw_baby.py` | BABY token ledger investigation |
| `backend/check_raw_strk.py` | STRK token ledger investigation |
| `backend/check_strk.py` | STRK transactions check |
| `backend/check_btc.py` | BTC transactions check |
| `backend/analyze_ils_conversions.py` | ILS conversion investigation |
| `backend/analyze_cash.py` | Cash discrepancy analysis |

#### Demo/Test Scripts (Not Real Tests)
| File | Description |
|------|-------------|
| `backend/test_import.py` | Manual Kraken import test with hardcoded account ID |
| `backend/test_portfolio_value.py` | Manual portfolio value check |
| `backend/test_corporate_actions.py` | Demo script showing corporate actions feature |

### Frontend Files (2 files, ~705 lines)

| File | Description |
|------|-------------|
| `frontend/src/components/Navbar.jsx` | Old navbar, replaced by `Layout/Navbar.jsx` |
| `frontend/src/pages/Positions.jsx` | Orphaned page with no route, replaced by `Holdings.jsx` |

### Infrastructure (0 files)

The `airflow/docker-compose.override.yml.bak` was already ignored by `.gitignore` (`*.bak` pattern).

## Dependencies Removed

| Package | Location | Reason |
|---------|----------|--------|
| `@heroicons/react` | frontend/package.json | Zero imports found; all icons are inline SVGs |

## Minor Cleanups

### Unused React Imports Removed (4 files)

| File | Change |
|------|--------|
| `frontend/src/pages/Insights.jsx` | `import React, { useState }` -> `import { useState }` |
| `frontend/src/pages/Settings.jsx` | `import React, { useState, useEffect }` -> `import { useState, useEffect }` |
| `frontend/src/pages/Activity.jsx` | `import React, { useState, ... }` -> `import { useState, ... }` |
| `frontend/src/pages/Accounts.jsx` | `import React, { useState, useEffect }` -> `import { useState, useEffect }` |

### .gitignore Updates

Added pattern to ignore user broker data uploads:
```
backend/data/broker_uploads/*/
```

## Commits

| Hash | Message |
|------|---------|
| 1ec01d9 | chore: remove unused ibkr_web_client and ibkr_web_parser |
| 3b43b89 | chore: remove obsolete backend debug and data-fix scripts |
| a10e69b | chore: remove orphaned Navbar.jsx, Positions.jsx, and @heroicons/react |
| 08b6962 | refactor: remove unused React imports |
| 1e50985 | chore: add broker_uploads to .gitignore |

## Scripts Intentionally Kept

These scripts remain useful for ongoing maintenance:

- `validate_reconstruction.py` - Validates reconstruction accuracy vs IBKR
- `validate_vs_ibkr_live.py` - Live validation against IBKR API
- `check_holdings.py` - General holdings comparison utility
- `check_deposits.py` - Deposit tracking utility
- `check_forex.py` - Forex transaction review
- `check_ibkr_cash_txns.py` - IBKR cash transaction analysis
- `check_missing_settlements.py` - Find missing trade settlements
- `debug_kraken.py` - Kraken debugging utility
- `backfill_*.py` (all 8 files) - Data backfill utilities
- `import_*.py` (all 3 files) - Historical data import
- `record_cep_xxi_merger.py` - Corporate action recording
- `fix_etf_classification.py` - ETF classification fixes
- `update_asset_names.py` - Asset name updates

## Items Deferred

1. **Script Organization** - 35 root-level scripts in `backend/` could be organized into `backend/scripts/` subdirectories. Skipped because scripts may have hardcoded paths and require individual testing.

2. **Unused showModal State** - `Transactions.jsx` has `showModal` state marked "kept for future use". Left as-is per intentional design.
