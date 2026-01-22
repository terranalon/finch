# Phase 3: Broker Integrations Progress

## Status: In Progress

### Tasks Overview

| # | Task | Type | Status |
|---|------|------|--------|
| **Sprint 1: Crypto Exchanges** ||||
| 1 | Kraken - API Research | Research | ✅ Complete |
| 2 | Kraken - Implementation | API + File | ✅ Complete |
| 3 | Kraken - Documentation | Docs | ✅ Complete |
| 4 | Bit2C - API Research | Research | ✅ Complete |
| 5 | Bit2C - Implementation | API + File | ✅ Complete |
| 6 | Bit2C - Documentation | Docs | ✅ Complete |
| 7 | Binance - API Research | Research | ✅ Complete |
| 8 | Binance - Implementation | API + File | ✅ Complete |
| 9 | Binance - Documentation | Docs | ✅ Complete |
| **Sprint 1a: Crypto Price Provider** ||||
| 9c | CoinGecko - API Research | Research | ✅ Complete |
| 9d | CoinGecko - Implementation | API Client | ✅ Complete |
| 9e | CoinGecko - Documentation | Docs | ✅ Complete |
| 9f | CryptoCompare - Research & Implementation | API Client | ✅ Complete |
| 9g | Historical Price Backfill DAG | Integration | ✅ Complete |
| **Sprint 1b: Airflow Integration** ||||
| 9a | Airflow DAG Updates for Crypto Exchanges | Integration | ✅ Complete |
| 9b | Backend API Endpoints for Crypto Import | API | ✅ Complete |
| 9h | Unified Broker Router Refactoring | API | ✅ Complete |
| **Sprint 2: Israeli Brokers** ||||
| 10 | IBI - Research & Implementation | File | ⏳ Pending |
| 11 | IBI - Documentation | Docs | ⏳ Pending |
| 12 | Excellence - Research & Implementation | File | ⏳ Pending |
| 13 | Excellence - Documentation | Docs | ⏳ Pending |
| 14 | Altshuler Shaham - Research & Implementation | File | ⏳ Pending |
| 15 | Altshuler Shaham - Documentation | Docs | ⏳ Pending |
| **Sprint 3: Israeli Banks** ||||
| 16 | Bank Leumi - Research & Implementation | File | ⏳ Pending |
| 17 | Bank Leumi - Documentation | Docs | ⏳ Pending |
| 18 | Bank Hapoalim - Research & Implementation | File | ⏳ Pending |
| 19 | Bank Hapoalim - Documentation | Docs | ⏳ Pending |
| 20 | Discount Bank - Research & Implementation | File | ⏳ Pending |
| 21 | Discount Bank - Documentation | Docs | ⏳ Pending |
| 22 | Mizrahi Tefahot - Research & Implementation | File | ⏳ Pending |
| 23 | Mizrahi Tefahot - Documentation | Docs | ⏳ Pending |
| **Sprint 4: Polish** ||||
| 24 | Stock Split Transaction Type | Feature | ⏳ Pending |
| 25 | Broker Tutorial Content System | Feature | ⏳ Pending |
| 26 | File Upload Progress Tracking | Feature | ⏳ Pending |

---

## Documentation Standards

Each broker integration includes a documentation file at `docs/brokers/<broker-type>.md` with:

### For API-based Brokers
- API documentation links
- Authentication method
- Endpoints used and their purpose
- Rate limits
- Data mapping to `BrokerImportData`
- Example API responses

### For File-based Brokers
- Export instructions (how to get the file)
- File format (CSV, XLSX, etc.)
- Column schema with descriptions
- Hebrew column name mappings (for Israeli brokers)
- Data mapping to `BrokerImportData`
- Example file structure

---

## Completed Tasks

### Task 9a: Airflow DAG Updates for Crypto Exchanges ✅

**Completed:** 2026-01-20

