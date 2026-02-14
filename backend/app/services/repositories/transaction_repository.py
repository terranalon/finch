"""Transaction data access layer for view queries."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Query, Session

from app.models import Account, Asset, Holding, Transaction

_TransactionRow = tuple[Transaction, Holding, Asset, Account]

_TRADE_TYPES = ["Buy", "Sell"]
_DIVIDEND_TYPES = ["Dividend", "Tax"]
_FOREX_TYPES = ["Forex Conversion"]
_CASH_TYPES = ["Deposit", "Withdrawal", "Fee", "Transfer", "Custody Fee", "Interest"]


class TransactionRepository:
    """Read-only queries for transaction view endpoints."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_trades(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[_TransactionRow]:
        query = self._filtered_query(
            account_ids, _TRADE_TYPES, account_id=account_id, symbol=symbol
        )
        return self._paginate(query, limit, offset)

    def find_dividends(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[_TransactionRow]:
        query = self._filtered_query(
            account_ids, _DIVIDEND_TYPES, account_id=account_id, symbol=symbol
        )
        return self._paginate(query, limit, offset)

    def find_forex(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[_TransactionRow]:
        query = self._base_query(account_ids, _FOREX_TYPES, account_id=account_id)
        return self._paginate(query, limit, offset)

    def find_cash_activity(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[_TransactionRow]:
        query = self._base_query(account_ids, _CASH_TYPES, account_id=account_id)
        return self._paginate(query, limit, offset)

    def count_trades(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
    ) -> int:
        return self._filtered_query(
            account_ids, _TRADE_TYPES, account_id=account_id, symbol=symbol
        ).count()

    def count_dividends(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
    ) -> int:
        return self._filtered_query(
            account_ids, _DIVIDEND_TYPES, account_id=account_id, symbol=symbol
        ).count()

    def count_forex(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
    ) -> int:
        return self._base_query(account_ids, _FOREX_TYPES, account_id=account_id).count()

    def count_cash_activity(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
    ) -> int:
        return self._base_query(account_ids, _CASH_TYPES, account_id=account_id).count()

    def _base_query(
        self,
        account_ids: Sequence[int],
        transaction_types: list[str],
        *,
        account_id: int | None = None,
    ) -> Query:
        """Build the shared join + filter query for transaction views."""
        query = (
            self._db.query(Transaction, Holding, Asset, Account)
            .join(Transaction.holding)
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(
                Transaction.type.in_(transaction_types),
                Account.id.in_(account_ids),
            )
        )
        if account_id:
            query = query.filter(Account.id == account_id)
        return query

    def _filtered_query(
        self,
        account_ids: Sequence[int],
        transaction_types: list[str],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
    ) -> Query:
        """Build base query with optional symbol filter."""
        query = self._base_query(account_ids, transaction_types, account_id=account_id)
        if symbol:
            query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))
        return query

    @staticmethod
    def _paginate(query: Query, limit: int, offset: int) -> list[_TransactionRow]:
        """Apply consistent ordering and pagination."""
        return (
            query.order_by(desc(Transaction.date), desc(Transaction.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def find_with_holdings_and_assets_by_account(
        self, account_id: int, *, as_of_date: date | None = None
    ) -> list[tuple[Transaction, Holding, Asset]]:
        """Find transactions with Holding and Asset for an account.

        If as_of_date is provided, only includes transactions on or before that date.
        Ordered chronologically by (date, id).
        """
        query = (
            self._db.query(Transaction, Holding, Asset)
            .join(Transaction.holding)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(Holding.account_id == account_id)
        )
        if as_of_date is not None:
            query = query.filter(Transaction.date <= as_of_date)
        return query.order_by(Transaction.date, Transaction.id).all()  # ty: ignore[invalid-return-type] -- Row[tuple] is structurally equivalent to tuple

    def count_by_account(self, account_id: int) -> int:
        """Count transactions for an account (existence check)."""
        return (
            self._db.query(Transaction)
            .join(Transaction.holding)
            .filter(Holding.account_id == account_id)
            .limit(1)
            .count()
        )

    def find_first_by_holding(self, holding_id: int) -> Transaction | None:
        """Find first transaction for a holding (existence check)."""
        return self._db.query(Transaction).filter(Transaction.holding_id == holding_id).first()
