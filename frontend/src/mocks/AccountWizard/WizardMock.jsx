/**
 * Account Creation Wizard - Interactive Mock
 *
 * This mock demonstrates the full UX flow for validating the wizard design
 * before implementation. All steps are functional for navigation purposes.
 */

import React, { useState } from 'react';

// Mock broker data
const BROKER_CATEGORIES = [
  {
    id: 'brokerage',
    label: 'Brokerage',
    description: 'Traditional brokerage for stocks and ETFs',
    icon: 'building',
  },
  {
    id: 'crypto',
    label: 'Crypto Exchange',
    description: 'Connect your crypto exchange account',
    icon: 'bitcoin',
  },
  {
    id: 'link',
    label: 'Link Existing',
    description: "Add an account you've already created",
    icon: 'link',
  },
];

const BROKERS = {
  brokerage: [
    { type: 'ibkr', name: 'Interactive Brokers', hasApi: true, formats: ['XML'] },
    { type: 'meitav', name: 'Meitav Trade', hasApi: false, formats: ['XLSX'] },
  ],
  crypto: [
    { type: 'kraken', name: 'Kraken', hasApi: true, formats: ['CSV'] },
    { type: 'bit2c', name: 'Bit2C', hasApi: true, formats: ['CSV'] },
    { type: 'binance', name: 'Binance', hasApi: true, formats: ['CSV'] },
  ],
};

const LINKABLE_ACCOUNTS = [
  { id: 1, name: 'Main IBKR', institution: 'Interactive Brokers', type: 'Investment', currency: 'USD' },
  { id: 2, name: 'Crypto Holdings', institution: 'Kraken', type: 'Crypto', currency: 'USD' },
];

// Icons as inline SVGs
const Icons = {
  building: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z" />
    </svg>
  ),
  bitcoin: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  ),
  link: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
    </svg>
  ),
  x: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  ),
  arrowLeft: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
    </svg>
  ),
  check: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  ),
  upload: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  ),
  api: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
    </svg>
  ),
  chevronDown: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  ),
  sparkles: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
    </svg>
  ),
};