**Changes to `airflow/dags/hourly_broker_import.py`:**
- Added credential detection for Kraken (`kraken.api_key`, `kraken.api_secret`)
- Added credential detection for Bit2C (`bit2c.api_key`, `bit2c.api_secret`)
- Added import handlers calling `/api/kraken/import-auto/{account_id}` and `/api/bit2c/import-auto/{account_id}`
- Refactored to data-driven `BROKER_CONFIG` pattern for maintainability

---

### Task 9b: Backend API Endpoints for Crypto Import ✅

**Completed:** 2026-01-20

**Files Created:**
- `backend/app/services/crypto_import_service.py` - Generic import service for crypto exchanges
- `backend/app/routers/kraken.py` - Kraken API routes (`/api/kraken/import-auto/{account_id}`, `/api/kraken/test-credentials/{account_id}`)
- `backend/app/routers/bit2c.py` - Bit2C API routes (`/api/bit2c/import-auto/{account_id}`, `/api/bit2c/test-credentials/{account_id}`)

**Files Modified:**
- `backend/app/main.py` - Registered new routers
- `backend/app/dependencies/user_scope.py` - Added `get_user_account()` and `get_broker_credentials()` helpers
- `backend/app/services/price_fetcher.py` - Integrated CoinGecko for crypto price fetching

**Key Features:**
- `CryptoImportService` handles positions, transactions, cash transactions, and dividends
- Helper method `_get_or_create_holding()` consolidates asset+holding lookup/create
- `PriceFetcher` now routes crypto assets (`asset_class == "Crypto"`) to CoinGecko, all others to Yahoo Finance
- `_fetch_price_for_asset()` helper ensures DRY principle for price source routing

---

### Task 9h: Unified Broker Router Refactoring ✅

**Completed:** 2026-01-21

**Goal:** Consolidate all broker API endpoints into a single unified router with a data-driven registry pattern, and add Binance API integration.

**Changes to `backend/app/routers/brokers.py`:**

1. **Registered Binance in BROKER_REGISTRY:**
   ```python
   BrokerType.BINANCE: BrokerConfig(
       key="binance",
       name="Binance",
       credential_type=CredentialType.API_KEY_SECRET,
       client_class=BinanceClient,
       credentials_class=BinanceCredentials,
       balance_method="get_account_balances",
   ),
   ```

2. **Removed `supports_test_credentials` field:**
   - All brokers now support credential testing
   - IBKR uses `IBKRFlexClient.request_flex_query()` to validate credentials
   - Crypto brokers fetch balances to validate

3. **Added data-driven client instantiation:**
   - `BrokerConfig` now includes `client_class`, `credentials_class`, `balance_method`
   - Eliminated if/elif chains in favor of `getattr(client, config.balance_method)()`
   - Adding new brokers only requires registry entry, no code changes

4. **Added credential helper functions:**
   - `get_credential_fields()` - returns field names for credential type
   - `has_credentials()` - checks if credentials exist
   - `remove_credential_fields()` - removes credential fields from metadata

5. **Added account validation helper:**
   - `_get_validated_account()` - validates ownership and returns Account or raises 404
   - Replaced 5 repetitions of account validation logic

6. **Added crypto client factory:**
   - `_create_crypto_client()` - creates broker client from registry config
   - Uses `config.client_class` and `config.credentials_class`
   - Eliminated if/elif chains for client instantiation

7. **Added credential data builder:**
   - `build_credential_data()` - creates credential dict from Pydantic model
   - Handles both `api_key_secret` and `flex_query` credential types
   - Adds `updated_at` timestamp automatically

8. **Dynamic error messages:**
   - Error messages in `_get_flex_query_credentials()` now use broker name/key from config
   - Future brokers get correct error messages without code changes

