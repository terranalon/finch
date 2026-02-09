"""Adapter for IBKR parser to implement BaseBrokerParser interface.

This adapter wraps the existing IBKRParser class to work with the
broker-agnostic parser registry system.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime

from app.services.brokers.base_broker_parser import (
    BaseBrokerParser,
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.brokers.ibkr.parser import IBKRParser

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

    def _convert_transactions(self, raw_transactions: list) -> list[ParsedTransaction]:
        """Convert raw IBKR transactions to normalized format."""
        result = []
        for txn in raw_transactions:
            try:
                result.append(
                    ParsedTransaction(
                        trade_date=txn.trade_date,
                        symbol=txn.symbol,
                        transaction_type=txn.transaction_type,
                        quantity=txn.quantity,
                        price_per_unit=txn.price,
                        fees=txn.commission,
                        currency=txn.currency,
                        notes=txn.description,
                        raw_data=txn,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed transaction: %s", e)
        return result

    def _convert_positions(self, raw_positions: list) -> list[ParsedPosition]:
        """Convert raw IBKR positions to normalized format."""
        result = []
        for pos in raw_positions:
            try:
                result.append(
                    ParsedPosition(
                        symbol=pos.symbol,
                        quantity=pos.quantity,
                        cost_basis=pos.cost_basis,
                        currency=pos.currency,
                        asset_class=pos.asset_class,
                        raw_data=pos,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed position: %s", e)
        return result

    def _convert_dividends(self, raw_dividends: list) -> list[ParsedTransaction]:
        """Convert raw IBKR dividends to normalized format."""
        result = []
        for div in raw_dividends:
            try:
                result.append(
                    ParsedTransaction(
                        trade_date=div.date,
                        symbol=div.symbol,
                        transaction_type="Dividend",
                        amount=div.amount,
                        currency=div.currency,
                        notes=div.description,
                        raw_data=div,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed dividend: %s", e)
        return result

    def _convert_transfers(self, raw_transfers: list) -> list[ParsedCashTransaction]:
        """Convert raw IBKR transfers to normalized format."""
        result = []
        for transfer in raw_transfers:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=transfer.date,
                        transaction_type=transfer.type,
                        amount=transfer.amount,
                        currency=transfer.currency,
                        notes=transfer.description,
                        raw_data=transfer,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed transfer: %s", e)
        return result

    def _convert_forex(self, raw_forex: list) -> list[ParsedCashTransaction]:
        """Convert raw IBKR forex transactions to normalized format."""
        result = []
        for fx in raw_forex:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=fx.date,
                        transaction_type="Forex Conversion",
                        amount=fx.from_amount,
                        currency=fx.from_currency,
                        notes=f"Convert to {fx.to_currency}",
                        raw_data=fx,
                    )
                )
                result.append(
                    ParsedCashTransaction(
                        date=fx.date,
                        transaction_type="Forex Conversion",
                        amount=fx.to_amount,
                        currency=fx.to_currency,
                        notes=f"Convert from {fx.from_currency}",
                        raw_data=fx,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed forex: %s", e)
        return result

    def _convert_other_cash(self, raw_other: list) -> list[ParsedCashTransaction]:
        """Convert other cash transactions (interest, tax, fees) to normalized format."""
        result = []
        for item in raw_other:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=item.date,
                        transaction_type=item.type,
                        amount=item.amount,
                        currency=item.currency,
                        notes=item.description,
                        raw_data=item,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed other cash transaction: %s", e)
        return result

    def _convert_dividend_cash_impact(self, raw_dividends: list) -> list[ParsedCashTransaction]:
        """Convert dividends to cash transactions (dividends credit cash)."""
        result = []
        for div in raw_dividends:
            try:
                result.append(
                    ParsedCashTransaction(
                        date=div.date,
                        transaction_type="Dividend",
                        amount=div.amount,
                        currency=div.currency,
                        notes=f"Dividend from {div.symbol}",
                        raw_data=div,
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping dividend cash impact: %s", e)
        return result
