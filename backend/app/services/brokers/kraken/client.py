"""Kraken API client for fetching account data.

Implements Kraken's HMAC-SHA512 authentication and provides methods
for fetching balances, trade history, and ledger entries.
"""

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedPosition,
    ParsedTransaction,
)
from app.services.brokers.kraken.constants import normalize_kraken_asset
from app.services.market_data.coingecko_client import CoinGeckoClient

logger = logging.getLogger(__name__)

KRAKEN_API_URL = "https://api.kraken.com"


@dataclass
class KrakenCredentials:
    """Kraken API credentials."""

    api_key: str
    api_secret: str


class KrakenAPIError(Exception):
    """Exception raised for Kraken API errors."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class KrakenClient:
    """Client for interacting with Kraken REST API.

    Implements HMAC-SHA512 authentication and handles rate limiting.

    Usage:
        client = KrakenClient(KrakenCredentials(api_key="...", api_secret="..."))
        balances = client.get_balance()
        trades = client.get_trades_history(start=datetime(2024, 1, 1))
    """

    def __init__(
        self, credentials: KrakenCredentials, coingecko_client: CoinGeckoClient | None = None
    ):
        """Initialize Kraken client with credentials.

        Args:
            credentials: Kraken API credentials
            coingecko_client: Optional CoinGecko client for fetching deposit prices.
                             If not provided, one will be created lazily when needed.
        """
        self.api_key = credentials.api_key
        self.api_secret = base64.b64decode(credentials.api_secret)
        self._nonce_offset = 0
        self._coingecko_client = coingecko_client

    def _get_nonce(self) -> int:
        """Generate always-increasing nonce value."""
        # Use millisecond timestamp with offset to ensure uniqueness
        nonce = int(time.time() * 1000) + self._nonce_offset
        self._nonce_offset += 1
        return nonce

    def _sign_request(self, uri_path: str, data: dict) -> str:
        """Generate HMAC-SHA512 signature for request.

        Signature = base64(HMAC-SHA512(uri_path + SHA256(nonce + postdata), secret))
        """
        # URL encode the data
        postdata = urllib.parse.urlencode(data)

        # Create message: SHA256(nonce + postdata)
        message = (str(data["nonce"]) + postdata).encode()
        sha256_hash = hashlib.sha256(message).digest()

        # Create signature: HMAC-SHA512(uri_path + sha256_hash, secret)
        sign_message = uri_path.encode() + sha256_hash
        signature = hmac.new(self.api_secret, sign_message, hashlib.sha512)

        return base64.b64encode(signature.digest()).decode()

    def _private_request(
        self, endpoint: str, data: dict | None = None, timeout: float = 30.0
    ) -> dict:
        """Make authenticated private API request.

        Args:
            endpoint: API endpoint path (e.g., "/0/private/Balance")
            data: Request data (excluding nonce)
            timeout: Request timeout in seconds

        Returns:
            API response result

        Raises:
            KrakenAPIError: If API returns errors
        """
        uri_path = endpoint
        url = KRAKEN_API_URL + uri_path

        # Build request data with nonce
        request_data = data.copy() if data else {}
        request_data["nonce"] = self._get_nonce()

        # Sign the request
        signature = self._sign_request(uri_path, request_data)

        headers = {
            "API-Key": self.api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, data=request_data, headers=headers)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Kraken API HTTP error: {e}")
            raise KrakenAPIError(f"HTTP error: {e}") from e

        # Check for API errors
        if result.get("error"):
            errors = result["error"]
            error_msg = ", ".join(errors)
            logger.error(f"Kraken API error: {error_msg}")
            raise KrakenAPIError(error_msg, errors)

        return result.get("result", {})

    def _normalize_asset(self, asset: str) -> str:
        """Normalize Kraken asset names to standard symbols."""
        return normalize_kraken_asset(asset)

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

    def get_balance(self) -> dict[str, Decimal]:
        """Get current account balances.

        Returns:
            Dictionary of asset -> balance
        """
        result = self._private_request("/0/private/Balance")

        balances = {}
        for asset, balance_str in result.items():
            normalized_asset = self._normalize_asset(asset)
            balance = Decimal(balance_str)
            if balance > 0:
                # Aggregate assets that map to same symbol
                if normalized_asset in balances:
                    balances[normalized_asset] += balance
                else:
                    balances[normalized_asset] = balance

        return balances

    def get_trades_history(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Get trade history.

        Args:
            start: Start time filter
            end: End time filter
            offset: Result offset for pagination

        Returns:
            Tuple of (trades list, total count)
        """
        data: dict = {"ofs": offset}

        if start:
            data["start"] = int(start.timestamp())
        if end:
            data["end"] = int(end.timestamp())

        result = self._private_request("/0/private/TradesHistory", data)

        trades = list(result.get("trades", {}).values())
        count = result.get("count", len(trades))

        return trades, count

    def get_ledgers(
        self,
        asset: str | None = None,
        ledger_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Get ledger entries.

        Args:
            asset: Filter by asset (e.g., "XBT", "USD")
            ledger_type: Filter by type ("all", "deposit", "withdrawal", "trade", "staking")
            start: Start time filter
            end: End time filter
            offset: Result offset for pagination

        Returns:
            Tuple of (ledger entries list, total count)
        """
        data: dict = {"ofs": offset}

        if asset:
            data["asset"] = asset
        if ledger_type:
            data["type"] = ledger_type
        if start:
            data["start"] = int(start.timestamp())
        if end:
            data["end"] = int(end.timestamp())

        result = self._private_request("/0/private/Ledgers", data)

        ledgers = list(result.get("ledger", {}).values())
        count = result.get("count", len(ledgers))

        return ledgers, count

    def fetch_all_data(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BrokerImportData:
        """Fetch all account data and return as BrokerImportData.

        This method fetches:
        - Current balances (positions)
        - All ledger entries (deposits, withdrawals, trades, staking)

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
        try:
            balances = self.get_balance()
            for asset, quantity in balances.items():
                positions.append(
                    ParsedPosition(
                        symbol=asset,
                        quantity=quantity,
                        currency="USD",  # Crypto assets are priced in USD
                        asset_class="Crypto",
                    )
                )
            logger.info(f"Fetched {len(positions)} Kraken positions")
        except KrakenAPIError as e:
            logger.error(f"Failed to fetch Kraken balances: {e}")

        # Fetch all ledger entries with pagination
        all_ledger_entries: list[dict] = []
        transactions: list[ParsedTransaction] = []  # Crypto deposits/withdrawals added here
        cash_transactions: list[ParsedCashTransaction] = []
        dividends: list[ParsedTransaction] = []
        all_dates: list[date] = []

        offset = 0
        page_size = 50
        max_pages = 100  # Safety limit

        for _ in range(max_pages):
            try:
                ledgers, total = self.get_ledgers(start=start, end=end, offset=offset)
            except KrakenAPIError as e:
                logger.error(f"Failed to fetch Kraken ledgers: {e}")
                break

            if not ledgers:
                break

            for entry in ledgers:
                entry_type = entry.get("type", "").lower()
                entry_time = entry.get("time")

                if entry_time:
                    entry_date = datetime.fromtimestamp(entry_time, tz=UTC).date()
                    all_dates.append(entry_date)

                if entry_type == "trade":
                    # Collect trade entries to process together (group by refid)
                    all_ledger_entries.append(entry)
                elif entry_type in ("deposit", "withdrawal", "staking", "transfer"):
                    # Process non-trade entries immediately
                    parsed = self._parse_ledger_entry(entry)
                    if parsed:
                        result_type, parsed_data = parsed
                        if result_type == "cash":
                            cash_transactions.append(parsed_data)
                        elif result_type == "dividend":
                            dividends.append(parsed_data)
                        elif result_type in ("crypto_deposit", "crypto_withdrawal", "transfer"):
                            # Crypto deposits/withdrawals/transfers go to transactions list
                            transactions.append(parsed_data)

            offset += page_size
            if offset >= total:
                break

            # Rate limiting - wait between pages
            time.sleep(2)  # Conservative delay to stay within rate limits

        # Process trade entries by grouping crypto+fiat sides
        # Returns both crypto transactions and trade settlement cash transactions
        trade_transactions, trade_settlements = self._process_trade_entries(all_ledger_entries)
        transactions.extend(trade_transactions)
        cash_transactions.extend(trade_settlements)

        logger.info(
            f"Fetched Kraken ledgers: {len(transactions)} crypto txns "
            f"({len(trade_transactions)} trades), {len(cash_transactions)} cash "
            f"({len(trade_settlements)} settlements), {len(dividends)} staking"
        )

        # Determine date range
        actual_start = min(all_dates) if all_dates else (start_date or date.today())
        actual_end = max(all_dates) if all_dates else (end_date or date.today())

        return BrokerImportData(
            start_date=actual_start,
            end_date=actual_end,
            positions=positions,
            transactions=transactions,
            cash_transactions=cash_transactions,
            dividends=dividends,
        )

    def _process_trade_entries(
        self, entries: list[dict]
    ) -> tuple[list[ParsedTransaction], list[ParsedCashTransaction]]:
        """Process trade ledger entries by grouping crypto+fiat sides.

        Kraken's ledger returns two entries per trade:
        - Crypto side: e.g., BTC +0.001 (you received BTC)
        - Fiat side: e.g., USD -100 (you paid USD)

        This method groups them by refid and creates:
        1. A crypto transaction with symbol, quantity, and calculated price
        2. A Trade Settlement cash transaction for the fiat impact (dual-entry accounting)

        Returns:
            Tuple of (crypto transactions, trade settlement cash transactions)
        """
        from app.services.brokers.kraken.constants import FIAT_CURRENCIES

        # Group entries by refid
        trades_by_refid: dict[str, list[dict]] = {}
        for entry in entries:
            refid = entry.get("refid", "")
            if refid:
                if refid not in trades_by_refid:
                    trades_by_refid[refid] = []
                trades_by_refid[refid].append(entry)

        transactions: list[ParsedTransaction] = []
        trade_settlements: list[ParsedCashTransaction] = []

        for refid, trade_entries in trades_by_refid.items():
            if len(trade_entries) < 2:
                # Single entry trade - unusual, skip or handle as-is
                logger.warning(f"Trade {refid} has only {len(trade_entries)} entry, skipping")
                continue

            # Separate crypto and fiat sides
            crypto_entry = None
            fiat_entry = None

            for entry in trade_entries:
                asset = self._normalize_asset(entry.get("asset", ""))
                if asset in FIAT_CURRENCIES:
                    fiat_entry = entry
                else:
                    crypto_entry = entry

            if not crypto_entry or not fiat_entry:
                # Crypto-to-crypto trade: both sides are crypto assets
                # Create transactions for both sides (one Buy, one Sell)
                crypto_entries = [
                    e
                    for e in trade_entries
                    if self._normalize_asset(e.get("asset", "")) not in FIAT_CURRENCIES
                ]

                if len(crypto_entries) != 2:
                    logger.warning(
                        f"Trade {refid} has unexpected structure: "
                        f"{len(crypto_entries)} crypto entries"
                    )
                    continue

                # Process crypto-to-crypto trade
                entry_time = crypto_entries[0].get("time")
                if not entry_time:
                    continue
                entry_date = datetime.fromtimestamp(entry_time, tz=UTC).date()

                for entry in crypto_entries:
                    txn = self._create_crypto_to_crypto_transaction(entry, entry_date, refid)
                    transactions.append(txn)

                # No Trade Settlement for crypto-to-crypto trades (no fiat involved)
                continue

            # Extract data
            entry_time = crypto_entry.get("time")
            if not entry_time:
                continue

            entry_date = datetime.fromtimestamp(entry_time, tz=UTC).date()
            crypto_asset = self._normalize_asset(crypto_entry.get("asset", ""))
            crypto_amount = Decimal(str(crypto_entry.get("amount", "0")))
            fiat_amount = Decimal(str(fiat_entry.get("amount", "0")))
            fiat_fee = Decimal(str(fiat_entry.get("fee", "0")))
            crypto_fee = Decimal(str(crypto_entry.get("fee", "0")))
            fiat_currency = self._normalize_asset(fiat_entry.get("asset", ""))

            # Determine transaction type and calculate price
            # Positive crypto = Buy, Negative crypto = Sell
            # NOTE: crypto_fee is subtracted from quantity to get NET amount received
            if crypto_amount > 0:
                # Buying crypto with fiat
                transaction_type = "Buy"
                quantity = crypto_amount - crypto_fee  # Net crypto received after fee
                # fiat_amount is negative (spent), so negate to get positive cost
                cost = abs(fiat_amount)
            else:
                # Selling crypto for fiat
                transaction_type = "Sell"
                # Total crypto leaving account = amount sold + fee paid in crypto
                quantity = abs(crypto_amount) + crypto_fee
                # fiat_amount is positive (received)
                cost = fiat_amount

            # Calculate price per unit
            price_per_unit = cost / quantity if quantity != 0 else None

            # Total fees (usually on fiat side)
            total_fees = fiat_fee + crypto_fee

            # Create crypto transaction
            transactions.append(
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=crypto_asset,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    amount=cost,
                    fees=total_fees,
                    currency="USD",
                    notes=f"Kraken trade - {refid}",
                    raw_data={"crypto": crypto_entry, "fiat": fiat_entry},
                )
            )

            # Create Trade Settlement for cash impact (dual-entry accounting)
            # fiat_amount is the principal amount, fee is charged separately
            # Total cash impact = fiat_amount - fiat_fee (fee reduces cash further)
            settlement_amount = fiat_amount - fiat_fee
            trade_settlements.append(
                ParsedCashTransaction(
                    date=entry_date,
                    transaction_type="Trade Settlement",
                    amount=settlement_amount,
                    currency=fiat_currency,
                    notes=f"Settlement for {crypto_asset} {transaction_type} - {refid}",
                    raw_data=fiat_entry,
                )
            )

        return transactions, trade_settlements

    def _create_crypto_to_crypto_transaction(
        self, entry: dict, entry_date: date, refid: str
    ) -> ParsedTransaction:
        """Create a transaction for one side of a crypto-to-crypto trade.

        For buys: net quantity = amount - fee (fee reduces what you receive)
        For sells: quantity = abs(amount) + fee (fee adds to what you give up)
        """
        asset = self._normalize_asset(entry.get("asset", ""))
        amount = Decimal(str(entry.get("amount", "0")))
        fee = Decimal(str(entry.get("fee", "0")))

        is_buy = amount > 0
        if is_buy:
            quantity = amount - fee
            transaction_type = "Buy"
        else:
            quantity = abs(amount) + fee
            transaction_type = "Sell"

        return ParsedTransaction(
            trade_date=entry_date,
            symbol=asset,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_unit=None,
            amount=None,
            fees=fee,
            currency="USD",
            notes=f"Kraken crypto-to-crypto trade ({transaction_type.lower()}) - {refid}",
            raw_data=entry,
        )

    def _parse_ledger_entry(
        self, entry: dict
    ) -> tuple[str, ParsedTransaction | ParsedCashTransaction] | None:
        """Parse a single non-trade ledger entry from API response.

        Trade entries are handled by _process_trade_entries() which groups
        crypto+fiat sides together.

        Returns:
            Tuple of (category, parsed_data) where category is one of:
            - "cash": Fiat deposit/withdrawal -> ParsedCashTransaction
            - "crypto_deposit": Crypto deposit -> ParsedTransaction
            - "crypto_withdrawal": Crypto withdrawal -> ParsedTransaction
            - "dividend": Staking reward -> ParsedTransaction
        """
        from app.services.brokers.kraken.constants import FIAT_CURRENCIES

        entry_type = entry.get("type", "").lower()
        entry_time = entry.get("time")

        if not entry_time:
            return None

        entry_date = datetime.fromtimestamp(entry_time, tz=UTC).date()
        asset = self._normalize_asset(entry.get("asset", ""))
        amount = Decimal(str(entry.get("amount", "0")))
        fee = Decimal(str(entry.get("fee", "0")))

        if entry_type == "deposit":
            if asset in FIAT_CURRENCIES:
                # Fiat deposit - goes on cash holding
                # Net amount = deposit amount - Kraken fee
                net_amount = amount - fee
                return (
                    "cash",
                    ParsedCashTransaction(
                        date=entry_date,
                        transaction_type="Deposit",
                        amount=net_amount,
                        currency=asset,
                        fees=fee,
                        notes=f"Kraken deposit - {entry.get('refid', '')}",
                        raw_data=entry,
                    ),
                )
            else:
                # Crypto deposit - creates holding quantity with market price at deposit time
                price = self._get_deposit_price(asset, entry_date)
                return (
                    "crypto_deposit",
                    ParsedTransaction(
                        trade_date=entry_date,
                        symbol=asset,
                        transaction_type="Deposit",
                        quantity=amount,
                        price_per_unit=price,  # Historical price for cost basis
                        amount=amount,  # Required for reconstruction service
                        currency="USD",
                        notes=f"Kraken crypto deposit - {entry.get('refid', '')}",
                        raw_data=entry,
                    ),
                )

        elif entry_type == "withdrawal":
            if asset in FIAT_CURRENCIES:
                # Fiat withdrawal - deducts from cash holding
                # Net amount = withdrawal amount - fee (both negative impact)
                net_amount = amount - fee  # e.g., -100 - 2 = -102
                return (
                    "cash",
                    ParsedCashTransaction(
                        date=entry_date,
                        transaction_type="Withdrawal",
                        amount=net_amount,  # Total withdrawn including fee
                        currency=asset,
                        fees=fee,
                        notes=f"Kraken withdrawal - {entry.get('refid', '')}",
                        raw_data=entry,
                    ),
                )
            else:
                # Crypto withdrawal - reduces holding quantity
                # Net amount = withdrawal amount - fee (both negative impact)
                net_quantity = amount - fee  # e.g., -0.007 - 0.00002 = -0.00702
                return (
                    "crypto_withdrawal",
                    ParsedTransaction(
                        trade_date=entry_date,
                        symbol=asset,
                        transaction_type="Withdrawal",
                        quantity=net_quantity,  # Total withdrawn including fee
                        price_per_unit=None,
                        amount=net_quantity,  # Required for reconstruction service
                        currency="USD",
                        notes=f"Kraken crypto withdrawal - {entry.get('refid', '')}",
                        raw_data=entry,
                    ),
                )

        elif entry_type == "staking":
            # Staking rewards have fees that need to be subtracted
            # Net quantity = gross reward - fee
            net_quantity = amount - fee
            return (
                "dividend",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Staking",
                    quantity=net_quantity,  # Net staking rewards after fee
                    amount=net_quantity,
                    fees=fee,
                    currency="USD",
                    notes=f"Kraken staking reward - {entry.get('refid', '')}",
                    raw_data=entry,
                ),
            )

        elif entry_type == "transfer":
            # Internal Kraken transfers (e.g., between staking variants like SOL.F -> SOL)
            # These affect crypto quantities but not cash
            # Amount is positive for receiving, negative for sending
            subtype = entry.get("subtype", "")
            return (
                "transfer",
                ParsedTransaction(
                    trade_date=entry_date,
                    symbol=asset,
                    transaction_type="Transfer",
                    quantity=amount,  # Positive=in, negative=out
                    price_per_unit=None,
                    amount=amount,  # For reconstruction service
                    currency="USD",
                    notes=f"Kraken transfer ({subtype}) - {entry.get('refid', '')}",
                    raw_data=entry,
                ),
            )

        return None
