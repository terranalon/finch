"""Check raw STRK ledger entries from Kraken."""
import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

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

    # Find STRK entries
    strk_entries = []
    for e in all_entries:
        asset = normalize_kraken_asset(e.get("asset", ""))
        if asset == "STRK":
            strk_entries.append(e)

    print(f"Found {len(strk_entries)} STRK entries in raw ledger")
    print("\nAll STRK ledger entries:")

    from datetime import UTC, datetime
    total = Decimal("0")
    for e in sorted(strk_entries, key=lambda x: x.get("time", 0)):
        entry_time = e.get("time")
        entry_date = datetime.fromtimestamp(entry_time, tz=UTC).strftime("%Y-%m-%d %H:%M") if entry_time else "?"
        entry_type = e.get("type", "?")
        amount = Decimal(str(e.get("amount", "0")))
        fee = Decimal(str(e.get("fee", "0")))
        balance = e.get("balance", "?")
        refid = e.get("refid", "?")

        net = amount - fee
        total += net
        print(f"  {entry_date} | {entry_type:12} | amt={amount:>15.8f} | fee={fee:>8.4f} | bal={balance:>15} | running={total:>15.8f} | {refid[:20]}")

    print(f"\nFinal calculated from raw: {total}")

finally:
    db.close()