**Available Binance Endpoints:**
- `GET /api/brokers/` - Lists Binance with other brokers
- `PUT /api/brokers/binance/credentials/{account_id}` - Store credentials
- `GET /api/brokers/binance/credentials/{account_id}` - Check credential status
- `POST /api/brokers/binance/test-credentials/{account_id}` - Test credentials
- `POST /api/brokers/binance/import/{account_id}` - Import data

**Code Simplification Results:**
- File reduced from ~700 lines to ~580 lines (17% reduction)
- All linting checks pass (`ruff check --fix && ruff format`)
- All 23 tests passing
- New brokers require only registry entry (no endpoint code changes)

---

## Sprint 1a: Crypto Price Provider

### Task 9c: CoinGecko - API Research ✅

**Completed:** 2026-01-20

**Deliverable:** `docs/research/coingecko-api-research.md`

**Key Findings:**
- API Base URL: `https://api.coingecko.com/api/v3`
- Endpoints: `/simple/price`, `/coins/{id}/history`, `/coins/{id}/market_chart/range`, `/coins/list`
- Rate limits: 10-30 req/min (free tier), 500-1000 req/min (Pro)
- **Important limitation:** Free tier limited to 365 days of historical data
- Symbol to CoinGecko ID mapping required (BTC → bitcoin, ETH → ethereum, etc.)

---

### Task 9d: CoinGecko - Implementation ✅

**Completed:** 2026-01-20

**Files Created:**
- `backend/app/services/coingecko_client.py` - CoinGecko API client
- `backend/tests/test_coingecko_client.py` - 27 unit tests

**Key Features:**
- `CoinGeckoClient` class with methods: `get_current_prices()`, `get_current_price()`, `get_historical_price()`, `get_price_history()`, `get_coin_list()`
- `SYMBOL_TO_ID` mapping for 25+ common cryptocurrencies
- Rate limiting (1 req/sec)
- Support for both Demo and Pro API keys

---

### Task 9e: CoinGecko - Documentation ✅

**Completed:** 2026-01-20

**Deliverable:** `docs/services/coingecko.md`

**Contents:**
- Quick start guide with code examples
- API endpoints reference
- Symbol to CoinGecko ID mapping table
- Rate limits and configuration
- Integration with currency conversion
- Comparison with yfinance (stocks)

---

### Task 9f: CryptoCompare - Research & Implementation ✅

**Completed:** 2026-01-20

**Problem Solved:** CoinGecko's free tier is limited to 365 days of historical data, but users can upload transactions older than 1 year.

**Solution:** Implemented CryptoCompare client as supplementary historical data source.

**Files Created:**
- `docs/research/cryptocompare-api-research.md` - API research document
- `backend/app/services/cryptocompare_client.py` - CryptoCompare API client
- `backend/tests/test_cryptocompare_client.py` - 17 unit tests
- `docs/services/cryptocompare.md` - Service documentation

**Key Features:**
- Full historical data back to coin inception (BTC from 2012, ETH from 2016)
- Uses standard symbols directly (no ID mapping needed)
- `get_historical_price()` and `get_price_history()` methods
- Auto-pagination for ranges > 2000 days
- Rate limiting (1 req/sec)

---

### Task 9g: Historical Price Backfill DAG ✅

**Completed:** 2026-01-20

**Goal:** Update the backfill DAG to support crypto historical prices.

**Files Modified:**
- `airflow/dags/queries.py` - Added `GET_CRYPTO_ASSETS` and `GET_NON_CRYPTO_ASSETS` queries
- `airflow/dags/backfill_historical_data.py` - Added `backfill_crypto_prices` task using CryptoCompare

**How It Works:**
- Stocks/ETFs: Uses Yahoo Finance (existing behavior)
- Crypto: Uses CryptoCompare (new, supports full history)
- Exchange rates: Uses Yahoo Finance (existing behavior)
- All three tasks run in parallel

**DAG Parameters:**
- `start_date`: Default "2017-01-01" (covers most crypto adoption)
- `end_date`: Default to yesterday

