import { cn, formatCurrency } from '../../lib';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { TYPE_LABELS } from './constants';

export function AccountCard({ account, holdings, currency, onClick }) {
  const topHoldings = (holdings || []).slice(0, 3);
  const remainingCount = (holdings || []).length - 3;

  return (
    <div
      onClick={() => onClick(account)}
      className={cn(
        'bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl',
        'p-5 cursor-pointer transition-all flex flex-col gap-3.5',
        'hover:border-[var(--accent-primary)] hover:shadow-[0_0_0_1px_var(--accent-primary)]'
      )}
    >
      {/* Header: logo + name + type */}
      <div className="flex items-center gap-3">
        <BrokerLogo type={account.broker_type} className="w-10 h-10 rounded-[10px] shrink-0" />
        <div className="min-w-0 flex-1">
          <span className="text-[15px] font-semibold text-[var(--text-primary)]">
            {account.name}
          </span>
          <span className="inline-block ml-2 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]">
            {TYPE_LABELS[account.account_type] || account.account_type}
          </span>
        </div>
      </div>

      {/* Value row */}
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold font-mono tabular-nums tracking-tight">
          {formatCurrency(account.value, currency, { decimals: 0 })}
        </span>
        <span className="text-[13px] font-semibold font-mono tabular-nums text-[var(--text-tertiary)]">
          {account.allocationPct.toFixed(1)}%
        </span>
      </div>

      {/* Holdings pills */}
      {topHoldings.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {topHoldings.map((h) => (
            <div
              key={h.symbol}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-subtle)]"
            >
              <span>{h.symbol}</span>
              <span className="font-mono tabular-nums text-[10px] text-[var(--text-tertiary)]">
                {formatCurrency(h.marketValue, currency, { decimals: 0 })}
              </span>
            </div>
          ))}
          {remainingCount > 0 && (
            <div className="px-2 py-1 rounded-md text-[10px] font-semibold bg-[var(--blue-muted)] text-[var(--accent-primary)] border border-transparent">
              +{remainingCount} more
            </div>
          )}
        </div>
      )}

      {/* Footer: sync status */}
      <div className="flex items-center pt-2.5 border-t border-[var(--border-subtle)]">
        <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-faint)]">
          <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', account.syncStatus.color)} />
          Last synced {account.lastSyncFormatted}
        </div>
      </div>
    </div>
  );
}
