"""Pydantic schemas for API validation."""

from app.schemas.account import Account, AccountCreate, AccountUpdate
from app.schemas.asset import Asset, AssetCreate, AssetUpdate
from app.schemas.exchange_rate import ExchangeRate, ExchangeRateCreate, ExchangeRateUpdate
from app.schemas.historical_snapshot import (
    HistoricalSnapshot,
    HistoricalSnapshotCreate,
    HistoricalSnapshotUpdate,
)
from app.schemas.holding import Holding, HoldingCreate, HoldingUpdate
from app.schemas.holding_lot import HoldingLot, HoldingLotCreate, HoldingLotUpdate
from app.schemas.portfolio import (
    Portfolio,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioWithAccountCount,
)
from app.schemas.transaction import Transaction, TransactionCreate, TransactionUpdate
from app.schemas.transaction_views import (
    CashActivityResponse,
    DividendResponse,
    ForexResponse,
    TradeResponse,
)

__all__ = [
    # Account schemas
    "Account",
    "AccountCreate",
    "AccountUpdate",
    # Asset schemas
    "Asset",
    "AssetCreate",
    "AssetUpdate",
    # Holding schemas
    "Holding",
    "HoldingCreate",
    "HoldingUpdate",
    # HoldingLot schemas
    "HoldingLot",
    "HoldingLotCreate",
    "HoldingLotUpdate",
    # Portfolio schemas
    "Portfolio",
    "PortfolioCreate",
    "PortfolioUpdate",
    "PortfolioWithAccountCount",
    # Transaction schemas
    "Transaction",
    "TransactionCreate",
    "TransactionUpdate",
    # Transaction view schemas
    "TradeResponse",
    "DividendResponse",
    "ForexResponse",
    "CashActivityResponse",
    # ExchangeRate schemas
    "ExchangeRate",
    "ExchangeRateCreate",
    "ExchangeRateUpdate",
    # HistoricalSnapshot schemas
    "HistoricalSnapshot",
    "HistoricalSnapshotCreate",
    "HistoricalSnapshotUpdate",
]
