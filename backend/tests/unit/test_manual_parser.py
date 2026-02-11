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


class TestManualParserBuySell:

    def test_buy_aapl(self, parsed_csv: "BrokerImportData"):
        buys = [t for t in parsed_csv.transactions if t.symbol == "AAPL" and t.transaction_type == "Buy"]
        assert len(buys) == 1
        assert buys[0].trade_date == date(2025, 1, 15)
        assert buys[0].quantity == Decimal("10")
        assert buys[0].price_per_unit == Decimal("175.50")
        assert buys[0].amount == Decimal("1755.0")
        assert buys[0].fees == Decimal("4.99")
        assert buys[0].currency == "USD"

    def test_sell_spy(self, parsed_csv: "BrokerImportData"):
        sells = [t for t in parsed_csv.transactions if t.symbol == "SPY" and t.transaction_type == "Sell"]
        assert len(sells) == 1
        assert sells[0].quantity == Decimal("5")
        assert sells[0].price_per_unit == Decimal("465.20")

    def test_buy_crypto(self, parsed_csv: "BrokerImportData"):
        btc = [t for t in parsed_csv.transactions if t.symbol == "BTC"]
        assert len(btc) == 1
        assert btc[0].quantity == Decimal("0.05")
        assert btc[0].price_per_unit == Decimal("62000.00")
        assert btc[0].fees == Decimal("12.50")

    def test_buy_tase(self, parsed_csv: "BrokerImportData"):
        teva = [t for t in parsed_csv.transactions if t.symbol == "TEVA.TA"]
        assert len(teva) == 1
        assert teva[0].quantity == Decimal("100")
        assert teva[0].currency == "ILS"


class TestManualParserCash:

    def test_deposit(self, parsed_csv: "BrokerImportData"):
        deposits = [t for t in parsed_csv.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) == 1
        assert deposits[0].amount == Decimal("10000.00")
        assert deposits[0].currency == "USD"

    def test_withdrawal_negative(self, parsed_csv: "BrokerImportData"):
        withdrawals = [t for t in parsed_csv.cash_transactions if t.transaction_type == "Withdrawal"]
        assert len(withdrawals) == 1
        assert withdrawals[0].amount == Decimal("-2000.00")


class TestManualParserDividends:

    def test_dividend(self, parsed_csv: "BrokerImportData"):
        divs = [d for d in parsed_csv.dividends if d.transaction_type == "Dividend"]
        assert len(divs) == 2
        aapl_div = next(d for d in divs if d.symbol == "AAPL")
        assert aapl_div.amount == Decimal("9.50")

    def test_staking(self, parsed_csv: "BrokerImportData"):
        staking = [d for d in parsed_csv.dividends if d.transaction_type == "Staking"]
        assert len(staking) == 1
        assert staking[0].symbol == "ETH"
        assert staking[0].quantity == Decimal("0.012")

    def test_interest(self, parsed_csv: "BrokerImportData"):
        interest = [d for d in parsed_csv.dividends if d.transaction_type == "Interest"]
        assert len(interest) == 1
        assert interest[0].amount == Decimal("45.00")


class TestManualParserXLSX:

    def test_xlsx_total_records(self, parsed_xlsx: "BrokerImportData"):
        assert parsed_xlsx.total_records == 15

    def test_xlsx_date_range(self, parsed_xlsx: "BrokerImportData"):
        assert parsed_xlsx.start_date == date(2025, 1, 15)
        assert parsed_xlsx.end_date == date(2025, 9, 1)

    def test_xlsx_buy_aapl(self, parsed_xlsx: "BrokerImportData"):
        buys = [t for t in parsed_xlsx.transactions if t.symbol == "AAPL" and t.transaction_type == "Buy"]
        assert len(buys) == 1
        assert buys[0].quantity == Decimal("10")


class TestManualParserValidation:

    def test_validate_valid_csv(self, parser: ManualParser, sample_csv_content: bytes):
        is_valid, error = parser.validate_file(sample_csv_content, "data.csv")
        assert is_valid is True
        assert error is None

    def test_validate_wrong_extension(self, parser: ManualParser, sample_csv_content: bytes):
        is_valid, error = parser.validate_file(sample_csv_content, "data.xml")
        assert is_valid is False
        assert "Unsupported file type" in error

    def test_missing_required_column(self, parser: ManualParser):
        bad_csv = b"date,type,symbol\n2025-01-01,Buy,AAPL\n"
        with pytest.raises(ValueError, match="Missing required columns.*currency"):
            parser.parse(bad_csv)

    def test_invalid_type(self, parser: ManualParser):
        bad_csv = b"date,type,symbol,quantity,price,amount,currency,fees,notes\n2025-01-01,Unknown,AAPL,10,100,,USD,,\n"
        result = parser.parse(bad_csv)
        assert result.total_records == 0

    def test_missing_conditional_field(self, parser: ManualParser):
        """Buy without quantity should be skipped."""
        csv_data = b"date,type,symbol,quantity,price,amount,currency,fees,notes\n2025-01-01,Buy,AAPL,,100,,USD,,\n"
        result = parser.parse(csv_data)
        assert result.total_records == 0
