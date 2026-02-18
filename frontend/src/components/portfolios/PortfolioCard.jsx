import { useState } from 'react';
import { cn, formatCurrency } from '../../lib';
import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { StarIcon, PencilIcon } from './icons';
import { AccountRow } from './AccountRow';
import { SetDefaultDialog } from './SetDefaultDialog';
import { DeleteConfirmDialog } from './DeleteConfirmDialog';
import { LinkAccountDropdown } from './LinkAccountDropdown';
import { PortfolioModal } from './PortfolioModal';

export function PortfolioCard({ portfolio }) {
  const { updatePortfolio, setDefault } = usePortfolioPage();
  const [showDefaultDialog, setShowDefaultDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async (data) => {
    setSaving(true);
    const ok = await updatePortfolio(portfolio.id, data);
    setSaving(false);
    if (ok) setShowEditModal(false);
  };

  const accounts = portfolio.accounts || [];
  const accountCount = accounts.length;

  return (
    <>
      <div
        className={cn(
          'bg-[var(--bg-secondary)] border rounded-xl overflow-hidden flex flex-col transition-colors',
          portfolio.is_default
            ? 'border-amber-500/30'
            : 'border-[var(--border-primary)] hover:border-[var(--border-secondary)]'
        )}
      >
        <div className="flex items-start justify-between p-[18px] border-b border-[var(--border-primary)] flex-shrink-0">
          <div className="flex items-start gap-2 min-w-0">
            <button
              onClick={() => !portfolio.is_default && setShowDefaultDialog(true)}
              className={cn(
                'mt-0.5 p-0.5 transition-all',
                portfolio.is_default
                  ? 'text-amber-400 cursor-default'
                  : 'text-[var(--text-tertiary)] hover:text-amber-400 hover:scale-110 cursor-pointer'
              )}
              title={portfolio.is_default ? 'Default portfolio' : 'Set as default'}
            >
              <StarIcon filled={portfolio.is_default} className="w-4 h-4" />
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[15px] font-semibold text-[var(--text-primary)] leading-tight">
                  {portfolio.name}
                </span>
                <button
                  onClick={() => setShowEditModal(true)}
                  className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                  title="Edit portfolio"
                >
                  <PencilIcon className="w-3.5 h-3.5" />
                </button>
                {portfolio.is_default && (
                  <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-amber-500/15 text-amber-400">
                    Default
                  </span>
                )}
              </div>
              <p className="text-[19px] font-bold text-[var(--text-primary)] mt-1 tabular-nums">
                {formatCurrency(portfolio.total_value, portfolio.default_currency, { compact: true })}
              </p>
              {portfolio.description && (
                <p className="text-[12px] text-[var(--text-tertiary)] mt-1 leading-snug line-clamp-2">
                  {portfolio.description}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="px-[18px] py-3.5 flex-1 overflow-y-auto max-h-[260px]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-tertiary)] mb-2">
            Accounts ({accountCount})
          </p>
          {accounts.length === 0 ? (
            <p className="text-xs text-[var(--text-tertiary)] py-2">No accounts linked yet.</p>
          ) : (
            accounts.map((account) => (
              <AccountRow
                key={account.id}
                account={account}
                portfolioId={portfolio.id}
              />
            ))
          )}
        </div>

        <div className="px-[18px] py-2.5 border-t border-[var(--border-primary)] flex items-center justify-between flex-shrink-0">
          <LinkAccountDropdown portfolioId={portfolio.id} />
          <button
            onClick={() => setShowDeleteDialog(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--negative)] border border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer"
          >
            Delete
          </button>
        </div>
      </div>

      <SetDefaultDialog
        isOpen={showDefaultDialog}
        onClose={() => setShowDefaultDialog(false)}
        portfolio={portfolio}
        onConfirm={setDefault}
      />
      <DeleteConfirmDialog
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        portfolio={portfolio}
      />
      <PortfolioModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        portfolio={portfolio}
        onSave={handleSave}
        loading={saving}
      />
    </>
  );
}
