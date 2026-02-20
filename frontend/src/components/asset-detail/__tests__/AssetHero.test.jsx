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

const onToggleFavorite = vi.fn();
const onRefreshPrice = vi.fn();

function renderHero(assetOverrides = {}) {
  const asset = { ...mockAsset, ...assetOverrides };
  return render(
    <AssetHero asset={asset} onToggleFavorite={onToggleFavorite} onRefreshPrice={onRefreshPrice} />
  );
}

describe('AssetHero', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders symbol and name', () => {
    renderHero();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });

  it('renders asset type in a badge', () => {
    renderHero();
    expect(screen.getByText('Stock')).toBeInTheDocument();
  });

  it('shows exchange and currency', () => {
    renderHero();
    expect(screen.getByText('NASDAQ')).toBeInTheDocument();
    expect(screen.getByText('USD')).toBeInTheDocument();
  });

  it('displays formatted price', () => {
    renderHero();
    expect(screen.getByText('$237.42')).toBeInTheDocument();
  });

  it('shows positive change with up indicator when close > open', () => {
    renderHero();
    const changeEl = screen.getByText(/\u25B2/);
    expect(changeEl).toBeInTheDocument();
    expect(changeEl.className).toContain('text-positive');
  });

  it('shows negative change with down indicator when close < open', () => {
    renderHero({ daily_metrics: { open: 240.00, close: 237.42, high: 241.00, low: 236.00 } });
    const changeEl = screen.getByText(/\u25BC/);
    expect(changeEl).toBeInTheDocument();
    expect(changeEl.className).toContain('text-negative');
  });

  it('renders filled star when is_favorite is true', () => {
    renderHero({ is_favorite: true });
    expect(screen.getByRole('button', { name: /remove from favorites/i })).toBeInTheDocument();
  });

  it('renders outline star when is_favorite is false', () => {
    renderHero();
    expect(screen.getByRole('button', { name: /add to favorites/i })).toBeInTheDocument();
  });

  it('calls onToggleFavorite when star button clicked', () => {
    renderHero();
    fireEvent.click(screen.getByRole('button', { name: /add to favorites/i }));
    expect(onToggleFavorite).toHaveBeenCalledOnce();
  });

  it('calls onRefreshPrice when refresh button clicked', () => {
    renderHero();
    fireEvent.click(screen.getByRole('button', { name: /refresh price/i }));
    expect(onRefreshPrice).toHaveBeenCalledOnce();
  });

  it('handles null daily_metrics gracefully (shows last_fetched_price, no change)', () => {
    renderHero({ daily_metrics: null });
    expect(screen.getByText('$237.42')).toBeInTheDocument();
    expect(screen.queryByText(/\u25B2|\u25BC/)).not.toBeInTheDocument();
  });
});