**Verification:**
- DAG triggered successfully
- Backfilled 72,825 stock/ETF prices, 19,298 exchange rates
- Crypto prices ready (0 records as no crypto holdings exist yet)

---

## Sprint 1: Crypto Exchanges

### Tasks 1-3: Kraken ✅

**Completed:** 2026-01-20

**Files Created:**
- `docs/research/kraken-api-research.md` - API research
- `backend/app/services/kraken_client.py` - API client
- `backend/app/services/kraken_parser.py` - CSV file parser
- `backend/app/services/kraken_constants.py` - Asset pair mappings
- `backend/tests/test_kraken_client.py` - Client tests
- `backend/tests/test_kraken_parser.py` - Parser tests
- `docs/brokers/kraken.md` - Broker documentation

**Features:**
- API client with HMAC-SHA512 authentication
- CSV file parser for trades export
- Symbol normalization (XXBT → BTC, XETH → ETH)
- Support for both API and file-based imports

---

### Kraken Integration Bugfixes ✅

**Completed:** 2026-01-21

**Problem:** After initial Kraken sync, portfolio balances were incorrect:
- USD balance showed $19,170 instead of actual $948.80
- Some crypto quantities were slightly off
- Some prices weren't loading (rate limit errors)

**Root Cause Analysis:**
1. **Missing dual-entry accounting**: Trades created crypto transactions but no Trade Settlement on cash
2. **Fee handling incomplete**: Multiple transaction types weren't subtracting fees correctly
3. **Decimal precision loss**: Using `amount` (2 decimals) instead of `quantity` (8 decimals)
4. **Wrong CoinGecko mapping**: BABY token mapped to baby-doge-coin instead of babylon
5. **Rate limiting**: Individual price calls instead of batch requests

**Bugfixes Applied:**

| File | Fix | Lines |
|------|-----|-------|
| `kraken_client.py` | Staking fees: `quantity = amount - fee` | ~630 |
| `kraken_client.py` | Withdrawal fees: `net_quantity = amount - fee` | ~598 |
| `kraken_client.py` | Sell fees (fiat trades): `quantity = abs(crypto_amount) + crypto_fee` | ~490 |
| `kraken_client.py` | Sell fees (crypto-to-crypto): `sell_quantity = abs(amount) + fee` | ~448 |
| `portfolio_reconstruction_service.py` | Deposit precision: prefer `quantity` over `amount` | ~187 |
| `portfolio_reconstruction_service.py` | Withdrawal precision: prefer `quantity` over `amount` | ~197 |
| `portfolio_reconstruction_service.py` | Transfer precision: prefer `quantity` over `amount` | ~223 |
| `coingecko_client.py` | BABY token mapping: `"BABY": "babylon"` | ~56 |
| `price_fetcher.py` | Batch crypto price fetching | ~213-232 |

**Verification Results:**
- All crypto balances match Kraken API exactly (BTC, ETH, SOL, HBAR, XLM, KAS, BABY)
- USD balance within $0.01 of API (acceptable due to 2-decimal column limit)
- All prices now fetching correctly via batch CoinGecko calls

**Lessons Learned:**
See `CLAUDE.md` → "Broker Integration Guidelines" for comprehensive checklist.

---

### Tasks 4-6: Bit2C ✅

**Completed:** 2026-01-20

**Files Created:**
- `docs/research/bit2c-api-research.md` - API research
- `backend/app/services/bit2c_client.py` - API client
- `backend/app/services/bit2c_parser.py` - CSV file parser
- `backend/app/services/bit2c_constants.py` - Asset mappings and constants
- `backend/tests/test_bit2c_client.py` - Client tests
- `backend/tests/test_bit2c_parser.py` - Parser tests
- `docs/brokers/bit2c.md` - Broker documentation

**Features:**
- Israeli crypto exchange support
- API client with HMAC authentication
- XLSX file parser for trade history (English and Hebrew)
- ILS/NIS to crypto pair handling
- Dual-entry accounting (Trade Settlements)

