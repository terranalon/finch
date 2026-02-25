import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

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

// Placeholder broker for the manual account path — satisfies DataConnectionStep's
// property reads (hasApi, supportedFormats) without a real broker selection.
const MANUAL_BROKER = {
  name: 'Manual',
  type: null,
  hasApi: false,
  supportedFormats: ['.csv', '.xlsx'],
  supportsSnapshot: false,
  supportsSmartOnboarding: false,
};

function FinchLogo() {
  return (
    <svg viewBox="0 0 32 32" fill="none" width="24" height="24">
      <rect width="32" height="32" rx="8" fill="#2563EB" />
      <path d="M8 16l5 5 11-11" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

async function apiPost(endpoint, body) {
  const options = { method: 'POST' };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.body = JSON.stringify(body);
  }
  const response = await api(endpoint, options);
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.message || 'Request failed');
  }
  return response.json();
}

function ensureOnce(idRef, promiseRef, createFn) {
  if (idRef.current) return Promise.resolve(idRef.current);
  if (promiseRef.current) return promiseRef.current;

  const promise = createFn().finally(() => { promiseRef.current = null; });
  promiseRef.current = promise;
  return promise;
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
  const queryClient = useQueryClient();
  const { refetchPortfolios } = usePortfolio();

  const [currentStep, setCurrentStep] = useState(1);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);

  const portfolioIdRef = useRef(null);
  const createPortfolioPromiseRef = useRef(null);
  const accountIdRef = useRef(null);
  const createAccountPromiseRef = useRef(null);

  const [isImporting, setIsImporting] = useState(false);
  const [importResults, setImportResults] = useState(null);
  const [sectionValidation, setSectionValidation] = useState(null);

  const [notification, setNotification] = useState({ message: null, type: 'error' });
  const [showGuide, setShowGuide] = useState(null);

  const showNotification = useCallback((message, type = 'error') => {
    setNotification({ message, type });
  }, []);

  const handleCategorySelect = useCallback((cat) => {
    setCategory(cat);
    if (cat.id === CATEGORY_IDS.MANUAL) {
      setBroker(MANUAL_BROKER);
      setCurrentStep(4);
    } else {
      setCurrentStep(3);
    }
  }, []);

  const handleBrokerSelect = useCallback((b) => {
    setBroker(b);
    setCurrentStep(4);
  }, []);

  const ensurePortfolio = useCallback(async () => {
    return ensureOnce(portfolioIdRef, createPortfolioPromiseRef, async () => {
      const portfolio = await apiPost('/portfolios', { name: 'My Portfolio' });
      portfolioIdRef.current = portfolio.id;
      return portfolio.id;
    });
  }, []);

  const createAccount = useCallback(async (portfolioId) => {
    return ensureOnce(accountIdRef, createAccountPromiseRef, async () => {
      const account = await apiPost('/accounts', {
        name: broker?.name || 'Manual Account',
        account_type: broker?.defaultAccountType || 'Investment',
        currency: broker?.defaultCurrency || 'USD',
        institution: broker?.name || 'Manual',
        broker_type: broker?.type || null,
        portfolio_ids: [portfolioId],
      });
      accountIdRef.current = account.id;
      return account.id;
    });
  }, [broker]);

  const saveCredentials = useCallback(async (accountId, credentials) => {
    const response = await api(`/brokers/${broker.type}/credentials/${accountId}`, {
      method: 'PUT',
      body: JSON.stringify(credentials),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.message || 'Failed to save credentials');
    }
  }, [broker]);

  const importViaOnboard = useCallback(async (accountId) => {
    const response = await api(`/brokers/${broker.type}/onboard/${accountId}`, { method: 'POST' });

    if (response.status === 422) {
      const err = await response.json();
      if (err.extra?.missing_sections) {
        setSectionValidation({ missing: err.extra.missing_sections, required: err.extra.required_sections });
        return null;
      }
      throw new Error(err.message || 'Import validation failed');
    }
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.message || 'Import failed');
    }

    const results = await response.json();
    const isFullHistory = results.import_mode === 'full_history';
    return isFullHistory ? transformImportResults(results) : transformSnapshotResults(results);
  }, [broker]);

  const importWithCredentials = useCallback(async (accountId, credentials) => {
    await saveCredentials(accountId, credentials);

    if (broker.type === 'ibkr' || broker.supportsSmartOnboarding) {
      return await importViaOnboard(accountId);
    }

    if (broker.supportsSnapshot) {
      const results = await apiPost(`/brokers/${broker.type}/snapshot/${accountId}`);
      return transformSnapshotResults(results);
    }

    const results = await apiPost(`/brokers/${broker.type}/import/${accountId}`);
    return transformImportResults(results);
  }, [broker, saveCredentials, importViaOnboard]);

  const importWithFile = useCallback(async (accountId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('broker_type', broker?.type || 'manual');

    const results = await apiPost(`/broker-data/upload/${accountId}`, formData);
    return transformFileUploadResults(results);
  }, [broker]);

  const handleDataComplete = useCallback(async (data) => {
    setIsImporting(true);
    setSectionValidation(null);

    try {
      const portfolioId = await ensurePortfolio();
      const accountId = await createAccount(portfolioId);

      let results = null;
      if (data.credentials) {
        results = await importWithCredentials(accountId, data.credentials);
      } else if (data.file) {
        results = await importWithFile(accountId, data.file);
      }

      if (results === null) {
        setIsImporting(false);
        return;
      }

      setImportResults(results);
      setIsImporting(false);
      setCurrentStep(5);
    } catch (error) {
      // Reset account ref so a retry creates a fresh account rather than
      // leaving an orphan and creating a second one on the next attempt.
      accountIdRef.current = null;
      createAccountPromiseRef.current = null;
      setIsImporting(false);
      showNotification(`Import failed: ${error.message}`);
    }
  }, [ensurePortfolio, createAccount, importWithCredentials, importWithFile, showNotification]);

  const handleTestCredentials = useCallback(async (credentials) => {
    const result = await apiPost(`/brokers/${broker.type}/test-credentials`, credentials);
    if (result.status !== 'success') {
      throw new Error(result.message || 'Credential test failed');
    }
    return result;
  }, [broker]);

  const handleGoToDashboard = useCallback(async (portfolioName) => {
    if (portfolioIdRef.current && portfolioName && portfolioName !== 'My Portfolio') {
      await api(`/portfolios/${portfolioIdRef.current}`, {
        method: 'PUT',
        body: JSON.stringify({ name: portfolioName }),
      }).catch(() => {
        showNotification('Portfolio rename failed. You can rename it from the Portfolios page.', 'error');
      });
    }
    await refetchPortfolios();
    // Optimistically update the accounts guard cache so OnboardingGuard
    // doesn't redirect back to /onboarding on the next render.
    queryClient.setQueryData(['accounts', 'hasAny'], true);
    navigate('/');
  }, [refetchPortfolios, navigate, queryClient]);

  const handleStepClick = useCallback((stepNum) => {
    if ((accountIdRef.current && !sectionValidation) || isImporting) return;
    if (stepNum > currentStep) return;
    setCurrentStep(stepNum);
  }, [isImporting, sectionValidation, currentStep]);

  const handleAddAnother = useCallback(() => {
    setCategory(null);
    setBroker(null);
    accountIdRef.current = null;
    createAccountPromiseRef.current = null;
    setImportResults(null);
    setSectionValidation(null);
    setCurrentStep(2);
  }, []);

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
              if (accountIdRef.current && !sectionValidation) return;
              // Going back abandons the current account setup; reset so a
              // re-entry creates a fresh account for whichever broker the
              // user picks next.
              accountIdRef.current = null;
              createAccountPromiseRef.current = null;
              setSectionValidation(null);
              setCurrentStep(category?.id === CATEGORY_IDS.MANUAL ? 2 : 3);
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

      <OnboardingStepIndicator steps={STEPS} currentStep={currentStep} onStepClick={(accountIdRef.current && !sectionValidation) || isImporting ? undefined : handleStepClick} />

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
