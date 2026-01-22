"""Backfill Trade Settlement transactions from historical XML file."""

import logging
import xml.etree.ElementTree as ET
from decimal import Decimal

from app.database import SessionLocal
from app.models import Asset, Holding, Transaction
from app.services.ibkr_parser import IBKRParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SessionLocal()
account_id = 7

print("=== BACKFILLING FROM HISTORICAL XML ===\n")

# Read historical XML
xml_path = "/app/data/Portfolio_Tracker_Query.xml"
print(f"Reading {xml_path}...")
with open(xml_path) as f:
    xml_data = f.read()

root = ET.fromstring(xml_data)

# Extract trades
print("Extracting trades...")
trades = IBKRParser.extract_transactions(root)
print(f"Found {len(trades)} trades\n")

created_count = 0
skipped_count = 0

for trade_data in trades:
    try:
        # Skip forex pairs
        symbol = trade_data["symbol"]
        if "." in symbol:
            currency_codes = {"USD", "CAD", "ILS", "EUR", "GBP", "JPY"}
            parts = symbol.split(".")
            if len(parts) == 2 and parts[0] in currency_codes and parts[1] in currency_codes:
                continue

        net_cash = trade_data.get("net_cash")
        if not net_cash or net_cash == 0:
            logger.debug(f"Skipping {symbol} - no netCash")
            skipped_count += 1
            continue

        trade_currency = trade_data.get("currency", "USD")

        # Find or create cash asset
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

        # Check if settlement already exists
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.holding_id == cash_holding.id,
                Transaction.date == trade_data["trade_date"],
                Transaction.type == "Trade Settlement",
                Transaction.amount == net_cash,
            )
            .first()
        )

        if existing:
            logger.debug(f"Settlement exists for {symbol} on {trade_data['trade_date']}")
            skipped_count += 1
            continue

        # Create settlement
        settlement = Transaction(
            holding_id=cash_holding.id,
            date=trade_data["trade_date"],
            type="Trade Settlement",
            amount=net_cash,
            notes=f"Cash settlement for {symbol} {trade_data['transaction_type']}",
        )
        db.add(settlement)
        created_count += 1

        if created_count % 10 == 0:
            logger.info(f"Created {created_count} settlements...")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        continue

db.commit()

print("\n=== BACKFILL COMPLETE ===")
print(f"Created: {created_count}")
print(f"Skipped: {skipped_count}")

final_count = db.query(Transaction).filter(Transaction.type == "Trade Settlement").count()
print(f"\nTotal Trade Settlements: {final_count}")

db.close()
