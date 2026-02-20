# Asset Detail Page (Frontend) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `/assets/:id` frontend page showing comprehensive asset detail (price, position, chart, stats, about, dividends) with Stock/ETF/Crypto layout variants.

**Architecture:** Page orchestrator (`AssetDetail.jsx`) fetches 4 API endpoints in parallel on mount, distributes data to 7 child components. Two content tabs (Overview | Transactions) share a persistent chart. Position strip shows aggregated holdings with expandable per-account breakdown. Existing Assets page slide-out gets a "View Details" link to the new page.

**Tech Stack:** React, Recharts (area chart), Tailwind CSS with CSS variable tokens, Vitest + React Testing Library

**GH Issue:** #91

**TDD Approach:** Every component follows RED -> GREEN -> REFACTOR. Write the failing test first, then implement the minimal code to make it pass.

---

## Task 0: Create worktree and branch

**Step 1: Create the worktree**

```bash
cd /Users/alonsamocha/PycharmProjects/portofolio_tracker
git worktree add .worktrees/asset-detail-page -b feature/asset-detail-page
```

**Step 2: Symlink .env for Docker**

```bash
ln -sf /Users/alonsamocha/PycharmProjects/portofolio_tracker/.env .worktrees/asset-detail-page/.env
```

**Step 3: Install frontend deps**

```bash
cd .worktrees/asset-detail-page/frontend && npm install
```

---

## Task 1: AssetDetail page skeleton (route + data fetching + loading/error states)

This is the page orchestrator - special case where we build a minimal skeleton first, then test it, because all child components depend on it existing.

**Files:**
- Test: `frontend/src/pages/__tests__/AssetDetail.test.jsx`
- Create: `frontend/src/pages/AssetDetail.jsx`
- Modify: `frontend/src/App.jsx`

### Step 1: Write the failing test

Create `frontend/src/pages/__tests__/AssetDetail.test.jsx`:

```jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AssetDetail from '../AssetDetail';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useParams: () => ({ id: '1' }),
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

const mockApi = vi.fn();
vi.mock('../../lib/index.js', () => ({
  api: (...args) => mockApi(...args),
  formatCurrency: (v) => `$${Number(v || 0).toFixed(2)}`,
  formatPercent: (v) => `${Number(v || 0).toFixed(2)}%`,
  formatDate: (d) => d || '',
  formatNumber: (v) => String(v || 0),
  formatPriceChange: () => ({ indicator: '', colorClass: '', change: '', percent: '' }),
  getChangeColor: () => '',
  getChangeIndicator: () => '',
  cn: (...args) => args.filter(Boolean).join(' '),
}));

vi.mock('../../contexts/index.js', () => ({
  useCurrency: () => ({ currency: 'USD', currencySymbol: '$' }),
}));

const mockAssetDetail = {
  id: 1, symbol: 'AAPL', name: 'Apple Inc.', asset_class: 'Stock',
  currency: 'USD', exchange: 'NASDAQ', is_favorite: false,
  last_fetched_price: 237.42, last_fetched_at: '2026-02-20T10:00:00Z',
  daily_metrics: { open: 234.80, close: 237.42, high: 238.10, low: 234.15 },
};

function mockSuccessfulFetch() {
  mockApi
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockAssetDetail) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ data: [] }) });
}

describe('AssetDetail', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('shows loading skeleton initially', () => {
    mockApi.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AssetDetail />);
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders breadcrumb with asset symbol after loading', async () => {
    mockSuccessfulFetch();
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
    expect(screen.getByText('Assets')).toBeInTheDocument();
  });

  it('shows error state when asset returns 404', async () => {
    mockApi.mockResolvedValueOnce({ ok: false, status: 404 });
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText('Asset not found')).toBeInTheDocument();
    });
  });

  it('shows error state when fetch throws', async () => {
    mockApi.mockRejectedValueOnce(new Error('Network error'));
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('switches between Overview and Transactions tabs', async () => {
    mockSuccessfulFetch();
    render(<AssetDetail />);
    await waitFor(() => screen.getByText('AAPL'));
    const txnTab = screen.getByRole('button', { name: 'Transactions' });
    fireEvent.click(txnTab);
    expect(txnTab).toHaveClass('font-semibold');
  });

  it('navigates back to assets on error CTA click', async () => {
    mockApi.mockResolvedValueOnce({ ok: false, status: 404 });
    render(<AssetDetail />);
    await waitFor(() => screen.getByText('Asset not found'));
    fireEvent.click(screen.getByText('Back to Assets'));
    expect(mockNavigate).toHaveBeenCalledWith('/assets');
  });
});
```

