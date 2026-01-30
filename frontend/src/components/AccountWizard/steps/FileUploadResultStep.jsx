import {
  CheckIcon,
  ChartBarIcon,
  DocumentIcon,
  CalendarIcon,
  PlusIcon,
  ArrowRightIcon,
} from '../icons.jsx';

/**
 * Reusable stats card component for displaying import statistics.
 */
function StatsCard({ title, transactions, assets, dateStart, dateEnd, variant = 'default' }) {
  const isAccent = variant === 'accent';

  return (
    <div
      className={
        isAccent
          ? 'rounded-2xl border-2 border-emerald-300 dark:border-emerald-700 overflow-hidden'
          : 'rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden'
      }
    >
      <div
        className={
          isAccent
            ? 'px-5 py-3 bg-emerald-100 dark:bg-emerald-900/40 border-b border-emerald-200 dark:border-emerald-800'
            : 'px-5 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700'
        }
      >
        <h3
          className={
            isAccent
              ? 'font-semibold text-emerald-800 dark:text-emerald-300'
              : 'font-semibold text-gray-900 dark:text-white'
          }
        >
          {title}
        </h3>
      </div>
      <div
        className={
          isAccent
            ? 'grid grid-cols-3 divide-x divide-emerald-200 dark:divide-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20'
            : 'grid grid-cols-3 divide-x divide-gray-200 dark:divide-gray-700'
        }
      >
        <div className="p-4 text-center">
          <DocumentIcon
            className={
              isAccent
                ? 'size-5 text-emerald-600 dark:text-emerald-400 mx-auto mb-1.5'
                : 'size-5 text-purple-600 dark:text-purple-400 mx-auto mb-1.5'
            }
          />
          <p
            className={
              isAccent
                ? 'text-xl font-bold text-emerald-700 dark:text-emerald-400 tabular-nums'
                : 'text-xl font-bold text-gray-900 dark:text-white tabular-nums'
            }
          >
            {transactions}
          </p>
          <p
            className={
              isAccent
                ? 'text-xs text-emerald-600 dark:text-emerald-500'
                : 'text-xs text-gray-500 dark:text-gray-400'
            }
          >
            Transactions
          </p>
        </div>
        <div className="p-4 text-center">
          <ChartBarIcon
            className={
              isAccent
                ? 'size-5 text-emerald-600 dark:text-emerald-400 mx-auto mb-1.5'
                : 'size-5 text-blue-600 dark:text-blue-400 mx-auto mb-1.5'
            }
          />
          <p
            className={
              isAccent
                ? 'text-xl font-bold text-emerald-700 dark:text-emerald-400 tabular-nums'
                : 'text-xl font-bold text-gray-900 dark:text-white tabular-nums'
            }
          >
            {assets}
          </p>
          <p
            className={
              isAccent
                ? 'text-xs text-emerald-600 dark:text-emerald-500'
                : 'text-xs text-gray-500 dark:text-gray-400'
            }
          >
            Assets
          </p>
        </div>
        <div className="p-4 text-center">
          <CalendarIcon
            className={
              isAccent
                ? 'size-5 text-emerald-600 dark:text-emerald-400 mx-auto mb-1.5'
                : 'size-5 text-amber-600 dark:text-amber-400 mx-auto mb-1.5'
            }
          />
          <p
            className={
              isAccent
                ? 'text-sm font-semibold text-emerald-700 dark:text-emerald-400'
                : 'text-sm font-semibold text-gray-900 dark:text-white'
            }
          >
            {dateStart}
          </p>
          <p
            className={
              isAccent
                ? 'text-sm font-semibold text-emerald-700 dark:text-emerald-400'
                : 'text-sm font-semibold text-gray-900 dark:text-white'
            }
          >
            to {dateEnd}
          </p>
          <p
            className={
              isAccent
                ? 'text-xs text-emerald-600 dark:text-emerald-500 mt-0.5'
                : 'text-xs text-gray-500 dark:text-gray-400 mt-0.5'
            }
          >
            Date Range
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Shows result after each file upload with option to upload more files.
 * Used for brokers like Meitav that require multiple yearly files.
 */
export function FileUploadResultStep({
  currentUpload,
  allUploads,
  brokerName,
  onUploadAnother,
  onContinue,
}) {
  // Calculate combined stats from all uploads
  const combinedStats = allUploads.reduce(
    (acc, upload) => ({
      totalTransactions: acc.totalTransactions + (upload.summary?.totalTransactions || 0),
      totalAssets: Math.max(acc.totalAssets, upload.summary?.totalAssets || 0),
    }),
    { totalTransactions: 0, totalAssets: 0 }
  );

  // Calculate combined date range
  const allDates = allUploads
    .flatMap((u) => [u.dateRange?.startDate, u.dateRange?.endDate])
    .filter(Boolean)
    .map((d) => new Date(d))
    .filter((d) => !isNaN(d.getTime()));

  const combinedDateRange = allDates.length > 0
    ? {
        start: new Date(Math.min(...allDates)).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        }),
        end: new Date(Math.max(...allDates)).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        }),
      }
    : { start: 'N/A', end: 'N/A' };

  const hasMultipleFiles = allUploads.length > 1;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Success header */}
      <div className="text-center mb-8">
        <div className="size-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
          <CheckIcon className="size-8 text-emerald-600 dark:text-emerald-400" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          File imported successfully!
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          {hasMultipleFiles
            ? `You've imported ${allUploads.length} files covering ${combinedDateRange.start} to ${combinedDateRange.end}.`
            : `We found data from ${currentUpload.summary?.dateRange?.start || 'N/A'} to ${currentUpload.summary?.dateRange?.end || 'N/A'}.`}
        </p>
      </div>

      {/* File stats cards */}
      <div className="space-y-4 mb-6">
        {hasMultipleFiles ? (
          <>
            {/* Individual file cards */}
            {allUploads.map((upload, idx) => (
              <StatsCard
                key={idx}
                title={upload.fileName}
                transactions={upload.summary?.totalTransactions || 0}
                assets={upload.summary?.totalAssets || 0}
                dateStart={upload.summary?.dateRange?.start || 'N/A'}
                dateEnd={upload.summary?.dateRange?.end || 'N/A'}
              />
            ))}

            {/* Combined total card */}
            <StatsCard
              title={`Combined Total (${allUploads.length} files)`}
              transactions={combinedStats.totalTransactions}
              assets={combinedStats.totalAssets}
              dateStart={combinedDateRange.start}
              dateEnd={combinedDateRange.end}
              variant="accent"
            />
          </>
        ) : (
          /* Single file card */
          <StatsCard
            title="Import Summary"
            transactions={currentUpload.summary?.totalTransactions || 0}
            assets={currentUpload.summary?.totalAssets || 0}
            dateStart={currentUpload.summary?.dateRange?.start || 'N/A'}
            dateEnd={currentUpload.summary?.dateRange?.end || 'N/A'}
          />
        )}
      </div>

      {/* Question prompt */}
      <div className="text-center mb-6">
        <p className="text-gray-600 dark:text-gray-400">
          Do you have more files to import?
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          type="button"
          onClick={onUploadAnother}
          className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-base font-semibold border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        >
          <PlusIcon className="size-5" />
          Upload Another File
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
        >
          That's All
          <ArrowRightIcon className="size-5" />
        </button>
      </div>
    </div>
  );
}