---

### Bit2C Integration Bugfixes ✅

**Completed:** 2026-01-21

**Problem:** Applied lessons learned from Kraken integration to fix critical bugs in Bit2C before real API testing.

**Root Cause Analysis:**
1. **Missing dual-entry accounting**: Trades created crypto transactions but no Trade Settlement on ILS cash
2. **Empty `cash_transactions`**: `fetch_all_data()` returned empty list instead of Trade Settlements
3. **No constants file**: Inline mappings instead of centralized constants

**Bugfixes Applied:**

| File | Fix |
|------|-----|
| `bit2c_constants.py` | NEW: Created constants file with `ASSET_NAME_MAP`, `TRADING_PAIRS`, `FIAT_CURRENCIES`, and `normalize_bit2c_asset()` |
| `bit2c_client.py` | `_parse_trade()` now returns tuple `(crypto_txn, settlement_txn)` for dual-entry |
| `bit2c_client.py` | `fetch_all_data()` now collects Trade Settlements in `cash_transactions` |
| `bit2c_parser.py` | `_parse_trade()` now returns tuple with Trade Settlement |
| `bit2c_parser.py` | `parse()` unpacks dual-entry tuple and collects Trade Settlements |
| `bit2c_parser.py` | Uses `normalize_bit2c_asset()` from constants |

**Dual-Entry Accounting:**
- **Buy trade**: Creates crypto transaction + Trade Settlement (negative ILS, cash leaves)
- **Sell trade**: Creates crypto transaction + Trade Settlement (positive ILS, cash received)
- Settlement amount includes fees: Buy = `-(fiat + fee)`, Sell = `fiat - fee`

**Test Results:**
- 11 client tests passing (3 new dual-entry tests)
- 26 parser tests passing (5 new dual-entry tests)
- Total: 37 tests passing

**Code Simplification (via code-simplifier agent):**
- Removed redundant identity mappings from `ASSET_NAME_MAP`
- Added empty string handling to `to_decimal()`
- Simplified `_parse_row()` return type
- Condensed verbose comments

**Status:** Ready for verification with real account (see `CLAUDE.md` → Broker Integration Guidelines)

---

### Bit2C FundsHistory Discovery ✅

**Completed:** 2026-01-22

**Problem:** The documented `/Order/AccountHistory` endpoint returns empty results even for accounts with known deposit/withdrawal activity. This prevented fetching deposit/withdrawal data via API.

**Discovery:** Found an **undocumented** endpoint `/AccountAPI/FundsHistory.json` in a third-party C# client:
- Source: https://github.com/macdasi/Bit2C.ApiClient/blob/master/Bit2C.API/Client.cs

**Testing Results:** The undocumented endpoint successfully returns deposit/withdrawal data:
- 25 Deposits (including ₪15,000 ILS deposit on 16/12/24)
- 20 Withdrawals (including ETH/BTC withdrawals on 06/12/24)
- 9 FeeWithdrawals
- Plus refunds and other action types

**Action Types Discovered:**

| Value | Type | Description |
|-------|------|-------------|
| 2 | Deposit | NIS or crypto deposit |
| 3 | Withdrawal | NIS or crypto withdrawal |
| 4 | FeeWithdrawal | Withdrawal fee |
| 23 | RefundWithdrawal | Refunded withdrawal |
| 24 | RefundFeeWithdrawal | Refunded withdrawal fee |
| 26 | DepositFee | Deposit fee |
| 27 | RefundDepositFee | Refunded deposit fee |

**Implementation:**

| File | Change |
|------|--------|
| `bit2c_client.py` | Added `get_funds_history()` method to fetch from `/AccountAPI/FundsHistory.json` |
| `bit2c_client.py` | Added `_parse_funds_record()` method to parse deposit/withdrawal records |
| `bit2c_client.py` | Updated `fetch_all_data()` to include FundsHistory data |
| `test_bit2c_client.py` | Added tests for FundsHistory parsing (deposits, withdrawals, fees) |

