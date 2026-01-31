import {
  CheckIcon,
  ChartBarIcon,
  DocumentIcon,
  BanknotesIcon,
  CalendarIcon,
} from '../icons.jsx';

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
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <ChartBarIcon className="size-6 text-blue-600 dark:text-blue-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.totalAssets || 0}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Assets</p>
        </div>
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-center">
          <DocumentIcon className="size-6 text-purple-600 dark:text-purple-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.totalTransactions || 0}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Transactions</p>
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
