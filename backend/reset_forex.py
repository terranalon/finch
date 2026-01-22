"""Delete all Forex Conversion transactions to re-import with fixed parser."""

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

print("=== DELETING ALL FOREX CONVERSION TRANSACTIONS ===\n")

# Count forex conversions
forex_count = (
    db.query(Transaction)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Forex Conversion", Asset.asset_class == "Cash")
    .count()
)

print(f"Found {forex_count} Forex Conversion transactions\n")

if forex_count == 0:
    print("No forex conversions to delete!")
    db.close()
    exit(0)

# Show breakdown by currency
from sqlalchemy import func

breakdown = (
    db.query(
        Asset.symbol,
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total"),
    )
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Forex Conversion", Asset.asset_class == "Cash")
    .group_by(Asset.symbol)
    .all()
)

print("Breakdown by currency:\n")
for symbol, count, total in breakdown:
    print(f"  {symbol}: {count} txns, Net: {float(total or 0):+,.2f}")

print("\nAfter deletion, we will re-import with the fixed parser that skips STK: transactions")
print("This will eliminate the double-counting with Trade Settlement transactions.\n")

response = input("Proceed with deletion? (yes/no): ")

if response.lower() != "yes":
    print("Cancelled.")
    db.close()
    exit(0)

print("\nDeleting all Forex Conversion transactions...")

# Get IDs of all forex conversions
forex_ids = [
    txn.id
    for txn in db.query(Transaction)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Forex Conversion", Asset.asset_class == "Cash")
    .all()
]

# Delete them
for txn_id in forex_ids:
    txn = db.query(Transaction).get(txn_id)
    if txn:
        db.delete(txn)

db.commit()

print(f"\n✓ Successfully deleted all {len(forex_ids)} Forex Conversion transactions")
print("Now run the import to recreate them with the fixed logic.")

db.close()
