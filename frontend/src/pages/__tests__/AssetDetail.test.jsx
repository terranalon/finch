import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AssetDetail from '../AssetDetail';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useParams: () => ({ id: '1' }),
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

// The page is a thin orchestrator over useAssetDetailData; mock the hook so the
// test exercises layout/branching rather than data fetching (covered elsewhere).
const mockHook = vi.fn();
vi.mock('../../hooks/useAssetDetailData', () => ({
  useAssetDetailData: (...args) => mockHook(...args),
}));

vi.mock('../../components/asset-detail', () => ({
  AssetHero: () => <div data-testid="asset-hero" />,
  PositionStrip: () => <div data-testid="position-strip" />,
  AssetChart: () => <div data-testid="asset-chart" />,
  AssetStatsGrid: () => <div data-testid="asset-stats-grid" />,
  AssetAbout: () => <div data-testid="asset-about" />,
  AssetDividend: () => <div data-testid="asset-dividend" />,
  RecentActivity: () => <div data-testid="recent-activity" />,
}));

const baseAsset = {
  id: 1,
  symbol: 'AAPL',
  name: 'Apple Inc.',
  asset_class: 'Stock',
  currency: 'USD',
  daily_metrics: { dividend_yield: 0.5 },
};

function hookResult(overrides = {}) {
  return {
    asset: baseAsset,
    position: null,
    recentActivity: [],
    activityCount: 0,
    priceHistory: null,
    chartPeriod: '1y',
    loading: false,
    error: null,
    currency: 'USD',
    setChartPeriod: vi.fn(),
    toggleFavorite: vi.fn(),
    refreshPrice: vi.fn(),
    ...overrides,
  };
}

describe('AssetDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes the route id to the data hook', () => {
    mockHook.mockReturnValue(hookResult());
    render(<AssetDetail />);
    expect(mockHook).toHaveBeenCalledWith('1');
  });

  it('shows loading skeleton while loading', () => {
    mockHook.mockReturnValue(hookResult({ loading: true, asset: null }));
    render(<AssetDetail />);
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('shows error state and navigates back to assets on CTA click', () => {
    mockHook.mockReturnValue(hookResult({ error: 'Asset not found', asset: null }));
    render(<AssetDetail />);
    expect(screen.getByText('Asset not found')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Back to Assets'));
    expect(mockNavigate).toHaveBeenCalledWith('/assets');
  });

  it('renders breadcrumb, hero, chart, stats, activity and about', () => {
    mockHook.mockReturnValue(hookResult());
    render(<AssetDetail />);
    expect(screen.getByText('Assets')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('asset-hero')).toBeInTheDocument();
    expect(screen.getByTestId('asset-chart')).toBeInTheDocument();
    expect(screen.getByTestId('asset-stats-grid')).toBeInTheDocument();
    expect(screen.getByTestId('recent-activity')).toBeInTheDocument();
    expect(screen.getByTestId('asset-about')).toBeInTheDocument();
  });

  it('renders PositionStrip only when a position exists', () => {
    mockHook.mockReturnValue(hookResult({ position: null }));
    const { rerender } = render(<AssetDetail />);
    expect(screen.queryByTestId('position-strip')).not.toBeInTheDocument();

    mockHook.mockReturnValue(hookResult({ position: { asset_id: 1, quantity: 10 } }));
    rerender(<AssetDetail />);
    expect(screen.getByTestId('position-strip')).toBeInTheDocument();
  });

  it('shows dividend when dividend_yield present and not Crypto', () => {
    mockHook.mockReturnValue(hookResult());
    render(<AssetDetail />);
    expect(screen.getByTestId('asset-dividend')).toBeInTheDocument();
  });

  it('hides dividend for Crypto assets', () => {
    mockHook.mockReturnValue(
      hookResult({
        asset: { ...baseAsset, asset_class: 'Crypto' },
      })
    );
    render(<AssetDetail />);
    expect(screen.queryByTestId('asset-dividend')).not.toBeInTheDocument();
  });

  it('hides dividend when dividend_yield is missing', () => {
    mockHook.mockReturnValue(
      hookResult({
        asset: { ...baseAsset, daily_metrics: {} },
      })
    );
    render(<AssetDetail />);
    expect(screen.queryByTestId('asset-dividend')).not.toBeInTheDocument();
  });
});
