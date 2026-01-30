import { useState } from 'react';
import { WizardStepIndicator } from './WizardStepIndicator';

function XIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

export function AccountWizard({ isOpen, onClose, portfolioId, linkableAccounts = [] }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [maxReachedStep, setMaxReachedStep] = useState(1);
  const [skippedSteps, setSkippedSteps] = useState([]);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);
  const [accountDetails, setAccountDetails] = useState(null);
  const [skippedData, setSkippedData] = useState(false);
  const [showImportResults, setShowImportResults] = useState(false);
  const [importResults, setImportResults] = useState(null);

  const reset = () => {
    setCurrentStep(1);
    setMaxReachedStep(1);
    setSkippedSteps([]);
    setCategory(null);
    setBroker(null);
    setAccountDetails(null);
    setSkippedData(false);
    setShowImportResults(false);
    setImportResults(null);
  };

  const handleClose = () => {
    reset();
    onClose?.();
  };

  const goToStep = (step) => {
    setCurrentStep(step);
  };

  if (!isOpen) return null;

  const effectiveStep = showImportResults ? 4 : currentStep;
  const showStepIndicator = effectiveStep > 1 && category?.id !== 'link';

  return (
    <div className="fixed inset-0 z-50 bg-white dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 dark:border-gray-800">
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

      {/* Main content - placeholder */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          <div className="text-center text-gray-500">
            Step {currentStep} content placeholder
          </div>
        </div>
      </main>
    </div>
  );
}

export default AccountWizard;