**Test Results:**
- 13 client tests passing (added FundsHistory tests)
- All dual-entry accounting tests passing

**Documentation Updated:**
- `docs/research/bit2c-api-research.md` - Added FundsHistory endpoint documentation

**Status:** ✅ Complete - Ready for production sync

---

### Tasks 7-9: Binance ✅

**Completed:** 2026-01-20

**Files Created:**
- `docs/research/binance-api-research.md` - API research
- `backend/app/services/binance_client.py` - API client
- `backend/app/services/binance_parser.py` - CSV file parser
- `backend/tests/test_binance_client.py` - Client tests
- `backend/tests/test_binance_parser.py` - Parser tests
- `docs/brokers/binance.md` - Broker documentation

**Features:**
- API client with HMAC-SHA256 authentication
- CSV file parser for trade history export
- Support for spot trading pairs
- Symbol pair parsing (BTCUSDT → BTC/USDT)

**Status:** Needs verification with real account (see `CLAUDE.md` → Broker Integration Guidelines)

---

## Sprint 2: Israeli Brokers

> **⚠️ IMPORTANT:** Before implementing any broker, read `CLAUDE.md` → "Broker Integration Guidelines"

### Task 10: IBI - Research & Implementation

**Status:** ⏳ Pending

**Goal:** Support IBI Trade (52K accounts, fastest growing Israeli broker).

**Files to Create:**
- `backend/app/services/ibi_parser.py`
- `backend/tests/test_ibi_parser.py`
- `backend/tests/fixtures/ibi_sample.xlsx`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 11: IBI - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/ibi.md`

**Contents:**
- Export instructions from IBI "Spark" platform
- Excel column schema (Hebrew → English mappings)
- Agorot to ILS conversion rules
- TASE security number resolution

---

### Task 12: Excellence - Research & Implementation

**Status:** ⏳ Pending

**Goal:** Support Excellence Investment House (Phoenix group).

**Files to Create:**
- `backend/app/services/excellence_parser.py`
- `backend/tests/test_excellence_parser.py`
- `backend/tests/fixtures/excellence_sample.xlsx`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 13: Excellence - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/excellence.md`

---

### Task 14: Altshuler Shaham - Research & Implementation

**Status:** ⏳ Pending

**Goal:** Support Altshuler Shaham broker.

**Files to Create:**
- `backend/app/services/altshuler_parser.py`
- `backend/tests/test_altshuler_parser.py`
- `backend/tests/fixtures/altshuler_sample.xlsx`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 15: Altshuler Shaham - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/altshuler.md`

---

## Sprint 3: Israeli Banks

> **⚠️ IMPORTANT:** Before implementing any broker, read `CLAUDE.md` → "Broker Integration Guidelines"

### Task 16: Bank Leumi - Research & Implementation

**Status:** ⏳ Pending

**Goal:** Support Bank Leumi brokerage accounts.

**Files to Create:**
- `backend/app/services/leumi_parser.py`
- `backend/tests/test_leumi_parser.py`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 17: Bank Leumi - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/leumi.md`

---

### Task 18: Bank Hapoalim - Research & Implementation

**Status:** ⏳ Pending

**Files to Create:**
- `backend/app/services/hapoalim_parser.py`
- `backend/tests/test_hapoalim_parser.py`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 19: Bank Hapoalim - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/hapoalim.md`

---

### Task 20: Discount Bank - Research & Implementation

**Status:** ⏳ Pending

**Files to Create:**
- `backend/app/services/discount_parser.py`
- `backend/tests/test_discount_parser.py`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 21: Discount Bank - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/discount.md`

---

### Task 22: Mizrahi Tefahot - Research & Implementation

**Status:** ⏳ Pending

