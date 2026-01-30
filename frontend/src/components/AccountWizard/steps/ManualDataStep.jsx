import { useRef, useState } from 'react';

import { cn } from '../../../lib/index.js';
import {
  ArrowLeftIcon,
  CheckIcon,
  DownloadIcon,
  SparklesIcon,
  TableIcon,
  UploadIcon,
} from '../icons.jsx';

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
