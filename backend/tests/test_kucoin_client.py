"""Tests for KuCoin API client."""

import base64
import hashlib
import hmac
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.brokers.kucoin.client import (
    KuCoinAPIError,
    KuCoinClient,
    KuCoinCredentials,
)


class TestKuCoinClientSignature:
    """Tests for KuCoin HMAC-SHA256 signature generation."""

    def test_generate_signature(self):
        credentials = KuCoinCredentials(
            api_key="test_key", api_secret="test_secret", api_passphrase="test_pass"
        )
        client = KuCoinClient(credentials)

        timestamp = "1705312200000"
        method = "GET"
        endpoint = "/api/v1/accounts"
        body = ""

        signature = client._generate_signature(timestamp, method, endpoint, body)

        assert isinstance(signature, str)
        # Verify by recomputing
        str_to_sign = timestamp + method + endpoint + body
        expected = base64.b64encode(
            hmac.new(
                b"test_secret",
                str_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        assert signature == expected

    def test_signature_changes_with_params(self):
        credentials = KuCoinCredentials("key", "secret", "pass")
        client = KuCoinClient(credentials)

        sig1 = client._generate_signature("1000", "GET", "/api/v1/accounts", "")
        sig2 = client._generate_signature("2000", "GET", "/api/v1/accounts", "")

        assert sig1 != sig2

    def test_encrypt_passphrase(self):
        """KuCoin API v2 encrypts the passphrase with the secret."""
        credentials = KuCoinCredentials("key", "test_secret", "test_pass")
        client = KuCoinClient(credentials)

        encrypted = client._encrypt_passphrase()

        expected = base64.b64encode(
            hmac.new(
                b"test_secret",
                b"test_pass",
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        assert encrypted == expected


class TestKuCoinClientParsing:
    """Tests for response parsing methods."""

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("key", "secret", "pass"))

    def test_parse_fill_buy(self, client):
        fill = {
            "symbol": "BTC-USDT",
            "tradeId": "trade123",
            "orderId": "order123",
            "side": "buy",
            "price": "42000.00",
            "size": "0.5",
            "funds": "21000.00",
            "fee": "10.50",
            "feeCurrency": "USDT",
            "createdAt": 1705312200000,
        }

        result = client._parse_fill(fill)

        assert result is not None
        assert result.symbol == "BTC"
        assert result.transaction_type == "Buy"
        assert result.quantity == Decimal("0.5")
        assert result.price_per_unit == Decimal("42000.00")
        assert result.amount == Decimal("21000.00")
        assert result.fees == Decimal("10.50")
        assert result.currency == "USDT"
        assert result.trade_date == date(2024, 1, 15)

    def test_parse_fill_sell(self, client):
        fill = {
            "symbol": "ETH-USDT",
            "tradeId": "trade456",
            "orderId": "order456",
            "side": "sell",
            "price": "2500.00",
            "size": "2.0",
            "funds": "5000.00",
            "fee": "2.50",
            "feeCurrency": "USDT",
            "createdAt": 1705758600000,
        }

        result = client._parse_fill(fill)

        assert result is not None
        assert result.transaction_type == "Sell"
        assert result.quantity == Decimal("2.0")

    def test_parse_deposit(self, client):
        deposit = {
            "currency": "BTC",
            "amount": "0.5",
            "fee": "0",
            "status": "SUCCESS",
            "createdAt": 1704873600000,
        }

        result = client._parse_deposit(deposit)

        assert result is not None
        assert result.transaction_type == "Deposit"
        assert result.amount == Decimal("0.5")
        assert result.currency == "BTC"
        assert result.date == date(2024, 1, 10)

    def test_parse_deposit_filters_failed(self, client):
        deposit = {
            "currency": "BTC",
            "amount": "0.5",
            "fee": "0",
            "status": "PROCESSING",
            "createdAt": 1704873600000,
        }

        result = client._parse_deposit(deposit)
        assert result is None

    def test_parse_withdrawal(self, client):
        withdrawal = {
            "currency": "ETH",
            "amount": "1.0",
            "fee": "0.005",
            "status": "SUCCESS",
            "createdAt": 1706781600000,
        }

        result = client._parse_withdrawal(withdrawal)

        assert result is not None
        assert result.transaction_type == "Withdrawal"
        assert result.amount == Decimal("-1.0")
        assert result.currency == "ETH"

    def test_parse_withdrawal_filters_failed(self, client):
        withdrawal = {
            "currency": "ETH",
            "amount": "1.0",
            "fee": "0.005",
            "status": "FAILURE",
            "createdAt": 1706781600000,
        }

        result = client._parse_withdrawal(withdrawal)
        assert result is None


class TestKuCoinClientAPIRequests:
    """Tests for API request handling with mocked responses."""

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("test_key", "test_secret", "test_pass"))

    @patch("app.services.brokers.kucoin.client.httpx.Client")
    def test_get_account_balances(self, mock_client_class, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "200000",
            "data": [
                {
                    "id": "1",
                    "currency": "BTC",
                    "type": "trade",
                    "balance": "0.5",
                    "available": "0.4",
                    "holds": "0.1",
                },
                {
                    "id": "2",
                    "currency": "ETH",
                    "type": "trade",
                    "balance": "2.0",
                    "available": "2.0",
                    "holds": "0",
                },
                {
                    "id": "3",
                    "currency": "USDT",
                    "type": "trade",
                    "balance": "0",
                    "available": "0",
                    "holds": "0",
                },
                {
                    "id": "4",
                    "currency": "BTC",
                    "type": "main",
                    "balance": "1.0",
                    "available": "1.0",
                    "holds": "0",
                },
            ],
        }
        mock_response.status_code = 200

        mock_http = MagicMock()
        mock_http.get.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_http

        balances = client.get_account_balances()

        # Only trade accounts, only non-zero
        assert "BTC" in balances
        assert balances["BTC"] == Decimal("0.5")
        assert "ETH" in balances
        assert balances["ETH"] == Decimal("2.0")
        assert "USDT" not in balances  # Zero balance

    @patch("app.services.brokers.kucoin.client.httpx.Client")
    def test_api_error_handling(self, mock_client_class, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "400100",
            "msg": "Invalid API-KEY",
        }
        mock_response.status_code = 200

        mock_http = MagicMock()
        mock_http.get.return_value = mock_response
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_http

        with pytest.raises(KuCoinAPIError) as exc_info:
            client.get_account_balances()

        assert "Invalid API-KEY" in str(exc_info.value)


class TestKuCoinClientFetchAllData:
    """Tests for the fetch_all_data method."""

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("key", "secret", "pass"))

    @patch.object(KuCoinClient, "get_account_balances")
    @patch.object(KuCoinClient, "_fetch_all_fills")
    @patch.object(KuCoinClient, "_fetch_all_deposits")
    @patch.object(KuCoinClient, "_fetch_all_withdrawals")
    @patch.object(KuCoinClient, "_fetch_staking_rewards")
    def test_fetch_all_data_returns_broker_import_data(
        self,
        mock_staking,
        mock_withdrawals,
        mock_deposits,
        mock_fills,
        mock_balances,
        client,
    ):
        mock_balances.return_value = {"BTC": Decimal("1.0"), "ETH": Decimal("5.0")}
        mock_fills.return_value = []
        mock_deposits.return_value = []
        mock_withdrawals.return_value = []
        mock_staking.return_value = []

        result = client.fetch_all_data(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))

        assert result is not None
        assert len(result.positions) == 2

        btc_pos = next(p for p in result.positions if p.symbol == "BTC")
        assert btc_pos.quantity == Decimal("1.0")
        assert btc_pos.asset_class == "Crypto"

    @patch.object(KuCoinClient, "get_account_balances")
    @patch.object(KuCoinClient, "_fetch_all_fills")
    @patch.object(KuCoinClient, "_fetch_all_deposits")
    @patch.object(KuCoinClient, "_fetch_all_withdrawals")
    @patch.object(KuCoinClient, "_fetch_staking_rewards")
    def test_fetch_all_data_handles_api_errors(
        self,
        mock_staking,
        mock_withdrawals,
        mock_deposits,
        mock_fills,
        mock_balances,
        client,
    ):
        mock_balances.side_effect = KuCoinAPIError("API Error")
        mock_fills.return_value = []
        mock_deposits.return_value = []
        mock_withdrawals.return_value = []
        mock_staking.return_value = []

        result = client.fetch_all_data()

        assert result is not None
        assert len(result.positions) == 0
