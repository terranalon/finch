export const ibkrGuide = {
  api: {
    title: 'Connect IBKR Flex Query',
    overview:
      'Connect your Interactive Brokers account to automatically import your trades, dividends, transfers, forex, cash transactions, and positions via the IBKR Flex Web Service. New activity is synced periodically.',
    estimatedTime: '10 minutes',
    prerequisites: [
      'A funded IBKR account with Client Portal access',
      'Access to Account Management at secure.interactivebrokers.com (not TWS)',
    ],
    steps: [
      {
        title: 'Log into IBKR Account Management',
        description:
          'Log into the IBKR Client Portal / Account Management at secure.interactivebrokers.com. The Flex settings live there, not in Trader Workstation (TWS).',
      },
      {
        title: 'Open the API Settings',
        description:
          'Navigate to Settings > User Settings > API. This is where the Flex Web Service is configured.',
      },
      {
        title: 'Generate a Flex Web Service Token',
        description:
          'Generate a Flex Web Service Token and copy it somewhere safe -- you will paste it into Finch below.',
        tip: 'The token expires after 60 days. Set a renewal reminder so your sync does not silently stop.',
      },
      {
        title: 'Open Custom Flex Queries',
        description:
          'Navigate to Reports > Flex Queries > Custom Flex Queries. Finch reads your data through an Activity Flex Query that you define here.',
      },
      {
        title: 'Create an Activity Flex Query',
        description:
          'Create a new Activity Flex Query and enable exactly these sections:',
        checklist: [
          { label: 'Open Positions', required: true },
          { label: 'Trades', required: true },
          { label: 'Cash Transactions', required: true },
          { label: 'Transfers', required: true },
          { label: 'Dividends', required: true },
          { label: 'Forex Trades', required: true },
          { label: 'Cash Report', required: true },
          { label: 'Account Information -- check only "Date Opened"', required: true },
        ],
        tip: 'Under Account Information, check only "Date Opened" -- Finch uses it to determine how much history to import automatically. No other personal information is requested.',
      },
      {
        title: 'Save the Query and Copy the Query ID',
        description:
          'Save the query, then copy the Query ID shown next to it in the query list.',
      },
      {
        title: 'Enter Token and Query ID in Finch',
        description:
          'Paste your Flex Token and Flex Query ID into the fields below, then click "Test Connection" to verify everything works.',
      },
    ],
    security: {
      recommended: [
        'The Flex Token is read-only -- it cannot execute trades or withdraw funds',
        'Set a reminder to renew the token before its 60-day expiry',
      ],
      avoid: [
        'Sharing your Flex Token with anyone',
        'Adding extra Account Information fields to the query -- only "Date Opened" is needed',
      ],
      note: 'We store your credentials encrypted. Finch only uses the token to read the Flex Query you created, and you can revoke it at any time from the IBKR API settings.',
    },
    dataScope: [
      { type: 'Trades', included: true, note: 'Buy and sell orders, all asset types' },
      { type: 'Dividends', included: true, note: 'Cash and stock dividends' },
      { type: 'Transfers', included: true, note: 'In/out transfers' },
      { type: 'Forex', included: true, note: 'Currency conversions' },
      { type: 'Cash Transactions', included: true, note: 'Deposits, withdrawals, fees' },
      { type: 'Open Positions', included: true, note: 'Current holdings snapshot' },
    ],
    limitations: [
      'The Flex API has a hard 365-day lookback limit -- use file upload for older history',
      'The Flex Token must be renewed every 60 days',
    ],
    troubleshooting: [
      {
        problem: '"Invalid token" error',
        solution:
          'Your Flex Token has most likely expired (tokens last 60 days). Generate a new token under Settings > User Settings > API and update it in Finch.',
      },
      {
        problem: '"Missing sections" error',
        solution:
          'Your Flex Query does not include all required sections. Edit the query and enable Open Positions, Trades, Cash Transactions, Transfers, Dividends, Forex Trades, Cash Report, and Account Information (Date Opened only).',
      },
      {
        problem: 'Empty import',
        solution:
          'The query date range may not cover any activity. Check the date range configured on your Flex Query and run an import again.',
      },
    ],
    afterSetup:
      'Once connected, Finch will automatically sync new transactions from IBKR. Remember to renew your Flex Token every 60 days so syncing continues.',
  },

  file: {
    title: 'Export from IBKR',
    overview:
      'Import your IBKR history from an exported Flex Query XML file. This imports the same data as the API connection and is the way to bring in history older than the API\'s 365-day lookback limit.',
    estimatedTime: '5 minutes',
    prerequisites: [
      'An IBKR account with transaction history',
      'A saved Activity Flex Query with the required sections (see the API connection guide)',
    ],
    steps: [
      {
        title: 'Log into IBKR Account Management',
        description:
          'Log into IBKR Account Management at secure.interactivebrokers.com.',
      },
      {
        title: 'Open Flex Queries',
        description: 'Go to Reports > Flex Queries to see your saved queries.',
      },
      {
        title: 'Run Your Saved Query',
        description:
          'Run your saved Activity Flex Query with the date range you want to import. Make sure the query includes all required sections: Open Positions, Trades, Cash Transactions, Transfers, Dividends, Forex Trades, Cash Report, and Account Information (Date Opened only).',
        tip: 'For a first import, choose the widest date range available so your full history comes across.',
      },
      {
        title: 'Download as XML',
        description: 'Download the query result in XML format.',
        tip: 'Finch accepts XML only -- a CSV or PDF export cannot be imported.',
      },
      {
        title: 'Upload the XML File in Finch',
        description:
          'Switch to the "Upload File" tab in Finch and drag the downloaded XML file into the upload area, or click to browse for it.',
      },
    ],
    dataScope: [
      { type: 'Trades', included: true, note: 'Buy and sell orders, all asset types' },
      { type: 'Dividends', included: true, note: 'Cash and stock dividends' },
      { type: 'Transfers', included: true, note: 'In/out transfers' },
      { type: 'Forex', included: true, note: 'Currency conversions' },
      { type: 'Cash Transactions', included: true, note: 'Deposits, withdrawals, fees' },
      { type: 'Open Positions', included: true, note: 'Current holdings snapshot' },
    ],
    limitations: [
      'File must be the Flex Query XML export (not CSV or PDF)',
      'Only the sections enabled on the saved query are included in the export',
    ],
    troubleshooting: [
      {
        problem: 'Wrong file format',
        solution:
          'The export must be XML. If you downloaded a CSV or PDF, run the query again and choose the XML format when downloading.',
      },
      {
        problem: 'Partial data after import',
        solution:
          'Your Flex Query is missing some required sections. Edit the query to include all required sections, re-run it, and upload the new XML file.',
      },
    ],
  },
};
