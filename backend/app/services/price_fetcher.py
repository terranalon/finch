"""Price fetching service for asset prices."""

import logging
from datetime import date, datetime
from decimal import Decimal

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.models.asset_price import AssetPrice
from app.services.coingecko_client import CoinGeckoClient

logger = logging.getLogger(__name__)

# Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
_AGOROT_DIVISOR = Decimal("100")

# Lazy-loaded CoinGecko client (singleton)
_coingecko_client: CoinGeckoClient | None = None


def _get_coingecko_client() -> CoinGeckoClient:
    """Get or create the CoinGecko client singleton."""
    global _coingecko_client
    if _coingecko_client is None:
        _coingecko_client = CoinGeckoClient()
    return _coingecko_client


class PriceFetcher:
    """Service for fetching and updating asset prices from external sources."""

    @staticmethod
    def _fetch_price_for_asset(asset: Asset) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for an asset, routing to the appropriate data source.

        Crypto assets use CoinGecko, all others use Yahoo Finance.

        Args:
            asset: Asset model instance

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        if asset.asset_class == "Crypto":
            return PriceFetcher.fetch_crypto_price(asset.symbol, "usd")
        return PriceFetcher.fetch_price(asset.symbol)

    @staticmethod
    def fetch_price(symbol: str) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for a single symbol from Yahoo Finance.

        Args:
            symbol: The ticker symbol (e.g., 'AAPL', 'BTC-USD')

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Try to get current price from different fields (in order of preference)
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )

            if price and price > 0:
                price_decimal = Decimal(str(price))

                # Convert Israeli stocks from Agorot to ILS
                if symbol.endswith(".TA"):
                    price_decimal = price_decimal / _AGOROT_DIVISOR
                    logger.debug(f"Converted {symbol} price from Agorot to ILS: {price_decimal}")

                return price_decimal, datetime.now()

            logger.warning(f"No valid price found for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None

    @staticmethod
    def fetch_prices_batch(symbols: list[str]) -> dict[str, tuple[Decimal, datetime]]:
        """
        Fetch prices for multiple symbols.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary mapping symbol to (price, timestamp) tuples
        """
        results = {}

        for symbol in symbols:
            result = PriceFetcher.fetch_price(symbol)
            if result:
                results[symbol] = result

        return results

    @staticmethod
    def fetch_crypto_price(
        symbol: str, vs_currency: str = "usd"
    ) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for a cryptocurrency from CoinGecko.

        Args:
            symbol: The crypto symbol (e.g., 'BTC', 'ETH')
            vs_currency: Quote currency (default: 'usd')

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        try:
            client = _get_coingecko_client()
            price = client.get_current_price(symbol, vs_currency)

            if price and price > 0:
                logger.info(
                    f"Fetched crypto price for {symbol} from CoinGecko: {price} {vs_currency.upper()}"
                )
                return price, datetime.now()

            logger.warning(f"No valid crypto price found for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error fetching crypto price for {symbol}: {str(e)}")
            return None

    @staticmethod
    def update_asset_price(db: Session, asset: Asset) -> bool:
        """
        Update price for a single asset in the database.

        Args:
            db: Database session
            asset: Asset model instance

        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = PriceFetcher._fetch_price_for_asset(asset)
            if result:
                price, timestamp = result
                asset.last_fetched_price = price
                asset.last_fetched_at = timestamp
                db.commit()
                logger.info(f"Updated price for {asset.symbol}: {price}")
                return True
            else:
                logger.warning(f"Failed to fetch price for {asset.symbol}")
                return False

        except Exception as e:
            logger.error(f"Error updating price for {asset.symbol}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def update_all_asset_prices(db: Session, asset_class: str | None = None) -> dict[str, int]:
        """
        Update prices for all assets (or filtered by asset class).

        Crypto assets are batched in a single API call to avoid rate limits.

        Args:
            db: Database session
            asset_class: Optional filter for specific asset class

        Returns:
            Dictionary with update statistics
        """
        query = select(Asset)

        if asset_class:
            query = query.where(Asset.asset_class == asset_class)

        assets = db.execute(query).scalars().all()

        stats = {"total": len(assets), "updated": 0, "failed": 0, "skipped": 0}

        # Separate crypto and non-crypto assets
        crypto_assets = []
        other_assets = []

        for asset in assets:
            if not asset.symbol:
                stats["skipped"] += 1
                continue
            if asset.asset_class == "Cash":
                stats["skipped"] += 1
                continue

            if asset.asset_class == "Crypto":
                crypto_assets.append(asset)
            else:
                other_assets.append(asset)

        # Batch fetch crypto prices in a single API call
        if crypto_assets:
            crypto_symbols = [a.symbol for a in crypto_assets]
            logger.info(f"Batch fetching prices for {len(crypto_symbols)} crypto assets")

            try:
                client = _get_coingecko_client()
                crypto_prices = client.get_current_prices(crypto_symbols, "usd")

                for asset in crypto_assets:
                    price = crypto_prices.get(asset.symbol)
                    if price and price > 0:
                        asset.last_fetched_price = price
                        asset.last_fetched_at = datetime.now()
                        stats["updated"] += 1
                        logger.debug(f"Updated crypto price for {asset.symbol}: {price}")
                    else:
                        stats["failed"] += 1
                        logger.warning(f"No price found for crypto {asset.symbol}")

                db.commit()
            except Exception as e:
                logger.error(f"Error batch fetching crypto prices: {e}")
                stats["failed"] += len(crypto_assets)

        # Fetch non-crypto prices one by one (Yahoo Finance)
        for asset in other_assets:
            success = PriceFetcher.update_asset_price(db, asset)
            if success:
                stats["updated"] += 1
            else:
                stats["failed"] += 1

        logger.info(f"Price update complete: {stats}")
        return stats

    @staticmethod
    def get_historical_prices(symbol: str, period: str = "1mo") -> dict | None:
        """
        Get historical price data for a symbol.

        Args:
            symbol: The ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Dictionary with historical data or None if fetch failed
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None

            # Convert to dictionary format
            data = {"symbol": symbol, "period": period, "data": []}

            # Convert Israeli stocks from Agorot to ILS
            is_israeli_stock = symbol.endswith(".TA")
            divisor = float(_AGOROT_DIVISOR) if is_israeli_stock else 1.0

            for hist_date, row in hist.iterrows():
                data["data"].append(
                    {
                        "date": hist_date.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]) / divisor,
                        "high": float(row["High"]) / divisor,
                        "low": float(row["Low"]) / divisor,
                        "close": float(row["Close"]) / divisor,
                        "volume": int(row["Volume"]) if "Volume" in row else 0,
                    }
                )

            if is_israeli_stock:
                logger.debug(f"Converted {symbol} historical prices from Agorot to ILS")

            return data

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

    @staticmethod
    def get_price_for_date(db: Session, asset_id: int, target_date: date) -> Decimal | None:
        """
        Get asset price for a specific date.

        - For past dates: Returns closing price from asset_prices table
        - For today: Returns current price from Asset.last_fetched_price (fetches if stale)
        - For future dates: Returns None

        Args:
            db: Database session
            asset_id: Asset ID
            target_date: Date for price lookup

        Returns:
            Price as Decimal, or None if not found
        """
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.warning(f"Asset {asset_id} not found")
            return None

        if target_date < date.today():
            # Historical date - use closing price from asset_prices table
            asset_price = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset_id, AssetPrice.date == target_date)
                .first()
            )

            if asset_price:
                return asset_price.closing_price

            # Forward-fill: use most recent historical price before target_date
            # This handles weekends, holidays, and gaps in historical data
            most_recent_price = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset_id, AssetPrice.date < target_date)
                .order_by(AssetPrice.date.desc())
                .first()
            )

            if most_recent_price:
                logger.debug(
                    f"No price for {asset.symbol} on {target_date}, "
                    f"forward-filling from {most_recent_price.date}"
                )
                return most_recent_price.closing_price

            # Only fall back to last_fetched_price if no historical data exists at all
            logger.warning(
                f"No historical price data for {asset.symbol} before {target_date}, "
                f"using last_fetched_price"
            )
            return asset.last_fetched_price

        elif target_date == date.today():
            # Current day - use last_fetched_price (fetch if stale)
            is_stale = (
                not asset.last_fetched_at
                or (datetime.now() - asset.last_fetched_at).total_seconds() > 300
            )
            if is_stale:
                logger.info(f"Fetching fresh price for {asset.symbol}")
                result = PriceFetcher._fetch_price_for_asset(asset)
                if result:
                    asset.last_fetched_price, asset.last_fetched_at = result
                    db.commit()

            return asset.last_fetched_price

        else:
            # Future date
            logger.warning(f"Cannot get price for future date: {target_date}")
            return None
