# CoinGecko Integration

## Overview

CoinGecko is the **single source of truth for cryptocurrency prices** in this portfolio tracker, similar to how yfinance is used for stock prices. The `CoinGeckoClient` provides a consistent interface for fetching current and historical crypto prices.

## Purpose

- Fetch current prices for crypto holdings
- Get historical prices for portfolio valuation at specific dates
- Provide price data independent of which exchange the crypto was traded on

## Location

```
backend/app/services/coingecko_client.py
```

## Quick Start

```python
from app.services.coingecko_client import CoinGeckoClient

# Create client (uses settings.coingecko_api_key if available)
client = CoinGeckoClient()

# Get current prices
prices = client.get_current_prices(["BTC", "ETH", "USDC"])
print(prices)  # {"BTC": Decimal("42150.32"), "ETH": Decimal("2250.15"), ...}

# Get single price
btc_price = client.get_current_price("BTC")

# Get historical price for a specific date
from datetime import date
historical = client.get_historical_price("BTC", date(2024, 1, 15))
```

## API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/simple/price` | Batch current prices | `get_current_prices()` |
| `/coins/{id}/history` | Price at specific date | `get_historical_price()` |
| `/coins/{id}/market_chart/range` | Price history range | `get_price_history()` |
| `/coins/list` | Symbol to ID mapping | `get_coin_list()` |

## Symbol to CoinGecko ID Mapping

CoinGecko uses unique IDs (e.g., "bitcoin") rather than symbols (e.g., "BTC"). The client maintains an internal mapping for common cryptocurrencies:

| Symbol | CoinGecko ID |
|--------|--------------|
| BTC | bitcoin |
| ETH | ethereum |
| LTC | litecoin |
| USDC | usd-coin |
| USDT | tether |
| DOGE | dogecoin |
| SOL | solana |
| ... | ... |

For unknown symbols, the client falls back to lowercase conversion. You can add custom mappings:

```python
client.add_symbol_mapping("NEWTOKEN", "new-token-id")
```

## Rate Limits

| Plan | Rate Limit | Monthly Credits |
|------|------------|-----------------|
| Free (Demo) | 10-30 req/min | 10,000 |
| Pro | 500-1000 req/min | 500K-3M |

The client automatically enforces a 1-second delay between requests to stay within limits.

## Configuration

Add to your `.env` file (optional - free tier works without key):

```bash
COINGECKO_API_KEY=your_api_key_here
```

For Pro API access:

```python
client = CoinGeckoClient(api_key="pro-key", use_pro_api=True)
```

## Integration with Currency Conversion

**Design Decision:** All prices are fetched in USD and converted to ILS using the `exchange_rates` table.

```python
from app.services.coingecko_client import CoinGeckoClient
from app.services.currency_service import CurrencyService

# Get price in USD
client = CoinGeckoClient()
btc_usd = client.get_current_price("BTC")  # Decimal("42150.32")

# Convert to ILS
currency_service = CurrencyService(db)
usd_ils_rate = currency_service.get_rate("USD", "ILS")
btc_ils = btc_usd * usd_ils_rate
```

## Comparison with yfinance (Stocks)

| Feature | yfinance (Stocks) | CoinGecko (Crypto) |
|---------|-------------------|-------------------|
| Asset Types | Stocks, ETFs, Indices | Cryptocurrencies |
| Symbol Format | Ticker (AAPL) | CoinGecko ID (bitcoin) |
| Israeli Support | .TA suffix | N/A |
| Price Currency | Native | USD (converted to ILS) |
| Rate Limits | Unofficial | Documented |
| API Key | None | Optional |

## Error Handling

The client handles errors gracefully:

```python
from app.services.coingecko_client import CoinGeckoClient, CoinGeckoAPIError

client = CoinGeckoClient()

try:
    prices = client.get_current_prices(["BTC"])
except CoinGeckoAPIError as e:
    print(f"API error: {e}")
    if e.status_code == 429:
        print("Rate limit exceeded - wait before retrying")
```

For batch operations, the client returns partial results rather than failing entirely if some symbols aren't found.

## Caching Recommendations

For production use, consider caching:

1. **Current prices:** Cache for 60 seconds (matches API update frequency)
2. **Historical prices:** Cache indefinitely (data doesn't change)
3. **Coin list:** Cache for 24 hours (stable data)

## Testing

Run unit tests:

```bash
cd backend
pytest tests/test_coingecko_client.py -v
```

Tests use mocked API responses - no real API calls are made.

## References

- [CoinGecko API Docs](https://docs.coingecko.com)
- [API Research Document](../research/coingecko-api-research.md)
- [Source Code](../../backend/app/services/coingecko_client.py)
