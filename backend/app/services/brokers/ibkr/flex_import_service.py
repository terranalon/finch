"""IBKR Flex Query import orchestration service.

API-based imports fetch transactions, cash balances, and reconstruct holdings.
Positions are derived from transaction history via holdings reconstruction.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Account
from app.models.broker_data_source import BrokerDataSource
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
        pre_fetched_root: ET.Element | None = None,
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
            pre_fetched_root: Optional pre-parsed XML root to skip fetching.

        Returns:
            Statistics dictionary with import results
        """
        mode = f"incremental from {start_date}" if start_date else "full snapshot"
        logger.info("Starting IBKR Flex Query import for account %s (%s)", account_id, mode)

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

            if pre_fetched_root is not None:
                root = pre_fetched_root
            else:
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

                logger.info("Successfully fetched Flex Query data (%d bytes)", len(xml_data))

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
                "Extracted %d transactions, %d dividends, %d transfers, "
                "%d forex, %d other cash, %d cash balances",
                len(transactions),
                len(dividends),
                len(transfers),
                len(forex_txns),
                len(other_cash),
                len(cash_data),
            )

            # Step 4: Create data source record for coverage tracking
            today = date.today()
            source = BrokerDataSource(
                account_id=account_id,
                broker_type="ibkr",
                source_type="api_fetch",
                source_identifier="IBKR Flex Query API",
                start_date=start_date or today,
                end_date=today,
                status="pending",
            )
            db.add(source)
            db.flush()

            # Step 5: Import cash balances
            logger.info("Importing cash balances...")
            stats["cash"] = IBKRImportService._import_cash_balances(db, account_id, cash_data)

            # Step 6: Import all transaction types
            logger.info("Importing transactions...")
            stats["transactions"] = IBKRImportService._import_transactions(
                db, account_id, transactions, source_id=source.id
            )
            stats["dividends"] = IBKRImportService._import_dividends(
                db, account_id, dividends, source_id=source.id
            )
            stats["transfers"] = IBKRImportService._import_transfers(
                db, account_id, transfers, source_id=source.id
            )
            stats["forex"] = IBKRImportService._import_forex_transactions(
                db, account_id, forex_txns, source_id=source.id
            )
            stats["other_cash"] = IBKRImportService._import_other_cash_transactions(
                db, account_id, other_cash, source_id=source.id
            )
            stats["dividend_cash"] = IBKRImportService._import_dividend_cash(
                db, account_id, dividends, source_id=source.id
            )

            # Step 7: Reconstruct holdings from transaction history
            logger.info("Reconstructing holdings from transactions...")
            stats["holdings_reconstruction"] = reconstruct_and_update_holdings(db, account_id)

            # Step 8: Finalize data source
            source.status = "completed"
            source.import_stats = stats

            # Step 9: Update asset prices (symbols from transactions)
            all_symbols = {
                item.symbol for items in (transactions, dividends) for item in items if item.symbol
            }
            if all_symbols:
                logger.info("Updating prices for %d symbols...", len(all_symbols))
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
            logger.error("IBKR Flex Query import failed: %s", e, exc_info=True)
            stats["status"] = "failed"
            stats["errors"].append(str(e))
            stats["end_time"] = datetime.now().isoformat()
            return stats
