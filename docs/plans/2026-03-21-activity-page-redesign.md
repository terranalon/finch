# Activity Page Redesign + Decomposition

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Activity page to match the finalized mock (`mocks/activity-playground.html`) and decompose the 1116-line monolith into focused components following the Dashboard's patterns.

**Architecture:** Extract a `useActivityData` hook for data fetching, move UI components into `components/activity/`, update `TransactionCard` styling to match mock, replace `MultiSelectFilter` dropdowns with a single filter-icon popover, add "View Asset Details" button to the detail panel, and use `useSlideover` hook for panel behavior.

**Tech Stack:** React, Tailwind CSS, existing `useSlideover`/`useClickOutside` hooks, `PageContainer`/`PageHeader` layout components.

**Worktree:** `.worktrees/activity-redesign` on branch `feat/activity-page-redesign`

**Reference mock:** `mocks/activity-playground.html` (open in browser, toggle dark/light with top-right button)

---

## Task 1: Create `useActivityData` hook

**Files:**
- Create: `frontend/src/hooks/useActivityData.js`

**Step 1: Create the hook**

Extract the data-fetching `useEffect` from `Activity.jsx:743-811` into a standalone hook. Follow the same pattern as `useDashboardData` (`frontend/src/hooks/useDashboardData.js`).

```js
import { useState, useEffect } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import { api, transformTrade, transformDividend, transformForex, transformCash } from '../lib';

export function useActivityData() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';
      const currencyParam = currency ? `&display_currency=${currency}` : '';

      try {
        const [accountsRes, tradesRes, dividendsRes, forexRes, cashRes] = await Promise.all([
          api(`/accounts?is_active=true${portfolioParam}`),
          api(`/transactions/trades?limit=500${portfolioParam}${currencyParam}`),
          api(`/transactions/dividends?limit=500${portfolioParam}${currencyParam}`),
          api(`/transactions/forex?limit=500${portfolioParam}`),
          api(`/transactions/cash?limit=500${portfolioParam}${currencyParam}`),
        ]);

        if (cancelled) return;

        if (!accountsRes.ok) throw new Error(`Failed to fetch accounts: ${accountsRes.statusText}`);
        if (!tradesRes.ok) throw new Error(`Failed to fetch trades: ${tradesRes.statusText}`);
        if (!dividendsRes.ok) throw new Error(`Failed to fetch dividends: ${dividendsRes.statusText}`);
        if (!forexRes.ok) throw new Error(`Failed to fetch forex: ${forexRes.statusText}`);
        if (!cashRes.ok) throw new Error(`Failed to fetch cash: ${cashRes.statusText}`);

        const [accountsData, tradesData, dividendsData, forexData, cashData] = await Promise.all([
          accountsRes.json(),
          tradesRes.json(),
          dividendsRes.json(),
          forexRes.json(),
          cashRes.json(),
        ]);

        const allTransactions = [
          ...tradesData.items.map(transformTrade),
          ...dividendsData.items.map(transformDividend),
          ...forexData.items.map(transformForex),
          ...cashData.items.map(transformCash),
        ];

        allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));

        setTransactions(allTransactions);
        setAccounts(accountsData.items);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [currency, selectedPortfolioId]);

  return { transactions, accounts, loading, error, currency };
}
```

**Step 2: Verify no lint errors**

Run: `cd frontend && npx eslint src/hooks/useActivityData.js --no-error-on-unmatched-pattern`
Expected: No errors (or only warnings)

**Step 3: Commit**

```bash
git add frontend/src/hooks/useActivityData.js
git commit -m "feat(activity): extract useActivityData hook"
```

---

## Task 2: Create `icons.jsx`

**Files:**
- Create: `frontend/src/components/activity/icons.jsx`

**Step 1: Create consolidated icons file**

Extract all SVG icon components from `Activity.jsx:28-146` into a single icons file. These are: `SearchIcon`, `XMarkIcon`, `ChevronLeftIcon`, `ChevronRightIcon`, `ChevronDoubleLeftIcon`, `ChevronDoubleRightIcon`, `ChevronDownIcon`, `ArrowUpIcon`, `ArrowDownIcon`, `PlusCircleIcon`, `MinusCircleIcon`, `ReceiptPercentIcon`, `BanknotesIcon`, `ArrowsRightLeftIcon`, `CalendarIcon`.

Add two new icons needed by the filter popover and detail panel:

