# Fix Broken Tests & Add CI Gate — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 82 broken backend tests (34 failures + 48 errors) and add a GitHub Actions CI workflow that blocks merging PRs with failing tests.

**Architecture:** Seven independent test-fix tasks (parallelizable) grouped by root cause, followed by a verification pass and CI workflow addition. Each task touches a different set of files with no overlap.

**Tech Stack:** pytest, slowapi, SQLAlchemy 2.0, GitHub Actions, PostgreSQL 15

---

## Root Cause Summary

| Bucket | Root Cause | Broken Tests | Files |
|--------|-----------|--------------|-------|
| 1 | Rate limiter not disabled in integration test fixtures | ~27 errors | conftest, routers/, broker_data_delete |
| 2 | Mock targets stale after registry refactor | 2 failures | test_brokers_router.py |
| 3 | Mock patches class instead of static method | 4-5 failures | test_snapshot_endpoint.py |
| 4 | Wrong DB credentials in test fixture | 11 errors | test_staged_import.py |
| 5 | Account model uses many-to-many now, tests use old `portfolio_id` FK | 7 errors | test_reconstruction, test_historical |
| 6 | Missing `xlsxwriter` dev dependency for XLSX test fixture | 3 errors | test_manual_parser.py |
| 7 | Remaining failures (auth/MFA, others) | ~28 failures | TBD after 1-6 |

---

## Task 1: Disable Rate Limiter in Integration Test Fixtures

**Resolves:** ~27 errors across `tests/routers/test_accounts.py`, `tests/routers/test_portfolios.py`, `tests/test_broker_data_delete.py`

**Root cause:** The integration `client` fixture (in `tests/integration/conftest.py`) does not disable or reset the slowapi rate limiter. After 5 login calls across tests, the limiter returns 429, the auth fixture gets no `access_token`, and every subsequent test errors with `KeyError: 'access_token'`.

**Files:**
- Modify: `backend/tests/integration/conftest.py`
- Reference: `backend/app/rate_limiter.py` (the shared `limiter` instance)

**Step 1: Read the integration conftest**

Read `backend/tests/integration/conftest.py` to find the `client` fixture and `auth_headers` fixture.

**Step 2: Add rate limiter disable to the integration conftest**

At the top of `backend/tests/integration/conftest.py`, add the import:

```python
from app.rate_limiter import limiter
```

Then add an autouse session-scoped fixture that disables the rate limiter for all integration tests:

```python
@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable rate limiter during tests to prevent 429 cascades."""
    limiter.enabled = False
    yield
    limiter.enabled = True
```

**Step 3: Run the affected tests to verify**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/routers/ tests/test_broker_data_delete.py -v --tb=short
```

Expected: All 27 previously-erroring tests now pass or fail with real assertion errors (not `KeyError: 'access_token'`).

**Step 4: Commit**

```bash
git add backend/tests/integration/conftest.py
git commit -m "fix(tests): disable rate limiter in integration test fixtures"
```

---

## Task 2: Fix Import Service Registry Mock Targets

**Resolves:** 2 failures in `tests/test_brokers_router.py` (`test_kraken_import_success`, `test_bit2c_import_success`)

**Root cause:** The brokers router was refactored to use `BrokerImportServiceRegistry.get_import_service()` instead of importing `CryptoImportService` directly. Tests still mock `app.routers.brokers.CryptoImportService`, which no longer exists in that module.

**Files:**
- Modify: `backend/tests/test_brokers_router.py`
- Reference: `backend/app/routers/brokers.py` (the `_import_crypto_broker` function)
- Reference: `backend/app/services/brokers/import_service_registry.py`

**Step 1: Read the current router implementation**

Read `backend/app/routers/brokers.py`, specifically the `_import_crypto_broker` function. Note that it:
1. Calls `config.create_client()` to get a broker client
2. Calls `BrokerImportServiceRegistry.get_import_service(config.key, db)` to get the service
3. Calls `import_service.import_data(client)` to perform the import

**Step 2: Update mock targets in both failing tests**

In `test_kraken_import_success` and `test_bit2c_import_success`, change the mock from:

```python
patch("app.routers.brokers.CryptoImportService") as mock_service_class
```

to:

```python
patch("app.routers.brokers.BrokerImportServiceRegistry.get_import_service") as mock_get_service
```

Then update the mock setup. Instead of:

```python
mock_service_class.return_value.import_data.return_value = ImportStats(...)
```

Use:

```python
mock_service = MagicMock()
mock_service.import_data.return_value = ImportStats(...)
mock_get_service.return_value = mock_service
```

And update any assertions that reference `mock_service_class` to use the new mock shape.

**Step 3: Run the affected tests**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/test_brokers_router.py::TestCryptoBrokerImport -v --tb=short
```

