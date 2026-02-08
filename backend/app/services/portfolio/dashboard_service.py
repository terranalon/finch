"""Dashboard summary service.

Computes all sections of the dashboard (account values, allocation,
top holdings, performance) in USD. Display-currency conversion is the
router's responsibility.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Account, Asset, HistoricalSnapshot, Holding
from app.services.portfolio.holding_valuation_service import HoldingValuationService
from app.services.portfolio.types import (
    AccountValue,
    AllocationItem,
    DashboardSummary,
    HoldingValue,
    PerformancePoint,
    TopHolding,
)
from app.services.shared.currency_service import CurrencyService


class DashboardService:
    """Builds the dashboard summary for a set of accounts."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._valuation = HoldingValuationService(db)
        self._currency = CurrencyService(db)

    def get_summary(self, account_ids: list[int]) -> DashboardSummary:
        """Build a complete dashboard summary.

        All monetary values are computed in USD and ILS.
        Display-currency conversion is the router's responsibility.
        """
        accounts = self._build_accounts(account_ids)
        total_usd = sum(a.value_usd for a in accounts)
        total_ils = sum(a.value_ils for a in accounts)

        day_change_usd, day_change_pct, prev_close_usd = self._calc_day_change(
            account_ids, total_usd
        )

        return DashboardSummary(
            total_value_usd=total_usd,
            total_value_ils=total_ils,
            day_change_usd=day_change_usd,
            day_change_pct=day_change_pct,
            previous_close_value_usd=prev_close_usd,
            accounts=accounts,
            asset_allocation=self._calc_allocation(account_ids),
            top_holdings=self._calc_top_holdings(account_ids),
            historical_performance=self._get_performance(account_ids),
        )

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

    # ------------------------------------------------------------------
    # Private section builders
    # ------------------------------------------------------------------

    def _build_accounts(self, account_ids: list[int]) -> list[AccountValue]:
        accounts = (
            self._db.query(Account)
            .filter(Account.is_active.is_(True), Account.id.in_(account_ids))
            .all()
        )

        usd_ils = self._currency.get_exchange_rate("USD", "ILS")

        result: list[AccountValue] = []
        for account in accounts:
            holdings = (
                self._db.query(Holding)
                .filter(Holding.account_id == account.id, Holding.is_active.is_(True))
                .all()
            )

            account_usd = Decimal("0")
            for holding in holdings:
                hv = self._value_asset_holding(holding.asset, holding.quantity)
                if hv is not None:
                    account_usd += hv.market_value_usd

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
                )
            )
        return result

    def _calc_day_change(
        self, account_ids: list[int], total_value_usd: Decimal
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        yesterday = date.today() - timedelta(days=1)
        row = (
            self._db.query(func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"))
            .filter(
                HistoricalSnapshot.date == yesterday,
                HistoricalSnapshot.account_id.in_(account_ids),
            )
            .first()
        )

        prev_usd = Decimal(str(row.total_usd or 0)) if row else None

        if prev_usd and prev_usd > 0:
            change = total_value_usd - prev_usd
            pct = (change / prev_usd) * 100
            return change, pct, prev_usd

        return None, None, prev_usd

    def _calc_allocation(self, account_ids: list[int]) -> list[AllocationItem]:
        holdings_with_assets = (
            self._db.query(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .filter(Holding.is_active.is_(True), Holding.account_id.in_(account_ids))
            .all()
        )

        buckets: dict[str, dict] = {}
        for holding, asset in holdings_with_assets:
            hv = self._value_asset_holding(asset, holding.quantity)
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

    def _calc_top_holdings(self, account_ids: list[int], limit: int = 10) -> list[TopHolding]:
        rows = (
            self._db.query(Holding, Asset, Account.name.label("account_name"))
            .join(Asset, Holding.asset_id == Asset.id)
            .join(Account, Holding.account_id == Account.id)
            .filter(Holding.is_active.is_(True), Holding.account_id.in_(account_ids))
            .all()
        )

        items: list[TopHolding] = []
        for holding, asset, account_name in rows:
            hv = self._value_asset_holding(asset, holding.quantity)
            if hv is None:
                continue

            price = Decimal("1") if hv.is_cash else (asset.last_fetched_price or Decimal("0"))
            items.append(
                TopHolding(
                    holding_id=holding.id,
                    symbol=asset.symbol,
                    name=asset.name,
                    asset_class=asset.asset_class,
                    account_name=account_name,
                    quantity=holding.quantity,
                    cost_basis=holding.cost_basis,
                    current_price=price,
                    currency=asset.currency or "USD",
                    market_value_usd=hv.market_value_usd,
                )
            )

        items.sort(key=lambda x: x.market_value_usd, reverse=True)
        return items[:limit]

    def _get_performance(self, account_ids: list[int], days: int = 30) -> list[PerformancePoint]:
        rows = (
            self._db.query(
                HistoricalSnapshot.date,
                func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"),
                func.sum(HistoricalSnapshot.total_value_ils).label("total_ils"),
            )
            .filter(HistoricalSnapshot.account_id.in_(account_ids))
            .group_by(HistoricalSnapshot.date)
            .order_by(HistoricalSnapshot.date.desc())
            .limit(days)
            .all()
        )

        return [
            PerformancePoint(
                date=str(r.date),
                value_usd=float(r.total_usd or 0),
                value_ils=float(r.total_ils or 0),
            )
            for r in reversed(rows)
        ]
