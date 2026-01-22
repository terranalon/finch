# Kraken API Research

**Date:** 2026-01-20
**Purpose:** Research Kraken API for portfolio tracker integration

## API Overview

Kraken provides both REST and WebSocket APIs for trading and account management. For our portfolio tracker, we'll use the **Spot REST API** to fetch account balances, trade history, and ledger entries.

**API Base URL:** `https://api.kraken.com`

## Authentication

### Method: HMAC-SHA512 with Nonce

Kraken uses a two-part API key system:
- **Public Key** (`API-Key`): Sent in HTTP header
- **Private Key**: Used locally to generate signature, never transmitted

### Signature Generation

```
HMAC-SHA512(URI_path + SHA256(nonce + POST_data), base64_decode(private_key))
```

#### Steps:
1. Generate nonce (always-increasing 64-bit integer, typically unix timestamp in milliseconds)
2. Concatenate nonce with URL-encoded POST data
3. SHA256 hash the result
4. Concatenate URI path (e.g., `/0/private/Balance`) with the hash
5. HMAC-SHA512 using base64-decoded private key
6. Base64 encode result for `API-Sign` header

### Required Headers
- `API-Key`: Public API key
- `API-Sign`: Base64-encoded HMAC-SHA512 signature

### Required POST Parameters
- `nonce`: Always-increasing 64-bit integer
- `otp` (optional): 2FA code if enabled on API key

### Important: Nonce Management
- Nonce must always increase; cannot reset to lower values
- Excessive invalid nonces can trigger temporary bans
- Recommended: Use `int(time.time() * 1000)` for millisecond precision

## Rate Limits

### Counter-Based System

| Account Tier | Max Counter | Decay Rate |
|-------------|-------------|------------|
| Starter     | 15          | -0.33/sec  |
| Intermediate| 20          | -0.5/sec   |
| Pro         | 20          | -1/sec     |

### Counter Increments by Endpoint Type

| Endpoint Type | Counter Increment |
|--------------|-------------------|
| Ledger/Trade history | +2 |
| Other API calls | +1 |
| AddOrder/CancelOrder | Separate limiter |

### Error Responses
- `EAPI:Rate limit exceeded` - Counter exceeded max
- `EService: Throttled: [UNIX timestamp]` - Too many concurrent requests

### Recommended Strategy
- Start with max 1 request/second
- For history endpoints (+2), limit to 1 request every 4-6 seconds
- Track counter locally and preemptively delay

## Endpoints for Portfolio Tracking

### 1. Get Account Balance

**Endpoint:** `POST /0/private/Balance`

**Permission Required:** `Funds permissions - Query`

**Response:** Returns all cash balances, net of pending withdrawals.

**Asset Suffixes:**
- `.B` - Balances in yield-bearing products
- `.F` - Balances earning in Kraken Rewards
- `.S` - Staked assets
- `.M` - Margin assets

**Response Format:**
```json
{
  "error": [],
  "result": {
    "ZUSD": "123.4567",
    "XXBT": "0.12345678",
    "XETH": "1.23456789",
    "XXBT.S": "0.05000000"
  }
}
```

### 2. Get Trades History

**Endpoint:** `POST /0/private/TradesHistory`

**Permission Required:** `Orders and trades - Query closed orders & trades`

**Pagination:** Returns 50 results at a time, most recent by default

**Parameters:**
- `start` - Starting unix timestamp
- `end` - Ending unix timestamp
- `ofs` - Result offset for pagination

**Response Fields (per trade):**
- `ordertxid` - Order transaction ID
- `pair` - Trading pair
- `time` - Unix timestamp
- `type` - "buy" or "sell"
- `ordertype` - "market", "limit", etc.
- `price` - Price per unit
- `cost` - Total cost
- `fee` - Fees paid
- `vol` - Volume/quantity
- `margin` - Margin amount (if margin trade)
- `misc` - Comma-delimited list of flags

### 3. Get Ledgers

**Endpoint:** `POST /0/private/Ledgers`

**Permission Required:** `Data - Query ledger entries`

**Pagination:** Returns 50 results at a time

**Parameters:**
- `asset` - Comma-delimited list of assets (optional)
- `aclass` - Asset class (default: "currency")
- `type` - Type filter: "all", "deposit", "withdrawal", "trade", "margin", "transfer", "staking"
- `start` - Starting unix timestamp
- `end` - Ending unix timestamp
- `ofs` - Result offset

