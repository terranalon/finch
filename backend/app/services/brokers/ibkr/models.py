"""Typed dataclasses for IBKR Flex Query parser output.

Inspired by ibflex (https://github.com/csingley/ibflex), these frozen
dataclasses replace the raw dicts previously returned by IBKRParser.
Field-name typos now raise AttributeError immediately instead of
producing silent KeyError defaults downstream.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class IBKRSymbolInfo:
    """Symbol normalization result from IBKRParser.normalize_symbol()."""

    yf_symbol: str
    original_symbol: str
    needs_validation: bool


@dataclass(frozen=True)
class IBKRPosition:
    """A single open position from extract_positions()."""

    symbol: str
    original_symbol: str
    description: str
    asset_category: str
    asset_class: str
    listing_exchange: str
    quantity: Decimal
    cost_basis: Decimal
    currency: str
    account_id: str
    needs_validation: bool
    cusip: str | None = None
    isin: str | None = None
    conid: str | None = None
    figi: str | None = None


@dataclass(frozen=True)
class IBKRTransaction:
    """A single trade from extract_transactions()."""

    symbol: str
    original_symbol: str
    description: str
    asset_category: str
    asset_class: str
    listing_exchange: str
    trade_date: date
    transaction_type: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    net_cash: Decimal
    currency: str
    account_id: str
    needs_validation: bool
    cusip: str | None = None
    isin: str | None = None
    conid: str | None = None
    figi: str | None = None
    external_transaction_id: str | None = None


@dataclass(frozen=True)
class IBKRDividend:
    """A single dividend from extract_dividends()."""

    symbol: str
    original_symbol: str
    description: str
    asset_category: str
    asset_class: str
    date: date
    amount: Decimal
    currency: str
    account_id: str
    needs_validation: bool


@dataclass(frozen=True)
class IBKRTransfer:
    """A deposit or withdrawal from extract_transfers()."""

    date: date
    type: str
    amount: Decimal
    currency: str
    description: str
    account_id: str


@dataclass(frozen=True)
class IBKROtherCashTransaction:
    """Interest, tax, or fee from extract_other_cash_transactions()."""

    date: date
    type: str
    ibkr_type: str
    amount: Decimal
    currency: str
    symbol: str
    description: str
    account_id: str


@dataclass(frozen=True)
class IBKRForexTransaction:
    """A currency conversion from extract_forex_transactions()."""

    date: date
    from_currency: str
    to_currency: str
    from_amount: Decimal
    to_amount: Decimal
    realized_pl: Decimal
    description: str
    account_id: str


@dataclass(frozen=True)
class IBKRCashBalance:
    """Cash balance by currency from extract_cash_balances().

    The parser enriches symbol, description, and asset_class so consumers
    don't need to derive them from the currency code.
    """

    symbol: str
    currency: str
    balance: Decimal
    description: str
    asset_class: str
    account_id: str


@dataclass(frozen=True)
class IBKRStatementOfFundsBalance:
    """Daily cash balance record from extract_statement_of_funds_balances()."""

    date: date
    currency: str
    balance: Decimal
    activity: str


@dataclass(frozen=True)
class IBKRAccountInfo:
    """Account metadata from the AccountInformation section."""

    account_id: str
    date_opened: date
