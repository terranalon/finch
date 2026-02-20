import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AssetHero from '../AssetHero';

vi.mock('../../../lib/index.js', () => ({
  formatCurrency: (v) => `$${Number(v || 0).toFixed(2)}`,
  formatPercent: (v) => `${Number(v || 0).toFixed(2)}%`,
  formatDate: (d, opts) => (opts?.relative ? '5m ago' : d || ''),
  getChangeColor: (v) => (v > 0 ? 'text-positive' : v < 0 ? 'text-negative' : 'text-neutral'),
  getChangeIndicator: (v) => (v > 0 ? '\u25B2' : v < 0 ? '\u25BC' : ''),
  cn: (...args) => args.filter(Boolean).join(' '),
}));

const mockAsset = {
  id: 1,
  symbol: 'AAPL',
  name: 'Apple Inc.',
  asset_class: 'Stock',
  currency: 'USD',
  exchange: 'NASDAQ',
  is_favorite: false,
  last_fetched_price: 237.42,
  last_fetched_at: '2026-02-20T10:00:00Z',
  daily_metrics: { open: 234.80, close: 237.42, high: 238.10, low: 234.15 },
};

describe('AssetHero', () => {
  const onToggleFavorite = vi.fn();
  const onRefreshPrice = vi.fn();

  beforeEach(() => { vi.clearAllMocks(); });

  it('renders symbol and name', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });

  it('renders asset type in a badge', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText('Stock')).toBeInTheDocument();
  });

  it('shows exchange and currency', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText('USD')).toBeInTheDocument();
  });

  it('displays formatted price', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText('$237.42')).toBeInTheDocument();
  });

  it('shows positive change with up indicator when close > open', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    // close (237.42) > open (234.80) => positive change
    expect(screen.getByText(/▲/)).toBeInTheDocument();
    const changeEl = screen.getByText(/▲/);
    expect(changeEl.className).toContain('text-positive');
  });

  it('shows negative change with down indicator when close < open', () => {
    const negAsset = {
      ...mockAsset,
      daily_metrics: { open: 240.00, close: 237.42, high: 241.00, low: 236.00 },
    };
    render(<AssetHero asset={negAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText(/▼/)).toBeInTheDocument();
    const changeEl = screen.getByText(/▼/);
    expect(changeEl.className).toContain('text-negative');
  });

  it('renders filled star when is_favorite is true', () => {
    render(<AssetHero asset={{ ...mockAsset, is_favorite: true }} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByRole('button', { name: /remove from favorites/i })).toBeInTheDocument();
  });

  it('renders outline star when is_favorite is false', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByRole('button', { name: /add to favorites/i })).toBeInTheDocument();
  });

  it('calls onToggleFavorite when star button clicked', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    fireEvent.click(screen.getByRole('button', { name: /add to favorites/i }));
    expect(onToggleFavorite).toHaveBeenCalledOnce();
  });

  it('calls onRefreshPrice when refresh button clicked', () => {
    render(<AssetHero asset={mockAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    fireEvent.click(screen.getByRole('button', { name: /refresh price/i }));
    expect(onRefreshPrice).toHaveBeenCalledOnce();
  });

  it('handles null daily_metrics gracefully (shows last_fetched_price, no change)', () => {
    const noMetricsAsset = { ...mockAsset, daily_metrics: null };
    render(<AssetHero asset={noMetricsAsset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />);
    expect(screen.getByText('$237.42')).toBeInTheDocument();
    // no change indicator
    expect(screen.queryByText(/▲|▼/)).not.toBeInTheDocument();
  });
});
