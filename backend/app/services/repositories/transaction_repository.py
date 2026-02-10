"""Transaction data access layer for view queries."""

from collections.abc import Sequence

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Account, Asset, Holding, Transaction


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
    ) -> list[tuple[Transaction, Holding, Asset, Account]]:
        query = (
            self._db.query(Transaction, Holding, Asset, Account)
            .join(Holding, Transaction.holding_id == Holding.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(
                Transaction.type.in_(["Buy", "Sell"]),
                Account.id.in_(account_ids),
            )
        )
        if account_id:
            query = query.filter(Account.id == account_id)
        if symbol:
            query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))

        return (
            query.order_by(desc(Transaction.date), desc(Transaction.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def find_dividends(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Transaction, Holding, Asset, Account]]:
        query = (
            self._db.query(Transaction, Holding, Asset, Account)
            .join(Holding, Transaction.holding_id == Holding.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(
                Transaction.type.in_(["Dividend", "Tax"]),
                Account.id.in_(account_ids),
            )
        )
        if account_id:
            query = query.filter(Account.id == account_id)
        if symbol:
            query = query.filter(Asset.symbol.ilike(f"%{symbol}%"))

        return (
            query.order_by(desc(Transaction.date), desc(Transaction.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def find_forex(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Transaction, Holding, Asset, Account]]:
        query = (
            self._db.query(Transaction, Holding, Asset, Account)
            .join(Holding, Transaction.holding_id == Holding.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(
                Transaction.type == "Forex Conversion",
                Account.id.in_(account_ids),
            )
        )
        if account_id:
            query = query.filter(Account.id == account_id)

        return (
            query.order_by(desc(Transaction.date), desc(Transaction.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def find_cash_activity(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Transaction, Holding, Asset, Account]]:
        cash_types = [
            "Deposit",
            "Withdrawal",
            "Fee",
            "Transfer",
            "Custody Fee",
            "Interest",
        ]
        query = (
            self._db.query(Transaction, Holding, Asset, Account)
            .join(Holding, Transaction.holding_id == Holding.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(
                Transaction.type.in_(cash_types),
                Account.id.in_(account_ids),
            )
        )
        if account_id:
            query = query.filter(Account.id == account_id)

        return (
            query.order_by(desc(Transaction.date), desc(Transaction.id))
            .offset(offset)
            .limit(limit)
            .all()
        )
