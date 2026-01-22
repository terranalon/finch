"""Check BTC transactions."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from collections import defaultdict
from decimal import Decimal

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    btc_asset = db.query(Asset).filter(Asset.symbol == "BTC").first()
    btc_holding = db.query(Holding).filter(
        Holding.account_id == KRAKEN_ACCOUNT_ID,
        Holding.asset_id == btc_asset.id
    ).first()

    print(f"BTC Holding: qty={btc_holding.quantity}")

    txns = db.query(Transaction).filter(Transaction.holding_id == btc_holding.id).all()
    print(f"Total transactions: {len(txns)}")

    by_type = defaultdict(lambda: {"count": 0, "qty_sum": Decimal("0")})
    for t in txns:
        by_type[t.type]["count"] += 1
        qty = t.quantity or Decimal("0")
        if t.type == "Sell":
            by_type[t.type]["qty_sum"] -= qty
        else:
            by_type[t.type]["qty_sum"] += qty

    print("\nBy type:")
    total_qty = Decimal("0")
    for txn_type, data in sorted(by_type.items()):
        print(f"  {txn_type}: count={data['count']}, qty_change={data['qty_sum']:.8f}")
        total_qty += data["qty_sum"]

    print(f"\nCalculated total: {total_qty:.8f}")
    print(f"DB quantity: {btc_holding.quantity:.8f}")

    # Check for Transfer transactions
    transfer_count = sum(1 for t in txns if t.type == "Transfer")
    print(f"\nTransfer transactions in DB: {transfer_count}")

finally:
    db.close()
