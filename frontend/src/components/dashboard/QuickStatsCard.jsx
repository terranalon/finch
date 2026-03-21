import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import { Skeleton } from '../ui';

export function QuickStatsCard({ summary, loading, currency }) {
  if (loading || !summary) {
    return <div className="card"><Skeleton className="h-[160px] w-full" /></div>;
  }

  const gainLoss = (summary.total_value || 0) - (summary.total_cost_basis || 0);
  const gainLossPct = summary.total_cost_basis > 0
    ? (gainLoss / summary.total_cost_basis) * 100
    : 0;

  const holdingsCount = summary.top_holdings?.length || 0;
  const accountsCount = summary.accounts?.length || 0;

  // Best performer by day change
  const best = summary.top_holdings
    ?.filter((h) => h.day_change_pct != null)
    ?.sort((a, b) => b.day_change_pct - a.day_change_pct)?.[0];

  return (
    <div className="card">
      <span className="text-[13px] font-semibold mb-3 block">Quick Stats</span>
      <div className="grid grid-cols-2 gap-3">
        {/* Total Gain/Loss */}
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-3">
          <div className="text-[10px] text-[var(--text-tertiary)] mb-1">Total P&L</div>
          <div className={cn('text-[14px] font-bold font-mono tabular-nums', getChangeColor(gainLoss))}>
            {formatCurrency(gainLoss, currency)}
          </div>
          <div className={cn('text-[10px] font-mono tabular-nums', getChangeColor(gainLoss))}>
            {formatPercent(gainLossPct)}
          </div>
        </div>

        {/* Holdings Count */}
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-3">
          <div className="text-[10px] text-[var(--text-tertiary)] mb-1">Holdings</div>
          <div className="text-[14px] font-bold font-mono tabular-nums">
            {holdingsCount}
          </div>
          <div className="text-[10px] text-[var(--text-tertiary)]">
            across {accountsCount} account{accountsCount !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Best Performer */}
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-3 col-span-2">
          <div className="text-[10px] text-[var(--text-tertiary)] mb-1">Best Performer Today</div>
          {best ? (
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[13px] font-semibold">{best.name || best.symbol}</span>
                <span className="text-[10px] text-[var(--text-tertiary)] ml-1.5">{best.symbol}</span>
              </div>
              <span className={cn('text-[13px] font-bold font-mono tabular-nums', getChangeColor(best.day_change_pct))}>
                {formatPercent(best.day_change_pct)}
              </span>
            </div>
          ) : (
            <div className="text-[12px] text-[var(--text-tertiary)]">No data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
