"""Check STRK transactions."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from decimal import Decimal

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    asset = db.query(Asset).filter(Asset.symbol == "STRK").first()
    holding = db.query(Holding).filter(
        Holding.account_id == KRAKEN_ACCOUNT_ID,
        Holding.asset_id == asset.id
    ).first()

    print(f"STRK Holding: qty={holding.quantity}")
    print("\nTransactions:")

    txns = db.query(Transaction).filter(Transaction.holding_id == holding.id).order_by(Transaction.date).all()
    total = Decimal("0")
    for t in txns:
        qty = t.quantity or Decimal("0")
        if t.type == "Sell":
            total -= qty
            sign = "-"
        else:
            total += qty
            sign = "+"
        print(f"  {t.date} | {t.type:15} | {sign}{qty:>15.8f} | running: {total:>15.8f} | {t.notes[:50] if t.notes else ''}")

    print(f"\nFinal calculated: {total}")
    print(f"DB quantity: {holding.quantity}")

finally:
    db.close()
