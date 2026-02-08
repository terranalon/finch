"""Shared holding-valuation logic.

This service is the single source of truth for "what is a holding worth?"
It replaces duplicated inline code in dashboard.py, positions.py, and
snapshot_service._value_holdings().
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.constants import AssetClass
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.portfolio.types import HoldingValue
from app.services.shared.currency_service import CurrencyService


class HoldingValuationService:
    """Values holdings in a target currency.

    Instance-based so the db session is injected once and shared across
    all calls, matching the pattern established by PortfolioValuationService.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._currency = CurrencyService(db)

    def value_holding(
        self,
        *,
        asset_id: int,
        ticker: str,
        name: str | None,
        asset_class: str | None,
        currency: str,
        quantity: Decimal,
        last_fetched_price: Decimal | None,
        valuation_date: date | None = None,
    ) -> HoldingValue | None:
        """Value a single holding.

        Returns None when the holding should be excluded (e.g. negative cash
        or zero-price non-cash asset).
        """
        is_cash = asset_class == AssetClass.CASH

        if is_cash:
            if quantity <= 0:
                return None
            market_value_native = quantity
        else:
            price = self._resolve_price(asset_id, last_fetched_price, valuation_date)
            if price is None:
                return None
            market_value_native = quantity * price

        market_value_usd = self._to_usd(market_value_native, currency, valuation_date)

        return HoldingValue(
            asset_id=asset_id,
            ticker=ticker,
            name=name,
            asset_class=asset_class,
            currency=currency,
            quantity=quantity,
            market_value_usd=market_value_usd,
            market_value_native=market_value_native,
            is_cash=is_cash,
        )

    def value_holdings_batch(
        self,
        holdings: list[dict],
        valuation_date: date | None = None,
    ) -> tuple[Decimal, Decimal]:
        """Value a batch of holdings, returning totals in USD and ILS.

        Each holding dict must have keys: asset_id, quantity, currency, asset_class.
        Optional keys: symbol, name, last_fetched_price.

        Returns:
            (total_value_usd, total_value_ils)
        """
        total_usd = Decimal("0")

        for h in holdings:
            result = self.value_holding(
                asset_id=h["asset_id"],
                ticker=h.get("symbol", ""),
                name=h.get("name"),
                asset_class=h["asset_class"],
                currency=h["currency"],
                quantity=h["quantity"],
                last_fetched_price=h.get("last_fetched_price"),
                valuation_date=valuation_date,
            )
            if result is not None:
                total_usd += result.market_value_usd

        total_ils = self._convert(total_usd, "USD", "ILS", valuation_date)
        return total_usd, total_ils

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_price(
        self,
        asset_id: int,
        last_fetched_price: Decimal | None,
        valuation_date: date | None,
    ) -> Decimal | None:
        """Get the price to use for a non-cash asset."""
        if valuation_date and valuation_date < date.today():
            price = PriceFetcher.get_price_for_date(self._db, asset_id, valuation_date)
            return price if price is not None and price > 0 else None

        # Current valuation -- use the last fetched price
        if last_fetched_price is not None and last_fetched_price > 0:
            return last_fetched_price
        return None

    def _to_usd(
        self,
        amount: Decimal,
        from_currency: str,
        valuation_date: date | None,
    ) -> Decimal:
        """Convert *amount* to USD."""
        if from_currency == "USD":
            return amount
        return self._convert(amount, from_currency, "USD", valuation_date)

    def _convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        valuation_date: date | None,
    ) -> Decimal:
        """Convert between currencies, falling back to the original amount."""
        rate = self._currency.get_exchange_rate(from_currency, to_currency, valuation_date)
        return amount * rate if rate else amount