### Step 2: Run to verify it fails

```bash
cd frontend && npx vitest run src/pages/__tests__/AssetDetail.test.jsx
```

Expected: FAIL (module `../AssetDetail` not found)

### Step 3: Implement AssetDetail.jsx + add route

Create `frontend/src/pages/AssetDetail.jsx` with full data fetching orchestrator:
- `useParams()` for asset ID
- `useEffect` with sequential-then-parallel API fetching (first `/assets/{id}/detail`, then fan out positions + trades + dividends + prices)
- `useState` for: `asset`, `position`, `trades`, `dividends`, `priceHistory`, `chartPeriod`, `activeTab`, `loading`, `error`
- `useCallback` handlers for: `handlePeriodChange`, `handleToggleFavorite`, `handleRefreshPrice`
- Loading state: `<PageContainer><SkeletonHero /><SkeletonChart /><SkeletonCard /></PageContainer>`
- Error state: centered message with "Back to Assets" button
- Content: breadcrumb + hero placeholder + position placeholder + tabs (Overview | Transactions) + chart placeholder + tab content placeholders

Modify `frontend/src/App.jsx`: add route `<Route path="/assets/:id" ...>` with `<AssetDetail />` import.

**API endpoints used:**
- `GET /assets/{id}/detail` -> `setAsset(data)` (returns `AssetDetailResponse`)
- `GET /positions?limit=100&display_currency=USD` -> filter client-side by `asset_id`, `setPosition(match)`
- `GET /transactions/trades?symbol=X&limit=500` -> `setTrades(data.items)`
- `GET /transactions/dividends?symbol=X&limit=500` -> `setDividends(data.items)`
- `GET /prices/historical/{symbol}?period=1y` -> `setPriceHistory(data)`

**Action handlers:**
- `PUT /assets/{id}/favorite` -> update `asset.is_favorite`
- `PATCH /assets/{id}/price` -> update `asset.last_fetched_price` + `last_fetched_at`

### Step 4: Run test to verify it passes

```bash
cd frontend && npx vitest run src/pages/__tests__/AssetDetail.test.jsx
```

Expected: all 6 tests PASS

### Step 5: Commit

```bash
git add frontend/src/App.jsx frontend/src/pages/AssetDetail.jsx frontend/src/pages/__tests__/AssetDetail.test.jsx
git commit -m "feat: add /assets/:id route and AssetDetail page skeleton with tests"
```

### Step 6: Run /simplify-branch

---

## Task 2: AssetHero component (TDD)

