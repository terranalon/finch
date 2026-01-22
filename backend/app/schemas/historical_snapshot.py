"""Pydantic schemas for HistoricalSnapshot model."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HistoricalSnapshotBase(BaseModel):
    """Base HistoricalSnapshot schema with common fields."""

    date: date
    account_id: int
    total_value_usd: Decimal | None = Field(None, ge=0, description="Total portfolio value in USD")
    total_value_ils: Decimal | None = Field(None, ge=0, description="Total portfolio value in ILS")


class HistoricalSnapshotCreate(HistoricalSnapshotBase):
    """Schema for creating a new HistoricalSnapshot."""

    pass


class HistoricalSnapshotUpdate(BaseModel):
    """Schema for updating an existing HistoricalSnapshot."""

    total_value_usd: Decimal | None = Field(None, ge=0)
    total_value_ils: Decimal | None = Field(None, ge=0)


class HistoricalSnapshot(HistoricalSnapshotBase):
    """Schema for HistoricalSnapshot responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
