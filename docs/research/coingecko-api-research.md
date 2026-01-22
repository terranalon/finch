# CoinGecko API Research

**Date:** 2026-01-20
**Purpose:** Research CoinGecko API for cryptocurrency price fetching (analogous to yfinance for stocks)

## API Overview

CoinGecko is the world's largest independent crypto data aggregator, integrated with 1,000+ exchanges and listing 18,000+ coins. For our portfolio tracker, we'll use it as the **single source of truth for cryptocurrency prices**, similar to how yfinance is used for stocks.

**API Base URL (Demo/Free):** `https://api.coingecko.com/api/v3`
**API Base URL (Pro):** `https://pro-api.coingecko.com/api/v3`

## Authentication

### Demo API (Free Tier)
- Optional API key for basic endpoints
- Header: `x-cg-demo-api-key: YOUR_API_KEY`
- Query param: `x_cg_demo_api_key=YOUR_API_KEY`

### Pro API (Paid Tiers)
- Required API key
- Header (recommended): `x-cg-pro-api-key: YOUR_API_KEY`
- Query param: `x_cg_pro_api_key=YOUR_API_KEY`

## Rate Limits

| Plan | Monthly Credits | Rate Limit (req/min) | Historical Data |
|------|-----------------|---------------------|-----------------|
| Demo (Free) | 10,000 | 10-30 | Last 365 days |
| Analyst | 500,000 | 500 | Full history |
| Lite | 1,000,000 | 500 | Full history |
| Pro | 3,000,000 | 1,000 | Full history |

**Credit Usage:**
- Each API request = 1 credit
- Only successful requests (HTTP 200) count toward credit limit
- All requests count toward rate limit (including errors)

**Recommended Strategy:**
- Start with Demo API (free) for our use case
- Implement caching to reduce API calls
- Respect rate limits with delays between batch requests

## Required Endpoints

### 1. Get Current Prices (Batch)

**Endpoint:** `GET /simple/price`

**Purpose:** Query current prices for multiple coins at once.

**Parameters:**
- `ids` (required): Comma-separated list of CoinGecko coin IDs (e.g., "bitcoin,ethereum")
- `vs_currencies` (required): Quote currency (e.g., "usd")
- `include_market_cap`: Include market cap (optional)
- `include_24hr_vol`: Include 24hr volume (optional)
- `include_24hr_change`: Include 24hr price change (optional)
- `include_last_updated_at`: Include last update timestamp (optional)

**Example Request:**
```
GET /simple/price?ids=bitcoin,ethereum,litecoin&vs_currencies=usd&include_last_updated_at=true
```

**Example Response:**
```json
{
  "bitcoin": {
    "usd": 42150.32,
    "last_updated_at": 1705766400
  },
  "ethereum": {
    "usd": 2250.15,
    "last_updated_at": 1705766400
  },
  "litecoin": {
    "usd": 68.42,
    "last_updated_at": 1705766400
  }
}
```

**Cache/Update Frequency:**
- Demo API: every 60 seconds
- Pro API: every 20 seconds

### 2. Get Coins List (Symbol to ID Mapping)

**Endpoint:** `GET /coins/list`

**Purpose:** Get list of all supported coins with their IDs, symbols, and names.

**Parameters:**
- `include_platform`: Include platform contract addresses (optional)

