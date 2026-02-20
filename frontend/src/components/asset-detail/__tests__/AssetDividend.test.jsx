import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import AssetDividend from '../AssetDividend';

vi.mock('../../../lib/index.js', () => ({
  formatCurrency: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '--'),
  formatPercent: (v) => (v != null ? `${Number(v).toFixed(2)}%` : '--'),
  formatDate: (d) => d || '--',
}));

const assetWithDividend = {
  currency: 'USD',
  ex_dividend_date: '2026-03-10',
  daily_metrics: {
    dividend_rate: 1.00,
    dividend_yield: 0.0044,
    payout_ratio: 0.157,
  },
};

const positionWithHolding = {
  total_quantity: 50,
  avg_cost_per_unit: 200.00,
};

describe('AssetDividend', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders "Dividend Income" title', () => {
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('Dividend Income')).toBeInTheDocument();
  });

  it('shows annual income computed from position.total_quantity * dividend_rate', () => {
    // 50 * 1.00 = $50.00
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('$50.00')).toBeInTheDocument();
  });

  it('shows current yield from daily_metrics.dividend_yield', () => {
    // 0.0044 * 100 = 0.44%
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('0.44%')).toBeInTheDocument();
  });

  it('shows per share/year from daily_metrics.dividend_rate', () => {
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('$1.00')).toBeInTheDocument();
  });

  it('shows yield on cost from dividend_rate / avg_cost * 100', () => {
    // (1.00 / 200) * 100 = 0.50%
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('0.50%')).toBeInTheDocument();
  });

  it('shows "--" for income and yield-on-cost when position is null', () => {
    render(<AssetDividend asset={assetWithDividend} position={null} />);
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('shows ex-dividend date', () => {
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('2026-03-10')).toBeInTheDocument();
  });

  it('shows payout ratio', () => {
    // 0.157 * 100 = 15.70%
    render(<AssetDividend asset={assetWithDividend} position={positionWithHolding} />);
    expect(screen.getByText('15.70%')).toBeInTheDocument();
  });
});
