"""KuCoin API client for fetching account data.

Implements KuCoin's HMAC-SHA256 authentication with API v2 passphrase encryption.
Provides methods for fetching balances, trade fills, deposits, withdrawals, and staking rewards.
"""

import base64
import hashlib
import hmac
import logging
import time
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
from app.services.brokers.kucoin.constants import parse_symbol

logger = logging.getLogger(__name__)

KUCOIN_API_URL = "https://api.kucoin.com"
_FILLS_WINDOW_DAYS = 7
_PAGE_SIZE = 500
_REQUEST_DELAY = 0.35  # seconds between requests


@dataclass
class KuCoinCredentials:
    """KuCoin API credentials (3 fields required)."""

    api_key: str
    api_secret: str
    api_passphrase: str


class KuCoinAPIError(Exception):
    """Exception raised for KuCoin API errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class KuCoinClient:
    """Client for interacting with KuCoin REST API.

    Implements HMAC-SHA256 authentication with API v2 passphrase encryption.
    """

    def __init__(self, credentials: KuCoinCredentials) -> None:
        self.api_key = credentials.api_key
        self.api_secret = credentials.api_secret.encode("utf-8")
        self.api_passphrase = credentials.api_passphrase

    def _generate_signature(self, timestamp: str, method: str, endpoint: str, body: str) -> str:
        """Generate HMAC-SHA256 signature for request.

        Signature = base64(HMAC-SHA256(timestamp + method + endpoint + body, secret))
        """
        str_to_sign = timestamp + method + endpoint + body
        signature = hmac.new(
            self.api_secret,
            str_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _encrypt_passphrase(self) -> str:
        """Encrypt passphrase for API v2.

        Encrypted = base64(HMAC-SHA256(passphrase, secret))
        """
        encrypted = hmac.new(
            self.api_secret,
            self.api_passphrase.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(encrypted).decode("utf-8")

    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        """Make authenticated signed API request."""
        timestamp = str(int(time.time() * 1000))

        # Build query string for GET requests
        query_string = ""
        if params and method == "GET":
            query_string = "?" + "&".join(f"{k}={v}" for k, v in params.items())

        full_endpoint = endpoint + query_string
        body = ""

        signature = self._generate_signature(timestamp, method, full_endpoint, body)
        encrypted_passphrase = self._encrypt_passphrase()

        headers = {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json",
        }

        url = KUCOIN_API_URL + endpoint

        try:
            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    response = client.get(url, params=params, headers=headers)
                else:
                    response = client.post(url, headers=headers)

                result = response.json()

        except httpx.HTTPError as e:
            logger.error("KuCoin API HTTP error: %s", e)
            raise KuCoinAPIError(f"HTTP error: {e}") from e

        # KuCoin returns "200000" for success
        code = result.get("code", "")
        if str(code) != "200000":
            error_msg = result.get("msg", "Unknown error")
            logger.error("KuCoin API error: %s - %s", code, error_msg)
            raise KuCoinAPIError(error_msg, code)

        return result

    def get_account_balances(self) -> dict[str, Decimal]:
        """Get current trade account balances.

        Returns:
            Dictionary of currency -> balance for non-zero trade accounts.
        """
        result = self._signed_request("GET", "/api/v1/accounts")

        balances: dict[str, Decimal] = {}
        for account in result.get("data", []):
            if account.get("type") != "trade":
                continue
            balance = Decimal(str(account.get("balance", "0")))
            if balance > 0:
                currency = account["currency"]
                balances[currency] = balance

        return balances

    def _fetch_paginated(
        self,
        endpoint: str,
        start_at: int | None = None,
        end_at: int | None = None,
        extra_params: dict | None = None,
    ) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        all_items: list[dict] = []
        current_page = 1

        while True:
            params: dict = {"pageSize": _PAGE_SIZE, "currentPage": current_page}
            if start_at is not None:
                params["startAt"] = start_at
            if end_at is not None:
                params["endAt"] = end_at
            if extra_params:
                params.update(extra_params)

            result = self._signed_request("GET", endpoint, params)
            data = result.get("data", {})

            items = data.get("items", [])
            all_items.extend(items)

            total_page = data.get("totalPage", 1)
            if current_page >= total_page:
                break

            current_page += 1
            time.sleep(_REQUEST_DELAY)

        return all_items

    def _fetch_all_fills(
        self, start: datetime | None, end: datetime | None
    ) -> list[ParsedTransaction]:
        """Fetch all trade fills, chunked into 7-day windows."""
        transactions: list[ParsedTransaction] = []

        if not start or not end:
            end = end or datetime.now(tz=UTC)
            start = start or (end - timedelta(days=_FILLS_WINDOW_DAYS))

        current_start = start
        while current_start < end:
            current_end = min(current_start + timedelta(days=_FILLS_WINDOW_DAYS), end)

            start_ms = int(current_start.timestamp() * 1000)
            end_ms = int(current_end.timestamp() * 1000)

            fills = self._fetch_paginated("/api/v1/fills", start_at=start_ms, end_at=end_ms)

            for fill in fills:
                parsed = self._parse_fill(fill)
                if parsed:
                    transactions.append(parsed)

            current_start = current_end
            time.sleep(_REQUEST_DELAY)

        logger.info("Fetched %d KuCoin fills", len(transactions))
        return transactions

    def _fetch_all_deposits(
        self, start: datetime | None, end: datetime | None
    ) -> list[ParsedCashTransaction]:
        """Fetch all deposit records."""
        start_at = int(start.timestamp() * 1000) if start else None
        end_at = int(end.timestamp() * 1000) if end else None

        deposits = self._fetch_paginated("/api/v1/deposits", start_at=start_at, end_at=end_at)

        results: list[ParsedCashTransaction] = []
        for dep in deposits:
            parsed = self._parse_deposit(dep)
            if parsed:
                results.append(parsed)

        logger.info("Fetched %d KuCoin deposits", len(results))
        return results

    def _fetch_all_withdrawals(
        self, start: datetime | None, end: datetime | None
    ) -> list[ParsedCashTransaction]:
        """Fetch all withdrawal records."""
        start_at = int(start.timestamp() * 1000) if start else None
        end_at = int(end.timestamp() * 1000) if end else None

        withdrawals = self._fetch_paginated("/api/v1/withdrawals", start_at=start_at, end_at=end_at)

        results: list[ParsedCashTransaction] = []
        for w in withdrawals:
            parsed = self._parse_withdrawal(w)
            if parsed:
                results.append(parsed)

        logger.info("Fetched %d KuCoin withdrawals", len(results))
        return results

    def _fetch_staking_rewards(
        self, start: datetime | None, end: datetime | None
    ) -> list[ParsedTransaction]:
        """Fetch staking rewards from account ledger.

        KuCoin's ledger endpoint requires bounded date ranges. If no range is
        provided, defaults to the last 180 days.
        """
        if not end:
            end = datetime.now(tz=UTC)
        if not start:
            start = end - timedelta(days=180)

        start_at = int(start.timestamp() * 1000)
        end_at = int(end.timestamp() * 1000)

        staking_biz_types = ["KUCOIN_BONUS", "STAKING", "SOFT_STAKING_PROFITS"]
        results: list[ParsedTransaction] = []

        for biz_type in staking_biz_types:
            try:
                entries = self._fetch_paginated(
                    "/api/v1/accounts/ledgers",
                    start_at=start_at,
                    end_at=end_at,
                    extra_params={"bizType": biz_type},
                )
                for entry in entries:
                    parsed = self._parse_ledger_staking(entry)
                    if parsed:
                        results.append(parsed)
            except KuCoinAPIError:
                logger.warning("Failed to fetch KuCoin %s ledger entries", biz_type)

        logger.info("Fetched %d KuCoin staking rewards", len(results))
        return results

    def fetch_all_data(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BrokerImportData:
        """Fetch all account data and return as BrokerImportData."""
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
            balances = self.get_account_balances()
            for currency, quantity in balances.items():
                positions.append(
                    ParsedPosition(
                        symbol=currency,
                        quantity=quantity,
                        currency=currency,
                        asset_class="Crypto",
                    )
                )
            logger.info("Fetched %d KuCoin positions", len(positions))
        except KuCoinAPIError as e:
            logger.error("Failed to fetch KuCoin balances: %s", e)

        transactions = self._fetch_all_fills(start, end)

        cash_transactions = [
            *self._fetch_all_deposits(start, end),
            *self._fetch_all_withdrawals(start, end),
        ]

        dividends = self._fetch_staking_rewards(start, end)

        # Determine date range from all data
        all_dates: list[date] = [
            *[t.trade_date for t in transactions],
            *[c.date for c in cash_transactions],
            *[d.trade_date for d in dividends],
        ]

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

    def _parse_fill(self, fill: dict) -> ParsedTransaction | None:
        """Parse a single trade fill from API response."""
        created_at = fill.get("createdAt")
        if not created_at:
            return None

        trade_date = datetime.fromtimestamp(created_at / 1000, tz=UTC).date()
        symbol_str = fill.get("symbol", "")
        base_asset, quote_asset = parse_symbol(symbol_str)

        side = fill.get("side", "").lower()
        if side not in ("buy", "sell"):
            return None

        quantity = Decimal(str(fill.get("size", "0")))
        price = Decimal(str(fill.get("price", "0")))
        funds = Decimal(str(fill.get("funds", "0")))
        fee = Decimal(str(fill.get("fee", "0")))

        return ParsedTransaction(
            trade_date=trade_date,
            symbol=base_asset,
            transaction_type="Buy" if side == "buy" else "Sell",
            quantity=quantity,
            price_per_unit=price,
            amount=funds,
            fees=fee,
            currency=quote_asset,
            external_transaction_id=fill.get("tradeId", ""),
            notes=f"KuCoin {side} - {symbol_str}",
            raw_data=fill,
        )

    def _parse_deposit(self, deposit: dict) -> ParsedCashTransaction | None:
        """Parse a deposit from API response."""
        status = deposit.get("status", "")
        if status != "SUCCESS":
            return None

        created_at = deposit.get("createdAt")
        if not created_at:
            return None

        deposit_date = datetime.fromtimestamp(created_at / 1000, tz=UTC).date()

        return ParsedCashTransaction(
            date=deposit_date,
            transaction_type="Deposit",
            amount=Decimal(str(deposit.get("amount", "0"))),
            currency=deposit.get("currency", ""),
            fees=Decimal(str(deposit.get("fee", "0"))),
            notes="KuCoin deposit",
            raw_data=deposit,
        )

    def _parse_withdrawal(self, withdrawal: dict) -> ParsedCashTransaction | None:
        """Parse a withdrawal from API response."""
        status = withdrawal.get("status", "")
        if status != "SUCCESS":
            return None

        created_at = withdrawal.get("createdAt")
        if not created_at:
            return None

        withdrawal_date = datetime.fromtimestamp(created_at / 1000, tz=UTC).date()
        amount = Decimal(str(withdrawal.get("amount", "0")))

        return ParsedCashTransaction(
            date=withdrawal_date,
            transaction_type="Withdrawal",
            amount=-amount,
            currency=withdrawal.get("currency", ""),
            fees=Decimal(str(withdrawal.get("fee", "0"))),
            notes="KuCoin withdrawal",
            raw_data=withdrawal,
        )

    def _parse_ledger_staking(self, entry: dict) -> ParsedTransaction | None:
        """Parse a staking reward from ledger entry."""
        created_at = entry.get("createdAt")
        if not created_at:
            return None

        entry_date = datetime.fromtimestamp(created_at / 1000, tz=UTC).date()
        currency = entry.get("currency", "")
        amount = Decimal(str(entry.get("amount", "0")))

        if amount <= 0:
            return None

        biz_type = entry.get("bizType", "Staking")

        return ParsedTransaction(
            trade_date=entry_date,
            symbol=currency,
            transaction_type="Staking",
            amount=amount,
            currency=currency,
            notes=f"KuCoin {biz_type}",
            raw_data=entry,
        )
