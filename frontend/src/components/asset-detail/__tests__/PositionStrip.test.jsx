import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PositionStrip from '../PositionStrip';

vi.mock('../../../lib/index.js', () => ({
  formatCurrency: (v) => `$${Number(v || 0).toFixed(2)}`,
  formatPercent: (v, opts) => `${Number(v || 0).toFixed(opts?.decimals ?? 2)}%`,
  formatNumber: (v, opts) => Number(v || 0).toFixed(opts?.decimals ?? 2),
  cn: (...args) => args.filter(Boolean).join(' '),
}));

const stockAsset = { id: 1, symbol: 'AAPL', asset_class: 'Stock', currency: 'USD' };
const cryptoAsset = { id: 2, symbol: 'BTC', asset_class: 'Crypto', currency: 'USD' };

const singleAccountPosition = {
  asset_id: 1,
  total_quantity: 10,
  avg_cost_per_unit: 180.00,
  current_value: 2374.20,
  total_cost: 1800.00,
  total_return: 574.20,
  total_return_percent: 31.90,
  accounts: [
    { name: 'IBKR Main', quantity: 10, avg_cost: 180.00, current_value: 2374.20, return_value: 574.20, return_percent: 31.90 },
  ],
};

const multiAccountPosition = {
  ...singleAccountPosition,
  accounts: [
    { name: 'IBKR Main', quantity: 7, avg_cost: 175.00, current_value: 1661.94, return_value: 436.94, return_percent: 35.67 },
    { name: 'Meitav IRA', quantity: 3, avg_cost: 190.00, current_value: 712.26, return_value: 142.26, return_percent: 24.96 },
  ],
};

const negativePosition = {
  ...singleAccountPosition,
  total_return: -200.00,
  total_return_percent: -11.11,
  accounts: [singleAccountPosition.accounts[0]],
};

function renderStrip(position, asset = stockAsset) {
  return render(<PositionStrip position={position} asset={asset} />);
}

describe('PositionStrip', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders nothing when position is null', () => {
    const { container } = renderStrip(null);
    expect(container.firstChild).toBeNull();
  });

  it('renders quantity, avg cost, market value, and total return', () => {
    renderStrip(singleAccountPosition);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('$180.00')).toBeInTheDocument();
    expect(screen.getByText('$2374.20')).toBeInTheDocument();
    expect(screen.getByText('$574.20')).toBeInTheDocument();
  });

  it('applies green accent border for positive P&L', () => {
    const { container } = renderStrip(singleAccountPosition);
    expect(container.firstChild.className).toContain('border-positive');
  });

  it('applies red accent border for negative P&L', () => {
    const { container } = renderStrip(negativePosition);
    expect(container.firstChild.className).toContain('border-negative');
  });

  it('shows expand chevron when position has multiple accounts', () => {
    renderStrip(multiAccountPosition);
    expect(screen.getByRole('button', { name: /expand/i })).toBeInTheDocument();
  });

  it('hides chevron when single account', () => {
    renderStrip(singleAccountPosition);
    expect(screen.queryByRole('button', { name: /expand/i })).not.toBeInTheDocument();
  });

  it('toggles account breakdown table on chevron click', () => {
    renderStrip(multiAccountPosition);
    expect(screen.queryByText('IBKR Main')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /expand/i }));
    expect(screen.getByText('IBKR Main')).toBeInTheDocument();
    expect(screen.getByText('Meitav IRA')).toBeInTheDocument();
  });

  it('shows account name, quantity, avg cost, market value, P&L per account row', () => {
    renderStrip(multiAccountPosition);
    fireEvent.click(screen.getByRole('button', { name: /expand/i }));
    expect(screen.getByText('IBKR Main')).toBeInTheDocument();
    expect(screen.getByText('$175.00')).toBeInTheDocument();
    expect(screen.getByText('$1661.94')).toBeInTheDocument();
  });

  it('formats crypto quantities with 4 decimal places', () => {
    const cryptoPosition = {
      ...singleAccountPosition,
      total_quantity: 0.5432,
      accounts: [{ ...singleAccountPosition.accounts[0], quantity: 0.5432 }],
    };
    renderStrip(cryptoPosition, cryptoAsset);
    expect(screen.getByText('0.5432')).toBeInTheDocument();
  });

  it('formats stock quantities with 0 decimal places', () => {
    renderStrip(singleAccountPosition);
    expect(screen.getByText('10')).toBeInTheDocument();
  });
});
