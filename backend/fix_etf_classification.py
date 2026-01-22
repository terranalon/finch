#!/usr/bin/env python3
"""Fix ETF classification for existing assets.

This script identifies assets classified as "Stock" that are actually ETFs or
MutualFunds and updates their asset_class field.

Usage:
    python fix_etf_classification.py              # Preview changes (dry run)
    python fix_etf_classification.py --apply      # Apply changes to database
    python fix_etf_classification.py --verbose    # Show detailed output
"""

import argparse
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Asset
from app.services.asset_type_detector import AssetTypeDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fix ETF classification for existing assets")

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry run)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def fix_etf_classification(dry_run: bool = True, verbose: bool = False) -> dict[str, int]:
    """Detect and fix ETF/MutualFund misclassifications."""
    db = SessionLocal()

    try:
        # Find all Stock assets that might be ETFs or MutualFunds
        query = select(Asset).where(Asset.asset_class == "Stock")
        stock_assets = db.execute(query).scalars().all()

        stats = {
            "total": len(stock_assets),
            "reclassified": 0,
            "unchanged": 0,
            "not_found": 0,
            "errors": 0,
        }
        reclassified: list[tuple[str, str, str]] = []  # (symbol, old_class, new_class)

        logger.info(f"Checking {stats['total']} Stock assets for misclassification...")

        for asset in stock_assets:
            if verbose:
                logger.debug(f"Checking {asset.symbol}...")

            result = AssetTypeDetector.detect_asset_type(asset.symbol)

            if result.source == "not_found":
                stats["not_found"] += 1
                if verbose:
                    logger.debug(f"{asset.symbol}: not found in Yahoo Finance")
                continue

            if result.source == "error":
                stats["errors"] += 1
                if verbose:
                    logger.debug(f"{asset.symbol}: error - {result.error}")
                continue

            if result.detected_type and result.detected_type != "Stock":
                old_class = asset.asset_class
                new_class = result.detected_type
                reclassified.append((asset.symbol, old_class, new_class))

                if verbose:
                    logger.debug(f"{asset.symbol}: {old_class} -> {new_class}")

                if not dry_run:
                    asset.asset_class = new_class
                    meta = asset.meta_data or {}
                    meta["asset_class_reclassified"] = True
                    meta["asset_class_source"] = "yfinance_detection"
                    asset.meta_data = meta

                stats["reclassified"] += 1
            else:
                stats["unchanged"] += 1
                if verbose:
                    logger.debug(f"{asset.symbol}: confirmed as Stock")

        if not dry_run and stats["reclassified"] > 0:
            db.commit()
            logger.info("Changes committed to database.")

        _print_summary(stats, reclassified, dry_run)

        return stats

    finally:
        db.close()


def _print_summary(
    stats: dict[str, int],
    reclassified: list[tuple[str, str, str]],
    dry_run: bool,
) -> None:
    """Print summary of classification results."""
    prefix = "DRY RUN - " if dry_run else ""
    logger.info(f"{prefix}ETF CLASSIFICATION FIX COMPLETE")
    logger.info(f"Total Stock assets checked: {stats['total']}")
    logger.info(f"Reclassified: {stats['reclassified']}")
    logger.info(f"Unchanged (confirmed Stock): {stats['unchanged']}")
    logger.info(f"Not found in Yahoo Finance: {stats['not_found']}")
    logger.info(f"Errors: {stats['errors']}")

    if reclassified:
        logger.info("Reclassified assets:")
        for symbol, old_class, new_class in reclassified[:30]:
            logger.info(f"  {symbol}: {old_class} -> {new_class}")
        if len(reclassified) > 30:
            logger.info(f"  ... and {len(reclassified) - 30} more")

    if dry_run and stats["reclassified"] > 0:
        logger.info("Run with --apply to apply these changes to the database.")


def main() -> None:
    """Run ETF classification fix."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    mode = "DRY RUN (preview only)" if not args.apply else "LIVE (will update database)"
    logger.info(f"ETF CLASSIFICATION FIX - Mode: {mode}")

    fix_etf_classification(dry_run=not args.apply, verbose=args.verbose)


if __name__ == "__main__":
    main()
