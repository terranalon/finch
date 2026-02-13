"""IBKR Flex Query import orchestration service.

API-based imports fetch only open positions and cash balances.
Transactions are imported separately via manual XML file upload.
"""

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Account
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.parser import IBKRParser

logger = logging.getLogger(__name__)


class IBKRFlexImportService:
    """Service for importing IBKR data using Flex Query API (cloud-ready)."""

    @staticmethod
    def import_all(
        db: Session, account_id: int, flex_token: str, flex_query_id: str
    ) -> dict[str, Any]:
        """
        Import open positions and cash from IBKR Flex Query API.

        Transactions are NOT imported from the API -- they come from
        manual XML file uploads only.

        Steps:
        1. Fetch Flex Query report via HTTP API
        2. Parse XML response
        3. Extract positions and cash balances
        4. Import positions as holdings, cash as cash holdings
        5. Update asset prices

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

            # Step 3: Extract positions and cash only
            logger.info("Extracting positions and cash balances...")
            positions_data = IBKRParser.extract_positions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            logger.info(
                f"Extracted {len(positions_data)} positions, {len(cash_data)} cash balances"
            )

            # Step 4: Import positions as holdings
            logger.info("Importing positions...")
            pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
            stats["positions"] = pos_stats

            # Step 5: Import cash balances
            logger.info("Importing cash balances...")
            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash"] = cash_stats

            # Step 6: Update asset prices
            logger.info("Updating asset prices...")
            all_symbols = {pos.symbol for pos in positions_data if pos.symbol}
            price_stats = IBKRImportService._update_asset_prices(db, list(all_symbols))
            stats["price_updates"] = price_stats

            stats["unique_assets_in_file"] = len(all_symbols)
            stats["symbols_in_file"] = list(all_symbols)

            # Commit all changes
            db.commit()

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            logger.info("IBKR Flex Query import completed successfully")
            logger.info(
                f"Summary: {pos_stats.get('holdings_created', 0)} new holdings, "
                f"{pos_stats.get('holdings_updated', 0)} updated holdings, "
                f"{cash_stats.get('holdings_created', 0)} cash holdings"
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
    ) -> dict[str, Any]:
        """
        Import historical positions and cash by fetching multiple 365-day periods.

        This method overcomes IBKR's 365-day limitation by:
        1. Splitting date range into 365-day chunks
        2. Fetching each period separately
        3. Merging all XML responses
        4. Importing positions and cash only

        Transactions are NOT imported -- they come from manual XML uploads.

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

            # Step 3: Extract positions and cash only
            logger.info("Extracting positions and cash balances...")
            positions_data = IBKRParser.extract_positions(root)
            cash_data = IBKRParser.extract_cash_balances(root)

            logger.info(
                f"Extracted {len(positions_data)} positions, {len(cash_data)} cash balances"
            )

            # Step 4: Import positions as holdings
            logger.info("Importing positions...")
            pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)
            stats["positions"] = pos_stats

            # Step 5: Import cash balances
            logger.info("Importing cash balances...")
            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)
            stats["cash"] = cash_stats

            # Step 6: Update asset prices
            logger.info("Updating asset prices...")
            all_symbols = {pos.symbol for pos in positions_data if pos.symbol}
            price_stats = IBKRImportService._update_asset_prices(db, list(all_symbols))
            stats["price_updates"] = price_stats

            stats["unique_assets_in_file"] = len(all_symbols)
            stats["symbols_in_file"] = list(all_symbols)

            # Commit all changes
            db.commit()

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            logger.info("Historical IBKR import completed successfully")
            logger.info(
                f"Summary: {pos_stats.get('holdings_created', 0)} new holdings, "
                f"{pos_stats.get('holdings_updated', 0)} updated holdings, "
                f"{cash_stats.get('holdings_created', 0)} cash holdings"
            )

            return stats

        except Exception as e:
            db.rollback()
            logger.error(f"Historical IBKR import failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats
