/**
 * Assets Page - Finch Redesign
 *
 * Purpose: Browse all assets with market data, performance metrics, and favorites
 * Design Reference: Delta by eToro
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { Skeleton } from '../components/ui';

// ============================================
// CONSTANTS
// ============================================

const ASSET_CLASSES = ['All', 'Crypto', 'Stock', 'ETF', 'MutualFund', 'Cash', 'Other'];
const ASSET_CLASS_LABELS = {
  All: 'All',
  Crypto: 'Crypto',
  Stock: 'Stocks',
  ETF: 'ETFs',
  MutualFund: 'Funds',
  Cash: 'Forex',
  Other: 'Other',
};

const TIME_PERIODS = [
  { id: '1d', label: '1D', changeKey: 'change_1d', pctKey: 'change_1d_pct' },
  { id: '1w', label: '1W', changeKey: 'change_1w', pctKey: 'change_1w_pct' },
  { id: '1m', label: '1M', changeKey: 'change_1m', pctKey: 'change_1m_pct' },
];

// ============================================
// ICONS
// ============================================

function MagnifyingGlassIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
  );
}

function StarIcon({ className, filled }) {
  if (filled) {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
      </svg>
    );
  }
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
    </svg>
  );
}

function ChevronUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
    </svg>
  );
}

function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function ChevronUpDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15 12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
    </svg>
  );
}

function XMarkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function ArrowTopRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
    </svg>
  );
}

function BriefcaseIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M6 3.75A2.75 2.75 0 0 1 8.75 1h2.5A2.75 2.75 0 0 1 14 3.75v.443c.572.055 1.14.122 1.706.2C17.053 4.582 18 5.75 18 7.07v3.469c0 1.126-.694 2.191-1.83 2.54-1.952.599-4.024.921-6.17.921s-4.219-.322-6.17-.921C2.694 12.73 2 11.665 2 10.539V7.07c0-1.321.947-2.489 2.294-2.676A41.047 41.047 0 0 1 6 4.193V3.75Zm6.5 0v.325a41.622 41.622 0 0 0-5 0V3.75c0-.69.56-1.25 1.25-1.25h2.5c.69 0 1.25.56 1.25 1.25ZM10 10a1 1 0 0 0-1 1v.01a1 1 0 0 0 1 1h.01a1 1 0 0 0 1-1V11a1 1 0 0 0-1-1H10Z" clipRule="evenodd" />
      <path d="M3 15.055v-.684c.126.053.255.1.39.142 2.092.642 4.313.987 6.61.987 2.297 0 4.518-.345 6.61-.987.135-.041.264-.089.39-.142v.684c0 1.347-.985 2.53-2.363 2.686a41.454 41.454 0 0 1-9.274 0C3.985 17.585 3 16.402 3 15.055Z" />
    </svg>
  );
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatPrice(value, currency) {
  if (!value && value !== 0) return '—';
  return formatCurrency(value, currency);
}

/**
 * Simple SVG line chart for price history
 */
