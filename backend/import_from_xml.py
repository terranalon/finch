#!/usr/bin/env python3
"""Standalone script to import IBKR data from XML file."""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Import IBKR data from XML file."""
    # Configuration
    account_id = 7  # Interactive Brokers account
    xml_path = Path(__file__).parent / "data" / "Portfolio_Tracker_Query.xml"

    if not xml_path.exists():
        logger.error(f"XML file not found: {xml_path}")
        sys.exit(1)

    logger.info(f"Reading XML file: {xml_path}")
    with open(xml_path) as f:
        xml_data = f.read()

    logger.info(f"Loaded XML file: {len(xml_data)} bytes")

    # Parse XML
    logger.info("Parsing XML...")
    root = IBKRParser.parse_xml(xml_data)
    if root is None:
        logger.error("Failed to parse XML")
        sys.exit(1)

    # Extract data
    logger.info("Extracting data from XML...")
    positions_data = IBKRParser.extract_positions(root)
    transactions_data = IBKRParser.extract_transactions(root)
    dividends_data = IBKRParser.extract_dividends(root)
    transfers_data = IBKRParser.extract_transfers(root)
    forex_data = IBKRParser.extract_forex_transactions(root)
    cash_data = IBKRParser.extract_cash_balances(root)

    logger.info(
        f"Extracted: {len(positions_data)} positions, "
        f"{len(transactions_data)} transactions, "
        f"{len(dividends_data)} dividends, "
        f"{len(transfers_data)} transfers, "
        f"{len(forex_data)} forex, "
        f"{len(cash_data)} cash"
    )

    # Import to database
    db = SessionLocal()
    try:
        logger.info("Importing cash balances...")
        cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
        logger.info(f"Cash stats: {cash_stats}")

        logger.info("Importing transactions...")
        txn_stats = IBKRImportService._import_transactions(db, account_id, transactions_data)
        logger.info(f"Transaction stats: {txn_stats}")

        logger.info("Importing dividends...")
        div_stats = IBKRImportService._import_dividends(db, account_id, dividends_data)
        logger.info(f"Dividend stats: {div_stats}")

        logger.info("Importing transfers...")
        transfer_stats = IBKRImportService._import_transfers(db, account_id, transfers_data)
        logger.info(f"Transfer stats: {transfer_stats}")

        logger.info("Importing forex...")
        forex_stats = IBKRImportService._import_forex_transactions(db, account_id, forex_data)
        logger.info(f"Forex stats: {forex_stats}")

        logger.info("Reconstructing holdings from transactions...")
        reconstruction_stats = reconstruct_and_update_holdings(db, account_id)
        logger.info(f"Reconstruction stats: {reconstruction_stats}")

        db.commit()
        logger.info("Import completed successfully!")

        # Print summary
        print("\n" + "=" * 80)
        print("IMPORT SUMMARY")
        print("=" * 80)
        print(f"Transactions: {txn_stats}")
        print(f"Dividends: {div_stats}")
        print(f"Transfers: {transfer_stats}")
        print(f"Forex: {forex_stats}")
        print(f"Cash: {cash_stats}")
        print(f"Holdings Reconstruction: {reconstruction_stats}")
        print("=" * 80)

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
