"""Delete Forex Conversion transactions that came from STK: FxTransactions.

These are duplicates of Trade Settlement transactions.
"""

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

print("=== FINDING STK FOREX CONVERSIONS TO DELETE ===\n")

# Find all Forex Conversion transactions that have "STK:" in notes
stk_forex = (
    db.query(Transaction)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(
        Transaction.type == "Forex Conversion",
        Asset.asset_class == "Cash",
        Transaction.notes.like("%STK:%"),
    )
    .all()
)

print(f"Found {len(stk_forex)} Forex Conversion transactions with 'STK:' in notes\n")

if not stk_forex:
    print("No STK forex conversions found!")
    db.close()
    exit(0)

# Show sample
print("Sample transactions to delete:\n")
for i, txn in enumerate(stk_forex[:10]):
    holding = db.query(Holding).get(txn.holding_id)
    asset = db.query(Asset).get(holding.asset_id)
    print(f"{txn.date} {asset.symbol:4s} {float(txn.amount):+12.2f} - {txn.notes[:50]}")

print(f"\n...and {max(0, len(stk_forex) - 10)} more")
print(f"\nTotal to delete: {len(stk_forex)}")

response = input("\nProceed with deletion? (yes/no): ")

if response.lower() != "yes":
    print("Cancelled.")
    db.close()
    exit(0)

print("\nDeleting STK forex conversions...")

for txn in stk_forex:
    db.delete(txn)

db.commit()

print(f"\n✓ Successfully deleted {len(stk_forex)} STK forex conversion transactions")

# Verify
remaining = (
    db.query(Transaction)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(
        Transaction.type == "Forex Conversion",
        Asset.asset_class == "Cash",
        Transaction.notes.like("%STK:%"),
    )
    .count()
)

if remaining == 0:
    print("✓ No STK forex conversions remaining")
else:
    print(f"WARNING: Still found {remaining} STK forex conversions!")

db.close()
