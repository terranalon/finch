import {
  CheckIcon,
  ChartBarIcon,
  DocumentIcon,
  CalendarIcon,
  FolderIcon,
  PlusIcon,
  ArrowRightIcon,
} from '../icons.jsx';

const DATE_FORMAT_OPTIONS = {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
};

function formatDate(date) {
  return date.toLocaleDateString('en-US', DATE_FORMAT_OPTIONS);
}

/**
 * Calculate combined statistics from all file uploads.
 */
function calculateCombinedStats(allUploads) {
  const totalTransactions = allUploads.reduce(
    (sum, upload) => sum + (upload.summary?.totalTransactions || 0),
    0
  );

  const allSymbols = new Set(allUploads.flatMap((upload) => upload.symbols || []));

  const allDates = allUploads
    .flatMap((u) => [u.dateRange?.startDate, u.dateRange?.endDate])
    .filter(Boolean)
    .map((d) => new Date(d))
    .filter((d) => !isNaN(d.getTime()));

  const dateRange = allDates.length > 0
    ? {
        start: formatDate(new Date(Math.min(...allDates))),
        end: formatDate(new Date(Math.max(...allDates))),
      }
    : { start: 'N/A', end: 'N/A' };

  return {
    totalTransactions,
    totalAssets: allSymbols.size,
    dateRange,
  };
}

/**
 * Shows result after each file upload with option to upload more files.
 * Used for brokers like Meitav that require multiple yearly files.
 */
export function FileUploadResultStep({
  currentUpload,
  allUploads,
  onUploadAnother,
  onContinue,
}) {
  const combinedStats = calculateCombinedStats(allUploads);

  const hasMultipleFiles = allUploads.length > 1;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Success header */}
      <div className="text-center mb-8">
        <div className="size-16 rounded-full bg-positive-light dark:bg-positive-bg-dark/30 flex items-center justify-center mx-auto mb-4">
          <CheckIcon className="size-8 text-positive dark:text-positive-dark" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
          File imported successfully!
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg">
          {hasMultipleFiles
            ? `You've imported ${allUploads.length} files covering ${combinedStats.dateRange.start} to ${combinedStats.dateRange.end}.`
            : `We found data from ${currentUpload.summary?.dateRange?.start || 'N/A'} to ${currentUpload.summary?.dateRange?.end || 'N/A'}.`}
        </p>
      </div>

      {/* Import summary card */}
      <div className="rounded-2xl border border-[var(--border-primary)] overflow-hidden mb-6">
        {/* Card header */}
        <div className="px-5 py-4 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)]">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="text-sm font-semibold text-[var(--text-secondary)]">
              <FolderIcon className="size-4 text-[var(--text-tertiary)] mx-auto mb-1" />
              File
            </div>
            <div className="text-sm font-semibold text-[var(--text-secondary)]">
              <DocumentIcon className="size-4 text-purple-600 dark:text-purple-400 mx-auto mb-1" />
              Transactions
            </div>
            <div className="text-sm font-semibold text-[var(--text-secondary)]">
              <ChartBarIcon className="size-4 text-blue-600 dark:text-blue-400 mx-auto mb-1" />
              Assets
            </div>
            <div className="text-sm font-semibold text-[var(--text-secondary)]">
              <CalendarIcon className="size-4 text-amber-600 dark:text-amber-400 mx-auto mb-1" />
              Date Range
            </div>
          </div>
        </div>

        {/* File rows */}
        <div className="divide-y divide-[var(--border-primary)]">
          {allUploads.map((upload, idx) => (
            <div key={idx} className="px-5 py-4 grid grid-cols-4 gap-4 items-center text-center">
              <div className="text-sm text-[var(--text-primary)] truncate" title={upload.fileName}>
                {upload.fileName}
              </div>
              <div className="text-lg font-bold text-[var(--text-primary)] tabular-nums">
                {upload.summary?.totalTransactions || 0}
              </div>
              <div className="text-lg font-bold text-[var(--text-primary)] tabular-nums">
                {upload.summary?.totalAssets || 0}
              </div>
              <div className="text-sm text-[var(--text-secondary)]">
                <span className="block">{upload.summary?.dateRange?.start || 'N/A'}</span>
                <span className="block">to {upload.summary?.dateRange?.end || 'N/A'}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Totals row - only for multiple files */}
        {hasMultipleFiles && (
          <div className="px-5 py-4 grid grid-cols-4 gap-4 items-center text-center bg-positive-light dark:bg-positive-bg-dark/30 border-t-2 border-positive-light dark:border-positive-dark/30">
            <div className="text-sm font-semibold text-positive dark:text-positive-dark">
              Total ({allUploads.length} files)
            </div>
            <div className="text-lg font-bold text-positive dark:text-positive-dark tabular-nums">
              {combinedStats.totalTransactions}
            </div>
            <div className="text-lg font-bold text-positive dark:text-positive-dark tabular-nums">
              {combinedStats.totalAssets}
            </div>
            <div className="text-sm font-semibold text-positive dark:text-positive-dark">
              <span className="block">{combinedStats.dateRange.start}</span>
              <span className="block">to {combinedStats.dateRange.end}</span>
            </div>
          </div>
        )}
      </div>

      {/* Question prompt */}
      <div className="text-center mb-6">
        <p className="text-[var(--text-secondary)]">
          Do you have more files to import?
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          type="button"
          onClick={onUploadAnother}
          className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-base font-semibold border-2 border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
        >
          <PlusIcon className="size-5" />
          Upload Another File
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
        >
          That's All
          <ArrowRightIcon className="size-5" />
        </button>
      </div>
    </div>
  );
}
