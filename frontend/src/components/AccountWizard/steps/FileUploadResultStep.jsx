import {
  CheckIcon,
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

      {/* Import summary table */}
      <div className="rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">
                File
              </th>
              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700 dark:text-gray-300">
                Transactions
              </th>
              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700 dark:text-gray-300">
                Assets
              </th>
              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700 dark:text-gray-300">
                Date Range
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {allUploads.map((upload, idx) => (
              <tr key={idx}>
                <td className="px-4 py-3 text-sm text-gray-900 dark:text-white truncate max-w-[200px]" title={upload.fileName}>
                  {upload.fileName}
                </td>
                <td className="px-4 py-3 text-sm text-right tabular-nums text-gray-900 dark:text-white">
                  {upload.summary?.totalTransactions || 0}
                </td>
                <td className="px-4 py-3 text-sm text-right tabular-nums text-gray-900 dark:text-white">
                  {upload.summary?.totalAssets || 0}
                </td>
                <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                  {upload.summary?.dateRange?.start || 'N/A'} - {upload.summary?.dateRange?.end || 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
          {/* Totals footer - only show for multiple files */}
          {hasMultipleFiles && (
            <tfoot>
              <tr className="bg-emerald-50 dark:bg-emerald-950/30 border-t-2 border-emerald-300 dark:border-emerald-700">
                <td className="px-4 py-3 text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                  Total ({allUploads.length} files)
                </td>
                <td className="px-4 py-3 text-sm text-right tabular-nums font-semibold text-emerald-700 dark:text-emerald-400">
                  {combinedStats.totalTransactions}
                </td>
                <td className="px-4 py-3 text-sm text-right tabular-nums font-semibold text-emerald-700 dark:text-emerald-400">
                  {combinedStats.totalAssets}
                </td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-emerald-700 dark:text-emerald-400">
                  {combinedDateRange.start} - {combinedDateRange.end}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
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
