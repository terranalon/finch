"""Portfolio model - groups accounts for a user."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.portfolio_account import portfolio_accounts

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class Portfolio(Base):
    """Portfolio model representing a grouping of accounts."""

    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    default_currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        secondary=portfolio_accounts,
        back_populates="portfolios",
    )

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}')>"
