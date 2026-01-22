import React, { useState, useEffect } from 'react';
import { cn, api } from '../lib';

const SVG_PROPS = { fill: 'none', viewBox: '0 0 24 24', strokeWidth: 1.5, stroke: 'currentColor' };

function XMarkIcon({ className }) {
  return (
    <svg className={className} {...SVG_PROPS}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function SettingsIcon({ className }) {
  return (
    <svg className={className} {...SVG_PROPS}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

function CheckCircleIcon({ className }) {
  return (
    <svg className={className} {...SVG_PROPS}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function ModalWrapper({ onClose, children }) {
  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {children}
      </div>
    </>
  );
}

function ModalHeader({ title, subtitle, onClose }) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-[var(--border-primary)]">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
        {subtitle && <p className="text-sm text-[var(--text-secondary)]">{subtitle}</p>}
      </div>
      <button
        onClick={onClose}
        className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
      >
        <XMarkIcon className="size-5 text-[var(--text-secondary)]" />
      </button>
    </div>
  );
}

function StepIndicator({ currentStep }) {
  const isComplete = currentStep > 1;

  return (
    <div className="px-4 pt-4">
      <div className="flex items-center gap-2 text-xs">
        <Step number={1} label="Test" isActive={currentStep === 1} isComplete={isComplete} />
        <div className={cn('w-6 h-px', isComplete ? 'bg-emerald-400' : 'bg-[var(--border-primary)]')} />
        <Step number={2} label="Save" isActive={currentStep === 2} isComplete={false} />
      </div>
    </div>
  );
}

function Step({ number, label, isActive, isComplete }) {
  const containerClass = isComplete
    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
    : isActive
      ? 'bg-accent/10 text-accent font-medium'
      : 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]';

  const badgeClass = isComplete
    ? 'bg-emerald-500 text-white'
    : isActive
      ? 'bg-accent text-white'
      : 'bg-[var(--border-primary)] text-[var(--text-tertiary)]';

  return (
    <div className={cn('flex items-center gap-1.5 px-2 py-1 rounded-full', containerClass)}>
      <span className={cn('size-4 rounded-full flex items-center justify-center text-[10px] font-bold', badgeClass)}>
        {isComplete ? '\u2713' : number}
      </span>
      <span>{label}</span>
    </div>
  );
}

const INPUT_CLASS = cn(
  'w-full px-2.5 py-2 rounded-md text-sm',
  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
  'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
  'focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent'
);

function FormField({ label, type = 'text', value, onChange, placeholder }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
        {label}
      </label>
      <input
        type={type}
        required
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={INPUT_CLASS}
      />
    </div>
  );
}

export function ApiCredentialsModal({ isOpen, onClose, account, onCredentialsSaved, hasCredentials, onGoToSettings }) {
  const isIbkr = account?.broker_type === 'ibkr';
  const [formData, setFormData] = useState(
    isIbkr
      ? { flex_token: '', flex_query_id: '' }
      : { api_key: '', api_secret: '' }
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState(null);
  const [testResult, setTestResult] = useState(null);

  // Reset form when modal opens/closes or account changes
  useEffect(() => {
    if (isOpen) {
      setFormData(
        account?.broker_type === 'ibkr'
          ? { flex_token: '', flex_query_id: '' }
          : { api_key: '', api_secret: '' }
      );
      setError(null);
      setTestResult(null);
    }
  }, [isOpen, account?.broker_type]);

  if (!isOpen || !account) return null;

  // If credentials already exist, show redirect to settings
  if (hasCredentials) {
    return (
      <ModalWrapper onClose={onClose}>
        <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-sm w-full">
          <ModalHeader title="API Connected" onClose={onClose} />
          <div className="p-4 space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
              <CheckCircleIcon className="size-8 text-emerald-500" />
              <div>
                <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                  Your API is already connected
                </p>
                <p className="text-xs text-emerald-600/80 dark:text-emerald-400/80">
                  {account.institution} credentials are configured
                </p>
              </div>
            </div>

            <p className="text-sm text-[var(--text-secondary)]">
              To update or manage your API credentials, go to the Settings tab.
            </p>

            <div className="flex justify-end gap-2 pt-2 border-t border-[var(--border-primary)]">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onGoToSettings?.();
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
              >
                <SettingsIcon className="size-3.5" />
                Go to Settings
              </button>
            </div>
          </div>
        </div>
      </ModalWrapper>
    );
  }

  const handleTest = async () => {
    setIsTesting(true);
    setError(null);
    setTestResult(null);

    try {
      // First save the credentials
      const saveRes = await api(`/brokers/${account.broker_type}/credentials/${account.id}`, {
        method: 'PUT',
        body: JSON.stringify(formData),
      });

      if (!saveRes.ok) {
        const data = await saveRes.json();
        throw new Error(data.detail || 'Failed to save credentials');
      }

      // Then test them
      const testRes = await api(`/brokers/${account.broker_type}/test-credentials/${account.id}`, {
        method: 'POST',
      });

      const testData = await testRes.json();

      if (!testRes.ok) {
        throw new Error(testData.detail || 'Credentials test failed');
      }

      setTestResult(testData);
    } catch (err) {
      console.error('Error testing credentials:', err);
      setError(err.message);
    } finally {
      setIsTesting(false);
    }
  };

  const handleDone = (e) => {
    e.stopPropagation();
    onClose();
    onCredentialsSaved?.();
  };

  const handleSaveAndImport = async (e) => {
    e.stopPropagation();
    setIsImporting(true);
    setError(null);

    try {
      // Trigger import using the saved credentials
      const res = await api(`/brokers/${account.broker_type}/import/${account.id}`, {
        method: 'POST',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Import failed');
      }

      const result = await res.json();
      alert(`Import completed: ${result.stats?.transactions_imported || 0} transactions imported`);
      onClose();
      onCredentialsSaved?.();
    } catch (err) {
      console.error('Error importing data:', err);
      setError(err.message);
    } finally {
      setIsImporting(false);
    }
  };

  const currentStep = testResult ? 2 : 1;

  const updateField = (field) => (e) => setFormData({ ...formData, [field]: e.target.value });

  return (
    <ModalWrapper onClose={onClose}>
      <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full">
        <ModalHeader title="Connect API" subtitle={account.institution} onClose={onClose} />

        <StepIndicator currentStep={currentStep} />

        <form onSubmit={(e) => e.preventDefault()} className="p-4 space-y-3">
          {isIbkr ? (
            <>
              <FormField
                label="Flex Token"
                type="password"
                value={formData.flex_token}
                onChange={updateField('flex_token')}
                placeholder="Enter your Flex token"
              />
              <FormField
                label="Flex Query ID"
                value={formData.flex_query_id}
                onChange={updateField('flex_query_id')}
                placeholder="Enter your Flex Query ID"
              />
            </>
          ) : (
            <>
              <FormField
                label="API Key"
                value={formData.api_key}
                onChange={updateField('api_key')}
                placeholder="Enter your API key"
              />
              <FormField
                label="API Secret"
                type="password"
                value={formData.api_secret}
                onChange={updateField('api_secret')}
                placeholder="Enter your API secret"
              />
            </>
          )}

          {testResult && (
            <div className="p-2.5 rounded-md bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
              <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                {'\u2713'} {testResult.message}
              </p>
              {testResult.balances && (
                <p className="text-xs text-emerald-600/80 dark:text-emerald-400/80 mt-0.5">
                  Found {testResult.assets_count} assets
                </p>
              )}
            </div>
          )}

          {error && (
            <div className="p-2.5 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
              <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-[var(--border-primary)]">
            {!testResult ? (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleTest}
                  disabled={isTesting}
                  className="px-3 py-1.5 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isTesting ? 'Testing...' : 'Test Connection'}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setTestResult(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                >
                  {'\u2190'} Re-enter
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleDone}
                    disabled={isImporting}
                    className="px-3 py-1.5 rounded-md text-xs font-medium border border-accent text-accent hover:bg-accent/10 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Save Only
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveAndImport}
                    disabled={isImporting}
                    className="px-3 py-1.5 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {isImporting ? 'Importing...' : 'Save & Import'}
                  </button>
                </div>
              </>
            )}
          </div>
        </form>
      </div>
    </ModalWrapper>
  );
}
