import { useState } from 'react';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { cn } from '../../lib';

export function AccountActionDialog({ isOpen, onClose, account, portfolioId }) {
  const { unlinkAccount, deleteAccount, portfolios } = usePortfolioPage();
  const [acting, setActing] = useState(null);

  const portfolioCount = portfolios.filter(
    (p) => p.accounts?.some((a) => a.id === account?.id)
  ).length;
  const canUnlink = portfolioCount > 1;
  const unlinkBlockedReason = canUnlink
    ? null
    : 'This account only exists in this portfolio and cannot be unlinked. Use "Delete" to remove it.';

  const handleUnlink = async () => {
    setActing('unlink');
    const ok = await unlinkAccount(portfolioId, account.id);
    setActing(null);
    if (ok) onClose();
  };

  const handleDelete = async () => {
    setActing('delete');
    const ok = await deleteAccount(account.id);
    setActing(null);
    if (ok) onClose();
  };

  if (!isOpen || !account) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl p-6 max-w-sm w-full shadow-xl">
          <h3 className="text-base font-semibold text-[var(--text-primary)] mb-4">
            Remove Account
          </h3>

          <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-secondary)] mb-4">
            <BrokerLogo type={account.broker_type} className="size-9 rounded-lg object-contain flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">{account.name}</p>
              <p className="text-xs text-[var(--text-tertiary)]">
                {[account.account_type, account.currency].filter(Boolean).join(' · ')}
              </p>
            </div>
          </div>

          <p className="text-sm text-[var(--text-secondary)] mb-4">
            How would you like to remove this account?
          </p>

          <div className="flex flex-col gap-2 mb-5">
            {/* Wrapper div carries the tooltip when the button is disabled */}
            <div title={unlinkBlockedReason ?? undefined}>
              <button
                onClick={handleUnlink}
                disabled={!!acting || !canUnlink}
                className={cn(
                  'w-full px-4 py-3 rounded-lg text-sm font-medium text-left border border-[var(--border-primary)] bg-[var(--bg-secondary)] transition-colors',
                  canUnlink && !acting
                    ? 'hover:bg-[var(--bg-tertiary)] cursor-pointer'
                    : 'opacity-50 cursor-not-allowed pointer-events-none'
                )}
              >
                <span className="block text-[var(--text-primary)]">
                  {acting === 'unlink' ? 'Unlinking...' : 'Unlink from this portfolio'}
                </span>
                <span className="block text-xs text-[var(--text-tertiary)] mt-0.5">
                  {canUnlink
                    ? 'The account remains available in other portfolios'
                    : 'Not available — account only exists in this portfolio'}
                </span>
              </button>
            </div>

            <button
              onClick={handleDelete}
              disabled={!!acting}
              className="w-full px-4 py-3 rounded-lg text-sm font-medium text-left border border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer disabled:opacity-50"
            >
              <span className="block text-[var(--negative)]">
                {acting === 'delete' ? 'Deleting...' : 'Delete account permanently'}
              </span>
              <span className="block text-xs text-[var(--text-tertiary)] mt-0.5">
                Removes the account and all its transaction history
              </span>
            </button>
          </div>

          <button
            onClick={onClose}
            disabled={!!acting}
            className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}
