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
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3 text-balance">
          What type of account would you like to add?
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg text-pretty">
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
                'border-[var(--border-primary)]',
                'hover:border-accent',
                'hover:bg-accent-50/50 dark:hover:bg-accent-900/20',
                'transition-all text-left group cursor-pointer'
              )}
            >
              <div className={cn(
                'p-4 rounded-2xl bg-[var(--bg-tertiary)]',
                'group-hover:bg-accent-100 dark:group-hover:bg-accent-900/30 transition-colors'
              )}>
                <Icon className="size-8 text-[var(--text-secondary)] group-hover:text-accent dark:group-hover:text-accent-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-[var(--text-primary)] group-hover:text-accent dark:group-hover:text-accent-400">
                  {category.label}
                </h3>
                <p className="text-[var(--text-tertiary)] mt-1">
                  {category.description}
                </p>
              </div>
              <ChevronRightIcon className="size-5 text-[var(--text-tertiary)] group-hover:text-accent group-hover:translate-x-1 transition-all" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