// Step Indicator Component
function StepIndicator({ currentStep, totalSteps = 5 }) {
  const steps = [
    { num: 1, label: 'Type' },
    { num: 2, label: 'Broker' },
    { num: 3, label: 'Details' },
    { num: 4, label: 'Connect' },
    { num: 5, label: 'Done' },
  ];

  return (
    <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        {steps.map((step, idx) => (
          <React.Fragment key={step.num}>
            <div className="flex items-center gap-2">
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                  ${currentStep > step.num
                    ? 'bg-emerald-500 text-white'
                    : currentStep === step.num
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  }
                `}
              >
                {currentStep > step.num ? (
                  <Icons.check className="w-4 h-4" />
                ) : (
                  step.num
                )}
              </div>
              <span
                className={`
                  text-sm font-medium hidden sm:block
                  ${currentStep >= step.num
                    ? 'text-gray-900 dark:text-white'
                    : 'text-gray-400 dark:text-gray-500'
                  }
                `}
              >
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-0.5 mx-2
                  ${currentStep > step.num
                    ? 'bg-emerald-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                  }
                `}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// Step 1: Account Type Selection
function AccountTypeStep({ onSelect }) {
  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        What type of account would you like to add?
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Choose the category that best describes your account.
      </p>

      <div className="grid gap-4">
        {BROKER_CATEGORIES.map((category) => {
          const Icon = Icons[category.icon];
          return (
            <button
              key={category.id}
              onClick={() => onSelect(category.id)}
              className="flex items-center gap-4 p-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-left group"
            >
              <div className="p-3 rounded-xl bg-gray-100 dark:bg-gray-800 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                <Icon className="w-6 h-6 text-gray-600 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {category.label}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {category.description}
                </p>
              </div>
              <Icons.chevronDown className="w-5 h-5 text-gray-400 -rotate-90" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Step 1b: Link Existing Accounts
function LinkExistingStep({ onSelect, onBack }) {
  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Link an existing account
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Select an account to add to this portfolio.
      </p>

      {LINKABLE_ACCOUNTS.length > 0 ? (
        <div className="space-y-3">
          {LINKABLE_ACCOUNTS.map((account) => (
            <button
              key={account.id}
              onClick={() => onSelect(account)}
              className="w-full flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-left"
            >
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {account.name}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {account.institution} &middot; {account.type} &middot; {account.currency}
                </p>
              </div>
              <span className="px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-600 text-white">
                Link
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <Icons.link className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            No accounts available to link.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            All accounts are already in this portfolio.
          </p>
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <Icons.arrowLeft className="w-4 h-4" />
          Back to account types
        </button>
      </div>
    </div>
  );
}

// Step 2: Broker Selection
function BrokerSelectionStep({ category, onSelect, onBack }) {
  const brokers = BROKERS[category] || [];

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Select your {category === 'crypto' ? 'exchange' : 'broker'}
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Choose from our supported {category === 'crypto' ? 'exchanges' : 'brokers'}.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        {brokers.map((broker) => (
          <button
            key={broker.type}
            onClick={() => onSelect(broker)}
            className="flex flex-col items-start p-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-left group"
          >
            <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
              {broker.name}
            </h3>
            <div className="flex gap-2 mt-2">
              {broker.hasApi && (
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                  API
                </span>
              )}
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                {broker.formats.join(', ')}
              </span>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <Icons.arrowLeft className="w-4 h-4" />
          Back to account types
        </button>
      </div>
    </div>
  );
}

// Step 3: Account Details
function AccountDetailsStep({ broker, onSubmit, onBack }) {
  const [name, setName] = useState(`My ${broker.name} Account`);
  const [accountType, setAccountType] = useState(
    broker.type === 'kraken' || broker.type === 'bit2c' || broker.type === 'binance'
      ? 'Crypto'
      : 'Investment'
  );
  const [currency, setCurrency] = useState(
    broker.type === 'meitav' || broker.type === 'bit2c' ? 'ILS' : 'USD'
  );

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Account details
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Configure your {broker.name} account.
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
            Account Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., Main Portfolio"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Account Type
            </label>
            <select
              value={accountType}
              onChange={(e) => setAccountType(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Investment">Investment</option>
              <option value="IRA">IRA</option>
              <option value="401k">401(k)</option>
              <option value="Crypto">Crypto</option>
              <option value="Savings">Savings</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="ILS">ILS</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-8 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <Icons.arrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          onClick={() => onSubmit({ name, accountType, currency })}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          Continue
        </button>
      </div>
    </div>
  );
}

// Step 4: Data Connection
function DataConnectionStep({ broker, onComplete, onSkip, onBack }) {
  const [connectionMethod, setConnectionMethod] = useState(broker.hasApi ? 'api' : 'file');
  const [isExpanded, setIsExpanded] = useState(false);
  const [testStatus, setTestStatus] = useState('idle'); // idle | testing | success | error

  const handleTest = () => {
    setTestStatus('testing');
    setTimeout(() => {
      setTestStatus('success');
    }, 1500);
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Connect your data
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Import your transaction history from {broker.name}.
      </p>

      {/* Tab switcher (only if API is supported) */}
      {broker.hasApi && (
        <div className="flex gap-1 p-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <button
            onClick={() => setConnectionMethod('api')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              connectionMethod === 'api'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Icons.api className="w-4 h-4" />
            Connect API
          </button>
          <button
            onClick={() => setConnectionMethod('file')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              connectionMethod === 'file'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Icons.upload className="w-4 h-4" />
            Upload File
          </button>
        </div>
      )}

      {/* API Connection */}
      {connectionMethod === 'api' && broker.hasApi && (
        <div className="space-y-4">
          {/* Collapsible instructions */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400 text-sm"
          >
            <span>How to get your API credentials</span>
            <Icons.chevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </button>

          {isExpanded && (
            <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm text-gray-600 dark:text-gray-400">
              <ol className="list-decimal list-inside space-y-2">
                <li>Log into your {broker.name} account</li>
                <li>Go to Settings &gt; API Keys</li>
                <li>Create a new key with read-only permissions</li>
                <li>Copy the API Key and Secret</li>
              </ol>
            </div>
          )}

          {/* Credential fields */}
          <div className="space-y-3">
            {broker.type === 'ibkr' ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Flex Token
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your Flex Web Service Token"
                    className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Flex Query ID
                  </label>
                  <input
                    type="text"
                    placeholder="Enter your Query ID"
                    className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    API Key
                  </label>
                  <input
                    type="text"
                    placeholder="Enter your API Key"
                    className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    API Secret
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your API Secret"
                    className="w-full px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
              </>
            )}
          </div>

          {/* Test result */}
          {testStatus === 'success' && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400">
              <Icons.check className="w-5 h-5" />
              <span className="text-sm font-medium">Connection successful! Found 3 assets.</span>
            </div>
          )}

          {/* Test button */}
          <button
            onClick={handleTest}
            disabled={testStatus === 'testing'}
            className="w-full px-4 py-2.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {testStatus === 'testing' ? 'Testing...' : testStatus === 'success' ? 'Test Again' : 'Test Connection'}
          </button>
        </div>
      )}

      {/* File Upload */}
      {connectionMethod === 'file' && (
        <div className="space-y-4">
          {/* Instructions */}
          <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm text-gray-600 dark:text-gray-400">
            <p className="font-medium text-gray-900 dark:text-white mb-2">Export from {broker.name}:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Log into your account</li>
              <li>Go to Reports or History</li>
              <li>Export as {broker.formats.join(' or ')}</li>
            </ol>
          </div>

          {/* Drop zone */}
          <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-colors cursor-pointer">
            <Icons.upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Drop your file here or click to browse
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Supports {broker.formats.join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-8 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        >
          <Icons.arrowLeft className="w-4 h-4" />
          Back
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Skip for now
          </button>
          <button
            onClick={onComplete}
            disabled={testStatus !== 'success' && connectionMethod === 'api'}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {connectionMethod === 'api' ? 'Save & Import' : 'Upload & Import'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Step 5: Success
function SuccessStep({ broker, accountDetails, skippedData, onViewAccount, onAddAnother, onDone }) {
  return (
    <div className="p-6 text-center">
      {/* Success animation placeholder */}
      <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
        <Icons.check className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
      </div>

      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Account created!
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Your {broker.name} account is ready to use.
      </p>

      {/* Account summary card */}
      <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-left mb-6">
        <h3 className="font-semibold text-gray-900 dark:text-white">
          {accountDetails?.name || `My ${broker.name} Account`}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {broker.name} &middot; {accountDetails?.accountType || 'Investment'} &middot; {accountDetails?.currency || 'USD'}
        </p>

        {!skippedData && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
              <Icons.check className="w-4 h-4" />
              <span>156 transactions imported (Jan 2023 - Present)</span>
            </div>
          </div>
        )}

        {skippedData && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
              <Icons.sparkles className="w-4 h-4" />
              <span>Import your data to start tracking</span>
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="space-y-3">
        <button
          onClick={onViewAccount}
          className="w-full px-4 py-2.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          View Account
        </button>
        <div className="flex gap-3">
          <button
            onClick={onAddAnother}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Add Another Account
          </button>
          <button
            onClick={onDone}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

// Main Wizard Component
export default function WizardMock({ isOpen, onClose }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [category, setCategory] = useState(null);
  const [broker, setBroker] = useState(null);
  const [accountDetails, setAccountDetails] = useState(null);
  const [skippedData, setSkippedData] = useState(false);

  const reset = () => {
    setCurrentStep(1);
    setCategory(null);
    setBroker(null);
    setAccountDetails(null);
    setSkippedData(false);
  };

  const handleClose = () => {
    reset();
    onClose?.();
  };

  const handleCategorySelect = (cat) => {
    setCategory(cat);
    if (cat === 'link') {
      // Stay on step 1 but show link UI
    } else {
      setCurrentStep(2);
    }
  };

  const handleBrokerSelect = (b) => {
    setBroker(b);
    setCurrentStep(3);
  };

  const handleDetailsSubmit = (details) => {
    setAccountDetails(details);
    setCurrentStep(4);
  };

  const handleDataComplete = () => {
    setSkippedData(false);
    setCurrentStep(5);
  };

  const handleDataSkip = () => {
    setSkippedData(true);
    setCurrentStep(5);
  };

  const handleAddAnother = () => {
    reset();
  };

  if (!isOpen) return null;

  // Determine which step UI to show
  let stepContent;
  if (currentStep === 1) {
    if (category === 'link') {
      stepContent = (
        <LinkExistingStep
          onSelect={() => {
            handleClose();
          }}
          onBack={() => setCategory(null)}
        />
      );
    } else {
      stepContent = <AccountTypeStep onSelect={handleCategorySelect} />;
    }
  } else if (currentStep === 2) {
    stepContent = (
      <BrokerSelectionStep
        category={category}
        onSelect={handleBrokerSelect}
        onBack={() => {
          setCurrentStep(1);
          setCategory(null);
        }}
      />
    );
  } else if (currentStep === 3) {
    stepContent = (
      <AccountDetailsStep
        broker={broker}
        onSubmit={handleDetailsSubmit}
        onBack={() => setCurrentStep(2)}
      />
    );
  } else if (currentStep === 4) {
    stepContent = (
      <DataConnectionStep
        broker={broker}
        onComplete={handleDataComplete}
        onSkip={handleDataSkip}
        onBack={() => setCurrentStep(3)}
      />
    );
  } else if (currentStep === 5) {
    stepContent = (
      <SuccessStep
        broker={broker}
        accountDetails={accountDetails}
        skippedData={skippedData}
        onViewAccount={handleClose}
        onAddAnother={handleAddAnother}
        onDone={handleClose}
      />
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={handleClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              Add Account
            </h1>
            <button
              onClick={handleClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Icons.x className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Step indicator (hide on step 1 and link flow) */}
          {currentStep > 1 && category !== 'link' && (
            <StepIndicator currentStep={currentStep} />
          )}

          {/* Step content */}
          <div className="flex-1 overflow-y-auto">
            {stepContent}
          </div>
        </div>
      </div>
    </>
  );
}
