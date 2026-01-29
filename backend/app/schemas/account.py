"""Pydantic schemas for Account model."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountBase(BaseModel):
    """Base Account schema with common fields."""

    portfolio_id: str | None = None
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

    pass


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
    snapshot_status: str | None = None
    created_at: datetime
    updated_at: datetime
