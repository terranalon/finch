from datetime import date
from decimal import Decimal

from app.database import SessionLocal
from app.services.currency_service import CurrencyService
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.price_fetcher import PriceFetcher

db = SessionLocal()
holdings = PortfolioReconstructionService.reconstruct_holdings(
    db, 7, date.today(), apply_ticker_changes=True
)

total_usd = Decimal("0")

print("Portfolio Value with Cash Deductions:")
print("=" * 70)

for h in sorted(holdings, key=lambda x: x["symbol"]):
    symbol = h["symbol"]
    quantity = h["quantity"]
    asset_id = h["asset_id"]
    currency = h["currency"]
    asset_class = h.get("asset_class", "")

    if asset_class == "Cash":
        if quantity > 0:
            if currency != "USD":
                rate = CurrencyService.get_exchange_rate(db, currency, "USD", date.today())
                value_usd = quantity * rate if rate else quantity
            else:
                value_usd = quantity
            total_usd += value_usd
            print(
                f"{symbol:15s} {float(quantity):>12.2f} {currency:>4s} = ${float(value_usd):>12.2f} USD"
            )
    else:
        price = PriceFetcher.get_price_for_date(db, asset_id, date.today())
        if price and price > 0:
            value_native = quantity * price
            if currency != "USD":
                rate = CurrencyService.get_exchange_rate(db, currency, "USD", date.today())
                value_usd = value_native * rate if rate else value_native
            else:
                value_usd = value_native
            total_usd += value_usd
            print(
                f"{symbol:15s} {float(quantity):>8.2f} @ ${float(price):>8.2f} = ${float(value_usd):>12.2f} USD"
            )

print("=" * 70)
print(f"TOTAL: ${float(total_usd):,.2f} USD")
print("IBKR:  $48,443.83 USD")
print(f"Diff:  ${float(total_usd - Decimal('48443.83')):,.2f} USD")
