"""Backfill historical crypto prices from CryptoCompare.

This script fetches historical prices for all crypto assets that have
transactions in a given account, using CryptoCompare for data older
than 365 days (CoinGecko free tier limitation).

Run from backend directory:
    python backfill_crypto_prices.py [account_id]
"""

import logging
import sys
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Asset, AssetPrice, Holding, Transaction
from app.services.cryptocompare_client import CryptoCompareClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_crypto_assets_for_account(db: Session, account_id: int) -> list[Asset]:
    """Get all crypto assets that have transactions in the account."""
    asset_ids = (
        db.query(Holding.asset_id)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(
            Holding.account_id == account_id,
            Asset.asset_class == "Crypto",
        )
        .distinct()
        .all()
    )
    asset_ids = [a[0] for a in asset_ids]

    if not asset_ids:
        return []

    return db.query(Asset).filter(Asset.id.in_(asset_ids)).all()


def get_earliest_transaction_date(db: Session, account_id: int) -> date | None:
    """Get the earliest transaction date for an account."""
    result = (
        db.query(func.min(Transaction.date))
        .join(Holding, Transaction.holding_id == Holding.id)
        .filter(Holding.account_id == account_id)
        .scalar()
    )
    return result


def backfill_prices_for_asset(
    db: Session,
    client: CryptoCompareClient,
    asset: Asset,
    start_date: date,
    end_date: date,
) -> dict:
    """Fetch and store historical prices for a single asset."""
    stats = {
        "symbol": asset.symbol,
        "fetched": 0,
        "stored": 0,
        "skipped_existing": 0,
        "errors": [],
    }

    logger.info("Fetching prices for %s from %s to %s", asset.symbol, start_date, end_date)

    try:
        # Fetch price history from CryptoCompare
        prices = client.get_price_history(asset.symbol, start_date, end_date, "USD")
        stats["fetched"] = len(prices)

        if not prices:
            logger.warning("No price data returned for %s", asset.symbol)
            return stats

        # Store prices in database
        for price_date, price in prices:
            # Check if price already exists
            existing = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset.id, AssetPrice.date == price_date)
                .first()
            )

            if existing:
                stats["skipped_existing"] += 1
                continue

            asset_price = AssetPrice(
                asset_id=asset.id,
                date=price_date,
                closing_price=price,
                currency="USD",
                source="cryptocompare",
            )
            db.add(asset_price)
            stats["stored"] += 1

        db.commit()
        logger.info(
            "  %s: fetched=%d, stored=%d, skipped=%d",
            asset.symbol,
            stats["fetched"],
            stats["stored"],
            stats["skipped_existing"],
        )

    except Exception as e:
        logger.error("Error fetching prices for %s: %s", asset.symbol, e)
        stats["errors"].append(str(e))
        db.rollback()

    return stats


def backfill_crypto_prices(account_id: int) -> dict:
    """Backfill historical prices for all crypto assets in an account.

    Args:
        account_id: Account ID to backfill prices for

    Returns:
        Dictionary with statistics about the backfill operation
    """
    db = SessionLocal()
    client = CryptoCompareClient()

    stats = {
        "account_id": account_id,
        "assets_processed": 0,
        "total_prices_fetched": 0,
        "total_prices_stored": 0,
        "asset_stats": [],
    }

    try:
        earliest_date = get_earliest_transaction_date(db, account_id)
        if not earliest_date:
            logger.warning("No transactions found for account %d", account_id)
            return stats

        end_date = date.today()
        logger.info("Backfilling prices from %s to %s", earliest_date, end_date)

        assets = get_crypto_assets_for_account(db, account_id)
        logger.info("Found %d crypto assets to process", len(assets))

        for asset in assets:
            asset_stats = backfill_prices_for_asset(db, client, asset, earliest_date, end_date)
            stats["asset_stats"].append(asset_stats)
            stats["assets_processed"] += 1
            stats["total_prices_fetched"] += asset_stats["fetched"]
            stats["total_prices_stored"] += asset_stats["stored"]

        logger.info("Backfill complete!")

    except Exception as e:
        logger.exception("Error during backfill: %s", e)
        raise
    finally:
        db.close()

    return stats


if __name__ == "__main__":
    target_account_id = int(sys.argv[1]) if len(sys.argv) > 1 else 23

    logger.info("=== BACKFILLING CRYPTO PRICES FOR ACCOUNT %d ===\n", target_account_id)

    results = backfill_crypto_prices(target_account_id)

    logger.info("\n=== BACKFILL RESULTS ===")
    logger.info("Account: %d", results["account_id"])
    logger.info("Assets processed: %d", results["assets_processed"])
    logger.info("Total prices fetched: %d", results["total_prices_fetched"])
    logger.info("Total prices stored: %d", results["total_prices_stored"])

    logger.info("\nPer-asset breakdown:")
    for asset_stat in results["asset_stats"]:
        logger.info(
            "  %s: fetched=%d, stored=%d, skipped=%d",
            asset_stat["symbol"],
            asset_stat["fetched"],
            asset_stat["stored"],
            asset_stat["skipped_existing"],
        )
