"""Corporate Action model for tracking ticker changes, splits, mergers, etc."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CorporateAction(Base):
    """
    Track corporate actions affecting asset positions.

    Supports:
    - Symbol changes (CEP -> XXI)
    - Stock splits (1:2, 2:1, etc.)
    - Reverse splits
    - Mergers & acquisitions
    - Spinoffs
    """

    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Action type
    action_type: Mapped[str] = mapped_column(
        String(50)
    )  # SYMBOL_CHANGE, SPLIT, REVERSE_SPLIT, MERGER, SPINOFF

    # Asset references
    old_asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    new_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))

    # Action details
    effective_date: Mapped[datetime] = mapped_column(Date)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(15, 8))  # For splits: 2.0 = 2:1 split
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    # Relationships
    old_asset: Mapped["Asset"] = relationship("Asset", foreign_keys=[old_asset_id])
    new_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[new_asset_id])

    def __repr__(self):
        return f"<CorporateAction(type={self.action_type}, {self.old_asset.symbol if self.old_asset else '?'} -> {self.new_asset.symbol if self.new_asset else '?'}, {self.effective_date})>"
