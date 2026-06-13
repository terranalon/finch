# Accounts Page Rebuild

**Issue:** #127
**Branch:** `feat/accounts-page`
**Date:** 2026-04-07

## Goal

Replace the monolithic `Accounts.jsx` (900+ lines, accordion cards) with a componentized
grid-card layout matching the accounts-playground mock. Follows the same decomposition
pattern used in Dashboard (#136) and Activity (#139).

## Mock Summary

1. **Title bar** -- "Accounts" + subtitle (`N accounts`) + "Add Account" button
2. **Allocation strip** -- horizontal stacked bar showing each account's share, with
   labeled badges underneath (broker color dot + name + %)
3. **Account card grid** -- `auto-fill, minmax(340px, 1fr)` grid of cards, each showing:
   - Broker logo + account name + type badge (Brokerage / Crypto / Pension)
   - Total value (large mono) + allocation %
   - Top 3 holdings as pills (`AAPL $4,746`) + "+N more" pill
   - Footer: sync dot (green/amber/red) + "Last synced X ago"
4. **"+ Add Account"** dashed placeholder card at the end of the grid
5. **Account sidebar** (slide-over on card click):
   - Header: logo + name, type + allocation%, View Details btn, close btn
   - Value block: total value + P&L with color
   - Summary card: Total Cost, Unrealized P&L, Positions, Sync Status
   - Holdings card: per-holding rows with icon, symbol, qty, value, P&L
   - Recent Activity card: latest transactions

## Token Mapping (mock -> real CSS vars)

| Mock token        | App token             |
|-------------------|-----------------------|
| `--bg-card`       | `--bg-secondary`      |
| `--bg-card-hover` | `--bg-tertiary`       |
| `--bg-elevated`   | `--bg-tertiary`       |
| `--border`        | `--border-primary`    |
| `--border-subtle` | `--border-subtle`     |
| `--text-primary`  | `--text-primary`      |
| `--text-secondary`| `--text-secondary`    |
| `--text-muted`    | `--text-tertiary`     |
| `--text-faint`    | `--text-faint`        |
| `--accent`        | `--accent-primary`    |
| `--accent-hover`  | `--accent-hover`      |
| `--accent-muted`  | `--blue-muted`        |
| `--positive`      | `--positive`          |
| `--negative`      | `--negative`          |
| `--warning`       | `--warning`           |

## Data Sources

| Data need                       | Endpoint                                                      |
|---------------------------------|---------------------------------------------------------------|
| Account list                    | `GET /api/accounts?is_active=true&portfolio_id={pid}`         |
| Account values + holding counts | `GET /api/dashboard/summary?display_currency={c}&portfolio_id={pid}` |
| Per-account holdings + P&L      | `GET /api/positions?display_currency={c}&portfolio_id={pid}`  |
| Broker configs                  | `GET /api/broker-data/supported-brokers`                      |
| Recent activity (sidebar only)  | `GET /api/transactions?account_name={name}&limit=5` (lazy)    |

Positions response includes `accounts[]` array per position with per-account `market_value`,
`pnl`, `quantity` -- group by `account_id` to get holdings per account.

## Architecture

```
pages/Accounts.jsx                  (thin orchestrator, ~100 lines)
hooks/useAccountsData.js            (data fetching + enrichment)
components/accounts/
  AllocationStrip.jsx               (stacked bar + badges)
  AccountCard.jsx                   (single grid card)
  AccountGrid.jsx                   (grid container + add-account card)
  AccountSidebar.jsx                (slide-over detail panel)
  icons.jsx                         (PlusIcon, ExternalLinkIcon)
  index.js                          (barrel exports)
```

Existing components reused: `PageContainer`, `Skeleton`, `BrokerLogo`, `AccountWizard`,
`AlertDialog` (inlined in old page -- extract or keep inline), `useSlideover`.

## Broker Colors (for allocation bar)

```js
const BROKER_COLORS = {
  ibkr: '#E31937',
  meitav: '#2563EB',
  kraken: '#7B61FF',
  bit2c: '#F7931A',
  binance: '#F0B90B',
};
```
Fallback: `var(--text-tertiary)` for unknown brokers.

## Tasks

### 1. Create `useAccountsData` hook
- Fetch accounts + dashboard summary + positions in parallel
- Build `accountsMap` from dashboard summary (id -> value, holding_count)
- Group positions by account_id using positions[].accounts[] breakdown
- Return `{ accounts, accountHoldings, totalValue, loading, error, currency }`
- Each account enriched with: value, holdingCount, lastSync, syncStatus, allocationPct

### 2. Build components
- **AllocationStrip**: stacked bar segments (width proportional to value), badges below
- **AccountCard**: broker logo, name+type badge, value+allocation%, top 3 holding pills, sync footer
- **AccountGrid**: CSS grid wrapper + "Add Account" dashed card
- **AccountSidebar**: uses `useSlideover`, shows summary/holdings/activity when account selected

### 3. Rebuild `Accounts.jsx`
- Thin page component using `useAccountsData` + new components
- Preserve: AccountWizard integration, delete/unlink dialog, rename capability
- Loading/error states using PageContainer + Skeleton (same pattern as Activity)

### 4. Verify & simplify
- Test on localhost:5176 (isolated vite)
- Run /simplify-branch
- Create PR targeting main

## Preserved Functionality

The existing page's management features (rename, delete/unlink, API credentials, batch upload)
move to the AccountSidebar's action buttons and the AccountDetail page (`/accounts/:id`).
The AccountWizard remains triggered by the "Add Account" button.
