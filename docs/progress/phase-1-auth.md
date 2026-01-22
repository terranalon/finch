# Phase 1: Authentication & Multi-Tenancy Progress

## Status: 🔄 In Progress (Backend Complete, Frontend Pending)

### Backend Tasks (Complete)

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add auth dependencies | ✅ Complete |
| 2 | Create User model | ✅ Complete |
| 3 | Create Session model | ✅ Complete |
| 4 | Create Portfolio model | ✅ Complete |
| 5 | Create AuthService | ✅ Complete |
| 6 | Create Auth Router | ✅ Complete |
| 7 | Create Auth Dependency | ✅ Complete |
| 8 | Create Database Migration | ✅ Complete |
| 9 | Add Google OAuth Endpoints | 🔄 Deferred |
| 10 | Create Demo User Seeding Script | ✅ Complete |
| 11 | Migrate Account Model to Portfolio | ✅ Complete |
| 12 | Create Data Migration Script | ✅ Complete |
| 13 | Update Routers with Auth | ✅ Complete |

### Frontend Tasks (Pending)

| Task | Description | Status |
|------|-------------|--------|
| 14 | Create API Client (`frontend/src/lib/api.js`) | ⏳ Pending |
| 15 | Create AuthContext | ⏳ Pending |
| 16 | Create Login Page | ⏳ Pending |
| 17 | Create Register Page | ⏳ Pending |
| 18 | Create ProtectedRoute Component | ⏳ Pending |
| 19 | Update App.jsx with Auth | ⏳ Pending |
| 20 | Refactor Pages to Use API Client | ⏳ Pending |
| 21 | Add /auth/me Endpoint (Backend) | ⏳ Pending |

## Planning Summary (2026-01-18)

**Key Decisions:**
- **Task 9 (Google OAuth):** Deferred until after data migration
- **Task 11 (Migration Strategy):** Option A - Add `portfolio_id`, keep `entity_id` temporarily
- **Auth Requirement:** All data endpoints require authentication from start
- **Demo User:** Real user in database (`demo@finch.com`) with sample data

**Detailed TDD plans added to:** `docs/plans/2026-01-18-finch-mvp-implementation.md`

### Task 10: Create Demo User Seeding Script (2026-01-18)
- Created `backend/scripts/__init__.py`
- Created `backend/scripts/seed_demo_user.py` with:
  - `create_demo_user()` function
  - Creates `demo@finch.com` user with "Demo Portfolio"
  - Idempotent (returns existing if already created)
- Created `backend/tests/test_seed_demo_user.py` with 2 tests

### Task 11: Migrate Account Model to Portfolio (2026-01-18)
- Modified `backend/app/models/account.py`:
  - Added `portfolio_id` column (nullable, FK to portfolios)
  - Made `entity_id` nullable (was required)
  - Added `portfolio` relationship
  - Added index on `portfolio_id`
- Modified `backend/app/models/portfolio.py`:
  - Added `accounts` relationship
- Created `backend/alembic/versions/add_portfolio_to_account.py` migration
- Created `backend/tests/test_account_portfolio.py` with 2 tests

### Task 12: Create Data Migration Script (2026-01-18)
- Created `backend/scripts/migrate_entities_to_portfolios.py` with:
  - Creates migration user (`migrated@finch.local`)
  - For each Entity, creates Portfolio with same name
  - Links accounts to portfolios via `portfolio_id`
  - Idempotent (safe to run multiple times)
- Created `backend/tests/test_entity_migration.py` with 4 tests

### Task 13: Update Routers with Auth (2026-01-19)
- Created `backend/app/dependencies/user_scope.py` with:
  - `get_user_portfolio_ids()` - returns user's portfolio IDs
  - `get_user_account_ids()` - returns user's account IDs
- Updated all data routers with `get_current_user` dependency
- Added user-scoped filtering to all queries

**Routers updated with auth:**
- `accounts.py` - All 5 endpoints (list, get, create, update, delete)
- `holdings.py` - All 5 endpoints (list, get, create, update, delete, reconstruct)
- `dashboard.py` - 2 endpoints (summary with auth, benchmark without)
- `transactions.py` - All 5 endpoints (list, get, create, update, delete)
- `transaction_views.py` - All 4 endpoints (trades, dividends, forex, cash)
- `positions.py` - 1 endpoint (list)
- `snapshots.py` - All 6 endpoints (create, account, portfolio, validate, value, backfill)
- `broker_data.py` - 3 endpoints (upload, coverage, delete)
- `ibkr.py` - All 4 endpoints (import-flex, import-auto, import-historical, import-from-file)

**Shared data routers (no auth needed):**
- `assets.py` - Shared asset catalog (all users see same assets)
- `prices.py` - Market prices (public data)

- Created `backend/tests/test_protected_routes.py` with 4 tests
- Fixed deprecated `regex` → `pattern` in Query parameters

## Completed Tasks

### Task 1: Add Authentication Dependencies (2026-01-18)
- Added bcrypt, PyJWT, authlib, httpx, email-validator to `backend/pyproject.toml`
- Added auth config (JWT settings, Google OAuth) to `backend/app/config.py`
- Added hatch build config to fix wheel packaging
- Ran `uv sync --extra dev` to install dependencies

### Task 2: Create User Model (2026-01-18)
- Created `backend/app/models/user.py` with email/password and Google OAuth fields
- Created `backend/tests/test_user_model.py` with 3 tests
- Updated `backend/app/models/__init__.py` to export User

