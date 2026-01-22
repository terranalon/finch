"""Backfill Trade Settlement transactions for existing Buy/Sell transactions.

This script creates Trade Settlement cash transactions for all existing Buy/Sell
transactions that don't already have corresponding settlements.
"""

import logging
from decimal import Decimal

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction
from app.services.ibkr_flex_client import IBKRFlexClient
from app.services.ibkr_parser import IBKRParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SessionLocal()

# Get account credentials
account_id = 7
from app.models import Account

account = db.query(Account).filter(Account.id == account_id).first()
flex_token = account.meta_data["ibkr"]["flex_token"]
flex_query_id = account.meta_data["ibkr"]["flex_query_id"]

print("=== BACKFILLING TRADE SETTLEMENTS ===\n")

# Fetch fresh data from IBKR
print("Fetching IBKR data...")
xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)
root = IBKRParser.parse_xml(xml_data)

# Extract trades with netCash
print("Extracting trades...")
trades = IBKRParser.extract_transactions(root)
print(f"Found {len(trades)} trades from IBKR\n")

created_count = 0
skipped_count = 0
error_count = 0

for trade_data in trades:
    try:
        # Skip forex pairs
        symbol = trade_data["symbol"]
        if "." in symbol:
            currency_codes = {"USD", "CAD", "ILS", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD"}
            parts = symbol.split(".")
            if len(parts) == 2 and parts[0] in currency_codes and parts[1] in currency_codes:
                continue

        # Get the netCash value
        net_cash = trade_data.get("net_cash")
        if not net_cash or net_cash == 0:
            logger.debug(f"Skipping {trade_data['symbol']} - no netCash")
            skipped_count += 1
            continue

        # Find the stock asset and holding (to verify this trade exists in our DB)
        asset = db.query(Asset).filter(Asset.symbol == trade_data["symbol"]).first()

        if not asset:
            logger.warning(f"Asset not found: {trade_data['symbol']}")
            skipped_count += 1
            continue

        # Find or create cash asset
        trade_currency = trade_data.get("currency", "USD")
        cash_asset = (
            db.query(Asset)
            .filter(Asset.symbol == trade_currency, Asset.asset_class == "Cash")
            .first()
        )

        if not cash_asset:
            cash_asset = Asset(
                symbol=trade_currency,
                name=f"{trade_currency} Cash",
                asset_class="Cash",
                currency=trade_currency,
            )
            db.add(cash_asset)
            db.flush()
            logger.info(f"Created cash asset: {trade_currency}")

        # Find or create cash holding
        cash_holding = (
            db.query(Holding)
            .filter(Holding.account_id == account_id, Holding.asset_id == cash_asset.id)
            .first()
        )

        if not cash_holding:
            cash_holding = Holding(
                account_id=account_id,
                asset_id=cash_asset.id,
                quantity=Decimal("0"),
                cost_basis=Decimal("0"),
                is_active=True,
            )
            db.add(cash_holding)
            db.flush()
            logger.info(f"Created cash holding for {trade_currency}")

        # Check if Trade Settlement already exists
        existing_settlement = (
            db.query(Transaction)
            .filter(
                Transaction.holding_id == cash_holding.id,
                Transaction.date == trade_data["trade_date"],
                Transaction.type == "Trade Settlement",
                Transaction.amount == net_cash,
            )
            .first()
        )

        if existing_settlement:
            logger.debug(
                f"Settlement already exists for {trade_data['symbol']} on {trade_data['trade_date']}"
            )
            skipped_count += 1
            continue

        # Create Trade Settlement transaction
        settlement = Transaction(
            holding_id=cash_holding.id,
            date=trade_data["trade_date"],
            type="Trade Settlement",
            amount=net_cash,
            notes=f"Cash settlement for {trade_data['symbol']} {trade_data['transaction_type']}",
        )
        db.add(settlement)
        created_count += 1

        if created_count % 10 == 0:
            logger.info(f"Created {created_count} settlements...")

    except Exception as e:
        logger.error(f"Error processing trade {trade_data.get('symbol')}: {str(e)}")
        error_count += 1
        continue

# Commit all changes
db.commit()

print("\n=== BACKFILL COMPLETE ===")
print(f"Created: {created_count}")
print(f"Skipped: {skipped_count}")
print(f"Errors: {error_count}")

# Verify final count
final_count = db.query(Transaction).filter(Transaction.type == "Trade Settlement").count()
print(f"\nTotal Trade Settlement transactions in DB: {final_count}")

db.close()
