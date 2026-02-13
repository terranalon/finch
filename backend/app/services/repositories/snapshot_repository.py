"""Historical snapshot data access layer."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Account, HistoricalSnapshot


class SnapshotRepository:
    """Centralized historical snapshot data access.

    Naming conventions:
    - find_* : Query that may return None or empty collection
    - create : Insert new record (uses flush, not commit)
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_account_and_date(
        self, account_id: int, snapshot_date: date
    ) -> HistoricalSnapshot | None:
        """Find a snapshot for a specific account and date."""
        return (
            self._db.query(HistoricalSnapshot)
            .filter(
                HistoricalSnapshot.account_id == account_id,
                HistoricalSnapshot.date == snapshot_date,
            )
            .first()
        )

    def sum_values_by_date(
        self, account_ids: list[int], target_date: date
    ) -> Decimal | None:
        """Sum total_value_usd for given accounts on a specific date."""
        row = (
            self._db.query(
                func.sum(HistoricalSnapshot.total_value_usd).label("total_usd")
            )
            .filter(
                HistoricalSnapshot.date == target_date,
                HistoricalSnapshot.account_id.in_(account_ids),
            )
            .first()
        )
        return Decimal(str(row.total_usd)) if row and row.total_usd else None

    def find_aggregated_performance(
        self, account_ids: list[int], days: int = 30
    ) -> list[tuple]:
        """Aggregated portfolio value by date, most recent first, limited to N days.

        Returns list of Row(date, total_usd, total_ils).
        """
        return (
            self._db.query(
                HistoricalSnapshot.date,
                func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"),
                func.sum(HistoricalSnapshot.total_value_ils).label("total_ils"),
            )
            .filter(HistoricalSnapshot.account_id.in_(account_ids))
            .group_by(HistoricalSnapshot.date)
            .order_by(HistoricalSnapshot.date.desc())
            .limit(days)
            .all()
        )

    def find_by_account(
        self,
        account_id: int,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
    ) -> Sequence[HistoricalSnapshot]:
        """Find snapshots for an account with optional date range and limit."""
        query = self._db.query(HistoricalSnapshot).filter(
            HistoricalSnapshot.account_id == account_id
        )
        if start_date:
            query = query.filter(HistoricalSnapshot.date >= start_date)
        if end_date:
            query = query.filter(HistoricalSnapshot.date <= end_date)
        return query.order_by(HistoricalSnapshot.date.desc()).limit(limit).all()

    def find_aggregated_portfolio_history(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
        account_ids: list[int] | None = None,
    ) -> list[tuple]:
        """Aggregated portfolio history across accounts.

        Returns list of Row(date, total_usd, total_ils).
        """
        query = self._db.query(
            HistoricalSnapshot.date,
            func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"),
            func.sum(HistoricalSnapshot.total_value_ils).label("total_ils"),
        ).join(Account, HistoricalSnapshot.account_id == Account.id)

        if account_ids is not None:
            query = query.filter(HistoricalSnapshot.account_id.in_(account_ids))
        if start_date:
            query = query.filter(HistoricalSnapshot.date >= start_date)
        if end_date:
            query = query.filter(HistoricalSnapshot.date <= end_date)

        return (
            query.group_by(HistoricalSnapshot.date)
            .order_by(HistoricalSnapshot.date.desc())
            .limit(limit)
            .all()
        )

    def delete_by_account_and_date_range(
        self, account_id: int, start_date: date, end_date: date
    ) -> int:
        """Delete snapshots for an account within a date range. Returns count deleted."""
        return (
            self._db.query(HistoricalSnapshot)
            .filter(
                HistoricalSnapshot.account_id == account_id,
                HistoricalSnapshot.date >= start_date,
                HistoricalSnapshot.date <= end_date,
            )
            .delete(synchronize_session=False)
        )

    def create(
        self,
        account_id: int,
        snapshot_date: date,
        total_value_usd: Decimal,
        total_value_ils: Decimal,
    ) -> HistoricalSnapshot:
        """Create a new snapshot. Uses flush(), not commit()."""
        snapshot = HistoricalSnapshot(
            account_id=account_id,
            date=snapshot_date,
            total_value_usd=total_value_usd,
            total_value_ils=total_value_ils,
        )
        self._db.add(snapshot)
        self._db.flush()
        return snapshot
