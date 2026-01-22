# Binance API Research

## Overview

Binance is the world's largest cryptocurrency exchange by trading volume. This document covers the REST API for spot trading, which we'll use for portfolio tracking.

**Official Documentation:**
- [Binance Spot API Docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)
- [GitHub Repository](https://github.com/binance/binance-spot-api-docs)
- [Account Endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints)
- [Signature Examples](https://github.com/binance/binance-signature-examples)

---

## Authentication

### Method: HMAC SHA256

Binance uses HMAC-SHA256 for request signing. Unlike Kraken and Bit2C which use nonces, Binance uses timestamps.

### Signature Process

1. Build query string with all parameters including `timestamp`
2. Compute HMAC-SHA256 of query string using `secretKey`
3. Append signature as `signature` parameter
4. Include API key in header as `X-MBX-APIKEY`

### Required Parameters

| Parameter | Description |
|-----------|-------------|
| `timestamp` | Millisecond timestamp when request was created |
| `signature` | HMAC-SHA256 of query string |
| `recvWindow` | Optional. Validity window in ms (default: 5000, max: 60000) |

### Python Signature Example

```python
import hashlib
import hmac
import time
import urllib.parse

def generate_signature(query_string: str, secret_key: str) -> str:
    """Generate HMAC-SHA256 signature for Binance API."""
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def sign_request(params: dict, secret_key: str) -> str:
    """Sign request parameters and return full query string."""
    params['timestamp'] = int(time.time() * 1000)
    query_string = urllib.parse.urlencode(params)
    signature = generate_signature(query_string, secret_key)
    return f"{query_string}&signature={signature}"
```

### Important Notes

- The `secretKey` is NEVER sent in requests - only used locally for signing
- Signature is case-insensitive, but `secretKey` and payload are case-sensitive
- Non-ASCII characters must be percent-encoded before signing
- As of 2026-01-15: Payloads must be percent-encoded before computing signatures

---

## Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://api.binance.com` |
| Backup | `https://api1.binance.com`, `https://api2.binance.com`, `https://api3.binance.com` |
| Testnet | `https://testnet.binance.vision` |

---

## Rate Limits

Binance uses a weight-based rate limiting system.

| Limit Type | Value |
|------------|-------|
| Request Weight | 1200/minute per IP |
| Order Rate | 10 orders/second, 100,000 orders/24h |

### Headers

| Header | Description |
|--------|-------------|
| `X-MBX-USED-WEIGHT-*` | Current used weight for time interval |
| `X-MBX-ORDER-COUNT-*` | Current order count for time interval |

### Rate Limit Response

- **429**: Rate limit exceeded - back off immediately
- **418**: IP auto-banned for repeated violations

---

## Required Endpoints

### 1. Account Information

**Endpoint:** `GET /api/v3/account`

**Weight:** 20

**Security:** SIGNED (USER_DATA)

**Response:**
```json
{
  "makerCommission": 15,
  "takerCommission": 15,
  "buyerCommission": 0,
  "sellerCommission": 0,
  "canTrade": true,
  "canWithdraw": true,
  "canDeposit": true,
  "accountType": "SPOT",
  "balances": [
    {
      "asset": "BTC",
      "free": "4723846.89208129",
      "locked": "0.00000000"
    },
    {
      "asset": "ETH",
      "free": "4763368.68006011",
      "locked": "0.00000000"
    }
  ]
}
```

**Mapping to ParsedPosition:**
```python
ParsedPosition(
    symbol=balance["asset"],          # "BTC"
    quantity=Decimal(balance["free"]) + Decimal(balance["locked"]),
    currency=balance["asset"],
    asset_class="Crypto",
)
```

---

### 2. Trade History

**Endpoint:** `GET /api/v3/myTrades`

**Weight:** 20

**Security:** SIGNED (USER_DATA)

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `symbol` | Yes | Trading pair (e.g., "BTCUSDT") |
| `startTime` | No | Start time in ms |
| `endTime` | No | End time in ms |
| `fromId` | No | TradeId to fetch from |
| `limit` | No | Default 500, max 1000 |

**Note:** Time between `startTime` and `endTime` cannot exceed 24 hours.

**Response:**
```json
[
  {
    "symbol": "BTCUSDT",
    "id": 28457,
    "orderId": 100234,
    "price": "42000.00",
    "qty": "0.5",
    "quoteQty": "21000.00",
    "commission": "10.50",
    "commissionAsset": "USDT",
    "time": 1499865549590,
    "isBuyer": true,
    "isMaker": false,
    "isBestMatch": true
  }
]
```

**Mapping to ParsedTransaction:**
```python
ParsedTransaction(
    trade_date=datetime.fromtimestamp(trade["time"] / 1000).date(),
    symbol=base_asset,                    # "BTC" from "BTCUSDT"
    transaction_type="Buy" if trade["isBuyer"] else "Sell",
    quantity=Decimal(trade["qty"]),
    price_per_unit=Decimal(trade["price"]),
    amount=Decimal(trade["quoteQty"]),
    fees=Decimal(trade["commission"]),
    currency=quote_asset,                 # "USDT" from "BTCUSDT"
    raw_data=trade,
)
```

---

### 3. Deposit History

**Endpoint:** `GET /sapi/v1/capital/deposit/hisrec`

**Weight:** 1

**Security:** SIGNED (USER_DATA)

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `coin` | No | Filter by coin |
| `status` | No | 0:pending, 1:success, 6:credited |
| `startTime` | No | Default: 90 days ago |
| `endTime` | No | Default: now |
| `limit` | No | Default 1000, max 1000 |

**Note:** Time interval must be within 0-90 days.

**Response:**
```json
[
  {
    "id": "769800519366885376",
    "amount": "0.001",
    "coin": "BTC",
    "network": "BTC",
    "status": 1,
    "address": "1HPn8Rx...",
    "txId": "b3c6...",
    "insertTime": 1617620000000,
    "confirmTimes": "1/1"
  }
]
```

**Mapping to ParsedCashTransaction:**
```python
ParsedCashTransaction(
    date=datetime.fromtimestamp(deposit["insertTime"] / 1000).date(),
    transaction_type="Deposit",
    amount=Decimal(deposit["amount"]),
    currency=deposit["coin"],
    notes=f"Binance deposit - {deposit['txId']}",
    raw_data=deposit,
)
```

---

### 4. Withdrawal History

**Endpoint:** `GET /sapi/v1/capital/withdraw/history`

**Weight:** 1 (10 requests/second limit)

**Security:** SIGNED (USER_DATA)

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `coin` | No | Filter by coin |
| `status` | No | 0:Email Sent, 1:Cancelled, 2:Awaiting, 3:Rejected, 4:Processing, 5:Failure, 6:Completed |
| `startTime` | No | Default: 90 days ago |
| `endTime` | No | Default: now |
| `limit` | No | Default 1000, max 1000 |

**Response:**
```json
[
  {
    "id": "b6ae22...",
    "amount": "0.1",
    "transactionFee": "0.0005",
    "coin": "ETH",
    "status": 6,
    "address": "0x...",
    "txId": "0xb5c8...",
    "applyTime": "2021-04-05 12:00:00",
    "network": "ETH",
    "confirmNo": 12
  }
]
```

**Mapping to ParsedCashTransaction:**
```python
ParsedCashTransaction(
    date=datetime.strptime(withdrawal["applyTime"], "%Y-%m-%d %H:%M:%S").date(),
    transaction_type="Withdrawal",
    amount=-Decimal(withdrawal["amount"]),  # Negative for withdrawal
    currency=withdrawal["coin"],
    notes=f"Binance withdrawal - fee: {withdrawal['transactionFee']}",
    raw_data=withdrawal,
)
```

---

### 5. All Coins Information

**Endpoint:** `GET /sapi/v1/capital/config/getall`

**Weight:** 10

**Security:** SIGNED (USER_DATA)

**Purpose:** Get all coins' information including network details. Useful for validating assets.

---

## File Export Format

### How to Export from Binance UI

1. Log in to Binance account
2. Go to **Profile** > **Orders** > **Spot Order**
3. Click **Trade History** > **Export Trade History**
4. Select date range (max 1 year, starting from 2017-07-13)
5. Click **Generate** (max 5 statements/month)
6. Download CSV within 7 days

### Export Limitations

- Max 10,000 data points per export
- Max 6 months per export range
- Max 5 exports per month
- Download link expires after 7 days

### Available Export Types

1. **Trade History** - Buy/sell orders
2. **Transaction History** - Deposits and withdrawals
3. **Distribution History** - Staking rewards, airdrops
4. **Convert History** - Instant conversions

### CSV Format (Trade History)

| Column | Description |
|--------|-------------|
| `Date(UTC)` | Trade timestamp |
| `Pair` | Trading pair (e.g., "BTCUSDT") |
| `Side` | "BUY" or "SELL" |
| `Price` | Execution price |
| `Executed` | Quantity executed |
| `Amount` | Total value |
| `Fee` | Trading fee |

---

## Symbol Parsing

Binance uses concatenated symbols without delimiter (e.g., "BTCUSDT", "ETHBTC").

### Strategy for Parsing

```python
# Common quote assets (check in order of specificity)
QUOTE_ASSETS = ["USDT", "BUSD", "USDC", "USD", "BTC", "ETH", "BNB"]

def parse_symbol(symbol: str) -> tuple[str, str]:
    """Parse Binance symbol into base and quote assets."""
    for quote in QUOTE_ASSETS:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return base, quote
    return symbol, "UNKNOWN"

# Examples:
# "BTCUSDT" -> ("BTC", "USDT")
# "ETHBTC" -> ("ETH", "BTC")
# "DOGEUSDC" -> ("DOGE", "USDC")
```

---

## Implementation Considerations

### 1. Pagination for Trade History

Since each `myTrades` call requires a specific symbol, we need to:
1. Get account balances to find all traded assets
2. Query trade history for each asset pair
3. Handle pagination with `fromId` parameter

### 2. Rate Limiting Strategy

```python
# Track weight usage
class BinanceClient:
    def __init__(self):
        self.weight_used = 0
        self.weight_limit = 1200
        self.last_reset = time.time()

    def _check_rate_limit(self, weight: int):
        """Check if we have enough weight, sleep if needed."""
        now = time.time()
        if now - self.last_reset >= 60:
            self.weight_used = 0
            self.last_reset = now

        if self.weight_used + weight > self.weight_limit:
            sleep_time = 60 - (now - self.last_reset)
            time.sleep(sleep_time)
            self.weight_used = 0
            self.last_reset = time.time()

        self.weight_used += weight
```

### 3. Time Range Handling

- Trade history: Max 24 hours per request
- Deposit/Withdrawal history: Max 90 days per request

Need to split long date ranges into chunks.

---

## Comparison with Other Exchanges

| Feature | Binance | Kraken | Bit2C |
|---------|---------|--------|-------|
| Auth Method | HMAC-SHA256 + timestamp | HMAC-SHA512 + nonce | HMAC-SHA512 + custom nonce |
| Rate Limit | Weight-based (1200/min) | Call count + tier | Not documented |
| Trade History | Per-symbol (24h max) | All trades (paginated) | All trades |
| Deposit/Withdrawal | SAPI endpoints | Ledger entries | Separate endpoints |
| Symbol Format | Concatenated (BTCUSDT) | Pairs (XXBTZUSD) | Pairs (BtcNis) |

---

## Security Best Practices

1. **Never share API secret** - Only used locally for signing
2. **Use IP whitelist** - Restrict API key to specific IPs
3. **Minimal permissions** - Only enable required permissions (read-only for portfolio tracking)
4. **Separate keys** - Use different keys for different purposes
5. **Monitor usage** - Check for unauthorized access

---

## References

- [Binance Spot API Documentation](https://developers.binance.com/docs/binance-spot-api-docs/rest-api)
- [Request Security](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/request-security)
- [Account Endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints)
- [Wallet Endpoints](https://developers.binance.com/docs/wallet/capital/deposite-history)
- [Signature Examples (GitHub)](https://github.com/binance/binance-signature-examples)
- [Export Trade History FAQ](https://www.binance.com/en/support/faq/how-to-download-spot-trading-transaction-history-statement-e4ff64f2533f4d23a0b3f8f17f510eab)