**Shows:** Symbol (mono font), name, asset type badge, exchange, currency. Large price, day change with arrow, "last updated" relative time + refresh button. Favorite star toggle top-right.

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/AssetHero.test.jsx`
- Create: `frontend/src/components/asset-detail/AssetHero.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx` (replace hero placeholder)

### Step 1: Write the failing test

Create `frontend/src/components/asset-detail/__tests__/AssetHero.test.jsx`:

**Test cases:**
1. Renders symbol and name
2. Renders asset type in a badge
3. Shows exchange and currency
4. Displays formatted price
5. Shows positive change with up indicator when close > open
6. Shows negative change with down indicator when close < open
7. Renders filled star when `is_favorite` is true
8. Renders outline star when `is_favorite` is false
9. Calls `onToggleFavorite` when star button clicked
10. Calls `onRefreshPrice` when refresh button clicked
11. Handles null `daily_metrics` gracefully (shows `last_fetched_price`, no change)

**Mock pattern:** Mock `../../../lib/index.js` for formatters. No router/context mocks needed (pure component via props).

### Step 2: Run to verify it fails

```bash
cd frontend && npx vitest run src/components/asset-detail/__tests__/AssetHero.test.jsx
```

Expected: FAIL (module `../AssetHero` not found)

### Step 3: Implement AssetHero.jsx

**Props:** `{ asset, onToggleFavorite, onRefreshPrice }`

**Price change logic:**
- Current price: `asset.daily_metrics?.close ?? asset.last_fetched_price`
- Previous: `asset.daily_metrics?.open`
- Change: `current - previous` (null if no daily_metrics)
- Change %: `(change / previous) * 100`
- Use `getChangeColor()` and `getChangeIndicator()` from `../lib`

**Layout from mock `.hero` section:**
- Row 1: identity (symbol mono + dot + name) left, star button right
- Row 2: meta (Badge type, exchange, currency)
- Row 3: price (large mono) + change (colored, with arrow)
- Row 4: "Last updated" relative time + refresh button

### Step 4: Run tests + wire into AssetDetail.jsx

Replace hero placeholder in `AssetDetail.jsx`:
```jsx
<AssetHero asset={asset} onToggleFavorite={handleToggleFavorite} onRefreshPrice={handleRefreshPrice} />
```

```bash
cd frontend && npx vitest run src/components/asset-detail/__tests__/AssetHero.test.jsx
```

Expected: all tests PASS

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/AssetHero.jsx frontend/src/components/asset-detail/__tests__/AssetHero.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add AssetHero component with price, change, and favorite toggle"
```

### Step 6: Run /simplify-branch

---

## Task 3: PositionStrip component (TDD)

**Shows:** Horizontal strip with green/red top accent border. Fields: Quantity, Avg Cost, Market Value, Total Return. Chevron expands per-account breakdown when multiple accounts. Hidden when user doesn't hold the asset.

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/PositionStrip.test.jsx`
- Create: `frontend/src/components/asset-detail/PositionStrip.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx`

### Step 1: Write the failing test

**Test cases:**
1. Renders nothing when `position` is null
2. Renders quantity, avg cost, market value, and total return
3. Applies green accent border (`--positive`) for positive P&L
4. Applies red accent border (`--negative`) for negative P&L
5. Shows expand chevron when `position.accounts.length > 1`
6. Hides chevron when single account
7. Toggles account breakdown table on chevron click
8. Shows account name, quantity, avg cost, market value, P&L per account row
9. Formats crypto quantities with 4 decimal places (when `asset.asset_class === 'Crypto'`)
10. Formats stock quantities with 0 decimal places

**Mock data:** Position with `accounts: [{name: 'IBKR Main', ...}, {name: 'Meitav IRA', ...}]`

### Step 2: Run to verify it fails

### Step 3: Implement PositionStrip.jsx

**Props:** `{ position, asset }`

**Key details:**
- Return `null` if `!position`
- `const isCrypto = asset.asset_class === 'Crypto'`
- Quantity decimals: `isCrypto ? 4 : 0`
- Unit label: `isCrypto ? asset.symbol : (qty === 1 ? 'share' : 'shares')`
- `useState(false)` for `expanded`
- Account table columns: Account, Quantity, Avg Cost, Market Value, P&L
- Use `formatCurrency`, `formatPercent`, `formatNumber` from `../../lib`

### Step 4: Run tests + wire into AssetDetail.jsx

Add between hero and content tabs: `{position && <PositionStrip position={position} asset={asset} />}`

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/PositionStrip.jsx frontend/src/components/asset-detail/__tests__/PositionStrip.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add PositionStrip with expandable per-account breakdown"
```

### Step 6: Run /simplify-branch

---

## Task 4: AssetChart component (TDD)

