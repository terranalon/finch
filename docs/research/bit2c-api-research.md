# Bit2C API Research

**Date:** 2026-01-20
**Purpose:** Research Bit2C API for portfolio tracker integration

## API Overview

Bit2C is an Israeli cryptocurrency exchange founded in 2012, offering trading in BTC, ETH, LTC, and USDC against Israeli Shekel (NIS). Licensed and regulated by the Israel Securities Authority (ISA).

**API Base URL:** `https://bit2c.co.il`

## Authentication

### Method: HMAC-SHA512

Bit2C uses HMAC-SHA512 signing for authenticated requests.

### Signature Generation

```
signature = base64(HMAC-SHA512(params_string, secret.toUpperCase()))
```

#### Steps:
1. Convert API secret to uppercase
2. Create URL-encoded parameter string including nonce
3. Generate HMAC-SHA512 hash using uppercase secret
4. Base64 encode the result

### Required Headers (Private Endpoints)

| Header | Value |
|--------|-------|
| `Content-Type` | `application/x-www-form-urlencoded` |
| `key` | API key |
| `sign` | Base64-encoded HMAC-SHA512 signature |

### Nonce Format

Bit2C uses a custom timestamp-based nonce:
```javascript
nonce = parseInt(((new Date()).getTime() - 1389729146519) / 250, 10)
```

This calculates time in 250ms intervals since January 14, 2014. The nonce must always increase.

## Trading Pairs

| Pair | Description |
|------|-------------|
| BtcNis | Bitcoin / Israeli Shekel |
| EthNis | Ethereum / Israeli Shekel |
| LtcNis | Litecoin / Israeli Shekel |
| UsdcNis | USDC / Israeli Shekel |

## Endpoints

### Public Endpoints (No Auth Required)

#### Get Ticker
**Endpoint:** `GET /Exchanges/{pair}/Ticker.json`

**Response:**
```json
{
  "h": 123456.78,    // High
  "l": 123000.00,    // Low
  "ll": 122000.00,   // Last price
  "av": 10.5,        // Volume
  "a": 123500.00     // Ask
}
```

#### Get Order Book
**Endpoint:** `GET /Exchanges/{pair}/orderbook.json`

Cached 1 second. Returns full bids and asks lists.

#### Get Order Book Top
**Endpoint:** `GET /Exchanges/{pair}/orderbook-top.json`

#### Get Last 24h Trades
**Endpoint:** `GET /Exchanges/{pair}/lasttrades`

#### Get All Trades
**Endpoint:** `GET /Exchanges/{pair}/trades.json`

Cached 5 minutes.

### Private Endpoints (Auth Required)

#### Get Balance
**Endpoint:** `GET /Account/Balance`

**Permission Required:** Balance read access

**Response:**
```json
{
  "AVAILABLE_NIS": 1000.00,
  "NIS": 1000.00,
  "AVAILABLE_BTC": 0.5,
  "BTC": 0.5,
  "AVAILABLE_ETH": 2.0,
  "ETH": 2.0,
  "AVAILABLE_LTC": 5.0,
  "LTC": 5.0,
  "AVAILABLE_USDC": 100.0,
  "USDC": 100.0,
  "Fees": {
    "BtcNis": { "FeeMaker": 0.5, "FeeTaker": 0.5 },
    "EthNis": { "FeeMaker": 0.5, "FeeTaker": 0.5 }
  }
}
```

#### Get My Orders
**Endpoint:** `GET /Order/MyOrders?pair={pair}`

Returns open orders for the specified pair.

#### Get Order by ID
**Endpoint:** `GET /Order/GetById?id={orderId}`

#### Get Account History
**Endpoint:** `GET /Order/AccountHistory`

**Parameters:**
- `fromTime` - Start time (format: "dd/MM/yyyy HH:mm:ss.fff")
- `toTime` - End time (format: "dd/MM/yyyy HH:mm:ss.fff")

**⚠️ NOTE:** This endpoint returns empty results for most accounts. Use `FundsHistory` instead for deposits/withdrawals.

#### Get Funds History (UNDOCUMENTED - Critical for Deposits/Withdrawals)
**Endpoint:** `GET /AccountAPI/FundsHistory.json`

**⚠️ IMPORTANT:** This endpoint is NOT documented in the official Bit2C API docs but is essential for fetching deposit and withdrawal history. Discovered via third-party C# client: https://github.com/macdasi/Bit2C.ApiClient

**Parameters:**
- `nonce` - Required nonce for authentication

**Response:** Array of fund movement records

