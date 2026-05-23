# Assets Page Implementation Plan

**Issue:** #126
**Branch:** `feat/assets-page`
**Mock:** `mocks/assets-playground.html`

## Overview

Rebuild the Assets page from the existing monolithic `Assets.jsx` into a componentized architecture
matching the finalized mock. The Assets page is a **global market catalog** showing all known assets
(not just user-held positions) with market data, sorting, filtering, and an asset detail sidebar.

## Key Distinction

- **Assets page** = global catalog of all system assets with market data (price, change, mkt cap, volume, sparkline)
- **Holdings page** = user's portfolio positions with cost basis and P&L
- A "portfolio badge" on the Asset column indicates which assets the user holds

## Architecture

```
Assets.jsx (page)
  +-- AssetClassTabs          (segmented control: All/Crypto/Stocks/ETFs/Forex)
  +-- AssetsFilterRow          (search input + time period toggle + favorites toggle)
  +-- AssetsTable              (table wrapper with header + body + footer)
  |     +-- AssetRow           (per-asset row with star, icon, price, change, sparkline)
  |     +-- SparklineCell      (80x28 inline SVG sparkline)
  +-- AssetDetailSidebar       (shared from dashboard -- already exists)
```

## Data Flow

1. `useAssetsData` hook fetches:
   - `GET /api/assets/market?display_currency={cur}&limit=500` -> all assets with change data
   - `GET /api/positions?display_currency={cur}&portfolio_id={pid}` -> user holdings (for portfolio badge)
2. Positions are indexed by `asset_id` into a Map for O(1) lookup
3. Filtering (asset class, search, favorites) and sorting happen client-side on the full dataset
4. Sparklines are procedurally generated from change data (same approach as mock)

## Implementation Tasks

### Task 1: useAssetsData Hook
**File:** `frontend/src/hooks/useAssetsData.js`

- Fetch from `/api/assets/market` with `display_currency` from PortfolioContext
- Fetch from `/api/positions` with `portfolio_id` from PortfolioContext
- Return `{ assets, positions, loading, error, currency, toggleFavorite }`
- `positions` is a Map keyed by `asset_id` for O(1) lookup
- `toggleFavorite(assetId)` calls `PUT /api/assets/{id}/favorite` with optimistic update

### Task 2: Page-Specific Components
**Directory:** `frontend/src/components/assets/`

#### AssetClassTabs.jsx
- Props: `tabs, activeTab, onTabChange`
- Segmented control with count badges
- Active tab: `bg-[var(--bg-secondary)]` with accent badge
- Inactive tab: `bg-transparent`, `text-[var(--text-tertiary)]`

#### AssetsFilterRow.jsx
- Props: `searchQuery, onSearchChange, selectedPeriod, onPeriodChange, showFavoritesOnly, onFavoritesToggle`
- Left: search input (240px) with magnifying glass icon
- Right: time period toggle (1D/1W/1M/1Y pills) + favorites toggle button
- Active period pill: `bg-[var(--accent-primary)] text-white`
- Active favorites: amber highlight with filled star

#### AssetsTable.jsx
- Props: `assets, positions, timePeriod, currency, sortConfig, onSort, onRowClick, onToggleFavorite`
- 7 columns: Star (40px), Asset (auto), Price (120px), Change (140px), Mkt Cap (120px), Volume (100px), Trend (100px)
- Sortable columns: symbol, price, changePct, marketCap, volume
- Footer: "Showing X of Y assets" with favorites count

#### AssetRow.jsx
- Props: `asset, position, timePeriod, currency, onToggleFavorite, onClick`
- Star toggle, colored icon circle, symbol+name+portfolio badge, price, change with indicator, mkt cap, volume, sparkline
- All numbers use `font-mono tabular-nums`
- Change colors: `text-[var(--positive)]` / `text-[var(--negative)]`

#### SparklineCell.jsx
- Props: `assetId, periodIndex, changePct`
- 80x28 SVG with cubic bezier path
- Stroke color matches change direction (positive/negative/neutral)
- Deterministic pseudo-random from seed (assetId + periodIndex)

#### icons.jsx
- MagnifyingGlassIcon, StarOutlineIcon, StarFilledIcon, BriefcaseIcon, SortIcon

### Task 3: Rewrite Assets.jsx
**File:** `frontend/src/pages/Assets.jsx`

- Import PageContainer from layout
- Wire useAssetsData hook
- Client-side filtering: asset class tabs, search (debounced), favorites toggle
- Client-side sorting with sort config state
- Loading skeleton matching table layout
- Error state with retry button
- Empty state when no assets match filters

### Task 4: Wire AssetDetailSidebar
- Import shared `AssetDetailSidebar` from `../components/dashboard`
- On row click, construct payload via `toAssetClickPayload`-style mapping
- Pass `onFavoriteToggle` for sidebar star sync

## CSS Token Mapping (Mock -> App)

| Mock Token | App Token |
|-----------|-----------|
| `--bg-base` | `--bg-primary` |
| `--bg-card` | `--bg-secondary` |
| `--bg-card-hover` | `--bg-tertiary` |
| `--bg-elevated` | `--bg-tertiary` |
| `--border` | `--border-primary` |
| `--border-subtle` | `--border-subtle` |
| `--text-primary` | `--text-primary` |
| `--text-secondary` | `--text-secondary` |
| `--text-muted` | `--text-tertiary` |
| `--text-faint` | `--text-faint` |
| `--accent` | `--accent-primary` |
| `--accent-hover` | `--accent-hover` |
| `--accent-muted` | `accent-primary` with opacity |
| `--positive` | `--positive` |
| `--negative` | `--negative` |
| `--warning` | `--amber` |

## API Field Mapping

The `/api/assets/market` response already includes: `change_1d`, `change_1d_pct`, `change_1w`,
`change_1w_pct`, `change_1m`, `change_1m_pct`. It does NOT include `change_1y`, `market_cap`,
or `volume`.

**For this PR:** Display mkt cap and volume from the `/api/assets/{id}/detail` endpoint's
`daily_metrics` if available. Since the market endpoint doesn't include these yet, show them
as "--" in the table for assets without detail data. The mock's 1Y period will also show "--"
for change values. Backend enrichment is a follow-up task.

## File Changes Summary

| File | Action |
|------|--------|
| `frontend/src/hooks/useAssetsData.js` | Create |
| `frontend/src/components/assets/index.js` | Create |
| `frontend/src/components/assets/AssetClassTabs.jsx` | Create |
| `frontend/src/components/assets/AssetsFilterRow.jsx` | Create |
| `frontend/src/components/assets/AssetsTable.jsx` | Create |
| `frontend/src/components/assets/AssetRow.jsx` | Create |
| `frontend/src/components/assets/SparklineCell.jsx` | Create |
| `frontend/src/components/assets/icons.jsx` | Create |
| `frontend/src/pages/Assets.jsx` | Rewrite |

## Out of Scope (Follow-up)

- Backend: Add `change_1y` / `change_1y_pct` to AssetMarketResponse
- Backend: Add `market_cap` and `volume` to AssetMarketResponse
- Backend: Optional sparkline data array in market response
- Mobile responsive layout
