"""Pydantic schemas for Holding model."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HoldingBase(BaseModel):
    """Base Holding schema with common fields."""

    account_id: int
    asset_id: int
    quantity: Decimal = Field(..., ge=0, description="Total quantity held")
    cost_basis: Decimal = Field(..., ge=0, description="Total cost basis in account currency")
    strategy_horizon: str | None = Field(
        None,
        max_length=20,
        description="Investment strategy: ShortTerm, MediumTerm, LongTerm, etc.",
    )
    tags: dict[str, Any] | None = None
    is_active: bool = True


class HoldingCreate(HoldingBase):
    """Schema for creating a new Holding."""

    pass


class HoldingUpdate(BaseModel):
    """Schema for updating an existing Holding."""

    quantity: Decimal | None = Field(None, ge=0)
    cost_basis: Decimal | None = Field(None, ge=0)
    strategy_horizon: str | None = Field(None, max_length=20)
    tags: dict[str, Any] | None = None
    is_active: bool | None = None


class Holding(HoldingBase):
    """Schema for Holding responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# --- List endpoint response schemas ---


class HoldingAccountInfo(BaseModel):
    """Account info nested in a holding list item."""

    id: int
    name: str
    type: str | None = None
    institution: str | None = None
    currency: str | None = None


class HoldingAssetInfo(BaseModel):
    """Asset info nested in a holding list item."""

    id: int
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    category: str | None = None


class HoldingListItem(BaseModel):
    """Single item returned by GET /api/holdings."""

    id: int
    account_id: int
    asset_id: int
    quantity: float
    cost_basis: float
    strategy_horizon: str | None = None
    tags: list | None = None
    is_active: bool
    closed_at: str | None = None
    created_at: str
    updated_at: str
    account: HoldingAccountInfo
    asset: HoldingAssetInfo


class ReconstructionStatsResponse(BaseModel):
    """Response for POST /api/holdings/reconstruct/{account_id}."""

    account_id: int
    holdings_updated: int
    holdings_activated: int
    holdings_deactivated: int
    reconstructed_count: int
