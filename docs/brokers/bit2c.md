# Bit2C Integration

## Overview

Bit2C is Israel's first and largest cryptocurrency exchange, founded in 2012. It allows trading of Bitcoin, Ethereum, Litecoin, and USDC against Israeli Shekel (NIS). Bit2C is licensed and regulated by the Israel Securities Authority (ISA).

**Supported Data:**
- Account balances (BTC, ETH, LTC, USDC, NIS)
- Trade history
- Deposit and withdrawal records

**Import Methods:**
- XLSX file upload (recommended)
- API connection

## File Export Instructions (Recommended)

### Step 1: Access Export

1. Log into your Bit2C account at [bit2c.co.il](https://bit2c.co.il)
2. Navigate to **History** (היסטוריה) > **Transactions** (פעולות)
3. Select your desired date range

### Step 2: Download Report

1. Click **Export** to download your transaction history
2. The file will be downloaded as an XLSX file
3. Files are available in both English and Hebrew - both are supported

### Step 3: Import to Portfolio Tracker

1. In Portfolio Tracker, go to **Import** > **Upload File**
2. Select **Bit2C** as the broker
3. Upload your XLSX file
4. Review the imported transactions and confirm

### Supported Transaction Types

The file parser handles all Bit2C transaction types:
- **Buy/Sell** (קניה/מכירה) - Crypto trades
- **Deposit** (הפקדה) - NIS or crypto deposits
- **Withdrawal** (משיכה) - NIS or crypto withdrawals
- **Fee** (עמלה) - Custody and platform fees
- **FeeWithdrawal** (עמלת משיכה) - Withdrawal fees
- **Credit** (זיכוי) - Account credits

---

## API Connection (Alternative)

### Step 1: Generate API Key

1. Log into your Bit2C account at [bit2c.co.il](https://bit2c.co.il)
2. Go to **API** tab in your account settings
3. Click **Generate new key**
4. **Important:** Save your API Key and Secret securely. The secret is only shown once.

### Step 2: Connect in Portfolio Tracker

1. Go to **Settings** > **Integrations** > **Bit2C**
2. Enter your API Key
3. Enter your API Secret
4. Click **Connect**
5. The app will verify the connection and import your data

### API Security Notes

- API keys grant access to your account - keep them secure
- Only use the API key for this application
- You can revoke API keys at any time from Bit2C

## Trading Pairs

Bit2C supports the following trading pairs:

| Pair | Description |
|------|-------------|
| BtcNis | Bitcoin / Israeli Shekel |
| EthNis | Ethereum / Israeli Shekel |
| LtcNis | Litecoin / Israeli Shekel |
| UsdcNis | USDC / Israeli Shekel |

## Data Mapping

### Transaction Types

| Bit2C Action | Portfolio Tracker Type |
|--------------|----------------------|
| action: 0 | Buy |
| action: 1 | Sell |

### Asset Names

| Bit2C Name | Standard Name |
|------------|--------------|
| NIS | ILS (Israeli Shekel) |
| BTC | BTC |
| ETH | ETH |
| LTC | LTC |
| USDC | USDC |

## Currency Notes

- All trading on Bit2C is against Israeli Shekel (ILS)
- Fees are denominated in NIS (feeNis field)
- Prices are in NIS per unit of crypto

## Troubleshooting

### API Connection Failed

- Double-check your API key and secret are correct
- Ensure the API key hasn't expired or been revoked
- Verify you're copying the complete key (no spaces)

### Missing Transactions

- Bit2C API returns trade history based on date range
- Ensure your date range covers all desired transactions
- Very old transactions may require multiple queries

### Authentication Error

- API secrets must be used exactly as provided
- The signature is case-sensitive
- Ensure your system clock is accurate (affects nonce)

### Rate Limiting

- Bit2C may rate-limit frequent API requests
- If you receive errors, wait a few minutes before retrying
- The integration automatically handles reasonable request pacing

## Limitations

- **Deposits/Withdrawals:** May not be available via API
- **Cost basis:** Calculated from trade history
- **Real-time sync:** API sync is performed on-demand
- **Israeli market hours:** Trading is available 24/7

## About Bit2C

Bit2C was one of the world's first 10 bitcoin trading sites. It's the first company in Israel to develop an exchange platform supporting Hebrew, Arabic, English, and Russian languages.

The platform requires:
- Identity verification
- Connection to an Israeli bank account

Bit2C claims all coins are kept in cold storage and user funds are held separately from company operating funds.

## Support

If you encounter issues with Bit2C import:
1. Check the troubleshooting section above
2. Verify your API credentials are valid
3. Contact support with your error message