**Shows:** Recharts area chart with gradient fill (green up / red down). Period selector buttons (1D, 5D, 1M, 3M, 6M, 1Y). Custom tooltip.

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/AssetChart.test.jsx`
- Create: `frontend/src/components/asset-detail/AssetChart.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx`

### Step 1: Write the failing test

**Test cases:**
1. Renders "No price history available" when data is empty/null
2. Renders all period buttons (1D, 5D, 1M, 3M, 6M, 1Y)
3. Highlights the active period button
4. Calls `onPeriodChange` with correct value when period button clicked
5. Renders a chart container when data is provided (test for `ResponsiveContainer` or a data-testid)

**Note:** Recharts doesn't render well in jsdom, so test the period selector behavior and empty state. Don't try to assert on SVG chart internals.

**Mock:** Mock `recharts` to return simple divs, or use `data-testid` on wrapper elements.

### Step 2: Run to verify it fails

### Step 3: Implement AssetChart.jsx

**Props:** `{ priceHistory, activePeriod, onPeriodChange, currency }`

**Key details:**
- `const PERIODS = [{label: '1D', value: '1d'}, {label: '5D', value: '5d'}, {label: '1M', value: '1mo'}, {label: '3M', value: '3mo'}, {label: '6M', value: '6mo'}, {label: '1Y', value: '1y'}]`
- Chart data: `priceHistory?.data || []`, use `close` as the value, `date` as the key
- Color logic: `const isPositive = data.length >= 2 && data[data.length-1].close >= data[0].close`
- Use `useChartColors()` from `../../hooks/useChartColors`
- `<ResponsiveContainer width="100%" height={340}>`
- `<AreaChart>` with `<Area type="monotone" dataKey="close" />`
- Gradient via `<defs><linearGradient>` using positive/negative color
- XAxis: format dates, YAxis: format currency (compact)
- Custom tooltip component with date + formatted price
- Period bar below chart: row of buttons, active gets `bg-accent text-white`

**Reference:** Follow the exact Recharts pattern from `HistoricalPerformanceChart.jsx` (`frontend/src/components/HistoricalPerformanceChart.jsx`).

### Step 4: Run tests + wire into AssetDetail.jsx

Replace chart placeholder:
```jsx
<AssetChart priceHistory={priceHistory} activePeriod={chartPeriod} onPeriodChange={handlePeriodChange} currency={asset.currency} />
```

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/AssetChart.jsx frontend/src/components/asset-detail/__tests__/AssetChart.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add AssetChart with Recharts area chart and period selector"
```

### Step 6: Run /simplify-branch

---

## Task 5: AssetStatsGrid component (TDD)

**Shows:** Card with "Key Statistics" title + 4-col grid of label/value pairs. Grid adapts per asset type (Stock 16 items, ETF 8, Crypto 10). Responsive: 3-col tablet, 2-col mobile.

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/AssetStatsGrid.test.jsx`
- Create: `frontend/src/components/asset-detail/AssetStatsGrid.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx`

### Step 1: Write the failing test

**Test cases:**
1. Renders "Key Statistics" title
2. Shows Stock-specific labels: "P/E (TTM)", "EPS (TTM)", "Beta", "52W Range"
3. Shows ETF-specific labels: "NAV", "Expense Ratio", "Fund Family"
4. Shows Crypto-specific labels: "Circulating Supply", "Max Supply", "ATH", "ATL"
5. Displays `'--'` for null metric values
6. Does not show Stock labels when asset is ETF

**Mock assets:** One per type (Stock with daily_metrics, ETF, Crypto).

### Step 2: Run to verify it fails

### Step 3: Implement AssetStatsGrid.jsx

**Props:** `{ asset }`

**Key function:** `getStatsItems(asset)` returns `[{label, value}]` based on `asset.asset_class`:

- **Stock:** Prev Close, Open, Day Range, 52W Range, Market Cap, Volume, Avg Volume, Beta, P/E TTM, Forward P/E, EPS TTM, Earnings Date, Div Yield, Ex-Div Date, 1Y Target Est, PEG Ratio
- **ETF:** NAV, Expense Ratio, Fund Family, Day Range, 52W Range, Volume, Avg Volume, Div Yield
- **Crypto:** Market Cap, Rank, 24h Volume, Circulating Supply, Max Supply, Dominance, ATH, ATH Date, ATL, ATL Date

**Formatting:** Use `formatCurrency`, `formatNumber`, `formatPercent`, `formatDate` from `../../lib`. Null -> `'--'`.

**Grid CSS:** `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4` with border-b + border-r on items.

### Step 4: Run tests + wire into AssetDetail.jsx Overview tab

```jsx
{activeTab === 'Overview' && <AssetStatsGrid asset={asset} />}
```

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/AssetStatsGrid.jsx frontend/src/components/asset-detail/__tests__/AssetStatsGrid.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add AssetStatsGrid with type-adaptive 4-col layout"
```

