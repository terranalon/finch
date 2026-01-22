# Kraken Integration

## Overview

Kraken is a US-based cryptocurrency exchange founded in 2011. This integration supports importing your trading history, deposits, withdrawals, and staking rewards.

**Supported Data:**
- Account balances (spot holdings)
- Trade history
- Deposits and withdrawals
- Staking rewards
- Transfer and adjustment records

**Import Methods:**
- CSV file upload (Ledger export)
- API connection (optional)

## File Export Instructions

### Step 1: Access History Export

1. Log into your Kraken account at [kraken.com](https://www.kraken.com)
2. Click on your account icon in the top-right corner
3. Navigate to **History** > **Export**

### Step 2: Configure Export

1. Select **Ledgers** as the export type
2. Set your desired date range:
   - **Start Date**: The earliest date you want to include
   - **End Date**: Today or your desired end date
3. Under **Assets**, leave "All" selected (or choose specific assets)
4. Under **Fields**, leave "All" selected
5. Under **Format**, select **CSV**

### Step 3: Download

1. Click **Generate** to create the export
2. Wait for the status to change from "Queued" to "Processed"
3. Click **Download** to save the ZIP file
4. Extract the ZIP file to get the `ledgers.csv` file

### Step 4: Import to Portfolio Tracker

1. In Portfolio Tracker, go to **Import** > **Upload File**
2. Select **Kraken** as the broker
3. Upload your `ledgers.csv` file
4. Review the imported transactions and confirm

## API Connection (Optional)

For automatic syncing, you can connect your Kraken account via API.

### Step 1: Generate API Key

1. Log into Kraken
2. Go to **Settings** > **API**
3. Click **Generate new key**
4. Give it a name (e.g., "Portfolio Tracker")
5. Set permissions:
   - **Query Funds** - Required
   - **Query Ledger Entries** - Required
   - **Query Orders & Trades** - Required
   - Leave all other permissions disabled
6. Click **Generate key**
7. **Important:** Save your API Key and Private Key securely. The private key is only shown once.

### Step 2: Connect in Portfolio Tracker

1. Go to **Settings** > **Integrations** > **Kraken**
2. Enter your API Key
3. Enter your Private Key
4. Click **Connect**
5. The app will verify the connection and import your data

### API Security Notes

- Only grant read-only permissions (Query, not Trade/Withdraw)
- Never share your private key
- You can revoke API keys at any time from Kraken

## Data Mapping

### Transaction Types

| Kraken Type | Portfolio Tracker Type |
|-------------|----------------------|
| deposit | Deposit |
| withdrawal | Withdrawal |
| trade (buy) | Buy |
| trade (sell) | Sell |
| staking | Staking Reward |
| transfer | Transfer |
| adjustment | Adjustment |

### Asset Names

Kraken uses non-standard asset names that are automatically converted:

| Kraken Name | Standard Name |
|-------------|--------------|
| XXBT / XBT | BTC |
| XETH | ETH |
| ZUSD | USD |
| ZEUR | EUR |
| XXRP | XRP |
| XXLM | XLM |

Staked assets (e.g., `XXBT.S`) are mapped to their base asset (`BTC`).

## Troubleshooting

### "Empty CSV file" Error

- Ensure you selected "Ledgers" as the export type
- Check that the date range includes transactions
- Verify the file is the CSV from inside the ZIP, not the ZIP itself

### Missing Transactions

- Kraken exports are paginated. If you have a large history, ensure you selected a date range that includes all desired transactions
- Try exporting in smaller date chunks if needed

### API Connection Failed

- Double-check your API key and secret are correct
- Ensure the API key has the required permissions
- Check that the API key hasn't expired or been revoked
- Kraken may rate-limit API connections; wait a few minutes and try again

### Duplicate Transactions

The import process automatically detects and skips duplicate transactions based on:
- Transaction ID (txid)
- Reference ID (refid)
- Date and amount combination

## Limitations

- **Margin trading:** Margin trades are recorded but may require manual review
- **Cost basis:** Kraken doesn't provide original cost basis; it's calculated from trade history
- **Real-time sync:** API sync is performed on-demand, not in real-time
- **Historical limits:** Very old transactions may not be available via API

## Support

If you encounter issues with Kraken import:
1. Check the troubleshooting section above
2. Verify your export file format
3. Contact support with your error message
