"""Check what CashTransactions IBKR provides."""

from app.database import SessionLocal
from app.models import Account
from app.services.ibkr_flex_client import IBKRFlexClient
from app.services.ibkr_parser import IBKRParser

db = SessionLocal()
account = db.query(Account).filter(Account.id == 7).first()

# Get credentials
flex_token = account.meta_data["ibkr"]["flex_token"]
flex_query_id = account.meta_data["ibkr"]["flex_query_id"]

print("Fetching IBKR Flex Query data...\n")
xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)

print("Parsing XML...\n")
root = IBKRParser.parse_xml(xml_data)

print("=== CASH TRANSACTION TYPES ===\n")
cash_types = IBKRParser.get_cash_transaction_types(root)
for txn_type, count in sorted(cash_types.items(), key=lambda x: -x[1]):
    print(f"{txn_type:30s}: {count} transactions")

print("\n=== SAMPLE CASH TRANSACTIONS (first 10) ===\n")
for stmt in root.findall(".//FlexStatement"):
    for i, cash_txn in enumerate(stmt.findall(".//CashTransaction")):
        if i >= 10:
            break
        txn_type = cash_txn.get("type", "")
        symbol = cash_txn.get("symbol", "N/A")
        amount = cash_txn.get("amount", "0")
        currency = cash_txn.get("currency", "USD")
        description = cash_txn.get("description", "")
        date = cash_txn.get("dateTime", "")[:10]

        print(f"{date} {txn_type:25s} {symbol:10s} {currency} {amount:>12s}")
        if description:
            print(f"         {description[:70]}")

print("\n=== KEY QUESTION ===")
print("Do CashTransactions include stock purchase/sale settlements?")
print("If NO, we need to import Trade.netCash as cash transactions.")

db.close()
