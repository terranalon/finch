"""Check current state before re-importing trades with Trade Settlement logic."""

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import Transaction

db = SessionLocal()

print("=== CURRENT TRANSACTION STATE ===\n")

# Check for any existing Trade Settlement transactions
trade_settlements = db.query(Transaction).filter(Transaction.type == "Trade Settlement").count()

print(f"Existing Trade Settlement transactions: {trade_settlements}")
print()

# Check Buy/Sell transaction counts
buy_sell_counts = (
    db.query(Transaction.type, func.count(Transaction.id).label("count"))
    .filter(Transaction.type.in_(["Buy", "Sell"]))
    .group_by(Transaction.type)
    .all()
)

print("=== BUY/SELL TRANSACTIONS ===")
for txn_type, count in buy_sell_counts:
    print(f"{txn_type}: {count}")
print()

# Check if re-importing will create duplicates
print("=== DUPLICATE DETECTION CHECK ===")
print("Re-importing will:")
print("1. Skip duplicate Buy/Sell transactions (already have them)")
print("2. Create NEW Trade Settlement transactions for each trade")
print()

print("Expected result after re-import:")
total_trades = sum(count for _, count in buy_sell_counts)
print(f"- Same {total_trades} Buy/Sell transactions (duplicates skipped)")
print(f"- NEW {total_trades} Trade Settlement transactions created")
print()

# Show sample of what will be created
print("=== SAMPLE TRADES THAT NEED SETTLEMENTS ===")
sample_trades = db.execute(
    text("""
    SELECT
        t.id,
        t.date,
        t.type,
        a.symbol,
        a.currency,
        t.quantity,
        t.price_per_unit,
        t.fees,
        (t.quantity * t.price_per_unit + t.fees) as estimated_cash_impact
    FROM transactions t
    JOIN holdings h ON t.holding_id = h.id
    JOIN assets a ON h.asset_id = a.id
    WHERE t.type IN ('Buy', 'Sell')
    AND a.asset_class != 'Cash'
    ORDER BY t.date DESC
    LIMIT 10
""")
).fetchall()

print("Recent trades (last 10):\n")
for txn_id, date, txn_type, symbol, currency, qty, price, fees, est_cash in sample_trades:
    sign = "-" if txn_type == "Buy" else "+"
    cash_impact = float(qty) * float(price) + float(fees)
    print(f"{date} {txn_type:4s} {symbol:10s} {currency} {sign}${cash_impact:,.2f} estimated")

print("\n=== READY TO RE-IMPORT ===")
print('Run: docker-compose exec backend python -c "')
print("from app.services.ibkr_flex_import_service import IBKRFlexImportService")
print("from app.database import SessionLocal")
print("db = SessionLocal()")
print("result = IBKRFlexImportService.import_full_report(db, 7)")
print("print(result)")
print('db.close()"')

db.close()
