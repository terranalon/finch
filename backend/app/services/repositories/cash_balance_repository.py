"""Daily cash balance data access layer."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DailyCashBalance


class CashBalanceRepository:
    """Centralized daily cash balance data access.

    Naming conventions:
    - find_* : Query that may return None or empty collection
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_latest_per_currency(
        self, account_id: int, as_of_date: date
    ) -> Sequence[DailyCashBalance]:
        """Find the most recent balance for each currency on or before as_of_date.

        Uses a subquery to find max(date) per currency, then joins back
        to get the full DailyCashBalance rows.
        """
        subquery = (
            self._db.query(
                DailyCashBalance.currency,
                func.max(DailyCashBalance.date).label("max_date"),
            )
            .filter(
                DailyCashBalance.account_id == account_id,
                DailyCashBalance.date <= as_of_date,
            )
            .group_by(DailyCashBalance.currency)
            .subquery()
        )

        return (
            self._db.query(DailyCashBalance)
            .join(
                subquery,
                (DailyCashBalance.currency == subquery.c.currency)
                & (DailyCashBalance.date == subquery.c.max_date),
            )
            .filter(DailyCashBalance.account_id == account_id)
            .all()
        )

    def find_by_account_and_date_range(
        self, account_id: int, start_date: date, end_date: date
    ) -> Sequence[DailyCashBalance]:
        """Find all cash balances for an account within a date range (inclusive)."""
        return (
            self._db.query(DailyCashBalance)
            .filter(
                DailyCashBalance.account_id == account_id,
                DailyCashBalance.date >= start_date,
                DailyCashBalance.date <= end_date,
            )
            .all()
        )

    def find_latest_per_currency_before_date(
        self, account_id: int, before_date: date
    ) -> Sequence[DailyCashBalance]:
        """Find the most recent balance for each currency strictly BEFORE a date.

        Same subquery pattern as find_latest_per_currency but with strict < instead of <=.
        """
        subquery = (
            self._db.query(
                DailyCashBalance.currency,
                func.max(DailyCashBalance.date).label("max_date"),
            )
            .filter(
                DailyCashBalance.account_id == account_id,
                DailyCashBalance.date < before_date,
            )
            .group_by(DailyCashBalance.currency)
            .subquery()
        )

        return (
            self._db.query(DailyCashBalance)
            .join(
                subquery,
                (DailyCashBalance.currency == subquery.c.currency)
                & (DailyCashBalance.date == subquery.c.max_date),
            )
            .filter(DailyCashBalance.account_id == account_id)
            .all()
        )
