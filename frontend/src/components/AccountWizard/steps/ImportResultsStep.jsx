import { CheckIcon } from '../icons.jsx';

function ChartBarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
    </svg>
  );
}

function DocumentTextIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function BanknotesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
    </svg>
  );
}

function CalendarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
    </svg>
  );
}

export function ImportResultsStep({ broker, importResults, onContinue }) {
  const { assets = [], summary = {} } = importResults || {};

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <div className="size-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
          <CheckIcon className="size-8 text-emerald-600 dark:text-emerald-400" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Data imported successfully!
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          Here's what we found in your {broker?.name || ''} account.
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <ChartBarIcon className="size-6 text-blue-600 dark:text-blue-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.totalAssets || 0}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Assets</p>
        </div>
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <DocumentTextIcon className="size-6 text-purple-600 dark:text-purple-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.totalTransactions || 0}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Transactions</p>
        </div>
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <BanknotesIcon className="size-6 text-emerald-600 dark:text-emerald-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            ${(summary.totalValue || 0).toLocaleString()}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Value</p>
        </div>
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <CalendarIcon className="size-6 text-amber-600 dark:text-amber-400 mx-auto mb-2" />
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            {summary.dateRange?.start || 'N/A'}
          </p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            to {summary.dateRange?.end || 'N/A'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Date Range</p>
        </div>
      </div>

      {/* Top Holdings Preview */}
      {assets.length > 0 && (
        <div className="rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-8">
          <div className="px-5 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-white">Top Holdings</h3>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {assets.slice(0, 4).map((asset, idx) => (
              <div key={idx} className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-4">
                  <div className="size-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                    <span className="text-sm font-bold text-gray-600 dark:text-gray-400">
                      {asset.symbol?.slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{asset.symbol}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{asset.name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900 dark:text-white">
                    ${(asset.value || 0).toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {asset.quantity} shares
                  </p>
                </div>
              </div>
            ))}
          </div>
          {(summary.totalAssets || 0) > 4 && (
            <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 text-center">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                +{(summary.totalAssets || 0) - 4} more assets
              </span>
            </div>
          )}
        </div>
      )}

      {/* Cash Balance */}
      {(summary.cashBalance || 0) > 0 && (
        <div className="flex items-center justify-between p-5 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 mb-8">
          <div className="flex items-center gap-3">
            <BanknotesIcon className="size-6 text-emerald-600 dark:text-emerald-400" />
            <span className="font-medium text-emerald-800 dark:text-emerald-300">Cash Balance</span>
          </div>
          <span className="text-xl font-bold text-emerald-700 dark:text-emerald-400">
            ${(summary.cashBalance || 0).toLocaleString()}
          </span>
        </div>
      )}

      {/* Continue Button */}
      <div className="flex justify-center">
        <button
          type="button"
          onClick={onContinue}
          className="px-8 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
