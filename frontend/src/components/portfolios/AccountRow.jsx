import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { formatCurrency } from '../../lib';
import { XMarkIcon } from './icons';
import { AccountActionDialog } from './AccountActionDialog';

export function AccountRow({ account, portfolioId }) {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);

  const meta = [account.account_type, account.currency, formatCurrency(account.value, account.currency, { compact: true })]
    .filter(Boolean)
    .join(' · ');

  return (
    <>
      <div className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-[var(--bg-tertiary)] mb-1.5 last:mb-0">
        <button
          onClick={() => navigate(`/accounts/${account.id}`, { state: { backTo: '/portfolios', backLabel: 'Back to Portfolios' } })}
          className="flex items-center gap-2.5 flex-1 min-w-0 text-left cursor-pointer hover:opacity-80 transition-opacity"
        >
          <BrokerLogo type={account.broker_type} className="size-8 rounded-lg object-contain flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-[var(--text-primary)] leading-tight truncate">
              {account.name}
            </p>
            <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{meta}</p>
          </div>
        </button>
        <button
          onClick={() => setDialogOpen(true)}
          className="p-1.5 ml-2 rounded-md text-[var(--text-tertiary)] hover:text-[var(--negative)] hover:bg-red-500/10 transition-all cursor-pointer flex-shrink-0"
          title="Remove account"
        >
          <XMarkIcon className="w-3.5 h-3.5" />
        </button>
      </div>

      <AccountActionDialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        account={account}
        portfolioId={portfolioId}
      />
    </>
  );
}
