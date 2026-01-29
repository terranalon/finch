"""Pydantic schemas for Account model."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AccountBase(BaseModel):
    """Base Account schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100)
    institution: str | None = Field(None, max_length=100)
    account_type: str = Field(
        ...,
        description="Account type: Brokerage, Pension, StudyFund, Bank, CryptoExchange, CryptoWallet, SelfCustodied, FamilyOffice",
    )
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")
    account_number: str | None = Field(None, max_length=100)
    external_id: str | None = Field(None, max_length=100)
    is_active: bool = True
    broker_type: str | None = Field(
        None, max_length=50, description="Broker type: ibkr, binance, ibi, etc."
    )
    meta_data: dict[str, Any] | None = None


class AccountCreate(AccountBase):
    """Schema for creating a new Account."""

    portfolio_ids: list[str] = Field(
        ..., min_length=1, description="Portfolio IDs to link account to"
    )


class AccountUpdate(BaseModel):
    """Schema for updating an existing Account."""

    name: str | None = Field(None, min_length=1, max_length=100)
    institution: str | None = Field(None, max_length=100)
    account_type: str | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    account_number: str | None = Field(None, max_length=100)
    external_id: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    broker_type: str | None = Field(None, max_length=50)
    meta_data: dict[str, Any] | None = None


class Account(AccountBase):
    """Schema for Account responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_ids: list[str] = []
    snapshot_status: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def extract_portfolio_ids(cls, data: Any) -> Any:
        """Extract portfolio_ids from SQLAlchemy relationship."""
        if not hasattr(data, "portfolios"):
            return data

        # Build dict from SQLAlchemy model attributes
        result = {
            key: getattr(data, key)
            for key in cls.model_fields
            if key != "portfolio_ids" and hasattr(data, key)
        }
        result["portfolio_ids"] = [p.id for p in data.portfolios]
        return result