**Response Fields (per entry):**
- `refid` - Reference ID
- `time` - Unix timestamp
- `type` - Ledger type
- `subtype` - Additional type info
- `aclass` - Asset class
- `asset` - Asset name
- `amount` - Transaction amount (negative for withdrawals)
- `fee` - Fee amount
- `balance` - Resulting balance

### 4. Query Ledgers (specific entries)

**Endpoint:** `POST /0/private/QueryLedgers`

**Permission Required:** `Data - Query ledger entries`

**Parameters:**
- `id` - Comma-delimited list of ledger IDs
- `trades` - Include trade-related entries (default: false)

## File Export Format

### How to Export from Kraken UI

1. Log into Kraken account
2. Navigate to History tab
3. Click Export tab
4. Select "Ledgers" from dropdown
5. Set date range
6. Under Format, select "CSV"
7. Click "Generate"
8. Wait for status "Processed"
9. Download and unzip

### Ledger CSV Columns

| Column | Description |
|--------|-------------|
| txid | Transaction ID |
| refid | Reference ID (links related entries) |
| time | Timestamp |
| type | Transaction type |
| subtype | Additional type info |
| aclass | Asset class |
| asset | Asset name |
| amount | Transaction amount |
| fee | Fee amount |
| balance | Resulting balance |

### Transaction Types in Ledger

| Type | Description |
|------|-------------|
| deposit | Fiat/crypto deposit |
| withdrawal | Fiat/crypto withdrawal |
| trade | Trade execution |
| margin | Margin trade |
| transfer | Internal transfer |
| staking | Staking reward |
| spend | Kraken Pay spend |
| receive | Kraken Pay receive |
| adjustment | Balance adjustment |

## Data Mapping to BrokerImportData

### ParsedTransaction Mapping (from TradesHistory)

| Kraken Field | Our Field | Notes |
|--------------|-----------|-------|
| `time` | `trade_date` | Convert from unix timestamp |
| `pair` | `symbol` | Map to standard format |
| `type` | `transaction_type` | "buy" → "Buy", "sell" → "Sell" |
| `vol` | `quantity` | |
| `price` | `price_per_unit` | |
| `cost` | `amount` | |
| `fee` | `fees` | |
| `pair` currency | `currency` | Extract quote currency |

### ParsedPosition Mapping (from Balance)

| Kraken Field | Our Field | Notes |
|--------------|-----------|-------|
| asset name | `symbol` | Map Kraken format (XXBT→BTC) |
| balance | `quantity` | |
| - | `cost_basis` | Not available from API |
| asset type | `currency` | Use asset's quote currency |
| - | `asset_class` | Infer "Crypto" |

### ParsedCashTransaction Mapping (from Ledgers)

| Kraken Field | Our Field | Notes |
|--------------|-----------|-------|
| `time` | `date` | Convert from unix timestamp |
| `type` | `transaction_type` | Map type values |
| `amount` | `amount` | Negative = outflow |
| `asset` | `currency` | Map Kraken format |

## Asset Name Mapping

Kraken uses non-standard asset names:

| Kraken | Standard |
|--------|----------|
| XXBT | BTC |
| XETH | ETH |
| ZUSD | USD |
| ZEUR | EUR |
| XXRP | XRP |
| XXLM | XLM |
| XLTC | LTC |

**Rule:** Remove leading 'X' or 'Z' for most assets.

## Test Environment

Kraken does not provide a public sandbox/test environment. Testing recommendations:
1. Create a Kraken account with minimal funds for testing
2. Use API keys with read-only permissions only
3. Mock API responses in unit tests using recorded responses

## Implementation Notes

### Python Libraries
- `requests` or `httpx` for HTTP
- `hashlib` for SHA256
- `hmac` for HMAC-SHA512
- `base64` for encoding
- `time` for nonce generation

### Error Handling
```json
{
  "error": ["EAPI:Rate limit exceeded"],
  "result": {}
}
```

Always check `error` array before processing `result`.

### Pagination Strategy
1. Start with no offset
2. If 50 results returned, add offset and fetch next page
3. Continue until fewer than 50 results
4. Respect rate limits between pages

## References

- [Kraken API Documentation](https://docs.kraken.com/api/)
- [Kraken REST Rate Limits](https://docs.kraken.com/api/docs/guides/spot-rest-ratelimits/)
- [Kraken API Authentication Guide](https://docs.kraken.com/api/docs/guides/spot-rest-auth)
