import { useState, useRef } from 'react';
import { cn } from '../../../lib';

function ArrowLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
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

function DownloadIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}

function TableIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 1.5v-1.5m0 0c0-.621.504-1.125 1.125-1.125m0 0h7.5" />
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

function SparklesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
    </svg>
  );
}

const REQUIRED_COLUMNS = ['date', 'type', 'symbol', 'quantity', 'price', 'currency'];
const OPTIONAL_COLUMNS = ['fees', 'notes', 'broker', 'account_id'];

export function ManualDataStep({ onComplete, onSkip, onBack }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Import your transactions
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          Upload a CSV or Excel file using our transaction template.
        </p>
      </div>

      {/* Template download section */}
      <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 border-2 border-indigo-200 dark:border-indigo-800">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-indigo-100 dark:bg-indigo-900/50">
            <TableIcon className="size-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Transaction Template
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Download our template and fill in your transactions. The file must include the required columns.
            </p>
            <div className="flex flex-wrap gap-3 mt-4">
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                <DownloadIcon className="size-4" />
                Download CSV Template
              </button>
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-white dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-2 border-indigo-200 dark:border-indigo-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition-colors cursor-pointer"
              >
                <DownloadIcon className="size-4" />
                Download Excel Template
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Required columns info */}
      <div className="mb-8 p-5 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
        <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Required Columns</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          {REQUIRED_COLUMNS.map((col) => (
            <div key={col} className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-red-500" />
              <span className="text-gray-700 dark:text-gray-300">{col}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Optional Columns</h5>
          <div className="flex flex-wrap gap-2 text-sm text-gray-500 dark:text-gray-400">
            {OPTIONAL_COLUMNS.map((col) => (
              <span key={col} className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800">
                {col}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Upload zone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        className={cn(
          'border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all mb-6',
          selectedFile
            ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20'
        )}
      >
        {selectedFile ? (
          <>
            <CheckIcon className="size-12 text-emerald-500 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {selectedFile.name}
            </p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">
              Click to select a different file
            </p>
          </>
        ) : (
          <>
            <UploadIcon className="size-12 text-gray-400 mx-auto mb-4" />
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              Drop your file here
            </p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">
              or click to browse
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-4">
              Supported formats: CSV, XLSX
            </p>
          </>
        )}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFileSelect}
        className="hidden"
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
        className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
      >
        Upload & Import
      </button>

      {/* Footer */}
      <div className="flex items-center justify-between mt-10">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back</span>
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 font-medium cursor-pointer"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