### Task 3: Create Session Model (2026-01-18)
- Created `backend/app/models/session.py` for JWT refresh token management
- Created `backend/tests/test_session_model.py` with 2 tests
- Includes cascade delete when user is deleted

### Task 4: Create Portfolio Model (2026-01-18)
- Created `backend/app/models/portfolio.py` for grouping accounts per user
- Created `backend/tests/test_portfolio_model.py` with 3 tests
- Relationships: User 1:Many Portfolio 1:Many Account (future)

### Task 5: Create AuthService (2026-01-18)
- Created `backend/app/services/auth_service.py` with:
  - Password hashing (bcrypt)
  - Token hashing (SHA-256 for long tokens)
  - JWT access/refresh token creation
  - Token verification
- Created `backend/tests/test_auth_service.py` with 7 tests

### Task 6: Create Auth Router (2026-01-18)
- Created `backend/app/schemas/auth.py` with request/response models
- Created `backend/app/routers/auth.py` with endpoints:
  - POST /api/auth/register
  - POST /api/auth/login
  - POST /api/auth/refresh
  - POST /api/auth/logout
- Registered router in `backend/app/main.py`
- Created `backend/tests/test_auth_router.py` with 8 tests

### Task 7: Create Auth Dependency (2026-01-18)
- Created `backend/app/dependencies/__init__.py`
- Created `backend/app/dependencies/auth.py` with:
  - `get_current_user` - JWT token validation
  - `get_current_user_optional` - for routes that work with/without auth
- Created `backend/tests/test_auth_dependency.py` with 4 tests

## Test Summary

**Total: 37+ tests passing**
- User model: 3 tests
- Session model: 2 tests
- Portfolio model: 3 tests
- Auth service: 7 tests
- Auth router: 8 tests
- Auth dependency: 4 tests
- Seed demo user: 2 tests
- Account portfolio: 2 tests
- Entity migration: 4 tests
- Protected routes: 4 tests

## Files Created/Modified

### New Files
- `backend/app/models/user.py`
- `backend/app/models/session.py`
- `backend/app/models/portfolio.py`
- `backend/app/services/auth_service.py`
- `backend/app/schemas/auth.py`
- `backend/app/routers/auth.py`
- `backend/app/dependencies/__init__.py`
- `backend/app/dependencies/auth.py`
- `backend/app/dependencies/user_scope.py`
- `backend/alembic/versions/add_auth_tables.py`
- `backend/alembic/versions/add_portfolio_to_account.py`
- `backend/scripts/__init__.py`
- `backend/scripts/seed_demo_user.py`
- `backend/scripts/migrate_entities_to_portfolios.py`
- `backend/tests/test_user_model.py`
- `backend/tests/test_session_model.py`
- `backend/tests/test_portfolio_model.py`
- `backend/tests/test_auth_service.py`
- `backend/tests/test_auth_router.py`
- `backend/tests/test_auth_dependency.py`
- `backend/tests/test_seed_demo_user.py`
- `backend/tests/test_account_portfolio.py`
- `backend/tests/test_entity_migration.py`
- `backend/tests/test_protected_routes.py`

### Modified Files
- `backend/pyproject.toml` - added auth dependencies
- `backend/app/config.py` - added JWT and Google OAuth settings
- `backend/app/models/__init__.py` - export new models
- `backend/app/models/account.py` - added portfolio_id column
- `backend/app/main.py` - register auth router
- `backend/app/routers/accounts.py` - added auth
- `backend/app/routers/holdings.py` - added auth
- `backend/app/routers/dashboard.py` - added auth
- `backend/app/routers/transactions.py` - added auth
- `backend/app/routers/transaction_views.py` - added auth
- `backend/app/routers/positions.py` - added auth
- `backend/app/routers/snapshots.py` - added auth
- `backend/app/routers/broker_data.py` - added auth
- `backend/app/routers/ibkr.py` - added auth

---

## Next Steps

### Backend Finalization (Tasks 1-13 Complete)

1. **Run Alembic migration:** `cd backend && alembic upgrade head`
2. **Run data migration:** Execute `migrate_entities_to_portfolios.py`
3. **Seed demo user (optional):** Execute `seed_demo_user.py`

### Frontend Authentication (Tasks 14-21 Pending)

**Implementation Plan:** `docs/plans/2026-01-18-finch-mvp-implementation.md` (see "Frontend Authentication Tasks" section)

**Approach:** Centralized API client with automatic auth header injection

Tasks to implement:
- **Task 14:** Create `frontend/src/lib/api.js` - centralized API client with token management
- **Task 15:** Create `AuthContext` - React context for auth state
- **Task 16:** Create `Login.jsx` - Login page with demo account button
- **Task 17:** Create `Register.jsx` - Registration page
- **Task 18:** Create `ProtectedRoute` - Route guard component
- **Task 19:** Update `App.jsx` - Add AuthProvider and protected routes
- **Task 20:** Refactor all pages to use API client instead of hardcoded fetch
- **Task 21:** Add `/auth/me` endpoint to backend for auth verification

### After Phase 1

Then proceed to:
- **Phase 2:** Data Model Migration (further cleanup if needed)
- **Phase 3:** Broker Integrations (Meitav, IBI, etc.)
- **Phase 4:** i18n & UI Polish (Hebrew localization)
- **Phase 5:** Deployment & Infrastructure
