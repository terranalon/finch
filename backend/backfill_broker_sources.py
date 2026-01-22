"""Backfill existing transactions with legacy BrokerDataSource records.

This script creates 'legacy' source records for all existing transactions
that were imported before the broker data source tracking system was implemented.
This enables the overlap detector to work with existing data.
"""

import logging

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Account, BrokerDataSource, Holding, Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def backfill_broker_sources() -> dict[str, int]:
    """Create legacy BrokerDataSource records for existing transactions.

    Returns:
        Dictionary with statistics about the backfill operation.
    """
    db = SessionLocal()
    stats = {"accounts_processed": 0, "sources_created": 0, "transactions_linked": 0, "skipped": 0}

    try:
        # Get all accounts that have transactions
        accounts_with_transactions = (
            db.query(
                Account.id,
                Account.name,
                Account.broker_type,
                func.min(Transaction.date).label("min_date"),
                func.max(Transaction.date).label("max_date"),
                func.count(Transaction.id).label("txn_count"),
            )
            .join(Holding, Account.id == Holding.account_id)
            .join(Transaction, Holding.id == Transaction.holding_id)
            .group_by(Account.id, Account.name, Account.broker_type)
            .all()
        )

        logger.info("Found %d accounts with transactions", len(accounts_with_transactions))

        for account in accounts_with_transactions:
            account_id = account.id
            account_name = account.name
            min_date = account.min_date
            max_date = account.max_date
            txn_count = account.txn_count

            # Determine broker type (default to 'ibkr' for existing accounts)
            broker_type = account.broker_type or "ibkr"

            logger.info(
                "Processing account %d (%s): %d transactions from %s to %s",
                account_id,
                account_name,
                txn_count,
                min_date,
                max_date,
            )

            # Check if legacy source already exists for this account
            existing_legacy = (
                db.query(BrokerDataSource)
                .filter(
                    BrokerDataSource.account_id == account_id,
                    BrokerDataSource.source_type == "legacy",
                )
                .first()
            )

            if existing_legacy:
                logger.info("  Skipping - legacy source already exists (id=%d)", existing_legacy.id)
                stats["skipped"] += 1
                continue

            # Update account's broker_type if not set
            if not account.broker_type:
                db.query(Account).filter(Account.id == account_id).update(
                    {"broker_type": broker_type}
                )
                logger.info("  Updated account broker_type to '%s'", broker_type)

            # Create legacy source record
            legacy_source = BrokerDataSource(
                account_id=account_id,
                broker_type=broker_type,
                source_type="legacy",
                source_identifier="Legacy Import (Pre-Consolidation)",
                start_date=min_date,
                end_date=max_date,
                status="completed",
                import_stats={"transactions": txn_count, "note": "Backfilled from existing data"},
            )
            db.add(legacy_source)
            db.flush()  # Get the ID

            logger.info("  Created legacy source id=%d", legacy_source.id)
            stats["sources_created"] += 1

            # Link existing transactions to this source
            # First get the holding IDs for this account
            holding_ids = [
                h.id for h in db.query(Holding.id).filter(Holding.account_id == account_id).all()
            ]

            # Then update transactions with those holdings
            linked = (
                db.query(Transaction)
                .filter(
                    Transaction.holding_id.in_(holding_ids),
                    Transaction.broker_source_id.is_(None),
                )
                .update({"broker_source_id": legacy_source.id}, synchronize_session=False)
            )

            logger.info("  Linked %d transactions to legacy source", linked)
            stats["transactions_linked"] += linked
            stats["accounts_processed"] += 1

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
    logger.info("=== BACKFILLING BROKER DATA SOURCES ===\n")

    stats = backfill_broker_sources()

    logger.info("\n=== BACKFILL RESULTS ===")
    logger.info("Accounts processed: %d", stats["accounts_processed"])
    logger.info("Sources created: %d", stats["sources_created"])
    logger.info("Transactions linked: %d", stats["transactions_linked"])
    logger.info("Skipped (already had legacy): %d", stats["skipped"])
