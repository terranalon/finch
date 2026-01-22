"""IBKR Web API JSON parser."""

import logging
from datetime import datetime
from decimal import Decimal

from app.services.asset_type_detector import map_ibkr_asset_class

logger = logging.getLogger(__name__)


class IBKRWebParser:
    """Parser for IBKR Client Portal Web API JSON responses."""

    @staticmethod
    def parse_positions(positions_data: list[dict]) -> list[dict]:
        """
        Parse positions from Web API response.

        Args:
            positions_data: List of position dictionaries from API

        Returns:
            List of normalized position dictionaries
        """
        parsed_positions = []

        for pos in positions_data:
            try:
                # Extract key fields
                symbol = pos.get("contractDesc", pos.get("ticker", ""))
                conid = pos.get("conid")  # Contract ID
                position = pos.get("position", 0)
                mkt_value = pos.get("mktValue", 0)
                avg_cost = pos.get("avgCost", 0)
                asset_class = pos.get("assetClass", "STK")
                currency = pos.get("currency", "USD")

                if not symbol or position == 0:
                    continue

                # Normalize symbol
                symbol_info = IBKRWebParser.normalize_symbol(symbol, asset_class)

                # Calculate cost basis from average cost and position
                cost_basis = abs(Decimal(str(avg_cost)) * Decimal(str(position)))

                parsed_positions.append(
                    {
                        "symbol": symbol_info["yf_symbol"],
                        "original_symbol": symbol_info["original_symbol"],
                        "description": pos.get("contractDesc", symbol),
                        "asset_category": asset_class,
                        "asset_class": IBKRWebParser.map_asset_class(
                            asset_class, symbol_info["yf_symbol"]
                        ),
                        "quantity": Decimal(str(position)),
                        "cost_basis": cost_basis,
                        "market_value": Decimal(str(mkt_value)) if mkt_value else None,
                        "currency": currency,
                        "conid": conid,
                        "needs_validation": symbol_info["needs_validation"],
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing position: {str(e)}")
                continue

        logger.info(f"Parsed {len(parsed_positions)} positions")
        return parsed_positions

    @staticmethod
    def parse_trades(trades_data: list[dict]) -> list[dict]:
        """
        Parse trades from Web API response.

        Args:
            trades_data: List of trade dictionaries from API

        Returns:
            List of normalized transaction dictionaries
        """
        parsed_trades = []

        for trade in trades_data:
            try:
                symbol = trade.get("symbol", "")
                side = trade.get("side", "")  # BUY or SELL
                quantity = trade.get("size", 0)
                price = trade.get("price", 0)
                commission = trade.get("commission", 0)
                trade_time = trade.get("trade_time", "")
                asset_class = trade.get("asset_class", "STK")
                currency = trade.get("currency", "USD")

                if not symbol:
                    continue

                # Parse trade date
                try:
                    # Trade time format: "20231215;093000"
                    if ";" in trade_time:
                        date_part = trade_time.split(";")[0]
                        trade_date = datetime.strptime(date_part, "%Y%m%d").date()
                    else:
                        trade_date = datetime.now().date()
                except:
                    trade_date = datetime.now().date()

                # Normalize symbol
                symbol_info = IBKRWebParser.normalize_symbol(symbol, asset_class)

                # Map side to transaction type
                transaction_type = "Buy" if side == "BUY" or side == "B" else "Sell"

                parsed_trades.append(
                    {
                        "symbol": symbol_info["yf_symbol"],
                        "original_symbol": symbol_info["original_symbol"],
                        "description": trade.get("description", symbol),
                        "asset_category": asset_class,
                        "asset_class": IBKRWebParser.map_asset_class(
                            asset_class, symbol_info["yf_symbol"]
                        ),
                        "trade_date": trade_date,
                        "transaction_type": transaction_type,
                        "quantity": abs(Decimal(str(quantity))),
                        "price": abs(Decimal(str(price))),
                        "commission": abs(Decimal(str(commission))),
                        "currency": currency,
                        "needs_validation": symbol_info["needs_validation"],
                    }
                )

            except Exception as e:
                logger.error(f"Error parsing trade: {str(e)}")
                continue

        logger.info(f"Parsed {len(parsed_trades)} trades")
        return parsed_trades

    @staticmethod
    def parse_ledger(ledger_data: dict) -> list[dict]:
        """
        Parse cash balances from ledger.

        Args:
            ledger_data: Ledger dictionary from API

        Returns:
            List of cash balance dictionaries
        """
        balances = []

        try:
            # Ledger has BASE (base currency) and other currencies
            for currency, data in ledger_data.items():
                if isinstance(data, dict):
                    cash_balance = data.get("cashbalance", 0)
                    if cash_balance != 0:
                        balances.append(
                            {"currency": currency, "balance": Decimal(str(cash_balance))}
                        )

        except Exception as e:
            logger.error(f"Error parsing ledger: {str(e)}")

        logger.info(f"Parsed {len(balances)} cash balances")
        return balances

    @staticmethod
    def normalize_symbol(symbol: str, asset_class: str) -> dict[str, any]:
        """
        Convert IBKR symbols to Yahoo Finance format.

        Args:
            symbol: IBKR symbol
            asset_class: Asset class (STK, OPT, etc.)

        Returns:
            Dictionary with yf_symbol, original_symbol, and needs_validation flag
        """
        # For now, use symbol as-is for US stocks
        # Can be enhanced later with exchange mapping
        if asset_class == "STK":
            return {
                "yf_symbol": symbol,
                "original_symbol": symbol,
                "needs_validation": True,  # Always validate with Yahoo Finance
            }

        return {"yf_symbol": symbol, "original_symbol": symbol, "needs_validation": True}

    @staticmethod
    def map_asset_class(ibkr_category: str, symbol: str | None = None) -> str:
        """Map IBKR asset classes to our asset classes."""
        return map_ibkr_asset_class(ibkr_category, symbol)
