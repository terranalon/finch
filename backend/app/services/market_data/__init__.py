"""External market data providers.

This module centralizes all external market data fetching:
- MarketDataService: Single entry point (routes to appropriate provider)
- YFinanceClient: Stock/ETF data from Yahoo Finance
- CoinGeckoClient: Cryptocurrency data from CoinGecko
- CryptoCompareClient: Fallback cryptocurrency data
- PriceFetcher: Legacy price fetching utilities

Usage:
    from app.services.market_data import MarketDataService

    service = MarketDataService()
    price = service.fetch_current_price("AAPL", "Stock")
    price = service.fetch_current_price("BTC", "Crypto")
"""

from .coingecko_client import CoinGeckoAPIError, CoinGeckoClient
from .cryptocompare_client import CryptoCompareClient
from .historical_data_fetcher import HistoricalDataFetcher
from .market_data_service import AssetMetadata, MarketDataService, PricePoint
from .price_fetcher import PriceFetcher
from .yfinance_client import TickerInfo, YFinanceClient, YFinanceError

__all__ = [
    "AssetMetadata",
    "CoinGeckoAPIError",
    "CoinGeckoClient",
    "CryptoCompareClient",
    "HistoricalDataFetcher",
    "MarketDataService",
    "PriceFetcher",
    "PricePoint",
    "TickerInfo",
    "YFinanceClient",
    "YFinanceError",
]
