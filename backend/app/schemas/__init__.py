"""Pydantic schemas for API validation."""

from app.schemas.account import Account, AccountCreate, AccountUpdate
from app.schemas.asset import Asset, AssetCreate, AssetUpdate
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
)
from app.schemas.exchange_rate import ExchangeRate, ExchangeRateCreate, ExchangeRateUpdate
from app.schemas.historical_snapshot import (
    HistoricalSnapshot,
    HistoricalSnapshotCreate,
    HistoricalSnapshotUpdate,
)
from app.schemas.holding import Holding, HoldingCreate, HoldingUpdate
from app.schemas.holding_lot import HoldingLot, HoldingLotCreate, HoldingLotUpdate
from app.schemas.market_data import (
    ExchangeRateRefreshResponse,
    PriceRefreshError,
    PriceRefreshResponse,
    RefreshStats,
)
from app.schemas.portfolio import (
    Portfolio,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioWithAccountCount,
)
from app.schemas.position import PositionAccountDetail, PositionResponse
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
    # Common schemas
    "ErrorDetail",
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
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
    # Position schemas
    "PositionAccountDetail",
    "PositionResponse",
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
    # Market data schemas
    "ExchangeRateRefreshResponse",
    "PriceRefreshError",
    "PriceRefreshResponse",
    "RefreshStats",
]
