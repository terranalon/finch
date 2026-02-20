/**
 * Broker configuration for the Account Wizard
 *
 * Contains categorization, display info, and setup instructions for each broker.
 */

export const BROKER_CATEGORIES = {
  brokerage: {
    id: 'brokerage',
    label: 'Brokerage',
    description: 'Traditional brokerage for stocks and ETFs',
    icon: 'BuildingLibrary',
  },
  crypto: {
    id: 'crypto',
    label: 'Crypto Exchange',
    description: 'Connect your crypto exchange account',
    icon: 'Bitcoin',
  },
  link: {
    id: 'link',
    label: 'Link Existing',
    description: "Add an account you've already created",
    icon: 'Link',
  },
};

export const BROKERS = {
  ibkr: {
    type: 'ibkr',
    name: 'Interactive Brokers',
    shortName: 'IBKR',
    category: 'brokerage',
    defaultCurrency: 'USD',
    defaultAccountType: 'Investment',
    hasApi: true,
    supportsSnapshot: true,
    supportedFormats: ['.xml'],
    apiType: 'flex', // Uses flex_token and flex_query_id
    instructions: {
      api: {
        title: 'Connect IBKR Flex Query',
        steps: [
          'Log into IBKR Account Management at secure.interactivebrokers.com',
          'Go to Settings > User Settings > API',
          'Generate a Flex Web Service Token (valid for 60 days)',
          'Go to Reports > Flex Queries > Custom Flex Queries',
          'Create a new query and include these sections: Open Positions, Trades, Cash Transactions, Transfers, Dividends, Forex Trades, Cash Report',
          'Under Account Information, check only "Date Opened" -- we use this to determine how much history to import automatically',
          'Copy the Query ID from the query list',
        ],
        note: 'We value your privacy -- we only use Date Opened to optimize your import. No personal information is requested. Your Flex Token expires after 60 days.',
      },
      file: {
        title: 'Export from IBKR',
        steps: [
          'Log into IBKR Account Management',
          'Go to Reports > Flex Queries',
          'Run your saved query (it should include: Trades, Cash Transactions, Transfers, Dividends, Open Positions)',
          'Download as XML format',
        ],
        formats: 'XML only',
      },
    },
    fields: {
      api: [
        { key: 'flex_token', label: 'Flex Token', type: 'password', placeholder: 'Enter your Flex Web Service Token' },
        { key: 'flex_query_id', label: 'Flex Query ID', type: 'text', placeholder: 'Enter your Query ID (numeric)' },
      ],
    },
  },

  meitav: {
    type: 'meitav',
    name: 'Meitav Trade',
    shortName: 'Meitav',
    category: 'brokerage',
    defaultCurrency: 'ILS',
    defaultAccountType: 'Investment',
    hasApi: false,
    supportedFormats: ['.xlsx'],
    instructions: {
      file: {
        title: 'Export from Meitav Trade',
        steps: [
          'Log into the Meitav Trade platform',
          'Go to Reports > Account Statement',
          'Export balance.xlsx for current holdings',
          'Export transactions.xlsx for transaction history',
        ],
        formats: 'Excel (.xlsx) files',
        note: 'You may need to upload balance and transactions separately.',
      },
    },
    fields: {},
  },

  bank_hapoalim: {
    type: 'bank_hapoalim',
    name: 'Bank Hapoalim',
    shortName: 'Hapoalim',
    category: 'brokerage',
    defaultCurrency: 'ILS',
    defaultAccountType: 'Investment',
    hasApi: false,
    supportedFormats: ['.xlsx'],
    instructions: {
      file: {
        title: 'Export from Bank Hapoalim',
        steps: [
          'Log into Bank Hapoalim online banking (personal.bankhapoalim.co.il)',
          'Navigate to Investments > Investment Portfolio',
          'Click on "Reports" or "Historical Transactions"',
          'IMPORTANT: Click "Customize Columns" and enable "Security Number" and "ISIN"',
          'Choose your date range',
          'Export as Excel file (Hebrew or English)',
        ],
        formats: 'Excel (.xlsx) files',
        note: 'You must enable Security Number column in export settings for proper symbol matching.',
      },
    },
    fields: {},
  },

  leumi: {
    type: 'leumi',
    name: 'Bank Leumi',
    shortName: 'Leumi',
    category: 'brokerage',
    defaultCurrency: 'ILS',
    defaultAccountType: 'Investment',
    hasApi: false,
    supportedFormats: ['.xls'],
    instructions: {
      file: {
        title: 'Export from Bank Leumi',
        steps: [
          'Log into Bank Leumi online banking (hb2.bankleumi.co.il)',
          'Navigate to Investments > Securities Portfolio',
          'Click on "Transaction History"',
          'Select your date range (up to 6 months per export)',
          'Export as Excel file (.xls)',
        ],
        formats: 'Excel (.xls) files',
        note: 'Bank Leumi exports cover up to 6 months per file. For longer history, export multiple files.',
      },
    },
    fields: {},
  },

  kraken: {
    type: 'kraken',
    name: 'Kraken',
    shortName: 'Kraken',
    category: 'crypto',
    defaultCurrency: 'USD',
    defaultAccountType: 'Crypto',
    hasApi: true,
    supportedFormats: ['.csv'],
    apiType: 'standard', // Uses api_key and api_secret
    instructions: {
      api: {
        title: 'Connect Kraken API',
        steps: [
          'Log into your Kraken account',
          'Click the profile icon (top right) > Settings > Connections & API tab',
          'Click "Create API key" to open the key configuration form',
          'Enable permissions: "Query Funds", "Query Closed Orders & Trades", and "Query Ledger Entries"',
          'Do NOT enable withdrawal or order modification permissions',
          'Click "Generate key" and confirm with 2FA if prompted',
          'Copy both the API Key and Private Key (Private Key is shown only once)',
        ],
        note: 'Keep your Private Key secret. We only need read access to import your data.',
      },
      file: {
        title: 'Export from Kraken',
        steps: [
          'Log into your Kraken account',
          'Click "History" in the left navigation bar',
          'Click "View statements" (top right), then "Export statement"',
          'Select "Ledger" as the export type',
          'Set date range to cover your full history, leave Assets on "All", change format to CSV',
          'Click "Submit", then download the CSV file when ready',
          'Upload the CSV file to Finch',
        ],
        formats: 'CSV only',
      },
    },
    fields: {
      api: [
        { key: 'api_key', label: 'API Key', type: 'text', placeholder: 'Enter your Kraken API Key' },
        { key: 'api_secret', label: 'Private Key', type: 'password', placeholder: 'Enter your Private Key' },
      ],
    },
  },

  bit2c: {
    type: 'bit2c',
    name: 'Bit2C',
    shortName: 'Bit2C',
    category: 'crypto',
    defaultCurrency: 'ILS',
    defaultAccountType: 'Crypto',
    hasApi: true,
    supportedFormats: ['.csv'],
    apiType: 'standard',
    instructions: {
      api: {
        title: 'Connect Bit2C API',
        steps: [
          'Log into your Bit2C account',
          'Go to Settings > API Keys',
          'Create a new API key',
          'Copy the API Key and Secret',
        ],
        note: 'Only enable read permissions. Never share your secret key.',
      },
      file: {
        title: 'Export from Bit2C',
        steps: [
          'Log into your Bit2C account',
          'Go to History',
          'Export your transaction history as CSV',
        ],
        formats: 'CSV only',
      },
    },
    fields: {
      api: [
        { key: 'api_key', label: 'API Key', type: 'text', placeholder: 'Enter your Bit2C API Key' },
        { key: 'api_secret', label: 'API Secret', type: 'password', placeholder: 'Enter your API Secret' },
      ],
    },
  },

  binance: {
    type: 'binance',
    name: 'Binance',
    shortName: 'Binance',
    category: 'crypto',
    defaultCurrency: 'USD',
    defaultAccountType: 'Crypto',
    hasApi: true,
    supportedFormats: ['.csv'],
    apiType: 'standard',
    instructions: {
      api: {
        title: 'Connect Binance API',
        steps: [
          'Log into your Binance account',
          'Go to Profile > API Management',
          'Create a new API key (choose "System generated")',
          'Enable only "Read" permissions',
          'Add your IP to the whitelist if required',
          'Copy the API Key and Secret Key',
        ],
        note: 'The Secret Key is only shown once. Store it securely.',
      },
      file: {
        title: 'Export from Binance',
        steps: [
          'Log into your Binance account',
          'Go to Orders > Spot Order > Trade History',
          'Click Export and select your date range',
          'Download as CSV',
        ],
        formats: 'CSV only',
      },
    },
    fields: {
      api: [
        { key: 'api_key', label: 'API Key', type: 'text', placeholder: 'Enter your Binance API Key' },
        { key: 'api_secret', label: 'Secret Key', type: 'password', placeholder: 'Enter your Secret Key' },
      ],
    },
  },

  kucoin: {
    type: 'kucoin',
    name: 'KuCoin',
    shortName: 'KuCoin',
    category: 'crypto',
    defaultCurrency: 'USD',
    defaultAccountType: 'Crypto',
    hasApi: true,
    supportsSmartOnboarding: true,
    supportedFormats: ['.csv'],
    apiType: 'passphrase',
    instructions: {
      api: {
        title: 'Connect KuCoin API',
        steps: [
          'Log into your KuCoin account',
          'Click your avatar (top right) > API Management',
          'Click "Create API"',
          'Choose a name and set a passphrase -- save it somewhere safe',
          'Enable "General" permission only (no Trading or Withdrawal needed)',
          'Complete 2FA verification',
          'Copy your API Key, Secret, and the passphrase you set',
        ],
        note: 'KuCoin retains ~6 months of trade history via API. For older accounts we create a snapshot of your current positions -- you can upload a full CSV export later.',
      },
      file: {
        title: 'Export from KuCoin',
        steps: [
          'Log into your KuCoin account',
          'Go to Orders > Spot Orders > Trade History',
          'Click "Export" and select your date range',
          'Repeat for Deposit History under Assets > Deposit',
          'Download each file as CSV',
        ],
        formats: 'CSV only',
      },
    },
    fields: {
      api: [
        { key: 'api_key', label: 'API Key', type: 'text', placeholder: 'Enter your KuCoin API Key' },
        { key: 'api_secret', label: 'API Secret', type: 'password', placeholder: 'Enter your API Secret' },
        { key: 'api_passphrase', label: 'API Passphrase', type: 'password', placeholder: 'Enter the passphrase you set when creating the key' },
      ],
    },
  },
};

/**
 * Get brokers filtered by category
 */
export function getBrokersByCategory(category) {
  return Object.values(BROKERS).filter((broker) => broker.category === category);
}

/**
 * Get broker config by type
 */
export function getBrokerConfig(brokerType) {
  return BROKERS[brokerType] || null;
}

/**
 * Get initial credentials object for a broker
 */
export function getInitialCredentials(brokerType) {
  const broker = BROKERS[brokerType];
  if (!broker?.fields?.api) return {};

  return broker.fields.api.reduce((acc, field) => {
    acc[field.key] = '';
    return acc;
  }, {});
}
