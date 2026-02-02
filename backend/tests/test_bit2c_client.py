"""Tests for Bit2C API client."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.brokers.bit2c.client import (
    Bit2CClient,
    Bit2CCredentials,
)


@pytest.fixture
def mock_credentials() -> Bit2CCredentials:
    """Create mock Bit2C credentials."""
    return Bit2CCredentials(
        api_key="test-api-key-12345",
        api_secret="test-secret-key-67890",
    )


@pytest.fixture
def client(mock_credentials: Bit2CCredentials) -> Bit2CClient:
    """Create a Bit2CClient instance."""
    return Bit2CClient(mock_credentials)


class TestBit2CClientAuth:
    """Test authentication and signing."""

    def test_nonce_increases(self, client: Bit2CClient):
        """Test that nonce always increases."""
        nonce1 = client._get_nonce()
        nonce2 = client._get_nonce()
        nonce3 = client._get_nonce()

        assert nonce2 > nonce1
        assert nonce3 > nonce2

    def test_sign_request(self, client: Bit2CClient):
        """Test request signing generates valid signature."""
        params = "nonce=12345&pair=BtcNis"

        signature = client._sign_request(params)

        # Signature should be base64 encoded
        assert isinstance(signature, str)
        # Should be non-empty
        assert len(signature) > 0


class TestBit2CClientBalance:
    """Test balance fetching."""

    def test_get_balance_success(self, client: Bit2CClient):
        """Test successful balance fetch."""
        mock_response = {
            "AVAILABLE_NIS": 1000.50,
            "NIS": 1000.50,
            "AVAILABLE_BTC": 0.5,
            "BTC": 0.5,
            "AVAILABLE_ETH": 2.0,
            "ETH": 2.0,
            "AVAILABLE_LTC": 0.0,
            "LTC": 0.0,
            "AVAILABLE_USDC": 100.0,
            "USDC": 100.0,
        }

        with patch.object(client, "_private_request", return_value=mock_response):
            balances = client.get_balance()

        assert balances["ILS"] == Decimal("1000.50")
        assert balances["BTC"] == Decimal("0.5")
        assert balances["ETH"] == Decimal("2.0")
        assert balances["USDC"] == Decimal("100.0")
        # Zero balances should not be included
        assert "LTC" not in balances


class TestBit2CClientHistory:
    """Test order history fetching."""

    def test_get_order_history_success(self, client: Bit2CClient):
        """Test successful order history fetch."""
        # Use actual API response format
        mock_response = [
            {
                "ticks": 1705674005,
                "created": "15/01/24 10:30",
                "action": 0,  # Buy
                "price": "250,000",
                "pair": "BtcNis",
                "reference": "BtcNis|12345|12346",
                "fee": "2.50000",
                "feeAmount": "12.50",
                "feeCoin": "₪",
                "firstAmount": "0.01",
                "firstAmountBalance": "0.01",
                "secondAmount": "-2,512.50",
                "secondAmountBalance": "0",
                "firstCoin": "BTC",
                "secondCoin": "₪",
                "isMaker": True,
            },
            {
                "ticks": 1705760405,
                "created": "16/01/24 14:20",
                "action": 1,  # Sell
                "price": "15,000",
                "pair": "EthNis",
                "reference": "EthNis|12347|12348",
                "fee": "2.50000",
                "feeAmount": "37.50",
                "feeCoin": "₪",
                "firstAmount": "0.5",
                "firstAmountBalance": "0",
                "secondAmount": "7,462.50",
                "secondAmountBalance": "7,462.50",
                "firstCoin": "ETH",
                "secondCoin": "₪",
                "isMaker": True,
            },
        ]

        with patch.object(client, "_private_request", return_value=mock_response):
            history = client.get_order_history(
                from_date=datetime(2024, 1, 1),
                to_date=datetime(2024, 1, 31),
                pair="BtcNis",
            )

        assert len(history) == 2
        assert history[0]["action"] == 0  # Buy
        assert history[1]["action"] == 1  # Sell


class TestBit2CClientDataMapping:
    """Test data mapping methods."""

    def test_parse_pair_btc(self, client: Bit2CClient):
        """Test BTC pair parsing."""
        symbol, currency = client._parse_pair("BtcNis")
        assert symbol == "BTC"
        assert currency == "ILS"

    def test_parse_pair_eth(self, client: Bit2CClient):
        """Test ETH pair parsing."""
        symbol, currency = client._parse_pair("EthNis")
        assert symbol == "ETH"
        assert currency == "ILS"

    def test_parse_pair_usdc(self, client: Bit2CClient):
        """Test USDC pair parsing."""
        symbol, currency = client._parse_pair("UsdcNis")
        assert symbol == "USDC"
        assert currency == "ILS"

    def test_parse_decimal_with_commas(self, client: Bit2CClient):
        """Test decimal parsing with comma-formatted strings."""
        assert client._parse_decimal("216,300") == Decimal("216300")
        assert client._parse_decimal("-1,025") == Decimal("-1025")
        assert client._parse_decimal("0.01") == Decimal("0.01")
        assert client._parse_decimal(None) == Decimal("0")


class TestBit2CClientFetchAll:
    """Test fetch_all_data method."""

    def test_fetch_all_data_basic(self, client: Bit2CClient):
        """Test fetching all data returns BrokerImportData."""
        balance_response = {
            "AVAILABLE_NIS": 1000.0,
            "NIS": 1000.0,
            "AVAILABLE_BTC": 0.1,
            "BTC": 0.1,
        }

        # Use actual API response format
        btc_history = [
            {
                "ticks": 1705674005,
                "created": "15/01/24 10:30",
                "action": 0,  # Buy
                "price": "250,000",
                "pair": "BtcNis",
                "reference": "BtcNis|12345|12346",
                "feeAmount": "12.50",
                "firstAmount": "0.01",
                "secondAmount": "-2,512.50",
                "firstCoin": "BTC",
            }
        ]

        def mock_private_request(endpoint, data=None, method="GET"):
            if "Balance" in endpoint:
                return balance_response
            elif "OrderHistory" in endpoint:
                # Only return data for BtcNis pair
                if data and data.get("pair") == "BtcNis":
                    return btc_history
                return []
            elif "FundsHistory" in endpoint:
                return []
            return []

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # Should have positions from balance
        assert len(result.positions) == 2  # ILS and BTC
        # Should have transactions from history
        assert len(result.transactions) == 1
        assert result.transactions[0].transaction_type == "Buy"
        # Should have Trade Settlement
        assert len(result.cash_transactions) == 1
        assert result.cash_transactions[0].transaction_type == "Trade Settlement"


class TestBit2CClientTransactions:
    """Test transaction parsing with dual-entry accounting."""

    def test_buy_creates_crypto_and_settlement(self, client: Bit2CClient):
        """Test that a BUY trade creates crypto transaction AND Trade Settlement."""
        balance_response = {"NIS": 1000.0, "BTC": 0.1}
        btc_history = [
            {
                "ticks": 1705674005,
                "created": "15/01/24 10:30",
                "action": 0,  # Buy
                "price": "250,000",
                "pair": "BtcNis",
                "reference": "BtcNis|12345|12346",
                "feeAmount": "12.50",
                "firstAmount": "0.01",
                "secondAmount": "-2,512.50",
                "firstCoin": "BTC",
            }
        ]
        funds_history = []  # No deposits/withdrawals

        def mock_private_request(endpoint, data=None, method="GET"):
            if "Balance" in endpoint:
                return balance_response
            elif "OrderHistory" in endpoint:
                if data and data.get("pair") == "BtcNis":
                    return btc_history
                return []
            elif "FundsHistory" in endpoint:
                return funds_history
            return []

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # Should have crypto transaction AND Trade Settlement
        assert len(result.transactions) == 1
        assert len(result.cash_transactions) == 1

        # Verify crypto transaction
        crypto_txn = result.transactions[0]
        assert crypto_txn.symbol == "BTC"
        assert crypto_txn.transaction_type == "Buy"
        assert crypto_txn.quantity == Decimal("0.01")
        assert crypto_txn.price_per_unit == Decimal("250000")
        assert crypto_txn.fees == Decimal("12.50")

        # Verify Trade Settlement (negative for buy)
        settlement = result.cash_transactions[0]
        assert settlement.transaction_type == "Trade Settlement"
        assert settlement.currency == "ILS"
        assert settlement.amount < 0  # Buy = cash leaves

    def test_sell_creates_crypto_and_settlement(self, client: Bit2CClient):
        """Test that a SELL trade creates crypto transaction AND Trade Settlement."""
        balance_response = {"NIS": 1000.0, "BTC": 0.1}
        eth_history = [
            {
                "ticks": 1705760405,
                "created": "16/01/24 14:20",
                "action": 1,  # Sell
                "price": "15,000",
                "pair": "EthNis",
                "reference": "EthNis|12347|12348",
                "feeAmount": "37.50",
                "firstAmount": "0.5",
                "secondAmount": "7,462.50",
                "firstCoin": "ETH",
            }
        ]
        funds_history = []

        def mock_private_request(endpoint, data=None, method="GET"):
            if "Balance" in endpoint:
                return balance_response
            elif "OrderHistory" in endpoint:
                if data and data.get("pair") == "EthNis":
                    return eth_history
                return []
            elif "FundsHistory" in endpoint:
                return funds_history
            return []

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # Should have crypto transaction AND Trade Settlement
        assert len(result.transactions) == 1
        assert len(result.cash_transactions) == 1

        # Verify crypto transaction
        crypto_txn = result.transactions[0]
        assert crypto_txn.symbol == "ETH"
        assert crypto_txn.transaction_type == "Sell"
        assert crypto_txn.quantity == Decimal("0.5")

        # Verify Trade Settlement (positive for sell)
        settlement = result.cash_transactions[0]
        assert settlement.transaction_type == "Trade Settlement"
        assert settlement.amount > 0  # Sell = cash received

    def test_funds_history_deposits_and_withdrawals(self, client: Bit2CClient):
        """Test that FundsHistory deposits and withdrawals are parsed correctly.

        ILS deposits/withdrawals go to cash_transactions.
        Crypto deposits/withdrawals go to transactions (for proper quantity tracking).
        """
        balance_response = {"NIS": 1000.0, "BTC": 0.1}
        funds_history = [
            {
                "ticks": 1734339780,
                "created": "16/12/24 07:03",
                "action": 2,  # ILS Deposit
                "price": "",
                "pair": "",
                "reference": "MH_NIS_125704",
                "firstAmount": "15,000",
                "firstCoin": "₪",
            },
            {
                "ticks": 1733526120,
                "created": "06/12/24 23:22",
                "action": 3,  # ETH Withdrawal (crypto)
                "price": "",
                "pair": "",
                "reference": "RX153800",
                "firstAmount": "-0.12386231",
                "firstCoin": "ETH",
            },
            {
                "ticks": 1733526120,
                "created": "06/12/24 23:22",
                "action": 4,  # ETH FeeWithdrawal (crypto)
                "price": "",
                "pair": "",
                "reference": "RX153800",
                "firstAmount": "-0.015",
                "firstCoin": "ETH",
            },
        ]

        def mock_private_request(endpoint, data=None, method="GET"):
            if "Balance" in endpoint:
                return balance_response
            elif "OrderHistory" in endpoint:
                return []
            elif "FundsHistory" in endpoint:
                return funds_history
            return []

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 31),
            )

        # Crypto withdrawals go to transactions, ILS deposit goes to cash_transactions
        assert len(result.transactions) == 2  # ETH withdrawal + ETH fee
        assert len(result.cash_transactions) == 1  # ILS deposit only

        # Verify ILS deposit (positive)
        deposit = result.cash_transactions[0]
        assert deposit.transaction_type == "Deposit"
        assert deposit.amount == Decimal("15000")
        assert deposit.currency == "ILS"

        # Verify ETH withdrawal (negative quantity, uses quantity field)
        withdrawal = [t for t in result.transactions if t.transaction_type == "Withdrawal"][0]
        assert withdrawal.quantity == Decimal("-0.12386231")
        assert withdrawal.symbol == "ETH"

        # Verify ETH withdrawal fee (negative quantity)
        fee = [t for t in result.transactions if t.transaction_type == "Withdrawal Fee"][0]
        assert fee.quantity == Decimal("-0.015")
        assert fee.symbol == "ETH"

    def test_trades_with_deposits_dual_entry(self, client: Bit2CClient):
        """Test that trades create settlements and deposits are included."""
        balance_response = {"NIS": 1000.0, "BTC": 0.1}
        btc_history = [
            {
                "ticks": 1705674005,
                "created": "15/01/24 10:30",
                "action": 0,  # Buy
                "price": "250,000",
                "pair": "BtcNis",
                "reference": "BtcNis|12345|12346",
                "feeAmount": "12.50",
                "firstAmount": "0.01",
                "secondAmount": "-2,512.50",
                "firstCoin": "BTC",
            }
        ]
        funds_history = [
            {
                "ticks": 1705500000,
                "created": "14/01/24 10:00",
                "action": 2,  # Deposit before trade
                "price": "",
                "pair": "",
                "reference": "MH_NIS_12345",
                "firstAmount": "10,000",
                "firstCoin": "₪",
            },
        ]

        def mock_private_request(endpoint, data=None, method="GET"):
            if "Balance" in endpoint:
                return balance_response
            elif "OrderHistory" in endpoint:
                if data and data.get("pair") == "BtcNis":
                    return btc_history
                return []
            elif "FundsHistory" in endpoint:
                return funds_history
            return []

        with patch.object(client, "_private_request", side_effect=mock_private_request):
            result = client.fetch_all_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        # Should have 1 crypto transaction, 2 cash transactions (1 settlement + 1 deposit)
        assert len(result.transactions) == 1
        assert len(result.cash_transactions) == 2

        # Verify we have both types
        types = {t.transaction_type for t in result.cash_transactions}
        assert "Trade Settlement" in types
        assert "Deposit" in types