### Step 6: Run /simplify-branch

---

## Task 6: AssetAbout component (TDD)

**Shows:** Collapsible card with "About" title + chevron. Body: description text + type-specific meta rows (key-value).

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/AssetAbout.test.jsx`
- Create: `frontend/src/components/asset-detail/AssetAbout.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx`

### Step 1: Write the failing test

**Test cases:**
1. Renders "About" title
2. Shows asset description text
3. Shows "No description available." when description is null
4. Toggles body visibility on header click (collapse/expand)
5. Shows Stock meta rows: Category, Industry, CEO, Employees, Website
6. Shows ETF meta rows: Category, Fund Family, Website
7. Shows Crypto meta rows: Category, Website
8. Renders website as external link with correct href

### Step 2: Run to verify it fails

### Step 3: Implement AssetAbout.jsx

**Props:** `{ asset }`

- `useState(true)` for `expanded`
- Chevron rotates 90deg when collapsed (`transform rotate(-90deg)`)
- Website: extract hostname from URL, render as `<a>` with external arrow icon
- Meta rows: flex justify-between with border-b separator

### Step 4: Run tests + wire into AssetDetail.jsx

Add to Overview tab below StatsGrid, inside a 2-column grid (left column):
```jsx
<div className={`grid gap-6 mt-6 ${hasDividend ? 'lg:grid-cols-2' : ''} items-start`}>
  <AssetAbout asset={asset} />
  {hasDividend && <div className="flex flex-col gap-6">{/* Dividend next task */}</div>}
</div>
```

Where `hasDividend = asset.daily_metrics?.dividend_yield != null && asset.asset_class !== 'Crypto'`

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/AssetAbout.jsx frontend/src/components/asset-detail/__tests__/AssetAbout.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add collapsible AssetAbout with type-specific meta rows"
```

### Step 6: Run /simplify-branch

---

## Task 7: AssetDividend component (TDD)

**Shows:** Card with "Dividend Income" title. 2x2 metrics grid (Annual Income, Yield on Cost, Per Share/Year, Current Yield). Bottom meta rows: Next Ex-Dividend, Payout Ratio.

**Files:**
- Test: `frontend/src/components/asset-detail/__tests__/AssetDividend.test.jsx`
- Create: `frontend/src/components/asset-detail/AssetDividend.jsx`
- Modify: `frontend/src/pages/AssetDetail.jsx`

### Step 1: Write the failing test

**Test cases:**
1. Renders "Dividend Income" title
2. Shows annual income computed from `position.total_quantity * daily_metrics.dividend_rate`
3. Shows current yield from `daily_metrics.dividend_yield`
4. Shows per share/year from `daily_metrics.dividend_rate`
5. Shows yield on cost from `dividend_rate / avg_cost_per_unit`
6. Shows `'--'` for income/yield-on-cost when position is null
7. Shows ex-dividend date
8. Shows payout ratio

### Step 2: Run to verify it fails

### Step 3: Implement AssetDividend.jsx

**Props:** `{ asset, position }`

