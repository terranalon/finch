"""IBKR Flex Query XML parser."""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal

from app.services.asset_type_detector import map_ibkr_asset_class

logger = logging.getLogger(__name__)


class IBKRParser:
    """Parser for IBKR Flex Query XML responses."""

    @staticmethod
    def parse_xml(xml_data: bytes) -> ET.Element | None:
        """
        Parse XML bytes into ElementTree Element.

        Args:
            xml_data: XML data as bytes

        Returns:
            ElementTree Element root, or None if parsing failed
        """
        try:
            root = ET.fromstring(xml_data)
            logger.info(f"Successfully parsed XML, root tag: {root.tag}")
            return root
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
            return None

    @staticmethod
    def merge_xml_documents(xml_data_list: list[bytes]) -> ET.Element | None:
        """
        Merge multiple Flex Query XML responses into a single ElementTree.

        This is used when fetching data in multiple 365-day chunks.
        Strategy: Parse first document as base, then append FlexStatement children
        from subsequent documents.

        Args:
            xml_data_list: List of XML data bytes to merge

        Returns:
            Merged ElementTree root, or None if parsing failed
        """
        if not xml_data_list:
            logger.error("No XML data provided for merging")
            return None

        if len(xml_data_list) == 1:
            # Single document, no merging needed
            return IBKRParser.parse_xml(xml_data_list[0])

        try:
            # Parse first document as base
            base_root = ET.fromstring(xml_data_list[0])
            logger.info(f"Merging {len(xml_data_list)} XML documents")

            # Find the first FlexStatement element to append to
            base_statement = base_root.find(".//FlexStatement")
            if base_statement is None:
                logger.error("No FlexStatement found in base document")
                return base_root

            # Merge subsequent documents
            for i, xml_data in enumerate(xml_data_list[1:], start=2):
                try:
                    doc_root = ET.fromstring(xml_data)
                    doc_statement = doc_root.find(".//FlexStatement")

                    if doc_statement is None:
                        logger.warning(f"No FlexStatement in document {i}, skipping")
                        continue

                    # Append all child elements from this statement to base
                    for child in doc_statement:
                        base_statement.append(child)

                    logger.info(f"Merged document {i}/{len(xml_data_list)}")

                except ET.ParseError as e:
                    logger.error(f"Error parsing document {i}: {str(e)}")
                    continue

            logger.info(f"Successfully merged {len(xml_data_list)} XML documents")
            return base_root

        except Exception as e:
            logger.error(f"Error merging XML documents: {str(e)}")
            return None

    @staticmethod
    def extract_positions(root: ET.Element) -> list[dict]:
        """
        Extract open positions from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of position dictionaries
        """
        positions = []

        try:
            # Find OpenPositions section
            for stmt in root.findall(".//FlexStatement"):
                for position in stmt.findall(".//OpenPosition"):
                    try:
                        symbol = position.get("symbol", "")
                        description = position.get("description", "")
                        asset_category = position.get("assetCategory", "")
                        listing_exchange = position.get("listingExchange", "")
                        position_value = position.get("position", "0")
                        cost_basis = position.get("costBasisMoney", "0")
                        currency = position.get("currency", "USD")
                        account_id = position.get("accountId", "")

                        # Extract permanent identifiers
                        cusip = position.get("cusip", "")
                        isin = position.get("isin", "")
                        conid = position.get("conid", "")
                        figi = position.get("figi", "")

                        if not symbol:
                            logger.warning("Skipping position without symbol")
                            continue

                        # Normalize symbol
                        symbol_info = IBKRParser.normalize_symbol(
                            symbol, asset_category, listing_exchange
                        )

                        positions.append(
                            {
                                "symbol": symbol_info["yf_symbol"],
                                "original_symbol": symbol_info["original_symbol"],
                                "description": description,
                                "asset_category": asset_category,
                                "asset_class": IBKRParser.map_asset_class(
                                    asset_category, symbol_info["yf_symbol"]
                                ),
                                "listing_exchange": listing_exchange,
                                "quantity": Decimal(str(position_value)),
                                "cost_basis": abs(Decimal(str(cost_basis))),
                                "currency": currency,
                                "account_id": account_id,
                                "needs_validation": symbol_info["needs_validation"],
                                # Permanent identifiers (don't change with ticker symbol changes)
                                "cusip": cusip or None,
                                "isin": isin or None,
                                "conid": conid or None,
                                "figi": figi or None,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing position {position.get('symbol')}: {str(e)}")
                        continue

            logger.info(f"Extracted {len(positions)} positions")
            return positions

        except Exception as e:
            logger.error(f"Error extracting positions: {str(e)}")
            return []

    @staticmethod
    def extract_transactions(root: ET.Element) -> list[dict]:
        """
        Extract trades from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of transaction dictionaries
        """
        transactions = []

        try:
            for stmt in root.findall(".//FlexStatement"):
                for trade in stmt.findall(".//Trade"):
                    try:
                        symbol = trade.get("symbol", "")
                        asset_category = trade.get("assetCategory", "")
                        listing_exchange = trade.get("listingExchange", "")
                        trade_date_str = trade.get("tradeDate", "")
                        buy_sell = trade.get("buySell", "")
                        quantity = trade.get("quantity", "0")
                        trade_price = trade.get("tradePrice", "0")
                        commission = trade.get("ibCommission", "0")
                        net_cash = trade.get("netCash", "0")
                        currency = trade.get("currency", "USD")
                        account_id = trade.get("accountId", "")
                        description = trade.get("description", "")

                        # Extract permanent identifiers
                        cusip = trade.get("cusip", "")
                        isin = trade.get("isin", "")
                        conid = trade.get("conid", "")
                        figi = trade.get("figi", "")
                        trade_id = trade.get("tradeID", "")

                        if not symbol or not trade_date_str:
                            logger.warning("Skipping trade without symbol or date")
                            continue

                        # Parse trade date
                        trade_date = datetime.strptime(trade_date_str, "%Y%m%d").date()

                        # Normalize symbol
                        symbol_info = IBKRParser.normalize_symbol(
                            symbol, asset_category, listing_exchange
                        )

                        # Map Buy/Sell to our transaction types
                        transaction_type = "Buy" if buy_sell == "BUY" else "Sell"

                        transactions.append(
                            {
                                "symbol": symbol_info["yf_symbol"],
                                "original_symbol": symbol_info["original_symbol"],
                                "description": description,
                                "asset_category": asset_category,
                                "asset_class": IBKRParser.map_asset_class(
                                    asset_category, symbol_info["yf_symbol"]
                                ),
                                "listing_exchange": listing_exchange,
                                "trade_date": trade_date,
                                "transaction_type": transaction_type,
                                "quantity": abs(Decimal(str(quantity))),
                                "price": abs(Decimal(str(trade_price))),
                                "commission": abs(Decimal(str(commission))),
                                "net_cash": Decimal(str(net_cash)),
                                "currency": currency,
                                "account_id": account_id,
                                "needs_validation": symbol_info["needs_validation"],
                                # Permanent identifiers (don't change with ticker symbol changes)
                                "cusip": cusip or None,
                                "isin": isin or None,
                                "conid": conid or None,
                                "figi": figi or None,
                                # External transaction ID for deduplication
                                "external_transaction_id": trade_id or None,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing trade {trade.get('symbol')}: {str(e)}")
                        continue

            logger.info(f"Extracted {len(transactions)} trades")
            return transactions

        except Exception as e:
            logger.error(f"Error extracting transactions: {str(e)}")
            return []

    @staticmethod
    def extract_dividends(root: ET.Element) -> list[dict]:
        """
        Extract dividend transactions from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of dividend dictionaries (deduplicated)
        """
        dividends = []
        seen_keys: set[tuple] = set()  # For deduplication

        try:
            for stmt in root.findall(".//FlexStatement"):
                for cash_txn in stmt.findall(".//CashTransaction"):
                    try:
                        transaction_type = cash_txn.get("type", "")

                        # Only process dividends
                        if transaction_type not in ["Dividends", "Payment In Lieu Of Dividends"]:
                            continue

                        symbol = cash_txn.get("symbol", "")
                        asset_category = cash_txn.get("assetCategory", "")
                        listing_exchange = cash_txn.get("listingExchange", "")
                        date_str = cash_txn.get("dateTime", "")
                        amount = cash_txn.get("amount", "0")
                        currency = cash_txn.get("currency", "USD")
                        account_id = cash_txn.get("accountId", "")
                        description = cash_txn.get("description", "")

                        if not symbol or not date_str:
                            logger.warning("Skipping dividend without symbol or date")
                            continue

                        # Parse date (format: YYYYMMDD;HHMMSS or YYYYMMDD)
                        if ";" in date_str:
                            date_part = date_str.split(";")[0]
                            txn_date = datetime.strptime(date_part, "%Y%m%d").date()
                        else:
                            txn_date = datetime.strptime(date_str[:8], "%Y%m%d").date()

                        # Normalize symbol
                        symbol_info = IBKRParser.normalize_symbol(
                            symbol, asset_category, listing_exchange
                        )

                        amount_decimal = abs(Decimal(str(amount)))

                        # Deduplicate: key is (date, symbol, currency, amount)
                        dedup_key = (txn_date, symbol, currency, str(amount_decimal))
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        dividends.append(
                            {
                                "symbol": symbol_info["yf_symbol"],
                                "original_symbol": symbol_info["original_symbol"],
                                "description": description,
                                "asset_category": asset_category,
                                "asset_class": IBKRParser.map_asset_class(
                                    asset_category, symbol_info["yf_symbol"]
                                ),
                                "date": txn_date,
                                "amount": amount_decimal,
                                "currency": currency,
                                "account_id": account_id,
                                "needs_validation": symbol_info["needs_validation"],
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing dividend: {str(e)}")
                        continue

            logger.info(f"Extracted {len(dividends)} dividends (deduplicated)")
            return dividends

        except Exception as e:
            logger.error(f"Error extracting dividends: {str(e)}")
            return []

    @staticmethod
    def extract_transfers(root: ET.Element) -> list[dict]:
        """
        Extract deposit/withdrawal transfers from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of transfer dictionaries (deduplicated)
        """
        transfers = []
        seen_keys: set[tuple] = set()  # For deduplication

        try:
            for stmt in root.findall(".//FlexStatement"):
                # Method 1: Look in CashTransaction section
                for cash_txn in stmt.findall(".//CashTransaction"):
                    try:
                        transaction_type = cash_txn.get("type", "")

                        # Match deposit/withdrawal types
                        if transaction_type not in [
                            "Deposits & Withdrawals",
                            "Deposits/Withdrawals",
                            "Deposits",
                            "Withdrawals",
                        ]:
                            continue

                        date_str = cash_txn.get("dateTime", "")
                        amount = cash_txn.get("amount", "0")
                        currency = cash_txn.get("currency", "USD")
                        description = cash_txn.get("description", "")
                        account_id = cash_txn.get("accountId", "")

                        if not date_str:
                            logger.warning("Skipping transfer without date")
                            continue

                        # Parse date (format: YYYYMMDD;HHMMSS or YYYYMMDD)
                        if ";" in date_str:
                            date_part = date_str.split(";")[0]
                            txn_date = datetime.strptime(date_part, "%Y%m%d").date()
                        else:
                            txn_date = datetime.strptime(date_str[:8], "%Y%m%d").date()

                        amount_decimal = Decimal(str(amount))

                        # Determine transfer type based on amount sign
                        transfer_type = "Deposit" if amount_decimal > 0 else "Withdrawal"

                        # Deduplicate: key is (date, type, currency, amount)
                        dedup_key = (txn_date, transfer_type, currency, str(abs(amount_decimal)))
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        transfers.append(
                            {
                                "date": txn_date,
                                "type": transfer_type,
                                "amount": abs(amount_decimal),
                                "currency": currency,
                                "description": description or f"{transfer_type} - {currency}",
                                "account_id": account_id,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing transfer: {str(e)}")
                        continue

                # Method 2: Look in dedicated Transfers section (if exists)
                for transfer in stmt.findall(".//Transfer"):
                    try:
                        date_str = transfer.get("date", "")
                        amount = transfer.get("amount", "0")
                        currency = transfer.get("currency", "USD")
                        description = transfer.get("description", "")
                        direction = transfer.get("direction", "")
                        account_id = transfer.get("accountId", "")

                        if not date_str:
                            continue

                        # Parse date
                        if ";" in date_str:
                            date_part = date_str.split(";")[0]
                            txn_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                        else:
                            txn_date = datetime.strptime(date_str[:8], "%Y%m%d").date()

                        amount_decimal = Decimal(str(amount))

                        # Use direction if available, otherwise use amount sign
                        if direction:
                            transfer_type = (
                                "Deposit"
                                if direction.lower() in ["in", "incoming"]
                                else "Withdrawal"
                            )
                        else:
                            transfer_type = "Deposit" if amount_decimal > 0 else "Withdrawal"

                        # Deduplicate
                        dedup_key = (txn_date, transfer_type, currency, str(abs(amount_decimal)))
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        transfers.append(
                            {
                                "date": txn_date,
                                "type": transfer_type,
                                "amount": abs(amount_decimal),
                                "currency": currency,
                                "description": description or f"{transfer_type} - {currency}",
                                "account_id": account_id,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing transfer from Transfers section: {str(e)}")
                        continue

            logger.info(f"Extracted {len(transfers)} transfers (deduplicated)")
            return transfers

        except Exception as e:
            logger.error(f"Error extracting transfers: {str(e)}")
            return []

    @staticmethod
    def extract_other_cash_transactions(root: ET.Element) -> list[dict]:
        """
        Extract other cash transactions (interest, taxes, fees) from FlexQueryResponse.

        These affect cash balances but aren't captured by other parsers:
        - Broker Interest Received/Paid
        - Withholding Tax
        - Other Fees (e.g., ADR custody fees)

        Args:
            root: XML root element

        Returns:
            List of cash transaction dictionaries (deduplicated)
        """
        transactions = []
        seen_keys: set[tuple] = set()  # For deduplication

        # Map IBKR types to our transaction types
        # Add new types here as they're discovered
        type_mapping = {
            "Broker Interest Received": "Interest",
            "Broker Interest Paid": "Interest",
            "Withholding Tax": "Tax",
            "Other Fees": "Fee",
            "Payment In Lieu Of Dividends": "Dividend",  # Stock loan dividends
            "Bond Interest Received": "Interest",
            "Bond Interest Paid": "Interest",
        }

        # Types we explicitly skip (handled elsewhere or not cash-affecting)
        skip_types = {
            "Dividends",  # Handled by extract_dividends
            "Deposits/Withdrawals",  # Handled by extract_transfers
            "Deposits & Withdrawals",
            "Deposits",
            "Withdrawals",
        }

        # Track unknown types for logging
        unknown_types: dict[str, int] = {}

        try:
            for stmt in root.findall(".//FlexStatement"):
                for cash_txn in stmt.findall(".//CashTransaction"):
                    try:
                        ibkr_type = cash_txn.get("type", "")

                        # Skip types handled elsewhere
                        if ibkr_type in skip_types:
                            continue

                        # Only process types we know about
                        if ibkr_type not in type_mapping:
                            # Log unknown types so we can add them
                            unknown_types[ibkr_type] = unknown_types.get(ibkr_type, 0) + 1
                            continue

                        date_str = cash_txn.get("dateTime", "")
                        amount = cash_txn.get("amount", "0")
                        currency = cash_txn.get("currency", "USD")
                        description = cash_txn.get("description", "")
                        account_id = cash_txn.get("accountId", "")
                        symbol = cash_txn.get("symbol", "")  # May be empty for interest

                        if not date_str:
                            logger.warning(f"Skipping {ibkr_type} without date")
                            continue

                        # Parse date (format: YYYYMMDD;HHMMSS or YYYYMMDD)
                        if ";" in date_str:
                            date_part = date_str.split(";")[0]
                            txn_date = datetime.strptime(date_part, "%Y%m%d").date()
                        else:
                            txn_date = datetime.strptime(date_str[:8], "%Y%m%d").date()

                        amount_decimal = Decimal(str(amount))

                        # Deduplicate: key is (date, ibkr_type, currency, amount)
                        dedup_key = (txn_date, ibkr_type, currency, str(amount_decimal))
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        transactions.append(
                            {
                                "date": txn_date,
                                "type": type_mapping[ibkr_type],
                                "ibkr_type": ibkr_type,
                                "amount": amount_decimal,  # Keep sign (negative for taxes/fees)
                                "currency": currency,
                                "symbol": symbol,  # Related stock symbol if applicable
                                "description": description,
                                "account_id": account_id,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing cash transaction: {str(e)}")
                        continue

            # Warn about unknown types so they can be added to type_mapping
            if unknown_types:
                logger.warning(
                    f"Found {sum(unknown_types.values())} CashTransactions with unknown types "
                    f"(not imported): {unknown_types}. Consider adding to type_mapping."
                )

            logger.info(f"Extracted {len(transactions)} other cash transactions (deduplicated)")
            return transactions

        except Exception as e:
            logger.error(f"Error extracting other cash transactions: {str(e)}")
            return []

    @staticmethod
    def get_cash_transaction_types(root: ET.Element) -> dict[str, int]:
        """
        Analyze what CashTransaction types exist in the Flex Query.
        Useful for identifying missing parsers.

        Returns:
            Dictionary with transaction type counts
        """
        type_counts = {}

        try:
            for stmt in root.findall(".//FlexStatement"):
                for cash_txn in stmt.findall(".//CashTransaction"):
                    txn_type = cash_txn.get("type", "UNKNOWN")
                    type_counts[txn_type] = type_counts.get(txn_type, 0) + 1

            logger.info(f"Found CashTransaction types: {type_counts}")
            return type_counts

        except Exception as e:
            logger.error(f"Error analyzing cash transaction types: {str(e)}")
            return {}

    @staticmethod
    def get_all_section_types(root: ET.Element) -> dict[str, int]:
        """
        Analyze what XML sections exist in the Flex Query.
        Helps identify what data is available.

        Returns:
            Dictionary with section names and counts
        """
        section_counts = {}

        try:
            for stmt in root.findall(".//FlexStatement"):
                for child in stmt:
                    section_name = child.tag
                    section_counts[section_name] = section_counts.get(section_name, 0) + 1

            logger.info(f"Found Flex Query sections: {section_counts}")
            return section_counts

        except Exception as e:
            logger.error(f"Error analyzing sections: {str(e)}")
            return {}

    @staticmethod
    def extract_statement_of_funds_summary(root: ET.Element) -> dict[str, dict[str, Decimal]]:
        """
        Extract Statement of Funds summary by currency and activity code.

        The Statement of Funds is IBKR's authoritative cash accounting that shows
        all cash movements with starting/ending balances. This can be used to
        validate our transaction-based reconstruction.

        Returns:
            Dictionary: {currency: {activity_code: total_amount}}
            Example: {
                "USD": {
                    "STARTING": Decimal("0"),
                    "DEPOSIT": Decimal("2500"),
                    "DIVIDEND": Decimal("169.41"),
                    "TRADE": Decimal("-31351.51"),
                    "FOREX": Decimal("38777.39"),
                    "INTEREST": Decimal("30.11"),
                    "TAX": Decimal("-26.08"),
                    "FEE": Decimal("-0.38"),
                    "ENDING": Decimal("10098.94")
                }
            }
        """
        summary: dict[str, dict[str, Decimal]] = {}

        # Map IBKR activity codes to our normalized codes
        activity_code_mapping = {
            # Starting/Ending balances
            "Starting Balance": "STARTING",
            "Ending Balance": "ENDING",
            "Ending Settled Cash": "ENDING",
            # Deposits/Withdrawals
            "Deposits & Withdrawals": "DEPOSIT",
            "Deposits/Withdrawals": "DEPOSIT",
            "Deposits": "DEPOSIT",
            "Withdrawals": "DEPOSIT",  # Will be negative
            "Electronic Fund Transfer": "DEPOSIT",
            # Trading
            "Trades": "TRADE",
            "Stock Trades": "TRADE",
            "Option Trades": "TRADE",
            "Commissions": "COMMISSION",
            # Dividends
            "Dividends": "DIVIDEND",
            "Payment In Lieu Of Dividends": "DIVIDEND",
            # Forex
            "Forex": "FOREX",
            "FX Translation G/L": "FOREX",
            # Interest
            "Broker Interest Received": "INTEREST",
            "Broker Interest Paid": "INTEREST",
            "Bond Interest Received": "INTEREST",
            "Bond Interest Paid": "INTEREST",
            "Credit Interest": "INTEREST",
            "Debit Interest": "INTEREST",
            # Tax
            "Withholding Tax": "TAX",
            # Fees
            "Other Fees": "FEE",
            "ADR Fees": "FEE",
        }

        try:
            for stmt in root.findall(".//FlexStatement"):
                # Look for StmtFunds section (Statement of Funds)
                for funds_line in stmt.findall(".//StmtFunds"):
                    try:
                        currency = funds_line.get("currency", "BASE")
                        activity = funds_line.get("activityDescription", "")
                        amount_str = funds_line.get("amount", "0")

                        if not currency:
                            continue

                        # Initialize currency dict if needed
                        if currency not in summary:
                            summary[currency] = {}

                        # Map to normalized activity code
                        normalized_activity = activity_code_mapping.get(
                            activity, f"OTHER:{activity}"
                        )

                        # Parse amount
                        amount = Decimal(str(amount_str))

                        # Add to summary (some activities may appear multiple times)
                        if normalized_activity in summary[currency]:
                            summary[currency][normalized_activity] += amount
                        else:
                            summary[currency][normalized_activity] = amount

                    except Exception as e:
                        logger.error(f"Error parsing StmtFunds line: {e}")
                        continue

                # Also try alternative StatementOfFunds element
                for funds_line in stmt.findall(".//StatementOfFundsLine"):
                    try:
                        currency = funds_line.get("currency", "BASE")
                        activity = funds_line.get("activityCode", "")
                        if not activity:
                            activity = funds_line.get("activityDescription", "")
                        amount_str = funds_line.get("amount", "0")

                        if not currency:
                            continue

                        if currency not in summary:
                            summary[currency] = {}

                        normalized_activity = activity_code_mapping.get(
                            activity, f"OTHER:{activity}"
                        )

                        amount = Decimal(str(amount_str))

                        if normalized_activity in summary[currency]:
                            summary[currency][normalized_activity] += amount
                        else:
                            summary[currency][normalized_activity] = amount

                    except Exception as e:
                        logger.error(f"Error parsing StatementOfFundsLine: {e}")
                        continue

            if summary:
                logger.info(
                    f"Extracted Statement of Funds summary for currencies: {list(summary.keys())}"
                )
            else:
                logger.info("No Statement of Funds section found in XML")

            return summary

        except Exception as e:
            logger.error(f"Error extracting Statement of Funds: {e}")
            return {}

    @staticmethod
    def extract_fx_positions(root: ET.Element) -> dict[str, Decimal]:
        """
        Extract FxPositions (cash balances by currency) from FlexQueryResponse.

        This is IBKR's authoritative cash position at report time.

        Returns:
            Dictionary: {currency: balance}
            Example: {"USD": Decimal("10098.94"), "ILS": Decimal("5.23")}
        """
        positions: dict[str, Decimal] = {}

        try:
            for stmt in root.findall(".//FlexStatement"):
                for fx_pos in stmt.findall(".//FxPosition"):
                    try:
                        currency = fx_pos.get("fxCurrency", "")
                        quantity_str = fx_pos.get("quantity", "0")

                        if not currency:
                            continue

                        quantity = Decimal(str(quantity_str))

                        # Handle multiple entries for same currency (shouldn't happen but be safe)
                        if currency in positions:
                            positions[currency] += quantity
                        else:
                            positions[currency] = quantity

                    except Exception as e:
                        logger.error(f"Error parsing FxPosition: {e}")
                        continue

            logger.info(f"Extracted FxPositions: {positions}")
            return positions

        except Exception as e:
            logger.error(f"Error extracting FxPositions: {e}")
            return {}

    @staticmethod
    def extract_statement_of_funds_balances(root: ET.Element) -> list[dict]:
        """
        Extract daily cash balances from StatementOfFunds (StmtFunds section).

        This provides IBKR's authoritative daily running cash balances by currency.
        Use this for historical cash balance reconstruction instead of summing transactions.

        Returns:
            List of daily balance records:
            [
                {
                    "date": date(2024, 5, 20),
                    "currency": "USD",
                    "balance": Decimal("1000.50"),
                    "activity": "Deposit"
                },
                ...
            ]
        """
        balances: list[dict] = []
        seen_keys: set[tuple] = set()

        try:
            for stmt in root.findall(".//FlexStatement"):
                stmt_funds = stmt.find(".//StmtFunds")
                if stmt_funds is None:
                    continue

                for line in stmt_funds.findall("StatementOfFundsLine"):
                    try:
                        date_str = line.get("date", "")
                        currency = line.get("currency", "")
                        balance_str = line.get("balance", "0")
                        activity = line.get("activityDescription", "")

                        if not date_str or not currency:
                            continue

                        # Parse date (YYYYMMDD format)
                        date_obj = datetime.strptime(date_str, "%Y%m%d").date()
                        balance = Decimal(str(balance_str))

                        # Deduplication: Use (date, currency) as key
                        # Keep only the last entry for each date+currency
                        key = (date_obj, currency)

                        # Remove previous entry with same key if exists
                        balances = [b for b in balances if (b["date"], b["currency"]) != key]

                        balances.append(
                            {
                                "date": date_obj,
                                "currency": currency,
                                "balance": balance,
                                "activity": activity,
                            }
                        )

                    except Exception as e:
                        logger.error(f"Error parsing StatementOfFundsLine: {e}")
                        continue

            # Sort by date and currency
            balances.sort(key=lambda x: (x["date"], x["currency"]))

            logger.info(
                f"Extracted {len(balances)} daily cash balance records from StmtFunds "
                f"({min((b['date'] for b in balances), default='N/A')} to "
                f"{max((b['date'] for b in balances), default='N/A')})"
            )
            return balances

        except Exception as e:
            logger.error(f"Error extracting StatementOfFunds balances: {e}")
            return []

    @staticmethod
    def analyze_fx_transactions(root: ET.Element) -> list[dict]:
        """
        Analyze forex transaction structure (diagnostic).
        Returns sample forex transactions with all attributes.
        """
        samples = []

        try:
            for stmt in root.findall(".//FlexStatement"):
                for fx_txn in stmt.findall(".//FxTransaction"):
                    # Get all attributes
                    sample = {}
                    for key, value in fx_txn.attrib.items():
                        sample[key] = value

                    samples.append(sample)

                    # Limit to first 3 samples
                    if len(samples) >= 3:
                        break

                if len(samples) >= 3:
                    break

            logger.info(f"Sample FxTransaction attributes: {samples}")
            return samples

        except Exception as e:
            logger.error(f"Error analyzing forex transactions: {str(e)}")
            return []

    @staticmethod
    def extract_forex_transactions(root: ET.Element) -> list[dict]:
        """
        Extract forex (currency conversion) transactions from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of forex transaction dictionaries
        """
        forex_txns = []
        seen_keys = set()  # For deduplication

        try:
            for stmt in root.findall(".//FlexStatement"):
                for fx_txn in stmt.findall(".//FxTransaction"):
                    try:
                        date_str = fx_txn.get("dateTime", "")
                        quantity = fx_txn.get("quantity", "0")
                        proceeds = fx_txn.get("proceeds", "0")
                        cost = fx_txn.get("cost", "0")
                        realized_pl = fx_txn.get("realizedPL", "0")
                        from_currency = fx_txn.get("fxCurrency", "")
                        to_currency = fx_txn.get("functionalCurrency", "USD")
                        description = fx_txn.get("activityDescription", "")
                        account_id = fx_txn.get("accountId", "")

                        if not date_str or not from_currency:
                            logger.warning("Skipping forex transaction without date or currency")
                            continue

                        # Parse date (format: YYYYMMDD or YYYYMMDD;HHMMSS)
                        if ";" in date_str:
                            date_part = date_str.split(";")[0]
                            txn_date = datetime.strptime(date_part, "%Y%m%d").date()
                        else:
                            txn_date = datetime.strptime(date_str[:8], "%Y%m%d").date()

                        quantity_decimal = Decimal(str(quantity))
                        proceeds_decimal = Decimal(str(proceeds))
                        cost_decimal = Decimal(str(cost))
                        realized_pl_decimal = Decimal(str(realized_pl))

                        # Skip stock trade settlements (description starts with "STK:")
                        # These are already captured as Trade.netCash
                        if description.startswith("STK:"):
                            continue

                        # Skip cash deposits/withdrawals that are NOT forex conversions
                        # Only entries starting with "CASH:" are actual forex conversions
                        # (e.g., "CASH: -1500 USD.CAD" means convert 1500 USD to CAD)
                        # Skip entries like:
                        # - "Net cash activity" = ILS balance adjustments
                        # - "CASH RECEIPTS / ELECTRONIC FUND TRANSFERS" = ILS deposits
                        if not description.startswith("CASH:"):
                            continue

                        # Deduplication check using (date, from_currency, to_currency, from_amount, to_amount)
                        from_amt = abs(quantity_decimal)
                        to_amt = (
                            abs(proceeds_decimal) if quantity_decimal < 0 else abs(quantity_decimal)
                        )
                        dedup_key = (
                            txn_date,
                            from_currency if quantity_decimal < 0 else to_currency,
                            to_currency if quantity_decimal < 0 else from_currency,
                            from_amt,
                            to_amt,
                        )

                        if dedup_key in seen_keys:
                            logger.debug(f"Skipping duplicate forex transaction: {dedup_key}")
                            continue
                        seen_keys.add(dedup_key)

                        # Determine conversion direction
                        # Negative quantity = sold from_currency, bought to_currency
                        # Positive quantity = bought from_currency, sold to_currency
                        if quantity_decimal < 0:
                            # Sold from_currency (e.g., ILS) to buy to_currency (e.g., USD)
                            forex_txns.append(
                                {
                                    "date": txn_date,
                                    "from_currency": from_currency,
                                    "to_currency": to_currency,
                                    "from_amount": abs(quantity_decimal),
                                    "to_amount": abs(proceeds_decimal),
                                    "realized_pl": realized_pl_decimal,
                                    "description": description
                                    or f"Convert {from_currency} to {to_currency}",
                                    "account_id": account_id,
                                }
                            )
                        else:
                            # Bought from_currency with to_currency
                            forex_txns.append(
                                {
                                    "date": txn_date,
                                    "from_currency": to_currency,
                                    "to_currency": from_currency,
                                    "from_amount": abs(cost_decimal),
                                    "to_amount": abs(quantity_decimal),
                                    "realized_pl": realized_pl_decimal,
                                    "description": description
                                    or f"Convert {to_currency} to {from_currency}",
                                    "account_id": account_id,
                                }
                            )

                    except Exception as e:
                        logger.error(f"Error parsing forex transaction: {str(e)}")
                        continue

            logger.info(f"Extracted {len(forex_txns)} forex transactions")
            return forex_txns

        except Exception as e:
            logger.error(f"Error extracting forex transactions: {str(e)}")
            return []

    @staticmethod
    def extract_cash_balances(root: ET.Element) -> list[dict]:
        """
        Extract cash balances by currency from FlexQueryResponse.

        Args:
            root: XML root element

        Returns:
            List of cash balance dictionaries
        """
        balances = []

        try:
            for stmt in root.findall(".//FlexStatement"):
                account_id = stmt.get("accountId", "")

                for cash_report in stmt.findall(".//CashReport"):
                    try:
                        currency = cash_report.get("currency", "USD")
                        ending_cash = cash_report.get("endingCash", "0")

                        balance_value = Decimal(str(ending_cash))

                        # Only include non-zero balances
                        if balance_value != 0:
                            balances.append(
                                {
                                    "currency": currency,
                                    "balance": balance_value,
                                    "account_id": account_id,
                                }
                            )

                    except Exception as e:
                        logger.error(f"Error parsing cash balance: {str(e)}")
                        continue

            logger.info(f"Extracted {len(balances)} cash balances")
            return balances

        except Exception as e:
            logger.error(f"Error extracting cash balances: {str(e)}")
            return []

    @staticmethod
    def normalize_symbol(
        ibkr_symbol: str, asset_category: str, listing_exchange: str = ""
    ) -> dict[str, any]:
        """
        Convert IBKR symbols to Yahoo Finance format.

        Args:
            ibkr_symbol: IBKR ticker symbol
            asset_category: IBKR asset category (STK, OPT, FUT, etc.)
            listing_exchange: Exchange code (NYSE, NASDAQ, LSE, etc.)

        Returns:
            Dictionary with yf_symbol, original_symbol, and needs_validation flag
        """
        # US Stocks (NYSE, NASDAQ, ARCA): usually identical
        if asset_category == "STK" and listing_exchange in [
            "NYSE",
            "NASDAQ",
            "ARCA",
            "AMEX",
            "BATS",
        ]:
            return {
                "yf_symbol": ibkr_symbol,
                "original_symbol": ibkr_symbol,
                "needs_validation": False,
            }

        # International stocks: may need exchange suffix
        exchange_map = {
            "LSE": ".L",  # London Stock Exchange
            "TSE": ".TO",  # Toronto Stock Exchange
            "TASE": ".TA",  # Tel Aviv Stock Exchange
            "FWB": ".F",  # Frankfurt
            "SWB": ".SG",  # Stuttgart
            "XETRA": ".DE",  # XETRA (Germany)
            "AEB": ".AS",  # Amsterdam
            "SBF": ".PA",  # Paris
            "BM": ".MC",  # Madrid
            "MIB": ".MI",  # Milan
            "SFB": ".SW",  # Swiss
            "ASX": ".AX",  # Australian
            "HKSE": ".HK",  # Hong Kong
            "TSE.JPN": ".T",  # Tokyo
            "KSE": ".KS",  # Korea
        }

        if asset_category == "STK" and listing_exchange in exchange_map:
            suffix = exchange_map[listing_exchange]
            yf_symbol = ibkr_symbol

            # TSE (Toronto) special handling:
            # IBKR uses periods (e.g., U.UN) but Yahoo Finance uses hyphens (e.g., U-UN)
            # This applies to unit trusts and other Canadian securities
            if listing_exchange == "TSE" and "." in ibkr_symbol:
                yf_symbol = ibkr_symbol.replace(".", "-")

            return {
                "yf_symbol": f"{yf_symbol}{suffix}",
                "original_symbol": ibkr_symbol,
                "needs_validation": True,
            }

        # Default: use as-is but flag for validation
        return {"yf_symbol": ibkr_symbol, "original_symbol": ibkr_symbol, "needs_validation": True}

    @staticmethod
    def map_asset_class(ibkr_category: str, symbol: str | None = None) -> str:
        """Map IBKR asset categories to our asset classes."""
        return map_ibkr_asset_class(ibkr_category, symbol)
