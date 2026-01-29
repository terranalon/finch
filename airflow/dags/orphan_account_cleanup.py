"""
Orphan Account Cleanup DAG

Deletes accounts that are no longer linked to any portfolio.
This can happen when accounts are unlinked from all portfolios.

Schedule: Weekly on Sunday at 3:00 AM UTC
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow.sdk import dag, task
from shared_db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Query to find orphan accounts (accounts with no portfolio links)
FIND_ORPHAN_ACCOUNTS = """
SELECT a.id, a.name, a.broker_type
FROM accounts a
LEFT JOIN portfolio_accounts pa ON a.id = pa.account_id
WHERE pa.account_id IS NULL
"""

default_args = {
    "owner": "portfolio_tracker",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="orphan_account_cleanup",
    default_args=default_args,
    description="Weekly cleanup of accounts not linked to any portfolio",
    schedule="0 3 * * 0",  # Sunday at 3:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["maintenance", "cleanup"],
)
def orphan_account_cleanup():
    """Delete accounts that have no portfolio links."""

    @task(task_id="cleanup_orphan_accounts")
    def cleanup_orphan_accounts() -> dict[str, int | list[str]]:
        """Find and delete orphan accounts using ORM for proper cascade."""
        # Import Account model from backend
        if "/opt/airflow/backend" not in sys.path:
            sys.path.insert(0, "/opt/airflow/backend")
        from app.models.account import Account

        session = SessionLocal()

        try:
            # Find orphan account IDs using raw SQL (efficient)
            orphan_rows = session.execute(text(FIND_ORPHAN_ACCOUNTS)).fetchall()

            stats = {
                "found": len(orphan_rows),
                "deleted": 0,
                "failed": 0,
                "deleted_accounts": [],
            }

            if not orphan_rows:
                logger.info("No orphan accounts found")
                return stats

            logger.info(f"Found {len(orphan_rows)} orphan account(s)")

            for account_id, account_name, broker_type in orphan_rows:
                try:
                    # Use ORM to delete - triggers cascade for holdings, snapshots, etc.
                    account = session.get(Account, account_id)
                    if account:
                        session.delete(account)
                        session.commit()

                        logger.info(f"Deleted orphan account: {account_name} (id={account_id})")
                        stats["deleted"] += 1
                        stats["deleted_accounts"].append(f"{account_name} ({broker_type})")
                    else:
                        logger.warning(f"Account {account_id} not found (already deleted?)")

                except Exception as e:
                    logger.error(f"Failed to delete account {account_name}: {str(e)}")
                    stats["failed"] += 1
                    session.rollback()
                    continue

            logger.info(
                f"Cleanup complete: {stats['deleted']} deleted, {stats['failed']} failed"
            )
            return stats

        except Exception as e:
            logger.error(f"Orphan cleanup failed: {str(e)}")
            raise
        finally:
            session.close()

    cleanup_orphan_accounts()


dag_instance = orphan_account_cleanup()
