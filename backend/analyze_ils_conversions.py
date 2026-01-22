"""Analyze ILS deposits vs forex conversions."""

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

# Get ILS forex conversions
ils_forex = (
    db.query(func.sum(Transaction.amount).label("total"))
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(
        Transaction.type == "Forex Conversion", Asset.symbol == "ILS", Asset.asset_class == "Cash"
    )
    .scalar()
)

print(f"ILS Forex Conversions (outgoing): ₪{float(ils_forex or 0):,.2f}")

# Get ILS deposits
ils_deposits = (
    db.query(func.sum(Transaction.amount).label("total"))
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Deposit", Asset.symbol == "ILS", Asset.asset_class == "Cash")
    .scalar()
)

print(f"ILS Deposits (incoming): ₪{float(ils_deposits or 0):,.2f}")
print(f"\nNet ILS (should be ~₪0): ₪{float(ils_deposits or 0) + float(ils_forex or 0):,.2f}")
print(f"Missing ILS conversions: ₪{-1 * (float(ils_deposits or 0) + float(ils_forex or 0)):,.2f}")

# Check USD from ILS conversions
usd_from_ils = (
    db.query(func.count(Transaction.id).label("count"), func.sum(Transaction.amount).label("total"))
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(
        Transaction.type == "Forex Conversion",
        Asset.symbol == "USD",
        Asset.asset_class == "Cash",
        Transaction.notes.like("%ILS%"),
    )
    .first()
)

print(
    f"\nUSD received from ILS conversions: {usd_from_ils.count} txns, ${float(usd_from_ils.total or 0):,.2f}"
)

# Estimate USD from missing ILS conversions (approx rate 0.28)
missing_ils = -1 * (float(ils_deposits or 0) + float(ils_forex or 0))
estimated_missing_usd = missing_ils * 0.28

print(f"Estimated missing USD from ILS: ${estimated_missing_usd:,.2f} (at ~0.28 rate)")
print(f"\nCurrent USD shortfall: ${10098.94 - (-1596.97):,.2f}")

db.close()
