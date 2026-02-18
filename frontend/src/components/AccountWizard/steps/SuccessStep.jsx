import { useState } from 'react';

import { CheckIcon, SparklesIcon, UploadIcon } from '../icons.jsx';
import { BatchUploadModal } from '../../BatchUploadModal.jsx';

export function SuccessStep({
  broker,
  accountDetails,
  skippedData,
  hasSnapshotData,
  createdAccountId,
  onViewAccount,
  onAddAnother,
  onDone,
}) {
  const isManual = !broker;
  const [showBatchUpload, setShowBatchUpload] = useState(false);

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="size-20 rounded-full bg-positive-light dark:bg-positive-bg-dark/30 flex items-center justify-center mx-auto mb-6">
        <CheckIcon className="size-10 text-positive dark:text-positive-dark" />
      </div>

      <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
        You're all set!
      </h2>
      <p className="text-[var(--text-tertiary)] text-lg mb-8">
        Your {isManual ? '' : `${broker.name} `}account has been added to your portfolio.
      </p>

      {/* Account summary card */}
      <div className="p-6 rounded-2xl bg-[var(--bg-secondary)] border-2 border-[var(--border-primary)] text-left mb-8">
        <h3 className="text-xl font-semibold text-[var(--text-primary)]">
          {accountDetails?.name || 'My Account'}
        </h3>
        {accountDetails?.description && (
          <p className="text-[var(--text-tertiary)] mt-1">
            {accountDetails.description}
          </p>
        )}
        <p className="text-[var(--text-tertiary)] mt-2">
          {broker?.name || 'Manual'} · {accountDetails?.accountType || 'Investment'} · {accountDetails?.currency || 'USD'}
        </p>

        {skippedData && (
          <div className="mt-4 pt-4 border-t border-[var(--border-primary)]">
            <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400">
              <SparklesIcon className="size-5" />
              <span className="font-medium">Import your data to start tracking</span>
            </div>
          </div>
        )}
      </div>

      {/* Full history success message */}
      {!hasSnapshotData && !skippedData && !isManual && (
        <div className="p-5 rounded-2xl bg-positive-light dark:bg-positive-bg-dark/20 border border-positive-light dark:border-positive-dark/30 text-left mb-8">
          <div className="flex items-start gap-3">
            <CheckIcon className="size-5 text-positive dark:text-positive-dark flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Your complete transaction history has been imported.
              </p>
              <p className="text-sm text-[var(--text-secondary)] mt-1">
                All trades, dividends, transfers, and cash transactions are included.
                New transactions will be imported automatically.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload History section -- only for snapshot-onboarded accounts */}
      {hasSnapshotData && (
        <div className="p-5 rounded-2xl bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800 text-left mb-8">
          <div className="flex items-start gap-3">
            <UploadIcon className="size-5 text-accent dark:text-accent-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Your current positions have been imported.
              </p>
              <p className="text-sm text-[var(--text-secondary)] mt-1">
                Your account doesn't include historical transactions yet. To track
                performance over time, upload your transaction history files from{' '}
                {broker?.name || 'your broker'}.
              </p>
              <div className="mt-4 flex items-center gap-4">
                <button
                  type="button"
                  aria-label="Upload History"
                  onClick={() => setShowBatchUpload(true)}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
                >
                  Upload History
                </button>
                <span className="text-xs text-[var(--text-tertiary)]">
                  You can also do this later from Account Settings
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="space-y-3">
        <button
          type="button"
          onClick={onViewAccount}
          className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
        >
          View Account
        </button>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onAddAnother}
            className="flex-1 px-6 py-3 rounded-xl text-base font-semibold border-2 border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
          >
            Add Another
          </button>
          <button
            type="button"
            onClick={onDone}
            className="flex-1 px-6 py-3 rounded-xl text-base font-semibold border-2 border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>

      {/* Batch Upload Modal */}
      {hasSnapshotData && createdAccountId && (
        <BatchUploadModal
          isOpen={showBatchUpload}
          onClose={() => setShowBatchUpload(false)}
          accountId={createdAccountId}
          brokerType={broker?.type}
          supportedFormats={broker?.supportedFormats || []}
        />
      )}
    </div>
  );
}
