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

export function DataConnectionStep({ broker, onComplete, onSkip, onBack, onShowGuide, onTestCredentials, onError, sectionValidation, isImporting }) {
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
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
          Import your data
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg">
          Connect your {broker.name} account to import transactions.
        </p>
      </div>

      {/* Tab switcher */}
      {broker.hasApi && (
        <div className="flex gap-2 p-1.5 mb-8 bg-[var(--bg-tertiary)] rounded-xl">
          <button
            type="button"
            onClick={() => setConnectionMethod('api')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold transition-all cursor-pointer',
              connectionMethod === 'api'
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
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
                ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            <UploadIcon className="size-5" />
            Upload File
          </button>
        </div>
      )}

      {/* Setup Guide Card */}
      <div className="mb-6 p-5 rounded-2xl bg-accent-50 dark:bg-accent-900/20 border-2 border-accent-200 dark:border-accent-800">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-accent-100 dark:bg-accent-900/50">
            <BookIcon className="size-6 text-accent dark:text-accent-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-[var(--text-primary)]">
              {connectionMethod === 'api' ? 'API Setup Guide' : 'Export Guide'}
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              {connectionMethod === 'api'
                ? `Step-by-step instructions for creating API credentials in ${broker.name}.`
                : `How to export your transaction history from ${broker.name}.`
              }
            </p>
            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={() => onShowGuide?.(connectionMethod)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
              >
                <BookIcon className="size-4" />
                View Full Guide
              </button>
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-accent dark:text-accent-400 hover:bg-accent-100 dark:hover:bg-accent-900/30 transition-colors cursor-pointer"
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
              <label className="block text-sm font-semibold text-[var(--text-secondary)] mb-2">
                {field.label}
              </label>
              <input
                type={field.type}
                placeholder={field.placeholder}
                value={credentials[field.key] || ''}
                onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                className={cn(
                  'w-full px-4 py-3 rounded-xl border-2 border-[var(--border-primary)]',
                  'bg-[var(--bg-primary)] text-[var(--text-primary)]',
                  'focus:ring-2 focus:ring-accent focus:border-accent',
                  'placeholder:text-[var(--text-tertiary)]'
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
            <div className="flex items-center gap-3 p-4 rounded-xl bg-positive-light dark:bg-positive-bg-dark/30 border-2 border-positive-light dark:border-positive-dark/30">
              <div className="p-2 rounded-full bg-positive text-white">
                <CheckIcon className="size-5" />
              </div>
              <div>
                <p className="font-semibold text-positive dark:text-positive-dark">Connection successful!</p>
                <p className="text-sm text-positive dark:text-positive-dark/80">Ready to import your data.</p>
              </div>
            </div>
          )}

          {/* Test result - error */}
          {testStatus === 'failed' && testError && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-negative-bg dark:bg-negative-bg-dark/30 border-2 border-negative-light dark:border-negative-dark/30">
              <div className="p-2 rounded-full bg-negative text-white flex-shrink-0">
                <XIcon className="size-5" />
              </div>
              <div>
                <p className="font-semibold text-negative dark:text-negative-dark">Connection failed</p>
                <p className="text-sm text-negative dark:text-negative-dark/80">{testError}</p>
              </div>
            </div>
          )}

          {/* Missing sections checklist */}
          {sectionValidation?.missing?.length > 0 && (
            <div className="p-5 rounded-xl bg-amber-50 dark:bg-amber-950/20 border-2 border-amber-300 dark:border-amber-700">
              <h4 className="font-semibold text-amber-800 dark:text-amber-300 mb-3">
                Your Flex Query is missing required sections
              </h4>
              <p className="text-sm text-amber-700 dark:text-amber-400 mb-4">
                Please update your Flex Query in IBKR to include these sections, then try importing again.
              </p>
              <div className="space-y-2">
                {sectionValidation.required.map((section) => {
                  const isMissing = sectionValidation.missing.includes(section);
                  return (
                    <div key={section} className="flex items-center gap-2">
                      {isMissing ? (
                        <XIcon className="size-5 text-red-500" />
                      ) : (
                        <CheckIcon className="size-5 text-emerald-500" />
                      )}
                      <span className={cn(
                        'text-sm',
                        isMissing
                          ? 'font-semibold text-negative dark:text-negative-dark'
                          : 'text-[var(--text-secondary)]'
                      )}>
                        {section}
                        {section === 'Account Information' && (
                          <span className="text-xs ml-1 text-gray-500">
                            (only &quot;Date Opened&quot; field needed)
                          </span>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Test button */}
          <button
            type="button"
            onClick={handleTest}
            disabled={testStatus === 'testing'}
            className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
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
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
              selectedFile
                ? 'border-positive dark:border-positive-dark bg-positive-light/50 dark:bg-positive-bg-dark/20'
                : fileError
                  ? 'border-negative dark:border-negative-dark bg-negative-bg/50 dark:bg-negative-bg-dark/20'
                  : 'border-[var(--border-primary)] hover:border-accent hover:bg-accent-50/50 dark:hover:bg-accent-900/20'
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
            className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
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
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back</span>
        </button>
        <div className="flex items-center gap-4">
          {onSkip && (
            <button
              type="button"
              onClick={onSkip}
              className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] font-medium cursor-pointer"
            >
              Skip for now
            </button>
          )}
          {connectionMethod === 'api' && testStatus === 'success' && (
            <button
              type="button"
              onClick={() => onComplete({ credentials })}
              disabled={isImporting}
              className="px-6 py-3 rounded-xl text-base font-semibold bg-positive text-white hover:bg-positive-dark transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isImporting ? 'Importing...' : 'Import Data'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
