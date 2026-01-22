"""Check if all Buy/Sell transactions have corresponding Trade Settlements."""

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction

db = SessionLocal()

# Count Buy/Sell transactions
buy_sell_count = (
    db.query(func.count(Transaction.id))
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Transaction.type.in_(["Buy", "Sell"]), Asset.asset_class != "Cash")
    .scalar()
)

# Count Trade Settlement transactions
trade_settlement_count = (
    db.query(func.count(Transaction.id)).filter(Transaction.type == "Trade Settlement").scalar()
)

print(f"Buy/Sell transactions: {buy_sell_count}")
print(f"Trade Settlement transactions: {trade_settlement_count}")
print(f"Missing settlements: {buy_sell_count - trade_settlement_count}\n")

# Get all stock trades and check for settlements
stock_trades = db.execute(
    text("""
    SELECT
        t.id as trade_id,
        t.date as trade_date,
        t.type as trade_type,
        a.symbol,
        a.currency,
        t.quantity,
        t.price_per_unit,
        t.fees
    FROM transactions t
    JOIN holdings h ON t.holding_id = h.id
    JOIN assets a ON h.asset_id = a.id
    WHERE t.type IN ('Buy', 'Sell')
    AND a.asset_class != 'Cash'
    ORDER BY t.date
""")
).fetchall()

print("Trades without settlements:\n")
missing_count = 0
for trade_id, trade_date, trade_type, symbol, currency, qty, price, fees in stock_trades:
    # Check if there's a matching Trade Settlement
    settlement = db.execute(
        text("""
        SELECT t2.id, t2.amount
        FROM transactions t2
        JOIN holdings h2 ON t2.holding_id = h2.id
        JOIN assets a2 ON h2.asset_id = a2.id
        WHERE t2.type = 'Trade Settlement'
        AND a2.symbol = :currency
        AND t2.date = :trade_date
    """),
        {"currency": currency, "trade_date": trade_date},
    ).fetchone()

    if not settlement:
        estimated_cash = float(qty) * float(price) + float(fees)
        print(
            f"{trade_date} {trade_type:4s} {symbol:10s} {currency} est_cash=${estimated_cash:,.2f}"
        )
        missing_count += 1

print(f"\nTotal missing settlements: {missing_count}")

db.close()
