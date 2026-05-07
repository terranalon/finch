import { AccountCard } from './AccountCard';
import { PlusIcon } from './icons';

export function AccountGrid({ accounts, accountHoldings, currency, onCardClick, onAddAccount }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-4">
      {accounts.map((account) => (
        <AccountCard
          key={account.id}
          account={account}
          holdings={accountHoldings.get(account.id) || []}
          currency={currency}
          onClick={onCardClick}
        />
      ))}

      {/* Add Account placeholder card */}
      <div
        onClick={onAddAccount}
        className="flex flex-col items-center justify-center gap-2.5 min-h-[200px] cursor-pointer border-2 border-dashed border-[var(--border-primary)] rounded-xl text-[var(--text-faint)] text-[13px] font-medium transition-all hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)] hover:bg-[var(--bg-secondary)]"
      >
        <PlusIcon className="w-6 h-6" />
        Add Account
      </div>
    </div>
  );
}
