import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { cn, formatCurrency, formatPercent, formatDate, getChangeColor } from '../../lib';
import { useChartColors } from '../../hooks/useChartColors';
import api from '../../lib/api';
import { Skeleton } from '../ui';

const PERIODS = [
  { label: '1W', api: '5d' },
  { label: '1M', api: '1mo' },
  { label: '3M', api: '3mo' },
  { label: '1Y', api: '1y' },
];

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M18 6 6 18" /><path d="m6 6 12 12" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
    </svg>
  );
}

export function AssetDetailSidebar({ asset, isOpen, onClose }) {
  const [period, setPeriod] = useState('1M');
  const [priceData, setPriceData] = useState([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const colors = useChartColors();

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  // Escape key closes sidebar
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') onClose?.();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  // Fetch price history
  useEffect(() => {
    if (!asset?.symbol || !isOpen) return;
    let cancelled = false;
    setChartLoading(true);
    const apiPeriod = PERIODS.find((p) => p.label === period)?.api || '1mo';
    api(`/api/dashboard/benchmark?symbol=${encodeURIComponent(asset.symbol)}&period=${apiPeriod}`)
      .then((res) => {
        if (!cancelled && res?.data) {
          setPriceData(res.data.map((d) => ({
            date: d.date,
            price: d.price,
            label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          })));
        }
      })
      .catch(() => { if (!cancelled) setPriceData([]); })
      .finally(() => { if (!cancelled) setChartLoading(false); });
    return () => { cancelled = true; };
  }, [asset?.symbol, period, isOpen]);

  // Fetch recent transactions
  useEffect(() => {
    if (!asset?.symbol || !isOpen) return;
    let cancelled = false;
    api(`/api/transactions/trades?symbol=${encodeURIComponent(asset.symbol)}&limit=5`)
      .then((res) => { if (!cancelled) setTransactions(res.items || res || []); })
      .catch(() => { if (!cancelled) setTransactions([]); });
    return () => { cancelled = true; };
  }, [asset?.symbol, isOpen]);

  // Reset period when asset changes
  useEffect(() => { setPeriod('1M'); }, [asset?.symbol]);

  if (!isOpen || !asset) return null;

  const changeColor = getChangeColor(asset.day_change_pct);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed top-0 right-0 z-50 h-dvh w-[420px] max-w-[90vw] bg-[var(--bg-secondary)] border-l border-[var(--border-primary)] shadow-2xl flex flex-col animate-slide-in-right">
        {/* Header (sticky) */}
        <div className="px-6 pt-5 pb-4 border-b border-[var(--border-primary)] flex-shrink-0">
          <div className="flex items-start justify-between mb-1">
            <div className="min-w-0">
              <h2 className="text-lg font-bold truncate">{asset.name || asset.symbol}</h2>
              <p className="text-[12px] text-[var(--text-tertiary)]">
                {asset.symbol}{asset.asset_class ? ` \u00B7 ${asset.asset_class}` : ''}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              <Link
                to={`/assets/${asset.id}`}
                onClick={onClose}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-accent border border-accent/30 rounded-lg hover:bg-accent/10 transition-colors"
              >
                View Details <ExternalLinkIcon />
              </Link>
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] transition-all cursor-pointer"
              >
                <CloseIcon />
              </button>
            </div>
          </div>
          <div className="flex items-baseline gap-3 mt-3">
            <span className="text-2xl font-bold font-mono tabular-nums">
              {asset.current_price != null
                ? formatCurrency(asset.current_price, asset.currency || 'USD')
                : '--'}
            </span>
            {asset.day_change_pct != null && (
              <span className={cn('text-sm font-semibold font-mono', changeColor)}>
                {formatPercent(asset.day_change_pct)} today
              </span>
            )}
          </div>
        </div>

        {/* Body (scrollable) */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Price History Chart */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[13px] font-semibold">Price History</span>
              <div className="flex gap-1">
                {PERIODS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => setPeriod(p.label)}
                    className={cn(
                      'px-2 py-1 rounded text-[10px] font-medium transition-all cursor-pointer',
                      period === p.label
                        ? 'bg-accent text-white'
                        : 'text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)]'
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="h-[160px] bg-[var(--bg-primary)] rounded-lg p-2">
              {chartLoading ? (
                <Skeleton className="h-full w-full" />
              ) : priceData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={priceData} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                    <defs>
                      <linearGradient id="asGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={colors.accent} stopOpacity={0.15} />
                        <stop offset="100%" stopColor={colors.accent} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="label"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 9, fill: colors.textTertiary }}
                      interval="preserveStartEnd"
                      minTickGap={40}
                    />
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-primary)',
                        borderRadius: '6px',
                        fontSize: '11px',
                      }}
                      formatter={(val) => [formatCurrency(val, asset.currency || 'USD'), 'Price']}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke={colors.accent}
                      strokeWidth={1.5}
                      fill="url(#asGrad)"
                      dot={false}
                      activeDot={{ r: 3, fill: colors.accent, stroke: colors.bgSecondary, strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-[var(--text-tertiary)] text-xs">
                  No price data available
                </div>
              )}
            </div>
          </div>

          {/* Recent Transactions */}
          {transactions.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[13px] font-semibold">Recent Transactions</span>
                <Link
                  to={`/activity?symbol=${asset.symbol}`}
                  onClick={onClose}
                  className="text-[11px] text-accent hover:text-accent-hover font-medium"
                >
                  View all
                </Link>
              </div>
              <div className="flex flex-col gap-1">
                {transactions.map((tx) => (
                  <div
                    key={tx.id}
                    className="flex items-center justify-between py-2 border-b border-[var(--border-primary)] last:border-b-0"
                  >
                    <div>
                      <div className="text-[12px] font-medium">{tx.type}</div>
                      <div className="text-[10px] text-[var(--text-tertiary)]">
                        {tx.date ? formatDate(tx.date) : ''}
                      </div>
                    </div>
                    <div className="text-right text-[12px] font-mono tabular-nums">
                      {tx.quantity != null && <div>{tx.quantity} shares</div>}
                      {tx.total_amount != null && (
                        <div className="text-[var(--text-tertiary)]">
                          {formatCurrency(tx.total_amount, tx.currency || 'USD')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
