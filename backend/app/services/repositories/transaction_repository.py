"""Transaction data access layer for view queries."""

from collections.abc import Sequence

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
            .join(Holding, Transaction.holding_id == Holding.id)
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
