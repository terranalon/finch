"""CryptoCompare API client for historical cryptocurrency prices.

Used for fetching historical prices older than 365 days,
which CoinGecko's free tier cannot provide.
"""

import logging
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

CRYPTOCOMPARE_BASE_URL = "https://min-api.cryptocompare.com"


class CryptoCompareAPIError(Exception):
    """Exception raised for CryptoCompare API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CryptoCompareClient:
    """Client for fetching historical cryptocurrency prices from CryptoCompare.

    This client supplements CoinGecko by providing historical data
    older than 365 days (CoinGecko's free tier limitation).

    Usage:
        client = CryptoCompareClient()
        price = client.get_historical_price("BTC", date(2020, 1, 15))
        history = client.get_price_history("ETH", date(2018, 1, 1), date(2018, 12, 31))
    """

    def __init__(self, api_key: str | None = None):
        """Initialize CryptoCompare client.

        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.base_url = CRYPTOCOMPARE_BASE_URL
        self._last_request_time: float = 0
        self._min_request_interval: float = 1.0  # seconds between requests

    def _get_headers(self) -> dict[str, str]:
        """Get request headers including API key if available."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Apikey {self.api_key}"
        return headers

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, endpoint: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        """Make HTTP request to CryptoCompare API.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response as dictionary

        Raises:
            CryptoCompareAPIError: If API returns an error
        """
        self._rate_limit()
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params, headers=self._get_headers())

                if response.status_code == 429:
                    raise CryptoCompareAPIError("Rate limit exceeded", status_code=429)

                response.raise_for_status()
                data = response.json()

                if data.get("Response") == "Error":
                    raise CryptoCompareAPIError(data.get("Message", "Unknown error"))

                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"CryptoCompare API HTTP error: {e}")
            raise CryptoCompareAPIError(
                f"HTTP error: {e}", status_code=e.response.status_code
            ) from e
        except httpx.HTTPError as e:
            logger.error(f"CryptoCompare API request error: {e}")
            raise CryptoCompareAPIError(f"Request error: {e}") from e

    def get_historical_price(
        self, symbol: str, target_date: date, vs_currency: str = "USD"
    ) -> Decimal | None:
        """Get historical closing price for a specific date.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            target_date: Date for historical price
            vs_currency: Quote currency (default: "USD")

        Returns:
            Closing price on that date, or None if unavailable
        """
        # Convert date to Unix timestamp (end of day)
        target_ts = int(
            datetime.combine(target_date, datetime.max.time()).replace(tzinfo=UTC).timestamp()
        )

        params = {
            "fsym": symbol.upper(),
            "tsym": vs_currency.upper(),
            "limit": 1,
            "toTs": target_ts,
        }

        try:
            result = self._request("/data/v2/histoday", params)
        except CryptoCompareAPIError as e:
            logger.error(f"Failed to fetch historical price for {symbol}: {e}")
            return None

        data_points = result.get("Data", {}).get("Data", [])
        if not data_points:
            logger.warning(f"No historical price found for {symbol} on {target_date}")
            return None

        # Find exact date match, or fall back to last available price
        best_point = None
        for point in data_points:
            point_date = datetime.fromtimestamp(point["time"], tz=UTC).date()
            if point_date == target_date:
                best_point = point
                break
            best_point = point  # Keep last seen as fallback

        close_price = best_point.get("close") if best_point else None
        if close_price and close_price > 0:
            return Decimal(str(close_price))
        return None

    def get_price_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        vs_currency: str = "USD",
    ) -> list[tuple[date, Decimal]]:
        """Get price history for date range.

        Fetches up to 2000 data points per request. For longer ranges,
        makes multiple requests automatically.

        Args:
            symbol: Crypto symbol
            start_date: Start of range
            end_date: End of range
            vs_currency: Quote currency

        Returns:
            List of (date, price) tuples sorted by date
        """
        all_prices: list[tuple[date, Decimal]] = []
        current_end = end_date

        while current_end >= start_date:
            # Calculate how many days we need
            days_needed = (current_end - start_date).days + 1
            limit = min(days_needed, 2000)

            end_ts = int(
                datetime.combine(current_end, datetime.max.time()).replace(tzinfo=UTC).timestamp()
            )

            params = {
                "fsym": symbol.upper(),
                "tsym": vs_currency.upper(),
                "limit": limit,
                "toTs": end_ts,
            }

            try:
                result = self._request("/data/v2/histoday", params)
            except CryptoCompareAPIError as e:
                logger.error(f"Failed to fetch price history for {symbol}: {e}")
                break

            data_points = result.get("Data", {}).get("Data", [])
            if not data_points:
                break

            batch_prices = []
            oldest_date = current_end

            for point in data_points:
                point_date = datetime.fromtimestamp(point["time"], tz=UTC).date()
                close_price = point.get("close")

                if (
                    start_date <= point_date <= end_date
                    and close_price is not None
                    and close_price > 0
                ):
                    batch_prices.append((point_date, Decimal(str(close_price))))
                    if point_date < oldest_date:
                        oldest_date = point_date

            all_prices.extend(batch_prices)

            # Move to the next batch (before the oldest date we got)
            if oldest_date <= start_date:
                break
            current_end = oldest_date - timedelta(days=1)

            # Avoid infinite loop if no progress
            if not batch_prices:
                break

        # Sort by date and remove duplicates using dict (preserves first occurrence)
        unique_prices = list(dict(sorted(all_prices, key=lambda x: x[0])).items())

        logger.info(f"Fetched {len(unique_prices)} historical prices for {symbol}")
        return unique_prices

    def get_coin_inception_date(self, symbol: str, vs_currency: str = "USD") -> date | None:
        """Get the earliest available date for a coin.

        Args:
            symbol: Crypto symbol
            vs_currency: Quote currency

        Returns:
            Earliest date with price data, or None if not found
        """
        # Request max limit starting from Unix epoch
        params = {
            "fsym": symbol.upper(),
            "tsym": vs_currency.upper(),
            "limit": 1,
            "toTs": int(datetime(2010, 1, 1, tzinfo=UTC).timestamp()),  # Early enough for BTC
        }

        try:
            result = self._request("/data/v2/histoday", params)
        except CryptoCompareAPIError:
            return None

        time_from = result.get("Data", {}).get("TimeFrom")
        if time_from:
            return datetime.fromtimestamp(time_from, tz=UTC).date()

        return None