Expected: Both tests pass.

**Step 4: Commit**

```bash
git add backend/tests/test_brokers_router.py
git commit -m "fix(tests): update crypto import tests to use registry mock target"
```

---

## Task 3: Fix Snapshot Endpoint Mock Targets

**Resolves:** 4-5 failures in `tests/unit/test_snapshot_endpoint.py`

**Root cause:** Tests patch the class `IBKRSyntheticImportService` but the router calls the static method `IBKRSyntheticImportService.import_snapshot(...)` directly. The mock doesn't intercept the static method call, so the real service runs, hits missing DB tables (SQLite), and fails. Additionally, `generate_snapshots_background` runs as a background task and also fails.

**Files:**
- Modify: `backend/tests/unit/test_snapshot_endpoint.py`
- Reference: `backend/app/routers/brokers.py` (the snapshot endpoint, around line 435)

**Step 1: Read the current test and router**

Read `backend/tests/unit/test_snapshot_endpoint.py` and the snapshot section of `backend/app/routers/brokers.py`.

**Step 2: Fix mock targets in all snapshot tests**

Change from:

```python
with patch("app.routers.brokers.IBKRSyntheticImportService") as mock_service:
    mock_service.import_snapshot.return_value = _make_completed_stats(...)
```

To:

```python
with patch("app.routers.brokers.IBKRSyntheticImportService.import_snapshot") as mock_import, \
     patch("app.routers.brokers.generate_snapshots_background"):
    mock_import.return_value = _make_completed_stats(...)
```

Update assertions that reference `mock_service.import_snapshot.call_args` to use `mock_import.call_args` instead.

Apply this pattern to all 4-5 test functions in the file.

**Step 3: Run the affected tests**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_snapshot_endpoint.py -v --tb=short
```

Expected: All snapshot tests pass.

**Step 4: Commit**

```bash
git add backend/tests/unit/test_snapshot_endpoint.py
git commit -m "fix(tests): patch static method and background task in snapshot tests"
```

---

## Task 4: Fix Staged Import DB Credentials

**Resolves:** 11 errors in `tests/test_staged_import.py`

**Root cause:** The test fixture uses `postgres:postgres` as default DB credentials, but the project uses `portfolio_user:dev_password`. All 11 tests fail at setup because PostgreSQL rejects the connection.

**Files:**
- Modify: `backend/tests/test_staged_import.py` (line ~47)

**Step 1: Read the test fixture**

Read `backend/tests/test_staged_import.py`, specifically the `test_db` fixture around line 38-62.

**Step 2: Fix the default database URL**

Change line ~47 from:

```python
test_db_url = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/portfolio_tracker_test",
)
```

To:

```python
db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
test_db_url = os.getenv(
    "TEST_DATABASE_URL",
    f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
)
```

This aligns with the pattern used in `tests/integration/conftest.py`.

**Step 3: Run the affected tests**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/test_staged_import.py -v --tb=short
```

Expected: All 11 tests pass (or fail with real assertion errors, not connection errors).

**Step 4: Commit**

```bash
git add backend/tests/test_staged_import.py
git commit -m "fix(tests): use correct DB credentials in staged import test fixture"
```

---

## Task 5: Fix Account Model Many-to-Many Usage

**Resolves:** 7 errors across `tests/test_portfolio_reconstruction_service.py` (4) and `tests/test_historical_data_fetcher.py` (3)

**Root cause:** The Account model was refactored from a direct `portfolio_id` foreign key to a many-to-many relationship via the `portfolio_accounts` junction table. Tests still create accounts with `Account(portfolio_id=...)`, which raises `TypeError: 'portfolio_id' is an invalid keyword argument`.

**Files:**
- Modify: `backend/tests/test_portfolio_reconstruction_service.py` (fixture around line 83-88)
- Modify: `backend/tests/test_historical_data_fetcher.py` (fixture around line 85-91)
- Reference: `backend/app/models/account.py` (current Account model)
- Reference: `backend/tests/integration/conftest.py` (correct pattern)

**Step 1: Read both test files and the correct pattern**

Read the test files and `backend/tests/integration/conftest.py` to see the correct account creation pattern:

```python
account = Account(
    name="Test Account",
    account_type="brokerage",
    institution="Test Broker",
    currency="USD",
)
account.portfolios.append(portfolio)
db.add(account)
db.commit()
```

**Step 2: Fix test_portfolio_reconstruction_service.py**

In the `account_with_transactions` fixture (around line 83-88), change from:

```python
account = Account(
    portfolio_id=portfolio.id,
    name="Test Account",
    account_type="brokerage",
    currency="USD",
)
```

To:

```python
account = Account(
    name="Test Account",
    account_type="brokerage",
    currency="USD",
)
account.portfolios.append(portfolio)
```