function SimpleLineChart({ data, height = 120, className }) {
  if (!data || data.length === 0) {
    return (
      <div className={cn('flex items-center justify-center text-[var(--text-tertiary)] text-sm', className)} style={{ height }}>
        No data available
      </div>
    );
  }

  const prices = data.map(d => d.close);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;

  const padding = 4;
  const chartHeight = height - padding * 2;

  // Handle single data point - show horizontal line
  if (prices.length === 1) {
    const y = padding + chartHeight / 2;
    const strokeColor = 'rgb(100, 116, 139)'; // slate-500 for neutral

    return (
      <div className={className} style={{ height }}>
        <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
          <line x1="0" y1={y} x2="100" y2={y} stroke={strokeColor} strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeDasharray="4 2" />
        </svg>
        <div className="text-center text-xs text-[var(--text-tertiary)] -mt-2">
          Market closed · Last: {formatCurrency(prices[0], 'USD')}
        </div>
      </div>
    );
  }

  // Generate path for multiple points
  const points = prices.map((price, i) => {
    const x = (i / (prices.length - 1)) * 100;
    const y = padding + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;

  // Determine if price went up or down
  const startPrice = prices[0];
  const endPrice = prices[prices.length - 1];
  const isPositive = endPrice >= startPrice;
  const strokeColor = isPositive ? 'rgb(16, 185, 129)' : 'rgb(239, 68, 68)'; // emerald-500 / red-500
  const fillColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

  // Create area path (closed path for fill)
  const areaPath = `${pathD} L 100,${height - padding} L 0,${height - padding} Z`;

  return (
    <div className={className} style={{ height }}>
      <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
        {/* Area fill */}
        <path d={areaPath} fill={fillColor} />
        {/* Line */}
        <path d={pathD} fill="none" stroke={strokeColor} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}

// ============================================
// COMPONENTS
// ============================================

function ChangeIndicator({ value, size = 'normal' }) {
  if (value === null || value === undefined) {
    return <span className="text-[var(--text-tertiary)]">—</span>;
  }

  const isPositive = value >= 0;
  const Icon = isPositive ? ChevronUpIcon : ChevronDownIcon;

  return (
    <span
      className={cn(
        'inline-flex items-center font-mono tabular-nums',
        size === 'large' ? 'text-lg font-semibold gap-1' : 'text-sm font-medium gap-0.5',
        isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
      )}
    >
      <Icon className={size === 'large' ? 'w-5 h-5' : 'w-3.5 h-3.5'} />
      {isPositive ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}

function SortableHeader({ label, sortKey, currentSort, onSort, align = 'left' }) {
  const isActive = currentSort.key === sortKey;

  return (
    <button
      onClick={() => onSort(sortKey)}
      className={cn(
        'flex items-center gap-1 font-medium text-sm transition-colors cursor-pointer',
        align === 'right' && 'justify-end w-full',
        isActive ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
      )}
    >
      {label}
      <ChevronUpDownIcon className={cn('w-4 h-4', isActive && 'text-accent')} />
    </button>
  );
}

function AssetRow({ asset, currency, userHolding, timePeriod, onToggleFavorite, onClick }) {
  const changeValue = asset[timePeriod.changeKey];
  const changePct = asset[timePeriod.pctKey];

  return (
    <tr
      onClick={() => onClick(asset)}
      className="hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
    >
      {/* Favorite */}
      <td className="px-4 py-4">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleFavorite(asset.id);
          }}
          className="p-1 rounded hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
        >
          <StarIcon
            className={cn(
              'w-5 h-5',
              asset.is_favorite
                ? 'text-amber-500'
                : 'text-[var(--text-tertiary)] hover:text-amber-500'
            )}
            filled={asset.is_favorite}
          />
        </button>
      </td>

      {/* Asset */}
      <td className="px-4 py-4">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold text-[var(--text-primary)]">{asset.symbol}</p>
              {userHolding && (
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-accent/15" title="In your portfolio">
                  <BriefcaseIcon className="w-3 h-3 text-accent" />
                </span>
              )}
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{asset.name}</p>
          </div>
        </div>
      </td>

      {/* Price - show in native currency */}
      <td className="px-4 py-4 text-right">
        <p className="font-mono tabular-nums text-[var(--text-primary)]">
          {formatPrice(asset.last_fetched_price, asset.currency)}
        </p>
      </td>

      {/* Change */}
      <td className="px-4 py-4 text-right">
        <div className="flex flex-col items-end">
          <ChangeIndicator value={changePct} />
          {changeValue !== null && changeValue !== undefined && (
            <span className={cn(
              'text-xs font-mono tabular-nums',
              changeValue >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {changeValue >= 0 ? '+' : ''}{formatCurrency(changeValue, currency)}
            </span>
          )}
        </div>
      </td>

      {/* Sector/Category */}
      <td className="px-4 py-4 text-right">
        <p className="text-sm text-[var(--text-secondary)]">
          {asset.category || asset.industry || '—'}
        </p>
      </td>
    </tr>
  );
}

function AssetDetailSlideOut({ asset, currency, userHolding, onClose, onToggleFavorite }) {
  const navigate = useNavigate();
  const [chartPeriod, setChartPeriod] = useState('1mo');
  const [historicalData, setHistoricalData] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (asset?.symbol) {
      setLoadingHistory(true);
      api(`/prices/historical/${asset.symbol}?period=${chartPeriod}`)
        .then((res) => res.ok ? res.json() : null)
        .then((data) => setHistoricalData(data))
        .catch(() => setHistoricalData(null))
        .finally(() => setLoadingHistory(false));
    }
  }, [asset?.symbol, chartPeriod]);

  if (!asset) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
      />

      {/* Slide-out Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-[var(--bg-primary)] shadow-2xl z-50 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-[var(--bg-primary)] border-b border-[var(--border-primary)] p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => onToggleFavorite(asset.id)}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
            >
              <StarIcon
                className={cn(
                  'w-5 h-5',
                  asset.is_favorite ? 'text-amber-500' : 'text-[var(--text-tertiary)]'
                )}
                filled={asset.is_favorite}
              />
            </button>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <XMarkIcon className="w-5 h-5 text-[var(--text-secondary)]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Asset Header */}
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{asset.name}</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              {asset.symbol} · {asset.asset_class} · {asset.category || asset.industry || 'N/A'}
            </p>
          </div>

          {/* Price - show in native currency */}
          <div>
            <p className="text-3xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">
              {formatPrice(asset.last_fetched_price, asset.currency)}
            </p>
            {asset.last_fetched_at && (
              <p className="text-sm text-[var(--text-tertiary)] mt-1">
                Last updated: {new Date(asset.last_fetched_at).toLocaleString()}
              </p>
            )}
          </div>

          {/* Price Chart */}
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[var(--text-primary)]">Price History</h3>
              <div className="flex gap-1">
                {[
                  { id: '1d', label: '1D' },
                  { id: '5d', label: '5D' },
                  { id: '1mo', label: '1M' },
                  { id: '3mo', label: '3M' },
                  { id: '1y', label: '1Y' },
                ].map((period) => (
                  <button
                    key={period.id}
                    onClick={() => setChartPeriod(period.id)}
                    className={cn(
                      'px-2 py-1 text-xs font-medium rounded transition-colors cursor-pointer',
                      chartPeriod === period.id
                        ? 'bg-accent text-white'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                    )}
                  >
                    {period.label}
                  </button>
                ))}
              </div>
            </div>
            {/* Price Chart */}
            <div className="h-32">
              {loadingHistory ? (
                <div className="h-full flex items-center justify-center text-[var(--text-tertiary)] text-sm">
                  Loading chart...
                </div>
              ) : historicalData?.data ? (
                <SimpleLineChart data={historicalData.data} height={128} />
              ) : (
                <div className="h-full flex items-center justify-center text-[var(--text-tertiary)] text-sm">
                  No historical data available
                </div>
              )}
            </div>
          </div>

          {/* Asset Details */}
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-4">
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-4">Asset Details</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Asset Class</span>
                <span className="text-sm text-[var(--text-primary)]">
                  {ASSET_CLASS_LABELS[asset.asset_class] || asset.asset_class}
                </span>
              </div>
              {asset.category && (
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Category</span>
                  <span className="text-sm text-[var(--text-primary)]">{asset.category}</span>
                </div>
              )}
              {asset.industry && (
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Industry</span>
                  <span className="text-sm text-[var(--text-primary)]">{asset.industry}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Currency</span>
                <span className="text-sm text-[var(--text-primary)]">{asset.currency}</span>
              </div>
              {asset.data_source && (
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Data Source</span>
                  <span className="text-sm text-[var(--text-primary)]">{asset.data_source}</span>
                </div>
              )}
            </div>
          </div>

          {/* User Holdings */}
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-4">
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3">Your Holdings</h3>
            {userHolding ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Quantity</span>
                  <span className="text-sm font-mono tabular-nums text-[var(--text-primary)]">
                    {userHolding.total_quantity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Market Value</span>
                  <span className="text-sm font-mono tabular-nums text-[var(--text-primary)]">
                    {formatCurrency(userHolding.total_market_value, currency)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Cost Basis</span>
                  <span className="text-sm font-mono tabular-nums text-[var(--text-primary)]">
                    {formatCurrency(userHolding.total_cost_basis, currency)}
                  </span>
                </div>
                <button
                  onClick={() => navigate('/holdings')}
                  className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
                >
                  View in Holdings
                  <ArrowTopRightIcon className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <p className="text-sm text-[var(--text-tertiary)]">
                You don't hold this asset
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function TableSkeleton() {
  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
      <div className="p-4 space-y-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <Skeleton className="w-8 h-8 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-40" />
            </div>
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ searchQuery }) {
  return (
    <div className="text-center py-16">
      <div className="inline-flex p-4 rounded-full bg-[var(--bg-tertiary)] mb-4">
        <MagnifyingGlassIcon className="w-8 h-8 text-[var(--text-tertiary)]" />
      </div>
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">No assets found</h3>
      <p className="text-[var(--text-secondary)] mt-1">
        {searchQuery
          ? `No assets matching "${searchQuery}"`
          : 'No assets available'}
      </p>
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function Assets() {
  const { currency } = useCurrency();
  const { selectedPortfolioId } = usePortfolio();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState('All');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [timePeriod, setTimePeriod] = useState(TIME_PERIODS[0]); // Default to 1D
  const [sort, setSort] = useState({ key: 'symbol', direction: 'asc' });
  const [selectedAsset, setSelectedAsset] = useState(null);

  // Data states
  const [assets, setAssets] = useState([]);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch assets with price changes
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';
        const [assetsRes, positionsRes] = await Promise.all([
          api(`/assets/market?limit=500&display_currency=${currency}`),
          api(`/positions?display_currency=${currency}${portfolioParam}`),
        ]);

        if (!assetsRes.ok) throw new Error('Failed to fetch assets');

        const assetsData = await assetsRes.json();
        setAssets(assetsData);

        if (positionsRes.ok) {
          const positionsData = await positionsRes.json();
          setPositions(positionsData);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currency, selectedPortfolioId]);

  // Create a map of asset_id -> position for quick lookup
  const positionsMap = useMemo(() => {
    const map = {};
    positions.forEach((pos) => {
      map[pos.asset_id] = pos;
    });
    return map;
  }, [positions]);

  // Filter assets
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchesSearch =
        asset.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        asset.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesClass = selectedClass === 'All' || asset.asset_class === selectedClass;
      const matchesFavorite = !showFavoritesOnly || asset.is_favorite;
      return matchesSearch && matchesClass && matchesFavorite;
    });
  }, [assets, searchQuery, selectedClass, showFavoritesOnly]);

  // Sort assets
  const sortedAssets = useMemo(() => {
    return [...filteredAssets].sort((a, b) => {
      let aVal = a[sort.key];
      let bVal = b[sort.key];

      // Handle null values
      if (aVal === null || aVal === undefined) aVal = sort.direction === 'asc' ? Infinity : -Infinity;
      if (bVal === null || bVal === undefined) bVal = sort.direction === 'asc' ? Infinity : -Infinity;

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (sort.direction === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });
  }, [filteredAssets, sort]);

  const handleSort = (key) => {
    setSort((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleToggleFavorite = async (assetId) => {
    try {
      const res = await api(`/assets/${assetId}/favorite`, {
        method: 'POST',
      });

      if (res.ok) {
        const updatedAsset = await res.json();
        setAssets((prev) =>
          prev.map((asset) =>
            asset.id === assetId ? { ...asset, is_favorite: updatedAsset.is_favorite } : asset
          )
        );
        // Update selected asset if open
        if (selectedAsset?.id === assetId) {
          setSelectedAsset((prev) =>
            prev ? { ...prev, is_favorite: updatedAsset.is_favorite } : null
          );
        }
      }
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const favoriteCount = assets.filter((a) => a.is_favorite).length;

  // Count assets per class for badges
  const classCounts = useMemo(() => {
    return ASSET_CLASSES.reduce((acc, cls) => {
      acc[cls] = cls === 'All'
        ? assets.length
        : assets.filter((a) => a.asset_class === cls).length;
      return acc;
    }, {});
  }, [assets]);

  // Filter out classes with 0 assets (except "All")
  const visibleClasses = ASSET_CLASSES.filter((cls) => cls === 'All' || classCounts[cls] > 0);

  if (loading) {
    return (
      <PageContainer>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-10 w-64" />
        </div>
        <Skeleton className="h-12 w-full mb-4" />
        <TableSkeleton />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <div className="text-center py-16">
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Error loading assets</h3>
          <p className="text-[var(--text-secondary)] mt-1">{error}</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Assets</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            {filteredAssets.length} of {assets.length} assets · {favoriteCount} favorites
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
          <input
            type="text"
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-9 pr-4 py-2 rounded-lg text-sm',
              'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
              'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
              'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
            )}
          />
        </div>
      </div>

      {/* Asset Class Tabs */}
      <div className="flex items-center gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg mb-4 overflow-x-auto">
        {visibleClasses.map((cls) => (
          <button
            key={cls}
            onClick={() => setSelectedClass(cls)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer whitespace-nowrap',
              selectedClass === cls
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            {ASSET_CLASS_LABELS[cls] || cls}
            <span className={cn(
              'text-xs px-1.5 py-0.5 rounded-full',
              selectedClass === cls
                ? 'bg-accent/10 text-accent'
                : 'bg-[var(--bg-secondary)] text-[var(--text-tertiary)]'
            )}>
              {classCounts[cls]}
            </span>
          </button>
        ))}
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* Time Period */}
        <div className="flex items-center gap-1 p-1 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg">
          {TIME_PERIODS.map((period) => (
            <button
              key={period.id}
              onClick={() => setTimePeriod(period)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                timePeriod.id === period.id
                  ? 'bg-accent text-white'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {period.label}
            </button>
          ))}
        </div>

        {/* Favorites Toggle */}
        <button
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer',
            showFavoritesOnly
              ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400'
              : 'bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          )}
        >
          <StarIcon className="w-4 h-4" filled={showFavoritesOnly} />
          Favorites Only
        </button>
      </div>

      {/* Table */}
      {sortedAssets.length === 0 ? (
        <EmptyState searchQuery={searchQuery} />
      ) : (
        <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden shadow-sm dark:shadow-none">
          <div className="overflow-x-auto">
            <table className="w-full table-fixed">
              <thead>
                <tr className="border-b border-[var(--border-primary)]">
                  <th className="px-4 py-3 w-14"></th>
                  <th className="px-4 py-3 text-left">
                    <SortableHeader label="Asset" sortKey="symbol" currentSort={sort} onSort={handleSort} />
                  </th>
                  <th className="px-4 py-3 w-28 text-right">
                    <SortableHeader label="Price" sortKey="last_fetched_price" currentSort={sort} onSort={handleSort} align="right" />
                  </th>
                  <th className="px-4 py-3 w-36 text-right">
                    <SortableHeader label={`Change (${timePeriod.label})`} sortKey={timePeriod.pctKey} currentSort={sort} onSort={handleSort} align="right" />
                  </th>
                  <th className="px-4 py-3 w-44 text-right">
                    <SortableHeader label="Category" sortKey="category" currentSort={sort} onSort={handleSort} align="right" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedAssets.map((asset) => (
                  <AssetRow
                    key={asset.id}
                    asset={asset}
                    currency={currency}
                    userHolding={positionsMap[asset.id]}
                    timePeriod={timePeriod}
                    onToggleFavorite={handleToggleFavorite}
                    onClick={setSelectedAsset}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-[var(--border-primary)] text-sm text-[var(--text-secondary)]">
            Showing {sortedAssets.length} of {assets.length} assets
          </div>
        </div>
      )}

      {/* Asset Detail Slide-out */}
      {selectedAsset && (
        <AssetDetailSlideOut
          asset={selectedAsset}
          currency={currency}
          userHolding={positionsMap[selectedAsset.id]}
          onClose={() => setSelectedAsset(null)}
          onToggleFavorite={handleToggleFavorite}
        />
      )}
    </PageContainer>
  );
}
