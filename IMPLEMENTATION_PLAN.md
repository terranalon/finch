# Portfolio Tracker - Implementation Plan

## Project Overview

**Objective**: Build a full-stack investment dashboard supporting multi-currency, multi-asset tracking with manual and automated data entry.

**Target User**: Single user (local deployment)
**Deployment**: Docker Compose for local development

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 15
- **Data Processing**: Polars (faster and more memory-efficient than Pandas)
- **Task Scheduler**: APScheduler
- **Market Data**: yfinance, CoinGecko API
- **Currency Rates**: ExchangeRate-API / yfinance

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Data Fetching**: TanStack Query (React Query)
- **Charts**: Recharts
- **HTTP Client**: Axios

### DevOps
- **Containerization**: Docker + Docker Compose
- **Database Migrations**: Alembic

---

## Conceptual Data Model

### Core Abstractions

**Entity** = Owner of financial resources
- Who owns the money/assets?
- Types: `Individual`, `Corporation`, `Trust`
- Example: "Personal", "My Company Ltd"

**Account** = Financial container where assets are custodied
- Where are the assets held?
- Has: institution name, account type, base currency
- Examples: "IBKR Main Brokerage", "Coinbase Wallet", "My Properties"

**Asset** = Thing of value that can be owned
- What do you own?
- Has: identifier, name, asset class, sector
- Examples: AAPL stock, Bitcoin, "123 Main St Apartment", USD cash

**Holding** = Ownership record connecting an account to an asset
- Tracks: quantity owned, cost basis, strategy
- Example: "100 shares of AAPL in IBKR account"

**Holding Lot** = Individual purchase lot (for FIFO cost basis tracking)
- Tracks: specific purchase date, quantity, cost per unit
- Used for: accurate P&L calculations, tax reporting

### Account Types

```python
account_types = [
    "Brokerage",       # IBKR, Meitav - stocks/bonds/ETFs
    "Pension",         # Israeli pension funds (קרן פנסיה)
    "StudyFund",       # Israeli study funds (קרן השתלמות)
    "Bank",            # Checking/savings accounts
    "CryptoExchange",  # Coinbase, Kraken, Binance (custodial)
    "CryptoWallet",    # Self-custodied wallets (hardware/software)
    "SelfCustodied",   # Direct ownership: real estate, physical gold, art
    "FamilyOffice"     # Family office managed accounts
]
```

### Asset Classes

```python
asset_classes = [
    "Stock",           # Public equities
    "Bond",            # Government/corporate bonds
    "ETF",             # Exchange-traded funds
    "MutualFund",      # Mutual funds
    "Crypto",          # Cryptocurrencies
    "Cash",            # USD, ILS, EUR, etc.
    "RealEstate",      # Properties (residential, commercial)
    "Commodity",       # Gold, silver, oil
    "PrivateEquity",   # Private company shares
    "Art",             # Art, collectibles
    "Other"            # Catch-all
]
```

### Entity Relationship Flow

```
Entity (Who owns?)
  └─> Account (Where held?)
       └─> Holding (What & how much?)
            ├─> Asset (What is it?)
            └─> Holding Lots (FIFO cost tracking)

Example:
"Personal" (Entity: Individual)
  ├─> "IBKR Main" (Account: Brokerage, USD)
  │    └─> 100 shares of AAPL (Asset: Stock)
  │         ├─> Lot 1: 50 shares @ $150 (2024-01-15)
  │         └─> Lot 2: 50 shares @ $180 (2024-03-10)
  │
  └─> "My Properties" (Account: SelfCustodied, ILS)
       └─> 1 unit of "Tel Aviv Apartment" (Asset: RealEstate)
            └─> Lot 1: 1 unit @ 2,000,000 ILS (2020-06-01)
```

---

## Database Schema Design

### Tables

#### 1. Entities
Represents owners of accounts (Individual, Corporation, or Trust).

