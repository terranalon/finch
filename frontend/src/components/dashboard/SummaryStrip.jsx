import { formatCurrency, formatPercent, getChangeColor } from '../../lib';
import { Skeleton, MiniSparkline } from '../ui';

export function SummaryStrip({ summary, snapshots, loading, currency }) {
  const sparkData = snapshots?.slice(-2);
  const isPositive = sparkData?.length >= 2
    ? sparkData[sparkData.length - 1].value >= sparkData[0].value
    : true;

  if (loading) {
    return (
      <div className="mb-5 pb-[18px] border-b border-[var(--border-primary)]">
        <Skeleton className="h-20 w-full rounded-lg" />
      </div>
    );
  }

  if (!summary) return null;

  const changeColor = getChangeColor(summary.day_change);
  const unrealizedPnl = summary.unrealized_pnl;
  const realizedPnl = summary.realized_pnl;

  return (
    <div className="mb-5 pb-[18px] border-b border-[var(--border-primary)]">
      <div className="flex items-center gap-8 flex-wrap">
        {/* Hero: total value */}
        <div className="flex-shrink-0">
          <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
            Total Portfolio Value
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[28px] font-bold font-mono tabular-nums leading-none">
              {formatCurrency(summary.total_value, currency)}
            </span>
            <MiniSparkline data={sparkData} positive={isPositive} width={200} height={40} filled />
          </div>
          {summary.day_change != null && (
            <div className="flex items-center gap-2 mt-1.5">
              <span className={`text-sm font-semibold font-mono tabular-nums ${changeColor}`}>
                {summary.day_change >= 0 ? '+' : ''}
                {formatCurrency(summary.day_change, currency)}
                {summary.day_change_pct != null && ` (${formatPercent(summary.day_change_pct)})`}
              </span>
              <span className="text-[11px] text-[var(--text-tertiary)]">today</span>
            </div>
          )}
        </div>

        {/* Metric cards */}
        <div className="flex items-center gap-6 flex-wrap flex-1 justify-end">
          {/* Unrealized P&L */}
          <div className="text-center min-w-[100px]">
            <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Unrealized P&L
            </div>
            <div className={`text-[17px] font-bold font-mono tabular-nums ${getChangeColor(unrealizedPnl)}`}>
              {unrealizedPnl != null && (unrealizedPnl >= 0 ? '+' : '')}
              {formatCurrency(unrealizedPnl || 0, currency)}
            </div>
          </div>

          {/* Realized P&L */}
          <div className="text-center min-w-[100px]">
            <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Realized P&L
            </div>
            <div className={`text-[17px] font-bold font-mono tabular-nums ${getChangeColor(realizedPnl)}`}>
              {realizedPnl != null && (realizedPnl >= 0 ? '+' : '')}
              {formatCurrency(realizedPnl || 0, currency)}
            </div>
          </div>

          {/* Cost Basis */}
          <div className="text-center min-w-[100px]">
            <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Cost Basis
            </div>
            <div className="text-[17px] font-bold font-mono tabular-nums">
              {formatCurrency(summary.total_cost_basis || 0, currency)}
            </div>
          </div>

          {/* Cash */}
          <div className="text-center min-w-[80px]">
            <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Cash
            </div>
            <div className="text-[17px] font-bold font-mono tabular-nums">
              {formatCurrency(summary.total_cash || 0, currency)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
