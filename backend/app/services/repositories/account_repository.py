"""Account data access layer."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from app.models import Account, Portfolio

if TYPE_CHECKING:
    from collections.abc import Sequence


class AccountRepository:
    """Centralized account data access.

    Naming conventions:
    - find_* : Query that may return None or empty list
    - get_* : Query that raises exception if missing
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, account_id: int) -> Account | None:
        """Find account by primary key."""
        return self._db.query(Account).filter(Account.id == account_id).first()

    def find_by_ids(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find multiple accounts by IDs."""
        return self._db.query(Account).filter(Account.id.in_(account_ids)).all()

    def find_active_by_ids(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find active accounts by IDs."""
        return (
            self._db.query(Account)
            .filter(Account.id.in_(account_ids), Account.is_active.is_(True))
            .all()
        )

    def find_by_user(self, user_id: str) -> "Sequence[Account]":
        """Find all accounts belonging to a user (via portfolios)."""
        return (
            self._db.query(Account)
            .join(Account.portfolios)
            .filter(Portfolio.user_id == user_id)
            .distinct()
            .all()
        )

    def find_by_portfolio(self, portfolio_id: str) -> "Sequence[Account]":
        """Find accounts in a specific portfolio."""
        return (
            self._db.query(Account)
            .join(Account.portfolios)
            .filter(Portfolio.id == portfolio_id)
            .all()
        )

    def find_with_holdings(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find accounts with holdings eagerly loaded."""
        return (
            self._db.query(Account)
            .options(joinedload(Account.holdings))
            .filter(Account.id.in_(account_ids))
            .all()
        )

    def find_active_with_holdings(self, account_ids: list[int]) -> "Sequence[Account]":
        """Find active accounts with active holdings eagerly loaded."""
        from app.models import Holding

        return (
            self._db.query(Account)
            .options(joinedload(Account.holdings.and_(Holding.is_active.is_(True))))
            .filter(Account.id.in_(account_ids), Account.is_active.is_(True))
            .all()
        )

    def find_all_active_ids(self) -> list[int]:
        """Find all active account IDs (for service accounts)."""
        return [
            row[0] for row in self._db.query(Account.id).filter(Account.is_active.is_(True)).all()
        ]
