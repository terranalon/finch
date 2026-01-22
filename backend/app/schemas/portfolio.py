"""Pydantic schemas for Portfolio model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortfolioBase(BaseModel):
    """Base Portfolio schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    default_currency: str = Field("USD", min_length=3, max_length=3)


class PortfolioCreate(PortfolioBase):
    """Schema for creating a new Portfolio."""

    pass


class PortfolioUpdate(BaseModel):
    """Schema for updating an existing Portfolio."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    default_currency: str | None = Field(None, min_length=3, max_length=3)


class Portfolio(PortfolioBase):
    """Schema for Portfolio responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class PortfolioWithAccountCount(Portfolio):
    """Portfolio with account count for list endpoint."""

    account_count: int = 0
    total_value: float | None = None  # Total portfolio value in default_currency
