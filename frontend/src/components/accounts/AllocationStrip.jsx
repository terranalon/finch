import { formatCurrency } from '../../lib';
import { Skeleton } from '../ui';

const BROKER_COLORS = {
  ibkr: '#E31937',
  meitav: '#2563EB',
  kraken: '#7B61FF',
  bit2c: '#F7931A',
  binance: '#F0B90B',
};

function getBrokerColor(brokerType) {
  return BROKER_COLORS[brokerType] || 'var(--text-tertiary)';
}

export function AllocationStrip({ accounts, totalValue, currency, loading }) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-5 w-24" />
        </div>
        <Skeleton className="h-2 w-full rounded-full" />
        <div className="flex gap-2 mt-2.5">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-7 w-24 rounded-md" />)}
        </div>
      </div>
    );
  }

  if (!accounts || accounts.length === 0) return null;

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4 mb-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold text-[var(--text-secondary)]">
          Portfolio Allocation
        </span>
        <span className="text-base font-bold font-mono tabular-nums">
          {formatCurrency(totalValue, currency, { decimals: 0 })}
        </span>
      </div>

      {/* Stacked bar */}
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        {accounts.map((acct) => (
          <div
            key={acct.id}
            className="h-full rounded-sm min-w-[4px] transition-opacity hover:opacity-80"
            style={{
              width: `${acct.allocationPct}%`,
              backgroundColor: getBrokerColor(acct.broker_type),
            }}
            title={`${acct.name}: ${formatCurrency(acct.value, currency, { decimals: 0 })} (${acct.allocationPct.toFixed(1)}%)`}
          />
        ))}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2 mt-2.5">
        {accounts.map((acct) => (
          <div
            key={acct.id}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-[var(--text-secondary)] bg-[var(--bg-tertiary)]"
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: getBrokerColor(acct.broker_type) }}
            />
            {acct.name}
            <span className="font-mono tabular-nums text-[11px] text-[var(--text-tertiary)]">
              {acct.allocationPct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
