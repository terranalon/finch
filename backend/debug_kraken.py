"""Debug Kraken import issues."""

import sys

sys.path.insert(0, "/Users/alonsamocha/PycharmProjects/portofolio_tracker/backend")

from collections import defaultdict
from decimal import Decimal

from app.database import SessionLocal
from app.models import Holding, Transaction
from app.services.brokers.kraken.client import KrakenClient, KrakenCredentials
from app.services.brokers.kraken.constants import normalize_kraken_asset

KRAKEN_ACCOUNT_ID = 23


def get_kraken_credentials(db):
    from app.models import Account
    account = db.query(Account).filter(Account.id == KRAKEN_ACCOUNT_ID).first()
    if account and account.meta_data and "kraken" in account.meta_data:
        creds = account.meta_data["kraken"]
        return creds.get("api_key"), creds.get("api_secret")
    return None, None


def main():
    db = SessionLocal()
    try:
        api_key, api_secret = get_kraken_credentials(db)
        if not api_key:
            print("No credentials found")
            return

        client = KrakenClient(KrakenCredentials(api_key=api_key, api_secret=api_secret))

        # Get ALL raw ledger entries
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

        print(f"Total raw ledger entries: {len(all_entries)}")

        # Calculate balances from raw entries (exactly as Kraken does)
        balances = defaultdict(Decimal)
        by_type = defaultdict(int)

        for entry in all_entries:
            asset = normalize_kraken_asset(entry.get("asset", ""))
            amount = Decimal(str(entry.get("amount", "0")))
            fee = Decimal(str(entry.get("fee", "0")))
            entry_type = entry.get("type", "")

            by_type[entry_type] += 1

            # Net impact = amount - fee
            net = amount - fee
            balances[asset] += net

        print("\n=== Entry counts by type ===")
        for t, count in sorted(by_type.items()):
            print(f"  {t}: {count}")

        print("\n=== Calculated balances from ALL entries ===")
        api_balances = client.get_balance()

        print(f"{'Asset':<10} {'Calculated':>15} {'API':>15} {'Diff':>12}")
        print("-" * 55)

        all_assets = set(balances.keys()) | set(api_balances.keys())
        for asset in sorted(all_assets):
            calc = balances.get(asset, Decimal("0"))
            api = api_balances.get(asset, Decimal("0"))
            diff = api - calc
            if calc != 0 or api != 0:
                status = "✓" if abs(diff) < Decimal("0.0001") else "✗"
                print(f"{asset:<10} {calc:>15.8f} {api:>15.8f} {diff:>12.8f} {status}")

        # Check what we're currently handling vs not handling
        print("\n=== Entry types we handle ===")
        print("  deposit, withdrawal, trade, staking")
        print("\n=== Entry types we DON'T handle ===")
        unhandled = set(by_type.keys()) - {"deposit", "withdrawal", "trade", "staking"}
        for t in unhandled:
            print(f"  {t}: {by_type[t]} entries")

        # Show sample transfer entries
        transfers = [e for e in all_entries if e.get("type") == "transfer"]
        if transfers:
            print("\n=== Sample TRANSFER entries (first 10) ===")
            for entry in transfers[:10]:
                asset = entry.get("asset", "")
                norm_asset = normalize_kraken_asset(asset)
                amount = entry.get("amount", "0")
                subtype = entry.get("subtype", "")
                print(f"  {asset} -> {norm_asset}: {amount} ({subtype})")

        # Check database state
        print("\n=== Current database holdings ===")
        holdings = db.query(Holding).filter(Holding.account_id == KRAKEN_ACCOUNT_ID).all()
        for h in holdings:
            if h.quantity != 0:
                txn_count = db.query(Transaction).filter(Transaction.holding_id == h.id).count()
                print(f"  {h.asset.symbol}: qty={h.quantity}, txns={txn_count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
