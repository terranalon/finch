"""Tests for Kraken broker parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.kraken_parser import KrakenParser


@pytest.fixture
def sample_csv_content() -> bytes:
    """Load sample Kraken ledgers CSV."""
    fixture_path = Path(__file__).parent / "fixtures" / "kraken_ledgers_sample.csv"
    return fixture_path.read_bytes()


@pytest.fixture
def parser() -> KrakenParser:
    """Create a KrakenParser instance."""
    return KrakenParser()


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
        assert end_date == date(2024, 2, 1)

    def test_extract_date_range_invalid_file(self, parser: KrakenParser):
        """Test error handling for invalid file."""
        with pytest.raises(ValueError, match="(Failed to parse|Empty CSV)"):
            parser.extract_date_range(b"invalid content")


class TestKrakenParserParsing:
    """Test full file parsing."""

    def test_parse_basic_structure(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test basic parsing returns BrokerImportData."""
        result = parser.parse(sample_csv_content)

        assert result.start_date == date(2024, 1, 15)
        assert result.end_date == date(2024, 2, 1)
        assert result.total_records > 0

    def test_parse_deposits(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test parsing deposit transactions."""
        result = parser.parse(sample_csv_content)

        deposits = [t for t in result.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) == 1

        deposit = deposits[0]
        assert deposit.amount == Decimal("1000.0000")
        assert deposit.currency == "USD"

    def test_parse_withdrawals(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test parsing withdrawal transactions."""
        result = parser.parse(sample_csv_content)

        withdrawals = [t for t in result.cash_transactions if t.transaction_type == "Withdrawal"]
        assert len(withdrawals) == 1

        withdrawal = withdrawals[0]
        assert withdrawal.amount == Decimal("-250.0000")
        assert withdrawal.currency == "USD"

    def test_parse_trades(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test parsing trade transactions."""
        result = parser.parse(sample_csv_content)

        # Trades are grouped by refid - we have 2 distinct trade pairs
        # Each trade has two entries (sell currency, buy currency)
        assert len(result.transactions) > 0

    def test_parse_staking_rewards(self, parser: KrakenParser, sample_csv_content: bytes):
        """Test parsing staking rewards."""
        result = parser.parse(sample_csv_content)

        # Staking rewards should be in dividends
        staking = [d for d in result.dividends if d.transaction_type == "Staking"]
        assert len(staking) == 1
        assert staking[0].symbol == "BTC"


class TestKrakenAssetMapping:
    """Test Kraken asset name normalization."""

    def test_normalize_asset_btc(self, parser: KrakenParser):
        """Test BTC normalization."""
        assert parser._normalize_asset("XXBT") == "BTC"
        assert parser._normalize_asset("XBT") == "BTC"

    def test_normalize_asset_eth(self, parser: KrakenParser):
        """Test ETH normalization."""
        assert parser._normalize_asset("XETH") == "ETH"
        assert parser._normalize_asset("ETH") == "ETH"

    def test_normalize_asset_usd(self, parser: KrakenParser):
        """Test USD normalization."""
        assert parser._normalize_asset("ZUSD") == "USD"
        assert parser._normalize_asset("USD") == "USD"

    def test_normalize_asset_eur(self, parser: KrakenParser):
        """Test EUR normalization."""
        assert parser._normalize_asset("ZEUR") == "EUR"

    def test_normalize_asset_staked(self, parser: KrakenParser):
        """Test staked asset normalization."""
        assert parser._normalize_asset("XXBT.S") == "BTC"
        assert parser._normalize_asset("XETH.S") == "ETH"

    def test_normalize_asset_rewards(self, parser: KrakenParser):
        """Test rewards asset normalization."""
        assert parser._normalize_asset("XXBT.F") == "BTC"


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
