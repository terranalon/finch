"""Dashboard summary service.

Computes all sections of the dashboard (account values, allocation,
top holdings, performance) in USD. Display-currency conversion is the
router's responsibility.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Holding
from app.services.portfolio.holding_valuation_service import HoldingValuationService
from app.services.portfolio.position_service import PositionService
from app.services.portfolio.types import (
    AccountValue,
    AllocationItem,
    DashboardSummary,
    HoldingValue,
    PerformancePoint,
    PositionResult,
    TopHolding,
)
from app.services.repositories import AccountRepository, HoldingRepository, PriceRepository
from app.services.repositories.snapshot_repository import SnapshotRepository
from app.services.repositories.transaction_repository import TransactionRepository
from app.services.shared.currency_service import CurrencyService

logger = logging.getLogger(__name__)


class DashboardService:
    """Builds the dashboard summary for a set of accounts."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._valuation = HoldingValuationService(db)
        self._currency = CurrencyService(db)
        self._account_repo = AccountRepository(db)
        self._holding_repo = HoldingRepository(db)
        self._snapshot_repo = SnapshotRepository(db)
        self._price_repo = PriceRepository(db)
        self._txn_repo = TransactionRepository(db)

    def get_summary(self, account_ids: list[int]) -> DashboardSummary:
        """Build a complete dashboard summary.

        All monetary values are computed in USD and ILS.
        Display-currency conversion is the router's responsibility.
        """
        # Single DB query for all holdings - shared across accounts, allocation,
        # cost/cash, and top holdings (eliminates N+1 per-account queries)
        rows = self._holding_repo.find_active_with_assets_and_accounts(account_ids)

        # Pre-compute valuations once — shared across all 4 sub-methods
        valuations: dict[int, HoldingValue] = {}
        for holding, asset, _account_name in rows:
            hv = self._value_asset_holding(asset, holding.quantity)
            if hv is not None:
                valuations[holding.id] = hv

        accounts = self._build_accounts(account_ids, rows, valuations)
        total_usd = sum((a.value_usd for a in accounts), Decimal("0"))
        total_ils = sum((a.value_ils for a in accounts), Decimal("0"))

        day_change_usd, day_change_pct, prev_close_usd = self._calc_day_change(
            account_ids, total_usd
        )

        cost_basis_usd, unrealized_pnl_usd, cash_usd = self._aggregate_from_positions(account_ids)

        # Combine unrealized P&L (active positions) + realized P&L (sold positions)
        realized_pnl_usd = self._txn_repo.sum_realized_pnl_usd(account_ids)
        total_pnl_usd = unrealized_pnl_usd + realized_pnl_usd
        pnl_pct = (total_pnl_usd / cost_basis_usd * 100) if cost_basis_usd > 0 else None

        return DashboardSummary(
            total_value_usd=total_usd,
            total_value_ils=total_ils,
            day_change_usd=day_change_usd,
            day_change_pct=day_change_pct,
            previous_close_value_usd=prev_close_usd,
            accounts=accounts,
            asset_allocation=self._calc_allocation(rows, valuations),
            top_holdings=self._calc_top_holdings(rows, valuations),
            historical_performance=self._get_performance(account_ids),
            total_cost_basis_usd=cost_basis_usd,
            total_cash_usd=cash_usd,
            total_return_usd=total_pnl_usd,
            total_return_pct=pnl_pct,
            unrealized_pnl_usd=unrealized_pnl_usd,
            realized_pnl_usd=realized_pnl_usd,
        )

    _MAX_POSITIONS = 10_000  # upper bound for fetching all positions

    def get_movers(
        self, account_ids: list[int], *, limit: int = 3
    ) -> tuple[list[PositionResult], list[PositionResult]]:
        """Return top gainers and losers by day_change_pct."""
        position_svc = PositionService(self._db)
        positions, _ = position_svc.get_positions(account_ids, limit=self._MAX_POSITIONS)

        with_change = [p for p in positions if p.day_change_pct is not None]
        by_pct = sorted(with_change, key=lambda p: p.day_change_pct, reverse=True)

        # ty can't narrow Decimal|None through list-comp filter (day_change_pct is non-None here)
        gainers = [p for p in by_pct if p.day_change_pct > 0][:limit]  # ty: ignore[unsupported-operator]
        # Reverse so most negative comes first
        losers = [p for p in by_pct if p.day_change_pct < 0][-limit:][::-1]  # ty: ignore[unsupported-operator]

        return gainers, losers

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _value_asset_holding(self, asset: Asset, quantity: Decimal) -> HoldingValue | None:
        """Shorthand for valuing a holding from an Asset ORM object."""
        return self._valuation.value_holding(
            asset_id=asset.id,
            ticker=asset.symbol,
            name=asset.name,
            asset_class=asset.asset_class,
            currency=asset.currency or "USD",
            quantity=quantity,
            last_fetched_price=asset.last_fetched_price,
        )

    def _to_usd(self, amount: Decimal, currency: str) -> Decimal:
        """Convert an amount from *currency* to USD."""
        if currency == "USD":
            return amount
        rate = self._currency.get_exchange_rate(currency, "USD")
        return amount * rate if rate else amount

    # ------------------------------------------------------------------
    # Private section builders
    # ------------------------------------------------------------------

    def _build_accounts(
        self,
        account_ids: list[int],
        rows: list[tuple[Holding, Asset, str]],
        valuations: dict[int, HoldingValue],
    ) -> list[AccountValue]:
        accounts = self._account_repo.find_active_by_ids(account_ids)
        usd_ils = self._currency.get_exchange_rate("USD", "ILS")

        # Group pre-fetched valuations and count holdings by account_id
        value_by_account: dict[int, Decimal] = {}
        count_by_account: dict[int, int] = {}
        for holding, _asset, _account_name in rows:
            hv = valuations.get(holding.id)
            if hv is not None:
                value_by_account[holding.account_id] = (
                    value_by_account.get(holding.account_id, Decimal("0")) + hv.market_value_usd
                )
            count_by_account[holding.account_id] = count_by_account.get(holding.account_id, 0) + 1

        result: list[AccountValue] = []
        for account in accounts:
            account_usd = value_by_account.get(account.id, Decimal("0"))
            account_ils = account_usd * usd_ils if usd_ils else account_usd

            result.append(
                AccountValue(
                    account_id=account.id,
                    name=account.name,
                    account_type=account.account_type,
                    institution=account.institution,
                    currency=account.currency,
                    value_usd=account_usd,
                    value_ils=account_ils,
                    broker_type=account.broker_type,
                    holding_count=count_by_account.get(account.id, 0),
                )
            )
        return result

    def _calc_day_change(
        self, account_ids: list[int], total_value_usd: Decimal
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        yesterday = date.today() - timedelta(days=1)
        prev_usd = self._snapshot_repo.sum_values_by_date(account_ids, yesterday)

        if prev_usd and prev_usd > 0:
            change = total_value_usd - prev_usd
            pct = (change / prev_usd) * 100
            return change, pct, prev_usd

        return None, None, prev_usd

    def _calc_allocation(
        self,
        rows: list[tuple[Holding, Asset, str]],
        valuations: dict[int, HoldingValue],
    ) -> list[AllocationItem]:
        buckets: dict[str, dict] = {}
        for holding, asset, _account_name in rows:
            hv = valuations.get(holding.id)
            if hv is None:
                continue

            cls = asset.asset_class or "Unknown"
            bucket = buckets.setdefault(cls, {"value": Decimal("0"), "count": 0})
            bucket["value"] += hv.market_value_usd
            bucket["count"] += 1

        items = [
            AllocationItem(asset_class=cls, total_value=b["value"], holding_count=b["count"])
            for cls, b in buckets.items()
        ]
        items.sort(key=lambda x: x.total_value, reverse=True)
        return items

    def _aggregate_from_positions(self, account_ids: list[int]) -> tuple[Decimal, Decimal, Decimal]:
        """Aggregate cost basis, P&L, and cash from the PositionService.

        Reuses the same per-position P&L logic that the Holdings page uses,
        which correctly handles currency conversion and per-holding cost basis.

        Returns (total_cost_basis_usd, total_pnl_usd, total_cash_usd).
        """
        position_svc = PositionService(self._db)
        positions, _ = position_svc.get_positions(account_ids, limit=self._MAX_POSITIONS)

        cost_basis = Decimal("0")
        pnl = Decimal("0")
        cash = Decimal("0")
        for p in positions:
            if p.asset_class == "Cash":
                if p.total_market_value_usd is not None:
                    cash += p.total_market_value_usd
            else:
                cost_basis += p.total_cost_basis_usd
                if p.total_pnl_usd is not None:
                    pnl += p.total_pnl_usd

        return cost_basis, pnl, cash

    def _calc_top_holdings(
        self,
        rows: list[tuple[Holding, Asset, str]],
        valuations: dict[int, HoldingValue],
        limit: int = 5,
    ) -> list[TopHolding]:
        # Batch-fetch previous closes for all non-cash assets (single query)
        today = date.today()
        non_cash_asset_ids = list(
            {
                asset.id
                for _holding, asset, _account_name in rows
                if asset.asset_class != "Cash"
                and asset.last_fetched_price
                and asset.last_fetched_price > 0
            }
        )
        prev_closes = self._price_repo.find_previous_closes(non_cash_asset_ids, today)

        items: list[TopHolding] = []
        for holding, asset, account_name in rows:
            hv = valuations.get(holding.id)
            if hv is None:
                continue

            price = Decimal("1") if hv.is_cash else (asset.last_fetched_price or Decimal("0"))

            day_change_pct: Decimal | None = None
            if not hv.is_cash and asset.last_fetched_price and asset.last_fetched_price > 0:
                prev = prev_closes.get(asset.id)
                if prev and prev.closing_price and prev.closing_price > 0:
                    day_change_pct = (
                        (asset.last_fetched_price - prev.closing_price) / prev.closing_price * 100
                    )

            # Convert cost_basis from native currency to USD
            cost_basis_usd = self._to_usd(
                holding.cost_basis or Decimal("0"), asset.currency or "USD"
            )

            items.append(
                TopHolding(
                    holding_id=holding.id,
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    name=asset.name,
                    asset_class=asset.asset_class,
                    account_name=account_name,
                    quantity=holding.quantity,
                    cost_basis=cost_basis_usd,
                    current_price=price,
                    currency=asset.currency or "USD",
                    market_value_usd=hv.market_value_usd,
                    day_change_pct=day_change_pct,
                    is_favorite=asset.is_favorite,
                ),
            )

        items.sort(key=lambda x: x.market_value_usd, reverse=True)
        return items[:limit]

    def _get_performance(self, account_ids: list[int], days: int = 30) -> list[PerformancePoint]:
        rows = self._snapshot_repo.find_aggregated_performance(account_ids, days)

        if not rows:
            return []

        # Filter out dates with incomplete account coverage.
        # Use local consistency: compare each date against ±2 neighbors.
        chronological = sorted(rows, key=lambda r: r.date)
        counts = [r.account_count for r in chronological]
        return [
            PerformancePoint(
                date=str(r.date),
                value_usd=float(r.total_usd or 0),
                value_ils=float(r.total_ils or 0),
            )
            for i, r in enumerate(chronological)
            if r.account_count >= max(counts[max(0, i - 2) : i + 3]) * 0.7
        ]
