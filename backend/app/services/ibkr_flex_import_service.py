"""IBKR Flex Query import orchestration service."""

import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Account
from app.services.base_import_service import (
    extract_date_range_serializable,
    extract_unique_symbols,
)
from app.services.ibkr_flex_client import IBKRFlexClient
from app.services.ibkr_import_service import IBKRImportService
from app.services.ibkr_parser import IBKRParser

logger = logging.getLogger(__name__)


class IBKRFlexImportService:
    """Service for importing IBKR data using Flex Query API (cloud-ready)."""

    @staticmethod
    def import_all(
        db: Session, account_id: int, flex_token: str, flex_query_id: str
    ) -> dict[str, any]:
        """
        Full import orchestrator using IBKR Flex Query API.

        Steps:
        1. Fetch Flex Query report via HTTP API
        2. Parse XML response
        3. Extract positions, transactions, dividends, cash
        4. Import all data using existing import methods

        Args:
            db: Database session
            account_id: Our internal account ID to import into
            flex_token: IBKR Flex Web Service token
            flex_query_id: Flex Query ID

        Returns:
            Statistics dictionary with import results
        """
        logger.info(f"Starting IBKR Flex Query import for account {account_id}")

        stats = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "positions": {},
            "transactions": {},
            "dividends": {},
            "transfers": {},
            "forex": {},
            "cash": {},
            "errors": [],
            "warnings": [],
        }

        try:
            # Validate account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                stats["status"] = "failed"
                stats["errors"].append(f"Account {account_id} not found")
                return stats

            # Step 1: Fetch Flex Query report
            logger.info("Fetching IBKR Flex Query report...")
            xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)

            if not xml_data:
                stats["status"] = "failed"
                stats["errors"].append(
                    "Failed to fetch Flex Query report. Check your token and query ID."
                )
                return stats

            logger.info(f"Successfully fetched Flex Query data ({len(xml_data)} bytes)")

            # Step 2: Parse XML
            logger.info("Parsing Flex Query XML...")
            root = IBKRParser.parse_xml(xml_data)

            if root is None:
                stats["status"] = "failed"
                stats["errors"].append("Failed to parse Flex Query XML response")
                return stats

            # Step 3: Analyze what data sections and transaction types exist
            logger.info("Analyzing Flex Query structure...")
            flex_sections = IBKRParser.get_all_section_types(root)
            cash_txn_types = IBKRParser.get_cash_transaction_types(root)
            fx_samples = IBKRParser.analyze_fx_transactions(root)
            stats["flex_sections"] = flex_sections
            stats["cash_transaction_types"] = cash_txn_types
            stats["fx_transaction_samples"] = fx_samples

            # Step 4: Extract data sections
            logger.info(
                "Extracting positions, transactions, dividends, transfers, forex, and cash..."
            )
            positions_data = IBKRParser.extract_positions(root)
            transactions_data = IBKRParser.extract_transactions(root)
            dividends_data = IBKRParser.extract_dividends(root)
            transfers_data = IBKRParser.extract_transfers(root)
            forex_data = IBKRParser.extract_forex_transactions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            logger.info(
                f"Extracted {len(positions_data)} positions, "
                f"{len(transactions_data)} transactions, "
                f"{len(dividends_data)} dividends, "
                f"{len(transfers_data)} transfers, "
                f"{len(forex_data)} forex conversions, "
                f"{len(cash_data)} cash balances"
            )

            # Step 4: Import positions
            logger.info("Importing positions...")
            pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
            stats["positions"] = pos_stats

            # Step 5: Import cash balances
            logger.info("Importing cash balances...")
            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash"] = cash_stats

            # Step 6: Import transactions
            logger.info("Importing transactions...")
            txn_stats = IBKRImportService._import_transactions(db, account_id, transactions_data)
            stats["transactions"] = txn_stats

            # Step 7: Import dividends
            logger.info("Importing dividends...")
            div_stats = IBKRImportService._import_dividends(db, account_id, dividends_data)
            stats["dividends"] = div_stats

            # Step 8: Import transfers
            logger.info("Importing transfers...")
            transfer_stats = IBKRImportService._import_transfers(db, account_id, transfers_data)
            stats["transfers"] = transfer_stats

            # Step 9: Import forex conversions
            logger.info("Importing forex conversions...")
            forex_stats = IBKRImportService._import_forex_transactions(db, account_id, forex_data)
            stats["forex"] = forex_stats

            # Step 10: Update asset prices
            logger.info("Updating asset prices...")
            all_symbols = extract_unique_symbols(positions_data, transactions_data, dividends_data)

            price_stats = IBKRImportService._update_asset_prices(db, list(all_symbols))
            stats["price_updates"] = price_stats

            # Track unique assets for UI display
            stats["unique_assets_in_file"] = len(all_symbols)
            stats["symbols_in_file"] = list(all_symbols)

            # Calculate date range from imported data for snapshot generation
            all_dates = (
                [txn.get("date") for txn in transactions_data]
                + [div.get("date") for div in dividends_data]
                + [transfer.get("date") for transfer in transfers_data]
                + [fx.get("date") for fx in forex_data]
            )
            date_range = extract_date_range_serializable(all_dates)
            if date_range:
                stats["date_range"] = date_range

            # Commit all changes
            db.commit()

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            logger.info("IBKR Flex Query import completed successfully")
            logger.info(
                f"Summary: {pos_stats['holdings_created'] + pos_stats['holdings_updated']} holdings, "
                f"{txn_stats['imported']} transactions, "
                f"{div_stats['imported']} dividends, "
                f"{transfer_stats['imported']} transfers, "
                f"{forex_stats['imported']} forex conversions"
            )

            return stats

        except Exception as e:
            db.rollback()
            logger.error(f"IBKR Flex Query import failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats

    @staticmethod
    def import_historical(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
        start_date: date,
        end_date: date | None = None,
    ) -> dict[str, any]:
        """
        Import complete historical data by fetching multiple 365-day periods.

        This method overcomes IBKR's 365-day limitation by:
        1. Splitting date range into 365-day chunks
        2. Fetching each period separately
        3. Merging all XML responses
        4. Importing merged data

        Use this when you need data from before the last 365 days.

        Args:
            db: Database session
            account_id: Our internal account ID
            flex_token: IBKR Flex Web Service token
            flex_query_id: Flex Query ID
            start_date: First date to import (e.g., account opening date)
            end_date: Last date to import (defaults to today)

        Returns:
            Statistics dictionary with import results
        """
        if not end_date:
            end_date = date.today()

        logger.info(f"Starting historical IBKR import for account {account_id}")
        logger.info(
            f"Date range: {start_date} to {end_date} ({(end_date - start_date).days + 1} days)"
        )

        stats = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "total_days": (end_date - start_date).days + 1,
            },
            "positions": {},
            "transactions": {},
            "dividends": {},
            "transfers": {},
            "forex": {},
            "cash": {},
            "errors": [],
            "warnings": [],
        }

        try:
            # Validate account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                stats["status"] = "failed"
                stats["errors"].append(f"Account {account_id} not found")
                return stats

            # Step 1: Fetch multi-period data
            logger.info("Fetching historical data in 365-day chunks...")
            xml_data_list = IBKRFlexClient.fetch_multi_period_report(
                flex_token, flex_query_id, start_date, end_date
            )

            if not xml_data_list:
                stats["status"] = "failed"
                stats["errors"].append("Failed to fetch any historical data periods")
                return stats

            stats["periods_fetched"] = len(xml_data_list)
            logger.info(f"Successfully fetched {len(xml_data_list)} periods")

            # Step 2: Merge XML documents
            logger.info("Merging XML documents...")
            root = IBKRParser.merge_xml_documents(xml_data_list)

            if root is None:
                stats["status"] = "failed"
                stats["errors"].append("Failed to merge XML documents")
                return stats

            # Step 3: Analyze what data sections exist
            logger.info("Analyzing merged data structure...")
            flex_sections = IBKRParser.get_all_section_types(root)
            cash_txn_types = IBKRParser.get_cash_transaction_types(root)
            fx_samples = IBKRParser.analyze_fx_transactions(root)
            stats["flex_sections"] = flex_sections
            stats["cash_transaction_types"] = cash_txn_types
            stats["fx_transaction_samples"] = fx_samples

            # Step 4: Extract data sections
            logger.info(
                "Extracting positions, transactions, dividends, transfers, forex, and cash..."
            )
            positions_data = IBKRParser.extract_positions(root)
            transactions_data = IBKRParser.extract_transactions(root)
            dividends_data = IBKRParser.extract_dividends(root)
            transfers_data = IBKRParser.extract_transfers(root)
            forex_data = IBKRParser.extract_forex_transactions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            logger.info(
                f"Extracted {len(positions_data)} positions, "
                f"{len(transactions_data)} transactions, "
                f"{len(dividends_data)} dividends, "
                f"{len(transfers_data)} transfers, "
                f"{len(forex_data)} forex conversions, "
                f"{len(cash_data)} cash balances"
            )

            # Step 5: Import positions
            logger.info("Importing positions...")
            pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
            stats["positions"] = pos_stats

            # Step 6: Import cash balances
            logger.info("Importing cash balances...")
            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash"] = cash_stats

            # Step 7: Import transactions
            logger.info("Importing transactions...")
            txn_stats = IBKRImportService._import_transactions(db, account_id, transactions_data)
            stats["transactions"] = txn_stats

            # Step 8: Import dividends
            logger.info("Importing dividends...")
            div_stats = IBKRImportService._import_dividends(db, account_id, dividends_data)
            stats["dividends"] = div_stats

            # Step 9: Import transfers
            logger.info("Importing transfers...")
            transfer_stats = IBKRImportService._import_transfers(db, account_id, transfers_data)
            stats["transfers"] = transfer_stats

            # Step 10: Import forex conversions
            logger.info("Importing forex conversions...")
            forex_stats = IBKRImportService._import_forex_transactions(db, account_id, forex_data)
            stats["forex"] = forex_stats

            # Step 11: Update asset prices
            logger.info("Updating asset prices...")
            all_symbols = extract_unique_symbols(positions_data, transactions_data, dividends_data)

            price_stats = IBKRImportService._update_asset_prices(db, list(all_symbols))
            stats["price_updates"] = price_stats

            # Track unique assets for UI display (consistent with import_all)
            stats["unique_assets_in_file"] = len(all_symbols)
            stats["symbols_in_file"] = list(all_symbols)

            # Commit all changes
            db.commit()

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            logger.info("Historical IBKR import completed successfully")
            logger.info(
                f"Summary: {pos_stats['holdings_created'] + pos_stats['holdings_updated']} holdings, "
                f"{txn_stats['imported']} transactions, "
                f"{div_stats['imported']} dividends, "
                f"{transfer_stats['imported']} transfers, "
                f"{forex_stats['imported']} forex conversions"
            )

            return stats

        except Exception as e:
            db.rollback()
            logger.error(f"Historical IBKR import failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats
