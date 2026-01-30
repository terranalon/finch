import {
  CheckIcon,
  ChartBarIcon,
  DocumentIcon,
  CalendarIcon,
  PlusIcon,
  ArrowRightIcon,
} from '../icons.jsx';

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
          {allUploads.length === 1
            ? `We found data from ${currentUpload.summary?.dateRange?.start || 'N/A'} to ${currentUpload.summary?.dateRange?.end || 'N/A'}.`
            : `You've imported ${allUploads.length} files covering ${combinedDateRange.start} to ${combinedDateRange.end}.`}
        </p>
      </div>

      {/* Current upload stats */}
      <div className="rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
        <div className="px-5 py-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {allUploads.length === 1 ? 'Import Summary' : 'Latest Import'}
          </h3>
        </div>
        <div className="grid grid-cols-3 divide-x divide-gray-200 dark:divide-gray-700">
          <div className="p-5 text-center">
            <DocumentIcon className="size-6 text-purple-600 dark:text-purple-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
              {currentUpload.summary?.totalTransactions || 0}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Transactions</p>
          </div>
          <div className="p-5 text-center">
            <ChartBarIcon className="size-6 text-blue-600 dark:text-blue-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
              {currentUpload.summary?.totalAssets || 0}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">Assets</p>
          </div>
          <div className="p-5 text-center">
            <CalendarIcon className="size-6 text-amber-600 dark:text-amber-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              {currentUpload.summary?.dateRange?.start || 'N/A'}
            </p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              to {currentUpload.summary?.dateRange?.end || 'N/A'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Date Range</p>
          </div>
        </div>
      </div>

      {/* Combined stats (if multiple uploads) */}
      {allUploads.length > 1 && (
        <div className="rounded-2xl border-2 border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20 p-5 mb-6">
          <h4 className="font-semibold text-emerald-800 dark:text-emerald-300 mb-3">
            Combined Total ({allUploads.length} files)
          </h4>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400 tabular-nums">
                {combinedStats.totalTransactions}
              </p>
              <p className="text-sm text-emerald-600 dark:text-emerald-500">Transactions</p>
            </div>
            <div>
              <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400 tabular-nums">
                {combinedStats.totalAssets}
              </p>
              <p className="text-sm text-emerald-600 dark:text-emerald-500">Assets</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                {combinedDateRange.start}
              </p>
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                to {combinedDateRange.end}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload history */}
      {allUploads.length > 1 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Imported Files
          </h4>
          <div className="space-y-2">
            {allUploads.map((upload, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm"
              >
                <span className="text-gray-700 dark:text-gray-300">{upload.fileName}</span>
                <span className="text-gray-500 dark:text-gray-400">
                  {upload.summary?.dateRange?.start} - {upload.summary?.dateRange?.end}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Question prompt */}
      <div className="text-center mb-6">
        <p className="text-gray-600 dark:text-gray-400">
          Do you have more files to import for earlier years?
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
