import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { formatCurrency } from '../../lib';
import { XMarkIcon } from './icons';

export function AccountRow({ account, portfolioId, onUnlink }) {
  const meta = [account.account_type, account.currency, formatCurrency(account.value, account.currency, { compact: true })]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-[var(--bg-tertiary)] mb-1.5 last:mb-0">
      <div className="flex items-center gap-2.5">
        <BrokerLogo type={account.broker_type} className="size-8 rounded-lg object-contain" />
        <div>
          <p className="text-[13px] font-medium text-[var(--text-primary)] leading-tight">
            {account.name}
          </p>
          <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{meta}</p>
        </div>
      </div>
      {onUnlink && (
        <button
          onClick={() => onUnlink(portfolioId, account.id)}
          className="p-1.5 rounded-md text-[var(--text-tertiary)] hover:text-[var(--negative)] hover:bg-red-500/10 transition-all cursor-pointer"
          title="Unlink account"
        >
          <XMarkIcon className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