```jsx
export function FilterIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
    </svg>
  );
}

export function ExternalLinkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-4.5-6h6m0 0v6m0-6L9.75 14.25" />
    </svg>
  );
}

export function DollarSignIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}
```

All icons follow the same pattern: accept `className` prop, render an SVG with `fill="none"`, `stroke="currentColor"`.

**Step 2: Commit**

```bash
git add frontend/src/components/activity/icons.jsx
git commit -m "feat(activity): add consolidated icons file"
```

---

## Task 3: Create `DateRangeFilter` component

**Files:**
- Create: `frontend/src/components/activity/DateRangeFilter.jsx`

**Step 1: Create the component**

Extract `DateRangeFilter` from `Activity.jsx:513-645` and the `DATE_RANGES` constant from `Activity.jsx:152-158`. Restyle to match the mock's `date-range-btn` / `date-range-panel` classes:

Key styling differences from current:
- Button: `flex items-center gap-1.5 px-3 py-[7px] bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg text-xs font-medium text-[var(--text-secondary)]` — smaller padding, `var(--bg-elevated)` background
- Panel: `min-w-[220px] bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.4)]` — narrower, card background
- Options: `text-xs` (12px), no icon prefix, rounded-md hover state
- Calendar icon: `w-3.5 h-3.5 text-[var(--text-muted)]`
- Custom range inputs: `text-[11px]` with accent border on focus

Props: `{ value, onChange }` — same API as current. The presets are an internal constant.

Import `CalendarIcon`, `ChevronDownIcon` from `./icons`.
Import `useClickOutside` from `../../hooks/useClickOutside`.

**Step 2: Commit**

```bash
git add frontend/src/components/activity/DateRangeFilter.jsx
git commit -m "feat(activity): extract DateRangeFilter component"
```

---

## Task 4: Create `FilterPopover` component

**Files:**
- Create: `frontend/src/components/activity/FilterPopover.jsx`

**Step 1: Create the component**

This is a **new component** replacing the two `MultiSelectFilter` dropdowns. Matches the mock's filter-icon-wrapper / filter-panel pattern.

Props:
```js
{
  types,            // string[] - available types ['Trade', 'Dividend', 'Forex', 'Cash']
  selectedTypes,    // Set<string> - currently excluded types (empty = all shown)
  onTypesChange,    // (Set<string>) => void
  accounts,         // { id, name, broker }[] - available accounts
  selectedAccounts, // Set<number> - currently excluded account IDs
  onAccountsChange, // (Set<number>) => void
}
```

**Filter model (matching the mock):** Filters use an **exclusion model** — checkboxes are checked by default, unchecking excludes. The badge count shows how many filter groups have exclusions (0-2). "Clear all" resets both sets to empty (everything included).

Structure:
```
[Filter icon button (34x34)] + [badge if active]
  └─ Popover (260px wide, card bg, border, shadow)
       ├─ Header: "Filters" + "Clear all"
       ├─ Type section (collapsible, starts collapsed)
       │    └─ Checkbox per type
       └─ Accounts section (collapsible, starts collapsed)
            └─ Checkbox per account
```

Key styling from mock:
- Icon button: `w-[34px] h-[34px] flex items-center justify-center bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg text-[var(--text-muted)]`
- Badge: `absolute -top-1 -right-1 w-4 h-4 rounded-full bg-accent text-white text-[9px] font-bold`
- Section labels: `text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wide` with chevron that rotates -90deg when collapsed
- Chips: `flex items-center gap-1.5 px-2 py-[5px] rounded-md text-xs text-[var(--text-secondary)]`
- Checkboxes: `accent-color: var(--accent)` (uses native accent), `w-[13px] h-[13px]`

Import `FilterIcon`, `ChevronDownIcon` from `./icons`.
Import `useClickOutside` from `../../hooks/useClickOutside`.

**Step 2: Commit**

```bash
git add frontend/src/components/activity/FilterPopover.jsx
git commit -m "feat(activity): add FilterPopover component"
```

---

## Task 5: Create `DateGroupHeader` component

**Files:**
- Create: `frontend/src/components/activity/DateGroupHeader.jsx`

**Step 1: Create the component**

Small presentational component. Props: `{ date }` (string, e.g. `'2026-02-28'`).

Formats date as full text (e.g. "FRIDAY, FEBRUARY 28, 2026") and renders:
```
[8px accent dot] [uppercase date text] [1px line]
```

