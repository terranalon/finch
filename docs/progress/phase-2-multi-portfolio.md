# Phase 2: Multi-Portfolio Support Progress

## Status: Complete ✅

### Tasks Overview

| Task | Description | Status |
|------|-------------|--------|
| 7 | Backend Portfolio CRUD Router | ✅ Completed |
| 8 | Auto-create default portfolio on registration | ✅ Completed |
| 9 | Add portfolio_id filter to endpoints | ✅ Completed |
| 10 | Frontend PortfolioContext | ✅ Completed |
| 11 | Portfolio selector in Navbar | ✅ Completed |
| 12 | Portfolio management in Settings | ✅ Completed |
| 13 | UI Consistency & Polish | ✅ Completed |
| 14 | Add default_currency to Portfolio model | ✅ Completed |
| 15 | Add default portfolio preference | ✅ Completed |
| 16 | Make "All Portfolios" opt-in | ✅ Completed |
| 17 | Show portfolio values in selector dropdown | ✅ Completed |
| 18 | Create second demo portfolio with data | ✅ Completed |

### Additional Work Completed (2026-01-20)

| Item | Description | Status |
|------|-------------|--------|
| 19 | Frontend pages pass portfolio_id to all API calls | ✅ Completed |
| 20 | Pages use portfolio's default_currency | ✅ Completed |
| 21 | Portfolio modal for create/edit with description field | ✅ Completed |
| 22 | "Set as Default" button in Settings | ✅ Completed |
| 23 | Transaction view endpoints support portfolio_id | ✅ Completed |
| 24 | Israeli portfolio historical data & daily movers | ✅ Completed |
| 25 | S&P 500 benchmark chart interpolation fix | ✅ Completed |
| 26 | "Show All Portfolios" toggle in Settings | ✅ Completed |

---

## Completed Tasks

### Task 7: Backend Portfolio CRUD Router (2026-01-19)

**Files Created:**
- `backend/app/schemas/portfolio.py` - Pydantic schemas for Portfolio
  - `PortfolioBase`, `PortfolioCreate`, `PortfolioUpdate`
  - `Portfolio`, `PortfolioWithAccountCount`
- `backend/app/routers/portfolios.py` - CRUD endpoints
  - `GET /api/portfolios` - List user's portfolios with account counts
  - `POST /api/portfolios` - Create new portfolio
  - `GET /api/portfolios/{id}` - Get single portfolio
  - `PUT /api/portfolios/{id}` - Update portfolio name/description
  - `DELETE /api/portfolios/{id}` - Delete portfolio (validation: not last, no accounts)

**Files Modified:**
- `backend/app/main.py` - Registered portfolios router
- `backend/app/schemas/__init__.py` - Exported portfolio schemas

### Task 8: Auto-create Default Portfolio on Registration (2026-01-19)

**Files Modified:**
- `backend/app/routers/auth.py`
  - Added Portfolio import
  - After creating user, creates "My Portfolio" with description "Default portfolio"
  - Ensures new users have a portfolio to add accounts to

---

### Task 9: Add portfolio_id Filter to Endpoints (2026-01-19)

**Files Modified:**
- `backend/app/dependencies/user_scope.py`
  - Updated `get_user_account_ids()` to accept optional `portfolio_id` parameter
  - Added `validate_user_portfolio()` helper function

**Endpoints Updated:**
- [x] `GET /api/accounts` (accounts.py)
- [x] `GET /api/holdings` (holdings.py)
- [x] `GET /api/dashboard/summary` (dashboard.py)
- [x] `GET /api/positions` (positions.py)
- [x] `GET /api/transactions` (transactions.py)
- [x] `GET /api/snapshots/portfolio` (snapshots.py)

### Task 10: Frontend PortfolioContext (2026-01-19)

**Files Created:**
- `frontend/src/contexts/PortfolioContext.jsx`
  - Fetches portfolios from `/api/portfolios` on mount
  - Stores `selectedPortfolioId` (null = all portfolios)
  - Persists to localStorage key `finch-portfolio-id`
  - Provides hook: `usePortfolio()` with portfolios, selectedPortfolioId, selectedPortfolio, selectPortfolio(), refetchPortfolios()

**Files Modified:**
- `frontend/src/contexts/index.js` - Export PortfolioProvider and usePortfolio
- `frontend/src/App.jsx` - Added PortfolioProvider inside AuthProvider

