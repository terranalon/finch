"""Check raw BABY ledger entries from Kraken."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from datetime import UTC, datetime
from decimal import Decimal

from app.database import SessionLocal
from app.models import Account
from app.services.kraken_client import KrakenClient, KrakenCredentials
from app.services.kraken_constants import normalize_kraken_asset

KRAKEN_ACCOUNT_ID = 23
db = SessionLocal()

try:
    account = db.query(Account).filter(Account.id == KRAKEN_ACCOUNT_ID).first()
    creds = account.meta_data["kraken"]
    client = KrakenClient(KrakenCredentials(api_key=creds["api_key"], api_secret=creds["api_secret"]))

    # Get all ledger entries
    all_entries = []
    offset = 0
    while True:
        ledgers, total = client.get_ledgers(offset=offset)
        if not ledgers:
            break
        all_entries.extend(ledgers)
        offset += 50
        if offset >= total:
            break

    # Find BABY entries
    baby_entries = []
    for e in all_entries:
        asset = normalize_kraken_asset(e.get("asset", ""))
        if asset == "BABY":
            baby_entries.append(e)

    print(f"Found {len(baby_entries)} BABY entries in raw ledger")
    print("\nAll BABY ledger entries:")

    total = Decimal("0")
    for e in sorted(baby_entries, key=lambda x: x.get("time", 0)):
        entry_time = e.get("time")
        entry_date = datetime.fromtimestamp(entry_time, tz=UTC).strftime("%Y-%m-%d %H:%M") if entry_time else "?"
        entry_type = e.get("type", "?")
        amount = Decimal(str(e.get("amount", "0")))
        fee = Decimal(str(e.get("fee", "0")))
        balance = e.get("balance", "?")
        refid = e.get("refid", "?")[:20]

        net = amount - fee
        total += net
        print(f"  {entry_date} | {entry_type:12} | amt={amount:>12.5f} | fee={fee:>8.5f} | bal={balance:>12} | running={total:>12.5f} | {refid}")

    print(f"\nFinal calculated from raw: {total}")

    # Get API balance
    api_balances = client.get_balance()
    print(f"API balance: {api_balances.get('BABY', 0)}")

finally:
    db.close()
