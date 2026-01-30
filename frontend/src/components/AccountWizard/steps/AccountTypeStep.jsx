import { cn } from '../../../lib';

const ACCOUNT_CATEGORIES = [
  {
    id: 'brokerage',
    label: 'Brokerage',
    description: 'Traditional brokerage for stocks and ETFs',
    icon: 'building',
    defaultAccountType: 'Investment',
  },
  {
    id: 'crypto',
    label: 'Crypto Exchange',
    description: 'Connect your crypto exchange account',
    icon: 'bitcoin',
    defaultAccountType: 'Crypto',
  },
  {
    id: 'manual',
    label: 'Manual',
    description: 'Import transactions from any source using our template',
    icon: 'document',
    defaultAccountType: 'Investment',
  },
];

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
  document: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  ),
  link: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
    </svg>
  ),
  chevronRight: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
    </svg>
  ),
};

export function AccountTypeStep({ onSelect, linkableAccounts = [] }) {
  const categories = linkableAccounts.length > 0
    ? [...ACCOUNT_CATEGORIES, {
        id: 'link',
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
          const Icon = Icons[category.icon];
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
              <Icons.chevronRight className="size-5 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