**Response Fields:**
```json
[
  {
    "ticks": 1734339780,
    "created": "16/12/24 07:03",
    "action": 2,
    "price": "",
    "pair": "",
    "reference": "MH_NIS_125704",
    "fee": "",
    "feeAmount": "",
    "feeCoin": "",
    "firstAmount": "15,000",
    "firstAmountBalance": "15,000",
    "secondAmount": "",
    "secondAmountBalance": "",
    "firstCoin": "₪",
    "secondCoin": "",
    "isMaker": null,
    "AddressLabel": ""
  }
]
```

**Action Types:**
| Value | Type | Description |
|-------|------|-------------|
| 2 | Deposit | NIS or crypto deposit |
| 3 | Withdrawal | NIS or crypto withdrawal |
| 4 | FeeWithdrawal | Withdrawal fee |
| 23 | RefundWithdrawal | Refunded withdrawal |
| 24 | RefundFeeWithdrawal | Refunded withdrawal fee |
| 26 | DepositFee | Deposit fee |
| 27 | RefundDepositFee | Refunded deposit fee |
| 28 | Unknown | Unknown type (observed in real data) |
| 31 | Unknown | Unknown type (observed in real data) |

**Notes:**
- `firstCoin` value of "₪" means ILS (Israeli Shekel)
- `firstAmount` uses comma formatting for thousands (e.g., "15,000")
- Negative `firstAmount` indicates outgoing funds (withdrawals)
- This is the ONLY way to get deposit/withdrawal data via API

#### Get Order History
**Endpoint:** `GET /Order/OrderHistory`

Returns history of completed orders.

#### Get Order History by Order ID
**Endpoint:** `GET /Order/HistoryByOrderId?id={orderId}`

#### Add Order
**Endpoint:** `POST /Order/AddOrder`

**Parameters:**
- `Amount` - Order amount
- `Price` - Limit price
- `Total` - Total in NIS
- `IsBid` - true for buy, false for sell
- `Pair` - Trading pair

#### Add Market Buy Order
**Endpoint:** `POST /Order/AddOrderMarketPriceBuy`

#### Add Market Sell Order
**Endpoint:** `POST /Order/AddOrderMarketPriceSell`

#### Add Stop Limit Order
**Endpoint:** `POST /Order/AddStopOrder`

#### Cancel Order
**Endpoint:** `POST /Order/CancelOrder`

**Parameters:**
- `id` - Order ID to cancel

#### Withdraw Crypto
**Endpoint:** `POST /Funds/WithdrawCoin`

#### Withdraw NIS
**Endpoint:** `POST /Funds/AddFund`

## Rate Limits

Documentation doesn't specify explicit rate limits. Recommended:
- Public endpoints: 1 request/second
- Private endpoints: 1 request/second
- Be conservative to avoid bans

## Data Mapping to BrokerImportData

### ParsedPosition (from Balance)

| Bit2C Field | Our Field | Notes |
|-------------|-----------|-------|
| `BTC` | `quantity` | |
| `ETH` | `quantity` | |
| `LTC` | `quantity` | |
| `USDC` | `quantity` | |
| `NIS` | `quantity` | Cash balance |
| - | `currency` | "ILS" for NIS |
| - | `asset_class` | "Crypto" or "Cash" |

### ParsedTransaction (from AccountHistory)

| Bit2C Field | Our Field | Notes |
|-------------|-----------|-------|
| `created` | `trade_date` | Parse datetime |
| `pair` | `symbol` | Extract base asset |
| `action` | `transaction_type` | 0="Buy", 1="Sell" |
| `amount` | `quantity` | |
| `price` | `price_per_unit` | |
| `fee` | `fees` | |
| - | `currency` | "ILS" |

### ParsedCashTransaction (from AccountHistory)

| Bit2C Field | Our Field | Notes |
|-------------|-----------|-------|
| deposit.created | `date` | |
| - | `transaction_type` | "Deposit" or "Withdrawal" |
| deposit.amount | `amount` | |
| - | `currency` | Asset type |

## File Export

Bit2C provides transaction history export from the web interface as XLSX files.
Files are available in both English and Hebrew.

### Export Steps
1. Login to bit2c.co.il
2. Go to History/Transactions (היסטוריה/פעולות)
3. Select date range
4. Export as XLSX

### File Format: XLSX

**Sheet Name:** `bit2c-financial-report-{DDMMYY}`

### Column Schema

