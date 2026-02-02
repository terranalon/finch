"""Tests for Bit2C broker parser."""

from pathlib import Path

import pytest

from app.services.brokers.bit2c.parser import Bit2CParser


@pytest.fixture
def parser() -> Bit2CParser:
    """Create a Bit2CParser instance."""
    return Bit2CParser()


@pytest.fixture
def sample_en_2024() -> bytes:
    """Load English 2024 sample file."""
    fixture_path = Path(__file__).parent.parent / "data" / "bit2c_samples" / "bit2c-2024-en.xlsx"
    return fixture_path.read_bytes()


@pytest.fixture
def sample_he_2024() -> bytes:
    """Load Hebrew 2024 sample file."""
    fixture_path = Path(__file__).parent.parent / "data" / "bit2c_samples" / "bit2c-2024-he.xlsx"
    return fixture_path.read_bytes()


@pytest.fixture
def sample_en_2025() -> bytes:
    """Load English 2025 sample file."""
    fixture_path = Path(__file__).parent.parent / "data" / "bit2c_samples" / "bit2c-2025-en.xlsx"
    return fixture_path.read_bytes()


@pytest.fixture
def sample_he_2025() -> bytes:
    """Load Hebrew 2025 sample file."""
    fixture_path = Path(__file__).parent.parent / "data" / "bit2c_samples" / "bit2c-2025-he.xlsx"
    return fixture_path.read_bytes()


class TestBit2CParserMetadata:
    """Test parser metadata methods."""

    def test_broker_type(self, parser: Bit2CParser):
        """Test broker type identifier."""
        assert parser.broker_type() == "bit2c"

    def test_broker_name(self, parser: Bit2CParser):
        """Test human-readable broker name."""
        assert parser.broker_name() == "Bit2C"

    def test_supported_extensions(self, parser: Bit2CParser):
        """Test supported file extensions."""
        assert ".xlsx" in parser.supported_extensions()

    def test_has_api(self, parser: Bit2CParser):
        """Test that Bit2C has API support."""
        assert parser.has_api() is True


