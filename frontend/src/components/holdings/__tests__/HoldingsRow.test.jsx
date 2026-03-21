import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
  formatCurrency: (v) => `$${Number(v).toFixed(2)}`,
  formatPercent: (v) => `${Number(v).toFixed(2)}%`,
  formatNumber: (v) => String(v),
  getChangeColor: (v) => (v >= 0 ? 'text-positive' : 'text-negative'),
  getChangeIndicator: (v) => (v >= 0 ? '+' : '-'),
  ASSET_COLORS: { Equity: '#3B82F6', Crypto: '#F59E0B', Cash: '#10B981' },
}));

vi.mock('../../../lib/api', () => ({ default: vi.fn() }));

import { HoldingsRow } from '../HoldingsRow';

const basePosition = {
  asset_id: 1,
  symbol: 'AAPL',
  name: 'Apple Inc.',
  asset_class: 'Equity',
  category: 'Technology',
  industry: 'Consumer Electronics',
  currency: 'USD',
  is_favorite: false,
  current_price: 175.5,
  day_change_pct: 1.23,
  total_quantity: 100,
  avg_cost_per_unit_native: 150.0,
  total_cost_basis: 15000.0,
  total_market_value: 17550.0,
  total_pnl: 2550.0,
  total_pnl_pct: 17.0,
  account_count: 2,
  accounts: [],
};

function renderRow(props = {}) {
  const defaultProps = {
    position: basePosition,
    isExpanded: false,
    onToggleExpand: vi.fn(),
    onRowClick: vi.fn(),
    onToggleFavorite: vi.fn(),
    displayCurrency: 'USD',
    ...props,
  };
  return render(
    <table>
      <tbody>
        <HoldingsRow {...defaultProps} />
      </tbody>
    </table>
  );
}

describe('HoldingsRow', () => {
  it('renders symbol and name', () => {
    renderRow();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });

  it('renders asset icon with first 2 chars of symbol', () => {
    renderRow();
    expect(screen.getByText('AA')).toBeInTheDocument();
  });

  it('renders account count badge', () => {
    renderRow();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('calls onRowClick when row is clicked', () => {
    const onRowClick = vi.fn();
    renderRow({ onRowClick });
    fireEvent.click(screen.getByText('AAPL').closest('tr'));
    expect(onRowClick).toHaveBeenCalled();
  });

  it('calls onToggleExpand when expand button is clicked without triggering row click', () => {
    const onToggleExpand = vi.fn();
    const onRowClick = vi.fn();
    renderRow({ onToggleExpand, onRowClick });
    const expandBtn = screen.getByTitle('Expand');
    fireEvent.click(expandBtn);
    expect(onToggleExpand).toHaveBeenCalled();
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('calls onToggleFavorite when star is clicked without triggering row click', () => {
    const onToggleFavorite = vi.fn();
    const onRowClick = vi.fn();
    renderRow({ onToggleFavorite, onRowClick });
    const starBtn = screen.getByTitle('Add to favorites');
    fireEvent.click(starBtn);
    expect(onToggleFavorite).toHaveBeenCalled();
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('shows dash for P&L when asset_class is Cash', () => {
    renderRow({ position: { ...basePosition, asset_class: 'Cash' } });
    const cells = document.querySelectorAll('td');
    const pnlCell = cells[10];
    expect(pnlCell.textContent).toContain('\u2014');
  });
});
