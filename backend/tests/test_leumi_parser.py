"""Tests for Bank Leumi parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.brokers.base_broker_parser import BrokerImportData
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


class TestLeumiParserParse:
    """Tests for full file parsing."""

    @pytest.fixture
    def parser(self):
        return LeumiParser()

    @pytest.fixture
    def sample_file_content(self):
        fixture_path = Path(__file__).parent / "fixtures" / "leumi_sample.xls"
        return fixture_path.read_bytes()

    @pytest.fixture
    def parsed(self, parser, sample_file_content):
        return parser.parse(sample_file_content)

    def test_returns_broker_import_data(self, parsed):
        assert isinstance(parsed, BrokerImportData)

    def test_has_transactions(self, parsed):
        assert len(parsed.transactions) > 0

    def test_has_dividends(self, parsed):
        assert len(parsed.dividends) > 0

    def test_buy_ils_transaction(self, parsed):
        """ILS buy: price converted from Agorot, symbol prefixed TASE:."""
        buys = [
            t for t in parsed.transactions if t.transaction_type == "Buy" and t.currency == "ILS"
        ]
        assert len(buys) >= 1
        buy = buys[0]
        assert buy.symbol.startswith("TASE:")
        assert buy.quantity > 0
        assert buy.price_per_unit is not None
        # Price should be in ILS (converted from Agorot: 1523 -> 15.23)
        assert buy.price_per_unit == Decimal("15.23")

    def test_buy_usd_transaction(self, parsed):
        """USD buy: price used directly, ticker extracted from name."""
        buys = [
            t for t in parsed.transactions if t.transaction_type == "Buy" and t.currency == "USD"
        ]
        assert len(buys) >= 1
        buy = buys[0]
        assert buy.symbol == "TLT"
        assert buy.price_per_unit == Decimal("87.50")

    def test_sell_transaction(self, parsed):
        sells = [t for t in parsed.transactions if t.transaction_type == "Sell"]
        assert len(sells) >= 1
        sell = sells[0]
        assert sell.quantity is not None
        assert sell.quantity > 0  # Should be abs() of negative quantity

    def test_dividend_uses_payment_date(self, parsed):
        """Dividends have no execution date -- should use payment date."""
        assert len(parsed.dividends) >= 1
        div = parsed.dividends[0]
        assert div.trade_date == date(2025, 10, 1)
        assert div.amount is not None

    def test_dividend_fees_from_tax(self, parsed):
        """Dividend fees should come from tax column (withholding tax)."""
        divs_with_tax = [d for d in parsed.dividends if d.fees > 0]
        assert len(divs_with_tax) >= 1
        assert divs_with_tax[0].fees == Decimal("8.88")

    def test_bonus_transaction(self, parsed):
        """Bonus shares: positive quantity, zero amount."""
        bonuses = [t for t in parsed.transactions if t.transaction_type == "Bonus"]
        assert len(bonuses) >= 1
        bonus = bonuses[0]
        assert bonus.quantity > 0
        assert bonus.amount == Decimal("0")

    def test_fractional_credit_is_sell(self, parsed):
        """Fractional credit (זיכוי שברים) should be mapped to Sell."""
        # The fixture has a fractional credit with -0.5 quantity
        sells = [t for t in parsed.transactions if t.transaction_type == "Sell"]
        fractional = [s for s in sells if s.quantity == Decimal("0.5")]
        assert len(fractional) >= 1

    def test_tax_transaction(self, parsed):
        """Tax events: standalone tax amount."""
        taxes = [t for t in parsed.transactions if t.transaction_type == "Tax"]
        assert len(taxes) >= 1
        tax = taxes[0]
        assert tax.amount == Decimal("12.30")

    def test_skips_cancellation_rows(self, parsed):
        """Cancellation rows should be skipped."""
        all_types = {t.transaction_type for t in [*parsed.transactions, *parsed.dividends]}
        assert "קניה וביטול" not in all_types
        assert "מכירה וביטול" not in all_types

    def test_skips_info_rows(self, parsed):
        """Info rows (מידע-הטבה) should be skipped."""
        all_types = {t.transaction_type for t in [*parsed.transactions, *parsed.dividends]}
        assert "מידע-הטבה" not in all_types

    def test_total_transaction_count(self, parsed):
        """Fixture has 7 valid rows (2 skip) = 6 trades + 1 dividend."""
        assert len(parsed.transactions) == 6
        assert len(parsed.dividends) == 1
