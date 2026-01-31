import { useState } from 'react';

import { cn } from '../../../lib/index.js';
import { useFileUpload } from '../hooks/useFileUpload.js';
import {
  ApiIcon,
  ArrowLeftIcon,
  BookIcon,
  CheckIcon,
  PlayIcon,
  SparklesIcon,
  UploadIcon,
  XIcon,
} from '../icons.jsx';

function getTestButtonLabel(status) {
  switch (status) {
    case 'testing':
      return 'Testing Connection...';
    case 'success':
      return 'Test Again';
    case 'failed':
      return 'Try Again';
    default:
      return 'Test Connection';
  }
}

export function DataConnectionStep({ broker, onComplete, onSkip, onBack, onShowGuide, onTestCredentials, onError }) {
  const [connectionMethod, setConnectionMethod] = useState(broker.hasApi ? 'api' : 'file');
  const [testStatus, setTestStatus] = useState('idle');
  const [testError, setTestError] = useState(null);
  const [credentials, setCredentials] = useState({});
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
    acceptedFormats: broker.supportedFormats,
    onValidationError: (message) => {
      setFileError(message);
      onError?.(message);
    },
  });

  const handleCredentialChange = (key, value) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
    // Reset test status when credentials change
    if (testStatus !== 'idle') {
      setTestStatus('idle');
      setTestError(null);
    }
  };

  const handleTest = async () => {
    setTestStatus('testing');
    setTestError(null);

    try {
      await onTestCredentials(credentials);
      setTestStatus('success');
    } catch (error) {
      setTestStatus('failed');
      setTestError(error.message);
    }
  };

  const handleFileInputChange = (e) => {
    setFileError(null);
    handleFileSelect(e);
  };

  const handleFileDropWithClear = (e) => {
    setFileError(null);
    handleFileDrop(e);
  };

  const formatDisplay = broker.supportedFormats
    .map((f) => f.replace('.', '').toUpperCase())
    .join(', ');

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Import your data
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          Connect your {broker.name} account to import transactions.
        </p>
      </div>

      {/* Tab switcher */}
      {broker.hasApi && (
        <div className="flex gap-2 p-1.5 mb-8 bg-gray-100 dark:bg-gray-800 rounded-xl">
          <button
            type="button"
            onClick={() => setConnectionMethod('api')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer',
              connectionMethod === 'api'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            <ApiIcon className="size-5" />
            Connect via API
          </button>
          <button
            type="button"
            onClick={() => setConnectionMethod('file')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer',
              connectionMethod === 'file'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            <UploadIcon className="size-5" />
            Upload File
          </button>
        </div>
      )}

      {/* Setup Guide Card */}
      <div className="mb-6 p-5 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border-2 border-blue-200 dark:border-blue-800">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/50">
            <BookIcon className="size-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {connectionMethod === 'api' ? 'API Setup Guide' : 'Export Guide'}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {connectionMethod === 'api'
                ? `Step-by-step instructions for creating API credentials in ${broker.name}.`
                : `How to export your transaction history from ${broker.name}.`
              }
            </p>
            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={() => onShowGuide?.(connectionMethod)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
              >
                <BookIcon className="size-4" />
                View Full Guide
              </button>
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors cursor-pointer"
              >
                <PlayIcon className="size-4" />
                Watch Video
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* API Connection */}
      {connectionMethod === 'api' && broker.hasApi && (
        <div className="space-y-5">
          {broker.fields?.api?.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                {field.label}
              </label>
              <input
                type={field.type}
                placeholder={field.placeholder}
                value={credentials[field.key] || ''}
                onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                className={cn(
                  'w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700',
                  'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                  'placeholder:text-gray-400'
                )}
              />
            </div>
          ))}

          {/* Security note */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
            <SparklesIcon className="size-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-300">
              Your credentials are encrypted and stored securely. We only request read-only access.
            </p>
          </div>

          {/* Test result - success */}
          {testStatus === 'success' && (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border-2 border-emerald-200 dark:border-emerald-800">
              <div className="p-2 rounded-full bg-emerald-500 text-white">
                <CheckIcon className="size-5" />
              </div>
              <div>
                <p className="font-semibold text-emerald-700 dark:text-emerald-400">Connection successful!</p>
                <p className="text-sm text-emerald-600 dark:text-emerald-500">Ready to import your data.</p>
              </div>
            </div>
          )}

          {/* Test result - error */}
          {testStatus === 'failed' && testError && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border-2 border-red-200 dark:border-red-800">
              <div className="p-2 rounded-full bg-red-500 text-white flex-shrink-0">
                <XIcon className="size-5" />
              </div>
              <div>
                <p className="font-semibold text-red-700 dark:text-red-400">Connection failed</p>
                <p className="text-sm text-red-600 dark:text-red-500">{testError}</p>
              </div>
            </div>
          )}

          {/* Test button */}
          <button
            type="button"
            onClick={handleTest}
            disabled={testStatus === 'testing'}
            className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            {getTestButtonLabel(testStatus)}
          </button>
        </div>
      )}

      {/* File Upload */}
      {connectionMethod === 'file' && (
        <div className="space-y-5">
          <div
            role="button"
            tabIndex={0}
            aria-label={`Upload file - click or drag and drop. Supported formats: ${formatDisplay}`}
            onClick={openFilePicker}
            onDragOver={handleDragOver}
            onDrop={handleFileDropWithClear}
            onKeyDown={handleKeyDown}
            className={cn(
              'border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
              selectedFile
                ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/20'
                : fileError
                  ? 'border-red-300 dark:border-red-700 bg-red-50/50 dark:bg-red-950/20'
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
                <UploadIcon className={cn(
                  'size-12 mx-auto mb-4',
                  fileError ? 'text-red-400' : 'text-gray-400'
                )} />
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  Drop your file here
                </p>
                <p className="text-gray-500 dark:text-gray-400 mt-2">
                  or click to browse
                </p>
                <p className={cn(
                  'text-sm mt-4',
                  fileError ? 'text-red-500 dark:text-red-400' : 'text-gray-400 dark:text-gray-500'
                )}>
                  {fileError || `Supported format: ${formatDisplay}`}
                </p>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={broker.supportedFormats.join(',')}
            onChange={handleFileInputChange}
            className="hidden"
            aria-hidden="true"
          />

          <button
            type="button"
            onClick={() => selectedFile && onComplete({ file: selectedFile })}
            disabled={!selectedFile}
            className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            Upload & Import
          </button>
        </div>
      )}

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
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={onSkip}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 font-medium cursor-pointer"
          >
            Skip for now
          </button>
          {connectionMethod === 'api' && testStatus === 'success' && (
            <button
              type="button"
              onClick={() => onComplete({ credentials })}
              className="px-6 py-3 rounded-xl text-base font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors cursor-pointer"
            >
              Import Data
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
