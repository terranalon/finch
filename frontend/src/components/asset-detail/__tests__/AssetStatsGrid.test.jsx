import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import AssetStatsGrid from '../AssetStatsGrid';

vi.mock('../../../lib/index.js', () => ({
  formatCurrency: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '--'),
  formatPercent: (v) => (v != null ? `${Number(v).toFixed(2)}%` : '--'),
  formatNumber: (v) => (v != null ? String(Number(v)) : '--'),
  formatDate: (d) => d || '--',
  cn: (...args) => args.filter(Boolean).join(' '),
}));

const stockAsset = {
  asset_class: 'Stock',
  sector: 'Technology',
  industry: 'Consumer Electronics',
  beta: 1.24,
  avg_volume: 58700000,
  earnings_date: '2026-04-24',
  ex_dividend_date: '2026-02-10',
  target_est: 248.50,
  week_52_high: 244.63,
  week_52_low: 164.08,
  peg_ratio: 1.68,
  daily_metrics: {
    date: '2026-02-20',
    open: 234.80,
    high: 238.10,
    low: 234.15,
    close: 237.42,
    volume: 52300000,
    market_cap: 3620000000000,
    pe_ratio: 37.2,
    forward_pe: 31.8,
    eps: 6.38,
    dividend_rate: 1.00,
    dividend_yield: 0.0044,
    payout_ratio: 0.157,
  },
};

const etfAsset = {
  asset_class: 'ETF',
  nav: 480.12,
  expense_ratio: 0.0003,
  fund_family: 'Vanguard',
  week_52_high: 510.20,
  week_52_low: 400.10,
  avg_volume: 5000000,
  daily_metrics: {
    open: 478.00,
    high: 482.00,
    low: 477.50,
    close: 480.12,
    volume: 3200000,
    dividend_yield: 0.013,
  },
};

const cryptoAsset = {
  asset_class: 'Crypto',
  max_supply: 21000000,
  ath: 73750.00,
  ath_date: '2024-03-14',
  atl: 67.81,
  atl_date: '2013-07-06',
  daily_metrics: {
    close: 87000,
    volume: 45000000000,
    market_cap: 1700000000000,
    market_cap_rank: 1,
    circulating_supply: 19600000,
    dominance: 54.2,
  },
};

describe('AssetStatsGrid', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders "Key Statistics" title', () => {
    render(<AssetStatsGrid asset={stockAsset} />);
    expect(screen.getByText('Key Statistics')).toBeInTheDocument();
  });

  it('shows Stock-specific labels', () => {
    render(<AssetStatsGrid asset={stockAsset} />);
    expect(screen.getByText('P/E (TTM)')).toBeInTheDocument();
    expect(screen.getByText('EPS (TTM)')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('52W Range')).toBeInTheDocument();
  });

  it('shows ETF-specific labels', () => {
    render(<AssetStatsGrid asset={etfAsset} />);
    expect(screen.getByText('NAV')).toBeInTheDocument();
    expect(screen.getByText('Expense Ratio')).toBeInTheDocument();
    expect(screen.getByText('Fund Family')).toBeInTheDocument();
  });

  it('shows Crypto-specific labels', () => {
    render(<AssetStatsGrid asset={cryptoAsset} />);
    expect(screen.getByText('Circulating Supply')).toBeInTheDocument();
    expect(screen.getByText('Max Supply')).toBeInTheDocument();
    expect(screen.getByText('ATH')).toBeInTheDocument();
    expect(screen.getByText('ATL')).toBeInTheDocument();
  });

  it('displays "--" for null metric values', () => {
    const assetWithNulls = {
      ...stockAsset,
      beta: null,
      daily_metrics: { ...stockAsset.daily_metrics, pe_ratio: null },
    };
    render(<AssetStatsGrid asset={assetWithNulls} />);
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('does not show Stock labels when asset is ETF', () => {
    render(<AssetStatsGrid asset={etfAsset} />);
    expect(screen.queryByText('P/E (TTM)')).not.toBeInTheDocument();
    expect(screen.queryByText('Beta')).not.toBeInTheDocument();
  });
});
