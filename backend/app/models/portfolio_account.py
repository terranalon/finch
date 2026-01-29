"""Association table for many-to-many Portfolio-Account relationship."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import func

from app.database import Base

portfolio_accounts = Table(
    "portfolio_accounts",
    Base.metadata,
    Column(
        "portfolio_id",
        String(36),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "account_id",
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("added_at", DateTime, server_default=func.now()),
)