**Files to Create:**
- `backend/app/services/mizrahi_parser.py`
- `backend/tests/test_mizrahi_parser.py`

**Integration Checklist:**
- [ ] Dual-entry accounting (asset transaction + Trade Settlement)
- [ ] Fee handling for all transaction types
- [ ] Use `quantity` field for shares (not `amount`)
- [ ] Test with real data and compare balances

---

### Task 23: Mizrahi Tefahot - Documentation

**Status:** ⏳ Pending

**Deliverable:** `docs/brokers/mizrahi.md`

---

## Sprint 4: Polish

### Task 24: Stock Split Transaction Type

**Status:** ⏳ Pending

**Goal:** Handle corporate actions (stock splits) that adjust share quantities and cost basis.

**Files to Modify:**
- `backend/app/models/transaction.py`
- `backend/app/services/corporate_actions_service.py`
- `backend/app/services/ibkr_parser.py`
- `backend/app/services/portfolio_reconstruction_service.py`

---

### Task 25: Broker Tutorial Content System

**Status:** ⏳ Pending

**Goal:** Guide users on how to export data from each supported broker.

**Files to Create:**
- `backend/app/services/broker_tutorials.py`
- `frontend/src/components/BrokerTutorial.jsx`

---

### Task 26: File Upload Progress Tracking

**Status:** ⏳ Pending

**Goal:** Show real-time progress for large file uploads.

**Files to Create:**
- `backend/app/routers/broker_data_streaming.py`
- `frontend/src/hooks/useFileUploadProgress.js`

---

## Test Summary

**Total Tests:** 81
- CoinGecko client: 27 tests (all passing)
- CryptoCompare client: 17 tests (all passing)
- Bit2C client: 11 tests (all passing)
- Bit2C parser: 26 tests (all passing)

---

## Files Created/Modified

### New Files

**Kraken:**
- `backend/app/services/kraken_client.py` - Kraken API client
- `backend/app/services/kraken_parser.py` - Kraken CSV parser
- `backend/app/services/kraken_constants.py` - Asset pair mappings
- `backend/tests/test_kraken_client.py` - Client tests
- `backend/tests/test_kraken_parser.py` - Parser tests
- `docs/research/kraken-api-research.md` - API research
- `docs/brokers/kraken.md` - Broker documentation

**Bit2C:**
- `backend/app/services/bit2c_client.py` - Bit2C API client
- `backend/app/services/bit2c_parser.py` - Bit2C XLSX parser
- `backend/app/services/bit2c_constants.py` - Asset mappings and constants
- `backend/tests/test_bit2c_client.py` - Client tests (11 tests)
- `backend/tests/test_bit2c_parser.py` - Parser tests (26 tests)
- `docs/research/bit2c-api-research.md` - API research
- `docs/brokers/bit2c.md` - Broker documentation

**Binance:**
- `backend/app/services/binance_client.py` - Binance API client
- `backend/app/services/binance_parser.py` - Binance CSV parser
- `backend/tests/test_binance_client.py` - Client tests
- `backend/tests/test_binance_parser.py` - Parser tests
- `docs/research/binance-api-research.md` - API research
- `docs/brokers/binance.md` - Broker documentation

**Crypto Price Providers:**
- `backend/app/services/coingecko_client.py` - CoinGecko API client
- `backend/app/services/cryptocompare_client.py` - CryptoCompare API client
- `backend/tests/test_coingecko_client.py` - 27 unit tests
- `backend/tests/test_cryptocompare_client.py` - 17 unit tests
- `docs/research/coingecko-api-research.md` - CoinGecko API research
- `docs/research/cryptocompare-api-research.md` - CryptoCompare API research
- `docs/services/coingecko.md` - CoinGecko service documentation
- `docs/services/cryptocompare.md` - CryptoCompare service documentation

