"""Pydantic schemas for Transaction model."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    """Base Transaction schema with common fields."""

    holding_id: int
    date: datetime.date
    type: str = Field(..., description="Transaction type: Buy, Sell, Dividend, etc.")
    quantity: Decimal | None = Field(None, description="Quantity for Buy/Sell transactions")
    price_per_unit: Decimal | None = Field(None, ge=0, description="Price per unit")
    amount: Decimal | None = Field(None, description="Cash amount for dividends/taxes")
    fees: Decimal = Field(default=Decimal("0.00"), ge=0, description="Transaction fees")
    currency_rate_to_usd_at_date: Decimal | None = Field(
        None, ge=0, description="Exchange rate to USD at transaction date"
    )
    notes: str | None = None


class TransactionCreateRequest(BaseModel):
    """Schema for creating a new Transaction (user-facing)."""

    account_id: int
    asset_id: int
    date: datetime.date
    type: str = Field(..., description="Transaction type: Buy, Sell, Dividend, etc.")
    quantity: Decimal | None = Field(None, description="Quantity for Buy/Sell transactions")
    price_per_unit: Decimal | None = Field(None, ge=0, description="Price per unit")
    amount: Decimal | None = Field(None, description="Cash amount for dividends/taxes")
    fees: Decimal = Field(default=Decimal("0.00"), ge=0, description="Transaction fees")
    currency_rate_to_usd_at_date: Decimal | None = Field(
        None, ge=0, description="Exchange rate to USD at transaction date"
    )
    notes: str | None = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new Transaction (internal)."""

    pass


class TransactionUpdate(BaseModel):
    """Schema for updating an existing Transaction."""

    holding_id: int | None = None
    date: datetime.date | None = None
    type: str | None = None
    quantity: Decimal | None = None
    price_per_unit: Decimal | None = Field(None, ge=0)
    amount: Decimal | None = Field(None)
    fees: Decimal | None = Field(None, ge=0)
    currency_rate_to_usd_at_date: Decimal | None = Field(None, ge=0)
    notes: str | None = None


class Transaction(TransactionBase):
    """Schema for Transaction responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
