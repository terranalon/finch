#!/usr/bin/env python3
"""Standalone script to update asset names from Yahoo Finance.

This script fetches company names from Yahoo Finance for assets where
the name field equals the symbol (or is empty). Useful for:
- Initial data cleanup after bulk imports
- Fixing assets imported without proper names
- Updating names after ticker symbol changes

Usage:
    python update_asset_names.py                    # Update assets where name == symbol
    python update_asset_names.py --force            # Update ALL asset names
    python update_asset_names.py --dry-run          # Preview changes without updating
    python update_asset_names.py --asset-class ETF  # Update only ETFs
"""

import argparse
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.asset_metadata_service import AssetMetadataService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update asset names from Yahoo Finance")

    parser.add_argument(
        "--force",
        action="store_true",
        help="Update all asset names, even if they already have names",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually updating",
    )

    parser.add_argument(
        "--asset-class",
        type=str,
        help="Filter by asset class (e.g., Stock, ETF, Crypto)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main():
    """Run asset name update."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Connect to database
    db = SessionLocal()

    try:
        # Print summary header
        print("=" * 80)
        print("ASSET NAME UPDATE")
        print("=" * 80)
        print()
        print(
            f"Mode:        {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will update database)'}"
        )
        print(
            f"Force:       {'Yes (update all)' if args.force else 'No (only where name == symbol)'}"
        )
        if args.asset_class:
            print(f"Asset Class: {args.asset_class}")
        print()
        print("=" * 80)
        print()

        # Run update
        stats = AssetMetadataService.update_all_asset_names(
            db, force=args.force, dry_run=args.dry_run, asset_class=args.asset_class
        )

        # Print results
        print()
        print("=" * 80)
        print("UPDATE COMPLETE")
        print("=" * 80)
        print()
        print(f"Total assets:     {stats['total']}")
        print(f"Updated:          {stats['updated']}")
        print(f"Skipped:          {stats['skipped']}")
        print(f"Not found:        {stats['not_found']}")
        print(f"Errors:           {stats['errors']}")
        print()

        if stats["updated_symbols"]:
            print("Updated names:")
            for item in stats["updated_symbols"][:20]:
                print(f"  - {item}")
            if len(stats["updated_symbols"]) > 20:
                print(f"  ... and {len(stats['updated_symbols']) - 20} more")
            print()

        if stats["not_found_symbols"]:
            print("Symbols not found in Yahoo Finance:")
            for symbol in stats["not_found_symbols"][:10]:
                print(f"  - {symbol}")
            if len(stats["not_found_symbols"]) > 10:
                print(f"  ... and {len(stats['not_found_symbols']) - 10} more")
            print()

        if stats["error_symbols"]:
            print("Errors:")
            for error in stats["error_symbols"][:10]:
                print(f"  - {error}")
            if len(stats["error_symbols"]) > 10:
                print(f"  ... and {len(stats['error_symbols']) - 10} more")
            print()

        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
