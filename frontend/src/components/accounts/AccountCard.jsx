import { useState } from 'react';
import { cn, formatCurrency } from '../../lib';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { TrashIcon } from './icons';
import { TYPE_LABELS } from './constants';

export function AccountCard({ account, holdings, currency, onClick, onDelete }) {
  const topHoldings = (holdings || []).slice(0, 3);
  const remainingCount = (holdings || []).length - 3;
  const [showConfirm, setShowConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const isShared = (account.portfolio_ids?.length ?? 0) > 1;

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    setShowConfirm(true);
  };

  const handleCancel = (e) => {
    e.stopPropagation();
    setShowConfirm(false);
  };

  const handleConfirm = async (e) => {
    e.stopPropagation();
    setIsDeleting(true);
    try {
      await onDelete?.(account.id);
    } catch {
      setIsDeleting(false);
      setShowConfirm(false);
    }
  };

  return (
    <div
      onClick={() => !showConfirm && onClick(account)}
      className={cn(
        'relative bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl',
        'p-5 cursor-pointer transition-all flex flex-col gap-3.5',
        !showConfirm && 'hover:border-[var(--accent-primary)] hover:shadow-[0_0_0_1px_var(--accent-primary)]'
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

      {/* Footer: sync status + trash */}
      <div className="flex items-center justify-between pt-2.5 border-t border-[var(--border-subtle)]">
        <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-faint)]">
          <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', account.syncStatus.color)} />
          Last synced {account.lastSyncFormatted}
        </div>
        <button
          onClick={handleDeleteClick}
          className="w-6 h-6 flex items-center justify-center rounded text-[var(--text-faint)] hover:text-[var(--negative)] hover:bg-[var(--negative)]/10 transition-all cursor-pointer"
          title={isShared ? 'Remove from portfolio' : 'Delete account'}
        >
          <TrashIcon className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Delete confirmation overlay */}
      {showConfirm && (
        <div
          className="absolute inset-0 rounded-xl bg-[var(--bg-secondary)]/95 backdrop-blur-[2px] flex flex-col items-center justify-center gap-3 p-5 border border-[var(--negative)]/30"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-[13px] text-[var(--text-secondary)] text-center">
            {isShared
              ? 'Remove this account from the current portfolio?'
              : 'Permanently delete this account and all its data?'}
          </p>
          <div className="flex gap-2 w-full">
            <button
              onClick={handleCancel}
              className="flex-1 px-3 py-1.5 rounded-md text-xs font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isDeleting}
              className="flex-1 px-3 py-1.5 rounded-md text-xs font-semibold bg-[var(--negative)] text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
            >
              {isDeleting ? 'Deleting...' : isShared ? 'Remove' : 'Delete'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
