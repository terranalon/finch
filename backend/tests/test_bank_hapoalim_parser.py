"""Tests for Bank Hapoalim parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.bank_hapoalim_parser import BankHapoalimParser


class TestBankHapoalimParserMetadata:
    """Tests for parser metadata methods."""

    def test_broker_type(self):
        assert BankHapoalimParser.broker_type() == "bank_hapoalim"

    def test_broker_name(self):
        assert BankHapoalimParser.broker_name() == "Bank Hapoalim"

    def test_supported_extensions(self):
        assert BankHapoalimParser.supported_extensions() == [".xlsx"]

    def test_has_api(self):
        assert BankHapoalimParser.has_api() is False


class TestBankHapoalimParserDateRange:
    """Tests for date range extraction."""

    @pytest.fixture
    def parser(self):
        return BankHapoalimParser()

    @pytest.fixture
    def english_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_en.xlsx"
        return fixture_path.read_bytes()

    @pytest.fixture
    def hebrew_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_he.xlsx"
        return fixture_path.read_bytes()

    def test_extract_date_range_english(self, parser, english_file_content):
        start_date, end_date = parser.extract_date_range(english_file_content)
        # Sample file covers 29/01/2023 to 29/01/2026
        assert start_date == date(2023, 1, 29)
        assert end_date == date(2026, 1, 29)

    def test_extract_date_range_hebrew(self, parser, hebrew_file_content):
        start_date, end_date = parser.extract_date_range(hebrew_file_content)
        assert start_date == date(2023, 1, 29)
        assert end_date == date(2026, 1, 29)


class TestBankHapoalimParserLanguageDetection:
    """Tests for language detection."""

    @pytest.fixture
    def parser(self):
        return BankHapoalimParser()

    @pytest.fixture
    def english_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_en.xlsx"
        return fixture_path.read_bytes()

    @pytest.fixture
    def hebrew_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_he.xlsx"
        return fixture_path.read_bytes()

    def test_detect_english_headers(self, parser, english_file_content):
        is_english = parser._detect_language(english_file_content)
        assert is_english is True

    def test_detect_hebrew_headers(self, parser, hebrew_file_content):
        is_english = parser._detect_language(hebrew_file_content)
        assert is_english is False


class TestBankHapoalimParserParsing:
    """Tests for full parsing."""

    @pytest.fixture
    def parser(self):
        return BankHapoalimParser()

    @pytest.fixture
    def english_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_en.xlsx"
        return fixture_path.read_bytes()

    @pytest.fixture
    def hebrew_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "bank_hapoalim_sample_he.xlsx"
        return fixture_path.read_bytes()

    def test_parse_returns_broker_import_data(self, parser, english_file_content):
        result = parser.parse(english_file_content)
        assert result is not None
        assert hasattr(result, "transactions")
        assert hasattr(result, "dividends")

    def test_parse_buy_transaction(self, parser, english_file_content):
        result = parser.parse(english_file_content)

        # Find buy transactions
        buy_txns = [t for t in result.transactions if t.transaction_type == "Buy"]
        assert len(buy_txns) > 0

        # First buy is מגדל כספית on 06/01/2026
        first_buy = buy_txns[0]
        assert first_buy.trade_date == date(2026, 1, 6)
        assert first_buy.quantity == Decimal("1469")
        assert first_buy.price_per_unit == Decimal("102.16")
        assert first_buy.currency == "ILS"
        # Security number should be in raw_data
        assert first_buy.raw_data.get("security_number") == "5140785"
        assert first_buy.raw_data.get("isin") == "IL0051407851"

    def test_parse_sell_transaction(self, parser, english_file_content):
        result = parser.parse(english_file_content)
        sell_txns = [t for t in result.transactions if t.transaction_type == "Sell"]
        assert len(sell_txns) > 0

        # Find the IBI USD sell on 25/11/2025
        ibi_sell = next(
            (t for t in sell_txns if t.raw_data.get("security_number") == "5137906"),
            None,
        )
        assert ibi_sell is not None
        assert ibi_sell.trade_date == date(2025, 11, 25)
        assert ibi_sell.quantity == Decimal("931")
        assert ibi_sell.currency == "USD"

    def test_parse_dividend(self, parser, english_file_content):
        result = parser.parse(english_file_content)
        assert len(result.dividends) > 0

        # Find Bank Hapoalim dividend on 08/12/2025
        hapoalim_div = next(
            (d for d in result.dividends if d.raw_data.get("security_number") == "662577"),
            None,
        )
        assert hapoalim_div is not None
        assert hapoalim_div.transaction_type == "Dividend"
        assert hapoalim_div.trade_date == date(2025, 12, 8)
        assert hapoalim_div.amount == Decimal("1.68")  # Gross dividend
        assert hapoalim_div.fees == Decimal("0.42")  # Israel tax

    def test_parse_deposit_transfer_in(self, parser, english_file_content):
        result = parser.parse(english_file_content)
        deposits = [t for t in result.transactions if t.transaction_type == "Deposit"]
        assert len(deposits) > 0

        # First deposit should have quantity and price
        deposit = deposits[0]
        assert deposit.quantity is not None
        assert deposit.quantity > 0
        assert deposit.price_per_unit is not None

    def test_parse_hebrew_file(self, parser, hebrew_file_content):
        """Verify Hebrew file parses correctly with same structure."""
        result = parser.parse(hebrew_file_content)
        assert result is not None
        assert len(result.transactions) > 0
        # Should have similar counts to English file
        buy_txns = [t for t in result.transactions if t.transaction_type == "Buy"]
        assert len(buy_txns) > 0
