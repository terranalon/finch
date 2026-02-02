"""Backfill price_per_unit for crypto deposit transactions.

This script populates the price_per_unit field for existing crypto deposits
that are missing cost basis data. It fetches historical prices from CoinGecko.

Run from backend directory:
    python backfill_deposit_prices.py [account_id]
"""

import logging
import sys
import time
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction
from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_deposits_missing_price(
    db: Session, account_id: int | None = None
) -> list[tuple[Transaction, Asset]]:
    """Get crypto deposits that are missing price_per_unit.

    Args:
        db: Database session
        account_id: Optional account ID filter

    Returns:
        List of (Transaction, Asset) tuples for deposits needing prices
    """
    query = (
        db.query(Transaction, Asset)
        .join(Holding, Transaction.holding_id == Holding.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(
            Transaction.type == "Deposit",
            Transaction.price_per_unit.is_(None),
            Asset.asset_class == "Crypto",
        )
    )

    if account_id:
        query = query.filter(Holding.account_id == account_id)

    return query.all()


def group_by_symbol_date(
    deposits: list[tuple[Transaction, Asset]],
) -> dict[tuple[str, date], list[Transaction]]:
    """Group deposits by (symbol, date) to minimize API calls.

    Args:
        deposits: List of (Transaction, Asset) tuples

    Returns:
        Dict mapping (symbol, date) to list of transactions
    """
    grouped: dict[tuple[str, date], list[Transaction]] = defaultdict(list)
    for txn, asset in deposits:
        key = (asset.symbol, txn.date)
        grouped[key].append(txn)
    return grouped


def backfill_deposit_prices(account_id: int | None = None) -> dict:
    """Backfill price_per_unit for crypto deposit transactions.

    Uses CoinGecko for recent prices, falls back to CryptoCompare for older data
    (CoinGecko free tier limits historical data to ~365 days).

    Args:
        account_id: Optional account ID to filter (None = all accounts)

    Returns:
        Dictionary with statistics about the backfill operation
    """
    db = SessionLocal()
    coingecko = CoinGeckoClient()
    cryptocompare = CryptoCompareClient()

    stats = {
        "account_id": account_id,
        "total_deposits": 0,
        "unique_lookups": 0,
        "prices_found": 0,
        "transactions_updated": 0,
        "prices_not_found": [],
        "errors": [],
    }

    try:
        deposits = get_deposits_missing_price(db, account_id)
        stats["total_deposits"] = len(deposits)

        if not deposits:
            logger.info("No crypto deposits missing price_per_unit")
            return stats

        logger.info("Found %d crypto deposits missing price_per_unit", len(deposits))

        grouped = group_by_symbol_date(deposits)
        stats["unique_lookups"] = len(grouped)
        logger.info("Grouped into %d unique (symbol, date) combinations", len(grouped))

        for (symbol, txn_date), transactions in grouped.items():
            logger.info(
                "Fetching price for %s on %s (%d txns)", symbol, txn_date, len(transactions)
            )

            price = None
            try:
                # Try CoinGecko first (better for recent data)
                price = coingecko.get_historical_price(symbol, txn_date, vs_currency="usd")

                if price is None:
                    # Fall back to CryptoCompare for older data
                    logger.info("  CoinGecko failed, trying CryptoCompare...")
                    price = cryptocompare.get_historical_price(symbol, txn_date, vs_currency="USD")

                if price is not None:
                    stats["prices_found"] += 1
                    logger.info("  Found price: $%s", price)

                    for txn in transactions:
                        txn.price_per_unit = price
                        stats["transactions_updated"] += 1

                    db.commit()
                else:
                    logger.warning("  No price found for %s on %s", symbol, txn_date)
                    stats["prices_not_found"].append({"symbol": symbol, "date": str(txn_date)})

            except Exception as e:
                logger.error("  Error fetching price for %s on %s: %s", symbol, txn_date, e)
                stats["errors"].append({"symbol": symbol, "date": str(txn_date), "error": str(e)})
                db.rollback()

            # Rate limiting: 2 second delay between API calls
            time.sleep(2)

        logger.info("Backfill complete!")

    except Exception as e:
        logger.exception("Error during backfill: %s", e)
        raise
    finally:
        db.close()

    return stats


def print_stats(stats: dict) -> None:
    """Print backfill statistics."""
    logger.info("=== BACKFILL RESULTS ===")
    logger.info("Account filter: %s", stats["account_id"] or "all accounts")
    logger.info("Total deposits found: %d", stats["total_deposits"])
    logger.info("Unique (symbol, date) lookups: %d", stats["unique_lookups"])
    logger.info("Prices found: %d", stats["prices_found"])
    logger.info("Transactions updated: %d", stats["transactions_updated"])

    if stats["prices_not_found"]:
        logger.info("Prices not found:")
        for item in stats["prices_not_found"]:
            logger.info("  %s on %s", item["symbol"], item["date"])

    if stats["errors"]:
        logger.info("Errors:")
        for item in stats["errors"]:
            logger.info("  %s on %s: %s", item["symbol"], item["date"], item["error"])


if __name__ == "__main__":
    target_account_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    if target_account_id:
        logger.info("=== BACKFILLING DEPOSIT PRICES FOR ACCOUNT %d ===\n", target_account_id)
    else:
        logger.info("=== BACKFILLING DEPOSIT PRICES FOR ALL ACCOUNTS ===\n")

    results = backfill_deposit_prices(target_account_id)
    print_stats(results)
