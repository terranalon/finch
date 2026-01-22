"""Test Kraken import directly."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from app.database import SessionLocal
from app.models import Account
from app.services.crypto_import_service import CryptoImportService
from app.services.kraken_client import KrakenClient, KrakenCredentials

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    # Get credentials
    account = db.query(Account).filter(Account.id == KRAKEN_ACCOUNT_ID).first()
    creds = account.meta_data["kraken"]
    api_key, api_secret = creds["api_key"], creds["api_secret"]

    # Fetch data
    print("Fetching data from Kraken...")
    client = KrakenClient(KrakenCredentials(api_key=api_key, api_secret=api_secret))
    data = client.fetch_all_data()

    print("\nData fetched:")
    print(f"  Transactions: {len(data.transactions)}")
    print(f"  Cash transactions: {len(data.cash_transactions)}")
    print(f"  Dividends: {len(data.dividends)}")
    print(f"  Positions: {len(data.positions)}")

    # Import
    print("\nImporting...")
    import_service = CryptoImportService(db)
    result = import_service.import_data(KRAKEN_ACCOUNT_ID, data, "Kraken")

    print("\nImport result:")
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

except Exception:
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
