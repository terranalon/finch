# CryptoCompare API Research

**Date:** 2026-01-20
**Purpose:** Research CryptoCompare API as a source for historical cryptocurrency prices older than 365 days (to supplement CoinGecko's free tier limitation)

## API Overview

CryptoCompare provides comprehensive cryptocurrency market data with extensive historical coverage. Unlike CoinGecko's free tier (limited to 365 days), CryptoCompare offers historical data going back to each coin's inception.

**API Base URL:** `https://min-api.cryptocompare.com`

## Why CryptoCompare?

| Feature | CoinGecko (Free) | CryptoCompare (Free) |
|---------|------------------|---------------------|
| Historical Data | Last 365 days | Full history (to coin inception) |
| Rate Limit | 10-30 req/min | 100,000 calls/month |
| API Key Required | Optional | Optional (recommended) |
| Data Granularity | Daily | Daily, Hourly, Minute |

**Use Case:** Pre-populate historical crypto prices for transactions older than 365 days, which CoinGecko's free tier cannot provide.

## Authentication

### Free Tier (No API Key)
- Works for basic endpoints
- Rate limit: ~50 calls/min
- Monthly limit: 100,000 calls

### With API Key (Recommended)
- Header: `authorization: Apikey YOUR_API_KEY`
- Higher rate limits
- Usage tracking

## Required Endpoint

### Historical Daily OHLCV

**Endpoint:** `GET /data/v2/histoday`

**Purpose:** Get daily historical prices for a cryptocurrency.

**Parameters:**
- `fsym` (required): From symbol (e.g., "BTC")
- `tsym` (required): To symbol/currency (e.g., "USD")
- `limit` (optional): Number of days (max 2000, default 30)
- `toTs` (optional): Unix timestamp for the last data point

**Example Request:**
```
GET /data/v2/histoday?fsym=BTC&tsym=USD&limit=30
```

**Example Response:**
```json
{
  "Response": "Success",
  "Message": "",
  "HasWarning": false,
  "Type": 100,
  "Data": {
    "Aggregated": false,
    "TimeFrom": 1702857600,
    "TimeTo": 1705449600,
    "Data": [
      {
        "time": 1702857600,
        "high": 43500.12,
        "low": 42100.45,
        "open": 42500.00,
        "volumefrom": 12345.67,
        "volumeto": 534567890.12,
        "close": 43200.50,
        "conversionType": "direct",
        "conversionSymbol": ""
      }
    ]
  }
}
```

**Key Fields:**
- `time`: Unix timestamp (00:00 UTC)
- `close`: Closing price (recommended for daily valuations)
- `high`, `low`, `open`: OHLC data if needed

## Tested Results

### BTC Historical Data (Back to 2012)
```
2012-12-29: $13.40
2012-12-31: $13.51
2013-01-01: $13.30
```

### ETH Historical Data (Back to 2016)
```
2016-07-29: $12.84
2016-08-01: $11.05
```

### Maximum Data per Request
- Limit: 2000 data points per request
- Range tested: 2020-07-30 to 2026-01-20 (2001 days returned)

## Symbol Format

CryptoCompare uses standard uppercase symbols directly (unlike CoinGecko which uses IDs):

| Symbol | CryptoCompare | CoinGecko ID |
|--------|---------------|--------------|
| BTC | BTC | bitcoin |
| ETH | ETH | ethereum |
| USDC | USDC | usd-coin |
| DOGE | DOGE | dogecoin |

**Advantage:** Our existing symbol format works directly with CryptoCompare.

## Rate Limits

| Tier | Rate Limit | Monthly Calls |
|------|------------|---------------|
| Free (no key) | ~50/min | 100,000 |
| Free (with key) | 100/min | 100,000 |
| Paid | Higher | 500K-10M+ |

## Error Handling

### Response Status
```json
{
  "Response": "Error",
  "Message": "fsym is a required param.",
  "HasWarning": false,
  "Type": 1,
  "Data": {}
}
```

### Common Errors
- `Response: "Error"`: Check `Message` for details
- Empty `Data.Data` array: Symbol not found or no data for time range
- Rate limit: HTTP 429 or error message

## Implementation Strategy

### For Historical Price Pre-population

```python
def get_historical_prices_bulk(symbol: str, start_date: date, end_date: date) -> list[tuple[date, Decimal]]:
    """Fetch up to 2000 days of historical prices."""
    end_ts = int(datetime.combine(end_date, datetime.min.time()).timestamp())

    params = {
        "fsym": symbol.upper(),
        "tsym": "USD",
        "limit": 2000,
        "toTs": end_ts
    }

    response = httpx.get(f"{BASE_URL}/data/v2/histoday", params=params)
    data = response.json()

    if data["Response"] != "Success":
        raise CryptoCompareAPIError(data.get("Message", "Unknown error"))

    prices = []
    for item in data["Data"]["Data"]:
        dt = datetime.fromtimestamp(item["time"], tz=UTC).date()
        if start_date <= dt <= end_date:
            prices.append((dt, Decimal(str(item["close"]))))

    return prices
```

### Fetching Full History (Multiple Requests)

For coins with >2000 days of history, iterate with `toTs` parameter:

```python
def get_full_history(symbol: str, start_date: date) -> list[tuple[date, Decimal]]:
    """Fetch complete price history by paginating."""
    all_prices = []
    current_end = date.today()

    while current_end > start_date:
        prices = get_historical_prices_bulk(symbol, start_date, current_end)
        if not prices:
            break
        all_prices.extend(prices)
        current_end = prices[0][0] - timedelta(days=1)

    return sorted(all_prices, key=lambda x: x[0])
```

## Integration with CoinGecko

**Recommended Approach:**

1. **Current prices:** Use CoinGecko (more reliable, better rate limits for current data)
2. **Recent historical (< 365 days):** Use CoinGecko
3. **Old historical (> 365 days):** Use CryptoCompare

```python
def get_historical_price(symbol: str, target_date: date) -> Decimal | None:
    days_ago = (date.today() - target_date).days

    if days_ago <= 365:
        # Use CoinGecko for recent data
        return coingecko_client.get_historical_price(symbol, target_date)
    else:
        # Use CryptoCompare for older data
        return cryptocompare_client.get_historical_price(symbol, target_date)
```

## Pre-population Script

For bootstrapping historical prices database:

```python
MAJOR_CRYPTOS = ["BTC", "ETH", "LTC", "XRP", "USDC", "USDT", "DOGE", "ADA", "SOL", "DOT"]

def pre_populate_historical_prices():
    """One-time script to populate historical prices table."""
    for symbol in MAJOR_CRYPTOS:
        # Get full history from CryptoCompare
        history = cryptocompare_client.get_full_history(symbol, date(2015, 1, 1))

        # Store in database
        for dt, price in history:
            db.execute(
                "INSERT INTO historical_prices (symbol, date, price_usd) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                (symbol, dt, price)
            )
```

## Comparison with Other APIs

| API | Historical Depth | Free Tier | Symbol Format |
|-----|-----------------|-----------|---------------|
| CoinGecko | 365 days | 10K/month | IDs (bitcoin) |
| CryptoCompare | Full history | 100K/month | Symbols (BTC) |
| Messari | Full history | 1K/month | Slugs (bitcoin) |
| CoinMarketCap | Full history | 10K/month | IDs (numeric) |

**Recommendation:** CryptoCompare is the best choice for historical data due to:
- Full historical coverage
- Generous free tier
- Direct symbol format (no mapping needed)
- Simple API structure

## References

- [CryptoCompare API Documentation](https://min-api.cryptocompare.com/documentation)
- [Historical Daily OHLCV Endpoint](https://min-api.cryptocompare.com/documentation?key=Historical&cat=dataHistoday)
- [API Pricing](https://www.cryptocompare.com/api/#pricing)