#### English Columns
| Column | Type | Description |
|--------|------|-------------|
| id | int | Transaction ID |
| created | datetime | Transaction timestamp (YYYY-MM-DD HH:MM:SS.fff) |
| accountAction | string | Transaction type |
| firstCoin | string | Primary asset (BTC, ETH, LTC, USDC, NIS) |
| secondCoin | string | Secondary asset or "N/A" |
| firstAmount | decimal | Primary amount (positive=received, negative=sent) |
| secondAmount | decimal | Secondary amount (NIS for trades) |
| price | decimal | Price per unit in NIS |
| feeAmount | decimal | Fee amount in NIS |
| fee | decimal | Fee percentage |
| balance1 | decimal | Balance after transaction (primary) |
| balance2 | decimal | NIS balance after transaction |
| ref | string | Reference ID (format: `{Pair}\|{OrderID}\|{OrderID}`) |
| isMaker | bool | Whether user was maker |
| AccountNumber | string | Bank account (for deposits) |
| BranchNumber | string | Bank branch |
| BankNumber | int | Bank code |
| BankName | string | Bank name |
| Address | string | Crypto address (for withdrawals) |
| Label | string | Address label |
| TXID | string | Blockchain transaction ID |

#### Hebrew Columns
| Hebrew | English Equivalent |
|--------|-------------------|
| מזהה | id |
| יצירה | created |
| סוג | accountAction |
| מטבע 1 | firstCoin |
| מטבע 2 | secondCoin |
| סכום 1 | firstAmount |
| סכום 2 | secondAmount |
| מחיר | price |
| עמלה | feeAmount |
| עמלה % | fee |
| יתרה 1 | balance1 |
| יתרת ש״ח | balance2 |
| אסמכתה | ref |
| פוזיציה | isMaker |
| בנק | BankNumber |
| סניף | BranchNumber |
| חשבון | AccountNumber |
| שם בנק | BankName |
| כתובת | Address |
| תווית | Label |
| TxID | TXID |

### Transaction Types (accountAction / סוג)

| English | Hebrew | Description |
|---------|--------|-------------|
| Buy | קניה | Crypto purchase with NIS |
| Sell | מכירה | Crypto sale for NIS |
| Deposit | הפקדה | NIS or crypto deposit |
| Withdrawal | משיכה | NIS or crypto withdrawal |
| Fee | עמלה | Custody/platform fee |
| FeeWithdrawal | עמלת משיכה | Withdrawal fee |
| Credit | זיכוי | Account credit/adjustment |

### Transaction Data Patterns

**Buy Transaction:**
- `firstCoin`: Asset bought (BTC, ETH, etc.)
- `firstAmount`: Positive (amount received)
- `secondCoin`: NIS
- `secondAmount`: Negative (NIS spent)
- `price`: Price per unit in NIS
- `feeAmount`: Fee in NIS

**Sell Transaction:**
- `firstCoin`: Asset sold
- `firstAmount`: Negative (amount sold)
- `secondCoin`: NIS
- `secondAmount`: Positive (NIS received)

**Deposit:**
- `firstCoin`: Asset deposited (NIS or crypto)
- `firstAmount`: Positive
- `secondCoin`: N/A
- Bank details populated for NIS deposits

**Withdrawal:**
- `firstCoin`: Asset withdrawn
- `firstAmount`: Negative
- `secondCoin`: N/A
- `Address` and `TXID` populated for crypto withdrawals

**Fee:**
- `firstCoin`: Asset charged (typically BTC or ETH)
- `firstAmount`: Negative
- `ref`: Contains fee type (e.g., `CUSTODY_FEE_MM-YYYY_COIN{N}_{ID}`)

## Implementation Notes

### Python Implementation

```python
import hashlib
import hmac
import base64
import time

def generate_nonce():
    """Generate Bit2C nonce."""
    # Milliseconds since Jan 14, 2014, divided by 250
    epoch = 1389729146519
    return int((time.time() * 1000 - epoch) / 250)

def sign_request(secret: str, params: str) -> str:
    """Generate HMAC-SHA512 signature."""
    secret_upper = secret.upper().encode('utf-8')
    message = params.encode('utf-8')
    signature = hmac.new(secret_upper, message, hashlib.sha512)
    return base64.b64encode(signature.digest()).decode('utf-8')
```

### Error Handling

Bit2C returns errors in JSON format. Check for error fields in responses.

## Security Notes

- API keys grant full account access - use read-only where possible
- Store secrets securely, never in code
- Use HTTPS only
- Nonce must always increase per API key

## References

- [Bit2C Official API Documentation](https://bit2c.co.il/home/api?language=en-US)
- [Node.js Library (GitHub)](https://github.com/OferE/bit2c)
- [Bit2C Website](https://bit2c.co.il)
