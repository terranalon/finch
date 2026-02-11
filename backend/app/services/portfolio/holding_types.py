"""Value objects for holding services."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class HoldingAccountInfo:
    id: int
    name: str
    type: str | None
    institution: str | None
    currency: str | None


@dataclass(frozen=True)
class HoldingAssetInfo:
    id: int
    symbol: str
    name: str | None
    asset_class: str | None
    category: str | None


@dataclass(frozen=True)
class HoldingDetail:
    id: int
    account_id: int
    asset_id: int
    quantity: float
    cost_basis: float
    strategy_horizon: str | None
    tags: str | None
    is_active: bool
    closed_at: str | None
    created_at: str
    updated_at: str
    account: HoldingAccountInfo
    asset: HoldingAssetInfo


@dataclass
class ReconstructionStats:
    account_id: int
    holdings_updated: int
    holdings_activated: int
    holdings_deactivated: int
    reconstructed_count: int
