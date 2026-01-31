import { useState } from 'react';

import { cn } from '../../../lib/index.js';
import { ArrowLeftIcon } from '../icons.jsx';

const CURRENCIES = [
  { value: 'USD', label: 'USD - US Dollar' },
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'GBP', label: 'GBP - British Pound' },
  { value: 'ILS', label: 'ILS - Israeli Shekel' },
];

const ACCOUNT_TYPES = [
  { value: 'Investment', label: 'Investment' },
  { value: 'IRA', label: 'IRA' },
  { value: '401k', label: '401(k)' },
  { value: 'Crypto', label: 'Crypto' },
  { value: 'Savings', label: 'Savings' },
];

export function AccountDetailsStep({ broker, category, onSubmit, onBack }) {
  const defaultName = broker
    ? `My ${broker.name} Account`
    : 'My Account';

  const [name, setName] = useState(defaultName);
  const [description, setDescription] = useState('');
  const [currency, setCurrency] = useState(broker?.defaultCurrency || 'USD');
  const [accountType, setAccountType] = useState(category?.defaultAccountType || 'Investment');
  const [showAccountTypeSelect, setShowAccountTypeSelect] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ name, description, accountType, currency });
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Account details
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          {broker ? `Set up your ${broker.name} account.` : 'Set up your account.'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Account Name */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Account Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className={cn(
              'w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
              'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
              'placeholder:text-gray-400'
            )}
            placeholder="e.g., Main Portfolio"
          />
        </div>

        {/* Description (Optional) */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Description <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className={cn(
              'w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
              'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
              'placeholder:text-gray-400'
            )}
            placeholder="e.g., Long-term retirement savings"
          />
        </div>

        {/* Currency */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Base Currency
          </label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className={cn(
              'w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
              'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer'
            )}
          >
            {CURRENCIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Account type - auto-filled with option to change */}
        <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
          {!showAccountTypeSelect ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Account Type</p>
                <p className="font-medium text-gray-900 dark:text-white">{accountType}</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAccountTypeSelect(true)}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium cursor-pointer"
              >
                Change
              </button>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Account Type
              </label>
              <select
                value={accountType}
                onChange={(e) => {
                  setAccountType(e.target.value);
                  setShowAccountTypeSelect(false);
                }}
                className={cn(
                  'w-full px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700',
                  'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer'
                )}
              >
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-6">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeftIcon className="size-5" />
            <span className="font-medium">Back</span>
          </button>
          <button
            type="submit"
            className="px-6 py-3 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
          >
            Continue
          </button>
        </div>
      </form>
    </div>
  );
}
