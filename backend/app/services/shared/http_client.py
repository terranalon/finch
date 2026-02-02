"""Base HTTP client with retry logic, timeouts, and error handling.

All external API clients should inherit from this class to get consistent
behavior for retries, timeouts, and error handling.
"""

import logging
from typing import Any, Self

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HTTPClient:
    """Base HTTP client with retry logic, timeouts, and error handling.

    All external API clients should inherit from this class.

    Example usage:
        class CoinGeckoClient(HTTPClient):
            def __init__(self):
                super().__init__(
                    base_url="https://api.coingecko.com/api/v3",
                    timeout=30.0,
                )

            def get_price(self, coin_id: str) -> dict:
                return self.get_json(f"/simple/price?ids={coin_id}&vs_currencies=usd")
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = headers or {}
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.default_headers,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    def _request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: URL path (will be joined with base_url if set)
            params: Query parameters
            json: JSON body (for POST/PUT)
            data: Form data (for POST/PUT)
            headers: Additional headers to merge with defaults

        Returns:
            httpx.Response object

        Raises:
            HTTPClientError: On HTTP errors, timeouts, or connection failures
        """
        merged_headers = {**self.default_headers, **(headers or {})}

        try:
            response = self.client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=merged_headers,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP {e.response.status_code} for {method} {url}: {e.response.text[:200]}"
            )
            raise HTTPClientError(
                message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout for {method} {url}")
            raise HTTPClientError(f"Request timed out: {url}") from e
        except httpx.ConnectError as e:
            logger.warning(f"Connection error for {method} {url}: {e}")
            raise HTTPClientError(f"Connection failed: {url}") from e

    def get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """HTTP GET request."""
        return self._request("GET", url, params=params, headers=headers)

    def post(
        self,
        url: str,
        json: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """HTTP POST request."""
        return self._request("POST", url, json=json, data=data, headers=headers)

    def put(
        self,
        url: str,
        json: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """HTTP PUT request."""
        return self._request("PUT", url, json=json, data=data, headers=headers)

    def delete(self, url: str, headers: dict | None = None) -> httpx.Response:
        """HTTP DELETE request."""
        return self._request("DELETE", url, headers=headers)

    def get_json(self, url: str, params: dict | None = None) -> Any:
        """HTTP GET returning parsed JSON."""
        response = self.get(url, params=params)
        return response.json()

    def post_json(self, url: str, json: dict | None = None) -> Any:
        """HTTP POST returning parsed JSON."""
        response = self.post(url, json=json)
        return response.json()
