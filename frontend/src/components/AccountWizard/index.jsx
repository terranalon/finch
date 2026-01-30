import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../../lib/index.js';
import { XIcon } from './icons.jsx';
import { WizardStepIndicator } from './WizardStepIndicator.jsx';
import { SetupGuidePanel } from './SetupGuidePanel.jsx';
import {
  AccountTypeStep,
  BrokerSelectionStep,
  AccountDetailsStep,
  DataConnectionStep,
  ManualDataStep,
  ImportingStep,
  ImportResultsStep,
  SuccessStep,
  LinkExistingStep,
} from './steps/index.js';
import { getBrokerConfig } from './constants/brokerConfig.js';

export function AccountWizard({ isOpen, onClose, portfolioId, linkableAccounts = [] }) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [maxReachedStep, setMaxReachedStep] = useState(1);
  const [skippedSteps, setSkippedSteps] = useState([]);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);
  const [accountDetails, setAccountDetails] = useState(null);
  const [createdAccountId, setCreatedAccountId] = useState(null);
  const [skippedData, setSkippedData] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [showImportResults, setShowImportResults] = useState(false);
  const [importResults, setImportResults] = useState(null);
  const [showGuide, setShowGuide] = useState(null);

  const reset = () => {
    setCurrentStep(1);
    setMaxReachedStep(1);
    setSkippedSteps([]);
    setCategory(null);
    setBroker(null);
    setAccountDetails(null);
    setCreatedAccountId(null);
    setSkippedData(false);
    setIsImporting(false);
    setShowImportResults(false);
    setImportResults(null);
    setShowGuide(null);
  };

  const handleClose = () => {
    reset();
    onClose?.();
  };

  const goToStep = (step) => {
    setCurrentStep(step);
    // Reset forward state when going back
    if (step === 1) {
      setCategory(null);
      setBroker(null);
      setAccountDetails(null);
    } else if (step === 2) {
      setBroker(null);
      setAccountDetails(null);
    } else if (step === 3) {
      setAccountDetails(null);
    }
  };

  // Step 1: Category selection
  const handleCategorySelect = (cat) => {
    setCategory(cat);
    if (cat.id === 'manual') {
      // Manual flow skips broker selection (step 2)
      setBroker(null);
      setSkippedSteps([2]);
      setCurrentStep(3);
      setMaxReachedStep(Math.max(maxReachedStep, 3));
    } else if (cat.id !== 'link') {
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

  // Step 3: Account details submission -> Create account via API
  const handleDetailsSubmit = async (details) => {
    setAccountDetails(details);

    try {
      const response = await api('/accounts', {
        method: 'POST',
        body: JSON.stringify({
          name: details.name,
          description: details.description || null,
          account_type: details.accountType,
          currency: details.currency,
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
      setCreatedAccountId(account.id);
      setCurrentStep(4);
      setMaxReachedStep(Math.max(maxReachedStep, 4));
    } catch (error) {
      console.error('Failed to create account:', error);
      alert(`Failed to create account: ${error.message}`);
    }
  };

  // Step 4: Data connection complete -> Import data
  const handleDataComplete = async (data) => {
    setIsImporting(true);

    try {
      if (data.credentials) {
        // API connection - save credentials using PUT (correct method)
        const credResponse = await api(`/brokers/${broker.type}/credentials/${createdAccountId}`, {
          method: 'PUT',
          body: JSON.stringify(data.credentials),
        });

        if (!credResponse.ok) {
          const error = await credResponse.json();
          throw new Error(error.detail || 'Failed to save credentials');
        }

        // Trigger data import using correct endpoint
        const importResponse = await api(`/brokers/${broker.type}/import/${createdAccountId}`, {
          method: 'POST',
        });

        if (!importResponse.ok) {
          const error = await importResponse.json();
          throw new Error(error.detail || 'Failed to import data');
        }

        const results = await importResponse.json();
        // Transform backend response to match UI expectations
        setImportResults(transformImportResults(results));
      } else if (data.file) {
        // File upload
        const formData = new FormData();
        formData.append('file', data.file);
        formData.append('broker_type', broker?.type || 'manual');

        const uploadResponse = await api(`/broker-data/upload/${createdAccountId}`, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          const error = await uploadResponse.json();
          throw new Error(error.detail || 'Failed to upload file');
        }

        const results = await uploadResponse.json();
        setImportResults(transformImportResults(results));
      }

      setSkippedData(false);
      setIsImporting(false);
      setShowImportResults(true);
    } catch (error) {
      console.error('Import failed:', error);
      setIsImporting(false);
      alert(`Import failed: ${error.message}`);
    }
  };

  // Transform backend import response to UI format
  const transformImportResults = (backendResults) => {
    const stats = backendResults.stats || {};

    // Calculate total transactions from all categories
    const transactionsImported = (stats.transactions?.imported || 0)
      + (stats.cash_transactions?.imported || 0)
      + (stats.dividends?.imported || 0);

    // Calculate total assets created
    const assetsCreated = (stats.transactions?.assets_created || 0)
      + (stats.positions?.assets_created || 0);

    // Get holdings count from reconstruction stats
    const holdingsCount = stats.holdings_reconstruction?.updated || 0;

    // Format date range
    const dateRange = stats.date_range || {};
    const formatDate = (dateStr) => {
      if (!dateStr) return 'N/A';
      try {
        return new Date(dateStr).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        });
      } catch {
        return dateStr;
      }
    };

    return {
      assets: [], // Backend doesn't return asset list in import response
      summary: {
        totalAssets: holdingsCount || assetsCreated,
        totalTransactions: transactionsImported,
        dateRange: {
          start: formatDate(dateRange.start_date),
          end: formatDate(dateRange.end_date),
        },
        totalValue: 0, // Would need separate API call to get current value
        cashBalance: 0,
      },
      message: backendResults.message,
    };
  };

  // Step 4: Test credentials before import
  const handleTestCredentials = async (credentials) => {
    // First save credentials
    const credResponse = await api(`/brokers/${broker.type}/credentials/${createdAccountId}`, {
      method: 'PUT',
      body: JSON.stringify(credentials),
    });

    if (!credResponse.ok) {
      const error = await credResponse.json();
      throw new Error(error.detail || 'Failed to save credentials');
    }

    // Then test them
    const testResponse = await api(`/brokers/${broker.type}/test-credentials/${createdAccountId}`, {
      method: 'POST',
    });

    const result = await testResponse.json();
    if (result.status !== 'success') {
      throw new Error(result.message || 'Credential test failed');
    }

    return result;
  };

  // Step 4: Skip data import
  const handleDataSkip = () => {
    setSkippedData(true);
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
      console.error('Failed to link account:', error);
      alert(`Failed to link account: ${error.message}`);
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
  const isManualFlow = category?.id === 'manual';
  const brokerConfig = broker ? getBrokerConfig(broker.type) : null;

  // Determine what to render
  let stepContent;

  if (isImporting) {
    stepContent = <ImportingStep message="Importing your data..." />;
  } else if (showImportResults) {
    stepContent = (
      <ImportResultsStep
        broker={brokerConfig}
        importResults={importResults}
        onContinue={handleImportResultsContinue}
      />
    );
  } else if (currentStep === 1) {
    if (category?.id === 'link') {
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
        onViewAccount={handleViewAccount}
        onAddAnother={handleAddAnother}
        onDone={handleClose}
      />
    );
  }

  const effectiveStep = showImportResults ? 4 : currentStep;
  const showStepIndicator = effectiveStep > 1 && category?.id !== 'link' && !isImporting;

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
    </div>
  );
}

export default AccountWizard;
