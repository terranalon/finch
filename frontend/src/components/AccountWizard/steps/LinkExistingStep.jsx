import { ArrowLeftIcon, LinkIcon } from '../icons.jsx';

export function LinkExistingStep({ linkableAccounts = [], onSelect, onBack }) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Link an existing account
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          Select an account to add to this portfolio.
        </p>
      </div>

      {linkableAccounts.length > 0 ? (
        <div className="space-y-3">
          {linkableAccounts.map((account) => (
            <button
              key={account.id}
              onClick={() => onSelect(account)}
              className="w-full flex items-center justify-between p-5 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-left cursor-pointer"
            >
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
                  {account.name}
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  {account.institution} · {account.account_type} · {account.currency}
                </p>
              </div>
              <span className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">
                Link
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-2xl">
          <LinkIcon className="size-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400 text-lg">
            No accounts available to link.
          </p>
          <p className="text-gray-400 dark:text-gray-500 mt-2">
            All accounts are already in this portfolio.
          </p>
        </div>
      )}

      <div className="mt-8">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back to account types</span>
        </button>
      </div>
    </div>
  );
}
