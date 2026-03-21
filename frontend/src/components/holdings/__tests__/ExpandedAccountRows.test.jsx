import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
  formatCurrency: (v) => `$${Number(v).toFixed(2)}`,
  formatPercent: (v) => `${Number(v).toFixed(2)}%`,
  formatNumber: (v) => String(v),
  getChangeColor: (v) => (v >= 0 ? 'text-positive' : 'text-negative'),
  getChangeIndicator: (v) => (v >= 0 ? '+' : '-'),
}));

import { ExpandedAccountRows } from '../ExpandedAccountRows';

const accounts = [
  {
    holding_id: 1,
    account_name: 'IBKR Main',
    institution: 'Interactive Brokers',
    account_type: 'Margin',
    quantity: 60,
    cost_basis_native: 9000,
    market_value_native: 10500,
    pnl_native: 1500,
    pnl_pct: 16.67,
  },
  {
    holding_id: 2,
    account_name: 'Kraken',
    institution: 'Kraken',
    account_type: 'Crypto',
    quantity: 40,
    cost_basis_native: 6000,
    market_value_native: 7050,
    pnl_native: 1050,
    pnl_pct: 17.5,
  },
];

function renderExpanded(props = {}) {
  return render(
    <table>
      <tbody>
        <ExpandedAccountRows
          accounts={accounts}
          currency="USD"
          assetClass="Equity"
          colSpan={12}
          {...props}
        />
      </tbody>
    </table>
  );
}

describe('ExpandedAccountRows', () => {
  it('renders all account names', () => {
    renderExpanded();
    expect(screen.getByText('IBKR Main')).toBeInTheDocument();
    expect(screen.getByText('Kraken')).toBeInTheDocument();
  });

  it('shows institution and account type', () => {
    renderExpanded();
    expect(screen.getByText(/Interactive Brokers/)).toBeInTheDocument();
    expect(screen.getByText(/Margin/)).toBeInTheDocument();
  });

  it('renders cost basis and market value for each account', () => {
    renderExpanded();
    expect(screen.getByText('$9000.00')).toBeInTheDocument();
    expect(screen.getByText('$10500.00')).toBeInTheDocument();
  });
});
