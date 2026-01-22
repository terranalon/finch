#!/usr/bin/env python3
"""Standalone script to backfill historical snapshots.

This script generates historical portfolio snapshots by reconstructing
holdings from transaction history. Useful for:
- Creating historical performance charts
- Filling gaps in snapshot data
- Generating snapshots retroactively

Usage:
    python backfill_historical_snapshots.py --account-id 7 --start 2024-05-01 --end 2026-01-10
    python backfill_historical_snapshots.py --account-id 7 --days 365
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Account
from app.services.snapshot_service import SnapshotService


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill historical portfolio snapshots using transaction reconstruction"
    )

    parser.add_argument("--account-id", type=int, required=True, help="Account ID to backfill")

    # Date range options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--start", type=str, help="Start date (YYYY-MM-DD). Requires --end")
    date_group.add_argument(
        "--days", type=int, help="Number of days to backfill from today (e.g., 365 for 1 year)"
    )

    parser.add_argument(
        "--end", type=str, help="End date (YYYY-MM-DD). Defaults to today. Only used with --start"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually creating snapshots",
    )

    return parser.parse_args()


def validate_date_range(start_date: date, end_date: date) -> None:
    """Validate date range is reasonable."""
    if start_date > end_date:
        print("❌ ERROR: Start date must be before end date")
        sys.exit(1)

    total_days = (end_date - start_date).days + 1

    if total_days > 730:  # 2 years max
        print(f"❌ ERROR: Date range too large ({total_days} days)")
        print("   Maximum is 730 days (2 years)")
        print("   Tip: Run multiple smaller backfills instead")
        sys.exit(1)

    if total_days > 365:
        print(f"⚠️  WARNING: Large date range ({total_days} days)")
        print("   This may take a while...")
        print()


def main():
    """Run historical snapshot backfill."""
    args = parse_args()

    # Parse dates
    if args.days:
        # Backfill from N days ago to today
        end_date = date.today()
        start_date = end_date - timedelta(days=args.days - 1)
    else:
        # Parse start/end dates
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end) if args.end else date.today()

    # Validate
    validate_date_range(start_date, end_date)

    # Connect to database
    db = SessionLocal()

    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == args.account_id).first()

        if not account:
            print(f"❌ ERROR: Account {args.account_id} not found")
            sys.exit(1)

        # Print summary
        total_days = (end_date - start_date).days + 1

        print("=" * 80)
        print("HISTORICAL SNAPSHOT BACKFILL")
        print("=" * 80)
        print()
        print(f"Account:     {account.name} (ID: {account.id})")
        print(f"Date Range:  {start_date} to {end_date}")
        print(f"Total Days:  {total_days}")
        print(
            f"Mode:        {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will create snapshots)'}"
        )
        print()
        print("=" * 80)
        print()

        if args.dry_run:
            print("✅ Dry run complete - no snapshots created")
            return

        # Confirm for large backfills
        if total_days > 180:
            response = input(
                f"Create {total_days} snapshots? This may take several minutes. [y/N]: "
            )
            if response.lower() != "y":
                print("Cancelled")
                return
            print()

        # Run backfill
        print("Starting backfill...")
        print()

        stats = SnapshotService.backfill_historical_snapshots(
            db, args.account_id, start_date, end_date
        )

        # Print results
        print()
        print("=" * 80)
        print("BACKFILL COMPLETE")
        print("=" * 80)
        print()
        print(f"✅ Created:  {stats['created']} snapshots")
        print(f"⏭️  Skipped:  {stats['skipped']} snapshots (already existed)")
        print(f"❌ Errors:   {len(stats['errors'])} snapshots")
        print()

        if stats["errors"]:
            print("Errors encountered:")
            for error in stats["errors"][:10]:  # Show first 10
                print(f"  - {error['date']}: {error['error']}")

            if len(stats["errors"]) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more")
            print()

        # Success rate
        total_attempted = stats["created"] + len(stats["errors"])
        if total_attempted > 0:
            success_rate = (stats["created"] / total_attempted) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