```jsx
import { cn } from '../../lib';

function formatDateHeader(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DateGroupHeader({ date }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="w-2 h-2 rounded-full bg-accent flex-shrink-0" />
      <h2 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide whitespace-nowrap">
        {formatDateHeader(date)}
      </h2>
      <div className="flex-1 h-px bg-[var(--border)]" />
    </div>
  );
}
```

Styling matches mock's `date-header` / `date-header-dot` / `date-header-text` / `date-header-line`:
- Dot: 8px, accent color
- Text: 12px (text-xs), font-semibold, uppercase, tracking-wide, muted color
- Line: 1px height, border color

**Step 2: Commit**

```bash
git add frontend/src/components/activity/DateGroupHeader.jsx
git commit -m "feat(activity): add DateGroupHeader component"
```

---

## Task 6: Create `ActivityTimeline` component

**Files:**
- Create: `frontend/src/components/activity/ActivityTimeline.jsx`

**Step 1: Create the component**

Extract timeline rendering from `Activity.jsx:974-1012`. Props:
```js
{
  groupedTransactions,  // Record<string, Transaction[]>
  currency,             // string
  onTransactionClick,   // (tx) => void
}
```

Renders sorted date groups, each with `DateGroupHeader` + card list:

```jsx
import { DateGroupHeader } from './DateGroupHeader';
import { TransactionCard } from '../Transactions/TransactionCard';
import { CalendarIcon } from './icons';

export function ActivityTimeline({ groupedTransactions, currency, onTransactionClick }) {
  const dateKeys = Object.keys(groupedTransactions).sort((a, b) => new Date(b) - new Date(a));

  if (dateKeys.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarIcon className="w-12 h-12 mx-auto text-[var(--text-muted)] mb-4" />
        <h3 className="text-lg font-medium text-[var(--text-primary)]">No transactions found</h3>
        <p className="text-[var(--text-secondary)] mt-1">
          Try adjusting your filters to see more results.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {dateKeys.map((date) => (
        <div key={date}>
          <DateGroupHeader date={date} />
          <div className="ml-4 pl-4 border-l-2 border-[var(--border)] flex flex-col gap-[10px]">
            {groupedTransactions[date].map((tx) => (
              <TransactionCard
                key={tx.id}
                tx={tx}
                variant="detailed"
                currency={currency}
                onClick={() => onTransactionClick(tx)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

Cards container: `ml-4 pl-4 border-l-2 border-[var(--border)]` with `gap-[10px]` (mock's `date-cards`).

**Step 2: Commit**

```bash
git add frontend/src/components/activity/ActivityTimeline.jsx
git commit -m "feat(activity): add ActivityTimeline component"
```

---

## Task 7: Create `TransactionDetailPanel` component

**Files:**
- Create: `frontend/src/components/activity/TransactionDetailPanel.jsx`

**Step 1: Create the component**

Extract `TransactionDetailPanel` from `Activity.jsx:199-497` and `DetailRow` from `Activity.jsx:500-507`. Also extract utility functions `getCurrencySymbol` (164-167), `formatRate` (170-173), `formatShortDate` (186-193).

Key changes from current:
1. **Use `useSlideover` hook** (from `../../hooks/useSlideover`) instead of inline scroll lock
2. **Animated slide-in**: Panel starts at `right: -420px`, transitions to `right: 0` on open with `transition: right 0.25s ease`
3. **Panel width**: 420px (mock's `detail-panel`)
4. **Close button**: 28x28 with `bg-[var(--bg-elevated)]` background, 6px radius (mock's `dp-close`)
5. **Icon in header**: 44px container, 12px radius, 22px icon (mock's `dp-tx-icon`)
6. **Amount box**: `bg-[var(--bg-elevated)]` background, 22px font-weight-700 mono
7. **Detail rows**: Label 12px muted, value 13px font-500 mono, with `border-b border-[var(--border-subtle)]` separator
8. **"View [SYMBOL] Details" button**: New addition for trades and dividends

Props:
```js
{
  transaction,  // Transaction | null
  currency,     // string
  onClose,      // () => void
}
```

The "View Asset Details" button (only rendered when `tx.type === 'trade' || tx.type === 'dividend'`):
```jsx
import { useNavigate } from 'react-router-dom';
// ... inside component:
const navigate = useNavigate();

