"""Type-specific transaction response schemas for the tabbed transaction views."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TradeResponse(BaseModel):
    """Response schema for Buy/Sell trades."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    symbol: str
    asset_name: str
    asset_class: str  # Stock, ETF, Crypto, etc.
    action: str  # "Buy" or "Sell"
    quantity: Decimal
    price_per_unit: Decimal
    fees: Decimal
    total: Decimal  # qty * price + fees (computed server-side)
    currency: str
    account_name: str
    notes: str | None = None


class DividendResponse(BaseModel):
    """Response schema for dividend and income transactions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    symbol: str
    asset_name: str
    type: str  # "Dividend", "Dividend Cash", "Tax", "Interest"
    amount: Decimal
    currency: str
    account_name: str
    notes: str | None = None


class ForexResponse(BaseModel):
    """Response schema for forex conversion transactions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    exchange_rate: Decimal
    account_name: str
    notes: str | None = None


class CashActivityResponse(BaseModel):
    """Response schema for cash activity (deposits, withdrawals, etc.)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    type: str  # "Deposit", "Withdrawal", "Fee", "Transfer"
    symbol: str | None = None  # For context (e.g., which asset the fee relates to)
    amount: Decimal
    currency: str
    account_name: str
    notes: str | None = None
