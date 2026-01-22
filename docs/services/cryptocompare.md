# CryptoCompare Integration

## Overview

CryptoCompare supplements the CoinGecko integration by providing **historical cryptocurrency prices older than 365 days**. While CoinGecko handles current prices and recent historical data, CryptoCompare fills the gap for older transactions.

## Purpose

- Fetch historical prices for transactions older than 365 days
- Pre-populate historical price database for major cryptocurrencies
- Support portfolio valuation at any historical date

## When to Use Each API

| Data Type | API | Reason |
|-----------|-----|--------|
| Current prices | CoinGecko | Better rate limits, more reliable |
| Historical (< 365 days) | CoinGecko | Native support |
| Historical (> 365 days) | CryptoCompare | Full history available |

## Location

```
backend/app/services/cryptocompare_client.py
```

## Quick Start

```python
from datetime import date
from app.services.cryptocompare_client import CryptoCompareClient

# Create client (API key optional)
client = CryptoCompareClient()

# Get historical price for a date older than 365 days
price = client.get_historical_price("BTC", date(2020, 1, 15))
print(price)  # Decimal("8750.45")

# Get price history for a date range
history = client.get_price_history("ETH", date(2018, 1, 1), date(2018, 12, 31))
for dt, price in history:
    print(f"{dt}: ${price}")
```

## API Endpoint Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/data/v2/histoday` | Daily historical OHLCV data | `get_historical_price()`, `get_price_history()` |

## Symbol Format

CryptoCompare uses standard uppercase symbols directly (no ID mapping needed):

```python
# Works directly - no mapping required
client.get_historical_price("BTC", date(2020, 1, 1))
client.get_historical_price("ETH", date(2018, 6, 15))
client.get_historical_price("DOGE", date(2019, 3, 20))
```

## Historical Data Availability

| Coin | Data Available From |
|------|---------------------|
| BTC | December 2012 |
| ETH | July 2015 |
| LTC | September 2013 |
| XRP | August 2013 |
| DOGE | December 2013 |

## Rate Limits

| Tier | Rate Limit | Monthly Calls |
|------|------------|---------------|
| Free (no key) | ~50/min | 100,000 |
| Free (with key) | 100/min | 100,000 |

The client enforces a 1-second delay between requests.

## Configuration

API key is optional but recommended for higher rate limits.

```python
# Without API key (works for most use cases)
client = CryptoCompareClient()

# With API key
client = CryptoCompareClient(api_key="your-api-key")
```

## Integration Pattern

### Combined Historical Price Lookup

```python
from datetime import date, timedelta
from app.services.coingecko_client import CoinGeckoClient
from app.services.cryptocompare_client import CryptoCompareClient

coingecko = CoinGeckoClient()
cryptocompare = CryptoCompareClient()

def get_historical_crypto_price(symbol: str, target_date: date) -> Decimal | None:
    """Get historical price using appropriate API based on date."""
    days_ago = (date.today() - target_date).days

    if days_ago <= 365:
        # Use CoinGecko for recent data
        return coingecko.get_historical_price(symbol, target_date)
    else:
        # Use CryptoCompare for older data
        return cryptocompare.get_historical_price(symbol, target_date)
```

### Pre-populating Historical Prices

```python
MAJOR_CRYPTOS = ["BTC", "ETH", "LTC", "XRP", "USDC", "USDT", "DOGE"]

def pre_populate_crypto_history(db_session):
    """One-time script to populate historical prices."""
    client = CryptoCompareClient()

    for symbol in MAJOR_CRYPTOS:
        # Fetch full history (up to 2000 days per request, auto-paginated)
        history = client.get_price_history(
            symbol,
            date(2015, 1, 1),  # Adjust based on coin availability
            date.today()
        )

        for dt, price in history:
            # Store in historical_prices table
            db_session.execute(
                "INSERT INTO historical_crypto_prices (symbol, date, price_usd) "
                "VALUES (:symbol, :date, :price) ON CONFLICT DO NOTHING",
                {"symbol": symbol, "date": dt, "price": price}
            )

        db_session.commit()
```

## Error Handling

```python
from app.services.cryptocompare_client import CryptoCompareClient, CryptoCompareAPIError

client = CryptoCompareClient()

try:
    price = client.get_historical_price("BTC", date(2020, 1, 1))
except CryptoCompareAPIError as e:
    print(f"API error: {e}")
    if e.status_code == 429:
        print("Rate limit exceeded - wait before retrying")
```

Methods return `None` or empty lists for graceful degradation rather than raising exceptions.

## Comparison with CoinGecko

| Feature | CoinGecko | CryptoCompare |
|---------|-----------|---------------|
| Current Prices | Yes | No (use CoinGecko) |
| Historical (< 365 days) | Yes | Yes |
| Historical (> 365 days) | No (free tier) | Yes |
| Symbol Format | IDs (bitcoin) | Symbols (BTC) |
| Rate Limit (free) | 10-30 req/min | 50 req/min |
| API Key Required | Optional | Optional |

## Testing

Run unit tests:

```bash
cd backend
pytest tests/test_cryptocompare_client.py -v
```

Tests use mocked API responses - no real API calls are made.

## References

- [CryptoCompare API Docs](https://min-api.cryptocompare.com/documentation)
- [API Research Document](../research/cryptocompare-api-research.md)
- [Source Code](../../backend/app/services/cryptocompare_client.py)
