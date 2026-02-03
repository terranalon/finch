/**
 * Holdings Page - Finch Redesign
 *
 * Purpose: Detailed view of all positions with drill-down
 *
 * Wired to real API endpoints:
 * - GET /api/positions?display_currency={currency}
 * - GET /api/accounts?is_active=true
 */

import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { cn, formatCurrency, formatPercent, formatNumber, getChangeColor, getChangeIndicator, api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { Card, CardHeader, CardTitle, CardContent, MultiSelectFilter, Skeleton, SkeletonTableRow } from '../components/ui';

// Map time range to API period
const TIME_RANGE_TO_PERIOD = {
  '1W': '5d',
  '1M': '1mo',
  '3M': '3mo',
  '1Y': '1y',
};

// ============================================
// ICONS (Heroicons)
// ============================================

function SearchIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
  );
}

function ChevronRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function ChevronLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
    </svg>
  );
}

function ChevronDoubleLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m18.75 4.5-7.5 7.5 7.5 7.5m-6-15L5.25 12l7.5 7.5" />
    </svg>
  );
}

function ChevronDoubleRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5" />
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

function XMarkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
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

// ============================================
// COMPONENTS
// ============================================

/**
 * Filter bar with search and multi-select dropdowns
 */
function FilterBar({
  searchQuery,
  setSearchQuery,
  selectedAccounts,
  setSelectedAccounts,
  selectedClasses,
  setSelectedClasses,
  selectedCategories,
  setSelectedCategories,
  accounts,
  assetClasses,
  categories,
}) {
  return (
    <div className="flex flex-col lg:flex-row gap-4 mb-6">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-tertiary)]" />
        <input
          type="text"
          placeholder="Search by symbol or name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={cn(
            'w-full pl-10 pr-4 py-2.5 rounded-lg',
            'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
            'transition-colors'
          )}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <MultiSelectFilter
          label="Accounts"
          options={accounts}
          selected={selectedAccounts}
          onChange={setSelectedAccounts}
          getOptionLabel={(a) => a.name}
          getOptionValue={(a) => a.id}
        />

        <MultiSelectFilter
          label="Classes"
          options={assetClasses}
          selected={selectedClasses}
          onChange={setSelectedClasses}
          getOptionLabel={(c) => c}
          getOptionValue={(c) => c}
        />

        <MultiSelectFilter
          label="Sectors"
          options={categories}
          selected={selectedCategories}
          onChange={setSelectedCategories}
          getOptionLabel={(c) => c}
          getOptionValue={(c) => c}
        />
      </div>
    </div>
  );
}

/**
 * Sortable table header
 */
