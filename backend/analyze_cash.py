from datetime import date

from app.database import SessionLocal
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService

db = SessionLocal()

# Run reconstruction
holdings = PortfolioReconstructionService.reconstruct_holdings(
    db, 7, date.today(), apply_ticker_changes=True
)

print("=== RECONSTRUCTED CASH HOLDINGS ===\n")
for h in holdings:
    if h["asset_class"] == "Cash":
        print(f"{h['symbol']:4s}: {float(h['quantity']):+12.2f} {h['currency']}")

print("\n=== WHAT IBKR REPORTS ===")
print("USD:  +10,098.94")
print("CAD:      +7.64")
print("ILS:       +0.00")

print("\n=== CASH TRANSACTION SOURCES ===")
from sqlalchemy import func

from app.models import Asset, Holding, Transaction

# Get cash impact by transaction type for USD
usd_sources = (
    db.query(Transaction.type, func.sum(Transaction.amount).label("total"))
    .join(Holding, Transaction.holding_id == Holding.id)
    .join(Asset, Holding.asset_id == Asset.id)
    .filter(Asset.symbol == "USD", Asset.asset_class == "Cash")
    .group_by(Transaction.type)
    .all()
)

print("\nUSD Cash Sources:")
usd_total = 0
for txn_type, total in usd_sources:
    if total:
        print(f"  {txn_type:20s}: ${float(total):+,.2f}")
        usd_total += float(total)
print(f"  {'TOTAL':20s}: ${usd_total:+,.2f}")

# Now let's see what Buy/Sell transactions exist
print("\n=== BUY/SELL IMPACT (not currently in cash transactions) ===")
from sqlalchemy import text

buy_sell_impact = db.execute(
    text("""
    SELECT
        t.type,
        SUM((t.quantity * t.price_per_unit) + t.fees) as total_cost
    FROM transactions t
    JOIN holdings h ON t.holding_id = h.id
    JOIN assets a ON h.asset_id = a.id
    WHERE t.type IN ('Buy', 'Sell')
    AND a.asset_class != 'Cash'
    AND a.currency = 'USD'
    GROUP BY t.type
""")
).fetchall()

print("\nUSD Buy/Sell (stock transactions, not cash):")
for txn_type, total_cost in buy_sell_impact:
    sign = "-" if txn_type == "Buy" else "+"
    print(f"  {txn_type:20s}: {sign}${float(total_cost):,.2f}")

# Show the math
print("\n=== UNDERSTANDING THE DISCREPANCY ===")
print(f"Cash transaction sources: ${usd_total:,.2f}")
print(
    f"Reconstruction shows:     ${float([h for h in holdings if h.get('symbol') == 'USD'][0]['quantity']):,.2f}"
)
print("IBKR reports:             $10,098.94")
print("\nThe reconstruction is applying Buy/Sell deductions on top of forex conversions")
print("But IBKR's forex conversions ALREADY account for stock purchases!")

db.close()
