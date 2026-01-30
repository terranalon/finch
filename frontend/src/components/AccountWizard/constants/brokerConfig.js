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
          'Create a new query with sections: Trades, Cash Transactions, Transfers, Dividends',
          'Copy the Query ID from the query list',
        ],
        note: 'Your Flex Token expires after 60 days. You can regenerate it anytime in Account Management.',
      },
      file: {
        title: 'Export from IBKR',
        steps: [
          'Log into IBKR Account Management',
          'Go to Reports > Flex Queries',
          'Run your saved query (or create one with Trades, Cash, Transfers sections)',
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
          'Go to Security > API',
          'Click "Create New Key"',
          'Enable permissions: "Query Ledger Entries" and "Query Trades History"',
          'Do NOT enable withdrawal permissions for safety',
          'Copy both the API Key and Private Key',
        ],
        note: 'Keep your Private Key secret. We only need read access to import your data.',
      },
      file: {
        title: 'Export from Kraken',
        steps: [
          'Log into your Kraken account',
          'Go to History > Export',
          'Select "Ledgers" as the export type',
          'Choose your date range',
          'Download as CSV',
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
