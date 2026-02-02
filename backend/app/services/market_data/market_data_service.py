"""Unified market data service - single entry point for all external price data.

This service routes requests to the appropriate provider based on asset type:
- Stocks/ETFs/MutualFunds: YFinance
- Cryptocurrencies: CoinGecko (with CryptoCompare fallback)

Centralizing external API calls here provides:
- Single place to add caching, rate limiting, fallbacks
- Consistent error handling
- Clear provider routing logic
- Easy to test (mock one service)
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient
from app.services.market_data.yfinance_client import YFinanceClient

logger = logging.getLogger(__name__)


@dataclass
class AssetMetadata:
    """Standardized asset metadata across all providers."""

    symbol: str
    name: str | None
    asset_class: str | None
    sector: str | None
    industry: str | None
    currency: str | None
    source: str  # 'yfinance', 'coingecko', etc.


@dataclass
class PricePoint:
    """Single price data point."""

    date: date
    price: Decimal
    source: str


class MarketDataService:
    """Single entry point for all external market data.

    Routes requests to the appropriate provider based on asset type.
    Services should use this instead of calling YFinance/CoinGecko directly.

    Example:
        service = MarketDataService()
        price = service.fetch_current_price("AAPL", "Stock")
        price = service.fetch_current_price("BTC", "Crypto")
    """

    # Asset classes that use CoinGecko
    CRYPTO_ASSET_CLASSES = {"Crypto", "Cryptocurrency"}

    # Asset classes that use YFinance
    STOCK_ASSET_CLASSES = {"Stock", "ETF", "MutualFund", "Bond", "Index"}

    def __init__(self):
        self._yfinance = YFinanceClient()
        self._coingecko = CoinGeckoClient()
        self._cryptocompare = CryptoCompareClient()

    def fetch_asset_metadata(
        self, symbol: str, asset_class: str | None = None
    ) -> AssetMetadata | None:
        """Fetch metadata for an asset from the appropriate provider.

        Args:
            symbol: Asset symbol (e.g., "AAPL", "BTC")
            asset_class: Known asset class (helps routing)

        Returns:
            AssetMetadata or None if not found
        """
        # Route to appropriate provider
        if self._is_crypto(symbol, asset_class):
            return self._fetch_crypto_metadata(symbol)
        else:
            return self._fetch_stock_metadata(symbol)

    def fetch_current_price(
        self, symbol: str, asset_class: str | None = None
    ) -> tuple[Decimal, datetime] | None:
        """Fetch current price from the appropriate provider.

        Args:
            symbol: Asset symbol
            asset_class: Known asset class (helps routing)

        Returns:
            Tuple of (price, timestamp) or None if not found
        """
        if self._is_crypto(symbol, asset_class):
            return self._fetch_crypto_price(symbol)
        else:
            return self._fetch_stock_price(symbol)

    def fetch_historical_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        asset_class: str | None = None,
    ) -> list[PricePoint]:
        """Fetch historical prices from the appropriate provider.

        Args:
            symbol: Asset symbol
            start_date: Start of date range
            end_date: End of date range
            asset_class: Known asset class (helps routing)

        Returns:
            List of PricePoint objects
        """
        if self._is_crypto(symbol, asset_class):
            return self._fetch_crypto_history(symbol, start_date, end_date)
        else:
            return self._fetch_stock_history(symbol, start_date, end_date)

    def _is_crypto(self, symbol: str, asset_class: str | None) -> bool:
        """Determine if an asset is cryptocurrency based on class or symbol heuristics."""
        if asset_class and asset_class in self.CRYPTO_ASSET_CLASSES:
            return True

        # Common crypto symbols
        known_crypto = {
            "BTC",
            "ETH",
            "LTC",
            "XRP",
            "USDC",
            "USDT",
            "DOGE",
            "ADA",
            "SOL",
            "DOT",
            "LINK",
            "MATIC",
            "UNI",
            "AVAX",
            "SHIB",
            "BNB",
        }
        return symbol.upper() in known_crypto

    def _fetch_stock_metadata(self, symbol: str) -> AssetMetadata | None:
        """Fetch stock/ETF metadata from YFinance."""
        info = self._yfinance.get_ticker_info(symbol)
        if not info:
            return None

        # Map quote_type to our asset_class
        asset_class = self._map_quote_type(info.quote_type)

        return AssetMetadata(
            symbol=symbol,
            name=info.name,
            asset_class=asset_class,
            sector=info.sector or info.category,  # sector for stocks, category for ETFs
            industry=info.industry,
            currency=info.currency,
            source="yfinance",
        )

    def _fetch_crypto_metadata(self, symbol: str) -> AssetMetadata | None:
        """Fetch cryptocurrency metadata from CoinGecko."""
        coin_info = self._coingecko.get_coin_info(symbol)
        if not coin_info:
            return None

        # Get categories as sector
        categories = coin_info.get("categories", [])
        sector = categories[0] if categories else "Cryptocurrency"

        return AssetMetadata(
            symbol=symbol,
            name=coin_info.get("name"),
            asset_class="Crypto",
            sector=sector,
            industry=None,
            currency="USD",
            source="coingecko",
        )

    def _fetch_stock_price(self, symbol: str) -> tuple[Decimal, datetime] | None:
        """Fetch stock/ETF price from YFinance."""
        return self._yfinance.get_current_price(symbol)

    def _fetch_crypto_price(self, symbol: str) -> tuple[Decimal, datetime] | None:
        """Fetch cryptocurrency price from CoinGecko with CryptoCompare fallback."""
        price = self._coingecko.get_current_price(symbol)
        if price is not None:
            return price, datetime.now()

        # Fallback to CryptoCompare
        logger.info(f"CoinGecko failed for {symbol}, trying CryptoCompare")
        price = self._cryptocompare.get_current_price(symbol)
        if price is not None:
            return price, datetime.now()

        return None

    def _fetch_stock_history(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[PricePoint]:
        """Fetch stock/ETF historical prices from YFinance."""
        # Calculate period based on date range
        days = (end_date - start_date).days
        if days <= 5:
            period = "5d"
        elif days <= 30:
            period = "1mo"
        elif days <= 90:
            period = "3mo"
        elif days <= 180:
            period = "6mo"
        elif days <= 365:
            period = "1y"
        elif days <= 730:
            period = "2y"
        else:
            period = "5y"

        history = self._yfinance.get_historical_data(symbol, period)

        # Filter to requested date range
        results = []
        for dt, price in history:
            d = dt.date() if isinstance(dt, datetime) else dt
            if start_date <= d <= end_date:
                results.append(PricePoint(date=d, price=price, source="yfinance"))

        return results

    def _fetch_crypto_history(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[PricePoint]:
        """Fetch cryptocurrency historical prices from CoinGecko."""
        history = self._coingecko.get_price_history(symbol, start_date, end_date)

        return [PricePoint(date=d, price=price, source="coingecko") for d, price in history]

    @staticmethod
    def _map_quote_type(quote_type: str | None) -> str:
        """Map YFinance quote type to our asset class."""
        mapping = {
            "EQUITY": "Stock",
            "ETF": "ETF",
            "MUTUALFUND": "MutualFund",
            "CRYPTOCURRENCY": "Crypto",
            "INDEX": "Index",
            "BOND": "Bond",
        }
        return mapping.get(quote_type, "Stock") if quote_type else "Stock"
