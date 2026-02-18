import {
  CheckIcon,
  ChartBarIcon,
  DocumentIcon,
  BanknotesIcon,
  CalendarIcon,
} from '../icons.jsx';

function ExclamationTriangleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  );
}

export function ImportResultsStep({ broker, importResults, onContinue }) {
  const { assets = [], summary = {}, emptySnapshot = false } = importResults || {};

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        {emptySnapshot ? (
          <>
            <div className="size-16 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto mb-4">
              <ExclamationTriangleIcon className="size-8 text-amber-600 dark:text-amber-400" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
              No positions found
            </h2>
            <p className="text-[var(--text-tertiary)] text-lg">
              We connected to {broker?.name || 'your broker'} but found no open positions. This
              usually means your Flex Query doesn't include the <strong>Open Positions</strong> section.
            </p>
          </>
        ) : (
          <>
            <div className="size-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
              <CheckIcon className="size-8 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
              Data imported successfully!
            </h2>
            <p className="text-[var(--text-tertiary)] text-lg">
              Here's what we found in your {broker?.name || ''} account.
            </p>
          </>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-center">
          <ChartBarIcon className="size-6 text-blue-600 dark:text-blue-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-[var(--text-primary)] font-mono tabular-nums">{summary.totalAssets || 0}</p>
          <p className="text-sm text-[var(--text-tertiary)]">Assets</p>
        </div>
        <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-center">
          <DocumentIcon className="size-6 text-purple-600 dark:text-purple-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-[var(--text-primary)] font-mono tabular-nums">{summary.totalTransactions || 0}</p>
          <p className="text-sm text-[var(--text-tertiary)]">Transactions</p>
        </div>
        <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-center">
          <CalendarIcon className="size-6 text-amber-600 dark:text-amber-400 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            {summary.dateRange?.start || 'N/A'}
          </p>
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            to {summary.dateRange?.end || 'N/A'}
          </p>
          <p className="text-xs text-[var(--text-tertiary)] mt-1">Date Range</p>
        </div>
      </div>

      {/* Top Holdings Preview */}
      {assets.length > 0 && (
        <div className="rounded-2xl border border-[var(--border-primary)] overflow-hidden mb-8">
          <div className="px-5 py-4 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)]">
            <h3 className="font-semibold text-[var(--text-primary)]">Top Holdings</h3>
          </div>
          <div className="divide-y divide-[var(--border-primary)]">
            {assets.slice(0, 4).map((asset, idx) => (
              <div key={idx} className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-4">
                  <div className="size-10 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
                    <span className="text-sm font-bold text-[var(--text-secondary)]">
                      {asset.symbol?.slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-[var(--text-primary)]">{asset.symbol}</p>
                    <p className="text-sm text-[var(--text-tertiary)]">{asset.name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-[var(--text-primary)] font-mono tabular-nums">
                    ${(asset.value || 0).toLocaleString()}
                  </p>
                  <p className="text-sm text-[var(--text-tertiary)]">
                    {asset.quantity} shares
                  </p>
                </div>
              </div>
            ))}
          </div>
          {(summary.totalAssets || 0) > 4 && (
            <div className="px-5 py-3 bg-[var(--bg-secondary)] border-t border-[var(--border-primary)] text-center">
              <span className="text-sm text-[var(--text-tertiary)]">
                +{(summary.totalAssets || 0) - 4} more assets
              </span>
            </div>
          )}
        </div>
      )}

      {/* Cash Balance */}
      {(summary.cashBalance || 0) > 0 && (
        <div className="flex items-center justify-between p-5 rounded-xl bg-positive-light dark:bg-positive-bg-dark/20 border border-positive-light dark:border-positive-dark/30 mb-8">
          <div className="flex items-center gap-3">
            <BanknotesIcon className="size-6 text-positive dark:text-positive-dark" />
            <span className="font-medium text-positive dark:text-positive-dark">Cash Balance</span>
          </div>
          <span className="text-xl font-bold text-positive dark:text-positive-dark font-mono tabular-nums">
            ${(summary.cashBalance || 0).toLocaleString()}
          </span>
        </div>
      )}

      {/* Continue Button */}
      <div className="flex justify-center">
        <button
          type="button"
          onClick={onContinue}
          className="px-8 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
