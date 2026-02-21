import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { usePortfolio } from '../../contexts';
import { api } from '../../lib/api';

import { OnboardingStepIndicator } from './OnboardingStepIndicator';
import { WelcomeStep } from './WelcomeStep';
import { FinishStep } from './FinishStep';

import { AccountTypeStep } from '../AccountWizard/steps/AccountTypeStep';
import { BrokerSelectionStep } from '../AccountWizard/steps/BrokerSelectionStep';
import { DataConnectionStep } from '../AccountWizard/steps/DataConnectionStep';
import { ImportingStep } from '../AccountWizard/steps/ImportingStep';
import { ImportResultsStep } from '../AccountWizard/steps/ImportResultsStep';
import { WizardNotification } from '../AccountWizard/WizardNotification';
import { SetupGuidePanel } from '../AccountWizard/SetupGuidePanel';
import { CATEGORY_IDS } from '../AccountWizard/constants/index.js';

const STEPS = ['Welcome', 'Type', 'Broker', 'Connect', 'Results', 'Finish'];

function FinchLogo() {
  return (
    <svg viewBox="0 0 32 32" fill="none" width="24" height="24">
      <rect width="32" height="32" rx="8" fill="#2563EB" />
      <path d="M8 16l5 5 11-11" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function formatDate(dateStr) {
  return dateStr ? new Date(dateStr).toLocaleDateString() : 'N/A';
}

function countTransactions(stats) {
  return (stats.transactions?.imported || 0)
    + (stats.cash_transactions?.imported || 0)
    + (stats.dividends?.imported || 0);
}

function formatDateRange(dateRange) {
  return { start: formatDate(dateRange.start_date), end: formatDate(dateRange.end_date) };
}

function transformImportResults(backendResults) {
  const stats = backendResults.stats || {};
  const assetsCreated = (stats.transactions?.assets_created || 0)
    + (stats.positions?.assets_created || 0);
  const holdingsCount = stats.holdings_reconstruction?.holdings_updated || 0;

  return {
    assets: [],
    summary: {
      totalAssets: holdingsCount || assetsCreated,
      totalTransactions: countTransactions(stats),
      dateRange: formatDateRange(stats.date_range || {}),
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
      dateRange: { start: 'Today', end: 'Today' },
    },
    message: backendResults.message,
  };
}

function transformFileUploadResults(results) {
  const stats = results.stats || {};

  return {
    assets: [],
    summary: {
      totalAssets: stats.unique_assets_in_file || 0,
      totalTransactions: countTransactions(stats),
      dateRange: formatDateRange(results.date_range || {}),
    },
    message: results.message,
  };
}

export function OnboardingFlow() {
  const navigate = useNavigate();
  const { refetchPortfolios } = usePortfolio();

  const [currentStep, setCurrentStep] = useState(1);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);

  // Resource IDs (lazy creation)
  const portfolioIdRef = useRef(null);
  const createPortfolioPromiseRef = useRef(null);
  const accountIdRef = useRef(null);
  const createPromiseRef = useRef(null);

  // Import state
  const [isImporting, setIsImporting] = useState(false);
  const [importResults, setImportResults] = useState(null);
  const [sectionValidation, setSectionValidation] = useState(null);

  // UI
  const [notification, setNotification] = useState({ message: null, type: 'error' });
  const [showGuide, setShowGuide] = useState(null);

  const showNotification = useCallback((message, type = 'error') => {
    setNotification({ message, type });
  }, []);

  // ---- Step handlers ----

  const handleCategorySelect = useCallback((cat) => {
    setCategory(cat);
    if (cat.id === CATEGORY_IDS.MANUAL) {
      setBroker(null);
      setCurrentStep(4);
    } else {
      setCurrentStep(3);
    }
  }, []);

  const handleBrokerSelect = useCallback((b) => {
    setBroker(b);
    setCurrentStep(4);
  }, []);

  // ---- Lazy resource creation ----

  const ensurePortfolio = useCallback(async () => {
    if (portfolioIdRef.current) return portfolioIdRef.current;
    if (createPortfolioPromiseRef.current) return createPortfolioPromiseRef.current;

    async function doCreate() {
      const response = await api('/portfolios', {
        method: 'POST',
        body: JSON.stringify({ name: 'My Portfolio' }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create portfolio');
      }
      const portfolio = await response.json();
      portfolioIdRef.current = portfolio.id;
      return portfolio.id;
    }

    const promise = doCreate().finally(() => { createPortfolioPromiseRef.current = null; });
    createPortfolioPromiseRef.current = promise;
    return promise;
  }, []);

  const createAccount = useCallback(async (pId) => {
    if (accountIdRef.current) return accountIdRef.current;
    if (createPromiseRef.current) return createPromiseRef.current;

    async function doCreate() {
      const response = await api('/accounts', {
        method: 'POST',
        body: JSON.stringify({
          name: broker?.name || 'Manual Account',
          account_type: broker?.defaultAccountType || 'Investment',
          currency: broker?.defaultCurrency || 'USD',
          institution: broker?.name || 'Manual',
          broker_type: broker?.type || null,
          portfolio_ids: [pId],
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create account');
      }
      const account = await response.json();
      accountIdRef.current = account.id;
      return account.id;
    }

    const promise = doCreate().finally(() => { createPromiseRef.current = null; });
    createPromiseRef.current = promise;
    return promise;
  }, [broker]);

  // ---- Import logic ----

  const handleDataComplete = useCallback(async (data) => {
    setIsImporting(true);

    try {
      const pId = await ensurePortfolio();
      const accountId = await createAccount(pId);

      if (data.credentials) {
        const credResponse = await api(`/brokers/${broker.type}/credentials/${accountId}`, {
          method: 'PUT',
          body: JSON.stringify(data.credentials),
        });
        if (!credResponse.ok) {
          const err = await credResponse.json();
          throw new Error(err.message || 'Failed to save credentials');
        }

        let results;
        if (broker.type === 'ibkr' || broker.supportsSmartOnboarding) {
          const importResponse = await api(`/brokers/${broker.type}/onboard/${accountId}`, { method: 'POST' });

          if (importResponse.status === 422) {
            const err = await importResponse.json();
            if (err.extra?.missing_sections) {
              setSectionValidation({ missing: err.extra.missing_sections, required: err.extra.required_sections });
              setIsImporting(false);
              return;
            }
            throw new Error(err.message || 'Import validation failed');
          }
          if (!importResponse.ok) {
            const err = await importResponse.json();
            throw new Error(err.message || 'Import failed');
          }

          results = await importResponse.json();
          const isFullHistory = results.import_mode === 'full_history';
          setImportResults(isFullHistory ? transformImportResults(results) : transformSnapshotResults(results));
        } else if (broker.supportsSnapshot) {
          const snapshotResponse = await api(`/brokers/${broker.type}/snapshot/${accountId}`, { method: 'POST' });
          if (!snapshotResponse.ok) {
            const err = await snapshotResponse.json();
            throw new Error(err.message || 'Snapshot import failed');
          }
          results = await snapshotResponse.json();
          setImportResults(transformSnapshotResults(results));
        } else {
          const importResponse = await api(`/brokers/${broker.type}/import/${accountId}`, { method: 'POST' });
          if (!importResponse.ok) {
            const err = await importResponse.json();
            throw new Error(err.message || 'Import failed');
          }
          results = await importResponse.json();
          setImportResults(transformImportResults(results));
        }

        setIsImporting(false);
        setCurrentStep(5);
      } else if (data.file) {
        const formData = new FormData();
        formData.append('file', data.file);
        formData.append('broker_type', broker?.type || 'manual');

        const uploadResponse = await api(`/broker-data/upload/${accountId}`, {
          method: 'POST',
          body: formData,
        });
        if (!uploadResponse.ok) {
          const err = await uploadResponse.json();
          throw new Error(err.message || 'File upload failed');
        }
        const results = await uploadResponse.json();
        setImportResults(transformFileUploadResults(results));
        setIsImporting(false);
        setCurrentStep(5);
      }
    } catch (error) {
      setIsImporting(false);
      showNotification(`Import failed: ${error.message}`);
    }
  }, [broker, ensurePortfolio, createAccount, showNotification]);

  const handleTestCredentials = useCallback(async (credentials) => {
    const testResponse = await api(`/brokers/${broker.type}/test-credentials`, {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    const result = await testResponse.json();
    if (result.status !== 'success') {
      throw new Error(result.message || 'Credential test failed');
    }
    return result;
  }, [broker]);

  // ---- Finish handlers ----

  const handleGoToDashboard = useCallback(async (portfolioName) => {
    if (portfolioIdRef.current && portfolioName && portfolioName !== 'My Portfolio') {
      api(`/portfolios/${portfolioIdRef.current}`, {
        method: 'PUT',
        body: JSON.stringify({ name: portfolioName }),
      }).catch(() => {});
    }
    await refetchPortfolios();
    navigate('/');
  }, [refetchPortfolios, navigate]);

  const handleStepClick = useCallback((stepNum) => {
    if (accountIdRef.current || isImporting) return;
    setCurrentStep(stepNum);
  }, [isImporting]);

  const handleAddAnother = useCallback(() => {
    setCategory(null);
    setBroker(null);
    accountIdRef.current = null;
    createPromiseRef.current = null;
    setImportResults(null);
    setSectionValidation(null);
    setCurrentStep(2);
  }, []);

  // ---- Render step content ----

  function renderStepContent() {
    if (isImporting) {
      return <ImportingStep message="Importing your data..." />;
    }

    switch (currentStep) {
      case 1:
        return <WelcomeStep onContinue={() => setCurrentStep(2)} />;
      case 2:
        return <AccountTypeStep onSelect={handleCategorySelect} />;
      case 3:
        return (
          <BrokerSelectionStep
            category={category}
            onSelect={handleBrokerSelect}
            onBack={() => setCurrentStep(2)}
          />
        );
      case 4:
        return (
          <DataConnectionStep
            broker={broker}
            onComplete={handleDataComplete}
            onBack={() => {
              if (accountIdRef.current) return;
              setCurrentStep(broker ? 3 : 2);
            }}
            onShowGuide={(type) => setShowGuide(type)}
            onTestCredentials={handleTestCredentials}
            onError={showNotification}
            sectionValidation={sectionValidation}
            isImporting={isImporting}
          />
        );
      case 5:
        return (
          <ImportResultsStep
            broker={broker}
            importResults={importResults}
            onContinue={() => setCurrentStep(6)}
          />
        );
      case 6:
        return (
          <FinishStep
            onGoToDashboard={handleGoToDashboard}
            onAddAnother={handleAddAnother}
            defaultPortfolioName="My Portfolio"
          />
        );
      default:
        return null;
    }
  }

  return (
    <div className="min-h-dvh bg-[var(--bg-primary)] flex flex-col">
      <div className="px-7 py-4 border-b border-[var(--border-primary)] flex items-center">
        <div className="flex items-center gap-2 text-lg font-bold text-[var(--text-primary)]">
          <FinchLogo />
          Finch
        </div>
      </div>

      <OnboardingStepIndicator steps={STEPS} currentStep={currentStep} onStepClick={handleStepClick} />

      <div className="flex-1 flex items-start justify-center overflow-y-auto">
        <div className="w-full max-w-4xl px-6 py-10">
          {renderStepContent()}
        </div>
      </div>

      <WizardNotification
        message={notification.message}
        type={notification.type}
        onDismiss={() => setNotification({ message: null, type: 'error' })}
      />

      {showGuide && broker && (
        <SetupGuidePanel
          broker={broker}
          guideType={showGuide}
          onClose={() => setShowGuide(null)}
        />
      )}
    </div>
  );
}
