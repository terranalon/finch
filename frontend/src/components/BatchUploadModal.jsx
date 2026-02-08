/**
 * BatchUploadModal -- manages multi-file batch uploads with session ID,
 * coverage timeline, finalization, and validation display.
 *
 * Used by:
 * - SuccessStep "Upload History" action (wizard flow)
 * - Accounts page "Upload File" action (all accounts)
 */

import { useState, useCallback, useMemo } from 'react';

import { api } from '../lib/index.js';
import { useFileUpload } from './AccountWizard/hooks/useFileUpload.js';
import { CoverageTimeline } from './CoverageTimeline.jsx';

// --- Icons (inline to avoid circular import with AccountWizard/icons) ---

function XIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function UploadIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

// --- Validation Banner ---

function ValidationBanner({ validation }) {
  if (!validation) return null;

  const { is_valid, positions_checked, positions_matched, discrepancies } = validation;

  const hasQuantityIssues = discrepancies?.some(
    (d) => d.type === 'missing_position' || d.type === 'quantity_mismatch'
  );
  const hasCostBasisOnly = !hasQuantityIssues && discrepancies?.length > 0;

  let bgClass, textClass, message;

  if (is_valid && !hasCostBasisOnly) {
    bgClass = 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800';
    textClass = 'text-emerald-700 dark:text-emerald-400';
    message = `${positions_matched}/${positions_checked} positions match your current holdings.`;
  } else if (is_valid && hasCostBasisOnly) {
    bgClass = 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800';
    textClass = 'text-amber-700 dark:text-amber-400';
    message = `${positions_matched}/${positions_checked} positions match. Cost basis differs slightly for ${discrepancies.length} position(s).`;
  } else {
    bgClass = 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800';
    textClass = 'text-red-700 dark:text-red-400';
    message = `${positions_matched}/${positions_checked} positions match. You may need additional historical files.`;
  }

  return (
    <div className={`p-4 rounded-xl border ${bgClass}`}>
      <p className={`text-sm font-medium ${textClass}`}>{message}</p>
    </div>
  );
}

// --- Main Component ---

