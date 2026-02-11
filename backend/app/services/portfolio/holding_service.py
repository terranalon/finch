"""Holding business logic - list formatting and reconstruction."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, Asset, Holding
from app.services.portfolio.holding_types import (
    HoldingAccountInfo,
    HoldingAssetInfo,
    HoldingDetail,
    ReconstructionStats,
)


class HoldingService:
    """Holding list queries and reconstruction logic."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_holdings(
        self,
        account_ids: Sequence[int],
        *,
        account_id: int | None = None,
        asset_id: int | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[HoldingDetail]:
        if not account_ids:
            return []

        query = (
            self._db.query(Holding, Account, Asset)
            .join(Account, Holding.account_id == Account.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(Holding.account_id.in_(account_ids))
        )

        if account_id is not None:
            query = query.filter(Holding.account_id == account_id)
        if asset_id is not None:
            query = query.filter(Holding.asset_id == asset_id)
        if is_active is not None:
            query = query.filter(Holding.is_active == is_active)

        results = query.offset(skip).limit(limit).all()

        return [
            HoldingDetail(
                id=holding.id,
                account_id=holding.account_id,
                asset_id=holding.asset_id,
                quantity=float(holding.quantity),
                cost_basis=float(holding.cost_basis),
                strategy_horizon=holding.strategy_horizon,
                tags=holding.tags,
                is_active=holding.is_active,
                closed_at=(
                    holding.closed_at.isoformat() if holding.closed_at else None
                ),
                created_at=holding.created_at.isoformat(),
                updated_at=holding.updated_at.isoformat(),
                account=HoldingAccountInfo(
                    id=account.id,
                    name=account.name,
                    type=account.account_type,
                    institution=account.institution,
                    currency=account.currency,
                ),
                asset=HoldingAssetInfo(
                    id=asset.id,
                    symbol=asset.symbol,
                    name=asset.name,
                    asset_class=asset.asset_class,
                    category=asset.category,
                ),
            )
            for holding, account, asset in results
        ]

    def reconstruct_holdings(self, account_id: int) -> ReconstructionStats:
        from app.services.portfolio.portfolio_reconstruction_service import (
            PortfolioReconstructionService,
        )

        today = date.today()
        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            self._db, account_id, today, apply_ticker_changes=False
        )

        reconstructed_map = {h["asset_id"]: h for h in reconstructed}
        holdings = (
            self._db.query(Holding)
            .filter(Holding.account_id == account_id)
            .all()
        )

        updated = 0
        activated = 0
        deactivated = 0

        for holding in holdings:
            recon = reconstructed_map.pop(holding.asset_id, None)

            if recon:
                old_qty = holding.quantity
                holding.quantity = recon["quantity"]
                holding.cost_basis = recon["cost_basis"]
                holding.is_active = recon["quantity"] != Decimal("0")

                if old_qty == Decimal("0") and holding.quantity != Decimal("0"):
                    activated += 1
                elif old_qty != Decimal("0") and holding.quantity == Decimal("0"):
                    deactivated += 1

                updated += 1
            else:
                if holding.quantity == Decimal("0"):
                    holding.is_active = False

        return ReconstructionStats(
            account_id=account_id,
            holdings_updated=updated,
            holdings_activated=activated,
            holdings_deactivated=deactivated,
            reconstructed_count=len(reconstructed),
        )
