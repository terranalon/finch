/**
 * Rich setup guide content for Kraken.
 * Covers both API connection and CSV file upload.
 */

export const krakenGuide = {
  api: {
    title: 'Connect Kraken API',
    overview:
      'Connect your Kraken account to automatically import your trades, deposits, withdrawals, and staking rewards. New transactions are synced periodically.',
    estimatedTime: '5 minutes',
    prerequisites: [
      'A verified Kraken account',
      '2FA enabled (recommended for API key creation)',
    ],
    steps: [
      {
        title: 'Open Settings',
        description:
          'Log into your Kraken account. Click the profile icon in the top-right corner, then select "Settings" from the dropdown menu.',
        screenshot: '/guides/kraken/api/home_with_settings.png',
      },
      {
        title: 'Go to Connections & API',
        description:
          'On the Settings page, click the "Connections & API" tab in the top navigation bar.',
        screenshot: '/guides/kraken/api/settings.png',
      },
      {
        title: 'Create a New API Key',
        description:
          'Click the purple "Create API key" button on the right side of the Spot trading API section.',
        screenshot: '/guides/kraken/api/connections_and_apis.png',
      },
      {
        title: 'Name Your Key',
        description:
          'In the "Add API key" dialog, enter a descriptive name such as "Finch Portfolio Tracker". This helps you identify the key later.',
        screenshot: '/guides/kraken/api/add_api_key.png',
      },
      {
        title: 'Set Permissions',
        description:
          'Enable only the read permissions needed for portfolio tracking. The permissions are organized in three columns:',
        screenshot: '/guides/kraken/api/add_api_key_example.png',
        checklist: [
          { label: 'Query (under Funds permissions)', required: true },
          { label: 'Query closed orders & trades (under Orders and trades)', required: true },
          { label: 'Query ledger entries (under Data)', required: true },
          { label: 'Export data (under Data)', required: false },
        ],
        tip: 'Never enable "Withdraw", "Create & modify orders", or "Deposit" permissions. Finch only needs read access to import your data.',
      },
      {
        title: 'Confirm with 2FA',
        description:
          'Click "Generate key" at the bottom of the dialog. If you have 2FA enabled, you will be asked to verify with your passkey or authenticator app.',
        screenshot: '/guides/kraken/api/add_api_key_step_2.png',
        optional: true,
      },
      {
        title: 'Copy Your Credentials',
        description:
          'Your API key has been created. Copy both the API Key and the Private Key using the copy buttons. The Private Key is only shown once -- save it immediately.',
        screenshot: '/guides/kraken/api/api_key_final_step.png',
        tip: 'Store your Private Key in a password manager. If you lose it, you will need to create a new key.',
      },
      {
        title: 'Enter Credentials in Finch',
        description:
          'Paste your API Key and Private Key into the fields below, then click "Test Connection" to verify everything works.',
        screenshot: null,
      },
    ],
    security: {
      recommended: [
        'Enable only read permissions (Query Funds, Query Closed Orders & Trades, Query Ledger Entries)',
        'Use a unique API key for Finch -- do not reuse keys from other services',
      ],
      avoid: [
        'Withdraw Funds permission',
        'Create & Modify Orders permission',
        'Sharing your Private Key with anyone',
      ],
      note: 'Your credentials are encrypted and stored securely. Finch only uses read-only access to import your data. You can revoke the key at any time from Kraken.',
    },
    dataScope: [
      { type: 'Trades', included: true, note: 'Buy and sell orders across all trading pairs' },
      { type: 'Deposits', included: true, note: 'Crypto and fiat deposits' },
      { type: 'Withdrawals', included: true, note: 'Crypto and fiat withdrawals' },
      { type: 'Staking Rewards', included: true, note: 'Imported via ledger entries' },
      { type: 'Internal Transfers', included: true, note: 'Between Kraken sub-accounts' },
      { type: 'Margin / Futures', included: false, note: 'Only spot trading is supported' },
    ],
    limitations: [
      'Only spot trading data is imported (no margin or futures)',
      'API rate limit: ~15 requests per minute',
    ],
    troubleshooting: [
      {
        problem: '"Invalid key" or "Permission denied" error',
        solution:
          'Check that you copied the full API Key and Private Key without leading/trailing spaces. Ensure "Query Funds", "Query Closed Orders & Trades", and "Query Ledger Entries" permissions are all enabled.',
      },
      {
        problem: 'Missing staking rewards',
        solution:
          'Staking rewards appear as ledger entries, not trades. Ensure "Query Ledger Entries" is enabled on your API key.',
      },
      {
        problem: 'Connection times out',
        solution:
          'Kraken may be experiencing high traffic. Wait a few minutes and try again.',
      },
    ],
    afterSetup:
      'Once connected, Finch will automatically sync new transactions from Kraken. You can trigger a manual sync from your account settings at any time.',
  },

  file: {
    title: 'Export from Kraken',
    overview:
      'Import your Kraken transaction history from a CSV export. This is useful for a one-time import or for importing historical data.',
    estimatedTime: '3 minutes',
    prerequisites: [
      'A Kraken account with transaction history',
      'Access to the Kraken Pro interface',
    ],
    steps: [
      {
        title: 'Open History',
        description:
          'Log into your Kraken account. Click "History" in the left navigation bar to view your transaction history.',
        screenshot: '/guides/kraken/file/history.png',
      },
      {
        title: 'View Statements',
        description:
          'On the History page, click the "View statements" link in the top-right corner. This opens the Statements page where you can export data.',
        screenshot: '/guides/kraken/file/history.png',
      },
      {
        title: 'Export Statement',
        description:
          'Click the purple "Export statement" button in the top-right corner of the Statements page.',
        screenshot: '/guides/kraken/file/statements.png',
      },
      {
        title: 'Select Ledger Export',
        description:
          'In the "Export statement" dialog, select "Ledger" from the dropdown menu.',
        screenshot: '/guides/kraken/file/export_statement_step_1.png',
        tip: 'Choose "Ledger" (not "Trades" or "Account Statement"). The ledger includes all transaction types: trades, deposits, withdrawals, and staking rewards.',
      },
      {
        title: 'Configure Export',
        description:
          'Set the start date to the date you created your Kraken account -- we need your entire transaction history for accurate portfolio tracking. Leave Transaction types, Assets, and Fields on "All". Important: change the Format from PDF to CSV.',
        screenshot: '/guides/kraken/file/export_statement_pick_format.png',
        tip: 'The default format is PDF -- make sure to switch it to CSV before submitting. If you are unsure when you opened your account, set the start date as far back as possible.',
      },
      {
        title: 'Download the Export',
        description:
          'Click "Submit" and wait for the export to generate. Once ready, it will appear under "On-demand statements" with a download icon. Click the download icon to save the CSV file.',
        screenshot: '/guides/kraken/file/export_statement_ready_to_download.png',
      },
      {
        title: 'Upload to Finch',
        description:
          'Switch to the "Upload File" tab in Finch and drag the downloaded CSV file into the upload area, or click to browse for it.',
        screenshot: null,
      },
    ],
    dataScope: [
      { type: 'Trades', included: true, note: 'Buy and sell orders' },
      { type: 'Deposits', included: true, note: 'Crypto and fiat' },
      { type: 'Withdrawals', included: true, note: 'Crypto and fiat' },
      { type: 'Staking Rewards', included: true, note: 'Included in ledger exports' },
      { type: 'Internal Transfers', included: true, note: 'Between sub-accounts' },
    ],
    limitations: [
      'File must be the original Kraken CSV export (not modified)',
      'Large exports may take a few minutes to generate on Kraken',
    ],
    troubleshooting: [
      {
        problem: '"Unsupported file format" error',
        solution:
          'Make sure you exported as CSV (not the default PDF). If you already exported as PDF, create a new export and change the format to CSV.',
      },
      {
        problem: 'Wrong export type selected',
        solution:
          'Use "Ledger" export, not "Trades" or "Account Statement". The ledger format includes all transaction types that Finch needs.',
      },
      {
        problem: 'Missing transactions in import',
        solution:
          'Check the date range of your export. If it does not cover your full history, create a new export with a wider range.',
      },
    ],
  },
};