```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'Individual', 'Corporation', 'Trust'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. Accounts
Financial accounts belonging to entities.Thisrds 
ad365
```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    institution VARCHAR(100), -- 'IBKR', 'Meitav', 'Coinbase', 'Self', etc.
    account_type VARCHAR(50) NOT NULL, -- 'Brokerage', 'Pension', 'StudyFund', 'Bank', 'CryptoExchange', 'CryptoWallet', 'SelfCustodied', 'FamilyOffice'
    currency VARCHAR(3) NOT NULL, -- Base currency: 'USD', 'ILS'
    account_number VARCHAR(100), -- For reference
    external_id VARCHAR(100), -- For API integrations
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_accounts_entity ON accounts(entity_id);
```

#### 3. Assets
Investment assets (stocks, crypto, real estate, bonds, commodities, etc.).

```sql
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE, -- 'AAPL', 'TEVA.TA', 'BTC-USD', or UUID for manual assets
    name VARCHAR(200) NOT NULL,
    asset_class VARCHAR(50) NOT NULL, -- 'Stock', 'Bond', 'ETF', 'MutualFund', 'Crypto', 'Cash', 'RealEstate', 'Commodity', 'PrivateEquity', 'Art', 'Other'
    sector VARCHAR(100), -- 'Tech', 'Healthcare', 'Residential', 'Energy', etc.
    is_manual_valuation BOOLEAN DEFAULT FALSE, -- True for assets without market data (real estate, private equity, art)
    data_source VARCHAR(50), -- 'yfinance', 'coingecko', 'manual'
    last_fetched_price DECIMAL(15, 4),
    last_fetched_at TIMESTAMP,
    metadata JSONB, -- Flexible storage for asset-specific data (property address, ISIN, blockchain address, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_assets_symbol ON assets(symbol);
CREATE INDEX idx_assets_class ON assets(asset_class);
```

#### 4. Holdings
Current positions in accounts (aggregate view).

```sql
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    quantity DECIMAL(20, 8) NOT NULL, -- Total quantity (sum of all lots)
    cost_basis DECIMAL(15, 2) NOT NULL, -- Total cost in account currency
    strategy_horizon VARCHAR(20), -- 'Short', 'Medium', 'Long'
    tags JSONB, -- ["High Risk", "Dividend"]
    is_active BOOLEAN DEFAULT TRUE, -- False when fully sold
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, asset_id)
);

