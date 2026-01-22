"""TASE Security model - cached Israeli securities data from TASE API."""

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class TASESecurity(Base):
    """Cached security data from Tel Aviv Stock Exchange (TASE) API.

    This table stores the mapping between Israeli security numbers (מספר נייר ערך)
    and their trading symbols, ISINs, and other metadata. Data is synced daily
    from the TASE Data Hub API.

    The primary use case is resolving Meitav Trade export files, which identify
    securities by their Israeli security number rather than trading symbols.
    """

    __tablename__ = "tase_securities"
    __table_args__ = (
        Index("idx_tase_securities_symbol", "symbol"),
        Index("idx_tase_securities_isin", "isin"),
        Index("idx_tase_securities_type_code", "security_type_code"),
    )

    # Israeli security number (מספר נייר ערך) - unique identifier
    security_id: Mapped[int] = mapped_column(primary_key=True)

    # Trading symbol on TASE (e.g., "TEVA", "LEUMI")
    symbol: Mapped[str | None] = mapped_column(String(50))

    # Yahoo Finance compatible symbol (symbol + ".TA" suffix)
    yahoo_symbol: Mapped[str | None] = mapped_column(String(50))

    # International Securities Identification Number
    isin: Mapped[str | None] = mapped_column(String(20))

    # Security name in Hebrew
    security_name: Mapped[str | None] = mapped_column(String(200))

    # Security name in English (if available)
    security_name_en: Mapped[str | None] = mapped_column(String(200))

    # Security type code from TASE (e.g., "0101" = Ordinary Share)
    security_type_code: Mapped[str | None] = mapped_column(String(10))

    # Company/issuer information
    company_name: Mapped[str | None] = mapped_column(String(200))
    company_sector: Mapped[str | None] = mapped_column(String(100))
    company_sub_sector: Mapped[str | None] = mapped_column(String(100))

    # Sync metadata
    last_synced_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<TASESecurity(id={self.security_id}, symbol='{self.symbol}', "
            f"name='{self.security_name}')>"
        )
