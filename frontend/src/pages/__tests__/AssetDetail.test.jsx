import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AssetDetail from '../AssetDetail';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useParams: () => ({ id: '1' }),
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

const mockApi = vi.fn();
vi.mock('../../lib/index.js', () => ({
  api: (...args) => mockApi(...args),
  formatCurrency: (v) => `$${Number(v || 0).toFixed(2)}`,
  formatPercent: (v) => `${Number(v || 0).toFixed(2)}%`,
  formatDate: (d) => d || '',
  formatNumber: (v) => String(v || 0),
  formatPriceChange: () => ({ indicator: '', colorClass: '', change: '', percent: '' }),
  getChangeColor: () => '',
  getChangeIndicator: () => '',
  cn: (...args) => args.filter(Boolean).join(' '),
}));

vi.mock('../../contexts/index.js', () => ({
  useCurrency: () => ({ currency: 'USD', currencySymbol: '$' }),
}));

vi.mock('../../components/asset-detail/AssetHero', () => ({
  default: () => <div data-testid="asset-hero" />,
}));

vi.mock('../../components/asset-detail/AssetChart', () => ({
  default: () => <div data-testid="asset-chart" />,
}));

vi.mock('../../components/asset-detail/AssetStatsGrid', () => ({
  default: () => <div data-testid="asset-stats-grid" />,
}));

vi.mock('../../components/asset-detail/AssetAbout', () => ({
  default: () => <div data-testid="asset-about" />,
}));

const mockAssetDetail = {
  id: 1, symbol: 'AAPL', name: 'Apple Inc.', asset_class: 'Stock',
  currency: 'USD', exchange: 'NASDAQ', is_favorite: false,
  last_fetched_price: 237.42, last_fetched_at: '2026-02-20T10:00:00Z',
  daily_metrics: { open: 234.80, close: 237.42, high: 238.10, low: 234.15 },
};

function mockSuccessfulFetch() {
  mockApi
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockAssetDetail) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ data: [] }) });
}

describe('AssetDetail', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('shows loading skeleton initially', () => {
    mockApi.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AssetDetail />);
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders breadcrumb with asset symbol after loading', async () => {
    mockSuccessfulFetch();
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });
    expect(screen.getByText('Assets')).toBeInTheDocument();
  });

  it('shows error state when asset returns 404', async () => {
    mockApi.mockResolvedValueOnce({ ok: false, status: 404 });
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText('Asset not found')).toBeInTheDocument();
    });
  });

  it('shows error state when fetch throws', async () => {
    mockApi.mockRejectedValueOnce(new Error('Network error'));
    render(<AssetDetail />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('switches between Overview and Transactions tabs', async () => {
    mockSuccessfulFetch();
    render(<AssetDetail />);
    await waitFor(() => screen.getByText('AAPL'));
    const txnTab = screen.getByRole('button', { name: 'Transactions' });
    fireEvent.click(txnTab);
    expect(txnTab).toHaveClass('font-semibold');
  });

  it('navigates back to assets on error CTA click', async () => {
    mockApi.mockResolvedValueOnce({ ok: false, status: 404 });
    render(<AssetDetail />);
    await waitFor(() => screen.getByText('Asset not found'));
    fireEvent.click(screen.getByText('Back to Assets'));
    expect(mockNavigate).toHaveBeenCalledWith('/assets');
  });
});
