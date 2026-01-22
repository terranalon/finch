"""Tests for Binance API client."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.binance_client import (
    BinanceAPIError,
    BinanceClient,
    BinanceCredentials,
)


class TestBinanceClientSignature:
    """Tests for Binance HMAC-SHA256 signature generation."""

    def test_generate_signature(self):
        """Test that signature is generated correctly."""
        credentials = BinanceCredentials(api_key="test_key", api_secret="test_secret")
        client = BinanceClient(credentials)

        # Known test case from Binance docs
        query_string = "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
        signature = client._generate_signature(query_string)

        # Signature should be a 64-character hex string
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_signature_changes_with_params(self):
        """Test that different params produce different signatures."""
        credentials = BinanceCredentials(api_key="test_key", api_secret="test_secret")
        client = BinanceClient(credentials)

        sig1 = client._generate_signature("timestamp=1000")
        sig2 = client._generate_signature("timestamp=2000")

        assert sig1 != sig2

    def test_signature_changes_with_secret(self):
        """Test that different secrets produce different signatures."""
        client1 = BinanceClient(BinanceCredentials("key", "secret1"))
        client2 = BinanceClient(BinanceCredentials("key", "secret2"))

        sig1 = client1._generate_signature("timestamp=1000")
        sig2 = client2._generate_signature("timestamp=1000")

        assert sig1 != sig2


class TestBinanceClientTimestamp:
    """Tests for timestamp generation."""

    def test_get_timestamp_returns_milliseconds(self):
        credentials = BinanceCredentials(api_key="key", api_secret="secret")
        client = BinanceClient(credentials)

        timestamp = client._get_timestamp()

        # Should be in milliseconds (13+ digits)
        assert timestamp > 1000000000000
        assert isinstance(timestamp, int)


class TestBinanceClientRateLimiting:
    """Tests for rate limiting logic."""

    def test_rate_limit_tracking(self):
        credentials = BinanceCredentials(api_key="key", api_secret="secret")
        client = BinanceClient(credentials)

        # Initial weight should be 0
        assert client._weight_used == 0

        # Simulate adding weight
        client._check_rate_limit(20)
        assert client._weight_used == 20

        client._check_rate_limit(30)
        assert client._weight_used == 50


class TestBinanceClientParsing:
    """Tests for response parsing methods."""

    @pytest.fixture
    def client(self):
        return BinanceClient(BinanceCredentials("key", "secret"))

    def test_parse_trade_buy(self, client):
        trade = {
            "symbol": "BTCUSDT",
            "id": 28457,
            "orderId": 100234,
            "price": "42000.00",
            "qty": "0.5",
            "quoteQty": "21000.00",
            "commission": "10.50",
            "commissionAsset": "USDT",
            "time": 1705312200000,  # 2024-01-15 10:30:00 UTC
            "isBuyer": True,
            "isMaker": False,
        }

        result = client._parse_trade(trade, "BTCUSDT")

        assert result is not None
        assert result.symbol == "BTC"
        assert result.transaction_type == "Buy"
        assert result.quantity == Decimal("0.5")
        assert result.price_per_unit == Decimal("42000.00")
        assert result.amount == Decimal("21000.00")
        assert result.fees == Decimal("10.50")
        assert result.currency == "USDT"

    def test_parse_trade_sell(self, client):
        trade = {
            "symbol": "BTCUSDT",
            "id": 28458,
            "price": "43500.00",
            "qty": "0.25",
            "quoteQty": "10875.00",
            "commission": "5.44",
            "time": 1705413900000,
            "isBuyer": False,
        }

        result = client._parse_trade(trade, "BTCUSDT")

        assert result.transaction_type == "Sell"
        assert result.quantity == Decimal("0.25")

    def test_parse_deposit(self, client):
        deposit = {
            "id": "769800519366885376",
            "amount": "0.5",
            "coin": "BTC",
            "network": "BTC",
            "status": 1,
            "address": "1HPn8Rx...",
            "txId": "b3c6abc123",
            "insertTime": 1704873600000,  # 2024-01-10 08:00:00 UTC
        }

        result = client._parse_deposit(deposit)

        assert result is not None
        assert result.transaction_type == "Deposit"
        assert result.amount == Decimal("0.5")
        assert result.currency == "BTC"
        assert result.date == date(2024, 1, 10)
        assert "b3c6abc123" in result.notes

    def test_parse_withdrawal(self, client):
        withdrawal = {
            "id": "withdrawal123",
            "amount": "1.0",
            "transactionFee": "0.0005",
            "coin": "ETH",
            "status": 6,
            "address": "0x...",
            "txId": "0xabc123",
            "applyTime": "2024-02-01 09:00:00",
        }

        result = client._parse_withdrawal(withdrawal)

        assert result is not None
        assert result.transaction_type == "Withdrawal"
        assert result.amount == Decimal("-1.0")  # Negative for withdrawal
        assert result.currency == "ETH"
        assert result.date == date(2024, 2, 1)
        assert "0.0005" in result.notes


class TestBinanceClientAPIRequests:
    """Tests for API request handling with mocked responses."""

    @pytest.fixture
    def client(self):
        return BinanceClient(BinanceCredentials("test_key", "test_secret"))

    @patch("app.services.binance_client.httpx.Client")
    def test_get_account_balances(self, mock_client_class, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0.1"},
                {"asset": "ETH", "free": "2.0", "locked": "0.0"},
                {"asset": "USDT", "free": "0.0", "locked": "0.0"},  # Zero balance
            ]
        }
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        balances = client.get_account_balances()

        assert "BTC" in balances
        assert balances["BTC"] == Decimal("0.6")  # free + locked
        assert "ETH" in balances
        assert balances["ETH"] == Decimal("2.0")
        assert "USDT" not in balances  # Zero balance excluded

    @patch("app.services.binance_client.httpx.Client")
    def test_api_error_handling(self, mock_client_class, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": -1021,
            "msg": "Timestamp for this request is outside of the recvWindow.",
        }
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(BinanceAPIError) as exc_info:
            client.get_account_balances()

        assert exc_info.value.code == -1021
        assert "recvWindow" in str(exc_info.value)


class TestBinanceClientFetchAllData:
    """Tests for the fetch_all_data method."""

    @pytest.fixture
    def client(self):
        return BinanceClient(BinanceCredentials("key", "secret"))

    @patch.object(BinanceClient, "get_account_balances")
    @patch.object(BinanceClient, "get_trade_history")
    @patch.object(BinanceClient, "get_deposit_history")
    @patch.object(BinanceClient, "get_withdrawal_history")
    def test_fetch_all_data_returns_broker_import_data(
        self, mock_withdrawals, mock_deposits, mock_trades, mock_balances, client
    ):
        mock_balances.return_value = {"BTC": Decimal("1.0"), "ETH": Decimal("5.0")}
        mock_trades.return_value = []
        mock_deposits.return_value = []
        mock_withdrawals.return_value = []

        result = client.fetch_all_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result is not None
        assert len(result.positions) == 2

        # Check positions
        btc_pos = next(p for p in result.positions if p.symbol == "BTC")
        assert btc_pos.quantity == Decimal("1.0")
        assert btc_pos.asset_class == "Crypto"

    @patch.object(BinanceClient, "get_account_balances")
    @patch.object(BinanceClient, "get_trade_history")
    @patch.object(BinanceClient, "get_deposit_history")
    @patch.object(BinanceClient, "get_withdrawal_history")
    def test_fetch_all_data_handles_api_errors(
        self, mock_withdrawals, mock_deposits, mock_trades, mock_balances, client
    ):
        # Simulate API error for balances
        mock_balances.side_effect = BinanceAPIError("API Error")
        mock_trades.return_value = []
        mock_deposits.return_value = []
        mock_withdrawals.return_value = []

        # Should not raise, just return empty positions
        result = client.fetch_all_data()

        assert result is not None
        assert len(result.positions) == 0