### Task 11: Portfolio Selector in Navbar (2026-01-19)

**Files Modified:**
- `frontend/src/components/layout/Navbar.jsx`
  - Added BriefcaseIcon, CheckIcon SVG components
  - Added PortfolioSelector dropdown component
  - Dropdown shows "All Portfolios" + list of user portfolios with account counts
  - Selected portfolio indicated with checkmark
  - Added to right side actions before ThemeToggle

### Task 12: Portfolio Management in Settings (2026-01-19)

**Files Modified:**
- `frontend/src/pages/Settings.jsx`
  - Added imports: api, usePortfolio
  - Added FolderIcon, PencilIcon, TrashIcon, PlusIcon SVG components
  - Added PortfolioManagement component with:
    - List of portfolios showing name + account count
    - Inline rename with pencil icon button
    - Delete button (only shown if >1 portfolio and 0 accounts)
    - "Create New Portfolio" button with inline form
    - Keyboard support (Enter to submit, Escape to cancel)
    - Error handling with dismissible alerts
  - Added PortfolioManagement after Profile section

---

## Verification Checklist

1. **After Task 7-8:**
   - [x] Test CRUD via API docs at `/docs`
   - [x] Register new user and verify default portfolio created

2. **After Task 9:**
   - [x] Test filtering with `?portfolio_id=<id>` parameter
   - [x] Verify unauthorized portfolio IDs return empty results

3. **After Task 10-11:**
   - [x] Portfolio selector appears in navbar
   - [x] Selection persists on refresh (localStorage)

4. **After Task 12:**
   - [x] Can create new portfolios in Settings
   - [x] Can rename portfolios
   - [x] Cannot delete last portfolio or portfolio with accounts

5. **After Task 13-18:**
   - [x] Icons consistent (BriefcaseIcon) in navbar and settings
   - [x] Portfolio selector has visible background/border
   - [x] Portfolio values shown in dropdown
   - [x] Demo user has two portfolios (US Investments, Israeli Savings)

## End-to-End Test

1. ✅ Register new user -> default portfolio created
2. ✅ Create second portfolio in Settings
3. ✅ Add account to second portfolio
4. ✅ Switch between portfolios in navbar
5. ✅ Verify data filters correctly on all pages

---

## Completed Tasks (13-18)

### Task 13: UI Consistency & Polish (2026-01-19)

**Changes Made:**
- Changed `FolderIcon` to `BriefcaseIcon` in Settings.jsx for consistency with Navbar
- Added background/border styling to portfolio selector button in Navbar

**Files Modified:**
- `frontend/src/components/layout/Navbar.jsx` - Added `bg-[var(--bg-secondary)] border border-[var(--border-primary)]` to selector button
- `frontend/src/pages/Settings.jsx` - Replaced FolderIcon with BriefcaseIcon

---

### Task 14: Add default_currency to Portfolio Model (2026-01-19)

**Changes Made:**
- Added `default_currency` field to Portfolio model (String(3), default "USD")
- Updated portfolio schemas with validation
- Migration created for new column

**Files Modified:**
- `backend/app/models/portfolio.py` - Added `default_currency` column
- `backend/app/schemas/portfolio.py` - Added to PortfolioBase with validation
- `backend/alembic/versions/add_portfolio_preferences.py` - Combined migration

---

### Task 15: Add Default Portfolio Preference (2026-01-19)

**Changes Made:**
- Added `is_default` field to Portfolio model (Boolean, default False)
- Created `PUT /api/portfolios/{id}/set-default` endpoint
- Automatically unsets previous default when setting new one
- Registration now creates portfolio with `is_default=True`

**Files Modified:**
- `backend/app/models/portfolio.py` - Added `is_default` column
- `backend/app/schemas/portfolio.py` - Added to response schemas
- `backend/app/routers/portfolios.py` - Added set-default endpoint
- `backend/app/routers/auth.py` - Sets is_default=True on registration

**Note:** Frontend UI for setting default portfolio in Settings not yet implemented (backend ready)

---

### Task 16: Make "All Portfolios" Opt-in (2026-01-19)

**Changes Made:**
- Added `show_combined_view` field to User model (Boolean, default True)
- Included in `/auth/me` response

**Files Modified:**
- `backend/app/models/user.py` - Added `show_combined_view` column
- `backend/app/schemas/auth.py` - Added to UserInfo schema
- `backend/alembic/versions/add_portfolio_preferences.py` - Combined migration