**Step 3: Fix test_historical_data_fetcher.py**

In the `test_account_with_holdings` fixture (around line 85-91), apply the same change: remove `portfolio_id`, add `account.portfolios.append(portfolio)`.

**Step 4: Run the affected tests**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/test_portfolio_reconstruction_service.py tests/test_historical_data_fetcher.py -v --tb=short
```

Expected: All 7 tests pass.

**Step 5: Commit**

```bash
git add backend/tests/test_portfolio_reconstruction_service.py backend/tests/test_historical_data_fetcher.py
git commit -m "fix(tests): use many-to-many account-portfolio pattern in test fixtures"
```

---

## Task 6: Add xlsxwriter Dev Dependency

**Resolves:** 3 errors in `tests/unit/test_manual_parser.py` (XLSX tests only)

**Root cause:** The test fixture generates XLSX files dynamically using `polars.DataFrame.write_excel()`, which requires the `xlsxwriter` package. This package is not in dev dependencies. The production code only reads XLSX (using `fastexcel`), so `xlsxwriter` is only needed for tests.

**Files:**
- Modify: `backend/pyproject.toml` (dev dependencies)

**Step 1: Add xlsxwriter to dev dependencies**

In `backend/pyproject.toml`, add `xlsxwriter` to the dev optional dependencies:

```toml
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "httpx>=0.26.0",
    "ruff>=0.1.11",
    "xlsxwriter>=3.0.0",
]
```

**Step 2: Install and run the affected tests**

```bash
cd backend && uv sync --extra dev
DATABASE_HOST=localhost uv run --extra dev python -m pytest tests/unit/test_manual_parser.py -v --tb=short
```

Expected: All manual parser tests pass (CSV and XLSX).

**Step 3: Commit**

```bash
git add backend/pyproject.toml uv.lock
git commit -m "fix(tests): add xlsxwriter dev dependency for XLSX test fixture"
```

---

## Task 7: Verify and Fix Remaining Failures

**Depends on:** Tasks 1-6 completed

**Purpose:** After fixing the 6 known root causes (~77 of 82 broken tests), re-run the full suite to identify any remaining failures. The auth/MFA tests showed no code mismatches in investigation, so their failures are likely caused by the rate limiter (fixed in Task 1) or other cascade effects.

**Step 1: Run the full test suite**

```bash
DATABASE_HOST=localhost uv run --extra dev python -m pytest --tb=short -q
```

**Step 2: Analyze remaining failures**

If any tests still fail:
- Auth/MFA failures: likely resolved by Task 1's rate limiter fix
- Other failures: investigate individually, fix, and commit

**Step 3: Confirm green suite**

Re-run until 0 failures, 0 errors. Target: `827 passed, 0 failed, 0 errors`.

---

## Task 8: Add GitHub Actions CI Workflow

**Depends on:** Task 7 (green test suite)

**Purpose:** Add a workflow that runs the backend test suite on every PR targeting `main`. Configure branch protection to require this check to pass before merging.

**Files:**
- Create: `.github/workflows/test.yml`

**Step 1: Create the workflow file**

```yaml
name: Backend Tests

on:
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: portfolio_user
          POSTGRES_PASSWORD: dev_password
          POSTGRES_DB: portfolio_tracker_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U portfolio_user -d portfolio_tracker_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Run tests
        env:
          DATABASE_HOST: localhost
        run: uv run pytest --tb=short -q
```

**Step 2: Test the workflow locally (optional)**

If `act` is installed:

```bash
act pull_request -W .github/workflows/test.yml
```

Otherwise, push the branch and create a PR to verify.

**Step 3: Enable branch protection**

After the workflow runs successfully on a PR:
1. Go to GitHub repo Settings > Branches > Branch protection rules
2. Add rule for `main`
3. Enable "Require status checks to pass before merging"
4. Select "Backend Tests" as a required check

**Step 4: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: add GitHub Actions workflow to run backend tests on PRs"
```

---

## Execution Strategy

**Tasks 1-6 are fully independent** and can be executed in parallel by separate agents. Each touches different files with no overlap:

| Task | Files Modified |
|------|---------------|
| 1 | `tests/integration/conftest.py` |
| 2 | `tests/test_brokers_router.py` |
| 3 | `tests/unit/test_snapshot_endpoint.py` |
| 4 | `tests/test_staged_import.py` |
| 5 | `tests/test_portfolio_reconstruction_service.py`, `tests/test_historical_data_fetcher.py` |
| 6 | `pyproject.toml` |

**Task 7** is a verification gate after all parallel tasks complete.
**Task 8** adds CI and is the final step.

### Recommended approach: Subagent-Driven (this session)

Dispatch 6 parallel agents for Tasks 1-6, verify with Task 7, then add CI with Task 8.