class TestBit2CParserDateRange:
    """Test date range extraction."""

    def test_extract_date_range_en_2024(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test extracting date range from English 2024 file."""
        start_date, end_date = parser.extract_date_range(sample_en_2024)

        # 2024 file should have dates in 2024
        assert start_date.year == 2024
        assert end_date.year == 2024
        assert start_date <= end_date

    def test_extract_date_range_he_2024(self, parser: Bit2CParser, sample_he_2024: bytes):
        """Test extracting date range from Hebrew 2024 file."""
        start_date, end_date = parser.extract_date_range(sample_he_2024)

        assert start_date.year == 2024
        assert end_date.year == 2024

    def test_extract_date_range_en_2025(self, parser: Bit2CParser, sample_en_2025: bytes):
        """Test extracting date range from English 2025 file."""
        start_date, end_date = parser.extract_date_range(sample_en_2025)

        assert start_date.year == 2025
        assert end_date.year == 2025


class TestBit2CParserEnglish:
    """Test parsing English files."""

    def test_parse_en_2024_structure(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test basic parsing of English 2024 file."""
        result = parser.parse(sample_en_2024)

        assert result.start_date.year == 2024
        assert result.end_date.year == 2024
        assert result.total_records > 0

    def test_parse_en_2024_trades(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test parsing buy trades from English 2024 file."""
        result = parser.parse(sample_en_2024)

        # Should have buy transactions
        buy_txns = [t for t in result.transactions if t.transaction_type == "Buy"]
        assert len(buy_txns) > 0

        # Check first buy transaction has expected fields
        buy = buy_txns[0]
        assert buy.symbol in ("BTC", "ETH", "LTC", "USDC")
        assert buy.quantity > 0
        assert buy.currency == "ILS"

    def test_parse_en_2025_deposits(self, parser: Bit2CParser, sample_en_2025: bytes):
        """Test parsing deposits from English 2025 file."""
        result = parser.parse(sample_en_2025)

        deposits = [t for t in result.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) > 0

        # Check deposit has expected fields
        deposit = deposits[0]
        assert deposit.amount > 0
        assert deposit.currency in ("ILS", "BTC", "ETH", "LTC", "USDC")

    def test_parse_en_2025_withdrawals(self, parser: Bit2CParser, sample_en_2025: bytes):
        """Test parsing withdrawals from English 2025 file."""
        result = parser.parse(sample_en_2025)

        withdrawals = [t for t in result.cash_transactions if t.transaction_type == "Withdrawal"]
        assert len(withdrawals) > 0

        # Withdrawals should have negative amounts
        for w in withdrawals:
            assert w.amount < 0

    def test_parse_en_2025_fees(self, parser: Bit2CParser, sample_en_2025: bytes):
        """Test parsing fees from English 2025 file."""
        result = parser.parse(sample_en_2025)

        fees = [t for t in result.cash_transactions if t.transaction_type == "Fee"]
        assert len(fees) > 0

        # Fees should have negative amounts
        for f in fees:
            assert f.amount < 0


class TestBit2CParserHebrew:
    """Test parsing Hebrew files."""

    def test_parse_he_2024_structure(self, parser: Bit2CParser, sample_he_2024: bytes):
        """Test basic parsing of Hebrew 2024 file."""
        result = parser.parse(sample_he_2024)

        assert result.start_date.year == 2024
        assert result.end_date.year == 2024
        assert result.total_records > 0

    def test_parse_he_2024_trades(self, parser: Bit2CParser, sample_he_2024: bytes):
        """Test parsing buy trades from Hebrew 2024 file."""
        result = parser.parse(sample_he_2024)

        buy_txns = [t for t in result.transactions if t.transaction_type == "Buy"]
        assert len(buy_txns) > 0

    def test_parse_he_2025_structure(self, parser: Bit2CParser, sample_he_2025: bytes):
        """Test basic parsing of Hebrew 2025 file."""
        result = parser.parse(sample_he_2025)

        assert result.start_date.year == 2025
        assert result.end_date.year == 2025
        assert result.total_records > 0


class TestBit2CParserConsistency:
    """Test that English and Hebrew files produce consistent results."""

    def test_en_he_2024_same_transaction_count(
        self, parser: Bit2CParser, sample_en_2024: bytes, sample_he_2024: bytes
    ):
        """Test that EN and HE 2024 files have same number of transactions."""
        result_en = parser.parse(sample_en_2024)
        result_he = parser.parse(sample_he_2024)

        assert len(result_en.transactions) == len(result_he.transactions)
        assert len(result_en.cash_transactions) == len(result_he.cash_transactions)

    def test_en_he_2025_same_transaction_count(
        self, parser: Bit2CParser, sample_en_2025: bytes, sample_he_2025: bytes
    ):
        """Test that EN and HE 2025 files have same number of transactions."""
        result_en = parser.parse(sample_en_2025)
        result_he = parser.parse(sample_he_2025)

        assert len(result_en.transactions) == len(result_he.transactions)
        assert len(result_en.cash_transactions) == len(result_he.cash_transactions)

    def test_en_he_2024_same_date_range(
        self, parser: Bit2CParser, sample_en_2024: bytes, sample_he_2024: bytes
    ):
        """Test that EN and HE 2024 files have same date range."""
        start_en, end_en = parser.extract_date_range(sample_en_2024)
        start_he, end_he = parser.extract_date_range(sample_he_2024)

        assert start_en == start_he
        assert end_en == end_he


class TestBit2CParserValidation:
    """Test file validation."""

    def test_validate_valid_file(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test validation of valid XLSX file."""
        is_valid, error = parser.validate_file(sample_en_2024, "report.xlsx")
        assert is_valid is True
        assert error is None

    def test_validate_wrong_extension(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test validation rejects wrong extension."""
        is_valid, error = parser.validate_file(sample_en_2024, "report.csv")
        assert is_valid is False
        assert "Unsupported file type" in error

    def test_validate_invalid_content(self, parser: Bit2CParser):
        """Test validation rejects invalid content."""
        is_valid, error = parser.validate_file(b"not valid xlsx content", "report.xlsx")
        assert is_valid is False


class TestBit2CParserDualEntry:
    """Test dual-entry accounting (Trade Settlements)."""

    def test_trade_creates_settlement(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test that each trade creates a Trade Settlement."""
        result = parser.parse(sample_en_2024)

        # Count trades
        trade_count = len(result.transactions)
        assert trade_count > 0

        # Count Trade Settlements
        settlements = [
            t for t in result.cash_transactions if t.transaction_type == "Trade Settlement"
        ]

        # Each trade should have a corresponding Trade Settlement
        assert len(settlements) == trade_count

    def test_buy_settlement_is_negative(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test that Buy trade settlements are negative (cash leaves account)."""
        result = parser.parse(sample_en_2024)

        # Find Buy trades
        buy_trades = [t for t in result.transactions if t.transaction_type == "Buy"]
        assert len(buy_trades) > 0

        # Find corresponding settlements by matching notes
        for buy in buy_trades:
            trade_id = buy.raw_data.get("id", "")
            matching_settlements = [
                s
                for s in result.cash_transactions
                if s.transaction_type == "Trade Settlement"
                and f"Settlement for {buy.symbol} Buy - {trade_id}" in s.notes
            ]
            assert len(matching_settlements) == 1
            settlement = matching_settlements[0]

            # Buy settlement should be negative (cash leaves account)
            assert settlement.amount < 0
            assert settlement.currency == "ILS"

    def test_sell_settlement_is_positive(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test that Sell trade settlements are positive (cash received)."""
        result = parser.parse(sample_en_2024)

        # Find Sell trades
        sell_trades = [t for t in result.transactions if t.transaction_type == "Sell"]

        # Skip if no sell trades in sample file
        if len(sell_trades) == 0:
            return

        # Find corresponding settlements by matching notes
        for sell in sell_trades:
            trade_id = sell.raw_data.get("id", "")
            matching_settlements = [
                s
                for s in result.cash_transactions
                if s.transaction_type == "Trade Settlement"
                and f"Settlement for {sell.symbol} Sell - {trade_id}" in s.notes
            ]
            assert len(matching_settlements) == 1
            settlement = matching_settlements[0]

            # Sell settlement should be positive (cash received)
            assert settlement.amount > 0
            assert settlement.currency == "ILS"

    def test_settlement_includes_fees(self, parser: Bit2CParser, sample_en_2024: bytes):
        """Test that settlement amounts include fees."""
        result = parser.parse(sample_en_2024)

        # Find trades with fees
        trades_with_fees = [t for t in result.transactions if t.fees and t.fees > 0]

        for trade in trades_with_fees:
            trade_id = trade.raw_data.get("id", "")
            txn_type = trade.transaction_type
            symbol = trade.symbol

            # Find matching settlement
            matching_settlements = [
                s
                for s in result.cash_transactions
                if s.transaction_type == "Trade Settlement"
                and f"Settlement for {symbol} {txn_type} - {trade_id}" in s.notes
            ]

            if len(matching_settlements) == 1:
                settlement = matching_settlements[0]
                # Calculate expected settlement
                fiat_amount = trade.amount or 0

                if txn_type == "Buy":
                    # Buy: -(fiat_amount + fee)
                    expected = -(fiat_amount + trade.fees)
                else:
                    # Sell: fiat_amount - fee
                    expected = fiat_amount - trade.fees

                assert settlement.amount == expected

    def test_en_he_same_settlement_count(
        self, parser: Bit2CParser, sample_en_2024: bytes, sample_he_2024: bytes
    ):
        """Test that EN and HE files produce same number of Trade Settlements."""
        result_en = parser.parse(sample_en_2024)
        result_he = parser.parse(sample_he_2024)

        settlements_en = [
            t for t in result_en.cash_transactions if t.transaction_type == "Trade Settlement"
        ]
        settlements_he = [
            t for t in result_he.cash_transactions if t.transaction_type == "Trade Settlement"
        ]

        assert len(settlements_en) == len(settlements_he)
