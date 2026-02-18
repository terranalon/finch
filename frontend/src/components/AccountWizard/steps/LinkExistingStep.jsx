import { ArrowLeftIcon, LinkIcon } from '../icons.jsx';

export function LinkExistingStep({ linkableAccounts = [], onSelect, onBack }) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
          Link an existing account
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg">
          Select an account to add to this portfolio.
        </p>
      </div>

      {linkableAccounts.length > 0 ? (
        <div className="space-y-3">
          {linkableAccounts.map((account) => (
            <button
              key={account.id}
              onClick={() => onSelect(account)}
              className="w-full flex items-center justify-between p-5 rounded-xl border-2 border-[var(--border-primary)] hover:border-accent hover:bg-accent-50/50 dark:hover:bg-accent-900/20 transition-all text-left cursor-pointer"
            >
              <div>
                <h3 className="font-semibold text-[var(--text-primary)] text-lg">
                  {account.name}
                </h3>
                <p className="text-[var(--text-tertiary)] mt-1">
                  {account.institution} · {account.account_type} · {account.currency}
                </p>
              </div>
              <span className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors">
                Link
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-[var(--bg-secondary)] rounded-2xl">
          <LinkIcon className="size-16 text-[var(--text-tertiary)] mx-auto mb-4" />
          <p className="text-[var(--text-tertiary)] text-lg">
            No accounts available to link.
          </p>
          <p className="text-[var(--text-tertiary)] mt-2">
            All accounts are already in this portfolio.
          </p>
        </div>
      )}

      <div className="mt-8">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back to account types</span>
        </button>
      </div>
    </div>
  );
}