CREATE INDEX idx_holdings_account ON holdings(account_id);
CREATE INDEX idx_holdings_asset ON holdings(asset_id);
CREATE INDEX idx_holdings_active ON holdings(is_active);
```

#### 4.5. Holding Lots
Individual purchase lots for FIFO cost basis tracking.

```sql
CREATE TABLE holding_lots (
    id SERIAL PRIMARY KEY,
    holding_id INTEGER REFERENCES holdings(id) ON DELETE CASCADE,
    quantity DECIMAL(20, 8) NOT NULL,
    cost_per_unit DECIMAL(15, 4) NOT NULL, -- In account currency
    purchase_date DATE NOT NULL,
    purchase_price_original DECIMAL(15, 4), -- Original price at purchase
    fees DECIMAL(15, 2) DEFAULT 0,
    is_closed BOOLEAN DEFAULT FALSE, -- True when fully sold (FIFO)
    remaining_quantity DECIMAL(20, 8), -- Quantity not yet sold
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lots_holding ON holding_lots(holding_id);
CREATE INDEX idx_lots_purchase_date ON holding_lots(purchase_date);
CREATE INDEX idx_lots_closed ON holding_lots(is_closed);
```

#### 5. Transactions
Historical record of all trades and updates.

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    holding_id INTEGER REFERENCES holdings(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'Buy', 'Sell', 'Dividend', 'Deposit', 'Withdrawal', 'ValuationUpdate'
    quantity DECIMAL(20, 8),
    price_per_unit DECIMAL(15, 4),
    fees DECIMAL(15, 2) DEFAULT 0,
    currency_rate_to_usd_at_date DECIMAL(12, 6),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_holding ON transactions(holding_id);
CREATE INDEX idx_transactions_date ON transactions(date);
```

#### 6. Exchange Rates
Historical currency exchange rates.

```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(12, 6) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, date)
);

CREATE INDEX idx_rates_currencies_date ON exchange_rates(from_currency, to_currency, date);
```

#### 7. Historical Snapshots
Daily portfolio value snapshots.

```sql
CREATE TABLE historical_snapshots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    total_value_usd DECIMAL(15, 2),
    total_value_ils DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, account_id)
);

CREATE INDEX idx_snapshots_date ON historical_snapshots(date);
CREATE INDEX idx_snapshots_account ON historical_snapshots(account_id);
```

---

## Backend Architecture

### Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration and environment variables
│   ├── database.py                # SQLAlchemy setup and session management
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── account.py
│   │   ├── asset.py
│   │   ├── holding.py
│   │   ├── holding_lot.py
│   │   ├── transaction.py
│   │   ├── exchange_rate.py
│   │   └── historical_snapshot.py
│   │
│   ├── schemas/                   # Pydantic models (request/response DTOs)
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── account.py
│   │   ├── holding.py
│   │   ├── transaction.py
│   │   └── dashboard.py
│   │
│   ├── routers/                   # API endpoint routers
│   │   ├── __init__.py
│   │   ├── dashboard.py           # GET /api/dashboard/summary
│   │   ├── entities.py            # CRUD for entities
│   │   ├── accounts.py            # CRUD for accounts
│   │   ├── holdings.py            # CRUD for holdings
│   │   ├── transactions.py        # Transaction management and CSV import
│   │   └── assets.py              # Asset search and management
│   │
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── price_fetcher.py       # Unified market data fetching
│   │   ├── currency_service.py    # Exchange rate management
│   │   ├── portfolio_calculator.py # P&L and allocation calculations
│   │   └── parsers/               # CSV transaction parsers
│   │       ├── __init__.py
│   │       ├── base_parser.py
│   │       ├── ibkr_parser.py
│   │       └── meitav_parser.py
│   │
│   └── tasks/                     # Scheduled background tasks
│       ├── __init__.py
│       └── daily_snapshot.py      # Daily portfolio snapshot job
│
├── alembic/                       # Database migration scripts
│   ├── versions/
│   └── env.py
├── tests/                         # Unit and integration tests
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Core Services

#### PriceFetcher Service
- Fetches current market prices from various sources
- Handles yfinance for stocks (US and Israeli)
- Integrates CoinGecko for crypto prices
- Returns last manual valuation for manual assets
- Implements caching and error handling

#### CurrencyService
- Fetches and caches exchange rates
- Stores historical rates in database
- Provides conversion between USD and ILS
- Falls back to last known rate if API fails

#### PortfolioCalculator
- Calculates holding metrics (market value, P&L, returns)
- Performs currency conversions
- Computes portfolio-wide metrics
- Generates breakdown by asset class, sector, account
- Calculates daily changes

#### CostBasisCalculator Service
- Implements FIFO (First-In-First-Out) lot tracking
- Handles buy transactions: creates new lots
- Handles sell transactions: consumes oldest lots first
- Calculates realized gains/losses on sales
- Updates holding aggregates after lot changes
- Supports partial lot sales

#### Transaction Parsers
- Base parser with common logic
- IBKR-specific CSV parser (using Polars for fast CSV processing)
- Meitav-specific CSV parser (using Polars)
- Validates and normalizes transaction data
- Creates/updates assets, holdings, and holding lots
- Integrates with CostBasisCalculator for lot management

---

## API Endpoints

### Dashboard

#### GET /api/dashboard/summary
Query Parameters:
- `currency` (required): USD | ILS
- `entity_id` (optional): Filter by entity

Response:
```json
{
  "total_net_worth": 1500000.00,
  "total_cost_basis": 1200000.00,
  "total_unrealized_pnl": 300000.00,
  "total_unrealized_pnl_pct": 25.0,
  "daily_change": 15000.00,
  "daily_change_pct": 1.0,
  "currency": "USD",
  "breakdown_by_asset_class": [
    {"asset_class": "Stock", "value": 1200000.00, "percentage": 80.0},
    {"asset_class": "Crypto", "value": 300000.00, "percentage": 20.0}
  ],
  "breakdown_by_sector": [...],
  "breakdown_by_account": [...]
}
```

### Holdings

#### GET /api/holdings
Query Parameters:
- `currency` (required): USD | ILS
- `entity_id` (optional): Filter by entity
- `account_id` (optional): Filter by account

Response:
```json
{
  "holdings": [
    {
      "id": 1,
      "asset": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_class": "Stock",
        "sector": "Tech"
      },
      "account_name": "IBKR Main",
      "entity_name": "Personal",
      "quantity": 100,
      "current_price": 180.50,
      "market_value": 18050.00,
      "cost_basis": 15000.00,
      "unrealized_pnl": 3050.00,
      "unrealized_pnl_pct": 20.33,
      "daily_change": 150.00,
      "daily_change_pct": 0.83,
      "strategy_horizon": "Long",
      "tags": ["High Risk"],
      "currency": "USD"
    }
  ]
}
```

### Transactions

#### POST /api/transactions/import
Upload and parse CSV file from brokers.

Request:
- `file`: CSV file upload
- `source`: "IBKR" | "Meitav"
- `account_id`: Target account

Response:
```json
{
  "preview": [
    {
      "date": "2024-01-15",
      "type": "Buy",
      "symbol": "AAPL",
      "quantity": 10,
      "price": 185.50,
      "fees": 1.50
    }
  ],
  "warnings": ["Symbol XYZ not found in database"],
  "import_id": "uuid-here"
}
```

#### POST /api/transactions/confirm-import/{import_id}
Confirm and commit the previewed import.

### Entities

#### GET /api/entities
List all entities.

#### POST /api/entities
Create a new entity.

### Accounts

#### GET /api/accounts
List all accounts (optionally filtered by entity).

#### POST /api/accounts
Create a new account.

---

## Frontend Architecture

### Project Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Dashboard/
│   │   │   ├── KPICards.jsx
│   │   │   ├── AllocationChart.jsx
│   │   │   ├── HoldingsTable.jsx
│   │   │   └── PerformanceChart.jsx
│   │   ├── Transactions/
│   │   │   ├── ImportCSV.jsx
│   │   │   └── TransactionList.jsx
│   │   ├── Layout/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Footer.jsx
│   │   └── Common/
│   │       ├── CurrencyToggle.jsx
│   │       ├── EntityFilter.jsx
│   │       └── LoadingSpinner.jsx
│   │
│   ├── hooks/
│   │   ├── usePortfolio.js       # TanStack Query hooks for portfolio data
│   │   ├── useCurrency.js        # Currency context and state
│   │   ├── useEntityFilter.js    # Entity filter state
│   │   └── useTransactions.js    # Transaction management hooks
│   │
│   ├── services/
│   │   └── api.js                # Axios instance with interceptors
│   │
│   ├── utils/
│   │   ├── formatters.js         # Number and currency formatting
│   │   └── calculations.js       # Client-side calculation helpers
│   │
│   ├── contexts/
│   │   └── AppContext.jsx        # Global app state
│   │
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Holdings.jsx
│   │   ├── Transactions.jsx
│   │   └── Settings.jsx
│   │
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
│
├── package.json
├── vite.config.js
├── tailwind.config.js
└── Dockerfile
```

### Key Components

#### Dashboard Page
- KPI cards showing total net worth, daily change, total P&L
- Allocation pie charts (asset class, sector, account)
- Recent transactions list
- Performance line chart (historical snapshots)

#### Holdings Table
- Sortable and filterable table
- Columns: Asset, Account, Quantity, Price, Market Value, Cost Basis, Unrealized P&L ($ and %), Daily Change
- Filter by entity, account, asset class, sector
- Search by symbol or name

#### CSV Import Flow
1. Upload CSV file
2. Select source (IBKR, Meitav)
3. Preview parsed transactions
4. Review warnings (missing assets, etc.)
5. Confirm and import
6. Show success/error feedback

### State Management
- **Global**: Currency preference, entity filter
- **TanStack Query**: All server data (portfolio, holdings, transactions)
- **Local**: Form states, UI toggles

---

## Implementation Tasks

### Phase 1: Foundation Setup
- [ ] Initialize Git repository
- [ ] Create Docker Compose configuration (PostgreSQL, backend, frontend)
- [ ] Set up backend project structure with FastAPI
- [ ] Set up frontend project with Vite + React + Tailwind
- [ ] Configure Alembic for database migrations
- [ ] Create initial database schema migration
- [ ] Set up environment configuration (.env files)

### Phase 2: Database & Core Models
- [ ] Implement SQLAlchemy ORM models (entities, accounts, assets, holdings, transactions)
- [ ] Create Pydantic schemas for API validation
- [ ] Write database initialization script with seed data
- [ ] Set up database connection pooling and session management

### Phase 3: Core Backend Services
- [ ] Implement PriceFetcher service (yfinance integration)
- [ ] Implement CurrencyService (exchange rate fetching and caching)
- [ ] Implement PortfolioCalculator (P&L calculations, allocations)
- [ ] Add error handling and fallback logic for external APIs
- [ ] Write unit tests for core services

### Phase 4: API Endpoints - Dashboard
- [ ] Create dashboard router and endpoints
- [ ] Implement GET /api/dashboard/summary
- [ ] Implement portfolio breakdown calculations
- [ ] Test with different currency parameters
- [ ] Add API documentation (docstrings)

### Phase 5: API Endpoints - Holdings & Accounts
- [ ] Create holdings router and CRUD endpoints
- [ ] Create accounts router and CRUD endpoints
- [ ] Create entities router and CRUD endpoints
- [ ] Implement filtering and sorting logic
- [ ] Test all CRUD operations

### Phase 6: Transaction Management
- [ ] Implement base CSV parser
- [ ] Implement IBKR CSV parser
- [ ] Implement Meitav CSV parser
- [ ] Create transaction import endpoints (upload, preview, confirm)
- [ ] Add transaction validation logic
- [ ] Test with sample CSV files from both brokers

### Phase 7: Frontend Foundation
- [ ] Set up React Router for navigation
- [ ] Create app layout (Navbar, Sidebar)
- [ ] Implement CurrencyContext and toggle component
- [ ] Set up TanStack Query client
- [ ] Create API service with Axios
- [ ] Implement error boundary and loading states

### Phase 8: Dashboard UI
- [ ] Create KPI cards component
- [ ] Implement allocation pie chart with Recharts
- [ ] Create holdings summary table
- [ ] Add entity filter dropdown
- [ ] Implement currency toggle functionality
- [ ] Test responsiveness on different screen sizes

### Phase 9: Holdings Page
- [ ] Create sortable/filterable holdings table
- [ ] Implement search functionality
- [ ] Add filters (entity, account, asset class)
- [ ] Show detailed holding metrics
- [ ] Add click-through to asset details
- [ ] Implement CSV export functionality

### Phase 10: Transaction Import UI
- [ ] Create file upload component
- [ ] Implement CSV preview table
- [ ] Show import warnings and errors
- [ ] Add confirmation dialog
- [ ] Display import success/failure feedback
- [ ] Add transaction history view

### Phase 11: Advanced Features
- [ ] Implement daily snapshot scheduler (APScheduler)
- [ ] Create historical performance chart
- [ ] Add crypto asset support (CoinGecko integration)
- [ ] Implement Israeli stock support (TASE)
- [ ] Add manual asset valuation updates
- [ ] Create asset management page (add/edit assets)

### Phase 12: Polish & Optimization
- [ ] Add loading skeletons for async data
- [ ] Implement optimistic updates for mutations
- [ ] Add toast notifications for user actions
- [ ] Optimize database queries (eager loading, indexing)
- [ ] Add request caching for price fetcher
- [ ] Write integration tests
- [ ] Create user documentation (README)
- [ ] Add data backup/export functionality

### Phase 13: Deployment Preparation
- [ ] Optimize Docker images (multi-stage builds)
- [ ] Add health check endpoints
- [ ] Configure logging (structured logs)
- [ ] Set up database backup script
- [ ] Create startup script for local deployment
- [ ] Write deployment documentation

---

## Technical Considerations

### Currency Handling
- Store all monetary values in their native currency
- Always convert on-read, never store converted values
- Cache exchange rates daily
- Handle missing historical rates gracefully

### Market Data Reliability
- Implement retry logic with exponential backoff
- Fall back to last known price if fetch fails
- Mark stale prices (>24 hours old)
- Log all pricing failures for debugging

### Israeli Stock Support
- Use `.TA` suffix for Tel Aviv Stock Exchange (e.g., TEVA.TA)
- yfinance may have delayed data; consider TASE official API as fallback
- Handle market hours (TASE closes at 5:30 PM IST)

### Transaction Import
- Never auto-commit imports without user review
- Show clear diff/preview before confirmation
- Handle duplicate detection (same date, symbol, quantity)
- Validate symbol existence; offer to create missing assets

### Performance Optimization
- Use database indexes on foreign keys and date columns
- Implement query result caching (holdings don't change frequently)
- Lazy load transaction history
- Consider Redis for price caching in future

### Error Handling
- Return meaningful error messages to frontend
- Log all errors with context
- Implement global exception handlers in FastAPI
- Show user-friendly error messages in UI

### FIFO Cost Basis Tracking
**Why FIFO?**
- FIFO (First-In-First-Out) is the default tax treatment in many jurisdictions
- Provides accurate P&L calculations for partial sales
- Essential for capital gains tax reporting

**How it works:**

1. **Buy Transaction:**
   - Create a new `holding_lot` with purchase date, quantity, and cost_per_unit
   - Update the `holdings` aggregate (add to quantity and cost_basis)

2. **Sell Transaction:**
   - Query `holding_lots` for the holding, ordered by `purchase_date ASC` (oldest first)
   - Consume lots sequentially:
     - If lot quantity >= sell quantity: reduce the lot's `remaining_quantity`, mark as closed if fully consumed
     - If lot quantity < sell quantity: close the lot completely, continue to next lot
   - Calculate realized P&L: `(sell_price - lot_cost_per_unit) * quantity_from_this_lot`
   - Update the `holdings` aggregate (subtract from quantity and cost_basis)

3. **Example:**
   ```
   Holdings: 100 shares of AAPL
   Lots:
     - Lot 1: 50 shares @ $150 (2024-01-15)
     - Lot 2: 50 shares @ $180 (2024-03-10)

   Sell 75 shares @ $200 (2024-06-01):
     - Consume Lot 1 entirely: 50 shares @ $150 → Realized gain: 50 * ($200 - $150) = $2,500
     - Consume 25 shares from Lot 2: 25 @ $180 → Realized gain: 25 * ($200 - $180) = $500
     - Total realized gain: $3,000
     - Remaining: 25 shares @ $180 (Lot 2 partial)
   ```

4. **Database Consistency:**
   - Use database transactions to ensure atomicity
   - The `holdings.quantity` must always equal `SUM(holding_lots.remaining_quantity)`
   - The `holdings.cost_basis` must equal `SUM(holding_lots.remaining_quantity * holding_lots.cost_per_unit)`

---

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://portfolio_user:password@postgres:5432/portfolio_tracker
EXCHANGE_RATE_API_KEY=your_key_here
COINGECKO_API_KEY=optional
LOG_LEVEL=INFO
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Development Workflow

1. **Database Changes**: Create Alembic migration → Review → Apply → Update models
2. **API Changes**: Update schema → Implement endpoint → Test with Swagger UI → Update frontend
3. **Frontend Changes**: Update component → Test in browser → Commit
4. **Testing**: Run backend tests → Manual frontend testing → Integration testing

---

## Future Enhancements (Post-MVP)

- [ ] Multi-user support with authentication
- [ ] Real-time price updates via WebSocket
- [ ] Mobile-responsive PWA
- [ ] Advanced charting (candlesticks, technical indicators)
- [ ] Portfolio rebalancing recommendations
- [ ] Tax reporting (capital gains, dividends)
- [ ] Integration with broker APIs (automatic sync)
- [ ] Alerts and notifications (price targets, allocation drift)
- [ ] Benchmark comparison (S&P 500, TASE 35)
- [ ] Custom asset categories and tags

---

## Getting Started (After Implementation)

```bash
# Clone repository
git clone <repo-url>
cd portfolio_tracker

# Start services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

---

## Notes & Decisions

- **Single-user design**: No authentication required; simplifies initial implementation
- **Local deployment**: Docker Compose is sufficient; no cloud considerations yet
- **Currency support**: USD and ILS only; easily extensible to other currencies
- **Asset classes**: Stock, Crypto, Real Estate, Cash initially; expandable
- **Broker support**: IBKR and Meitav first; parser architecture supports adding more

---

**Last Updated**: 2025-12-12
**Status**: Planning Phase
**Next Step**: Begin Phase 1 - Foundation Setup