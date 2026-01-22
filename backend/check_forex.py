from sqlalchemy import func

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

# Get all Forex Conversion transactions grouped by currency
print("=== FOREX CONVERSION TRANSACTIONS BY CURRENCY ===\n")
forex_txns = (
    db.query(
        Asset.symbol,
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount"),
    )
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Forex Conversion", Asset.asset_class == "Cash")
    .group_by(Asset.symbol)
    .all()
)

for symbol, count, total in forex_txns:
    print(f"{symbol}: {count} transactions, Net: {float(total or 0):+,.2f}")

# Get USD-specific transactions to understand the 52k balance
print("\n=== USD CASH IMPACT BY TRANSACTION TYPE ===\n")
usd_txns = (
    db.query(
        Transaction.type,
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount"),
    )
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Asset.symbol == "USD", Asset.asset_class == "Cash")
    .group_by(Transaction.type)
    .all()
)

for txn_type, count, total in usd_txns:
    if total:
        print(f"{txn_type:20s}: {count:3d} txns, Net: ${float(total):+,.2f}")

# Check for duplicate forex transactions
print("\n=== CHECKING FOR DUPLICATE FOREX TRANSACTIONS ===\n")
from sqlalchemy import text

duplicates = db.execute(
    text("""
    SELECT
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
).fetchall()

if duplicates:
    print(f"Found {len(duplicates)} duplicate forex transaction patterns:")
    for account_id, symbol, date, amount, count in duplicates[:15]:
        print(f"  {date}: {symbol} {float(amount):+.2f} appears {count} times")
else:
    print("No duplicate forex transactions found")

# Show recent USD forex transactions to understand the pattern
print("\n=== RECENT USD FOREX CONVERSIONS (last 15) ===\n")
recent_usd = (
    db.query(Transaction, Asset)
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type == "Forex Conversion", Asset.symbol == "USD")
    .order_by(Transaction.date.desc())
    .limit(15)
    .all()
)

for txn, asset in recent_usd:
    print(
        f"{txn.date}: USD {float(txn.amount):+10.2f} - {txn.notes[:70] if txn.notes else 'No notes'}"
    )

db.close()
