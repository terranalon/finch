"""Position aggregation service.

Aggregates holdings by asset across accounts, computing market values,
P&L, and day changes. Extracted from routers/positions.py.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import AssetClass
from app.models import Account, Asset, Holding
from app.models.asset_daily_metrics import AssetDailyMetrics
from app.services.portfolio.types import AccountHolding, PositionResult
from app.services.portfolio.valuation_service import PortfolioValuationService
from app.services.portfolio.valuation_types import DayChangeResult
from app.services.repositories.price_repository import PriceRepository
from app.services.shared.currency_service import CurrencyService


class PositionService:
    """Aggregates holdings into positions grouped by asset."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._currency = CurrencyService(db)

    def get_positions(
        self,
        account_ids: list[int],
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PositionResult], int]:
        """Build aggregated positions for the given accounts.

        Returns positions sorted by total market value (USD) descending.
        Pagination is applied after aggregation (positions are grouped by asset).
        """
        if not account_ids:
            return [], 0

        holdings_query = (
            self._db.query(Holding, Account, Asset)
            .join(Account, Holding.account_id == Account.id)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(Holding.is_active.is_(True), Holding.account_id.in_(account_ids))
            .all()
        )

        positions_map: dict[int, _PositionAccumulator] = {}

        for holding, account, asset in holdings_query:
            acc = positions_map.setdefault(asset.id, _PositionAccumulator(asset))
            acc.add_holding(holding, account, self._currency)

        # Batch day-change calculation
        valuation_svc = PortfolioValuationService(self._db)
        current_prices = {aid: acc.current_price for aid, acc in positions_map.items()}
        day_changes = valuation_svc.calculate_day_changes_batch(
            [acc.asset for acc in positions_map.values()],
            current_prices,
            date.today(),
        )

        # Batch market-cap fetch (latest AssetDailyMetrics per asset)
        asset_ids = list(positions_map.keys())
        market_caps = self._fetch_market_caps(asset_ids)

        # Batch 7-day change calculation
        week_changes = self._calc_week_changes(asset_ids, positions_map)

        results = [
            acc.to_result(
                day_changes.get(aid),
                market_cap=market_caps.get(aid),
                week_change_pct=week_changes.get(aid),
            )
            for aid, acc in positions_map.items()
        ]

        results.sort(
            key=lambda r: r.total_market_value_usd
            if r.total_market_value_usd is not None
            else r.total_cost_basis_usd,
            reverse=True,
        )

        total = len(results)
        return results[skip : skip + limit], total

    def _fetch_market_caps(self, asset_ids: list[int]) -> dict[int, Decimal]:
        """Batch-fetch latest market cap from asset_daily_metrics."""
        if not asset_ids:
            return {}

        latest_sq = (
            self._db.query(
                AssetDailyMetrics.asset_id,
                func.max(AssetDailyMetrics.date).label("max_date"),
            )
            .filter(
                AssetDailyMetrics.asset_id.in_(asset_ids),
                AssetDailyMetrics.market_cap.isnot(None),
            )
            .group_by(AssetDailyMetrics.asset_id)
            .subquery()
        )

        rows = (
            self._db.query(AssetDailyMetrics.asset_id, AssetDailyMetrics.market_cap)
            .join(
                latest_sq,
                (AssetDailyMetrics.asset_id == latest_sq.c.asset_id)
                & (AssetDailyMetrics.date == latest_sq.c.max_date),
            )
            .all()
        )

        return {aid: mc for aid, mc in rows if mc is not None}

    def _calc_week_changes(
        self,
        asset_ids: list[int],
        positions_map: dict[int, "_PositionAccumulator"],
    ) -> dict[int, Decimal]:
        """Calculate 7-day price change percentage for each asset."""
        if not asset_ids:
            return {}

        price_repo = PriceRepository(self._db)
        recent_prices = price_repo.find_latest_by_assets(asset_ids, limit_per_asset=8)
        week_ago = date.today() - timedelta(days=7)

        result: dict[int, Decimal] = {}
        for aid, prices in recent_prices.items():
            current = positions_map[aid].current_price
            if current is None or current <= 0:
                continue
            # Find the closing price on or just before 7 days ago
            ref = next((p for p in prices if p.date <= week_ago), None)
            if ref is None or ref.closing_price is None or ref.closing_price <= 0:
                continue
            result[aid] = ((current - ref.closing_price) / ref.closing_price) * 100

        return result


# ------------------------------------------------------------------
# Internal accumulator -- collects per-asset data while iterating
# ------------------------------------------------------------------


_NO_DAY_CHANGE = DayChangeResult(
    day_change=None,
    day_change_pct=None,
    previous_close_price=None,
    day_change_date=None,
    is_market_closed=False,
)


