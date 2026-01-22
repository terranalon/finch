"""Daily Cash Balance model - IBKR's authoritative cash balances from StmtFunds."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DailyCashBalance(Base):
    """
    Daily cash balance from IBKR Statement of Funds.

    This table stores IBKR's authoritative daily running cash balances by currency.
    Use this for historical cash reconstruction instead of summing transactions,
    as transactions may be incomplete or missing.
    """

    __tablename__ = "daily_cash_balances"
    __table_args__ = (
        UniqueConstraint("account_id", "date", "currency", name="uq_daily_cash_balance"),
        Index("idx_cash_balance_account_date", "account_id", "date"),
        Index("idx_cash_balance_account_currency", "account_id", "currency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    broker_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_data_sources.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<DailyCashBalance({self.currency} {self.balance} on {self.date})>"