// At the bottom of the detail rows:
{(tx.type === 'trade' || tx.type === 'dividend') && (
  <button
    onClick={() => { onClose(); navigate(`/assets/${encodeURIComponent(tx.symbol)}`); }}
    className={cn(
      'flex items-center justify-center gap-1.5 w-full py-2.5 mt-5',
      'bg-[var(--accent-muted,rgba(59,130,246,0.15))] text-accent border border-accent',
      'rounded-lg text-[13px] font-semibold cursor-pointer',
      'hover:bg-accent hover:text-white transition-colors'
    )}
  >
    <ExternalLinkIcon className="w-4 h-4" />
    View {tx.symbol} Details
  </button>
)}
```

All 4 type-specific render functions (`renderTradeDetails`, `renderDividendDetails`, `renderForexDetails`, `renderCashDetails`) move here unchanged except for styling updates to match the mock.

**Step 2: Commit**

```bash
git add frontend/src/components/activity/TransactionDetailPanel.jsx
git commit -m "feat(activity): add TransactionDetailPanel with View Asset button"
```

---

## Task 8: Create `PaginationFooter` component

**Files:**
- Create: `frontend/src/components/activity/PaginationFooter.jsx`

**Step 1: Create the component**

Extract pagination UI from `Activity.jsx:1015-1104`.

Props:
```js
{
  currentPage,     // number
  totalPages,      // number
  pageSize,        // number
  filteredCount,   // number
  totalCount,      // number
  onPageChange,    // (page: number) => void
  onPageSizeChange,// (size: number) => void
}
```

Styling updates to match mock:
- Container: `flex items-center gap-4 py-4 mt-2`
- Page size select: `text-xs text-[var(--text-muted)]`, select with `bg-[var(--bg-elevated)] border border-[var(--border)] rounded-md text-xs`
- Page info: `text-xs text-[var(--text-faint)]`
- Nav buttons: `w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md` with `hover:bg-[var(--border)]`
- Button icons: `w-3.5 h-3.5`
- Page number: `text-xs text-[var(--text-muted)] px-2`

Scroll to top on page change is handled inside the component.

Import `ChevronLeftIcon`, `ChevronRightIcon`, `ChevronDoubleLeftIcon`, `ChevronDoubleRightIcon` from `./icons`.

**Step 2: Commit**

```bash
git add frontend/src/components/activity/PaginationFooter.jsx
git commit -m "feat(activity): add PaginationFooter component"
```

---

## Task 9: Create barrel export

**Files:**
- Create: `frontend/src/components/activity/index.js`

**Step 1: Create the barrel**

```js
export { ActivityTimeline } from './ActivityTimeline';
export { DateGroupHeader } from './DateGroupHeader';
export { TransactionDetailPanel } from './TransactionDetailPanel';
export { DateRangeFilter } from './DateRangeFilter';
export { FilterPopover } from './FilterPopover';
export { PaginationFooter } from './PaginationFooter';
```

**Step 2: Commit**

```bash
git add frontend/src/components/activity/index.js
git commit -m "feat(activity): add barrel export"
```

---

## Task 10: Update `TransactionCard` styling

**Files:**
- Modify: `frontend/src/components/Transactions/TransactionCard.jsx`

**Step 1: Update the detailed variant styling**

Only the detailed variant's JSX changes — no logic changes. Update the return block starting at line 436.

Current (line 436-460):
```jsx
<div
  onClick={onClick}
  className={cn(
    'flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-lg',
    'border border-[var(--border-primary)] shadow-sm dark:shadow-none',
    onClick && 'hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer'
  )}
>
  <div className="flex items-start gap-3">
    <div className={cn('p-2 rounded-lg', style.bg)}>
      <Icon className={cn('size-4', style.text)} />
    </div>
    ...
```

New:
```jsx
<div
  onClick={onClick}
  className={cn(
    'flex items-start justify-between px-4 py-3.5 gap-3',
    'bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg',
    onClick && 'hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer'
  )}
>
  <div className="flex items-start gap-3">
    <div className={cn('w-9 h-9 rounded-[10px] flex items-center justify-center flex-shrink-0', style.bg)}>
      <Icon className={cn('w-[18px] h-[18px]', style.text)} />
    </div>
    ...
