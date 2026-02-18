import { useState } from 'react';

import { cn } from '../../../lib/index.js';
import { useFileUpload } from '../hooks/useFileUpload.js';
import {
  ArrowLeftIcon,
  CheckIcon,
  DownloadIcon,
  SparklesIcon,
  TableIcon,
  UploadIcon,
} from '../icons.jsx';

const REQUIRED_COLUMNS = ['date', 'type', 'symbol', 'currency'];
const OPTIONAL_COLUMNS = ['quantity', 'price', 'amount', 'fees', 'notes'];
const ACCEPTED_FORMATS = ['.csv', '.xlsx'];

const TEMPLATE_DOWNLOADS = [
  {
    href: '/templates/manual_import_example.csv',
    filename: 'manual_import_example.csv',
    label: 'Download CSV Template',
    className: 'bg-accent text-white hover:bg-accent-hover',
  },
  {
    href: '/templates/manual_import_example.xlsx',
    filename: 'manual_import_example.xlsx',
    label: 'Download Excel Template',
    className:
      'bg-[var(--bg-primary)] text-accent dark:text-accent-400 border-2 border-accent-200 dark:border-accent-800 hover:bg-accent-50 dark:hover:bg-accent-900/30',
  },
];

function getDropZoneStyle(selectedFile, fileError) {
  if (selectedFile) {
    return 'border-positive dark:border-positive-dark bg-positive-light/50 dark:bg-positive-bg-dark/20';
  }
  if (fileError) {
    return 'border-negative dark:border-negative-dark bg-negative-bg/50 dark:bg-negative-bg-dark/20';
  }
  return 'border-[var(--border-primary)] hover:border-accent hover:bg-accent-50/50 dark:hover:bg-accent-900/20';
}

export function ManualDataStep({ onComplete, onSkip, onBack, onError }) {
  const [fileError, setFileError] = useState(null);

  const {
    selectedFile,
    fileInputRef,
    handleFileSelect,
    handleFileDrop,
    handleDragOver,
    handleKeyDown,
    openFilePicker,
  } = useFileUpload({
    acceptedFormats: ACCEPTED_FORMATS,
    onValidationError: (message) => {
      setFileError(message);
      onError?.(message);
    },
  });

  const handleFileInputChange = (e) => {
    setFileError(null);
    handleFileSelect(e);
  };

  const handleFileDropWithClear = (e) => {
    setFileError(null);
    handleFileDrop(e);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
          Import your transactions
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg">
          Upload a CSV or Excel file using our transaction template.
        </p>
      </div>

      {/* Template download section */}
      <div className="mb-8 p-6 rounded-2xl bg-accent-50 dark:bg-accent-900/20 border-2 border-accent-200 dark:border-accent-800">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-accent-100 dark:bg-accent-900/50">
            <TableIcon className="size-6 text-accent dark:text-accent-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-[var(--text-primary)]">
              Transaction Template
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Download our template and fill in your transactions. The file must include the required columns.
            </p>
            <div className="flex flex-wrap gap-3 mt-4">
              {TEMPLATE_DOWNLOADS.map((tmpl) => (
                <a
                  key={tmpl.href}
                  href={tmpl.href}
                  download={tmpl.filename}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors cursor-pointer',
                    tmpl.className,
                  )}
                >
                  <DownloadIcon className="size-4" />
                  {tmpl.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Required columns info */}
      <div className="mb-8 p-5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)]">
        <h4 className="font-semibold text-[var(--text-primary)] mb-3">Required Columns</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          {REQUIRED_COLUMNS.map((col) => (
            <div key={col} className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-negative" aria-hidden="true" />
              <span className="text-[var(--text-secondary)]">{col}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-[var(--border-primary)]">
          <h5 className="font-medium text-[var(--text-secondary)] mb-2">Optional Columns</h5>
          <div className="flex flex-wrap gap-2 text-sm text-[var(--text-tertiary)]">
            {OPTIONAL_COLUMNS.map((col) => (
              <span key={col} className="px-2 py-1 rounded bg-[var(--bg-tertiary)]">
                {col}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Upload zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload file - click or drag and drop. Supported formats: CSV, XLSX"
        onClick={openFilePicker}
        onDragOver={handleDragOver}
        onDrop={handleFileDropWithClear}
        onKeyDown={handleKeyDown}
        className={cn(
          'border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all mb-6',
          'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
          getDropZoneStyle(selectedFile, fileError),
        )}
      >
        {selectedFile ? (
          <>
            <CheckIcon className="size-12 text-positive mx-auto mb-4" />
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              {selectedFile.name}
            </p>
            <p className="text-[var(--text-tertiary)] mt-2">
              Click to select a different file
            </p>
          </>
        ) : (
          <>
            <UploadIcon className={cn(
              'size-12 mx-auto mb-4',
              fileError ? 'text-negative' : 'text-[var(--text-tertiary)]'
            )} />
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              Drop your file here
            </p>
            <p className="text-[var(--text-tertiary)] mt-2">
              or click to browse
            </p>
            <p className={cn(
              'text-sm mt-4',
              fileError ? 'text-negative dark:text-negative-dark' : 'text-[var(--text-tertiary)]'
            )}>
              {fileError || 'Supported formats: CSV, XLSX'}
            </p>
          </>
        )}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFileInputChange}
        className="hidden"
        aria-hidden="true"
      />

      {/* Note about responsibility */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 mb-6">
        <SparklesIcon className="size-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-amber-800 dark:text-amber-300">
          <strong>Note:</strong> You are responsible for ensuring your data matches our template format. We cannot automatically parse data from brokers when using manual import.
        </p>
      </div>

      <button
        type="button"
        onClick={() => selectedFile && onComplete({ file: selectedFile })}
        disabled={!selectedFile}
        className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
      >
        Upload & Import
      </button>

      {/* Footer */}
      <div className="flex items-center justify-between mt-10">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back</span>
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] font-medium cursor-pointer"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
