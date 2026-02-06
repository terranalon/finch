"""Service for fetching and storing daily asset prices."""

import logging
from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.holding import Holding
from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient

logger = logging.getLogger(__name__)

# Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
AGOROT_DIVISOR = Decimal("100")

# CoinGecko only has ~1 year of historical data
COINGECKO_HISTORY_LIMIT_DAYS = 365


def _get_active_assets(db: Session, *, is_crypto: bool) -> list[Asset]:
    """Query assets with active holdings, filtered by asset class."""
    op = Asset.asset_class.__eq__ if is_crypto else Asset.asset_class.__ne__
    return (
        db.query(Asset)
        .filter(
            op("Crypto"),
            Asset.holdings.any(Holding.is_active.is_(True)),
        )
        .all()
    )


def _price_exists(db: Session, asset_id: int, target_date: date) -> bool:
    """Check whether a price record already exists for the given asset and date."""
    return (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == asset_id, AssetPrice.date == target_date)
        .first()
        is not None
    )


def _store_price(
    db: Session,
    *,
    asset_id: int,
    target_date: date,
    closing_price: Decimal,
    currency: str,
    source: str,
) -> None:
    """Add a new price record to the session (does not commit)."""
    db.add(
        AssetPrice(
            asset_id=asset_id,
            date=target_date,
            closing_price=closing_price,
            currency=currency,
            source=source,
        )
    )


class DailyPriceService:
    """Service for refreshing daily asset prices."""

    @staticmethod
    def refresh_stock_prices(db: Session, target_date: date | None = None) -> dict:
        """Fetch and store closing prices for non-crypto assets.

        Args:
            db: Database session
            target_date: Date to fetch prices for (defaults to yesterday)

        Returns:
            Dict with update statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        updated = 0
        skipped = 0
        failed = 0
        errors: list[dict[str, str]] = []

        assets = _get_active_assets(db, is_crypto=False)

        for asset in assets:
            try:
                if _price_exists(db, asset.id, target_date):
                    logger.info("Price for %s already exists for %s", asset.symbol, target_date)
                    skipped += 1
                    continue

                ticker = yf.Ticker(asset.symbol)
                hist = ticker.history(period="5d")

                if hist.empty or "Close" not in hist.columns:
                    logger.warning("No data for %s", asset.symbol)
                    failed += 1
                    errors = [*errors, {"symbol": asset.symbol, "error": "No data available"}]
                    continue

                price = Decimal(str(hist["Close"].iloc[-1]))

                # Convert Israeli stocks from Agorot to ILS
                if asset.symbol.endswith(".TA"):
                    price = price / AGOROT_DIVISOR

                _store_price(
                    db,
                    asset_id=asset.id,
                    target_date=target_date,
                    closing_price=price,
                    currency=asset.currency or "USD",
                    source="Yahoo Finance",
                )
                db.commit()

                logger.info("Updated %s: %s", asset.symbol, price)
                updated += 1

            except Exception:
                logger.exception("Failed to fetch %s", asset.symbol)
                failed += 1
                errors = [*errors, {"symbol": asset.symbol, "error": "Fetch failed"}]
                db.rollback()

        return {
            "date": target_date,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "source": "yfinance",
            "errors": errors,
        }

    @staticmethod
    def refresh_crypto_prices(db: Session, target_date: date | None = None) -> dict:
        """Fetch and store prices for crypto assets.

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
        source = "CoinGecko" if use_coingecko else "CryptoCompare"

        updated = 0
        skipped = 0
        failed = 0
        errors: list[dict[str, str]] = []

        assets = _get_active_assets(db, is_crypto=True)

        if not assets:
            logger.info("No crypto assets found")
            return {
                "date": target_date,
                "updated": 0,
                "skipped": 0,
                "failed": 0,
                "source": source.lower(),
                "errors": [],
            }

        # Collect assets needing prices
        assets_needing_prices: list[Asset] = []
        for asset in assets:
            if _price_exists(db, asset.id, target_date):
                logger.info("Price for %s already exists for %s", asset.symbol, target_date)
                skipped += 1
            else:
                assets_needing_prices = [*assets_needing_prices, asset]

        if not assets_needing_prices:
            logger.info("All crypto prices already up to date")
            return {
                "date": target_date,
                "updated": 0,
                "skipped": skipped,
                "failed": 0,
                "source": source.lower(),
                "errors": [],
            }

        # Batch fetch prices from the appropriate provider
        symbols = [asset.symbol for asset in assets_needing_prices]

        if use_coingecko:
            prices = CoinGeckoClient().get_current_prices(symbols, "usd")
        else:
            client = CryptoCompareClient()
            prices = {
                symbol: price
                for symbol in symbols
                if (price := client.get_historical_price(symbol, target_date)) is not None
            }

        # Store prices
        for asset in assets_needing_prices:
            try:
                price = prices.get(asset.symbol)
                if price is None:
                    logger.warning("%s: No price returned from API", asset.symbol)
                    failed += 1
                    errors = [
                        *errors,
                        {"symbol": asset.symbol, "error": "No price returned from API"},
                    ]
                    continue

                _store_price(
                    db,
                    asset_id=asset.id,
                    target_date=target_date,
                    closing_price=price,
                    currency="USD",
                    source=source,
                )

                logger.info("Updated %s: %s", asset.symbol, price)
                updated += 1

            except Exception:
                logger.exception("Failed to store %s", asset.symbol)
                failed += 1
                errors = [*errors, {"symbol": asset.symbol, "error": "Store failed"}]
                db.rollback()

        if updated > 0:
            try:
                db.commit()
            except Exception:
                logger.exception("Failed to commit crypto prices")
                db.rollback()
                failed += updated
                updated = 0

        return {
            "date": target_date,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "source": source.lower(),
            "errors": errors,
        }
