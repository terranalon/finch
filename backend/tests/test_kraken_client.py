"""Tests for Kraken API client."""

import base64
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.kraken_client import (
    KrakenAPIError,
    KrakenClient,
    KrakenCredentials,
)


@pytest.fixture
def mock_credentials() -> KrakenCredentials:
    """Create mock Kraken credentials."""
    # Base64 encoded secret for testing
    test_secret = base64.b64encode(b"test_secret_key_32_bytes_long!!!").decode()
    return KrakenCredentials(
        api_key="test_api_key",
        api_secret=test_secret,
    )


@pytest.fixture
def client(mock_credentials: KrakenCredentials) -> KrakenClient:
    """Create a KrakenClient instance."""
    return KrakenClient(mock_credentials)


class TestKrakenClientAuth:
    """Test authentication and signing."""

    def test_nonce_increases(self, client: KrakenClient):
        """Test that nonce always increases."""
        nonce1 = client._get_nonce()
        nonce2 = client._get_nonce()
        nonce3 = client._get_nonce()

        assert nonce2 > nonce1
        assert nonce3 > nonce2

    def test_sign_request(self, client: KrakenClient):
        """Test request signing generates valid signature."""
        uri_path = "/0/private/Balance"
        data = {"nonce": 1234567890}

        signature = client._sign_request(uri_path, data)

        # Signature should be base64 encoded
        assert isinstance(signature, str)
        # Should be able to decode it
        decoded = base64.b64decode(signature)
        # HMAC-SHA512 produces 64 bytes
        assert len(decoded) == 64


class TestKrakenClientAssetMapping:
    """Test asset name normalization."""

    def test_normalize_btc(self, client: KrakenClient):
        """Test BTC normalization."""
        assert client._normalize_asset("XXBT") == "BTC"
        assert client._normalize_asset("XBT") == "BTC"

    def test_normalize_eth(self, client: KrakenClient):
        """Test ETH normalization."""
        assert client._normalize_asset("XETH") == "ETH"

    def test_normalize_usd(self, client: KrakenClient):
        """Test USD normalization."""
        assert client._normalize_asset("ZUSD") == "USD"

    def test_normalize_staked(self, client: KrakenClient):
        """Test staked asset normalization."""
        assert client._normalize_asset("XXBT.S") == "BTC"
        assert client._normalize_asset("XETH.F") == "ETH"


class TestKrakenClientBalance:
    """Test balance fetching."""

    def test_get_balance_success(self, client: KrakenClient):
        """Test successful balance fetch."""
        mock_response = {
            "error": [],
            "result": {
                "ZUSD": "1000.5000",
                "XXBT": "0.50000000",
                "XETH": "2.00000000",
            },
        }

        with patch.object(client, "_private_request", return_value=mock_response["result"]):
            balances = client.get_balance()

        assert balances["USD"] == Decimal("1000.5000")
        assert balances["BTC"] == Decimal("0.50000000")
        assert balances["ETH"] == Decimal("2.00000000")

    def test_get_balance_aggregates_staked(self, client: KrakenClient):
        """Test that staked and regular balances are aggregated."""
        mock_response = {
            "error": [],
            "result": {
                "XXBT": "0.50000000",
                "XXBT.S": "0.10000000",  # Staked BTC
            },
        }

        with patch.object(client, "_private_request", return_value=mock_response["result"]):
            balances = client.get_balance()

        # Both should aggregate to BTC
        assert balances["BTC"] == Decimal("0.60000000")


class TestKrakenClientLedgers:
    """Test ledger fetching."""

    def test_get_ledgers_success(self, client: KrakenClient):
        """Test successful ledger fetch."""
        mock_response = {
            "ledger": {
                "L1": {
                    "refid": "REF1",
                    "time": 1705312200.0,
                    "type": "deposit",
                    "asset": "ZUSD",
                    "amount": "1000.0000",
                    "fee": "0.0000",
                    "balance": "1000.0000",
                },
            },
            "count": 1,
        }

        with patch.object(client, "_private_request", return_value=mock_response):
            ledgers, count = client.get_ledgers()

        assert count == 1
        assert len(ledgers) == 1
        assert ledgers[0]["type"] == "deposit"

    def test_get_ledgers_with_filters(self, client: KrakenClient):
        """Test ledger fetch with filters."""
        with patch.object(client, "_private_request") as mock_request:
            mock_request.return_value = {"ledger": {}, "count": 0}

            client.get_ledgers(
                asset="XBT",
                ledger_type="trade",
                start=datetime(2024, 1, 1, tzinfo=UTC),
                end=datetime(2024, 1, 31, tzinfo=UTC),
                offset=50,
            )

            # Check the request data includes all filters
            call_args = mock_request.call_args
            request_data = call_args[0][1]
            assert request_data["asset"] == "XBT"
            assert request_data["type"] == "trade"
            assert "start" in request_data
            assert "end" in request_data
            assert request_data["ofs"] == 50


class TestKrakenClientTrades:
    """Test trade history fetching."""

    def test_get_trades_history_success(self, client: KrakenClient):
        """Test successful trades fetch."""
        mock_response = {
            "trades": {
                "T1": {
                    "pair": "XXBTZUSD",
                    "time": 1705312200.0,
                    "type": "buy",
                    "price": "50000.00",
                    "cost": "500.00",
                    "fee": "0.50",
                    "vol": "0.01",
                },
            },
            "count": 1,
        }

        with patch.object(client, "_private_request", return_value=mock_response):
            trades, count = client.get_trades_history()

        assert count == 1
        assert len(trades) == 1
        assert trades[0]["type"] == "buy"


class TestKrakenClientErrors:
    """Test error handling."""

    def test_api_error_handling(self, client: KrakenClient):
        """Test API error is raised properly."""
        mock_json = MagicMock(return_value={"error": ["EAPI:Rate limit exceeded"], "result": {}})
        mock_response = MagicMock()
        mock_response.json = mock_json
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(KrakenAPIError, match="Rate limit"):
                client._private_request("/0/private/Balance")


class TestKrakenClientFetchAll:
    """Test fetch_all_data method."""

    def test_fetch_all_data_basic(self, client: KrakenClient):
        """Test fetching all data returns BrokerImportData."""
        # Mock balance response
        balance_response = {
            "ZUSD": "1000.0000",
            "XXBT": "0.10000000",
        }

        # Mock ledger response
        ledger_response = {
            "ledger": {
                "L1": {
                    "refid": "REF1",
                    "time": 1705312200.0,
                    "type": "deposit",
                    "asset": "ZUSD",
                    "amount": "1000.0000",
                    "fee": "0.0000",
                },
            },
            "count": 1,
        }

        def mock_private_request(endpoint, data=None, timeout=30.0):
            if "Balance" in endpoint:
                return balance_response
            elif "Ledgers" in endpoint:
                return ledger_response
            return {}

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # Should have positions from balance
        assert len(result.positions) == 2
        # Should have cash transactions from ledger
        assert len(result.cash_transactions) == 1
        assert result.cash_transactions[0].transaction_type == "Deposit"
