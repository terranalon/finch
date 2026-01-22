"""Delete duplicate forex transactions from database."""

from sqlalchemy import text

from app.database import SessionLocal
from app.models import Transaction

db = SessionLocal()

print("=== FINDING DUPLICATE FOREX TRANSACTIONS ===\n")

# Find all duplicate forex transactions
duplicates_query = text("""
    SELECT
        MIN(t.id) as keep_id,
        ARRAY_AGG(t.id ORDER BY t.id) as all_ids,
        h.account_id,
        a.symbol,
        t.date,
        t.amount,
        COUNT(*) as count
    FROM transactions t
    JOIN holdings h ON t.holding_id = h.id
    JOIN assets a ON h.asset_id = a.id
    WHERE t.type = 'Forex Conversion'
    AND a.asset_class = 'Cash'
    GROUP BY h.account_id, a.symbol, t.date, t.amount
    HAVING COUNT(*) > 1
    ORDER BY count DESC, t.date DESC
""")

duplicates = db.execute(duplicates_query).fetchall()

if not duplicates:
    print("No duplicate forex transactions found!")
    db.close()
    exit(0)

print(f"Found {len(duplicates)} duplicate patterns\n")

# Calculate what we'll delete
total_to_delete = 0
for row in duplicates:
    keep_id, all_ids, account_id, symbol, date, amount, count = row
    total_to_delete += count - 1  # Keep one, delete the rest
    print(f"{date} {symbol:4s} {float(amount):+12.2f} - {count} copies (keep ID {keep_id})")

print(f"\nTotal transactions to delete: {total_to_delete}")
print("This will remove duplicates, keeping one of each.\n")

response = input("Proceed with deletion? (yes/no): ")

if response.lower() != "yes":
    print("Cancelled.")
    db.close()
    exit(0)

print("\nDeleting duplicates...\n")

deleted_count = 0
for row in duplicates:
    keep_id, all_ids, account_id, symbol, date, amount, count = row

    # Get all IDs except the one we're keeping
    ids_to_delete = [id for id in all_ids if id != keep_id]

    # Delete them
    for txn_id in ids_to_delete:
        txn = db.query(Transaction).get(txn_id)
        if txn:
            db.delete(txn)
            deleted_count += 1

    if deleted_count % 10 == 0:
        print(f"Deleted {deleted_count} transactions...")

db.commit()

print(f"\n✓ Successfully deleted {deleted_count} duplicate transactions")
print("Each unique forex transaction now appears exactly once.\n")

# Verify the fix
print("=== VERIFYING: Checking for remaining duplicates ===\n")
remaining = db.execute(duplicates_query).fetchall()

if remaining:
    print(f"WARNING: Still found {len(remaining)} duplicate patterns!")
    for row in remaining[:5]:
        keep_id, all_ids, account_id, symbol, date, amount, count = row
        print(f"  {date} {symbol} {float(amount):+.2f} - {count} copies")
else:
    print("✓ No duplicates remaining - all fixed!")

db.close()
