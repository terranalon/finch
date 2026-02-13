"""Pydantic schemas for API validation."""

from app.schemas.account import Account, AccountCreate, AccountUpdate
from app.schemas.asset import Asset, AssetCreate, AssetMarketResponse, AssetUpdate
from app.schemas.auth import MfaRequiredResponse
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    StatusResponse,
)
from app.schemas.dashboard import (
    BenchmarkResponse,
    DashboardSummaryResponse,
)
from app.schemas.exchange_rate import ExchangeRate, ExchangeRateCreate, ExchangeRateUpdate
from app.schemas.historical_snapshot import (
    HistoricalSnapshot,
    HistoricalSnapshotCreate,
    HistoricalSnapshotUpdate,
)
from app.schemas.holding import (
    Holding,
    HoldingCreate,
    HoldingDetailResponse,
    HoldingUpdate,
    ReconstructionStatsResponse,
)
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
from app.schemas.price import (
    HistoricalPriceResponse,
    PriceUpdateResponse,
    SingleAssetPriceResponse,
)
from app.schemas.snapshot import (
    SnapshotCreateResponse,
    SnapshotPointResponse,
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
    "AssetMarketResponse",
    "AssetUpdate",
    # Auth response schemas
    "MfaRequiredResponse",
    # Common schemas
    "ErrorDetail",
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
    "StatusResponse",
    # Dashboard schemas
    "BenchmarkResponse",
    "DashboardSummaryResponse",
    # Holding schemas
    "Holding",
    "HoldingCreate",
    "HoldingDetailResponse",
    "HoldingUpdate",
    "ReconstructionStatsResponse",
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
    # Price schemas
    "HistoricalPriceResponse",
    "PriceUpdateResponse",
    "SingleAssetPriceResponse",
    # Snapshot schemas
    "SnapshotCreateResponse",
    "SnapshotPointResponse",
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