**Example Response:**
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin"
  },
  {
    "id": "ethereum",
    "symbol": "eth",
    "name": "Ethereum"
  },
  {
    "id": "usd-coin",
    "symbol": "usdc",
    "name": "USD Coin"
  }
]
```

**Note:** Symbol is lowercase in the response. Multiple coins may share the same symbol.

### 3. Get Historical Chart Data

**Endpoint:** `GET /coins/{id}/market_chart`

**Purpose:** Get historical chart data including price, market cap, and 24hr volume.

**Parameters:**
- `vs_currency` (required): Quote currency (e.g., "usd")
- `days` (required): Number of days ago (1, 7, 14, 30, 90, 180, 365, max)
- `interval`: Data interval (auto-selected based on days if not specified)
- `precision`: Decimal precision for prices

**Data Granularity (automatic):**
- 1 day from current time = 5-minutely data
- 2-90 days from current time = hourly data
- 90+ days from current time = daily data (00:00 UTC)

**Example Request:**
```
GET /coins/bitcoin/market_chart?vs_currency=usd&days=30
```

**Example Response:**
```json
{
  "prices": [
    [1705449600000, 41235.12],
    [1705536000000, 42150.32],
    ...
  ],
  "market_caps": [...],
  "total_volumes": [...]
}
```

**Cache/Update Frequency:**
- Every 30 seconds for last data point
- Last completed UTC day (00:00) available 10 minutes after midnight (00:10)

### 4. Get Historical Price for Specific Date

**Endpoint:** `GET /coins/{id}/history`

**Purpose:** Get historical data (price, market cap, 24hr volume) at a given date.

**Parameters:**
- `date` (required): Date in dd-mm-yyyy format
- `localization`: Include localized languages (default: true)

**Example Request:**
```
GET /coins/bitcoin/history?date=30-12-2024
```

**Example Response:**
```json
{
  "id": "bitcoin",
  "symbol": "btc",
  "name": "Bitcoin",
  "market_data": {
    "current_price": {
      "usd": 42150.32
    },
    "market_cap": {...},
    "total_volume": {...}
  }
}
```

**Note:**
- Data returned is at 00:00:00 UTC
- Available 35 minutes after midnight on next UTC day (00:35)
- Demo API limited to past 365 days

### 5. Get Historical Chart Data (Time Range)

**Endpoint:** `GET /coins/{id}/market_chart/range`

**Purpose:** Get historical chart data within specific time range.

**Parameters:**
- `vs_currency` (required): Quote currency
- `from` (required): Start timestamp (UNIX)
- `to` (required): End timestamp (UNIX)
- `interval`: Data interval (optional)
- `precision`: Decimal precision

**Example Request:**
```
GET /coins/bitcoin/market_chart/range?vs_currency=usd&from=1704067200&to=1706745600
```

**Note:** Same granularity rules as `/market_chart` apply.

## Symbol to CoinGecko ID Mapping

CoinGecko uses unique IDs rather than symbols (since multiple coins may share symbols).

### Common Mappings

| Our Symbol | CoinGecko ID |
|------------|--------------|
| BTC | bitcoin |
| ETH | ethereum |
| LTC | litecoin |
| XRP | ripple |
| USDC | usd-coin |
| USDT | tether |
| DOGE | dogecoin |
| ADA | cardano |
| SOL | solana |
| DOT | polkadot |
| LINK | chainlink |
| MATIC | matic-network |
| UNI | uniswap |
| AVAX | avalanche-2 |
| SHIB | shiba-inu |
| BNB | binancecoin |

### Mapping Strategy

1. **Static Mapping:** Maintain a dictionary of common crypto symbols to CoinGecko IDs
2. **Fallback:** For unknown symbols, convert to lowercase (works for many cases)
3. **Caching:** Cache `/coins/list` response to build dynamic mapping if needed

**Implementation Note:** The `/coins/list` endpoint returns ~16,000 coins. Consider:
- Caching locally with daily refresh
- Only mapping symbols we actually hold
- Manual overrides for ambiguous symbols

## Integration with Exchange Rates Table

**Design Decision:** Fetch prices in USD and convert to ILS using our existing `exchange_rates` table.

**Rationale:**
1. CoinGecko provides more reliable USD prices than ILS
2. We already have exchange rate infrastructure in place
3. Consistent with how other data sources work
4. Easier to validate prices against external sources

**Implementation:**
```python
# Get crypto price in USD from CoinGecko
btc_usd = coingecko_client.get_current_price("bitcoin", "usd")

# Convert to ILS using exchange_rates table
usd_ils_rate = currency_service.get_rate("USD", "ILS")
btc_ils = btc_usd * usd_ils_rate
```

## Comparison with yfinance

| Aspect | yfinance (Stocks) | CoinGecko (Crypto) |
|--------|-------------------|-------------------|
| Data Source | Yahoo Finance | CoinGecko |
| Asset Types | Stocks, ETFs, Indices | Cryptocurrencies |
| Symbol Format | Ticker (e.g., AAPL) | CoinGecko ID (e.g., bitcoin) |
| Rate Limits | Unofficial limits | 10-30 req/min (free) |
| Historical Data | Full history | 365 days (free) |
| Real-time | 15-min delay | ~60s delay |
| Authentication | None | Optional API key |
| Israeli Support | .TA suffix for TASE | N/A |

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid params) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not found (invalid coin ID) |
| 429 | Rate limit exceeded |
| 5xx | Server error |

### Error Response Format
```json
{
  "error": "coin not found"
}
```

### Recommended Strategy

1. Check for HTTP errors before parsing response
2. Implement exponential backoff for rate limits (429)
3. Log and skip failed coin lookups (don't crash entire batch)
4. Cache successful responses to reduce API calls

## Implementation Notes

### Python Libraries
- `httpx` for HTTP requests (already used in Kraken/Bit2C clients)
- `decimal.Decimal` for price precision

### Caching Considerations
- Cache current prices for 60 seconds (match API update frequency)
- Cache historical prices longer (data doesn't change)
- Cache `/coins/list` for 24 hours (stable data)

### Rate Limiting
- Implement delay between requests (1-2 seconds for batch operations)
- Track request count to stay within limits
- Consider async requests for better performance

## Test Environment

- CoinGecko Demo API works without API key for basic testing
- Use sandbox/test prices for unit tests (mock responses)
- Rate limits apply even for demo keys

## References

- [CoinGecko API Documentation](https://docs.coingecko.com)
- [CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)
- [CoinGecko Coin List (Google Sheets)](https://docs.google.com/spreadsheets/d/1wTTuxXt8n9q7C4NDXqQpI3wpKu1_5bGVmP9Xz0XGSyU/edit?usp=sharing)
- [Simple Price Endpoint](https://docs.coingecko.com/v3.0.1/reference/simple-price)
- [Market Chart Endpoint](https://docs.coingecko.com/v3.0.1/reference/coins-id-market-chart)
- [Coins List Endpoint](https://docs.coingecko.com/v3.0.1/reference/coins-list)
