"""Tests for Mizrahi Tefahot broker parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.brokers.mizrahi.constants import (
    ACTION_TYPE_MAP,
    CURRENCY_CODE_MAP,
)
from app.services.brokers.mizrahi.parser import MizrahiParser


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


class TestMizrahiDateRange:
    """Test date range extraction."""

    @pytest.fixture
    def parser(self):
        return MizrahiParser()

    @pytest.fixture
    def sample_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "mizrahi_sample.xls"
        return fixture_path.read_bytes()

    def test_extract_date_range(self, parser, sample_content):
        start_date, end_date = parser.extract_date_range(sample_content)
        assert isinstance(start_date, date)
        assert isinstance(end_date, date)
        assert start_date <= end_date

    def test_date_range_spans_fixture(self, parser, sample_content):
        """Fixture has dates from 06/02/25 to 15/01/26."""
        start_date, end_date = parser.extract_date_range(sample_content)
        assert start_date == date(2025, 2, 6)
        assert end_date == date(2026, 1, 15)

    def test_date_range_raises_on_empty(self, parser):
        """File with no dates should raise ValueError."""
        html = (
            "<html><body>"
            "<table><tr><td>header</td></tr></table>"
            "<table><tr><td>col</td></tr>"
            "<tr><td>no date</td></tr></table>"
            "</body></html>"
        )
        content = b"\xff\xfe" + html.encode("utf-16-le")
        with pytest.raises(ValueError, match="No valid dates found"):
            parser.extract_date_range(content)


class TestMizrahiFullParse:
    """Test full file parsing with fixture data."""

    @pytest.fixture
    def parser(self):
        return MizrahiParser()

    @pytest.fixture
    def sample_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "mizrahi_sample.xls"
        return fixture_path.read_bytes()

    @pytest.fixture
    def parsed(self, parser, sample_content):
        return parser.parse(sample_content)

    def test_returns_broker_import_data(self, parsed):
        from app.services.brokers.base_broker_parser import BrokerImportData

        assert isinstance(parsed, BrokerImportData)

    def test_transaction_count(self, parsed):
        """Fixture has 8 transaction rows."""
        assert len(parsed.transactions) == 8

    def test_ils_buy_continuous(self, parsed):
        """ILS continuous buy: El Al, price in Agorot -> ILS."""
        el_al = [
            t
            for t in parsed.transactions
            if "1087824" in t.symbol and t.transaction_type == "Buy"
        ]
        assert len(el_al) == 1
        txn = el_al[0]
        assert txn.currency == "ILS"
        assert txn.quantity == Decimal("10840")
        assert txn.price_per_unit == Decimal("18.40")  # 1840 agorot / 100
        assert txn.fees == Decimal("159.56")

    def test_ils_sell_continuous(self, parsed):
        """ILS continuous sell: TA-35 tracker."""
        ta35 = [
            t
            for t in parsed.transactions
            if "1143700" in t.symbol and t.transaction_type == "Sell"
        ]
        assert len(ta35) == 1
        txn = ta35[0]
        assert txn.currency == "ILS"
        assert txn.quantity == Decimal("7735")
        assert txn.price_per_unit == Decimal("38.80")  # 3880 agorot / 100

    def test_usd_buy(self, parsed):
        """USD buy: NVIDIA, price in dollars (no conversion)."""
        nvda_buys = [
            t
            for t in parsed.transactions
            if "0047241" in t.symbol and t.transaction_type == "Buy"
        ]
        assert len(nvda_buys) == 1
        txn = nvda_buys[0]
        assert txn.currency == "USD"
        assert txn.quantity == Decimal("300")
        assert txn.price_per_unit == Decimal("183.6")

    def test_usd_sell(self, parsed):
        """USD sell: NVIDIA, quantity should be positive (abs)."""
        nvda_sells = [
            t
            for t in parsed.transactions
            if "0047241" in t.symbol and t.transaction_type == "Sell"
        ]
        assert len(nvda_sells) == 1
        txn = nvda_sells[0]
        assert txn.quantity == Decimal("623")  # abs(-623)

    def test_usd_buy_fees_include_correspondent(self, parsed):
        """USD transactions should combine commission + correspondent fee."""
        nvda_buys = [
            t
            for t in parsed.transactions
            if "0047241" in t.symbol and t.transaction_type == "Buy"
        ]
        txn = nvda_buys[0]
        # commission 44.06 + correspondent 4.00
        assert txn.fees == Decimal("48.06")

    def test_double_space_buy(self, parsed):
        """Action type with double space should parse as Buy."""
        gin = [t for t in parsed.transactions if "1099787" in t.symbol]
        assert len(gin) == 1
        assert gin[0].transaction_type == "Buy"

    def test_benefit_as_buy(self, parsed):
        """Benefit should be parsed as Buy with no price (zero price -> None)."""
        benefit = [t for t in parsed.transactions if "32131757" in t.symbol]
        assert len(benefit) == 1
        assert benefit[0].transaction_type == "Buy"
        assert benefit[0].quantity == Decimal("1511")
        assert benefit[0].price_per_unit is None

    def test_exchange_writeoff_as_sell(self, parsed):
        """Exchange/write-off should be parsed as Sell."""
        exchange = [t for t in parsed.transactions if "32109902" in t.symbol]
        assert len(exchange) == 1
        assert exchange[0].transaction_type == "Sell"
        assert exchange[0].quantity == Decimal("1511")

    def test_redemption_as_sell(self, parsed):
        """Redemption should be parsed as Sell."""
        redemption = [t for t in parsed.transactions if "32014474" in t.symbol]
        assert len(redemption) == 1
        assert redemption[0].transaction_type == "Sell"
        assert redemption[0].quantity == Decimal("50126")

    def test_all_symbols_use_tase_prefix(self, parsed):
        """All symbols should use TASE:{number} format."""
        for txn in parsed.transactions:
            assert txn.symbol.startswith("TASE:"), (
                f"Symbol {txn.symbol} missing TASE: prefix"
            )

    def test_raw_data_preserved(self, parsed):
        """Raw data should contain original Hebrew action type."""
        txn = parsed.transactions[0]
        assert "action_type" in txn.raw_data
        assert "security_number" in txn.raw_data
        assert "security_name" in txn.raw_data


class TestMizrahiRegistry:
    """Test parser and import service registration."""

    def test_parser_in_registry(self):
        from app.services.brokers.broker_parser_registry import BrokerParserRegistry

        assert BrokerParserRegistry.is_supported("mizrahi")

    def test_get_parser_from_registry(self):
        from app.services.brokers.broker_parser_registry import BrokerParserRegistry

        parser = BrokerParserRegistry.get_parser("mizrahi")
        assert parser.broker_type() == "mizrahi"

    def test_import_service_supports_mizrahi(self):
        from app.services.brokers.shared.israeli_import_service import (
            IsraeliSecuritiesImportService,
        )

        assert "mizrahi" in IsraeliSecuritiesImportService.supported_broker_types()
