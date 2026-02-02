"""Binance API client for fetching account data.

Implements Binance's HMAC-SHA256 authentication with timestamp-based signing.
Provides methods for fetching balances, trade history, and deposit/withdrawal records.
"""

import hashlib
import hmac
import logging
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx

from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.brokers.binance.parser import parse_symbol

logger = logging.getLogger(__name__)

BINANCE_API_URL = "https://api.binance.com"

# Weight limit per minute for Binance API
_WEIGHT_LIMIT_PER_MINUTE = 1200


@dataclass
class BinanceCredentials:
    """Binance API credentials."""

    api_key: str
    api_secret: str


class BinanceAPIError(Exception):
    """Exception raised for Binance API errors."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class BinanceClient:
    """Client for interacting with Binance REST API.

    Implements HMAC-SHA256 authentication with timestamp-based signing.

    Usage:
        client = BinanceClient(BinanceCredentials(api_key="...", api_secret="..."))
        balances = client.get_account_balances()
        trades = client.get_trade_history("BTCUSDT", start=datetime(2024, 1, 1))
    """

    def __init__(self, credentials: BinanceCredentials):
        """Initialize Binance client with credentials."""
        self.api_key = credentials.api_key
        self.api_secret = credentials.api_secret
        self._weight_used = 0
        self._weight_reset_time = time.time()

    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC-SHA256 signature for request.

        Signature = hex(HMAC-SHA256(query_string, secret_key))
        """
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _check_rate_limit(self, weight: int) -> None:
        """Check rate limit and sleep if necessary."""
        now = time.time()

        # Reset weight counter every minute
        if now - self._weight_reset_time >= 60:
            self._weight_used = 0
            self._weight_reset_time = now

        # If we would exceed limit, wait for reset
        if self._weight_used + weight > _WEIGHT_LIMIT_PER_MINUTE:
            sleep_time = 60 - (now - self._weight_reset_time) + 1
            logger.info(f"Rate limit approaching, sleeping for {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self._weight_used = 0
            self._weight_reset_time = time.time()

        self._weight_used += weight

    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        weight: int = 1,
        timeout: float = 30.0,
    ) -> dict:
        """Make authenticated signed API request.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path (e.g., "/api/v3/account")
            params: Request parameters (excluding timestamp and signature)
            weight: Request weight for rate limiting
            timeout: Request timeout in seconds

        Returns:
            API response as dictionary

        Raises:
            BinanceAPIError: If API returns errors
        """
        self._check_rate_limit(weight)

        url = BINANCE_API_URL + endpoint

        # Build request parameters with timestamp
        request_params = params.copy() if params else {}
        request_params["timestamp"] = self._get_timestamp()

        # Generate signature
        query_string = urllib.parse.urlencode(request_params)
        signature = self._generate_signature(query_string)
        request_params["signature"] = signature

        headers = {
            "X-MBX-APIKEY": self.api_key,
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    response = client.get(url, params=request_params, headers=headers)
                elif method == "POST":
                    response = client.post(url, params=request_params, headers=headers)
                elif method == "DELETE":
                    response = client.delete(url, params=request_params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Update weight from response headers
                used_weight = response.headers.get("X-MBX-USED-WEIGHT-1M")
                if used_weight:
                    self._weight_used = int(used_weight)

                result = response.json()

        except httpx.HTTPError as e:
            logger.error(f"Binance API HTTP error: {e}")
            raise BinanceAPIError(f"HTTP error: {e}") from e

        # Check for API errors
        if isinstance(result, dict) and "code" in result and result["code"] < 0:
            error_msg = result.get("msg", "Unknown error")
            error_code = result.get("code")
            logger.error(f"Binance API error: {error_code} - {error_msg}")
            raise BinanceAPIError(error_msg, error_code)

        return result

    def get_account_balances(self) -> dict[str, Decimal]:
        """Get current account balances.

        Returns:
            Dictionary of asset -> total balance (free + locked)
        """
        result = self._signed_request("GET", "/api/v3/account", weight=20)

        balances = {}
        for balance in result.get("balances", []):
            asset = balance["asset"]
            free = Decimal(balance["free"])
            locked = Decimal(balance["locked"])
            total = free + locked

            if total > 0:
                balances[asset] = total

        return balances

    def get_trade_history(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Get trade history for a specific symbol.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            start: Start time filter
            end: End time filter
            limit: Max trades to return (max 1000)

        Returns:
            List of trade records

        Note:
            Time between start and end cannot exceed 24 hours per request.
        """
        all_trades = []

        # If date range exceeds 24 hours, split into chunks
        if start and end:
            current_start = start
            while current_start < end:
                current_end = min(current_start + timedelta(hours=24), end)

                params = {
                    "symbol": symbol,
                    "startTime": int(current_start.timestamp() * 1000),
                    "endTime": int(current_end.timestamp() * 1000),
                    "limit": limit,
                }

                trades = self._signed_request("GET", "/api/v3/myTrades", params, weight=20)
                all_trades.extend(trades)

                current_start = current_end

                # Small delay between requests
                time.sleep(0.5)
        else:
            params = {"symbol": symbol, "limit": limit}
            if start:
                params["startTime"] = int(start.timestamp() * 1000)
            if end:
                params["endTime"] = int(end.timestamp() * 1000)

            all_trades = self._signed_request("GET", "/api/v3/myTrades", params, weight=20)

        return all_trades

    def get_deposit_history(
        self,
        coin: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """Get deposit history.

        Args:
            coin: Filter by coin (optional)
            start: Start time filter (max 90 days range)
            end: End time filter

        Returns:
            List of deposit records
        """
        params: dict = {}

        if coin:
            params["coin"] = coin
        if start:
            params["startTime"] = int(start.timestamp() * 1000)
        if end:
            params["endTime"] = int(end.timestamp() * 1000)

        return self._signed_request("GET", "/sapi/v1/capital/deposit/hisrec", params, weight=1)

    def get_withdrawal_history(
        self,
        coin: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """Get withdrawal history.

        Args:
            coin: Filter by coin (optional)
            start: Start time filter (max 90 days range)
            end: End time filter

        Returns:
            List of withdrawal records
        """
        params: dict = {}

        if coin:
            params["coin"] = coin
        if start:
            params["startTime"] = int(start.timestamp() * 1000)
        if end:
            params["endTime"] = int(end.timestamp() * 1000)

        return self._signed_request("GET", "/sapi/v1/capital/withdraw/history", params, weight=1)

    def fetch_all_data(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BrokerImportData:
        """Fetch all account data and return as BrokerImportData.

        This method fetches:
        - Current balances (positions)
        - Trade history for all traded pairs
        - Deposit history
        - Withdrawal history

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            BrokerImportData containing all parsed records
        """
        # Convert dates to datetimes for API
        start = (
            datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)
            if start_date
            else None
        )
        end = (
            datetime.combine(end_date, datetime.max.time()).replace(tzinfo=UTC)
            if end_date
            else None
        )

        # Fetch balances for positions
        positions: list[ParsedPosition] = []
        traded_assets: set[str] = set()

        try:
            balances = self.get_account_balances()
            for asset, quantity in balances.items():
                positions.append(
                    ParsedPosition(
                        symbol=asset,
                        quantity=quantity,
                        currency=asset,
                        asset_class="Crypto",
                    )
                )
                traded_assets.add(asset)
            logger.info(f"Fetched {len(positions)} Binance positions")
        except BinanceAPIError as e:
            logger.error(f"Failed to fetch Binance balances: {e}")

        # Fetch trade history for each asset pair
        transactions: list[ParsedTransaction] = []
        all_dates: list[date] = []

        # Build list of symbols to query (common pairs)
        quote_assets = ["USDT", "BUSD", "BTC", "ETH", "BNB"]
        symbols_to_query = []

        for base in traded_assets:
            for quote in quote_assets:
                if base != quote:
                    symbols_to_query.append(f"{base}{quote}")

        # Query trade history for each symbol
        for symbol in symbols_to_query:
            try:
                trades = self.get_trade_history(symbol, start=start, end=end)

                for trade in trades:
                    parsed = self._parse_trade(trade, symbol)
                    if parsed:
                        transactions.append(parsed)
                        trade_time = trade.get("time")
                        if trade_time:
                            trade_date = datetime.fromtimestamp(trade_time / 1000, tz=UTC).date()
                            all_dates.append(trade_date)

            except BinanceAPIError as e:
                # Symbol might not exist or have no trades - skip silently
                if e.code != -1121:  # Invalid symbol
                    logger.debug(f"No trades for {symbol}: {e}")

        logger.info(f"Fetched {len(transactions)} Binance trades")

        # Fetch deposit history
        cash_transactions: list[ParsedCashTransaction] = []

        try:
            # Split into 90-day chunks if needed
            deposits = self._fetch_history_chunked(self.get_deposit_history, start, end)

            for deposit in deposits:
                parsed = self._parse_deposit(deposit)
                if parsed:
                    cash_transactions.append(parsed)
                    insert_time = deposit.get("insertTime")
                    if insert_time:
                        deposit_date = datetime.fromtimestamp(insert_time / 1000, tz=UTC).date()
                        all_dates.append(deposit_date)

            logger.info(f"Fetched {len(deposits)} Binance deposits")
        except BinanceAPIError as e:
            logger.error(f"Failed to fetch Binance deposits: {e}")

        # Fetch withdrawal history
        try:
            withdrawals = self._fetch_history_chunked(self.get_withdrawal_history, start, end)

            for withdrawal in withdrawals:
                parsed = self._parse_withdrawal(withdrawal)
                if parsed:
                    cash_transactions.append(parsed)
                    apply_time = withdrawal.get("applyTime")
                    if apply_time:
                        try:
                            withdrawal_date = datetime.strptime(
                                apply_time, "%Y-%m-%d %H:%M:%S"
                            ).date()
                            all_dates.append(withdrawal_date)
                        except ValueError:
                            pass

            logger.info(f"Fetched {len(withdrawals)} Binance withdrawals")
        except BinanceAPIError as e:
            logger.error(f"Failed to fetch Binance withdrawals: {e}")

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

    def _fetch_history_chunked(
        self,
        fetch_func,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict]:
        """Fetch history in 90-day chunks (API limitation)."""
        if not start or not end:
            return fetch_func(start=start, end=end)

        all_records = []
        current_start = start

        while current_start < end:
            current_end = min(current_start + timedelta(days=89), end)

            records = fetch_func(start=current_start, end=current_end)
            all_records.extend(records)

            current_start = current_end + timedelta(seconds=1)
            time.sleep(0.5)  # Rate limiting

        return all_records

    def _parse_trade(self, trade: dict, symbol: str) -> ParsedTransaction | None:
        """Parse a single trade from API response."""
        trade_time = trade.get("time")
        if not trade_time:
            return None

        trade_date = datetime.fromtimestamp(trade_time / 1000, tz=UTC).date()
        base_asset, quote_asset = parse_symbol(symbol)

        is_buyer = trade.get("isBuyer", False)
        quantity = Decimal(str(trade.get("qty", "0")))
        price = Decimal(str(trade.get("price", "0")))
        quote_qty = Decimal(str(trade.get("quoteQty", "0")))
        commission = Decimal(str(trade.get("commission", "0")))

        return ParsedTransaction(
            trade_date=trade_date,
            symbol=base_asset,
            transaction_type="Buy" if is_buyer else "Sell",
            quantity=quantity,
            price_per_unit=price,
            amount=quote_qty,
            fees=commission,
            currency=quote_asset,
            notes=f"Binance trade - {trade.get('id', '')}",
            raw_data=trade,
        )

    def _parse_deposit(self, deposit: dict) -> ParsedCashTransaction | None:
        """Parse a deposit from API response."""
        insert_time = deposit.get("insertTime")
        if not insert_time:
            return None

        deposit_date = datetime.fromtimestamp(insert_time / 1000, tz=UTC).date()

        return ParsedCashTransaction(
            date=deposit_date,
            transaction_type="Deposit",
            amount=Decimal(str(deposit.get("amount", "0"))),
            currency=deposit.get("coin", ""),
            notes=f"Binance deposit - {deposit.get('txId', '')}",
            raw_data=deposit,
        )

    def _parse_withdrawal(self, withdrawal: dict) -> ParsedCashTransaction | None:
        """Parse a withdrawal from API response."""
        apply_time = withdrawal.get("applyTime")
        if not apply_time:
            return None

        try:
            withdrawal_date = datetime.strptime(apply_time, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            return None

        amount = Decimal(str(withdrawal.get("amount", "0")))
        fee = Decimal(str(withdrawal.get("transactionFee", "0")))

        return ParsedCashTransaction(
            date=withdrawal_date,
            transaction_type="Withdrawal",
            amount=-amount,  # Negative for withdrawal
            currency=withdrawal.get("coin", ""),
            notes=f"Binance withdrawal - fee: {fee}",
            raw_data=withdrawal,
        )
