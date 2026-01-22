# Portfolio Tracker Coding Standards

## Type Hints (Python 3.11+)
Use built-in generics (`list`, `dict`, `set`, `tuple`) instead of `typing.List`, `typing.Dict`, etc. Python 3.9+ supports this natively, making typing imports unnecessary and code cleaner.

```python
def process(items: list[str]) -> dict[str, int]:  # Good
def process(items: List[str]) -> Dict[str, int]:  # Bad - legacy typing
```

## Airflow 3 SDK
Import from `airflow.sdk` instead of `airflow.decorators`. The SDK is the new standard for Airflow 3; decorators are deprecated Airflow 2 syntax.

```python
from airflow.sdk import dag, task      # Good - Airflow 3
from airflow.decorators import dag     # Bad - deprecated
```

## Logging
Use `logging` module instead of `print()`. Logging provides severity levels, timestamps, and can be configured for different environments (dev vs prod).

```python
logger = logging.getLogger(__name__)
logger.info("Processing started")      # Good - structured, filterable
print("Processing started")            # Bad - no context, hard to filter
```

## SQL Queries
Store queries in `queries.py` constants or `.sql` files. Separating SQL from business logic improves readability, enables syntax highlighting, and makes queries reusable.

```python
# queries.py
GET_ACTIVE_HOLDINGS = """SELECT ... FROM assets ..."""

# usage
from .queries import GET_ACTIVE_HOLDINGS
```

## Linting
Run `ruff check --fix . && ruff format .` before committing. Config in `backend/pyproject.toml` and `airflow/pyproject.toml` enforces Python 3.11+ syntax and Airflow 3 best practices.

## General
- Type hints on all function signatures
- f-strings for formatting
- Max line length: 100 chars

## Airflow Local Development (Astro CLI)

### Container Architecture
- **App containers** (`docker-compose.yml`): `portfolio_tracker_backend`, `portfolio_tracker_frontend`, `portfolio_tracker_db`
- **Airflow containers** (Astro-managed): `airflow_*-scheduler-1`, `airflow_*-api-server-1`, `airflow_*-triggerer-1`, `airflow_*-dag-processor-1`, `airflow_*-postgres-1`

These are separate - restarting app containers does NOT restart Airflow.

### Common Operations

```bash
# Restart Airflow containers (use this, not `astro dev restart` which needs TTY)
docker restart $(docker ps --format "{{.Names}}" | grep airflow)

# List DAGs
docker exec airflow_*-scheduler-1 airflow dags list

# Test a task directly (best way to run one-off tasks)
docker exec airflow_*-scheduler-1 airflow tasks test <dag_id> <task_id> <date>

# Trigger a DAG
docker exec airflow_*-scheduler-1 airflow dags trigger <dag_id>

# List pools
docker exec airflow_*-scheduler-1 airflow pools list
```

### Gotchas
- `astro dev parse` often fails due to Docker permission issues and mocked env vars - don't rely on it
- `astro dev restart` requires interactive TTY - use `docker restart` instead
- Airflow 3 CLI syntax differs from Airflow 2 (e.g., `airflow dags list-runs` changed)
- DAG files are mounted from `airflow/dags/` - changes are picked up automatically but container restart may be needed for new imports
- **Airflow 3 prohibits direct ORM access** from tasks - use CLI (`subprocess.run(["airflow", ...])`) or REST API instead of `create_session()` or importing models
- Stale import errors are cached in `import_error` table - clear with: `docker exec airflow_*-postgres-1 psql -U postgres -d postgres -c "DELETE FROM import_error WHERE filename LIKE '%<file>%';"`

### Astronomer Task Isolation (Important!)
Astronomer Runtime isolates tasks from Airflow's metadata database by setting `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` to `airflow-db-not-allowed:///` during task execution. This means:

**Inside tasks, you CANNOT:**
- Run `airflow` CLI commands (e.g., `airflow pools set`, `airflow pools list`)
- Access Airflow metadata tables directly
- Use `localhost:8080` to reach the Airflow API server

**For Airflow admin operations (pools, variables, connections):**
- Create them manually via Airflow UI (Admin -> Pools/Variables/Connections)
- Or run CLI commands from the host machine:
  ```bash
  docker exec <scheduler-container> airflow pools set db_write_pool 2 "Description"
  ```

This is a security feature to prevent tasks from modifying Airflow's internal state.

### Database Connections
- App uses `postgres:5432` (Docker network)
- Airflow DAGs use `host.docker.internal:5432` (cross-network access)
- Shared DB module at `airflow/dags/shared_db.py` handles this translation

---

## Broker Integration Guidelines

**CRITICAL:** Follow these rules when adding new broker integrations. Learned from Kraken integration bugs where balances were incorrect.

### 1. Dual-Entry Accounting (MANDATORY)
Every trade MUST create TWO transactions:
1. **Asset Transaction**: Buy/Sell on the asset holding (crypto/stock)
2. **Trade Settlement**: Cash impact on the cash holding (USD/ILS)

```python
# For a BUY order:
# 1. Asset transaction: quantity = +crypto_amount (positive)
# 2. Trade Settlement: amount = -fiat_amount (negative, deducts from cash)

# For a SELL order:
# 1. Asset transaction: quantity = -crypto_amount (negative)
# 2. Trade Settlement: amount = +fiat_amount (positive, adds to cash)
```

Without Trade Settlements, purchases won't deduct from cash balance, causing inflated USD balances.

### 2. Fee Handling (ALL fee types)
Fees must be subtracted/added correctly for EVERY transaction type:

| Transaction Type | Fee Rule |
|-----------------|----------|
| **Buy (fiat→crypto)** | `quantity = crypto_received` (fee usually in fiat, included in Trade Settlement) |
| **Sell (crypto→fiat)** | `quantity = abs(crypto_sold) + crypto_fee` (total crypto leaving account) |
| **Crypto-to-Crypto** | Sell side: `quantity = abs(amount) + fee`; Buy side: `quantity = amount` |
| **Staking Rewards** | `quantity = amount - fee` (net reward after fee) |
| **Withdrawal** | `quantity = abs(amount) + fee` (total leaving account) |
| **Deposit** | `quantity = amount` (fees usually external) |

### 3. Decimal Precision
- **Transaction.amount**: `Numeric(15, 2)` - only 2 decimal places (for fiat values)
- **Transaction.quantity**: `Numeric(20, 8)` - 8 decimal places (for crypto/shares)
- **ALWAYS** use `quantity` field for crypto, never `amount` for position calculations
- In `portfolio_reconstruction_service.py`, prefer `quantity` over `amount`:
  ```python
  deposit_qty = txn.quantity if txn.quantity is not None else txn.amount
  ```

### 4. Asset Normalization
Create a `<broker>_constants.py` file with symbol mappings:
```python
# Kraken: XXBT → BTC, XETH → ETH, ZUSD → USD
# Staked variants: SOL.S → SOL, ETH.S → ETH (map to base asset)
```

### 5. Price Provider Mappings
Add new crypto symbols to `coingecko_client.py:SYMBOL_TO_ID`:
```python
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "BABY": "babylon",  # NOT "baby-doge-coin"!
    # Verify correct ID at https://api.coingecko.com/api/v3/coins/list
}
```

### 6. Batch Price Fetching
Use batch API calls to avoid rate limits:
```python
# Good: Single API call for all crypto
crypto_prices = client.get_current_prices(["BTC", "ETH", "SOL"], "usd")

# Bad: Individual calls (rate limited)
for symbol in symbols:
    price = client.get_current_price(symbol, "usd")  # Will hit 429 errors
```

### 7. Testing Checklist
Before marking a broker integration complete:
- [ ] Clear all transactions for test account
- [ ] Re-sync from broker API
- [ ] Compare each asset balance with API response (must match exactly for crypto, <$0.01 for fiat)
- [ ] Verify USD/cash balance reflects all trade settlements
- [ ] Test re-sync (should skip duplicates)
- [ ] Verify historical data imports correctly

### 8. Common Bugs to Avoid
| Bug | Symptom | Fix |
|-----|---------|-----|
| Missing Trade Settlements | Cash balance inflated | Add dual-entry accounting |
| Fees not subtracted | Quantities slightly off | Include fees in all transaction types |
| Using `amount` for crypto | Precision loss (0.37 vs 0.37132823) | Use `quantity` field |
| Wrong CoinGecko ID | No price data | Verify at coingecko.com/api/v3/coins/list |
| Individual price calls | 429 rate limit errors | Use batch `get_current_prices()` |

### 9. Reference Implementations
- **IBKR** (`ibkr_import_service.py`): Best example of dual-entry accounting
- **Meitav** (`meitav_parser.py`): Good Israeli broker reference
- **Kraken** (`kraken_client.py`): Crypto exchange with all fee types handled
