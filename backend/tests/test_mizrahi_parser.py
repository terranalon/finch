"""Tests for Mizrahi Tefahot broker parser."""

from app.services.brokers.mizrahi.constants import (
    ACTION_TYPE_MAP,
    CURRENCY_CODE_MAP,
)


class TestConstants:
    """Test constant mappings."""

    def test_action_type_map_buy(self):
        assert ACTION_TYPE_MAP["קניה"] == "Buy"
        assert ACTION_TYPE_MAP["קניה רצף"] == "Buy"

    def test_action_type_map_buy_double_space(self):
        """Mizrahi files sometimes have double spaces in action types."""
        assert ACTION_TYPE_MAP["קניה  רצף"] == "Buy"

    def test_action_type_map_sell(self):
        assert ACTION_TYPE_MAP["מכירה"] == "Sell"
        assert ACTION_TYPE_MAP["מכירה רצף"] == "Sell"

    def test_action_type_map_sell_double_space(self):
        assert ACTION_TYPE_MAP["מכירה  רצף"] == "Sell"

    def test_action_type_map_special_types(self):
        assert ACTION_TYPE_MAP["הטבה"] == "Buy"
        assert ACTION_TYPE_MAP["פדיון"] == "Sell"
        assert ACTION_TYPE_MAP["החלפה/גריעה"] == "Sell"

    def test_currency_code_map(self):
        assert CURRENCY_CODE_MAP["000"] == "ILS"
        assert CURRENCY_CODE_MAP["001"] == "USD"


from pathlib import Path

import pytest

from app.services.brokers.mizrahi.parser import MizrahiParser


class TestMizrahiParserMetadata:
    """Test parser metadata methods."""

    def test_broker_type(self):
        assert MizrahiParser.broker_type() == "mizrahi"

    def test_broker_name(self):
        assert MizrahiParser.broker_name() == "Mizrahi Tefahot"

    def test_supported_extensions(self):
        assert MizrahiParser.supported_extensions() == [".xls"]

    def test_has_api(self):
        assert MizrahiParser.has_api() is False


class TestMizrahiHTMLParsing:
    """Test HTML table extraction from UTF-16 LE encoded .xls files."""

    @pytest.fixture
    def parser(self):
        return MizrahiParser()

    @pytest.fixture
    def sample_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "mizrahi_sample.xls"
        return fixture_path.read_bytes()

    def test_decode_utf16le(self, parser, sample_content):
        """File should decode as UTF-16 LE with BOM."""
        header, rows = parser._parse_html_tables(sample_content)
        assert header is not None

    def test_extract_account_number(self, parser, sample_content):
        """Header table should contain account number."""
        header, rows = parser._parse_html_tables(sample_content)
        assert "418-999999" in header

    def test_extract_data_rows(self, parser, sample_content):
        """Data table should have 8 transaction rows (excluding header row)."""
        header, rows = parser._parse_html_tables(sample_content)
        assert len(rows) == 8

    def test_data_row_has_columns(self, parser, sample_content):
        """Each data row should be a dict with Hebrew column names as keys."""
        header, rows = parser._parse_html_tables(sample_content)
        first_row = rows[0]
        assert "סוג פעולה" in first_row
        assert "מספר נייר" in first_row
        assert "כמות" in first_row
