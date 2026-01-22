"""Bit2C API client for fetching account data.

Implements Bit2C's HMAC-SHA512 authentication and provides methods
for fetching balances and account history.
"""

import base64
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

import httpx

from app.services.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.bit2c_constants import ASSET_NAME_MAP
from app.services.bit2c_constants import TRADING_PAIRS as TRADING_PAIRS_MAP
from app.services.coingecko_client import CoinGeckoClient

logger = logging.getLogger(__name__)

# Base URL for Bit2C API
BIT2C_API_URL = "https://bit2c.co.il"

# Supported trading pairs
TRADING_PAIRS = ["BtcNis", "EthNis", "LtcNis", "UsdcNis"]


@dataclass
class Bit2CCredentials:
    """Bit2C API credentials."""

    api_key: str
    api_secret: str


class Bit2CAPIError(Exception):
    """Exception raised for Bit2C API errors."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class Bit2CClient:
    """Client for interacting with Bit2C REST API.

    Implements HMAC-SHA512 authentication using uppercase secret.

    Usage:
        client = Bit2CClient(Bit2CCredentials(api_key="...", api_secret="..."))
        balances = client.get_balance()
        history = client.get_account_history(from_date, to_date)
    """

    def __init__(
        self,
        credentials: Bit2CCredentials,
        coingecko_client: CoinGeckoClient | None = None,
    ):
        """Initialize Bit2C client with credentials.

        Args:
            credentials: Bit2C API credentials
            coingecko_client: Optional CoinGecko client for fetching deposit prices.
                             If not provided, one will be created lazily when needed.
        """
        self.api_key = credentials.api_key
        self.api_secret = credentials.api_secret.upper()
        self._nonce_offset = 0
        self._coingecko_client = coingecko_client

    def _get_coingecko_client(self) -> CoinGeckoClient:
        """Get or create CoinGecko client for price lookups."""
        if self._coingecko_client is None:
            self._coingecko_client = CoinGeckoClient()
        return self._coingecko_client

    def _get_deposit_price(self, symbol: str, deposit_date: date) -> Decimal | None:
        """Fetch historical price for deposit cost basis.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            deposit_date: Date of deposit

        Returns:
            Price per unit in USD, or None if unavailable
        """
        try:
            client = self._get_coingecko_client()
            return client.get_historical_price(symbol, deposit_date, vs_currency="usd")
        except Exception as e:
            logger.warning("Could not fetch price for %s on %s: %s", symbol, deposit_date, e)
            return None

    def _get_nonce(self) -> int:
        """Generate always-increasing nonce value.

        Uses Unix timestamp (seconds) plus an offset to ensure nonce is always
        higher than any previously used values. Bit2C tracks the highest nonce
        per API key and rejects requests with lower nonces.
        """
        # Use Unix timestamp + offset for reliability
        # Adding 10000 provides buffer for any clock drift or previous testing
        nonce = int(time.time()) + 10000 + self._nonce_offset
        self._nonce_offset += 1
        return nonce

    def _sign_request(self, params: str) -> str:
        """Generate HMAC-SHA512 signature for request.

        Signature = base64(HMAC-SHA512(params, secret.upper()))
        """
        secret_bytes = self.api_secret.encode("utf-8")
        message_bytes = params.encode("utf-8")
        signature = hmac.new(secret_bytes, message_bytes, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode("utf-8")

    def _private_request(
        self,
        endpoint: str,
        data: dict | None = None,
        method: str = "GET",
        timeout: float = 30.0,
    ) -> dict | list:
        """Make authenticated private API request.

        Args:
            endpoint: API endpoint path (e.g., "/Account/Balance")
            data: Request parameters
            method: HTTP method (GET or POST)
            timeout: Request timeout in seconds

        Returns:
            API response (dict or list)

        Raises:
            Bit2CAPIError: If API returns errors

        Note:
            Bit2C requires the signature to be computed on raw (non-URL-encoded)
            parameter strings. Date parameters like "01/01/2020 00:00:00.000"
            must NOT be URL-encoded before signing.
        """
        url = BIT2C_API_URL + endpoint

        # Build request data with nonce
        request_data = data.copy() if data else {}
        request_data["nonce"] = self._get_nonce()

        # CRITICAL: Build params string WITHOUT URL encoding for signing
        # Bit2C expects raw values like "fromTime=01/01/2020 00:00:00.000"
        # not URL-encoded values like "fromTime=01%2F01%2F2020+00%3A00%3A00.000"
        params_string = "&".join(f"{k}={v}" for k, v in request_data.items())

        # Sign the raw params string
        signature = self._sign_request(params_string)

        headers = {
            "key": self.api_key,
            "sign": signature,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    # Use raw params in URL (httpx will handle necessary encoding)
                    response = client.get(f"{url}?{params_string}", headers=headers)
                else:
                    response = client.post(url, data=request_data, headers=headers)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Bit2C API HTTP error: {e}")
            raise Bit2CAPIError(f"HTTP error: {e}") from e

        # Check for API errors
        if isinstance(result, dict) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Bit2C API error: {error_msg}")
            raise Bit2CAPIError(error_msg)

        return result

    def _parse_pair(self, pair: str) -> tuple[str, str]:
        """Parse trading pair into symbol and currency.

        Args:
            pair: Trading pair (e.g., "BtcNis")

        Returns:
            Tuple of (symbol, currency)
        """
        return TRADING_PAIRS_MAP.get(pair, (pair, "ILS"))

    def _parse_bit2c_datetime(self, date_str: str) -> datetime | None:
        """Parse Bit2C datetime format.

        Supports multiple formats:
        - "dd/MM/yy HH:mm" (OrderHistory API response)
        - "dd/MM/yyyy HH:mm:ss.fff" (AccountHistory API response)
        - "dd/MM/yyyy HH:mm:ss" (alternative)
        """
        if not date_str:
            return None

        formats = [
            "%d/%m/%y %H:%M",  # OrderHistory format: "01/03/24 17:05"
            "%d/%m/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse Bit2C datetime: {date_str}")
        return None

    def get_balance(self) -> dict[str, Decimal]:
        """Get current account balances.

        Returns:
            Dictionary of asset -> balance (normalized symbols)
        """
        result = self._private_request("/Account/Balance")

        balances = {}
        supported_assets = ("NIS", "BTC", "ETH", "LTC", "USDC")

        for asset in supported_assets:
            balance = result.get(asset, 0)
            if balance and Decimal(str(balance)) > 0:
                symbol = ASSET_NAME_MAP.get(asset, asset)
                balances[symbol] = Decimal(str(balance))

        return balances

    def get_order_history(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        pair: str | None = None,
    ) -> list[dict]:
        """Get order history (trades) for a specific pair.

        Note: Bit2C has a 100-day limit on date ranges. Use get_all_order_history()
        for longer periods which handles chunking automatically.

        Args:
            from_date: Start date filter
            to_date: End date filter
            pair: Trading pair (e.g., "BtcNis"). Required by API.

        Returns:
            List of trade records
        """
        data = {}

        if from_date:
            data["fromTime"] = from_date.strftime("%d/%m/%Y %H:%M:%S.000")
        if to_date:
            data["toTime"] = to_date.strftime("%d/%m/%Y %H:%M:%S.999")
        if pair:
            data["pair"] = pair

        result = self._private_request("/Order/OrderHistory", data)

        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if result.get("error"):
                logger.warning(f"Bit2C OrderHistory error: {result.get('error')}")
                return []
            return result.get("Trades", [])
        return []

    def get_all_order_history(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict]:
        """Get complete order history across all pairs with automatic chunking.

        Bit2C API has a 100-day limit on date ranges, so this method automatically
        chunks requests into 90-day periods and queries all supported trading pairs.

        Args:
            from_date: Start date (defaults to 2018-01-01 if not specified)
            to_date: End date (defaults to today if not specified)

        Returns:
            List of all trade records across all pairs
        """
        from datetime import timedelta

        # Default date range
        if not from_date:
            from_date = datetime(2018, 1, 1)
        if not to_date:
            to_date = datetime.now()

        all_trades: list[dict] = []
        chunk_days = 90  # Stay under 100-day limit

        for pair in TRADING_PAIRS:
            current = from_date
            pair_count = 0

            while current < to_date:
                chunk_end = min(current + timedelta(days=chunk_days), to_date)

                try:
                    trades = self.get_order_history(current, chunk_end, pair)
                    if trades:
                        all_trades.extend(trades)
                        pair_count += len(trades)
                except Bit2CAPIError as e:
                    logger.warning(
                        f"Error fetching {pair} history for {current} - {chunk_end}: {e}"
                    )

                current = chunk_end + timedelta(days=1)

            if pair_count > 0:
                logger.info(f"Fetched {pair_count} trades for {pair}")

        logger.info(f"Total trades fetched from Bit2C: {len(all_trades)}")
        return all_trades

    def get_funds_history(self) -> list[dict]:
        """Get deposit and withdrawal history from FundsHistory endpoint.

        This endpoint returns all fund movements including:
        - Deposits (action=2): NIS and crypto deposits
        - Withdrawals (action=3): NIS and crypto withdrawals
        - Fee withdrawals (action=4): Withdrawal fees

        Returns:
            List of fund movement records
        """
        result = self._private_request("/AccountAPI/FundsHistory.json")

        if isinstance(result, list):
            logger.info(f"Fetched {len(result)} funds history records from Bit2C")
            return result
        elif isinstance(result, dict):
            if result.get("error"):
                logger.warning(f"Bit2C FundsHistory error: {result.get('error')}")
                return []
        return []

    def _parse_funds_record(
        self, record: dict, fee_quantity: Decimal = Decimal("0")
    ) -> tuple[ParsedTransaction | None, ParsedCashTransaction | None]:
        """Parse a funds history record into appropriate transaction type.

        FundsHistory action types:
        - 2: Deposit (ILS or crypto)
        - 3: Withdrawal (ILS or crypto)
        - 4: FeeWithdrawal (withdrawal fee, usually crypto) - handled separately, combined with withdrawal
        - 23: RefundWithdrawal (refunded withdrawal)
        - 24: RefundFeeWithdrawal (refunded withdrawal fee)
        - 26: DepositFee
        - 27: RefundDepositFee
        - 28: CustodyFee (monthly platform fee, crypto or ILS)
        - 31: InterestCredit (interest on ILS balance)

        Args:
            record: Raw funds history record from API
            fee_quantity: Fee amount to include with withdrawals (from matched fee record)

        Returns:
            Tuple of (ParsedTransaction for crypto, ParsedCashTransaction for ILS)
            One will be populated, the other None, based on the asset type.
        """
        action = record.get("action")
        created_str = record.get("created")

        if not created_str:
            return None, None

        record_dt = self._parse_bit2c_datetime(created_str)
        if not record_dt:
            return None, None

        first_coin = record.get("firstCoin", "")
        first_amount = self._parse_decimal(record.get("firstAmount", 0))
        reference = record.get("reference", "")

        # Determine if this is ILS (fiat) or crypto
        is_ils = first_coin == "₪"
        symbol = "ILS" if is_ils else first_coin

        # Map action to transaction type
        # Note: action=4 (Withdrawal Fee) is handled separately and combined with withdrawals
        if action == 2:
            transaction_type = "Deposit"
        elif action == 3:
            transaction_type = "Withdrawal"
        elif action == 23:
            transaction_type = "Refund Withdrawal"
        elif action == 24:
            transaction_type = "Refund Fee"
        elif action == 28:
            transaction_type = "Custody Fee"
        elif action == 31:
            transaction_type = "Interest"
        else:
            # Skip other action types (Buy/Sell are handled by OrderHistory)
            return None, None

        # For ILS (fiat), return ParsedCashTransaction
        if is_ils:
            # ILS amounts: positive for deposits/credits, negative for withdrawals/fees
            if transaction_type in ("Deposit", "Refund Withdrawal", "Refund Fee", "Interest"):
                amount = abs(first_amount)
            else:
                amount = -abs(first_amount) if first_amount > 0 else first_amount
            cash_txn = ParsedCashTransaction(
                date=record_dt.date(),
                transaction_type=transaction_type,
                amount=amount,
                currency="ILS",
                notes=f"Bit2C {transaction_type} - {reference}",
                raw_data=record,
            )
            return None, cash_txn

        # For crypto, return ParsedTransaction with quantity for 8-decimal precision
        entry_date = record_dt.date()

        if transaction_type == "Deposit":
            # Crypto deposit - positive quantity, fetch historical price for cost basis
            quantity = abs(first_amount)
            price = self._get_deposit_price(symbol, entry_date)
            # Calculate fiat value if we have a price
            fiat_amount = quantity * price if price else None
            crypto_txn = ParsedTransaction(
                trade_date=entry_date,
                symbol=symbol,
                transaction_type="Deposit",
                quantity=quantity,
                price_per_unit=price,  # Historical price for cost basis
                amount=fiat_amount,  # Fiat value of deposit (for UI display)
                fees=Decimal("0"),
                currency="USD" if price else symbol,
                notes=f"Bit2C crypto deposit - {reference}",
                raw_data=record,
            )
        elif transaction_type == "Withdrawal":
            # Crypto withdrawal - quantity is the net amount withdrawn (negative for outflow)
            # fee_quantity is the additional fee deducted from account (stored separately)
            quantity = first_amount if first_amount < 0 else -abs(first_amount)
            crypto_txn = ParsedTransaction(
                trade_date=entry_date,
                symbol=symbol,
                transaction_type="Withdrawal",
                quantity=quantity,  # Net withdrawal amount (not including fee)
                price_per_unit=None,
                amount=None,  # No fiat value for crypto withdrawals
                fees=fee_quantity,  # Fee in crypto units (note: may lose precision due to Numeric(15,2))
                currency=symbol,  # Currency is the crypto itself
                notes=f"Bit2C crypto withdrawal - {reference}" + (f" (fee: {fee_quantity} {symbol})" if fee_quantity else ""),
                raw_data=record,
            )
        elif transaction_type in ("Refund Withdrawal", "Refund Fee"):
            # Refunds - positive quantity
            quantity = abs(first_amount)
            crypto_txn = ParsedTransaction(
                trade_date=entry_date,
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                price_per_unit=None,
                amount=None,  # No fiat value for refunds
                fees=Decimal("0"),
                currency=symbol,  # Currency is the crypto itself
                notes=f"Bit2C {transaction_type.lower()} - {reference}",
                raw_data=record,
            )
        elif transaction_type == "Custody Fee":
            # Custody fee - negative quantity (already negative in API)
            quantity = first_amount if first_amount < 0 else -abs(first_amount)
            crypto_txn = ParsedTransaction(
                trade_date=entry_date,
                symbol=symbol,
                transaction_type="Custody Fee",
                quantity=quantity,
                price_per_unit=None,
                amount=None,  # No fiat value for custody fees
                fees=Decimal("0"),
                currency=symbol,  # Currency is the crypto itself
                notes=f"Bit2C custody fee - {reference}",
                raw_data=record,
            )
        else:
            return None, None

        return crypto_txn, None

    def fetch_all_data(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BrokerImportData:
        """Fetch all account data and return as BrokerImportData.

        Uses OrderHistory endpoint with automatic 90-day chunking to work around
        Bit2C's 100-day limit on date ranges. Queries all supported trading pairs.

        Args:
            start_date: Start date for historical data (defaults to 2018-01-01)
            end_date: End date for historical data (defaults to today)

        Returns:
            BrokerImportData containing all parsed records
        """
        # Convert dates to datetimes for API
        from_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        to_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

        # Fetch balances for positions
        positions: list[ParsedPosition] = []
        try:
            balances = self.get_balance()
            for symbol, quantity in balances.items():
                asset_class = "Cash" if symbol == "ILS" else "Crypto"
                positions.append(
                    ParsedPosition(
                        symbol=symbol,
                        quantity=quantity,
                        currency="ILS" if symbol == "ILS" else symbol,
                        asset_class=asset_class,
                    )
                )
            logger.info(f"Fetched {len(positions)} Bit2C positions")
        except Bit2CAPIError as e:
            logger.error(f"Failed to fetch Bit2C balances: {e}")

        # Fetch order history with automatic chunking
        transactions: list[ParsedTransaction] = []
        cash_transactions: list[ParsedCashTransaction] = []
        all_dates: list[date] = []

        try:
            # Use the new chunking method that handles 100-day limit
            history = self.get_all_order_history(from_datetime, to_datetime)

            for trade in history:
                result = self._parse_trade(trade)
                if result:
                    crypto_txn, settlement_txn = result
                    transactions.append(crypto_txn)
                    # Include Trade Settlements for dual-entry accounting
                    cash_transactions.append(settlement_txn)
                    all_dates.append(crypto_txn.trade_date)

            logger.info(f"Parsed {len(transactions)} Bit2C trades")
        except Bit2CAPIError as e:
            logger.error(f"Failed to fetch Bit2C history: {e}")

        # Fetch funds history (deposits/withdrawals) from FundsHistory endpoint
        try:
            funds_history = self.get_funds_history()
            crypto_count = 0
            cash_count = 0

            # First pass: collect all records and build fee lookup by reference number
            withdrawal_fees: dict[str, dict] = {}  # reference_num -> fee record
            other_records: list[dict] = []

            for record in funds_history:
                action = record.get("action")
                reference = record.get("reference", "")

                if action == 4:  # Withdrawal Fee
                    # Extract reference number from "FEE-BTC:162705" format
                    if ":" in reference:
                        ref_num = reference.split(":")[-1]
                        withdrawal_fees[ref_num] = record
                else:
                    other_records.append(record)

            # Second pass: process records, combining withdrawals with their fees
            for record in other_records:
                action = record.get("action")
                reference = record.get("reference", "")

                # For withdrawals, look up associated fee
                fee_quantity = Decimal("0")
                if action == 3:  # Withdrawal
                    # Extract reference number from "RX162705" format
                    ref_num = reference.replace("RX", "") if reference.startswith("RX") else reference
                    if ref_num in withdrawal_fees:
                        fee_record = withdrawal_fees[ref_num]
                        fee_quantity = abs(self._parse_decimal(fee_record.get("firstAmount", 0)))
                        logger.debug(f"Matched withdrawal {reference} with fee {fee_quantity}")

                crypto_txn, cash_txn = self._parse_funds_record(record, fee_quantity)
                if crypto_txn:
                    transactions.append(crypto_txn)
                    all_dates.append(crypto_txn.trade_date)
                    crypto_count += 1
                if cash_txn:
                    cash_transactions.append(cash_txn)
                    all_dates.append(cash_txn.date)
                    cash_count += 1

            logger.info(f"Parsed {crypto_count} Bit2C crypto deposits/withdrawals")
            logger.info(f"Parsed {cash_count} Bit2C ILS deposits/withdrawals/fees")
        except Bit2CAPIError as e:
            logger.error(f"Failed to fetch Bit2C funds history: {e}")

        # Determine date range
        actual_start = min(all_dates) if all_dates else (start_date or date.today())
        actual_end = max(all_dates) if all_dates else (end_date or date.today())

        return BrokerImportData(
            start_date=actual_start,
            end_date=actual_end,
            positions=positions,
            transactions=transactions,
            cash_transactions=cash_transactions,
            dividends=[],
        )

    def _parse_decimal(self, value: str | int | float | None) -> Decimal:
        """Parse a decimal value, handling comma-formatted strings.

        Bit2C API returns numbers as comma-formatted strings like "216,300" or "-1,025".
        """
        if value is None:
            return Decimal("0")
        # Convert to string, remove commas, then parse
        str_value = str(value).replace(",", "")
        try:
            return Decimal(str_value)
        except Exception:
            return Decimal("0")

    def _parse_trade(self, trade: dict) -> tuple[ParsedTransaction, ParsedCashTransaction] | None:
        """Parse a single trade, returning BOTH crypto txn and Trade Settlement (dual-entry).

        Per CLAUDE.md Broker Integration Guidelines:
        Every trade MUST create TWO transactions:
        1. Asset Transaction: Buy/Sell on the asset holding (crypto)
        2. Trade Settlement: Cash impact on the cash holding (ILS)

        Bit2C OrderHistory API response format:
        - action: 0=Buy, 1=Sell
        - price: Comma-formatted string (e.g., "216,300")
        - firstAmount: Crypto quantity (string decimal)
        - secondAmount: Fiat amount with sign (e.g., "-1,025")
        - feeAmount: Fee in fiat (string)
        - firstCoin: Crypto symbol (e.g., "BTC")
        - reference: Trade reference ID
        - created: Short date format "dd/MM/yy HH:mm"
        """
        created_str = trade.get("created")
        if not created_str:
            return None

        trade_dt = self._parse_bit2c_datetime(created_str)
        if not trade_dt:
            return None

        pair = trade.get("pair", "")
        symbol, currency = self._parse_pair(pair)

        # Prefer firstCoin if available (more reliable)
        if trade.get("firstCoin"):
            symbol = trade["firstCoin"]

        # action: 0=Buy, 1=Sell
        action = trade.get("action", 0)
        is_buy = action == 0
        transaction_type = "Buy" if is_buy else "Sell"

        # Parse values - Bit2C returns comma-formatted strings
        price = self._parse_decimal(trade.get("price", 0))
        quantity = self._parse_decimal(trade.get("firstAmount", 0))  # crypto quantity
        fiat_fee = self._parse_decimal(trade.get("feeAmount", 0))

        # secondAmount is the fiat value WITH FEE ALREADY INCLUDED
        # - For buys: negative (e.g., -2,512.50 = -(2500 + 12.50 fee))
        # - For sells: positive (e.g., 7,462.50 = 7500 - 37.50 fee)
        second_amount = self._parse_decimal(trade.get("secondAmount", 0))

        # Use secondAmount directly as settlement - it already has correct sign and fee
        # Only calculate from price if secondAmount is missing
        if second_amount != 0:
            settlement_amount = second_amount
            # For the crypto transaction amount, use absolute value (before fee)
            total_fiat = abs(second_amount)
        else:
            # Fallback: calculate from price * quantity (rare edge case)
            total_fiat = price * quantity if price > 0 and quantity > 0 else Decimal("0")
            # Calculate settlement with fee
            if is_buy:
                settlement_amount = -(total_fiat + fiat_fee)
            else:
                settlement_amount = total_fiat - fiat_fee

        trade_ref = trade.get("reference", "")

        crypto_txn = ParsedTransaction(
            trade_date=trade_dt.date(),
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_unit=price,
            amount=total_fiat,
            fees=fiat_fee,
            currency=currency,
            notes=f"Bit2C trade - {trade_ref}",
            raw_data=trade,
        )

        # Create Trade Settlement for ILS cash impact (dual-entry accounting)
        settlement_txn = ParsedCashTransaction(
            date=trade_dt.date(),
            transaction_type="Trade Settlement",
            amount=settlement_amount,
            currency="ILS",
            notes=f"Settlement for {symbol} {transaction_type} - {trade_ref}",
            raw_data=trade,
        )

        return crypto_txn, settlement_txn
