"""Tests for Kraken broker parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.services.brokers.kraken.parser import KrakenParser

if TYPE_CHECKING:
    from app.schemas.broker_import import BrokerImportData


@pytest.fixture
def sample_csv_content() -> bytes:
    """Load sample Kraken ledgers CSV."""
    fixture_path = Path(__file__).parent / "fixtures" / "kraken_ledgers_sample.csv"
    return fixture_path.read_bytes()


@pytest.fixture
def parser() -> KrakenParser:
    """Create a KrakenParser instance."""
    return KrakenParser()


@pytest.fixture
def parsed_result(parser: KrakenParser, sample_csv_content: bytes) -> "BrokerImportData":
    """Parse the sample CSV and return the result."""
    return parser.parse(sample_csv_content)


class TestKrakenParserMetadata:
    """Test parser metadata methods."""

    def test_broker_type(self, parser: KrakenParser):
        """Test broker type identifier."""
        assert parser.broker_type() == "kraken"

    def test_broker_name(self, parser: KrakenParser):
        """Test human-readable broker name."""
        assert parser.broker_name() == "Kraken"

    def test_supported_extensions(self, parser: KrakenParser):
        """Test supported file extensions."""
        assert ".csv" in parser.supported_extensions()

    def test_has_api(self, parser: KrakenParser):
        """Test that Kraken has API support."""
        assert parser.has_api() is True


class TestKrakenParserDateRange:
    """Test date range extraction."""

    def test_extract_date_range(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test extracting date range from CSV."""
        start_date, end_date = parser.extract_date_range(sample_csv_content)

        assert start_date == date(2024, 1, 15)
        assert end_date == date(2024, 2, 4)

    def test_extract_date_range_invalid_file(self, parser: KrakenParser):
        """Test error handling for invalid file."""
        with pytest.raises(ValueError, match="(Failed to parse|Empty CSV)"):
            parser.extract_date_range(b"invalid content")


class TestKrakenParserParsing:
    """Test full file parsing."""

    def test_parse_basic_structure(self, parsed_result: "BrokerImportData"):
        """Test basic parsing returns BrokerImportData with correct date range."""
        assert parsed_result.start_date == date(2024, 1, 15)
        assert parsed_result.end_date == date(2024, 2, 4)
        assert parsed_result.total_records > 0


class TestFiatTransactions:
    """Test fiat deposit and withdrawal parsing with fee handling."""

    def test_fiat_deposit_net_amount(self, parsed_result: "BrokerImportData"):
        """Test fiat deposit: net amount = gross - fee."""
        deposits = [t for t in parsed_result.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) == 1

        deposit = deposits[0]
        assert deposit.amount == Decimal("995.0000")
        assert deposit.currency == "USD"
        assert deposit.fees == Decimal("5.0000")

    def test_fiat_withdrawal_net_amount(self, parsed_result: "BrokerImportData"):
        """Test fiat withdrawal: net amount = gross - fee."""
        withdrawals = [
            t for t in parsed_result.cash_transactions if t.transaction_type == "Withdrawal"
        ]
        assert len(withdrawals) == 1

        withdrawal = withdrawals[0]
        assert withdrawal.amount == Decimal("-251.0000")
        assert withdrawal.currency == "USD"
        assert withdrawal.fees == Decimal("1.0000")


class TestCryptoTransactions:
    """Test crypto deposit and withdrawal parsing."""

    def test_crypto_deposit_creates_transaction(self, parsed_result: "BrokerImportData"):
        """Test crypto deposit uses raw amount without fee deduction."""
        crypto_deposits = [t for t in parsed_result.transactions if t.transaction_type == "Deposit"]
        assert len(crypto_deposits) == 1

        deposit = crypto_deposits[0]
        assert deposit.symbol == "ETH"
        assert deposit.quantity == Decimal("1.50000000")
        assert deposit.trade_date == date(2024, 2, 2)

    def test_crypto_withdrawal_creates_transaction(self, parsed_result: "BrokerImportData"):
        """Test crypto withdrawal: net quantity = gross - fee."""
        crypto_withdrawals = [
            t for t in parsed_result.transactions if t.transaction_type == "Withdrawal"
        ]
        assert len(crypto_withdrawals) == 1

        withdrawal = crypto_withdrawals[0]
        assert withdrawal.symbol == "BTC"
        assert withdrawal.quantity == Decimal("-0.00202000")
        assert withdrawal.trade_date == date(2024, 2, 3)


