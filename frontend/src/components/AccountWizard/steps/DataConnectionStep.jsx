import { useState, useRef } from 'react';
import { cn } from '../../../lib';

function ArrowLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
    </svg>
  );
}

function ApiIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
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

function BookIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
    </svg>
  );
}

function PlayIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" />
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

export function DataConnectionStep({ broker, onComplete, onSkip, onBack, onShowGuide }) {
  const [connectionMethod, setConnectionMethod] = useState(broker.hasApi ? 'api' : 'file');
  const [testStatus, setTestStatus] = useState('idle'); // idle, testing, success, error
  const [credentials, setCredentials] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleCredentialChange = (key, value) => {
    setCredentials(prev => ({ ...prev, [key]: value }));
  };

  const handleTest = () => {
    setTestStatus('testing');
    // Simulate API test - in real implementation, this calls the API
    setTimeout(() => {
      setTestStatus('success');
    }, 1500);
  };

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

  const formatDisplay = broker.supportedFormats.map(f => f.replace('.', '').toUpperCase()).join(', ');

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

          {/* Test result */}
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

          {/* Test button */}
          <button
            type="button"
            onClick={handleTest}
            disabled={testStatus === 'testing'}
            className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            {testStatus === 'testing' ? 'Testing Connection...' : testStatus === 'success' ? 'Test Again' : 'Test Connection'}
          </button>
        </div>
      )}

      {/* File Upload */}
      {connectionMethod === 'file' && (
        <div className="space-y-5">
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            className={cn(
              'border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all',
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
                  Supported format: {formatDisplay}
                </p>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={broker.supportedFormats.join(',')}
            onChange={handleFileSelect}
            className="hidden"
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
