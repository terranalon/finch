"""CoinGecko API client for cryptocurrency prices.

Serves as the single source of truth for crypto prices,
analogous to yfinance for stocks.
"""

import logging
import time
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_URL = "https://pro-api.coingecko.com/api/v3"

# Symbol to CoinGecko ID mapping for common cryptocurrencies
SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "XRP": "ripple",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "SOL": "solana",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "UNI": "uniswap",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "BNB": "binancecoin",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "ALGO": "algorand",
    "FIL": "filecoin",
    "AAVE": "aave",
    "CRO": "crypto-com-chain",
    "ETC": "ethereum-classic",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    # Additional mappings for Kraken assets
    "HBAR": "hedera-hashgraph",
    "KAS": "kaspa",
    "CHZ": "chiliz",
    "ONDO": "ondo-finance",
    "STRK": "starknet",
    "BABY": "babylon",  # Babylon - Bitcoin staking protocol
    "SNX": "havven",  # Synthetix
    "SAND": "the-sandbox",
}


class CoinGeckoAPIError(Exception):
    """Exception raised for CoinGecko API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CoinGeckoClient:
    """Client for fetching cryptocurrency prices from CoinGecko.

    This client serves as the single source of truth for crypto prices,
    similar to how yfinance is used for stock prices.

    Usage:
        client = CoinGeckoClient()
        prices = client.get_current_prices(["BTC", "ETH"])
        historical = client.get_historical_price("BTC", date(2024, 1, 1))
    """

    def __init__(self, api_key: str | None = None, use_pro_api: bool = False):
        """Initialize CoinGecko client.

        Args:
            api_key: Optional API key for higher rate limits
            use_pro_api: Use Pro API endpoint (requires paid plan)
        """
        self.api_key = api_key or getattr(settings, "coingecko_api_key", None)
        self.use_pro_api = use_pro_api
        self.base_url = COINGECKO_PRO_URL if use_pro_api else COINGECKO_BASE_URL
        self._last_request_time: float = 0
        self._min_request_interval: float = 1.0  # seconds between requests

    def _get_headers(self) -> dict[str, str]:
        """Get request headers including API key if available."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            if self.use_pro_api:
                headers["x-cg-pro-api-key"] = self.api_key
            else:
                headers["x-cg-demo-api-key"] = self.api_key
        return headers

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, endpoint: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        """Make HTTP request to CoinGecko API.

        Args:
            endpoint: API endpoint path (e.g., "/simple/price")
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response as dictionary

        Raises:
            CoinGeckoAPIError: If API returns an error
        """
        self._rate_limit()
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params, headers=self._get_headers())

                if response.status_code == 429:
                    raise CoinGeckoAPIError("Rate limit exceeded", status_code=response.status_code)

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"CoinGecko API HTTP error: {e}")
            raise CoinGeckoAPIError(f"HTTP error: {e}", status_code=e.response.status_code) from e
        except httpx.HTTPError as e:
            logger.error(f"CoinGecko API request error: {e}")
            raise CoinGeckoAPIError(f"Request error: {e}") from e

    def _symbol_to_id(self, symbol: str) -> str:
        """Convert cryptocurrency symbol to CoinGecko ID.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")

        Returns:
            CoinGecko coin ID (e.g., "bitcoin", "ethereum")
        """
        upper_symbol = symbol.upper()
        if upper_symbol in SYMBOL_TO_ID:
            return SYMBOL_TO_ID[upper_symbol]
        # Fallback: convert to lowercase (works for many coins)
        return symbol.lower()

    def get_current_prices(
        self, symbols: list[str], vs_currency: str = "usd"
    ) -> dict[str, Decimal]:
        """Get current prices for multiple cryptocurrencies.

        Args:
            symbols: List of crypto symbols (e.g., ["BTC", "ETH"])
            vs_currency: Quote currency (default: "usd")

        Returns:
            Dict mapping symbol to current price
        """
        if not symbols:
            return {}

        # Convert symbols to CoinGecko IDs
        symbol_to_id_map = {s: self._symbol_to_id(s) for s in symbols}
        ids = list(symbol_to_id_map.values())

        params = {
            "ids": ",".join(ids),
            "vs_currencies": vs_currency,
            "include_last_updated_at": "true",
        }

        try:
            result = self._request("/simple/price", params)
        except CoinGeckoAPIError as e:
            logger.error(f"Failed to fetch prices: {e}")
            return {}

        # Map results back to original symbols
        prices: dict[str, Decimal] = {}
        id_to_symbol = {v: k for k, v in symbol_to_id_map.items()}

        for coin_id, data in result.items():
            symbol = id_to_symbol.get(coin_id)
            if symbol and vs_currency in data:
                prices[symbol] = Decimal(str(data[vs_currency]))

        logger.info(f"Fetched prices for {len(prices)}/{len(symbols)} cryptocurrencies")
        return prices

    def get_current_price(self, symbol: str, vs_currency: str = "usd") -> Decimal | None:
        """Get current price for a single cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            vs_currency: Quote currency (default: "usd")

        Returns:
            Current price as Decimal, or None if not found
        """
        prices = self.get_current_prices([symbol], vs_currency)
        return prices.get(symbol)

    def get_historical_price(
        self, symbol: str, target_date: date, vs_currency: str = "usd"
    ) -> Decimal | None:
        """Get historical price for a specific date.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            target_date: Date for historical price
            vs_currency: Quote currency (default: "usd")

        Returns:
            Price on that date, or None if unavailable
        """
        coin_id = self._symbol_to_id(symbol)
        # CoinGecko expects date in dd-mm-yyyy format
        date_str = target_date.strftime("%d-%m-%Y")

        params = {"date": date_str, "localization": "false"}

        try:
            result = self._request(f"/coins/{coin_id}/history", params)
        except CoinGeckoAPIError as e:
            logger.error(f"Failed to fetch historical price for {symbol}: {e}")
            return None

        price = result.get("market_data", {}).get("current_price", {}).get(vs_currency)
        if price is not None:
            return Decimal(str(price))

        logger.warning(f"No historical price found for {symbol} on {target_date}")
        return None

    def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        vs_currency: str = "usd",
    ) -> list[tuple[date, Decimal]]:
        """Get price history for date range.

        Args:
            symbol: Crypto symbol
            start_date: Start of range
            end_date: End of range
            vs_currency: Quote currency

        Returns:
            List of (date, price) tuples
        """
        coin_id = self._symbol_to_id(symbol)

        # Convert dates to UNIX timestamps
        start_ts = int(
            datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC).timestamp()
        )
        end_ts = int(
            datetime.combine(end_date, datetime.max.time()).replace(tzinfo=UTC).timestamp()
        )

        params = {
            "vs_currency": vs_currency,
            "from": str(start_ts),
            "to": str(end_ts),
        }

        try:
            result = self._request(f"/coins/{coin_id}/market_chart/range", params)
        except CoinGeckoAPIError as e:
            logger.error(f"Failed to fetch price history for {symbol}: {e}")
            return []

        prices_data = result.get("prices", [])
        history: list[tuple[date, Decimal]] = []

        for timestamp_ms, price in prices_data:
            if price is not None:
                dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                history.append((dt.date(), Decimal(str(price))))

        logger.info(f"Fetched {len(history)} historical prices for {symbol}")
        return history

    def get_coin_list(self) -> list[dict[str, str]]:
        """Get list of all supported coins.

        Returns:
            List of dicts with 'id', 'symbol', 'name' keys
        """
        try:
            return self._request("/coins/list")
        except CoinGeckoAPIError as e:
            logger.error(f"Failed to fetch coin list: {e}")
            return []

    def get_coin_info(self, symbol: str) -> dict[str, str | list[str]] | None:
        """Get coin metadata (name, categories) from CoinGecko.

        Args:
            symbol: Crypto symbol (e.g., "BTC")

        Returns:
            Dict with 'name' and 'categories' keys, or None if not found.
            Example: {"name": "Bitcoin", "categories": ["Cryptocurrency", "Layer 1 (L1)"]}
        """
        coin_id = self._symbol_to_id(symbol)

        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }

        try:
            result = self._request(f"/coins/{coin_id}", params)
            return {
                "name": result.get("name", symbol),
                "categories": result.get("categories", []),
            }
        except CoinGeckoAPIError as e:
            logger.error(f"Failed to fetch coin info for {symbol}: {e}")
            return None

    def add_symbol_mapping(self, symbol: str, coin_id: str) -> None:
        """Add or update a symbol to CoinGecko ID mapping.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            coin_id: CoinGecko coin ID (e.g., "bitcoin")
        """
        SYMBOL_TO_ID[symbol.upper()] = coin_id
        logger.debug(f"Added symbol mapping: {symbol} -> {coin_id}")
