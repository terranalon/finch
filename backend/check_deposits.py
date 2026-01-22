"""Check all deposits in database."""

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

# Get all Deposit transactions
deposits = (
    db.query(Transaction.date, Asset.symbol, Transaction.amount)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Deposit", Asset.asset_class == "Cash")
    .order_by(Transaction.date)
    .all()
)

print(f"Total Deposit transactions in DB: {len(deposits)}\n")

for date, currency, amount in deposits:
    print(f"{date} {currency} {float(amount):>10.2f}")

ils_total = sum(float(amt) for d, c, amt in deposits if c == "ILS")
usd_total = sum(float(amt) for d, c, amt in deposits if c == "USD")

print(f"\nTotal ILS deposits: ₪{ils_total:,.2f}")
print(f"Total USD deposits: ${usd_total:,.2f}")

db.close()
