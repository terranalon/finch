"""Historical snapshot service for portfolio tracking."""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account
from app.services.market_data.historical_data_fetcher import HistoricalDataFetcher
from app.services.portfolio.holding_valuation_service import HoldingValuationService
from app.services.portfolio.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.repositories import AccountRepository
from app.services.repositories.snapshot_repository import SnapshotRepository

logger = logging.getLogger(__name__)


def update_snapshot_status(db: Session, account_id: int, status: str | None) -> None:
    """Update the snapshot_status field for an account.

    Args:
        db: Database session
        account_id: Account to update
        status: New status value ('generating', 'ready', 'failed', or None to clear)
    """
    account = AccountRepository(db).find_by_id(account_id)
    if account:
        account.snapshot_status = status
        db.commit()


def generate_snapshots_background(account_id: int, start_date: date) -> None:
    """Background task to generate historical snapshots after import.

    This function runs in a separate thread/task after the HTTP response
    has been sent. It generates historical snapshots for the account
    from the start_date to today.

    Args:
        account_id: Account to generate snapshots for
        start_date: Earliest date from the imported data
    """
    import time

    from app.database import SessionLocal

    # Brief delay to ensure import transaction is fully committed and visible
    # This prevents race conditions where the background task starts before
    # the database transaction isolation allows visibility of new records
    time.sleep(2)

    db = SessionLocal()
    try:
        # Verify we can see recent data before generating snapshots
        # This catches cases where the import transaction isn't yet visible
        from app.services.repositories import TransactionRepository

        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            recent_txn_count = TransactionRepository(db).count_by_account(account_id)
            if recent_txn_count > 0:
                break
            if attempt < max_retries - 1:
                logger.warning(
                    "No transactions found for account %d after import - "
                    "possible race condition, retry %d/%d after %ds delay",
                    account_id,
                    attempt + 1,
                    max_retries - 1,
                    retry_delay,
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        else:
            logger.warning(
                "No transactions found for account %d after %d retries - "
                "proceeding with snapshot generation anyway",
                account_id,
                max_retries,
            )

        svc = SnapshotService(db)
        svc.generate_account_snapshots(
            account_id, start_date, date.today(), invalidate_existing=True
        )
        update_snapshot_status(db, account_id, "ready")
        logger.info("Background snapshot generation complete for account %d", account_id)
    except Exception:
        logger.exception("Background snapshot generation failed for account %d", account_id)
        update_snapshot_status(db, account_id, "failed")
    finally:
        db.close()


class SnapshotService:
    """Service for creating and managing portfolio snapshots.

    Instance-based: stores a db session and delegates holding valuation
    to HoldingValuationService.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._valuation = HoldingValuationService(db)
        self._snapshot_repo = SnapshotRepository(db)
        self._account_repo = AccountRepository(db)

    def create_portfolio_snapshot(
        self,
        snapshot_date: date | None = None,
        allowed_account_ids: list[int] | None = None,
    ) -> dict:
        """Create a snapshot of the entire portfolio or specific accounts.

        Args:
            snapshot_date: Date for the snapshot (defaults to today)
            allowed_account_ids: List of account IDs to snapshot (defaults to all)

        Returns:
            Dictionary with snapshot statistics
        """
        if not snapshot_date:
            snapshot_date = date.today()

        stats = {
            "date": snapshot_date.isoformat(),
            "snapshots_created": 0,
            "total_value_usd": Decimal("0"),
            "accounts": [],
        }

        if allowed_account_ids is not None:
            accounts = self._account_repo.find_by_ids(allowed_account_ids)
        else:
            accounts = self._account_repo.find_by_ids(self._account_repo.find_all_active_ids())

        for account in accounts:
            snapshot_data = self._create_account_snapshot(account, snapshot_date)

            if snapshot_data:
                stats["snapshots_created"] += 1
                stats["total_value_usd"] += snapshot_data["value_usd"]
                stats["accounts"].append(
                    {
                        "account_id": account.id,
                        "account_name": account.name,
                        "value_usd": float(snapshot_data["value_usd"]),
                    }
                )

        logger.info(f"Created {stats['snapshots_created']} snapshots for {snapshot_date}")
        return stats

    def _create_account_snapshot(self, account: Account, snapshot_date: date) -> dict | None:
        """Create a snapshot for a single account using transaction reconstruction."""
        existing = self._snapshot_repo.find_by_account_and_date(account.id, snapshot_date)

        if existing:
            logger.info(f"Snapshot already exists for account {account.name} on {snapshot_date}")
            return None

        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            self._db, account.id, snapshot_date, apply_ticker_changes=True
        )

        if not reconstructed:
            logger.debug(f"No holdings for account {account.name} on {snapshot_date}")
            return None

        total_usd, total_ils = self._valuation.value_holdings_batch(
            reconstructed, valuation_date=snapshot_date
        )

        self._snapshot_repo.create(account.id, snapshot_date, total_usd, total_ils)
        self._db.commit()

        logger.info(
            f"Created snapshot for account {account.name}: "
            f"${total_usd:.2f} USD / ₪{total_ils:.2f} ILS"
        )

        return {
            "account_id": account.id,
            "date": snapshot_date,
            "value_usd": total_usd,
            "value_ils": total_ils,
        }

    @staticmethod
    def get_account_history(
        db: Session,
        account_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
    ) -> list[dict]:
        """Get historical snapshots for an account."""
        repo = SnapshotRepository(db)
        snapshots = repo.find_by_account(
            account_id, start_date=start_date, end_date=end_date, limit=limit
        )

        return [
            {
                "date": snapshot.date.isoformat(),
                "value_usd": float(snapshot.total_value_usd) if snapshot.total_value_usd else 0,
                "value_ils": float(snapshot.total_value_ils) if snapshot.total_value_ils else 0,
            }
            for snapshot in snapshots
        ]

    @staticmethod
    def get_portfolio_history(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
        allowed_account_ids: list[int] | None = None,
    ) -> list[dict]:
        """Get aggregated portfolio history across all accounts."""
        repo = SnapshotRepository(db)
        results = repo.find_aggregated_portfolio_history(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            account_ids=allowed_account_ids,
        )

        return [
            {
                "date": row.date.isoformat(),
                "value_usd": float(row.total_usd),
                "value_ils": float(row.total_ils),
            }
            for row in results
        ]

    def backfill_historical_snapshots(
        self, account_id: int, start_date: date, end_date: date
    ) -> dict:
        """Backfill historical snapshots using transaction reconstruction.

        Generates portfolio snapshots for every day between start_date and end_date
        by reconstructing holdings from transaction history.
        """
        account = self._account_repo.find_by_id(account_id)

        if not account:
            raise ValueError(f"Account {account_id} not found")

        logger.info(
            f"Starting backfill for account {account.name} ({account_id}) "
            f"from {start_date} to {end_date}"
        )

        stats = {
            "account_id": account_id,
            "account_name": account.name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": (end_date - start_date).days + 1,
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        current_date = start_date

        while current_date <= end_date:
            try:
                existing = self._snapshot_repo.find_by_account_and_date(account_id, current_date)

                if existing:
                    logger.debug(f"Snapshot already exists for {current_date}, skipping")
                    stats["skipped"] += 1
                    current_date += timedelta(days=1)
                    continue

                reconstructed = PortfolioReconstructionService.reconstruct_holdings(
                    self._db, account_id, current_date, apply_ticker_changes=True
                )

                if not reconstructed:
                    logger.debug(f"No holdings for {current_date}, skipping")
                    stats["skipped"] += 1
                    current_date += timedelta(days=1)
                    continue

                total_usd, total_ils = self._valuation.value_holdings_batch(
                    reconstructed, valuation_date=current_date
                )

                self._snapshot_repo.create(account_id, current_date, total_usd, total_ils)
                self._db.commit()

                stats["created"] += 1
                logger.info(
                    f"Created snapshot for {current_date}: "
                    f"${total_usd:.2f} USD (progress: {stats['created']}/{stats['total_days']})"
                )

            except Exception as e:
                logger.error(f"Error creating snapshot for {current_date}: {e}")
                stats["errors"].append({"date": current_date.isoformat(), "error": str(e)})
                self._db.rollback()

            current_date += timedelta(days=1)

        logger.info(
            f"Backfill completed: {stats['created']} created, "
            f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
        )

        return stats

    def generate_account_snapshots(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
        invalidate_existing: bool = False,
    ) -> dict:
        """Generate historical snapshots using streaming reconstruction.

        This is the unified entry point for snapshot generation, used by both
        background import tasks and the daily DAG.
        """
        stats = {
            "account_id": account_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "created": 0,
            "skipped": 0,
            "errors": [],
        }

        if invalidate_existing:
            deleted = self._snapshot_repo.delete_by_account_and_date_range(
                account_id, start_date, end_date
            )
            self._db.commit()
            logger.info(f"Deleted {deleted} existing snapshots for account {account_id}")

        try:
            HistoricalDataFetcher.ensure_historical_data(self._db, account_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            stats["errors"].append(f"Historical data fetch failed: {e}")

        for snapshot_date, holdings in PortfolioReconstructionService.reconstruct_holdings_timeline(
            self._db, account_id, start_date, end_date
        ):
            try:
                if not holdings:
                    stats["skipped"] += 1
                    continue

                existing = self._snapshot_repo.find_by_account_and_date(account_id, snapshot_date)

                if existing:
                    stats["skipped"] += 1
                    continue

                total_usd, total_ils = self._valuation.value_holdings_batch(
                    holdings, valuation_date=snapshot_date
                )

                self._snapshot_repo.create(account_id, snapshot_date, total_usd, total_ils)
                stats["created"] += 1

                if stats["created"] % 100 == 0:
                    self._db.commit()
                    logger.info(f"Generated {stats['created']} snapshots...")

            except Exception as e:
                logger.error(f"Error creating snapshot for {snapshot_date}: {e}")
                stats["errors"].append(f"{snapshot_date}: {e}")

        self._db.commit()
        logger.info(
            f"Snapshot generation complete: {stats['created']} created, "
            f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
        )

        return stats
