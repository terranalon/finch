# Finch - Portfolio Tracker Redesign Summary

## Overview

**Finch** is a unified portfolio tracker that aggregates all assets (Crypto, Stocks, Banks) into a single "God mode" view. The redesign transformed the application into a focused 5-page experience that answers "How am I doing?" in 5 seconds.

### Branding
- **Name**: Finch (contains "Fin" for Finance, sounds like "Fin-Check")
- **Visual Style**: Modern SaaS (Mercury/Coinbase/Stripe inspired)
- **Color Palette**: Deep Blue (#2563EB) as accent
- **Theme**: Light + Dark mode support

---

## Pages Implemented

### 1. Overview Page (`/`)
**Purpose**: Answer "How am I doing?" at a glance.

**Features**:
- Hero section with total portfolio value and daily change
- **Performance Chart** with Time-Weighted Return (TWR) using Modified Dietz method
  - Green line when performance >= 0%, red when < 0%
  - S&P 500 benchmark comparison (gray dashed line)
  - Toggle to show/hide benchmark
  - Hover shows both portfolio and S&P 500 percentages
- **Value Chart** showing absolute portfolio value
  - Shows change amount and percentage below value
- Time range selector (1W, 1M, 3M, 1Y, ALL)
- Daily Movers section (Top Gainers / Top Losers)
- Asset Allocation breakdown (Stocks, ETFs, Cash)
- Accounts summary with values

**API Endpoints Used**:
- `GET /api/dashboard/summary` - Portfolio totals, allocation, accounts
- `GET /api/positions` - Holdings with day changes
- `GET /api/snapshots/portfolio` - Historical portfolio values
- `GET /api/transactions/cash` - Cash flows for TWR calculation
- `GET /api/dashboard/benchmark` - S&P 500 performance data (NEW)

### 2. Holdings Page (`/holdings`)
**Purpose**: View all holdings across accounts with native currency display.

**Features**:
- Searchable/filterable holdings table
- **Native Currency Display**: Each holding shows values in its native currency
  - Israeli stocks (*.TA) show in ₪ (ILS)
  - Canadian stocks (*.TO) show in CA$
  - US stocks show in $
- Expandable rows showing per-account breakdown
- Slide-out panel with detailed holding information
- Footer shows portfolio total in display currency

**API Endpoints Used**:
- `GET /api/positions` - Holdings with native currency fields

### 3. Activity Page (`/activity`)
**Purpose**: Complete transaction history across all accounts.

**Features**:
- Unified timeline of all transactions
- Filterable by type (Trades, Dividends, Forex, Cash)
- Filterable by account
- Searchable by symbol
- Time range filter

**API Endpoints Used**:
- `GET /api/transactions/trades`
- `GET /api/transactions/dividends`
- `GET /api/transactions/forex`
- `GET /api/transactions/cash`

### 4. Accounts Page (`/accounts`)
**Purpose**: Manage brokerage accounts and view individual account details.

**Features**:
- Account list with values and status
- Expandable cards with data coverage info
- Import options (Connect API, Upload File)
- Account Detail page with:
  - Performance/Value chart (same as Overview)
  - Holdings tab
  - Transactions tab
  - Import History tab
  - Settings tab

**API Endpoints Used**:
- `GET /api/accounts`
- `GET /api/snapshots/account/{id}`
- `GET /api/positions?account_id={id}`

### 5. Insights Page (`/insights`) - MOCKED
**Purpose**: Deep-dive analytics and performance breakdowns.

**Status**: Uses hardcoded mock data. Not yet wired to real APIs.

---

## Key Technical Implementations

### Time-Weighted Return (TWR) Calculation
**Location**: `frontend/src/pages/Overview.jsx`, `frontend/src/pages/AccountDetail.jsx`

Uses Modified Dietz method to calculate true investment performance excluding the effect of deposits/withdrawals:

```javascript
// Formula: Return = (Ending - Beginning - CashFlows) / (Beginning + WeightedCashFlows)
const denominator = startValue + weightedCashFlow;
const performance = ((currentValue - startValue - totalCashFlow) / denominator) * 100;
```

### S&P 500 Benchmark
**Backend**: `backend/app/routers/dashboard.py`

New endpoint that fetches SPY data from Yahoo Finance:
```python
@router.get("/benchmark")
async def get_benchmark_performance(
    period: str = Query("1mo"),
    symbol: str = Query("SPY"),
) -> dict:
    # Fetches historical data and calculates cumulative % change
```

**Frontend**: Fetches benchmark data and merges with portfolio performance by date.

### Native Currency Display
**Backend**: `backend/app/routers/positions.py`

Returns both native and converted values:
```python
{
    "currency": "ILS",
    "total_market_value_native": 2328.00,  # Native currency
    "total_market_value": 640.00,           # Display currency
    "total_pnl_native": 322.00,
    "total_pnl": 90.00,
}
```

### Green/Red Performance Line
**Location**: `frontend/src/pages/Overview.jsx`, `frontend/src/pages/AccountDetail.jsx`

Creates separate data keys for positive/negative values with zero-crossing interpolation:
```javascript
const performanceChartData = useMemo(() => {
  // For each point, set positive/negative based on value
  result.push({
    ...point,
    positive: point.portfolio >= 0 ? point.portfolio : null,
    negative: point.portfolio < 0 ? point.portfolio : null,
    sp500: benchmarkMap.get(point.date) ?? null,
  });
});
```

### Currency Conversion
**Backend**: `backend/app/services/currency_conversion_helper.py`

Handles historical exchange rate lookups and value conversion:
```python
CurrencyConversionHelper.convert_value(db, amount, from_currency, to_currency, date)
```

---

## API Endpoints Created/Modified

### New Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/benchmark` | GET | S&P 500 benchmark performance data |

### Modified Endpoints
| Endpoint | Change |
|----------|--------|
| `/api/transactions/cash` | Added `display_currency` parameter for currency conversion |
| `/api/positions` | Added native currency fields (`*_native`) |

---

## Frontend Components

### Overview.jsx
- `HeroSection` - Total value with daily change
- `HistoricalChartSection` - Performance/Value chart with benchmark
- `DailyMoversSection` - Top gainers/losers
- `AllocationSection` - Asset class breakdown
- `AccountsSection` - Account summary cards

### Holdings.jsx
- `HoldingsTable` - Main holdings table with native currency
- `HoldingsRow` - Expandable row with per-account breakdown
- `HoldingSlideout` - Detailed holding panel

### AccountDetail.jsx
- `OverviewTab` - Chart and summary (mirrors Overview page)
- `HoldingsTab` - Account-specific holdings
- `TransactionsTab` - Account transactions
- `ImportHistoryTab` - Import logs
- `SettingsTab` - Account settings

### Activity.jsx
- Unified transaction timeline
- Filter components for type, account, date range

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Dividends | Basic only (shown in Activity timeline) |
| Benchmark | S&P 500 (SPY) comparison |
| Tax Lots | Skipped for now (backend supports it) |
| Platform | Responsive web first |
| Daily Movers | Combined view (not split by market) |
| Filters | Multi-select with all options selected by default |

---

## Files Modified

### Backend
- `backend/app/routers/dashboard.py` - Added benchmark endpoint
- `backend/app/routers/positions.py` - Added native currency fields
- `backend/app/routers/transaction_views.py` - Added currency conversion to cash endpoint

### Frontend
- `frontend/src/pages/Overview.jsx` - Complete redesign with TWR, benchmark
- `frontend/src/pages/Holdings.jsx` - Native currency display
- `frontend/src/pages/Activity.jsx` - Unified transaction timeline
- `frontend/src/pages/AccountDetail.jsx` - Account detail with charts
- `frontend/src/pages/Accounts.jsx` - Account management
- `frontend/src/pages/Insights.jsx` - Mocked analytics page

---

## Known Limitations

1. **Insights page** uses mocked data - needs to be wired to real APIs
2. **Benchmark** only available on Overview page (not Account Detail)
3. **Daily Movers** not split by market (Stocks vs Crypto)
4. **Mobile responsiveness** may need additional polish

---

## Future Enhancements

1. Wire up Insights page to real data
2. Add benchmark to Account Detail page
3. Split Daily Movers by market type
4. Add more benchmark options (NASDAQ, custom)
5. Portfolio rebalancing suggestions
6. Tax lot tracking UI