```

Also update in the detailed content render functions:
- Badge: Change `text-xs` to `text-[10px] font-bold uppercase tracking-wide px-1.5 py-px rounded`
- Symbol: Add `text-[13px]`
- Description lines: Add `text-[12px] text-[var(--text-muted)]`
- Account name: Change to `text-[11px] text-[var(--text-faint)]`

Update amount column wrapper (line 456-458):
```jsx
<div className="text-right flex-shrink-0 flex flex-col justify-center self-stretch">
```

Update amount text in `renderDetailedAmount` (the `<p>` tags around amounts):
```jsx
<p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
```

**Step 2: Verify the card still renders correctly for compact variant**

Run: `cd frontend && npx eslint src/components/Transactions/TransactionCard.jsx --no-error-on-unmatched-pattern`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/Transactions/TransactionCard.jsx
git commit -m "feat(activity): update TransactionCard styling to match mock"
```

---

## Task 11: Rewrite `Activity.jsx` page component

**Files:**
- Modify: `frontend/src/pages/Activity.jsx` (rewrite from 1116 lines to ~120 lines)

**Step 1: Rewrite the page**

Replace entire file content. The page now wires together the hook and extracted components:

```jsx
import { useState, useMemo, useEffect } from 'react';
import { useActivityData } from '../hooks/useActivityData';
import { PageContainer, PageHeader } from '../components/layout';
import { Skeleton } from '../components/ui';
import {
  ActivityTimeline,
  TransactionDetailPanel,
  DateRangeFilter,
  FilterPopover,
  PaginationFooter,
} from '../components/activity';
import { SearchIcon } from '../components/activity/icons';

const TRANSACTION_TYPES = ['Trade', 'Dividend', 'Forex', 'Cash'];

const DATE_RANGES = [
  { id: 'all', label: 'All Time', days: null },
  { id: '7d', label: 'Last 7 Days', days: 7 },
  { id: '30d', label: 'Last 30 Days', days: 30 },
  { id: '90d', label: 'Last 90 Days', days: 90 },
  { id: 'ytd', label: 'Year to Date', days: 'ytd' },
];

export default function Activity() {
  const { transactions, accounts, loading, error, currency } = useActivityData();

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [excludedTypes, setExcludedTypes] = useState(new Set());
  const [excludedAccounts, setExcludedAccounts] = useState(new Set());
  const [dateRange, setDateRange] = useState({ type: 'preset', preset: 'all', label: 'All Time' });

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Detail panel
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  // Filter + paginate + group
  const { groupedTransactions, filteredCount, totalCount, totalPages } = useMemo(() => {
    let filtered = transactions.filter((tx) => {
      // Type filter (exclusion model)
      const typeMap = { trade: 'Trade', dividend: 'Dividend', forex: 'Forex', cash: 'Cash' };
      if (excludedTypes.size > 0 && excludedTypes.has(typeMap[tx.type])) return false;

      // Account filter (exclusion model)
      if (excludedAccounts.size > 0) {
        const accountId = accounts.find((a) => a.name === tx.account_name)?.id;
        if (accountId && excludedAccounts.has(accountId)) return false;
      }

      // Search
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const symbolMatch = tx.symbol && tx.symbol.toLowerCase().includes(q);
        const nameMatch = tx.name && tx.name.toLowerCase().includes(q);
        if (!symbolMatch && !nameMatch) return false;
      }

      // Date range
      if (dateRange.type === 'custom' && dateRange.startDate && dateRange.endDate) {
        const txDate = new Date(tx.date);
        if (txDate < new Date(dateRange.startDate) || txDate > new Date(dateRange.endDate)) return false;
      } else if (dateRange.type === 'preset' && dateRange.preset !== 'all') {
        const txDate = new Date(tx.date);
        const now = new Date();
        const preset = DATE_RANGES.find((r) => r.id === dateRange.preset);
        if (preset?.days) {
          if (preset.days === 'ytd') {
            if (txDate < new Date(now.getFullYear(), 0, 1)) return false;
          } else {
            const cutoff = new Date(now);
            cutoff.setDate(cutoff.getDate() - preset.days);
            if (txDate < cutoff) return false;
          }
        }
      }

      return true;
    });

    const startIndex = (currentPage - 1) * pageSize;
    const paginated = filtered.slice(startIndex, startIndex + pageSize);

    const grouped = {};
    paginated.forEach((tx) => {
      if (!grouped[tx.date]) grouped[tx.date] = [];
      grouped[tx.date].push(tx);
    });

    return {
      groupedTransactions: grouped,
      filteredCount: filtered.length,
      totalCount: transactions.length,
      totalPages: Math.ceil(filtered.length / pageSize),
    };
  }, [transactions, searchQuery, excludedTypes, excludedAccounts, dateRange, currentPage, pageSize, accounts]);

  // Reset page on filter change
  useEffect(() => { setCurrentPage(1); }, [searchQuery, excludedTypes, excludedAccounts, dateRange]);

  if (loading) {
    return (
      <PageContainer>
        <PageHeader title="Activity" />
        <div className="flex flex-col lg:flex-row gap-4 mb-6">
          <Skeleton className="h-9 w-64" />
          <div className="flex gap-3 ml-auto">
            <Skeleton className="h-9 w-28" />
            <Skeleton className="h-9 w-9" />
          </div>
        </div>
        <div className="space-y-8">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="flex items-center gap-3 mb-4">
                <Skeleton className="w-2 h-2 rounded-full" />
                <Skeleton className="h-3 w-48" />
              </div>
              <div className="ml-4 pl-4 border-l-2 border-[var(--border)] flex flex-col gap-[10px]">
                {[1, 2].map((j) => <Skeleton key={j} className="h-[72px] w-full rounded-lg" />)}
              </div>
            </div>
          ))}
        </div>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <PageHeader title="Activity" />
        <div className="text-center py-12">
          <p className="text-negative mb-2">Error loading activity</p>
          <p className="text-[var(--text-secondary)] text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Title bar with filters inline */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-[22px] font-bold tracking-tight text-[var(--text-primary)]">Activity</h1>
        <div className="flex items-center gap-[10px]">
          {/* Search */}
          <div className="relative w-[260px]">
            <SearchIcon className="absolute left-[10px] top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-faint)] pointer-events-none" />
            <input
              type="text"
              placeholder="Search by symbol or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full py-2 pl-[34px] pr-3 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
          <FilterPopover
            types={TRANSACTION_TYPES}
            excludedTypes={excludedTypes}
            onTypesChange={setExcludedTypes}
            accounts={accounts}
            excludedAccounts={excludedAccounts}
            onAccountsChange={setExcludedAccounts}
          />
        </div>
      </div>

      <ActivityTimeline
        groupedTransactions={groupedTransactions}
        currency={currency}
        onTransactionClick={setSelectedTransaction}
      />

      <PaginationFooter
        currentPage={currentPage}
        totalPages={totalPages}
        pageSize={pageSize}
        filteredCount={filteredCount}
        totalCount={totalCount}
        onPageChange={setCurrentPage}
        onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
      />

      <TransactionDetailPanel
        transaction={selectedTransaction}
        currency={currency}
        onClose={() => setSelectedTransaction(null)}
      />
    </PageContainer>
  );
}
```

