"""Pydantic schemas for HoldingLot model."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HoldingLotBase(BaseModel):
    """Base HoldingLot schema with common fields."""

    holding_id: int
    quantity: Decimal = Field(..., ge=0, description="Original quantity purchased")
    cost_per_unit: Decimal = Field(..., ge=0, description="Cost per unit in account currency")
    purchase_date: date
    purchase_price_original: Decimal | None = Field(
        None, ge=0, description="Original purchase price in asset's native currency"
    )
    fees: Decimal = Field(default=Decimal("0.00"), ge=0, description="Transaction fees")
    is_closed: bool = False
    remaining_quantity: Decimal | None = Field(
        None, ge=0, description="Remaining quantity after partial sales"
    )


class HoldingLotCreate(HoldingLotBase):
    """Schema for creating a new HoldingLot."""

    pass


class HoldingLotUpdate(BaseModel):
    """Schema for updating an existing HoldingLot."""

    remaining_quantity: Decimal | None = Field(None, ge=0)
    is_closed: bool | None = None


class HoldingLot(HoldingLotBase):
    """Schema for HoldingLot responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
