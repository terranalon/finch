"""Reset Kraken account data."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from app.database import SessionLocal
from app.models import Holding, Transaction

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    holdings = db.query(Holding).filter(Holding.account_id == KRAKEN_ACCOUNT_ID).all()
    total_txns = 0
    for holding in holdings:
        txn_count = db.query(Transaction).filter(Transaction.holding_id == holding.id).delete()
        total_txns += txn_count
        holding.quantity = 0
        holding.cost_basis = 0
        holding.is_active = False
    db.commit()
    print(f"✓ Deleted {total_txns} transactions, reset {len(holdings)} holdings")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
