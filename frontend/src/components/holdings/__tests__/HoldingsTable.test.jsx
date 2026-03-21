import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
  formatCurrency: (v) => `$${Number(v).toFixed(2)}`,
  formatPercent: (v) => `${Number(v).toFixed(2)}%`,
  formatNumber: (v) => String(v),
  getChangeColor: () => '',
  getChangeIndicator: () => '',
  ASSET_COLORS: {},
}));

vi.mock('../../../lib/api', () => ({ default: vi.fn() }));

import { HoldingsTable } from '../HoldingsTable';

const positions = [
  {
    asset_id: 1, symbol: 'AAPL', name: 'Apple', asset_class: 'Equity',
    category: 'Tech', industry: 'Hardware', currency: 'USD',
    is_favorite: false, current_price: 175, day_change_pct: 1.2,
    total_quantity: 100, avg_cost_per_unit_native: 150,
    total_cost_basis_native: 15000, total_market_value_native: 17500,
    total_pnl_native: 2500, total_pnl_pct: 16.67, account_count: 1,
    accounts: [],
  },
];

describe('HoldingsTable', () => {
  it('renders all 12 column headers', () => {
    render(
      <HoldingsTable
        positions={positions}
        expandedRows={new Set()}
        sortField="total_market_value"
        sortDirection="desc"
        onSort={vi.fn()}
        onToggleExpand={vi.fn()}
        onRowClick={vi.fn()}
        onToggleFavorite={vi.fn()}
        totals={{ costBasis: 15000, marketValue: 17500, pnl: 2500, pnlPct: 16.67 }}
        currency="USD"
      />
    );
    // Sortable headers
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Qty')).toBeInTheDocument();
    expect(screen.getByText('Avg Cost')).toBeInTheDocument();
    // Cost Basis appears in both thead and tfoot
    const costBasisHeaders = screen.getAllByText('Cost Basis');
    expect(costBasisHeaders.length).toBeGreaterThanOrEqual(1);
    // Value appears in both thead (as "Value") and tfoot (as "Market Value")
    expect(screen.getByText('Value')).toBeInTheDocument();
    // P&L header in thead + "Total P&L" in tfoot
    const pnlHeaders = screen.getAllByText('P&L');
    expect(pnlHeaders.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Accts')).toBeInTheDocument();
  });

  it('renders the summary row in tfoot', () => {
    render(
      <HoldingsTable
        positions={positions}
        expandedRows={new Set()}
        sortField="total_market_value"
        sortDirection="desc"
        onSort={vi.fn()}
        onToggleExpand={vi.fn()}
        onRowClick={vi.fn()}
        onToggleFavorite={vi.fn()}
        totals={{ costBasis: 15000, marketValue: 17500, pnl: 2500, pnlPct: 16.67 }}
        currency="USD"
      />
    );
    expect(screen.getByText('All Holdings')).toBeInTheDocument();
  });

  it('renders empty state when no positions', () => {
    render(
      <HoldingsTable
        positions={[]}
        expandedRows={new Set()}
        sortField="total_market_value"
        sortDirection="desc"
        onSort={vi.fn()}
        onToggleExpand={vi.fn()}
        onRowClick={vi.fn()}
        onToggleFavorite={vi.fn()}
        totals={{ costBasis: 0, marketValue: 0, pnl: 0, pnlPct: 0 }}
        currency="USD"
        emptyMessage="No holdings match your filters"
      />
    );
    expect(screen.getByText('No holdings match your filters')).toBeInTheDocument();
  });
});
