"""Portfolio lifecycle management - valuation and deletion."""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.constants import AssetClass
from app.models import Asset, Holding, Portfolio
from app.models.account import Account
from app.schemas.portfolio import SharedAccountInfo
from app.services.shared.currency_service import CurrencyService


@dataclass(frozen=True)
class PortfolioValuation:
    """Result of portfolio value calculation with per-account breakdown."""

    total: float
    per_account: dict[int, float] = field(default_factory=dict)


class PortfolioManagementService:
    """Handles portfolio valuation and lifecycle operations."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._currency = CurrencyService(db)

    def calculate_portfolio_value(self, portfolio: Portfolio) -> PortfolioValuation:
        account_values_usd = {
            account.id: self._calculate_account_value_usd(account) for account in portfolio.accounts
        }

        total_value_usd = sum(account_values_usd.values(), Decimal("0"))

        if portfolio.default_currency != "USD":
            rate = self._currency.get_exchange_rate("USD", portfolio.default_currency)
            convert = (lambda v: float(v * rate)) if rate else (lambda v: float(v))
        else:
            convert = float

        return PortfolioValuation(
            total=convert(total_value_usd),
            per_account={
                account_id: convert(value) for account_id, value in account_values_usd.items()
            },
        )

    def _calculate_account_value_usd(self, account: Account) -> Decimal:
        holdings = (
            self._db.query(Holding)
            .filter(Holding.account_id == account.id, Holding.is_active.is_(True))
            .all()
        )

        total = Decimal("0")
        for holding in holdings:
            asset = self._db.query(Asset).filter(Asset.id == holding.asset_id).first()
            if not asset:
                continue

            asset_currency = asset.currency or "USD"

            if asset.asset_class == AssetClass.CASH:
                if holding.quantity <= 0:
                    continue
                market_value_native = holding.quantity
            else:
                if not asset.last_fetched_price:
                    continue
                market_value_native = holding.quantity * asset.last_fetched_price

            if asset_currency != "USD":
                rate_to_usd = self._currency.get_exchange_rate(asset_currency, "USD")
                market_value_usd = (
                    market_value_native * rate_to_usd if rate_to_usd else market_value_native
                )
            else:
                market_value_usd = market_value_native

            total += market_value_usd

        return total

    def categorize_accounts_for_deletion(
        self, portfolio: Portfolio
    ) -> tuple[list[Account], list[SharedAccountInfo]]:
        exclusive: list[Account] = []
        shared: list[SharedAccountInfo] = []

        for account in portfolio.accounts:
            other_portfolios = [p for p in account.portfolios if p.id != portfolio.id]
            if other_portfolios:
                shared = [
                    *shared,
                    SharedAccountInfo(
                        id=account.id,
                        name=account.name,
                        other_portfolios=[p.name for p in other_portfolios],
                    ),
                ]
            else:
                exclusive = [*exclusive, account]

        return exclusive, shared

    def delete_portfolio_cascade(self, portfolio: Portfolio) -> None:
        exclusive, _ = self.categorize_accounts_for_deletion(portfolio)

        for account in list(portfolio.accounts):
            if account in exclusive:
                self._db.delete(account)
            else:
                account.portfolios.remove(portfolio)

        self._db.delete(portfolio)
