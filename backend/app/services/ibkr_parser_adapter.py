"""Adapter for IBKR parser to implement BaseBrokerParser interface.

This adapter wraps the existing IBKRParser class to work with the
broker-agnostic parser registry system.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal

from app.services.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.ibkr_parser import IBKRParser

logger = logging.getLogger(__name__)


class IBKRParserAdapter(BaseBrokerParser):
    """Adapter that wraps IBKRParser with BaseBrokerParser interface.

    This enables the existing IBKR parsing logic to work with the
    new broker-agnostic data consolidation system.
    """

    @classmethod
    def broker_type(cls) -> str:
        return "ibkr"

    @classmethod
    def broker_name(cls) -> str:
        return "Interactive Brokers"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".xml"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract date range from IBKR Flex Query XML.

        Reads the FlexStatement attributes and also scans transaction dates
        to determine the actual data range.

        Args:
            file_content: XML file content as bytes

        Returns:
            Tuple of (start_date, end_date)

        Raises:
            ValueError: If date range cannot be determined
        """
        try:
            root = ET.fromstring(file_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}") from e

        # Try to get dates from FlexStatement attributes first
        statement = root.find(".//FlexStatement")
        if statement is not None:
            from_date = statement.get("fromDate")
            to_date = statement.get("toDate")

            if from_date and to_date:
                try:
                    start = datetime.strptime(from_date, "%Y%m%d").date()
                    end = datetime.strptime(to_date, "%Y%m%d").date()
                    logger.info("Date range from FlexStatement: %s to %s", start, end)
                    return start, end
                except ValueError:
                    pass

        # Fall back to scanning actual transaction dates
        dates: list[date] = []

        # Check trades
        for trade in root.findall(".//Trade"):
            trade_date = trade.get("tradeDate")
            if trade_date:
                try:
                    dates.append(datetime.strptime(trade_date, "%Y%m%d").date())
                except ValueError:
                    pass

        # Check cash transactions
        for cash_txn in root.findall(".//CashTransaction"):
            txn_date = cash_txn.get("dateTime", "")[:8]  # Take YYYYMMDD part
            if txn_date:
                try:
                    dates.append(datetime.strptime(txn_date, "%Y%m%d").date())
                except ValueError:
                    pass

        # Check forex transactions
        for fx_txn in root.findall(".//FxTransaction"):
            txn_date = fx_txn.get("dateTime", "")[:8]
            if txn_date:
                try:
                    dates.append(datetime.strptime(txn_date, "%Y%m%d").date())
                except ValueError:
                    pass

        if not dates:
            raise ValueError("Could not determine date range from XML - no dates found")

        start_date = min(dates)
        end_date = max(dates)
        logger.info("Date range from transactions: %s to %s", start_date, end_date)

        return start_date, end_date

    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse IBKR Flex Query XML into normalized import data.

        Uses the existing IBKRParser methods and converts results to
        the standard BrokerImportData format.

        Args:
            file_content: XML file content as bytes

        Returns:
            BrokerImportData containing parsed records
        """
        root = IBKRParser.parse_xml(file_content)
        if root is None:
            raise ValueError("Failed to parse XML")

        # Get date range
        start_date, end_date = self.extract_date_range(file_content)

        # Parse using existing methods
        raw_transactions = IBKRParser.extract_transactions(root)
        raw_positions = IBKRParser.extract_positions(root)
        raw_dividends = IBKRParser.extract_dividends(root)
        raw_transfers = IBKRParser.extract_transfers(root)
        raw_forex = IBKRParser.extract_forex_transactions(root)
        raw_other_cash = IBKRParser.extract_other_cash_transactions(root)

        # Convert to normalized format
        transactions = self._convert_transactions(raw_transactions)
        positions = self._convert_positions(raw_positions)
        dividends = self._convert_dividends(raw_dividends)

        # Cash transactions include:
        # - Transfers (deposits/withdrawals)
        # - Forex conversions
        # - Other cash (interest, taxes, fees)
        # - Dividend cash impact (dividends also credit cash)
        cash_transactions = (
            self._convert_transfers(raw_transfers)
            + self._convert_forex(raw_forex)
            + self._convert_other_cash(raw_other_cash)
            + self._convert_dividend_cash_impact(raw_dividends)
        )

        return BrokerImportData(
            start_date=start_date,
            end_date=end_date,
            transactions=transactions,
            positions=positions,
            cash_transactions=cash_transactions,
            dividends=dividends,
            raw_metadata={
                "parser": "IBKRParserAdapter",
                "raw_counts": {
                    "transactions": len(raw_transactions),
                    "positions": len(raw_positions),
                    "dividends": len(raw_dividends),
                    "transfers": len(raw_transfers),
                    "forex": len(raw_forex),
                    "other_cash": len(raw_other_cash),
                },
            },
        )

    def _convert_transactions(self, raw_transactions: list[dict]) -> list[ParsedTransaction]:
        """Convert raw IBKR transactions to normalized format."""
        result = []
        for txn in raw_transactions:
            try:
                result.append(
                    ParsedTransaction(
                        trade_date=txn["trade_date"],
                        symbol=txn["symbol"],
                        transaction_type=txn["transaction_type"],
                        quantity=txn.get("quantity"),
                        price_per_unit=txn.get("price"),
                        fees=txn.get("commission", Decimal("0")),
                        currency=txn.get("currency", "USD"),
                        notes=txn.get("description"),
                        raw_data=txn,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed transaction: %s", e)
        return result

    def _convert_positions(self, raw_positions: list[dict]) -> list[ParsedPosition]:
        """Convert raw IBKR positions to normalized format."""
        result = []
        for pos in raw_positions:
            try:
                result.append(
                    ParsedPosition(
                        symbol=pos["symbol"],
                        quantity=pos["quantity"],
                        cost_basis=pos.get("cost_basis"),
                        currency=pos.get("currency", "USD"),
                        asset_class=pos.get("asset_class"),
                        raw_data=pos,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed position: %s", e)
        return result

    def _convert_dividends(self, raw_dividends: list[dict]) -> list[ParsedTransaction]:
        """Convert raw IBKR dividends to normalized format."""
        result = []
        for div in raw_dividends:
            try:
                result.append(
                    ParsedTransaction(
                        trade_date=div["date"],
                        symbol=div["symbol"],
                        transaction_type="Dividend",
                        amount=div.get("amount"),
                        currency=div.get("currency", "USD"),
                        notes=div.get("description"),
                        raw_data=div,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed dividend: %s", e)
        return result

    def _convert_transfers(self, raw_transfers: list[dict]) -> list[ParsedCashTransaction]:
        """Convert raw IBKR transfers to normalized format."""
        result = []
        for transfer in raw_transfers:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=transfer["date"],
                        transaction_type=transfer["type"],  # 'Deposit', 'Withdrawal', etc.
                        amount=transfer["amount"],
                        currency=transfer.get("currency", "USD"),
                        notes=transfer.get("description"),
                        raw_data=transfer,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed transfer: %s", e)
        return result

    def _convert_forex(self, raw_forex: list[dict]) -> list[ParsedCashTransaction]:
        """Convert raw IBKR forex transactions to normalized format."""
        result = []
        for fx in raw_forex:
            try:
                # Forex creates two entries: one for each currency
                result.append(
                    ParsedCashTransaction(
                        date=fx["date"],
                        transaction_type="Forex Conversion",
                        amount=fx["from_amount"],
                        currency=fx["from_currency"],
                        notes=f"Convert to {fx['to_currency']}",
                        raw_data=fx,
                    )
                )
                result.append(
                    ParsedCashTransaction(
                        date=fx["date"],
                        transaction_type="Forex Conversion",
                        amount=fx["to_amount"],
                        currency=fx["to_currency"],
                        notes=f"Convert from {fx['from_currency']}",
                        raw_data=fx,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed forex: %s", e)
        return result

    def _convert_other_cash(self, raw_other: list[dict]) -> list[ParsedCashTransaction]:
        """Convert other cash transactions (interest, tax, fees) to normalized format."""
        result = []
        for item in raw_other:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=item["date"],
                        transaction_type=item["type"],  # 'Interest', 'Tax', 'Fee'
                        amount=item["amount"],  # Keeps sign (negative for tax/fees)
                        currency=item.get("currency", "USD"),
                        notes=item.get("description"),
                        raw_data=item,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed other cash transaction: %s", e)
        return result

    def _convert_dividend_cash_impact(
        self, raw_dividends: list[dict]
    ) -> list[ParsedCashTransaction]:
        """Convert dividends to cash transactions (dividends credit cash).

        Dividends are stored both:
        1. As stock transactions (linked to the holding that generated them)
        2. As cash transactions (they increase cash balance)

        This method creates the cash-side entries.
        """
        result = []
        for div in raw_dividends:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=div["date"],
                        transaction_type="Dividend",
                        amount=div["amount"],  # Positive - adds to cash
                        currency=div.get("currency", "USD"),
                        notes=f"Dividend from {div.get('symbol', 'unknown')}",
                        raw_data=div,
                    )
                )
            except (KeyError, TypeError) as e:
                logger.warning("Skipping dividend cash impact: %s", e)
        return result