**Computations:**
- `annualIncome = position ? position.total_quantity * asset.daily_metrics.dividend_rate : null`
- `yieldOnCost = position ? (asset.daily_metrics.dividend_rate / position.avg_cost_per_unit) * 100 : null`
- `perShareYear = asset.daily_metrics?.dividend_rate`
- `currentYield = asset.daily_metrics?.dividend_yield`
- Use `formatCurrency`, `formatPercent`, `formatDate`

### Step 4: Run tests + wire into AssetDetail.jsx

Add to right column of Overview grid (inside the `hasDividend` block):
```jsx
<AssetDividend asset={asset} position={position} />
```

### Step 5: Commit

```bash
git add frontend/src/components/asset-detail/AssetDividend.jsx frontend/src/components/asset-detail/__tests__/AssetDividend.test.jsx frontend/src/pages/AssetDetail.jsx
git commit -m "feat: add AssetDividend card with income metrics"
```

### Step 6: Run /simplify-branch

---

## Task 8: Transactions tab content

**Shows:** Merged table of trades + dividends sorted by date descending. Columns: Date, Type (badge), Quantity, Price, Total, Account. Empty state when no transactions.

**Files:**
- Modify: `frontend/src/pages/AssetDetail.jsx` (add Transactions tab rendering)
- Update: `frontend/src/pages/__tests__/AssetDetail.test.jsx` (add transaction tab tests)

### Step 1: Add failing test cases to existing AssetDetail test

Add to `AssetDetail.test.jsx`:
- Shows "No transactions" empty state when trades and dividends are empty
- Renders transaction rows when data exists (mock trades array)
- Shows TransactionBadge with correct type

### Step 2: Run to verify new tests fail

### Step 3: Implement Transactions tab in AssetDetail.jsx

- `useMemo` to merge trades + dividends, sort by date desc
- Map dividends to a common shape: `{date, type: item.type, quantity: null, price: null, total: item.amount, account: item.account_name}`
- Use `TransactionBadge` for type column
- Use `EmptyState` for empty case
- Wrap in `Card` component
- Crypto: 4 decimal places for quantity

### Step 4: Run tests to verify they pass

### Step 5: Commit

```bash
git add frontend/src/pages/AssetDetail.jsx frontend/src/pages/__tests__/AssetDetail.test.jsx
git commit -m "feat: add Transactions tab with merged trade/dividend table"
```

### Step 6: Run /simplify-branch

---

## Task 9: Update Assets page slide-out with "View Details" link

**Files:**
- Modify: `frontend/src/pages/Assets.jsx`

### Step 1: Add "View Details" button

In `AssetDetailSlideOut` (around line 312 in Assets.jsx), add a button near the existing "View in Holdings" button:

```jsx
<button onClick={() => navigate(`/assets/${asset.id}`)} className="btn btn-primary w-full">
  View Details
</button>
```

### Step 2: Verify manually

Click asset row -> slide-out opens -> click "View Details" -> navigates to `/assets/:id`.

### Step 3: Commit

```bash
git add frontend/src/pages/Assets.jsx
git commit -m "feat: add View Details link in asset slide-out panel"
```

### Step 4: Run /simplify-branch

---

## Task 10: Navbar highlighting for /assets sub-routes

**Files:**
- Possibly modify: `frontend/src/components/Layout/Navbar.jsx`

### Step 1: Test in browser

Navigate to `/assets/1`. Check if "Assets" nav link is highlighted.

React Router v6 `NavLink` uses prefix matching by default, so it should already work. If it does, **skip this task entirely**.

### Step 2: If not highlighted, fix

Add `end={link.to === '/'}` to NavLink so only the root route uses exact matching:

```jsx
<NavLink key={link.to} to={link.to} end={link.to === '/'} className={({isActive}) => cn(...)}>
```

### Step 3: Commit (only if changed)

```bash
git add frontend/src/components/Layout/Navbar.jsx
git commit -m "fix: ensure Assets nav link highlights on sub-routes"
```

### Step 4: Run /simplify-branch

---

## Task 11: Final verification and PR

### Step 1: Run all frontend tests

```bash
cd frontend && npx vitest run
```