class _PositionAccumulator:
    """Mutable accumulator used only inside PositionService.get_positions."""

    def __init__(self, asset: Asset) -> None:
        self.asset = asset
        self.current_price: Decimal | None = (
            Decimal("1") if asset.asset_class == AssetClass.CASH else asset.last_fetched_price
        )
        self.total_quantity = Decimal("0")
        self.total_cost_basis_usd = Decimal("0")
        self.total_cost_basis_native = Decimal("0")
        self.accounts: list[AccountHolding] = []

    @property
    def currency(self) -> str:
        return self.asset.currency or "USD"

    def add_holding(
        self,
        holding: Holding,
        account: Account,
        currency_svc: CurrencyService,
    ) -> None:
        is_cash = self.asset.asset_class == AssetClass.CASH
        price = Decimal("1") if is_cash else (self.asset.last_fetched_price or Decimal("0"))
        market_value_native = (
            holding.quantity if is_cash else (holding.quantity * price if price else Decimal("0"))
        )

        cost_basis_native = holding.cost_basis
        pnl_native = (market_value_native - cost_basis_native) if price else None
        pnl_pct = (
            (pnl_native / cost_basis_native * 100)
            if (pnl_native is not None and price and cost_basis_native > 0)
            else None
        )

        # Convert to USD
        if self.currency != "USD":
            rate = currency_svc.get_exchange_rate(self.currency, "USD")
            cost_basis_usd = cost_basis_native * rate if rate else cost_basis_native
            market_value_usd = (
                market_value_native * rate if (rate and price) else market_value_native
            )
        else:
            cost_basis_usd = cost_basis_native
            market_value_usd = market_value_native

        pnl_usd = (market_value_usd - cost_basis_usd) if price else None

        self.total_quantity += holding.quantity
        self.total_cost_basis_usd += cost_basis_usd
        self.total_cost_basis_native += cost_basis_native

        self.accounts.append(
            AccountHolding(
                holding_id=holding.id,
                account_id=account.id,
                account_name=account.name,
                account_type=account.account_type,
                institution=account.institution,
                quantity=holding.quantity,
                cost_basis_native=cost_basis_native,
                market_value_native=market_value_native if price else None,
                pnl_native=pnl_native,
                cost_basis_usd=cost_basis_usd,
                market_value_usd=market_value_usd if price else None,
                pnl_usd=pnl_usd,
                pnl_pct=pnl_pct,
                strategy_horizon=holding.strategy_horizon,
            )
        )

    def to_result(
        self,
        day_change: DayChangeResult | None = None,
        *,
        market_cap: Decimal | None = None,
        week_change_pct: Decimal | None = None,
    ) -> PositionResult:
        price = self.current_price
        total_mv_native = (self.total_quantity * price) if price is not None else None
        total_pnl_native = (
            (total_mv_native - self.total_cost_basis_native)
            if total_mv_native is not None
            else None
        )
        total_pnl_pct = (
            (total_pnl_native / self.total_cost_basis_native * 100)
            if (total_pnl_native is not None and self.total_cost_basis_native > 0)
            else None
        )

        # USD totals
        if total_mv_native is None:
            total_mv_usd = None
        elif self.currency != "USD":
            # Re-derive from per-account USD values (already accumulated)
            total_mv_usd = sum(
                (a.market_value_usd for a in self.accounts if a.market_value_usd is not None),
                Decimal("0"),
            )
        else:
            total_mv_usd = total_mv_native

        total_pnl_usd = (
            (total_mv_usd - self.total_cost_basis_usd) if total_mv_usd is not None else None
        )

        dc = day_change or _NO_DAY_CHANGE

        return PositionResult(
            asset_id=self.asset.id,
            symbol=self.asset.symbol,
            name=self.asset.name,
            asset_class=self.asset.asset_class,
            category=self.asset.category,
            industry=self.asset.industry,
            currency=self.currency,
            is_favorite=self.asset.is_favorite,
            current_price=price,
            previous_close_price=dc.previous_close_price,
            day_change=dc.day_change,
            day_change_pct=dc.day_change_pct,
            day_change_date=dc.day_change_date,
            is_market_closed=dc.is_market_closed,
            total_quantity=self.total_quantity,
            total_cost_basis_native=self.total_cost_basis_native,
            total_market_value_native=total_mv_native,
            total_pnl_native=total_pnl_native,
            avg_cost_per_unit_native=(
                self.total_cost_basis_native / self.total_quantity
                if self.total_quantity > 0
                else Decimal("0")
            ),
            total_cost_basis_usd=self.total_cost_basis_usd,
            total_market_value_usd=total_mv_usd,
            total_pnl_usd=total_pnl_usd,
            total_pnl_pct=total_pnl_pct,
            avg_cost_per_unit_usd=(
                self.total_cost_basis_usd / self.total_quantity
                if self.total_quantity > 0
                else Decimal("0")
            ),
            market_cap=market_cap,
            week_change_pct=week_change_pct,
            accounts=self.accounts,
        )
