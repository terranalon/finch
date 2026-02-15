"""IBKR Flex Query import orchestration service.

API-based imports fetch transactions, cash balances, and reconstruct holdings.
Positions are derived from transaction history via holdings reconstruction.
"""

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Account
from app.services.brokers.ibkr.flex_client import IBKRFlexClient
from app.services.brokers.ibkr.import_service import IBKRImportService
from app.services.brokers.ibkr.parser import IBKRParser
from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings

logger = logging.getLogger(__name__)


class IBKRFlexImportService:
    """Service for importing IBKR data using Flex Query API (cloud-ready)."""

    @staticmethod
    def import_all(
        db: Session,
        account_id: int,
        flex_token: str,
        flex_query_id: str,
        start_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Import transactions and cash from IBKR Flex Query API, then reconstruct holdings.

        Positions are NOT imported directly -- they are derived from transaction
        history via holdings reconstruction, consistent with crypto broker imports.

        Args:
            db: Database session
            account_id: Our internal account ID to import into
            flex_token: IBKR Flex Web Service token
            flex_query_id: Flex Query ID
            start_date: Optional start date for incremental import. When set,
                only transactions from this date onwards are fetched.

        Returns:
            Statistics dictionary with import results
        """
        mode = f"incremental from {start_date}" if start_date else "full snapshot"
        logger.info(f"Starting IBKR Flex Query import for account {account_id} ({mode})")

        stats: dict[str, Any] = {
            "account_id": account_id,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "transactions": {},
            "dividends": {},
            "transfers": {},
            "forex": {},
            "other_cash": {},
            "dividend_cash": {},
            "cash": {},
            "holdings_reconstruction": {},
            "price_updates": {},
            "errors": [],
            "warnings": [],
        }

        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                stats["status"] = "failed"
                stats["errors"].append(f"Account {account_id} not found")
                return stats

            # Step 1: Fetch Flex Query report (with optional date range)
            logger.info("Fetching IBKR Flex Query report...")
            xml_data = IBKRFlexClient.fetch_flex_report(
                flex_token, flex_query_id, from_date=start_date
            )

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

            # Step 3: Extract all data types
            logger.info("Extracting transactions and cash data...")
            cash_data = IBKRParser.extract_cash_balances(root)
            transactions = IBKRParser.extract_transactions(root)
            dividends = IBKRParser.extract_dividends(root)
            transfers = IBKRParser.extract_transfers(root)
            forex_txns = IBKRParser.extract_forex_transactions(root)
            other_cash = IBKRParser.extract_other_cash_transactions(root)

            logger.info(
                f"Extracted {len(transactions)} transactions, {len(dividends)} dividends, "
                f"{len(transfers)} transfers, {len(forex_txns)} forex, "
                f"{len(other_cash)} other cash, {len(cash_data)} cash balances"
            )

            # Step 4: Import cash balances
            logger.info("Importing cash balances...")
            stats["cash"] = IBKRImportService._import_cash_balances(db, account_id, cash_data)

            # Step 5: Import all transaction types
            logger.info("Importing transactions...")
            stats["transactions"] = IBKRImportService._import_transactions(
                db, account_id, transactions, source_id=None
            )
            stats["dividends"] = IBKRImportService._import_dividends(
                db, account_id, dividends, source_id=None
            )
            stats["transfers"] = IBKRImportService._import_transfers(
                db, account_id, transfers, source_id=None
            )
            stats["forex"] = IBKRImportService._import_forex_transactions(
                db, account_id, forex_txns, source_id=None
            )
            stats["other_cash"] = IBKRImportService._import_other_cash_transactions(
                db, account_id, other_cash, source_id=None
            )
            stats["dividend_cash"] = IBKRImportService._import_dividend_cash(
                db, account_id, dividends, source_id=None
            )

            # Step 6: Reconstruct holdings from transaction history
            logger.info("Reconstructing holdings from transactions...")
            stats["holdings_reconstruction"] = reconstruct_and_update_holdings(db, account_id)

            # Step 7: Update asset prices (symbols from transactions)
            all_symbols = {
                item.symbol for items in (transactions, dividends) for item in items if item.symbol
            }
            if all_symbols:
                logger.info(f"Updating prices for {len(all_symbols)} symbols...")
                stats["price_updates"] = IBKRImportService._update_asset_prices(
                    db, list(all_symbols)
                )

            db.commit()

            stats["status"] = "completed"
            stats["end_time"] = datetime.now().isoformat()
            logger.info("IBKR Flex Query import completed successfully")

            return stats

        except Exception as e:
            db.rollback()
            logger.error(f"IBKR Flex Query import failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats
