"""Backfill BrokerDataSource records for existing Kraken accounts.

This script creates 'api_fetch' source records for Kraken accounts that have
transactions but no BrokerDataSource tracking records. This enables the
Data Coverage card to display information for these accounts.

Run from backend directory:
    python backfill_kraken_sources.py
"""

import logging

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Account, BrokerDataSource, Holding, Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def backfill_kraken_sources() -> dict[str, int]:
    """Create BrokerDataSource records for Kraken accounts missing them.

    Returns:
        Dictionary with statistics about the backfill operation.
    """
    db = SessionLocal()
    stats = {
        "accounts_found": 0,
        "sources_created": 0,
        "transactions_linked": 0,
        "skipped_has_source": 0,
        "skipped_no_transactions": 0,
    }

    try:
        # Find all Kraken accounts
        kraken_accounts = db.query(Account).filter(Account.broker_type == "kraken").all()

        logger.info("Found %d Kraken accounts", len(kraken_accounts))
        stats["accounts_found"] = len(kraken_accounts)

        for account in kraken_accounts:
            account_id = account.id
            account_name = account.name

            logger.info("Processing account %d (%s)", account_id, account_name)

            # Check if any BrokerDataSource already exists for this account
            existing_source = (
                db.query(BrokerDataSource).filter(BrokerDataSource.account_id == account_id).first()
            )

            if existing_source:
                logger.info(
                    "  Skipping - source already exists (id=%d, type=%s)",
                    existing_source.id,
                    existing_source.source_type,
                )
                stats["skipped_has_source"] += 1
                continue

            # Get transaction date range and count for this account
            txn_stats = (
                db.query(
                    func.min(Transaction.date).label("min_date"),
                    func.max(Transaction.date).label("max_date"),
                    func.count(Transaction.id).label("txn_count"),
                )
                .join(Holding, Transaction.holding_id == Holding.id)
                .filter(Holding.account_id == account_id)
                .first()
            )

            if not txn_stats or not txn_stats.min_date:
                logger.info("  Skipping - no transactions found")
                stats["skipped_no_transactions"] += 1
                continue

            min_date = txn_stats.min_date
            max_date = txn_stats.max_date
            txn_count = txn_stats.txn_count

            logger.info(
                "  Found %d transactions from %s to %s",
                txn_count,
                min_date,
                max_date,
            )

            # Create BrokerDataSource record
            broker_source = BrokerDataSource(
                account_id=account_id,
                broker_type="kraken",
                source_type="api_fetch",
                source_identifier="Legacy API Import (Backfilled)",
                start_date=min_date,
                end_date=max_date,
                status="completed",
                import_stats={
                    "transactions": txn_count,
                    "note": "Backfilled from existing transactions",
                },
            )
            db.add(broker_source)
            db.flush()

            logger.info("  Created BrokerDataSource id=%d", broker_source.id)
            stats["sources_created"] += 1

            # Link existing transactions to this source
            holding_ids = [
                h.id for h in db.query(Holding.id).filter(Holding.account_id == account_id).all()
            ]

            linked = (
                db.query(Transaction)
                .filter(
                    Transaction.holding_id.in_(holding_ids),
                    Transaction.broker_source_id.is_(None),
                )
                .update({"broker_source_id": broker_source.id}, synchronize_session=False)
            )

            logger.info("  Linked %d transactions to source", linked)
            stats["transactions_linked"] += linked

        db.commit()
        logger.info("Backfill complete!")

    except Exception as e:
        db.rollback()
        logger.exception("Error during backfill: %s", e)
        raise
    finally:
        db.close()

    return stats


if __name__ == "__main__":
    logger.info("=== BACKFILLING KRAKEN BROKER DATA SOURCES ===\n")

    stats = backfill_kraken_sources()

    logger.info("\n=== BACKFILL RESULTS ===")
    logger.info("Kraken accounts found: %d", stats["accounts_found"])
    logger.info("Sources created: %d", stats["sources_created"])
    logger.info("Transactions linked: %d", stats["transactions_linked"])
    logger.info("Skipped (already had source): %d", stats["skipped_has_source"])
    logger.info("Skipped (no transactions): %d", stats["skipped_no_transactions"])