class TestTrades:
    """Test trade parsing with fee handling and Trade Settlement."""

    def test_buy_trade_quantity_subtracts_fee(self, parsed_result: "BrokerImportData"):
        """Test buy trade: quantity = crypto_received - crypto_fee."""
        btc_buys = [
            t
            for t in parsed_result.transactions
            if t.transaction_type == "Buy" and t.symbol == "BTC"
        ]
        assert len(btc_buys) == 1

        buy = btc_buys[0]
        assert buy.quantity == Decimal("0.00990000")
        assert buy.trade_date == date(2024, 1, 16)
        assert buy.fees == Decimal("0.2501")

    def test_sell_trade_quantity_adds_fee(self, parsed_result: "BrokerImportData"):
        """Test sell trade: quantity = abs(crypto_sold) + crypto_fee."""
        btc_sells = [
            t
            for t in parsed_result.transactions
            if t.transaction_type == "Sell" and t.symbol == "BTC"
        ]
        assert len(btc_sells) == 1

        sell = btc_sells[0]
        assert sell.quantity == Decimal("0.00505000")
        assert sell.trade_date == date(2024, 1, 20)

    def test_fiat_trade_creates_settlement(self, parsed_result: "BrokerImportData"):
        """Test fiat-crypto trade creates Trade Settlement cash transaction."""
        settlements = [
            t for t in parsed_result.cash_transactions if t.transaction_type == "Trade Settlement"
        ]
        assert len(settlements) == 1

        settlement = settlements[0]
        assert settlement.amount == Decimal("-500.5000")
        assert settlement.currency == "USD"
        assert settlement.date == date(2024, 1, 16)

    def test_crypto_to_crypto_trade_no_settlement(self, parsed_result: "BrokerImportData"):
        """Test crypto-to-crypto trade does not create Trade Settlement."""
        eth_buys = [
            t
            for t in parsed_result.transactions
            if t.transaction_type == "Buy" and t.symbol == "ETH"
        ]
        assert len(eth_buys) == 1
        assert eth_buys[0].quantity == Decimal("0.05000000")

        settlements = [
            t for t in parsed_result.cash_transactions if t.transaction_type == "Trade Settlement"
        ]
        assert len(settlements) == 1


class TestStakingRewards:
    """Test staking reward parsing with fee handling."""

    def test_staking_net_quantity(self, parsed_result: "BrokerImportData"):
        """Test staking reward: quantity = gross - fee."""
        staking = [d for d in parsed_result.dividends if d.transaction_type == "Staking"]
        assert len(staking) == 1

        reward = staking[0]
        assert reward.symbol == "BTC"
        assert reward.quantity == Decimal("0.00009000")
        assert reward.fees == Decimal("0.00001000")
        assert reward.trade_date == date(2024, 1, 25)


class TestTransfers:
    """Test internal transfer parsing."""

    def test_transfers_create_paired_transactions(self, parsed_result: "BrokerImportData"):
        """Test transfers create matching positive and negative ParsedTransaction entries."""
        transfers = [t for t in parsed_result.transactions if t.transaction_type == "Transfer"]
        assert len(transfers) == 2

        positive_transfer = next(t for t in transfers if t.quantity > 0)
        assert positive_transfer.symbol == "BTC"
        assert positive_transfer.quantity == Decimal("0.00100000")

        negative_transfer = next(t for t in transfers if t.quantity < 0)
        assert negative_transfer.symbol == "BTC"
        assert negative_transfer.quantity == Decimal("-0.00100000")


class TestKrakenAssetMapping:
    """Test Kraken asset name normalization."""

    @pytest.mark.parametrize(
        ("kraken_asset", "expected"),
        [
            ("XXBT", "BTC"),
            ("XBT", "BTC"),
            ("XETH", "ETH"),
            ("ETH", "ETH"),
            ("ZUSD", "USD"),
            ("USD", "USD"),
            ("ZEUR", "EUR"),
            ("XXBT.S", "BTC"),
            ("XETH.S", "ETH"),
            ("XXBT.F", "BTC"),
        ],
    )
    def test_normalize_asset(self, parser: KrakenParser, kraken_asset: str, expected: str):
        """Test Kraken asset names normalize to standard symbols."""
        assert parser._normalize_asset(kraken_asset) == expected


class TestKrakenParserValidation:
    """Test file validation."""

    def test_validate_valid_file(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test validation of valid CSV file."""
        is_valid, error = parser.validate_file(sample_csv_content, "ledgers.csv")
        assert is_valid is True
        assert error is None

    def test_validate_wrong_extension(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test validation rejects wrong extension."""
        is_valid, error = parser.validate_file(sample_csv_content, "ledgers.xlsx")
        assert is_valid is False
        assert "Unsupported file type" in error

    def test_validate_invalid_content(self, parser: KrakenParser):
        """Test validation rejects invalid content."""
        is_valid, error = parser.validate_file(b"not,valid,csv\ndata", "ledgers.csv")
        assert is_valid is False
