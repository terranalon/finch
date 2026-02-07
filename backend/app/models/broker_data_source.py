"""BrokerDataSource model - tracks imported data sources from brokers."""

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class BrokerDataSource(Base):
    """Tracks data sources imported from various brokers.

    Each record represents a single import event:
    - file_upload: User-uploaded historical data file
    - api_fetch: Data automatically fetched from broker API
    - synthetic: Auto-generated from current broker positions (snapshot onboarding)
    - legacy: Data from before this tracking system existed

    Used for:
    - Preventing overlapping imports (strict date range enforcement)
    - Providing audit trail (which source provided which data)
    - Detecting coverage gaps
    - Deduplicating file uploads (via file_hash)
    - Tracking synthetic snapshots for validation when real history is uploaded
    """

    __tablename__ = "broker_data_sources"
    __table_args__ = (
        # For overlap detection queries
        Index(
            "idx_broker_sources_account_broker_dates",
            "account_id",
            "broker_type",
            "start_date",
            "end_date",
        ),
        # For duplicate file detection
        Index("idx_broker_sources_file_hash", "file_hash", "account_id"),
        # For listing sources by account
        Index("idx_broker_sources_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))

    # Broker identification
    broker_type: Mapped[str] = mapped_column(String(50))  # 'ibkr', 'binance', 'ibi', etc.

    # Source type and identifier
    source_type: Mapped[str] = mapped_column(String(20))  # 'file_upload', 'api_fetch', 'synthetic', 'legacy'
    source_identifier: Mapped[str] = mapped_column(
        String(255)
    )  # Filename or "Daily Auto-Fetch YYYY-MM-DD"

    # Date range coverage
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # 'pending', 'completed', 'failed'

    # File-specific fields (nullable for API fetches)
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_hash: Mapped[str | None] = mapped_column(String(64))  # SHA256 hash
    file_format: Mapped[str | None] = mapped_column(String(10))  # 'xml', 'csv', 'json', 'xlsx'

    # Import statistics (JSONB for flexibility across broker types)
    import_stats: Mapped[dict | None] = mapped_column(
        JSONB
    )  # {"transactions": 45, "positions": 12, ...}

    # Error tracking
    errors: Mapped[list | None] = mapped_column(JSONB)  # List of error messages if failed

    # Discontinuous date ranges after ownership transfer
    date_ranges: Mapped[list | None] = mapped_column(JSONB)  # [{start_date, end_date}, ...]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="broker_data_sources")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="broker_source")

    def __repr__(self) -> str:
        return (
            f"<BrokerDataSource(id={self.id}, broker='{self.broker_type}', "
            f"type='{self.source_type}', dates={self.start_date} to {self.end_date})>"
        )

    @property
    def coverage_days(self) -> int:
        """Calculate the number of days covered by this source."""
        return (self.end_date - self.start_date).days + 1
