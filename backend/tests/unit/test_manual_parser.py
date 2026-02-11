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