**Step 2: Verify the app compiles**

Run: `cd frontend && npx eslint src/pages/Activity.jsx --no-error-on-unmatched-pattern`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/pages/Activity.jsx
git commit -m "feat(activity): rewrite page with extracted components"
```

---

## Task 12: Visual verification + cleanup

**Step 1: Start frontend dev server and verify**

Run: `cd frontend && npm run dev`

Open browser to Activity page. Verify against the mock (`mocks/activity-playground.html`):
- [ ] Timeline layout: dot + date + line header, left-bordered card groups
- [ ] Card styling: 36px icon, badge + symbol + desc + account, amount right-aligned and vertically centered
- [ ] Amount: 15px bold mono, type-colored, tabular-nums
- [ ] Filter bar: search + date range + filter icon inline with title
- [ ] Filter popover: collapsible Type/Account sections, badge count
- [ ] Date range: presets + custom range
- [ ] Detail panel slides in from right, 420px wide
- [ ] "View Asset Details" button in panel for trades/dividends
- [ ] Pagination: page size selector, info text, nav buttons
- [ ] Dark and light modes match
- [ ] Skeleton loading states match timeline layout

**Step 2: Remove `MultiSelectFilter` import from Activity**

Verify `MultiSelectFilter` is no longer imported in `Activity.jsx` (it was removed during the rewrite). The component itself stays in `components/ui/` since `Holdings.jsx` still uses it.

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(activity): visual polish and cleanup"
```

---

## Task 13: Create PR

**Step 1: Push and create PR**

```bash
git push -u origin feat/activity-page-redesign
```

Create PR targeting `main` with title: `feat: redesign Activity page + decompose monolith (#124)`

PR body should reference:
- Closes #124
- Summary: decomposed 1116-line monolith into 8 focused files, redesigned to match mock, added "View Asset Details" button, replaced MultiSelectFilter with filter icon popover
- Test plan: visual verification against mock in both themes
