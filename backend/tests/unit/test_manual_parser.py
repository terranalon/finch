"""Tests for Manual Import parser."""

from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.services.brokers.manual.parser import ManualParser

if TYPE_CHECKING:
    from app.services.brokers.base_broker_parser import BrokerImportData


@pytest.fixture
def parser() -> ManualParser:
    return ManualParser()


@pytest.fixture
def sample_csv_content() -> bytes:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "manual_import_sample.csv"
    return fixture_path.read_bytes()


@pytest.fixture
def sample_xlsx_content(sample_csv_content: bytes) -> bytes:
    """Generate XLSX from the CSV fixture using polars."""
    import polars as pl

    df = pl.read_csv(StringIO(sample_csv_content.decode("utf-8")))
    buffer = BytesIO()
    df.write_excel(buffer)
    return buffer.getvalue()


@pytest.fixture
def parsed_csv(parser: ManualParser, sample_csv_content: bytes) -> "BrokerImportData":
    return parser.parse(sample_csv_content)


@pytest.fixture
def parsed_xlsx(parser: ManualParser, sample_xlsx_content: bytes) -> "BrokerImportData":
    return parser.parse(sample_xlsx_content)


class TestManualParserMetadata:

    def test_broker_type(self, parser: ManualParser):
        assert parser.broker_type() == "manual"

    def test_broker_name(self, parser: ManualParser):
        assert parser.broker_name() == "Manual Import"

    def test_supported_extensions(self, parser: ManualParser):
        assert parser.supported_extensions() == [".csv", ".xlsx"]

    def test_has_no_api(self, parser: ManualParser):
        assert parser.has_api() is False


class TestManualParserDateRange:

    def test_extract_date_range_csv(self, parser: ManualParser, sample_csv_content: bytes):
        start, end = parser.extract_date_range(sample_csv_content)
        assert start == date(2025, 1, 15)
        assert end == date(2025, 9, 1)

    def test_extract_date_range_xlsx(self, parser: ManualParser, sample_xlsx_content: bytes):
        start, end = parser.extract_date_range(sample_xlsx_content)
        assert start == date(2025, 1, 15)
        assert end == date(2025, 9, 1)

    def test_extract_date_range_empty_file(self, parser: ManualParser):
        with pytest.raises(ValueError, match="Empty"):
            parser.extract_date_range(b"")

    def test_extract_date_range_missing_columns(self, parser: ManualParser):
        bad_csv = b"col_a,col_b\n1,2\n"
        with pytest.raises(ValueError, match="Missing required columns"):
            parser.extract_date_range(bad_csv)


class TestManualParserCSVStructure:

    def test_total_records(self, parsed_csv: "BrokerImportData"):
        assert parsed_csv.total_records == 15

    def test_date_range(self, parsed_csv: "BrokerImportData"):
        assert parsed_csv.start_date == date(2025, 1, 15)
        assert parsed_csv.end_date == date(2025, 9, 1)

    def test_transaction_count(self, parsed_csv: "BrokerImportData"):
        """Buy + Sell transactions (not dividends or cash)."""
        assert len(parsed_csv.transactions) == 9

    def test_cash_transaction_count(self, parsed_csv: "BrokerImportData"):
        """Deposit + Withdrawal."""
        assert len(parsed_csv.cash_transactions) == 2

    def test_dividend_count(self, parsed_csv: "BrokerImportData"):
        """Dividend + Interest + Staking."""
        assert len(parsed_csv.dividends) == 4
