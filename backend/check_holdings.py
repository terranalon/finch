"""Check holdings after import."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from decimal import Decimal

from app.database import SessionLocal
from app.models import Account, Holding, Transaction
from app.services.kraken_client import KrakenClient, KrakenCredentials

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    # Get API balances for comparison
    account = db.query(Account).filter(Account.id == KRAKEN_ACCOUNT_ID).first()
    creds = account.meta_data["kraken"]
    client = KrakenClient(KrakenCredentials(api_key=creds["api_key"], api_secret=creds["api_secret"]))
    api_balances = client.get_balance()

    print("=== Holdings comparison ===")
    print(f"{'Symbol':<10} {'DB Qty':>15} {'API Qty':>15} {'Diff':>12} {'Txn Count':>10}")
    print("-" * 65)

    holdings = db.query(Holding).filter(Holding.account_id == KRAKEN_ACCOUNT_ID).all()
    for h in sorted(holdings, key=lambda x: x.asset.symbol):
        symbol = h.asset.symbol
        db_qty = h.quantity
        api_qty = api_balances.get(symbol, Decimal("0"))
        diff = db_qty - api_qty
        txn_count = db.query(Transaction).filter(Transaction.holding_id == h.id).count()

        if db_qty != 0 or api_qty != 0:
            status = "✓" if abs(diff) < Decimal("0.0001") else "✗"
            print(f"{symbol:<10} {db_qty:>15.8f} {api_qty:>15.8f} {diff:>12.8f} {txn_count:>10} {status}")

    # Check transaction types for USD
    print("\n=== USD Transaction Types ===")
    usd_holding = next((h for h in holdings if h.asset.symbol == "USD"), None)
    if usd_holding:
        txns = db.query(Transaction).filter(Transaction.holding_id == usd_holding.id).all()
        by_type = {}
        for t in txns:
            if t.type not in by_type:
                by_type[t.type] = {"count": 0, "total": Decimal("0")}
            by_type[t.type]["count"] += 1
            by_type[t.type]["total"] += t.amount or Decimal("0")

        for txn_type, data in sorted(by_type.items()):
            print(f"  {txn_type}: count={data['count']}, total={data['total']:.2f}")

        print(f"\n  Sum of all USD transactions: {sum(d['total'] for d in by_type.values()):.2f}")
        print(f"  DB USD quantity: {usd_holding.quantity:.2f}")
        print(f"  API USD balance: {api_balances.get('USD', 0):.2f}")

finally:
    db.close()
