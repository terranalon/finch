import { useState } from 'react';
import { cn, formatCurrency } from '../../lib';
import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { StarIcon, PencilIcon, ChevronDownIcon } from './icons';
import { AccountRow } from './AccountRow';
import { SetDefaultDialog } from './SetDefaultDialog';
import { DeleteConfirmDialog } from './DeleteConfirmDialog';
import { LinkAccountDropdown } from './LinkAccountDropdown';
import { PortfolioModal } from './PortfolioModal';

export function PortfolioAccordionItem({ portfolio }) {
  const { updatePortfolio, setDefault } = usePortfolioPage();
  const [expanded, setExpanded] = useState(portfolio.is_default);
  const [showDefaultDialog, setShowDefaultDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const accounts = portfolio.accounts || [];
  const accountCount = accounts.length;

  const handleSave = async (data) => {
    setSaving(true);
    const ok = await updatePortfolio(portfolio.id, data);
    setSaving(false);
    if (ok) setShowEditModal(false);
  };

  const handleHeaderClick = (e) => {
    // Don't toggle accordion if clicking interactive elements
    if (e.target.closest('button')) return;
    setExpanded((prev) => !prev);
  };

  return (
    <>
      <div
        className={cn(
          'bg-[var(--bg-secondary)] border rounded-xl overflow-hidden transition-colors',
          portfolio.is_default && !expanded && 'border-amber-500/30',
          expanded ? 'border-accent/40' : 'border-[var(--border-primary)] hover:border-[var(--border-secondary)]'
        )}
      >
        <div
          className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors select-none"
          onClick={handleHeaderClick}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={(e) => { e.stopPropagation(); if (!portfolio.is_default) setShowDefaultDialog(true); }}
              className={cn(
                'p-0.5 transition-all',
                portfolio.is_default
                  ? 'text-amber-400 cursor-default'
                  : 'text-[var(--text-tertiary)] hover:text-amber-400 hover:scale-110 cursor-pointer'
              )}
              title={portfolio.is_default ? 'Default portfolio' : 'Set as default'}
            >
              <StarIcon filled={portfolio.is_default} className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[15px] font-semibold text-[var(--text-primary)]">
                {portfolio.name}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); setShowEditModal(true); }}
                className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
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
          </div>

          <div className="flex items-center gap-3.5">
            <span className="text-xs text-[var(--text-tertiary)] hidden sm:inline">
              {accountCount} account{accountCount !== 1 ? 's' : ''}
            </span>
            <span className="text-base font-semibold text-[var(--text-primary)] tabular-nums">
              {formatCurrency(portfolio.total_value, portfolio.default_currency, { compact: true })}
            </span>
            <ChevronDownIcon
              className={cn(
                'w-[18px] h-[18px] text-[var(--text-tertiary)] transition-transform duration-200',
                expanded && 'rotate-180'
              )}
            />
          </div>
        </div>

        <div
          className={cn(
            'overflow-hidden transition-[max-height] duration-[250ms] ease-out',
            expanded ? 'max-h-[600px] duration-300' : 'max-h-0'
          )}
        >
          <div className="px-5 pb-[18px] border-t border-[var(--border-primary)]">
            {portfolio.description && (
              <p className="text-xs text-[var(--text-tertiary)] pt-3 pb-1 leading-snug">
                {portfolio.description}
              </p>
            )}
            <div className="pt-3.5">
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

            <div className="flex gap-1.5 pt-2.5 mt-2.5 border-t border-[var(--border-primary)]">
              <LinkAccountDropdown portfolioId={portfolio.id} />
              <button
                onClick={() => setShowDeleteDialog(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--negative)] border border-red-500/30 hover:bg-red-500/10 transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
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
