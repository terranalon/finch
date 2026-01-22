"""Pydantic schemas for ExchangeRate model."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExchangeRateBase(BaseModel):
    """Base ExchangeRate schema with common fields."""

    from_currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")
    to_currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")
    date: date
    rate: Decimal = Field(..., gt=0, description="Exchange rate from_currency to to_currency")
    data_source: str | None = Field(
        None, max_length=50, description="Data source: ECB, BOI, Manual, etc."
    )


class ExchangeRateCreate(ExchangeRateBase):
    """Schema for creating a new ExchangeRate."""

    pass


class ExchangeRateUpdate(BaseModel):
    """Schema for updating an existing ExchangeRate."""

    rate: Decimal | None = Field(None, gt=0)
    data_source: str | None = Field(None, max_length=50)


class ExchangeRate(ExchangeRateBase):
    """Schema for ExchangeRate responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
