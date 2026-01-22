# Binance Integration

## Overview

Binance is the world's largest cryptocurrency exchange by trading volume. It offers trading for thousands of cryptocurrency pairs across spot, futures, and margin markets. This integration focuses on spot trading.

**Supported Data:**
- Account balances (all crypto assets)
- Trade history (spot trades)
- Deposit records
- Withdrawal records
- Distribution history (staking rewards, airdrops)

**Import Methods:**
- CSV file upload (recommended for one-time imports)
- API connection (for automated syncing)

## File Export Instructions (Recommended)

### Step 1: Access Export

1. Log into your Binance account at [binance.com](https://www.binance.com)
2. Click your **Profile** icon in the top-right corner
3. Navigate to **Orders** > **Spot Order**

### Step 2: Export Trade History

1. Click **Trade History** > **Export Trade History**
2. Select your desired date range (up to 1 year, starting from 2017-07-13)
3. Click **Generate** (limited to 5 exports per month)
4. Wait for processing, then click **Download**

**Note:** Download links expire after 7 days.

### Step 3: Export Deposits/Withdrawals

1. Navigate to **Wallet** > **Transaction History**
2. Select the transaction type (Deposit or Withdrawal)
3. Set your date range
4. Click **Export**

### Step 4: Import to Portfolio Tracker

1. In Portfolio Tracker, go to **Import** > **Upload File**
2. Select **Binance** as the broker
3. Upload your CSV file(s)
4. Review the imported transactions and confirm

### Export Limitations

| Limit | Value |
|-------|-------|
| Max rows per export | 10,000 |
| Max date range | 6 months |
| Max exports per month | 5 |
| Link expiration | 7 days |

---

## API Connection (Alternative)

### Step 1: Generate API Key

1. Log into your Binance account
2. Go to **Profile** > **API Management**
3. Click **Create API**
4. Choose **System generated** for the key type
5. Complete 2FA verification
6. **Important:** Save your API Key and Secret securely. The secret is only shown once.

### Step 2: Configure API Permissions

For portfolio tracking, you only need:
- ✅ **Enable Reading** - Required for fetching balances and history
- ❌ **Enable Spot & Margin Trading** - Not needed
- ❌ **Enable Withdrawals** - Not needed

**Security Tip:** Restrict the API key to your IP address under "IP Access Restrictions".

### Step 3: Connect in Portfolio Tracker

1. Go to **Settings** > **Integrations** > **Binance**
2. Enter your API Key
3. Enter your API Secret
4. Click **Connect**
5. The app will verify the connection and import your data

### API Security Notes

- Use read-only permissions whenever possible
- Enable IP whitelist restrictions
- Never share your API secret
- Rotate keys periodically
- Monitor for unauthorized access

---

## Supported CSV Formats

### Trade History Format

| Column | Description | Example |
|--------|-------------|---------|
| `Date(UTC)` | Trade timestamp | `2024-01-15 10:30:00` |
| `Pair` | Trading pair | `BTCUSDT` |
| `Side` | Trade direction | `BUY` or `SELL` |
| `Price` | Execution price | `42000.00` |
| `Executed` | Quantity traded | `0.5` |
| `Amount` | Total value | `21000.00` |
| `Fee` | Trading fee | `10.50` |

### Transaction History Format

| Column | Description | Example |
|--------|-------------|---------|
| `Date(UTC)` | Transaction timestamp | `2024-01-10 08:00:00` |
| `Operation` | Transaction type | `Deposit` or `Withdraw` |
| `Coin` | Asset | `BTC` |
| `Amount` | Quantity | `0.5` |
| `TxId` | Blockchain transaction ID | `abc123...` |

### Distribution History Format

| Column | Description | Example |
|--------|-------------|---------|
| `Date(UTC)` | Distribution timestamp | `2024-01-20 00:00:00` |
| `Coin` | Asset | `ETH` |
| `Amount` | Quantity | `0.001` |
| `Distribution Type` | Type of distribution | `Staking Rewards` |

---

## Data Mapping

### Symbol Parsing

Binance uses concatenated symbols without delimiters:

| Binance Symbol | Base Asset | Quote Asset |
|----------------|------------|-------------|
| `BTCUSDT` | BTC | USDT |
| `ETHBTC` | ETH | BTC |
| `DOGEUSDC` | DOGE | USDC |
| `BNBBUSD` | BNB | BUSD |

### Transaction Types

| Binance Action | Portfolio Tracker Type |
|----------------|----------------------|
| BUY | Buy |
| SELL | Sell |
| Deposit | Deposit |
| Withdraw | Withdrawal |
| Staking Rewards | Distribution |
| Airdrop | Distribution |

### Quote Assets Supported

- USDT (Tether)
- BUSD (Binance USD)
- USDC (USD Coin)
- USD
- BTC
- ETH
- BNB
- EUR
- GBP

---

## API Details

### Base URL
`https://api.binance.com`

### Authentication
HMAC-SHA256 with timestamp-based signing (no nonce required)

### Endpoints Used

| Endpoint | Purpose | Weight |
|----------|---------|--------|
| `GET /api/v3/account` | Fetch balances | 20 |
| `GET /api/v3/myTrades` | Trade history (per symbol) | 20 |
| `GET /sapi/v1/capital/deposit/hisrec` | Deposit history | 1 |
| `GET /sapi/v1/capital/withdraw/history` | Withdrawal history | 1 |

### Rate Limits

| Limit Type | Value |
|------------|-------|
| Request Weight | 1200/minute per IP |
| Order Rate | 10/second, 100,000/day |

The client automatically tracks weight usage and sleeps when approaching limits.

---

## Troubleshooting

### API Connection Failed

- Verify API key and secret are correct (no extra spaces)
- Check that "Enable Reading" permission is enabled
- If using IP restriction, ensure your IP is whitelisted
- API keys may be auto-disabled after 90 days of inactivity

### Invalid Signature Error

- Ensure your system clock is synchronized
- The timestamp must be within 5 seconds of Binance's server time
- Check that the API secret is entered correctly

### Missing Trades

- Trade history requires querying each trading pair separately
- Only symbols with non-zero balances are queried by default
- For historical trades in assets you no longer hold, use CSV export

### Rate Limit Exceeded (429)

- The client automatically handles rate limiting
- If you see 429 errors, wait 1 minute before retrying
- Repeated violations may result in temporary IP ban (418)

### CSV Import Issues

- Ensure the file is in UTF-8 encoding
- Check that column headers match expected format
- Date format should be `YYYY-MM-DD HH:MM:SS`

---

## Comparison with Other Exchanges

| Feature | Binance | Kraken | Bit2C |
|---------|---------|--------|-------|
| Symbol Format | Concatenated (BTCUSDT) | X/Z prefix (XXBTZUSD) | Pairs (BtcNis) |
| Auth Method | HMAC-SHA256 + timestamp | HMAC-SHA512 + nonce | HMAC-SHA512 + custom nonce |
| Trade History | Per-symbol query | All trades at once | All trades at once |
| Rate Limiting | Weight-based | Call count | Not documented |
| File Format | CSV | CSV | XLSX |

---

## Support

If you encounter issues with Binance import:
1. Check the troubleshooting section above
2. Verify your API credentials and permissions
3. Try exporting data as CSV for comparison
4. Contact support with your error message
