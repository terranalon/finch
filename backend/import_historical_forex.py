"""Import Forex Conversions from historical XML file."""

import xml.etree.ElementTree as ET

from app.database import SessionLocal
from app.services.ibkr_import_service import IBKRImportService
from app.services.ibkr_parser import IBKRParser

db = SessionLocal()
account_id = 7

print("=== IMPORTING HISTORICAL FOREX CONVERSIONS ===\n")

# Read historical XML
xml_path = "/app/data/Portfolio_Tracker_Query.xml"
print(f"Reading {xml_path}...")
with open(xml_path) as f:
    xml_data = f.read()

root = ET.fromstring(xml_data)

# Extract forex conversions
print("Extracting forex conversions...")
forex_data = IBKRParser.extract_forex_transactions(root)
print(f"Found {len(forex_data)} forex conversions (STK: transactions filtered out)\n")

# Import them
print("Importing...")
stats = IBKRImportService._import_forex_transactions(db, account_id, forex_data)

print("\n=== IMPORT RESULTS ===")
print(f"Total: {stats['total']}")
print(f"Imported: {stats['imported']}")
print(f"Duplicates skipped: {stats['duplicates_skipped']}")
print(f"Errors: {len(stats['errors'])}")

if stats["errors"]:
    print("\nErrors:")
    for error in stats["errors"][:5]:
        print(f"  - {error}")

db.close()
