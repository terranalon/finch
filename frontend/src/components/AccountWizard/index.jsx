import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../../lib/index.js';
import { XIcon } from './icons.jsx';
import { WizardStepIndicator } from './WizardStepIndicator.jsx';
import { WizardNotification } from './WizardNotification.jsx';
import { SetupGuidePanel } from './SetupGuidePanel.jsx';
import {
  AccountTypeStep,
  BrokerSelectionStep,
  AccountDetailsStep,
  DataConnectionStep,
  ManualDataStep,
  ImportingStep,
  ImportResultsStep,
  FileUploadResultStep,
  SuccessStep,
  LinkExistingStep,
} from './steps/index.js';
import { getBrokerConfig, CATEGORY_IDS } from './constants/index.js';

/**
 * Format a date string for display.
 * @param {string|null} dateStr - ISO date string or null
 * @param {string} fallback - Fallback value if date is invalid
 * @returns {string} Formatted date string
 */
function formatDateForDisplay(dateStr, fallback = 'N/A') {
  if (!dateStr) return fallback;
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function AccountWizard({ isOpen, onClose, portfolioId, linkableAccounts = [], existingAccountNames = [] }) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [maxReachedStep, setMaxReachedStep] = useState(1);
  const [skippedSteps, setSkippedSteps] = useState([]);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);
  const [accountDetails, setAccountDetails] = useState(null);
  const [createdAccountId, setCreatedAccountId] = useState(null);
  const accountIdRef = useRef(null);
  const createPromiseRef = useRef(null);
  const [skippedData, setSkippedData] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [showImportResults, setShowImportResults] = useState(false);
  const [importResults, setImportResults] = useState(null);
  const [showGuide, setShowGuide] = useState(null);
  // File upload loop state
  const [fileUploads, setFileUploads] = useState([]);
  const [showFileUploadResult, setShowFileUploadResult] = useState(false);
  const [lastFileUpload, setLastFileUpload] = useState(null);
  const [hasSnapshotData, setHasSnapshotData] = useState(false);

  // Notification state (replaces alert())
  const [notification, setNotification] = useState({ message: null, type: 'error' });

  const showNotification = useCallback((message, type = 'error') => {
    setNotification({ message, type });
  }, []);

  const dismissNotification = useCallback(() => {
    setNotification({ message: null, type: 'error' });
  }, []);

  const createAccount = useCallback(async () => {
    if (accountIdRef.current) return accountIdRef.current;
    if (createPromiseRef.current) return createPromiseRef.current;

    const promise = (async () => {
      try {
        const response = await api('/accounts', {
          method: 'POST',
          body: JSON.stringify({
            name: accountDetails.name,
            description: accountDetails.description || null,
            account_type: accountDetails.accountType,
            currency: accountDetails.currency,
            institution: broker?.name || 'Manual',
            broker_type: broker?.type || null,
            portfolio_ids: portfolioId ? [portfolioId] : [],
          }),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to create account');
        }

        const account = await response.json();
        accountIdRef.current = account.id;
        setCreatedAccountId(account.id);
        return account.id;
      } finally {
        createPromiseRef.current = null;
      }
    })();

    createPromiseRef.current = promise;
    return promise;
  }, [accountDetails, broker, portfolioId]);

  const reset = () => {
    setCurrentStep(1);
    setMaxReachedStep(1);
    setSkippedSteps([]);
    setCategory(null);
    setBroker(null);
    setAccountDetails(null);
    setCreatedAccountId(null);
    accountIdRef.current = null;
    createPromiseRef.current = null;
    setSkippedData(false);
    setIsImporting(false);
    setShowImportResults(false);
    setImportResults(null);
    setShowGuide(null);
    setFileUploads([]);
    setShowFileUploadResult(false);
    setLastFileUpload(null);
    setHasSnapshotData(false);
    setNotification({ message: null, type: 'error' });
  };

  const handleClose = () => {
    reset();
    onClose?.();
  };

  const goToStep = (step) => {
    if (accountIdRef.current) return; // Account persisted -- no going back
    setCurrentStep(step);
    if (step <= 3) setAccountDetails(null);
    if (step <= 2) setBroker(null);
    if (step <= 1) setCategory(null);
  };

  // Step 1: Category selection
  const handleCategorySelect = (cat) => {
    setCategory(cat);
    if (cat.id === CATEGORY_IDS.MANUAL) {
      // Manual flow skips broker selection (step 2)
      setBroker(null);
      setSkippedSteps([2]);
      setCurrentStep(3);
      setMaxReachedStep(Math.max(maxReachedStep, 3));
    } else if (cat.id !== CATEGORY_IDS.LINK) {
      setSkippedSteps([]);
      setCurrentStep(2);
      setMaxReachedStep(Math.max(maxReachedStep, 2));
    }
    // 'link' category is handled differently - shows LinkExistingStep
  };

  // Step 2: Broker selection
  const handleBrokerSelect = (b) => {
    setBroker(b);
    setCurrentStep(3);
    setMaxReachedStep(Math.max(maxReachedStep, 3));
  };

  // Step 3: Account details submission -> Store details and advance
  const handleDetailsSubmit = (details) => {
    setAccountDetails(details);
    setCurrentStep(4);
    setMaxReachedStep(Math.max(maxReachedStep, 4));
  };

  // Step 4: Data connection complete -> Create account then import data
  const handleDataComplete = async (data) => {
    setIsImporting(true);

    try {
      const accountId = await createAccount();

      if (data.credentials) {
        // API connection - save credentials using PUT
        const credResponse = await api(`/brokers/${broker.type}/credentials/${accountId}`, {
          method: 'PUT',
          body: JSON.stringify(data.credentials),
        });

        if (!credResponse.ok) {
          const error = await credResponse.json();
          throw new Error(error.detail || 'Failed to save credentials');
        }

        if (broker.supportsSnapshot) {
          // Snapshot-capable broker: import current positions
          const snapshotResponse = await api(`/brokers/${broker.type}/snapshot/${accountId}`, {
            method: 'POST',
          });

          if (!snapshotResponse.ok) {
            const error = await snapshotResponse.json();
            throw new Error(error.detail || 'Failed to import snapshot');
          }

          const results = await snapshotResponse.json();
          setImportResults(transformSnapshotResults(results));
          setHasSnapshotData(true);
        } else {
          // Regular broker: trigger full data import
          const importResponse = await api(`/brokers/${broker.type}/import/${accountId}`, {
            method: 'POST',
          });

          if (!importResponse.ok) {
            const error = await importResponse.json();
            throw new Error(error.detail || 'Failed to import data');
          }

          const results = await importResponse.json();
          setImportResults(transformImportResults(results));
        }

        setSkippedData(false);
        setIsImporting(false);
        setShowImportResults(true);
      } else if (data.file) {
        // File upload - supports progressive upload loop
        const formData = new FormData();
        formData.append('file', data.file);
        formData.append('broker_type', broker?.type || 'manual');

        const uploadResponse = await api(`/broker-data/upload/${accountId}`, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          const error = await uploadResponse.json();
          throw new Error(error.detail || 'Failed to upload file');
        }

        const results = await uploadResponse.json();

        // For file uploads, date_range is at top level, not in stats
        const dateRange = results.date_range || {};
        const stats = results.stats || {};

        // Calculate transactions from Meitav stats structure
        const transactionsImported = (stats.transactions?.imported || 0)
          + (stats.cash_transactions?.imported || 0)
          + (stats.dividends?.imported || 0);

        // Get unique assets count from file (tracked by backend)
        const uniqueAssetsInFile = stats.unique_assets_in_file || 0;
        const symbolsInFile = stats.symbols_in_file || [];

        // Add to file uploads array for progressive loop
        const newUpload = {
          fileName: data.file.name,
          summary: {
            totalTransactions: transactionsImported,
            totalAssets: uniqueAssetsInFile,
            dateRange: {
              start: formatDateForDisplay(dateRange.start_date, null),
              end: formatDateForDisplay(dateRange.end_date, null),
            },
          },
          // Keep raw dates for combined calculation
          dateRange: {
            startDate: dateRange.start_date,
            endDate: dateRange.end_date,
          },
          // Keep symbols for combined unique count
          symbols: symbolsInFile,
        };

        setFileUploads((prev) => [...prev, newUpload]);
        setLastFileUpload(newUpload);
        setSkippedData(false);
        setIsImporting(false);
        setShowFileUploadResult(true);
      }
    } catch (error) {
      setIsImporting(false);
      showNotification(`Import failed: ${error.message}`);
    }
  };

  // Transform backend import response to UI format
  function transformImportResults(backendResults) {
    const stats = backendResults.stats || {};

    // Calculate total transactions from all categories
    const transactionsImported = (stats.transactions?.imported || 0)
      + (stats.cash_transactions?.imported || 0)
      + (stats.dividends?.imported || 0);

    // Calculate total assets created
    const assetsCreated = (stats.transactions?.assets_created || 0)
      + (stats.positions?.assets_created || 0);

    // Get holdings count from reconstruction stats
    const holdingsCount = stats.holdings_reconstruction?.holdings_updated || 0;

    const dateRange = stats.date_range || {};

    return {
      assets: [], // Backend doesn't return asset list in import response
      summary: {
        totalAssets: holdingsCount || assetsCreated,
        totalTransactions: transactionsImported,
        dateRange: {
          start: formatDateForDisplay(dateRange.start_date),
          end: formatDateForDisplay(dateRange.end_date),
        },
      },
      message: backendResults.message,
    };
  }

  function transformSnapshotResults(backendResults) {
    const stats = backendResults.stats || {};
    const positionsImported = stats.positions_imported || 0;
    const holdingsUpdated = stats.holdings_reconstruction?.holdings_updated || 0;
    const totalImported = holdingsUpdated || positionsImported;

    return {
      assets: [],
      emptySnapshot: totalImported === 0,
      summary: {
        totalAssets: totalImported,
        totalTransactions: positionsImported,
        dateRange: {
          start: 'Today',
          end: 'Today',
        },
      },
      message: backendResults.message,
    };
  }

  // Step 4: Test credentials before import (stateless - no account needed)
  const handleTestCredentials = async (credentials) => {
    const testResponse = await api(`/brokers/${broker.type}/test-credentials`, {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    const result = await testResponse.json();
    if (result.status !== 'success') {
      throw new Error(result.message || 'Credential test failed');
    }

    return result;
  };

  // Step 4: Skip data import - create account then advance
  const handleDataSkip = async () => {
    try {
      await createAccount();
      setSkippedData(true);
      setCurrentStep(5);
      setMaxReachedStep(5);
    } catch (error) {
      showNotification(`Failed to create account: ${error.message}`);
    }
  };

  // File upload loop: Upload another file
  const handleUploadAnother = () => {
    setShowFileUploadResult(false);
    setLastFileUpload(null);
    // Stay on step 4 to show file upload UI again
  };

  // File upload loop: Done with all uploads
  const handleFileUploadsDone = () => {
    setShowFileUploadResult(false);
    setCurrentStep(5);
    setMaxReachedStep(5);
  };

  // Step 4b: Continue from import results to success
  const handleImportResultsContinue = () => {
    setShowImportResults(false);
    setCurrentStep(5);
    setMaxReachedStep(5);
  };

  // Link existing account
  const handleLinkAccount = async (account) => {
    try {
      const response = await api(`/portfolios/${portfolioId}/accounts/${account.id}/link`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to link account');
      }

      handleClose();
    } catch (error) {
      showNotification(`Failed to link account: ${error.message}`);
    }
  };

  // Success step actions
  const handleViewAccount = () => {
    handleClose();
    if (createdAccountId) {
      navigate(`/accounts/${createdAccountId}`);
    }
  };

  const handleAddAnother = () => {
    reset();
  };

  if (!isOpen) return null;

  // Compute derived values once
  const isManualFlow = category?.id === CATEGORY_IDS.MANUAL;
  const brokerConfig = broker ? getBrokerConfig(broker.type) : null;

  // Determine what to render
  let stepContent;

  if (isImporting) {
    stepContent = <ImportingStep message="Importing your data..." />;
  } else if (showFileUploadResult && lastFileUpload) {
    // Progressive file upload loop
    stepContent = (
      <FileUploadResultStep
        currentUpload={lastFileUpload}
        allUploads={fileUploads}
        brokerName={brokerConfig?.name || broker?.name || 'your broker'}
        onUploadAnother={handleUploadAnother}
        onContinue={handleFileUploadsDone}
      />
    );
  } else if (showImportResults) {
    // API import results (single import)
    stepContent = (
      <ImportResultsStep
        broker={brokerConfig}
        importResults={importResults}
        onContinue={handleImportResultsContinue}
      />
    );
  } else if (currentStep === 1) {
    if (category?.id === CATEGORY_IDS.LINK) {
      stepContent = (
        <LinkExistingStep
          linkableAccounts={linkableAccounts}
          onSelect={handleLinkAccount}
          onBack={() => setCategory(null)}
        />
      );
    } else {
      stepContent = (
        <AccountTypeStep
          onSelect={handleCategorySelect}
          linkableAccounts={linkableAccounts}
        />
      );
    }
  } else if (currentStep === 2) {
    stepContent = (
      <BrokerSelectionStep
        category={category}
        onSelect={handleBrokerSelect}
        onBack={() => goToStep(1)}
      />
    );
  } else if (currentStep === 3) {
    stepContent = (
      <AccountDetailsStep
        broker={brokerConfig}
        category={category}
        existingAccountNames={existingAccountNames}
        onSubmit={handleDetailsSubmit}
        onBack={() => goToStep(isManualFlow ? 1 : 2)}
      />
    );
  } else if (currentStep === 4) {
    if (isManualFlow) {
      stepContent = (
        <ManualDataStep
          onComplete={handleDataComplete}
          onSkip={handleDataSkip}
          onBack={() => goToStep(3)}
        />
      );
    } else {
      stepContent = (
        <DataConnectionStep
          broker={brokerConfig}
          onComplete={handleDataComplete}
          onSkip={handleDataSkip}
          onBack={() => goToStep(3)}
          onShowGuide={(type) => setShowGuide(type)}
          onTestCredentials={handleTestCredentials}
        />
      );
    }
  } else if (currentStep === 5) {
    stepContent = (
      <SuccessStep
        broker={brokerConfig}
        accountDetails={accountDetails}
        skippedData={skippedData}
        hasSnapshotData={hasSnapshotData}
        createdAccountId={createdAccountId}
        onViewAccount={handleViewAccount}
        onAddAnother={handleAddAnother}
        onDone={handleClose}
      />
    );
  }

  const effectiveStep = (showImportResults || showFileUploadResult) ? 4 : currentStep;
  const showStepIndicator = effectiveStep > 1 && category?.id !== CATEGORY_IDS.LINK && !isImporting;

  return (
    <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <button
            onClick={handleClose}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
          >
            <XIcon className="size-5" />
            <span className="font-medium hidden sm:inline">Cancel</span>
          </button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Add Account
          </h1>
          <div className="w-20" />
        </div>
      </header>

      {/* Step indicator */}
      {showStepIndicator && (
        <div className="flex-shrink-0 py-6 px-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
          <WizardStepIndicator
            currentStep={effectiveStep}
            maxReachedStep={maxReachedStep}
            skippedSteps={skippedSteps}
            onStepClick={goToStep}
            locked={!!createdAccountId}
          />
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          {stepContent}
        </div>
      </main>

      {/* Setup Guide Panel */}
      {showGuide && brokerConfig && (
        <SetupGuidePanel
          broker={brokerConfig}
          guideType={showGuide}
          onClose={() => setShowGuide(null)}
        />
      )}

      {/* Notification toast */}
      <WizardNotification
        message={notification.message}
        type={notification.type}
        onDismiss={dismissNotification}
      />
    </div>
  );
}

export default AccountWizard;