**Integration:**
- `backend/app/services/crypto_import_service.py` - Generic crypto exchange import service
- `backend/app/routers/kraken.py` - Kraken API endpoints
- `backend/app/routers/bit2c.py` - Bit2C API endpoints

### Modified Files
- `airflow/dags/hourly_broker_import.py` - Added Kraken/Bit2C credential detection and import handlers
- `airflow/dags/backfill_historical_data.py` - Added crypto price backfill task using CryptoCompare
- `airflow/dags/queries.py` - Added crypto asset queries
- `backend/app/main.py` - Registered kraken and bit2c routers
- `backend/app/dependencies/user_scope.py` - Added helper functions
- `backend/app/services/price_fetcher.py` - Integrated CoinGecko for crypto prices, added batch fetching for crypto
- `backend/app/services/coingecko_client.py` - Fixed BABY token mapping (babylon not baby-doge-coin)
- `backend/app/services/kraken_client.py` - Fixed fee handling for staking, withdrawals, and sell transactions
- `backend/app/services/portfolio_reconstruction_service.py` - Fixed decimal precision (prefer quantity over amount)
- `backend/app/routers/brokers.py` - Added Binance to registry, removed `supports_test_credentials`, added IBKR credential testing, data-driven client factories
- `CLAUDE.md` - Added Broker Integration Guidelines section

---

## Verification Checklist

### Sprint 1a: Crypto Price Provider
- [x] CoinGecko API research completed
- [x] CoinGecko client implementation (27 tests passing)
- [x] CoinGecko service documentation
- [x] CryptoCompare API research completed
- [x] CryptoCompare client implementation (17 tests passing)
- [x] CryptoCompare service documentation
- [x] Historical price backfill DAG updated for crypto
- [x] Backfill DAG tested and verified working

### Sprint 1b: Airflow Integration
- [x] Kraken credentials detected in DAG
- [x] Bit2C credentials detected in DAG
- [x] Kraken auto-import endpoint works (`POST /api/kraken/import-auto/{account_id}`)
- [x] Bit2C auto-import endpoint works (`POST /api/bit2c/import-auto/{account_id}`)
- [x] PriceFetcher routes crypto to CoinGecko
- [x] `intraday_price_refresh` DAG works for crypto assets
- [x] Unified broker router with data-driven registry pattern
- [x] Binance registered in BROKER_REGISTRY
- [x] All brokers support credential testing (IBKR via Flex Query)
- [x] Code simplified with helper functions and client factories

### Sprint 1: Crypto Exchanges
- [x] Kraken API research completed
- [x] Kraken client and parser implemented
- [x] Kraken documentation completed
- [x] Bit2C API research completed
- [x] Bit2C client and parser implemented
- [x] Bit2C documentation completed
- [x] Binance API research completed
- [x] Binance client and parser implemented
- [x] Binance documentation completed

### Sprint 2: Israeli Brokers
- [ ] IBI Excel upload works
- [ ] Excellence Excel upload works
- [ ] Altshuler Excel upload works

### Sprint 3: Israeli Banks
- [ ] Leumi file upload works
- [ ] Hapoalim file upload works
- [ ] Discount file upload works
- [ ] Mizrahi file upload works

### Sprint 4: Polish
- [ ] Stock splits apply correctly to holdings
- [ ] Tutorials display for all brokers
- [ ] Upload progress shows in UI

---

## Next Steps

1. ~~Complete **Tasks 1-3: Kraken**~~ ✅ Done
2. ~~Complete **Tasks 4-6: Bit2C**~~ ✅ Done
3. ~~Complete **Tasks 7-9: Binance**~~ ✅ Done
4. ~~Complete **Tasks 9c-9e: CoinGecko**~~ ✅ Done
5. ~~Complete **Tasks 9f-9g: CryptoCompare & Backfill**~~ ✅ Done
6. **Next:** Proceed to **Sprint 2: Israeli Brokers** (IBI, Excellence, Altshuler Shaham)
