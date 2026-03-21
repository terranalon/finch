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

const singlePosition = {
  asset_id: 1, symbol: 'AAPL', name: 'Apple', asset_class: 'Equity',
  category: 'Tech', industry: 'Hardware', currency: 'USD',
  is_favorite: false, current_price: 175, day_change_pct: 1.2,
  total_quantity: 100, avg_cost_per_unit_native: 150,
  total_cost_basis_native: 15000, total_market_value_native: 17500,
  total_pnl_native: 2500, total_pnl_pct: 16.67, account_count: 1,
  accounts: [],
};

function renderTable(props = {}) {
  return render(
    <HoldingsTable
      positions={[singlePosition]}
      expandedRows={new Set()}
      sortField="total_market_value"
      sortDirection="desc"
      onSort={vi.fn()}
      onToggleExpand={vi.fn()}
      onRowClick={vi.fn()}
      onToggleFavorite={vi.fn()}
      totals={{ costBasis: 15000, marketValue: 17500, pnl: 2500, pnlPct: 16.67 }}
      currency="USD"
      {...props}
    />
  );
}

describe('HoldingsTable', () => {
  it('renders all column headers', () => {
    renderTable();
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Qty')).toBeInTheDocument();
    expect(screen.getByText('Avg Cost')).toBeInTheDocument();
    expect(screen.getAllByText('Cost Basis').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Value')).toBeInTheDocument();
    expect(screen.getAllByText('P&L').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Accts')).toBeInTheDocument();
  });

  it('renders the summary row in tfoot', () => {
    renderTable();
    expect(screen.getByText('All Holdings')).toBeInTheDocument();
  });

  it('renders empty state when no positions', () => {
    renderTable({
      positions: [],
      totals: { costBasis: 0, marketValue: 0, pnl: 0, pnlPct: 0 },
      emptyMessage: 'No holdings match your filters',
    });
    expect(screen.getByText('No holdings match your filters')).toBeInTheDocument();
  });
});
