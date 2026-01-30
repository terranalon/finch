import { cn } from '../../../lib/index.js';
import { CATEGORY_IDS } from '../constants/index.js';

import {
  BitcoinIcon,
  BuildingIcon,
  ChevronRightIcon,
  DocumentIcon,
  LinkIcon,
} from '../icons.jsx';

const CATEGORY_ICONS = {
  building: BuildingIcon,
  bitcoin: BitcoinIcon,
  document: DocumentIcon,
  link: LinkIcon,
};

const ACCOUNT_CATEGORIES = [
  {
    id: CATEGORY_IDS.BROKERAGE,
    label: 'Brokerage',
    description: 'Traditional brokerage for stocks and ETFs',
    icon: 'building',
    defaultAccountType: 'Investment',
  },
  {
    id: CATEGORY_IDS.CRYPTO,
    label: 'Crypto Exchange',
    description: 'Connect your crypto exchange account',
    icon: 'bitcoin',
    defaultAccountType: 'Crypto',
  },
  {
    id: CATEGORY_IDS.MANUAL,
    label: 'Manual',
    description: 'Import transactions from any source using our template',
    icon: 'document',
    defaultAccountType: 'Investment',
  },
];

export function AccountTypeStep({ onSelect, linkableAccounts = [] }) {
  const categories = linkableAccounts.length > 0
    ? [...ACCOUNT_CATEGORIES, {
        id: CATEGORY_IDS.LINK,
        label: 'Link Existing',
        description: "Add an account you've already created",
        icon: 'link',
        defaultAccountType: null,
      }]
    : ACCOUNT_CATEGORIES;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3 text-balance">
          What type of account would you like to add?
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg text-pretty">
          Choose the category that best describes your account.
        </p>
      </div>

      <div className="grid gap-4">
        {categories.map((category) => {
          const Icon = CATEGORY_ICONS[category.icon];
          return (
            <button
              key={category.id}
              onClick={() => onSelect(category)}
              className={cn(
                'flex items-center gap-5 p-5 sm:p-6 rounded-2xl border-2',
                'border-gray-200 dark:border-gray-700',
                'hover:border-blue-500 dark:hover:border-blue-500',
                'hover:bg-blue-50/50 dark:hover:bg-blue-950/20',
                'transition-all text-left group cursor-pointer'
              )}
            >
              <div className={cn(
                'p-4 rounded-2xl bg-gray-100 dark:bg-gray-800',
                'group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors'
              )}>
                <Icon className="size-8 text-gray-600 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {category.label}
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  {category.description}
                </p>
              </div>
              <ChevronRightIcon className="size-5 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