All tests must pass.

### Step 2: Visual verification checklist

- [ ] Stock asset page (e.g., AAPL): hero, stats, chart, about, dividend, position strip
- [ ] ETF asset page (e.g., SPY): adapted stats, no PEG/EPS rows
- [ ] Crypto asset page (e.g., BTC): single-column layout, no dividend card, crypto stats
- [ ] Light mode and dark mode
- [ ] Favorite toggle (star fills/empties, persists on reload)
- [ ] Chart period switching (1D through 1Y)
- [ ] Position strip expand/collapse (multi-account)
- [ ] Position strip hidden when asset not held
- [ ] About section collapse/expand
- [ ] Tab switching (Overview <-> Transactions)
- [ ] Transaction table with badges
- [ ] Empty state for assets with no transactions
- [ ] Assets page slide-out "View Details" navigation
- [ ] Breadcrumb "Assets" link navigates back
- [ ] 404 error state with invalid asset ID
- [ ] Responsive: mobile, tablet, desktop

### Step 3: Create PR

```bash
gh pr create --title "feat: asset detail page frontend (#91)" --body "$(cat <<'EOF'
## Summary

- Add `/assets/:id` route with full asset detail page
- 6 child components: AssetHero, PositionStrip, AssetChart, AssetStatsGrid, AssetAbout, AssetDividend
- Stock/ETF/Crypto layout variants with type-adaptive stats grid
- Recharts area chart with period selector (1D-1Y)
- Expandable per-account position breakdown
- Collapsible About section with type-specific meta
- Dividend income card with computed metrics
- Transactions tab with merged trades + dividends table
- "View Details" link added to Assets page slide-out

Closes #91

**Deferred:** Performance horizontal bar chart (separate follow-up)

## Test plan

- [ ] Unit tests for all 6 child components + page integration test
- [ ] Visual verification on Stock, ETF, and Crypto assets
- [ ] Light/dark mode
- [ ] Responsive layout
- [ ] Error states (404, network failure)

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Reusable Utilities Reference

| Utility | Import | Purpose |
|---------|--------|---------|
| `api` | `../lib` | HTTP client with auth |
| `formatCurrency` | `../lib` | `$1,234.56` formatting |
| `formatPercent` | `../lib` | `+12.34%` with sign |
| `formatNumber` | `../lib` | `1,234,567` with separators |
| `formatDate` | `../lib` | Date formatting + relative |
| `formatPriceChange` | `../lib` | Returns `{indicator, colorClass, change, percent}` |
| `getChangeColor` | `../lib` | Returns Tailwind color class for pos/neg |
| `getChangeIndicator` | `../lib` | Returns up/down arrow |
| `cn` | `../lib` | Classname merger |
| `useCurrency` | `../contexts` | Active currency + symbol |
| `useChartColors` | `../hooks/useChartColors` | Theme-aware Recharts colors |
| `Card`, `CardTitle` | `../components/ui/Card` | Card container |
| `Badge` | `../components/ui/Badge` | Type/status badges |
| `TransactionBadge` | `../components/ui/Badge` | Auto-variant transaction badge |
| `Skeleton*` | `../components/ui/Skeleton` | Loading skeletons |
| `EmptyState` | `../components/ui/EmptyState` | Empty state with CTA |
| `PageContainer` | `../components/Layout/PageContainer` | Page wrapper |

## Testing Reference

| Pattern | Details |
|---------|---------|
| Framework | Vitest + React Testing Library |
| Setup | `./src/test/setup.js` imports `@testing-library/jest-dom` |
| API mock | `vi.mock('../../lib/index.js', () => ({ api: (...args) => mockApi(...args), ... }))` |
| Interaction | `fireEvent.click/change` (not userEvent) |
| Async | `await waitFor(() => expect(...))` |
| Child mock | `vi.mock('../ChildComponent', () => ({ default: (props) => <div data-testid="child" /> }))` |
| Cleanup | `beforeEach(() => { vi.clearAllMocks(); })` |
