"""Tests for Bank Leumi parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.brokers.leumi.parser import LeumiParser


class TestLeumiParserMetadata:
    """Tests for parser metadata methods."""

    def test_broker_type(self):
        assert LeumiParser.broker_type() == "leumi"

    def test_broker_name(self):
        assert LeumiParser.broker_name() == "Bank Leumi"

    def test_supported_extensions(self):
        assert LeumiParser.supported_extensions() == [".xls"]

    def test_has_api(self):
        assert LeumiParser.has_api() is False


class TestLeumiParserDateRange:
    """Tests for date range extraction."""

    @pytest.fixture
    def parser(self):
        return LeumiParser()

    @pytest.fixture
    def sample_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "leumi_sample.xls"
        return fixture_path.read_bytes()

    def test_extract_date_range(self, parser, sample_file_content):
        start_date, end_date = parser.extract_date_range(sample_file_content)
        assert isinstance(start_date, date)
        assert isinstance(end_date, date)
        assert start_date <= end_date

    def test_extract_date_range_spans_fixture_dates(self, parser, sample_file_content):
        """Fixture has dates from 10/07/2025 to 25/12/2025."""
        start_date, end_date = parser.extract_date_range(sample_file_content)
        assert start_date == date(2025, 7, 10)
        assert end_date == date(2025, 12, 25)

    def test_extract_date_range_includes_payment_dates(self, parser, sample_file_content):
        """Dividends have no execution date -- payment date should be included in range."""
        start_date, end_date = parser.extract_date_range(sample_file_content)
        # Dividend payment date is 01/10/2025, tax payment date is 15/12/2025
        assert start_date <= date(2025, 10, 1)
        assert end_date >= date(2025, 12, 15)