function SortableHeader({ field, label, sortField, sortDirection, onSort, align = 'left' }) {
  const isActive = sortField === field;
  const alignClass = align === 'right' ? 'justify-end' : 'justify-start';

  return (
    <th
      className={cn(
        'table-header cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors',
        align === 'right' && 'text-right'
      )}
      onClick={() => onSort(field)}
    >
      <div className={cn('flex items-center gap-1', alignClass)}>
        <span>{label}</span>
        {isActive && (
          <span className="text-accent">
            {sortDirection === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );
}

/**
 * Holdings table row
 */
function HoldingsRow({ position, currency, isExpanded, onToggle, onOpenDetail, onToggleFavorite }) {
  const dayChangeColor = getChangeColor(position.day_change_pct);
  const pnlColor = getChangeColor(position.total_pnl);
  const dayIndicator = getChangeIndicator(position.day_change_pct);
  const pnlIndicator = getChangeIndicator(position.total_pnl);

  const handleRowClick = (e) => {
    // Don't open detail if clicking on expand button or favorite star
    if (e.target.closest('[data-no-detail]')) return;
    onOpenDetail();
  };

  return (
    <>
      {/* Main row */}
      <tr
        id={`holdings-row-${position.asset_id}`}
        onClick={handleRowClick}
        className={cn(
          'table-row-hover border-b border-[var(--border-primary)] cursor-pointer',
          isExpanded && 'bg-[var(--bg-tertiary)]'
        )}
      >
        {/* Expand toggle */}
        <td className="table-cell w-10">
          <button
            data-no-detail
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            {isExpanded ? (
              <ChevronDownIcon className="w-4 h-4 text-[var(--text-secondary)]" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-[var(--text-secondary)]" />
            )}
          </button>
        </td>

        {/* Symbol */}
        <td className="table-cell whitespace-nowrap">
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold text-[var(--text-primary)]">
              {position.symbol}
            </span>
            <button
              data-no-detail
              onClick={(e) => {
                e.stopPropagation();
                onToggleFavorite();
              }}
              className="p-0.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
              title={position.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            >
              <StarIcon
                className={cn(
                  'w-4 h-4 transition-colors',
                  position.is_favorite ? 'text-amber-500' : 'text-[var(--text-tertiary)] hover:text-amber-400'
                )}
                filled={position.is_favorite}
              />
            </button>
          </div>
        </td>

        {/* Name */}
        <td className="table-cell">
          <div>
            <p className="text-[var(--text-primary)]">{position.name}</p>
            <p className="text-xs text-[var(--text-tertiary)]">
              {position.category}
              {position.industry && ` · ${position.industry}`}
            </p>
          </div>
        </td>

        {/* Price & Day Change - show in native currency */}
        <td className="table-cell text-right whitespace-nowrap">
          <p className="font-mono tabular-nums text-[var(--text-primary)]">
            {formatCurrency(position.current_price, position.currency)}
          </p>
          {position.asset_class !== 'Cash' && position.day_change_pct != null && (
            <p className={cn('text-xs tabular-nums', dayChangeColor)}>
              {dayIndicator} {formatPercent(position.day_change_pct)}
            </p>
          )}
        </td>

        {/* Quantity */}
        <td className="table-cell text-right font-mono tabular-nums text-[var(--text-primary)]">
          {formatNumber(position.total_quantity, { decimals: position.asset_class === 'Crypto' ? 4 : 0 })}
        </td>

        {/* Value - show in native currency */}
        <td className="table-cell text-right font-mono tabular-nums font-medium text-[var(--text-primary)]">
          {formatCurrency(position.total_market_value_native, position.currency, { compact: true })}
        </td>

        {/* P&L - show in native currency, blank for Cash */}
        <td className="table-cell text-right whitespace-nowrap">
          {position.asset_class === 'Cash' ? (
            <span className="text-[var(--text-tertiary)]">—</span>
          ) : (
            <>
              <p className={cn('font-mono tabular-nums font-medium', pnlColor)}>
                <span className="inline-flex items-center gap-0.5">{pnlIndicator}{formatCurrency(Math.abs(position.total_pnl_native), position.currency, { compact: true })}</span>
              </p>
              <p className={cn('text-xs tabular-nums', pnlColor)}>
                {formatPercent(position.total_pnl_pct)}
              </p>
            </>
          )}
        </td>

        {/* Accounts count */}
        <td className="table-cell text-center">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-accent/10 text-accent text-xs font-medium">
            {position.account_count}
          </span>
        </td>
      </tr>

      {/* Expanded account breakdown */}
      {isExpanded && (
        <tr>
          <td colSpan={8} className="bg-[var(--bg-tertiary)] p-0">
            <div className="px-12 py-4 border-b border-[var(--border-primary)]">
              <p className="text-sm font-medium text-[var(--text-secondary)] mb-3">
                Account Breakdown
              </p>
              <div className="space-y-2">
                {position.accounts.map((account) => (
                  <div
                    key={account.holding_id}
                    className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-primary)]"
                  >
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="font-medium text-[var(--text-primary)]">{account.account_name}</p>
                        <p className="text-xs text-[var(--text-tertiary)]">
                          {account.institution} · {account.account_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-8 text-sm">
                      <div className="text-right">
                        <p className="text-[var(--text-tertiary)]">Quantity</p>
                        <p className="font-mono tabular-nums text-[var(--text-primary)]">
                          {formatNumber(account.quantity, { decimals: position.asset_class === 'Crypto' ? 4 : 0 })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[var(--text-tertiary)]">Cost Basis</p>
                        <p className="font-mono tabular-nums text-[var(--text-primary)]">
                          {formatCurrency(account.cost_basis_native, position.currency, { compact: true })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[var(--text-tertiary)]">Value</p>
                        <p className="font-mono tabular-nums font-medium text-[var(--text-primary)]">
                          {formatCurrency(account.market_value_native, position.currency, { compact: true })}
                        </p>
                      </div>
                      <div className="text-right min-w-[80px]">
                        <p className="text-[var(--text-tertiary)]">P&L</p>
                        <p className={cn('font-mono tabular-nums font-medium', getChangeColor(account.pnl_native))}>
                          {getChangeIndicator(account.pnl_native)} {formatPercent(account.pnl_pct)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/**
 * Transaction card for slide-out panel - displays in native currency
 */
function TransactionCard({ tx }) {
  const isBuy = tx.type === 'BUY';
  // Use transaction's native currency
  const txCurrency = tx.currency || 'USD';

  return (
    <div className="flex items-start justify-between py-3 border-b border-[var(--border-primary)] last:border-0">
      <div className="flex items-start gap-3">
        <span className={cn(
          'badge mt-0.5',
          isBuy ? 'badge-buy' : 'badge-sell'
        )}>
          {tx.type}
        </span>
        <div>
          <p className="text-sm text-[var(--text-primary)]">
            {isBuy ? 'Bought' : 'Sold'} <span className="font-semibold">{tx.quantity} shares</span>
          </p>
          <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
            at {formatCurrency(tx.price, txCurrency)} per share
          </p>
          <p className="text-xs text-[var(--text-tertiary)] mt-1">{tx.date}</p>
        </div>
      </div>
      <p className={cn(
        'font-mono tabular-nums text-sm font-medium',
        isBuy ? 'text-negative' : 'text-positive'
      )}>
        {isBuy ? '-' : '+'}{formatCurrency(tx.total, txCurrency)}
      </p>
    </div>
  );
}

/**
 * Asset detail slide-out panel
 */
function AssetDetailPanel({ position, currency, onClose, onToggleFavorite }) {
  const [timeRange, setTimeRange] = useState('1M');
  const ranges = ['1W', '1M', '3M', '1Y'];
  const pnlColor = getChangeColor(position.total_pnl);
  const dayChangeColor = getChangeColor(position.day_change_pct);

  // Data fetching state
  const [priceHistory, setPriceHistory] = useState([]);
  const [priceLoading, setPriceLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [txLoading, setTxLoading] = useState(true);

  // Fetch price history when panel opens or time range changes - use native currency
  useEffect(() => {
    const fetchPriceHistory = async () => {
      // Skip for cash assets - they don't have price history
      if (position.asset_class === 'Cash') {
        setPriceLoading(false);
        setPriceHistory([]);
        return;
      }

      setPriceLoading(true);
      try {
        const period = TIME_RANGE_TO_PERIOD[timeRange] || '1mo';
        // Don't use display_currency - get native currency prices
        const res = await api(`/prices/historical/${encodeURIComponent(position.symbol)}?period=${period}`);
        if (res.ok) {
          const data = await res.json();
          // Transform data for chart - API returns {data: [{date, open, high, low, close, volume}, ...]}
          if (data.data && Array.isArray(data.data)) {
            const chartData = data.data.map((p) => ({
              date: new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
              price: p.close,
            }));
            setPriceHistory(chartData);
          } else {
            setPriceHistory([]);
          }
        } else {
          setPriceHistory([]);
        }
      } catch (err) {
        console.error('Error fetching price history:', err);
        setPriceHistory([]);
      } finally {
        setPriceLoading(false);
      }
    };

    fetchPriceHistory();
  }, [position.symbol, position.asset_class, timeRange]);

  // Fetch transactions for this symbol (limit to 3 most recent) - use native currency
  useEffect(() => {
    const fetchTransactions = async () => {
      setTxLoading(true);
      try {
        // Fetch without display_currency to get native currency values
        const res = await api(`/transactions/trades?symbol=${encodeURIComponent(position.symbol)}&limit=3`);
        if (res.ok) {
          const data = await res.json();
          // Transform to expected format
          const txData = data.map((t) => ({
            id: t.id,
            date: new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
            type: t.action === 'Buy' ? 'BUY' : 'SELL',
            quantity: parseFloat(t.quantity),
            price: parseFloat(t.price_per_unit),
            total: parseFloat(t.total),
            currency: t.currency, // Include native currency from transaction
          }));
          setTransactions(txData);
        } else {
          setTransactions([]);
        }
      } catch (err) {
        console.error('Error fetching transactions:', err);
        setTransactions([]);
      } finally {
        setTxLoading(false);
      }
    };

    fetchTransactions();
  }, [position.symbol]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-[var(--bg-primary)] border-l border-[var(--border-primary)] shadow-xl z-50 overflow-y-auto">
        {/* Header - z-10 to stay above scrolling content */}
        <div className="sticky top-0 z-10 bg-[var(--bg-primary)] border-b border-[var(--border-primary)] p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-xl font-semibold text-[var(--text-primary)]">{position.name}</h2>
                <button
                  onClick={onToggleFavorite}
                  className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                  title={position.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                >
                  <StarIcon
                    className={cn(
                      'w-5 h-5 transition-colors',
                      position.is_favorite ? 'text-amber-500' : 'text-[var(--text-tertiary)] hover:text-amber-400'
                    )}
                    filled={position.is_favorite}
                  />
                </button>
              </div>
              <p className="text-sm text-[var(--text-tertiary)]">
                {position.symbol} · {position.category}
                {position.industry && ` · ${position.industry}`}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
            >
              <XMarkIcon className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
          </div>

          {/* Price - show in native currency */}
          <div className="mt-4">
            <p className="text-3xl font-bold font-mono tabular-nums text-[var(--text-primary)]">
              {formatCurrency(position.current_price, position.currency)}
            </p>
            {position.asset_class === 'Cash' ? (
              <p className="text-sm text-[var(--text-tertiary)]">
                Exchange rate (1 {position.symbol} = {formatCurrency(position.current_price, position.currency)})
              </p>
            ) : position.day_change_pct != null && (
              <p className={cn('text-sm tabular-nums', dayChangeColor)}>
                {getChangeIndicator(position.day_change_pct)} ({formatPercent(position.day_change_pct)}) today
              </p>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Price Chart - skip for cash assets */}
          {position.asset_class !== 'Cash' && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Price History</CardTitle>
                  <div className="flex gap-1">
                    {ranges.map((range) => (
                      <button
                        key={range}
                        onClick={() => setTimeRange(range)}
                        className={cn(
                          'px-2.5 py-1 text-xs rounded-md transition-colors cursor-pointer',
                          timeRange === range
                            ? 'bg-accent text-white'
                            : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                        )}
                      >
                        {range}
                      </button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-40">
                  {priceLoading ? (
                    <div className="h-full flex items-center justify-center">
                      <div className="animate-pulse text-[var(--text-tertiary)]">Loading chart...</div>
                    </div>
                  ) : priceHistory.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={priceHistory}>
                        <XAxis
                          dataKey="date"
                          tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                          axisLine={{ stroke: 'var(--border-primary)' }}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                          domain={[
                            (dataMin) => Math.floor(dataMin * 0.95),
                            (dataMax) => Math.ceil(dataMax * 1.05)
                          ]}
                          tickFormatter={(v) => formatCurrency(v, position.currency, { compact: true })}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'var(--bg-secondary)',
                            border: '1px solid var(--border-primary)',
                            borderRadius: '8px',
                          }}
                          formatter={(value) => [formatCurrency(value, position.currency), 'Price']}
                        />
                        <Line
                          type="monotone"
                          dataKey="price"
                          stroke="#2563EB"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center">
                      <p className="text-sm text-[var(--text-tertiary)]">No price history available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Your Holdings */}
          <Card>
            <CardHeader>
              <CardTitle>Your Holdings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {position.accounts.map((account) => {
                  return (
                    <div
                      key={account.holding_id}
                      className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)]"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium text-[var(--text-primary)]">{account.account_name}</p>
                        <p className="font-mono tabular-nums font-medium text-[var(--text-primary)]">
                          {formatCurrency(account.market_value_native, position.currency)}
                        </p>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <div className="text-[var(--text-tertiary)]">
                          <span>{formatNumber(account.quantity, { decimals: position.asset_class === 'Crypto' ? 4 : 0 })} {position.asset_class === 'Crypto' ? 'units' : 'shares'}</span>
                          {position.asset_class !== 'Cash' && (
                            <span className="ml-1">· Cost: {formatCurrency(account.cost_basis_native, position.currency)}</span>
                          )}
                        </div>
                        {position.asset_class !== 'Cash' && account.pnl_native != null && (
                          <p className={cn('font-mono tabular-nums', getChangeColor(account.pnl_native))}>
                            {getChangeIndicator(account.pnl_native)} {formatCurrency(Math.abs(account.pnl_native), position.currency)} ({formatPercent(account.pnl_pct)})
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Total in native currency */}
              <div className="mt-4 pt-4 border-t border-[var(--border-primary)]">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-[var(--text-secondary)]">Total ({position.currency})</p>
                  <div className="text-right">
                    <p className="font-mono tabular-nums font-semibold text-[var(--text-primary)]">
                      {formatCurrency(position.total_market_value_native, position.currency)}
                    </p>
                    {position.asset_class !== 'Cash' && (
                      <p className={cn('text-sm tabular-nums', pnlColor)}>
                        {getChangeIndicator(position.total_pnl_native)} {formatCurrency(Math.abs(position.total_pnl_native), position.currency, { compact: true })} ({formatPercent(position.total_pnl_pct)})
                      </p>
                    )}
                  </div>
                </div>
                {/* Show converted value if different from display currency */}
                {position.currency !== currency && (
                  <div className="flex items-center justify-between mt-2 text-sm">
                    <p className="text-[var(--text-tertiary)]">Total ({currency})</p>
                    <p className="font-mono tabular-nums text-[var(--text-secondary)]">
                      {formatCurrency(position.total_market_value, currency)}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Recent Transactions */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Transactions</CardTitle>
                <a href="/activity" className="text-sm text-accent hover:underline cursor-pointer">
                  View all
                </a>
              </div>
            </CardHeader>
            <CardContent>
              {txLoading ? (
                <div className="py-4 text-center">
                  <div className="animate-pulse text-[var(--text-tertiary)]">Loading transactions...</div>
                </div>
              ) : transactions.length > 0 ? (
                <div>
                  {transactions.map((tx) => (
                    <TransactionCard key={tx.id} tx={tx} />
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center">
                  <p className="text-sm text-[var(--text-tertiary)]">No transactions found</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

export default function Holdings() {
  const { currency } = useCurrency();
  const { selectedPortfolioId } = usePortfolio();
  const [searchParams, setSearchParams] = useSearchParams();

  // Data fetching state
  const [positions, setPositions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Track if we've handled the initial symbol param
  const hasHandledSymbolParam = useRef(false);

  // Derived filter options from data
  const assetClasses = useMemo(() => {
    const classes = [...new Set(positions.map((p) => p.asset_class).filter(Boolean))];
    return classes.sort();
  }, [positions]);

  const categories = useMemo(() => {
    const cats = [...new Set(positions.map((p) => p.category).filter(Boolean))];
    return cats.sort();
  }, [positions]);

  // Filter state - initialized after data loads
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [selectedClasses, setSelectedClasses] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [filtersInitialized, setFiltersInitialized] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Fetch positions and accounts
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      // Build query params - add portfolio_id if a specific portfolio is selected
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      try {
        const [positionsRes, accountsRes] = await Promise.all([
          api(`/positions?display_currency=${currency}${portfolioParam}`),
          api(`/accounts?is_active=true${portfolioParam}`),
        ]);

        if (!positionsRes.ok) {
          throw new Error(`Failed to fetch positions: ${positionsRes.statusText}`);
        }
        if (!accountsRes.ok) {
          throw new Error(`Failed to fetch accounts: ${accountsRes.statusText}`);
        }

        const [positionsData, accountsResponse] = await Promise.all([
          positionsRes.json(),
          accountsRes.json(),
        ]);

        setPositions(positionsData);
        setAccounts(accountsResponse.items);
      } catch (err) {
        console.error('Error fetching holdings data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currency, selectedPortfolioId]);

  // Initialize filters when data loads (select all by default)
  useEffect(() => {
    if (!loading && positions.length > 0 && accounts.length > 0 && !filtersInitialized) {
      setSelectedAccounts(accounts.map((a) => a.id));
      setSelectedClasses([...assetClasses]);
      setSelectedCategories([...categories]);
      setFiltersInitialized(true);
    }
  }, [loading, positions, accounts, assetClasses, categories, filtersInitialized]);

  // Reset filters when currency changes (data refetches)
  useEffect(() => {
    setFiltersInitialized(false);
  }, [currency]);

  // Reset pagination when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedAccounts, selectedClasses, selectedCategories]);

  // Sort state
  const [sortField, setSortField] = useState('total_market_value');
  const [sortDirection, setSortDirection] = useState('desc');

  // Expanded rows
  const [expandedRows, setExpandedRows] = useState(new Set());

  // Detail panel
  const [selectedPosition, setSelectedPosition] = useState(null);

  // Handle pre-selection from URL query param (e.g., from Daily Movers click)
  // This needs filteredPositions to calculate the correct page
  const pendingSymbolRef = useRef(null);

  useEffect(() => {
    const symbol = searchParams.get('symbol');
    if (symbol && positions.length > 0 && !hasHandledSymbolParam.current) {
      hasHandledSymbolParam.current = true;
      pendingSymbolRef.current = symbol;

      // Find the position by symbol
      const position = positions.find(p => p.symbol === symbol);
      if (position) {
        // Open the detail panel
        setSelectedPosition(position);

        // Clear the query param to clean up the URL
        setSearchParams({}, { replace: true });
      }
    }
  }, [positions, searchParams, setSearchParams]);

  // Toggle favorite (mock - in real app would call API)
  const toggleFavorite = (assetId) => {
    setPositions((prev) =>
      prev.map((p) =>
        p.asset_id === assetId ? { ...p, is_favorite: !p.is_favorite } : p
      )
    );
    // Also update selected position if open
    if (selectedPosition?.asset_id === assetId) {
      setSelectedPosition((prev) => ({ ...prev, is_favorite: !prev.is_favorite }));
    }
  };

  // Filter and sort positions
  const filteredPositions = useMemo(() => {
    let result = positions.filter((position) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!position.symbol.toLowerCase().includes(query) &&
            !position.name.toLowerCase().includes(query)) {
          return false;
        }
      }

      // Account filter
      if (selectedAccounts.length > 0 && selectedAccounts.length < accounts.length) {
        const hasAccount = position.accounts.some(
          (acc) => selectedAccounts.includes(acc.account_id)
        );
        if (!hasAccount) return false;
      } else if (selectedAccounts.length === 0) {
        return false;
      }

      // Class filter
      if (selectedClasses.length > 0 && selectedClasses.length < assetClasses.length) {
        if (!selectedClasses.includes(position.asset_class)) {
          return false;
        }
      } else if (selectedClasses.length === 0) {
        return false;
      }

      // Category filter
      if (selectedCategories.length > 0 && selectedCategories.length < categories.length) {
        if (!selectedCategories.includes(position.category)) {
          return false;
        }
      } else if (selectedCategories.length === 0) {
        return false;
      }

      return true;
    });

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });

    return result;
  }, [positions, searchQuery, selectedAccounts, selectedClasses, selectedCategories, sortField, sortDirection, accounts.length, assetClasses.length, categories.length]);

  // Scroll to the row after page navigation (separate effect to handle pagination)
  // Must be after filteredPositions is defined
  useEffect(() => {
    if (pendingSymbolRef.current && filteredPositions.length > 0) {
      const symbol = pendingSymbolRef.current;
      const index = filteredPositions.findIndex(p => p.symbol === symbol);

      if (index !== -1) {
        // Calculate which page the asset is on
        const targetPage = Math.floor(index / pageSize) + 1;

        if (targetPage !== currentPage) {
          // Navigate to the correct page first
          setCurrentPage(targetPage);
        } else {
          // Already on the correct page, scroll to the row
          const position = filteredPositions[index];
          setTimeout(() => {
            const row = document.getElementById(`holdings-row-${position.asset_id}`);
            if (row) {
              row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            pendingSymbolRef.current = null;
          }, 100);
        }
      } else {
        // Asset not in filtered list (might be filtered out)
        pendingSymbolRef.current = null;
      }
    }
  }, [filteredPositions, currentPage, pageSize]);

  // Calculate totals
  const totals = useMemo(() => {
    return filteredPositions.reduce(
      (acc, pos) => ({
        marketValue: acc.marketValue + (pos.total_market_value || 0),
        costBasis: acc.costBasis + (pos.total_cost_basis || 0),
        pnl: acc.pnl + (pos.total_pnl || 0),
      }),
      { marketValue: 0, costBasis: 0, pnl: 0 }
    );
  }, [filteredPositions]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleRow = (assetId) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) {
        next.delete(assetId);
      } else {
        next.add(assetId);
      }
      return next;
    });
  };

  // Loading state
  if (loading) {
    return (
      <PageContainer title="Holdings">
        {/* Filters skeleton */}
        <div className="flex flex-col lg:flex-row gap-4 mb-6">
          <Skeleton className="h-11 w-full max-w-md" />
          <div className="flex flex-wrap gap-3">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-10 w-28" />
          </div>
        </div>

        {/* Table skeleton */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header w-10"></th>
                  <th className="table-header">Symbol</th>
                  <th className="table-header">Name</th>
                  <th className="table-header text-right">Price</th>
                  <th className="table-header text-right">Qty</th>
                  <th className="table-header text-right">Value</th>
                  <th className="table-header text-right">P&L</th>
                  <th className="table-header text-center">Accts</th>
                </tr>
              </thead>
              <tbody>
                {[1, 2, 3, 4, 5].map((i) => (
                  <SkeletonTableRow key={i} columns={8} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </PageContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer title="Holdings">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-negative mb-2">Error loading holdings</p>
            <p className="text-[var(--text-secondary)] text-sm">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors cursor-pointer"
            >
              Retry
            </button>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Holdings">
      {/* Filters */}
      <FilterBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedAccounts={selectedAccounts}
        setSelectedAccounts={setSelectedAccounts}
        selectedClasses={selectedClasses}
        setSelectedClasses={setSelectedClasses}
        selectedCategories={selectedCategories}
        setSelectedCategories={setSelectedCategories}
        accounts={accounts}
        assetClasses={assetClasses}
        categories={categories}
      />

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header w-10"></th>
                <SortableHeader
                  field="symbol"
                  label="Symbol"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  field="name"
                  label="Name"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  field="current_price"
                  label="Price"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  align="right"
                />
                <SortableHeader
                  field="total_quantity"
                  label="Qty"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  align="right"
                />
                <SortableHeader
                  field="total_market_value"
                  label="Value"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  align="right"
                />
                <SortableHeader
                  field="total_pnl_pct"
                  label="P&L"
                  sortField={sortField}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  align="right"
                />
                <th className="table-header text-center">Accts</th>
              </tr>
            </thead>
            <tbody>
              {filteredPositions
                .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                .map((position) => (
                  <HoldingsRow
                    key={position.asset_id}
                    position={position}
                    currency={currency}
                    isExpanded={expandedRows.has(position.asset_id)}
                    onToggle={() => toggleRow(position.asset_id)}
                    onOpenDetail={() => setSelectedPosition(position)}
                    onToggleFavorite={() => toggleFavorite(position.asset_id)}
                  />
                ))}
            </tbody>
          </table>

          {/* Empty state */}
          {filteredPositions.length === 0 && (
            <div className="text-center py-12">
              <p className="text-[var(--text-secondary)]">
                {positions.length === 0 ? 'No holdings found' : 'No holdings match your filters'}
              </p>
              {positions.length > 0 && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedAccounts(accounts.map((a) => a.id));
                    setSelectedClasses([...assetClasses]);
                    setSelectedCategories([...categories]);
                  }}
                  className="mt-2 text-sm text-accent hover:underline cursor-pointer"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer with pagination and totals */}
        {filteredPositions.length > 0 && (() => {
          const totalPages = Math.ceil(filteredPositions.length / pageSize);
          return (
            <div className="px-4 py-3 border-t border-[var(--border-primary)] bg-[var(--bg-tertiary)]">
              <div className="flex items-center justify-between">
                {/* Left: Pagination info and controls */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[var(--text-secondary)]">Show:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className={cn(
                        'px-2 py-1 rounded text-sm',
                        'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                        'text-[var(--text-primary)] cursor-pointer',
                        'focus:outline-none focus:ring-2 focus:ring-accent/50'
                      )}
                    >
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>
                  <p className="text-sm text-[var(--text-tertiary)]">
                    Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, filteredPositions.length)} of {filteredPositions.length}
                  </p>
                  {totalPages > 1 && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setCurrentPage(1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                        disabled={currentPage === 1}
                        className={cn(
                          'p-1.5 rounded',
                          'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                          'hover:bg-[var(--border-primary)] transition-colors',
                          currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        )}
                        title="First page"
                      >
                        <ChevronDoubleLeftIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setCurrentPage((p) => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                        disabled={currentPage === 1}
                        className={cn(
                          'p-1.5 rounded',
                          'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                          'hover:bg-[var(--border-primary)] transition-colors',
                          currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        )}
                        title="Previous page"
                      >
                        <ChevronLeftIcon className="w-4 h-4" />
                      </button>
                      <span className="text-sm text-[var(--text-secondary)] px-2">
                        {currentPage} / {totalPages}
                      </span>
                      <button
                        onClick={() => { setCurrentPage((p) => Math.min(totalPages, p + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                        disabled={currentPage >= totalPages}
                        className={cn(
                          'p-1.5 rounded',
                          'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                          'hover:bg-[var(--border-primary)] transition-colors',
                          currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        )}
                        title="Next page"
                      >
                        <ChevronRightIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setCurrentPage(totalPages); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                        disabled={currentPage >= totalPages}
                        className={cn(
                          'p-1.5 rounded',
                          'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                          'hover:bg-[var(--border-primary)] transition-colors',
                          currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                        )}
                        title="Last page"
                      >
                        <ChevronDoubleRightIcon className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Right: Totals */}
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-right">
                    <p className="text-[var(--text-tertiary)]">Total Value</p>
                    <p className="font-mono tabular-nums font-semibold text-[var(--text-primary)]">
                      {formatCurrency(totals.marketValue, currency)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[var(--text-tertiary)]">Total P&L</p>
                    <p className={cn('font-mono tabular-nums font-semibold', getChangeColor(totals.pnl))}>
                      {getChangeIndicator(totals.pnl)} {formatCurrency(Math.abs(totals.pnl), currency, { compact: true })}
                      {totals.costBasis > 0 && (
                        <span className="ml-1">
                          ({formatPercent((totals.pnl / totals.costBasis) * 100)})
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}
      </Card>

      {/* Detail slide-out panel */}
      {selectedPosition && (
        <AssetDetailPanel
          position={selectedPosition}
          currency={currency}
          onClose={() => setSelectedPosition(null)}
          onToggleFavorite={() => toggleFavorite(selectedPosition.asset_id)}
        />
      )}
    </PageContainer>
  );
}