**Note:** Frontend UI for toggling preference in Settings not yet implemented (backend ready)

---

### Task 17: Show Portfolio Values in Selector Dropdown (2026-01-19)

**Changes Made:**
- Added `include_values=true` query parameter to `/api/portfolios`
- Created `_calculate_portfolio_value()` helper function in portfolios router
- Calculates total holdings value, converts to portfolio's default_currency
- Frontend displays formatted currency values in dropdown

**Files Modified:**
- `backend/app/routers/portfolios.py` - Added value calculation logic
- `backend/app/schemas/portfolio.py` - Added `total_value: float | None` to PortfolioWithAccountCount
- `frontend/src/contexts/PortfolioContext.jsx` - Fetches with `include_values=true`
- `frontend/src/components/layout/Navbar.jsx` - Displays values using Intl.NumberFormat

---

### Task 18: Create Second Demo Portfolio with Data (2026-01-19)

**Changes Made:**
- Renamed default portfolio from "Demo Portfolio" to "US Investments"
- Created "Israeli Savings" portfolio with ILS currency
- Added Israeli assets: TEVA.TA, NICE.TA, LUMI.TA, POLI.TA
- Created two accounts: "Bank Leumi Brokerage", "Gemel Pension"
- Added sample holdings and transactions

**Files Modified:**
- `backend/scripts/seed_demo_user.py` - Added `ISRAELI_HOLDINGS_DATA` and `add_israeli_portfolio_to_existing_demo()` function

**Demo User Portfolios:**
| Portfolio | Currency | Accounts | Value |
|-----------|----------|----------|-------|
| US Investments | USD | 2 | $43,310.50 |
| Israeli Savings | ILS | 2 | ₪0* |

*Israeli stocks need price fetching to show values

---

## Remaining Work

All Phase 2 tasks completed!

---

## Completed Enhancements (2026-01-20)

### Task 19-25: Bug Fixes & Polish

**Frontend Portfolio Filtering (Task 19):**
- All pages now pass `portfolio_id` to API calls when a specific portfolio is selected
- Files modified: `Accounts.jsx`, `Holdings.jsx`, `Overview.jsx`, `Activity.jsx`, `Assets.jsx`

**Portfolio Currency Support (Task 20):**
- Added `portfolioCurrency` to PortfolioContext
- Overview and Accounts pages use portfolio's default_currency when viewing a specific portfolio
- Files modified: `PortfolioContext.jsx`, `Overview.jsx`, `Accounts.jsx`

**Portfolio Modal (Task 21):**
- Created `PortfolioModal` component for create/edit operations
- Includes name, default_currency dropdown, and description fields
- Replaced inline editing with cleaner modal UX
- Files modified: `Settings.jsx`

**Set as Default Button (Task 22):**
- Added "Set as Default" text button for non-default portfolios
- Default portfolio shows star icon and "Default" badge
- Files modified: `Settings.jsx`

**Transaction View Endpoints (Task 23):**
- Added `portfolio_id` parameter to all transaction view endpoints:
  - `GET /api/transactions/trades`
  - `GET /api/transactions/dividends`
  - `GET /api/transactions/forex`
  - `GET /api/transactions/cash`
- Files modified: `transaction_views.py`

**Israeli Portfolio Data (Task 24):**
- Added varied price history for Israeli stocks (day change calculation)
- Added ILS cash holdings to Migdal Pension account
- Generated historical snapshots for Israeli Savings portfolio
- Files modified: Database seeding scripts

**Benchmark Chart Fix (Task 25):**
- Fixed S&P 500 benchmark line gaps on 1M/3M timeframes
- `getBenchmarkValue()` now interpolates for weekends/holidays and uses first available date for early range
- Files modified: `Overview.jsx`

**Show All Portfolios Toggle (Task 26):**
- Added toggle in Settings Preferences section for "Show All Portfolios option"
- Created `UserPreferencesUpdate` schema and `PUT /auth/me` endpoint for updating user preferences
- Added `updatePreferences` function to AuthContext for updating user settings
- PortfolioContext respects `user.show_combined_view` preference
- When disabled, "All Portfolios" option hidden from portfolio selector
- Auto-switches to default portfolio when user disables combined view while viewing "All Portfolios"
- Files modified: `AuthContext.jsx`, `PortfolioContext.jsx`, `Settings.jsx`, `auth.py` (schemas & router)
