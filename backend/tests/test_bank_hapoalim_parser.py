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