function formatDateForDisplay(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function BatchUploadModal({
  isOpen,
  onClose,
  accountId,
  brokerType,
  supportedFormats = [],
  onComplete,
}) {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [uploads, setUploads] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [finalizeResult, setFinalizeResult] = useState(null);
  const [error, setError] = useState(null);

  const {
    selectedFile,
    fileInputRef,
    handleFileSelect,
    handleFileDrop,
    handleDragOver,
    handleKeyDown,
    openFilePicker,
    clearFile,
  } = useFileUpload({
    acceptedFormats: supportedFormats,
    onValidationError: setError,
  });

  const formatDisplay = supportedFormats
    .map((f) => f.replace('.', '').toUpperCase())
    .join(', ');

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('broker_type', brokerType);
      formData.append('session_id', sessionId);

      const res = await api(`/broker-data/upload/${accountId}`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        const detail = errData.detail;
        throw new Error(
          typeof detail === 'string'
            ? detail
            : detail?.message || detail?.error || JSON.stringify(detail)
        );
      }

      const result = await res.json();
      const dateRange = result.date_range || {};
      const stats = result.stats || {};
      const transactionsImported = (stats.transactions?.imported || 0)
        + (stats.cash_transactions?.imported || 0)
        + (stats.dividends?.imported || 0);

      setUploads((prev) => [
        ...prev,
        {
          fileName: selectedFile.name,
          startDate: dateRange.start_date,
          endDate: dateRange.end_date,
          transactions: transactionsImported || stats.total_records || 0,
          assets: stats.unique_assets_in_file || 0,
          symbols: stats.symbols_in_file || [],
        },
      ]);
      clearFile();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }, [selectedFile, brokerType, sessionId, accountId, clearFile]);

  const handleFinalize = useCallback(async () => {
    setIsFinalizing(true);
    setError(null);

    try {
      const res = await api(
        `/broker-data/finalize-batch/${accountId}?session_id=${sessionId}`,
        { method: 'POST' }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Finalization failed');
      }

      const result = await res.json();
      setFinalizeResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsFinalizing(false);
    }
  }, [accountId, sessionId]);

  const handleDone = useCallback(() => {
    onComplete?.();
    onClose();
  }, [onComplete, onClose]);

  // Compute combined stats for display
  const combinedStats = useMemo(() => {
    const totalTransactions = uploads.reduce((sum, u) => sum + u.transactions, 0);
    const allSymbols = new Set(uploads.flatMap((u) => u.symbols || []));
    return { totalTransactions, totalAssets: allSymbols.size };
  }, [uploads]);

  if (!isOpen) return null;

  const isFinalized = finalizeResult !== null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />

      {/* Modal */}
      <div
        data-testid="batch-upload-modal"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {isFinalized ? 'Import Complete' : 'Upload Transaction History'}
            </h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
            >
              <XIcon className="size-5 text-gray-500" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            {isFinalized ? (
              /* --- Finalize Results --- */
              <>
                <div className="text-center">
                  <div className="size-14 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
                    <CheckIcon className="size-7 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    Finalized {finalizeResult.sources_finalized} file{finalizeResult.sources_finalized !== 1 ? 's' : ''}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {formatDateForDisplay(finalizeResult.date_range?.start_date)} to{' '}
                    {formatDateForDisplay(finalizeResult.date_range?.end_date)}
                  </p>
                </div>

                <ValidationBanner validation={finalizeResult.validation} />

                <button
                  type="button"
                  onClick={handleDone}
                  className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
                >
                  Done
                </button>
              </>
            ) : (
              /* --- Upload Phase --- */
              <>
                {/* File drop zone */}
                <div>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={`Upload file - click or drag and drop. Supported formats: ${formatDisplay}`}
                    onClick={openFilePicker}
                    onDragOver={handleDragOver}
                    onDrop={(e) => {
                      setError(null);
                      handleFileDrop(e);
                    }}
                    onKeyDown={handleKeyDown}
                    className={[
                      'border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                      selectedFile
                        ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20',
                    ].join(' ')}
                  >
                    {selectedFile ? (
                      <>
                        <CheckIcon className="size-10 text-emerald-500 mx-auto mb-3" />
                        <p className="text-base font-semibold text-gray-900 dark:text-white">
                          {selectedFile.name}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Click to select a different file
                        </p>
                      </>
                    ) : (
                      <>
                        <UploadIcon className="size-10 text-gray-400 mx-auto mb-3" />
                        <p className="text-base font-semibold text-gray-900 dark:text-white">
                          Drop your file here
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          or click to browse
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
                          Supported format: {formatDisplay}
                        </p>
                      </>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={supportedFormats.join(',')}
                    onChange={(e) => {
                      setError(null);
                      handleFileSelect(e);
                    }}
                    className="hidden"
                    aria-hidden="true"
                  />
                </div>

                {/* Upload button */}
                <button
                  type="button"
                  aria-label="Upload & Stage"
                  onClick={handleUpload}
                  disabled={!selectedFile || isUploading}
                  className="w-full px-6 py-3 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                >
                  {isUploading ? 'Uploading...' : 'Upload & Stage'}
                </button>

                {/* Error display */}
                {error && (
                  <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                    <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                  </div>
                )}

                {/* Uploaded files list */}
                {uploads.length > 0 && (
                  <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                      <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                        Staged Files ({uploads.length})
                      </p>
                    </div>
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                      {uploads.map((upload, idx) => (
                        <div
                          key={idx}
                          className="px-4 py-3 grid grid-cols-3 gap-4 items-center text-sm"
                        >
                          <div className="text-gray-900 dark:text-white truncate" title={upload.fileName}>
                            {upload.fileName}
                          </div>
                          <div className="text-center font-semibold text-gray-900 dark:text-white tabular-nums">
                            {upload.transactions}
                          </div>
                          <div className="text-right text-gray-500 dark:text-gray-400 text-xs">
                            {formatDateForDisplay(upload.startDate)} - {formatDateForDisplay(upload.endDate)}
                          </div>
                        </div>
                      ))}
                    </div>
                    {/* Combined stats */}
                    <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>{combinedStats.totalTransactions} total transactions</span>
                      <span>{combinedStats.totalAssets} unique assets</span>
                    </div>
                  </div>
                )}

                {/* Coverage timeline */}
                {uploads.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Coverage
                    </h4>
                    <CoverageTimeline
                      files={uploads.map((u) => ({
                        fileName: u.fileName,
                        startDate: u.startDate,
                        endDate: u.endDate,
                        transactions: u.transactions,
                      }))}
                    />
                  </div>
                )}

                {/* Finalize button */}
                <button
                  type="button"
                  aria-label="Finalize Import"
                  onClick={handleFinalize}
                  disabled={uploads.length === 0 || isFinalizing}
                  className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                >
                  {isFinalizing ? 'Finalizing...' : 'Finalize Import'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
