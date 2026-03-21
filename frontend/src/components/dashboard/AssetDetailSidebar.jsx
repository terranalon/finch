import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { cn, formatCurrency, formatPercent, formatNumber, formatDate, getChangeColor, getChangeIndicator } from '../../lib';
import { useChartColors } from '../../hooks/useChartColors';
import { useSlideover } from '../../hooks/useSlideover';
import { usePortfolio } from '../../contexts';
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
    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
    </svg>
  );
}

function StarIcon({ filled, className }) {
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

/**
 * Shared asset detail sidebar used across Dashboard, Holdings, and other pages.
 *
 * Self-contained: fetches position data (per-account holdings, P&L),
 * price history, and recent transactions from API.
 *
 * @param asset  Minimal asset info: { id, symbol, name?, asset_class?, current_price?, day_change_pct?, currency? }
 * @param isOpen Whether the sidebar is visible
 * @param onClose Called when sidebar is dismissed
 * @param onFavoriteToggle Optional callback(assetId, newValue) for parent state sync
 */
export function AssetDetailSidebar({ asset, isOpen, onClose, onFavoriteToggle }) {
  const { selectedPortfolioId } = usePortfolio();
  const [period, setPeriod] = useState('1M');
  const [priceData, setPriceData] = useState([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [position, setPosition] = useState(null);
  const [posLoading, setPosLoading] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const colors = useChartColors();

  useSlideover(isOpen, onClose);

  // Fetch position details (account breakdown, P&L)
  useEffect(() => {
    if (!asset?.id || !isOpen) return;
    let cancelled = false;
    setPosLoading(true);
    const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';
    api(`/positions?limit=100${portfolioParam}`)
      .then((resp) => resp.json())
      .then((res) => {
        if (cancelled) return;
        const items = res.items || res || [];
        const match = items.find((p) => p.asset_id === asset.id);
        setPosition(match || null);
        setIsFavorite(match?.is_favorite ?? false);
      })
      .catch(() => { if (!cancelled) setPosition(null); })
      .finally(() => { if (!cancelled) setPosLoading(false); });
    return () => { cancelled = true; };
  }, [asset?.id, isOpen, selectedPortfolioId]);

  // Fetch price history
  useEffect(() => {
    if (!asset?.symbol || !isOpen) return;
    let cancelled = false;
    setChartLoading(true);
    const apiPeriod = PERIODS.find((p) => p.label === period)?.api || '1mo';
    api(`/prices/historical/${encodeURIComponent(asset.symbol)}?period=${apiPeriod}`)
      .then((resp) => resp.json())
      .then((res) => {
        if (!cancelled && res?.data && Array.isArray(res.data)) {
          setPriceData(res.data.map((d) => ({
            date: d.date,
            price: d.close,
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
    api(`/transactions/trades?symbol=${encodeURIComponent(asset.symbol)}&limit=3`)
      .then((resp) => resp.json())
      .then((res) => { if (!cancelled) setTransactions(res.items || res || []); })
      .catch(() => { if (!cancelled) setTransactions([]); });
    return () => { cancelled = true; };
  }, [asset?.symbol, isOpen]);

  // Reset period when asset changes
  useEffect(() => { setPeriod('1M'); }, [asset?.symbol]);

  const toggleFavorite = useCallback(() => {
    if (!asset?.id) return;
    const newVal = !isFavorite;
    setIsFavorite(newVal);
    onFavoriteToggle?.(asset.id, newVal);
    api(`/assets/${asset.id}/favorite`, { method: 'PUT' }).catch(() => {
      setIsFavorite(!newVal);
      onFavoriteToggle?.(asset.id, !newVal);
    });
  }, [asset?.id, isFavorite, onFavoriteToggle]);

  if (!isOpen || !asset) return null;

  // Merge data from position (fetched) and asset (prop) — position is richer
  const name = position?.name || asset.name || asset.symbol;
  const symbol = asset.symbol;
  const assetClass = position?.asset_class || asset.asset_class;
  const category = position?.category || assetClass;
  const industry = position?.industry;
  const nativeCurrency = position?.currency || asset.currency || 'USD';
  const currentPrice = position?.current_price ?? asset.current_price;
  const dayChangePct = position?.day_change_pct ?? asset.day_change_pct;
  const changeColor = getChangeColor(dayChangePct);
  const isCrypto = assetClass === 'Crypto';
  const isCash = assetClass === 'Cash';
  const unit = isCrypto ? 'units' : 'shares';
  const qtyDecimals = isCrypto ? 4 : 0;

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
              <div className="flex items-center gap-2 mb-0.5">
                <h2 className="text-lg font-bold truncate">{name}</h2>
                <button
                  onClick={toggleFavorite}
                  className="p-0.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                  title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                >
                  <StarIcon
                    className={cn(
                      'w-5 h-5 transition-colors',
                      isFavorite ? 'text-amber-500' : 'text-[var(--text-tertiary)] hover:text-amber-400'
                    )}
                    filled={isFavorite}
                  />
                </button>
              </div>
              <p className="text-[12px] text-[var(--text-tertiary)]">
                {symbol}
                {category && ` \u00B7 ${category}`}
                {industry && ` \u00B7 ${industry}`}
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

          {/* Price */}
          <div className="mt-3">
            <p className="text-2xl font-bold font-mono tabular-nums">
              {currentPrice != null ? formatCurrency(currentPrice, nativeCurrency) : '--'}
            </p>
            {isCash ? (
              <p className="text-[12px] text-[var(--text-tertiary)]">
                Exchange rate (1 {symbol} = {formatCurrency(currentPrice, nativeCurrency)})
              </p>
            ) : dayChangePct != null && (
              <p className={cn('text-sm font-mono tabular-nums', changeColor)}>
                {getChangeIndicator(dayChangePct)} ({formatPercent(dayChangePct)}) today
              </p>
            )}
          </div>
        </div>

        {/* Body (scrollable) */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Price History Chart (skip for cash) */}
          {!isCash && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[13px] font-semibold">Price History</span>
                <div className="flex gap-1">
                  {PERIODS.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => setPeriod(p.label)}
                      className={cn(
                        'px-2.5 py-1 rounded text-[10px] font-medium transition-all cursor-pointer',
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
                        formatter={(val) => [formatCurrency(val, nativeCurrency), 'Price']}
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
          )}

          {/* Your Holdings (per-account breakdown) */}
          {posLoading ? (
            <Skeleton className="h-[120px] w-full rounded-lg" />
          ) : position?.accounts?.length > 0 && (
            <div>
              <span className="text-[13px] font-semibold block mb-3">Your Holdings</span>
              <div className="flex flex-col gap-2">
                {position.accounts.map((acct) => (
                  <div
                    key={acct.holding_id}
                    className="p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)]"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[12px] font-medium text-[var(--text-primary)]">{acct.account_name}</span>
                      <span className="text-[12px] font-mono tabular-nums font-medium text-[var(--text-primary)]">
                        {formatCurrency(acct.market_value_native ?? acct.market_value ?? 0, nativeCurrency)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-[var(--text-tertiary)]">
                        {formatNumber(acct.quantity, { decimals: qtyDecimals })} {unit}
                        {!isCash && (
                          <span className="ml-1">&middot; Cost: {formatCurrency(acct.cost_basis_native ?? acct.cost_basis ?? 0, nativeCurrency)}</span>
                        )}
                      </span>
                      {!isCash && acct.pnl_native != null && (
                        <span className={cn('font-mono tabular-nums', getChangeColor(acct.pnl_native))}>
                          {getChangeIndicator(acct.pnl_native)} {formatCurrency(Math.abs(acct.pnl_native), nativeCurrency)}
                          {acct.pnl_pct != null && ` (${formatPercent(acct.pnl_pct)})`}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Totals (only show if multiple accounts) */}
              {position.accounts.length > 1 && (
                <div className="mt-3 pt-3 border-t border-[var(--border-primary)]">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] font-medium text-[var(--text-secondary)]">Total ({nativeCurrency})</span>
                    <div className="text-right">
                      <span className="text-[13px] font-mono tabular-nums font-semibold">
                        {formatCurrency(position.total_market_value_native ?? position.total_market_value ?? 0, nativeCurrency)}
                      </span>
                      {!isCash && position.total_pnl_native != null && (
                        <div className={cn('text-[10px] font-mono tabular-nums', getChangeColor(position.total_pnl_native))}>
                          {getChangeIndicator(position.total_pnl_native)} {formatCurrency(Math.abs(position.total_pnl_native), nativeCurrency)}
                          {position.total_pnl_pct != null && ` (${formatPercent(position.total_pnl_pct)})`}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recent Transactions */}
          {transactions.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[13px] font-semibold">Recent Transactions</span>
                <Link
                  to={`/activity?symbol=${symbol}`}
                  onClick={onClose}
                  className="text-[11px] text-accent hover:text-accent-hover font-medium"
                >
                  View all
                </Link>
              </div>
              <div className="flex flex-col">
                {transactions.map((tx) => {
                  const isBuy = tx.action === 'Buy';
                  const txCurrency = tx.currency || nativeCurrency;
                  return (
                    <div
                      key={tx.id}
                      className="flex items-start justify-between py-2.5 border-b border-[var(--border-primary)] last:border-b-0"
                    >
                      <div className="flex items-start gap-2.5">
                        <span className={cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-semibold mt-0.5',
                          isBuy ? 'bg-positive/10 text-positive' : 'bg-negative/10 text-negative'
                        )}>
                          {isBuy ? 'BUY' : 'SELL'}
                        </span>
                        <div>
                          <div className="text-[12px] text-[var(--text-primary)]">
                            {isBuy ? 'Bought' : 'Sold'}{' '}
                            <span className="font-semibold">
                              {tx.quantity != null && `${formatNumber(Number(tx.quantity), { decimals: qtyDecimals })} ${unit}`}
                            </span>
                          </div>
                          {tx.price_per_unit != null && (
                            <div className="text-[10px] text-[var(--text-tertiary)] mt-0.5">
                              at {formatCurrency(Number(tx.price_per_unit), txCurrency)} per {isCrypto ? 'unit' : 'share'}
                            </div>
                          )}
                          <div className="text-[10px] text-[var(--text-tertiary)] mt-0.5">
                            {tx.date ? formatDate(tx.date) : ''}
                          </div>
                        </div>
                      </div>
                      <span className={cn(
                        'text-[12px] font-mono tabular-nums font-medium flex-shrink-0',
                        isBuy ? 'text-negative' : 'text-positive'
                      )}>
                        {tx.total != null && `${isBuy ? '-' : '+'}${formatCurrency(Math.abs(Number(tx.total)), txCurrency)}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
