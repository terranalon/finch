"""Service for fetching and storing daily asset prices."""

import logging
from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient

logger = logging.getLogger(__name__)

# Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
AGOROT_DIVISOR = Decimal("100")

# CoinGecko only has ~1 year of historical data
COINGECKO_HISTORY_LIMIT_DAYS = 365

GET_NON_CRYPTO_ASSETS = """
SELECT a.id, a.symbol, a.currency
FROM assets a
WHERE a.asset_class != 'Crypto'
AND EXISTS (SELECT 1 FROM holdings h WHERE h.asset_id = a.id AND h.is_active = true)
"""

GET_CRYPTO_ASSETS = """
SELECT a.id, a.symbol, a.currency
FROM assets a
WHERE a.asset_class = 'Crypto'
AND EXISTS (SELECT 1 FROM holdings h WHERE h.asset_id = a.id AND h.is_active = true)
"""

CHECK_ASSET_PRICE_EXISTS = """
SELECT 1 FROM asset_prices
WHERE asset_id = :asset_id AND date = :date
"""

INSERT_ASSET_PRICE = """
INSERT INTO asset_prices (asset_id, date, closing_price, currency, source)
VALUES (:asset_id, :date, :closing_price, :currency, :source)
"""


class DailyPriceService:
    """Service for refreshing daily asset prices."""

    @staticmethod
    def refresh_stock_prices(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store closing prices for non-crypto assets.

        Args:
            db: Database session
            target_date: Date to fetch prices for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        stats: dict = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "source": "yfinance",
            "errors": [],
        }

        assets = db.execute(text(GET_NON_CRYPTO_ASSETS)).fetchall()

        for asset_id, symbol, currency in assets:
            try:
                existing = db.execute(
                    text(CHECK_ASSET_PRICE_EXISTS),
                    {"asset_id": asset_id, "date": target_date},
                ).first()

                if existing:
                    logger.info("Price for %s already exists for %s", symbol, target_date)
                    stats["skipped"] += 1
                    continue

                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty and "Close" in hist.columns:
                    price = Decimal(str(hist["Close"].iloc[-1]))

                    # Convert Israeli stocks from Agorot to ILS
                    if symbol.endswith(".TA"):
                        price = price / AGOROT_DIVISOR

                    db.execute(
                        text(INSERT_ASSET_PRICE),
                        {
                            "asset_id": asset_id,
                            "date": target_date,
                            "closing_price": float(price),
                            "currency": currency or "USD",
                            "source": "Yahoo Finance",
                        },
                    )
                    db.commit()

                    logger.info("Updated %s: %s", symbol, price)
                    stats["updated"] += 1
                else:
                    logger.warning("No data for %s", symbol)
                    stats["failed"] += 1
                    stats["errors"].append({"symbol": symbol, "error": "No data available"})

            except Exception:
                logger.exception("Failed to fetch %s", symbol)
                stats["failed"] += 1
                stats["errors"].append({"symbol": symbol, "error": "Fetch failed"})
                db.rollback()

        return stats

    @staticmethod
    def refresh_crypto_prices(db: Session, target_date: date | None = None) -> dict:
        """
        Fetch and store prices for crypto assets.

        Uses CoinGecko for recent dates (<1 year), CryptoCompare for older dates.

        Args:
            db: Database session
            target_date: Date to fetch prices for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        days_ago = (date.today() - target_date).days
        use_coingecko = days_ago <= COINGECKO_HISTORY_LIMIT_DAYS

        stats: dict = {
            "date": target_date,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "source": "coingecko" if use_coingecko else "cryptocompare",
            "errors": [],
        }

        assets = db.execute(text(GET_CRYPTO_ASSETS)).fetchall()

        if not assets:
            logger.info("No crypto assets found")
            return stats

        # Collect assets needing prices
        assets_needing_prices = []
        for asset_id, symbol, _currency in assets:
            existing = db.execute(
                text(CHECK_ASSET_PRICE_EXISTS),
                {"asset_id": asset_id, "date": target_date},
            ).first()

            if existing:
                logger.info("Price for %s already exists for %s", symbol, target_date)
                stats["skipped"] += 1
            else:
                assets_needing_prices.append((asset_id, symbol))

        if not assets_needing_prices:
            logger.info("All crypto prices already up to date")
            return stats

        # Batch fetch prices
        symbols = [symbol for _, symbol in assets_needing_prices]

        if use_coingecko:
            prices = _fetch_coingecko_prices(symbols)
        else:
            prices = _fetch_cryptocompare_prices(symbols, target_date)

        # Store prices
        for asset_id, symbol in assets_needing_prices:
            try:
                price = prices.get(symbol)
                if price is not None:
                    db.execute(
                        text(INSERT_ASSET_PRICE),
                        {
                            "asset_id": asset_id,
                            "date": target_date,
                            "closing_price": float(price),
                            "currency": "USD",
                            "source": "CoinGecko" if use_coingecko else "CryptoCompare",
                        },
                    )
                    db.commit()

                    logger.info("Updated %s: %s", symbol, price)
                    stats["updated"] += 1
                else:
                    error_msg = "No price returned from API"
                    logger.warning("%s: %s", symbol, error_msg)
                    stats["failed"] += 1
                    stats["errors"].append({"symbol": symbol, "error": error_msg})

            except Exception:
                logger.exception("Failed to store %s", symbol)
                stats["failed"] += 1
                stats["errors"].append({"symbol": symbol, "error": "Store failed"})
                db.rollback()

        return stats


def _fetch_coingecko_prices(symbols: list[str]) -> dict[str, Decimal]:
    """Fetch current prices from CoinGecko."""
    client = CoinGeckoClient()
    return client.get_current_prices(symbols, "usd")


def _fetch_cryptocompare_prices(symbols: list[str], target_date: date) -> dict[str, Decimal]:
    """Fetch historical prices from CryptoCompare."""
    client = CryptoCompareClient()
    prices: dict[str, Decimal] = {}
    for symbol in symbols:
        price = client.get_historical_price(symbol, target_date)
        if price is not None:
            prices[symbol] = price
    return prices
