"""Tests for Meitav Trade broker parser."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.brokers.meitav.parser import (
    ACTION_TYPE_MAP,
    AGOROT_TO_ILS,
    BALANCE_COLUMNS,
    SECURITY_TYPE_MAP,
    TRANSACTION_COLUMNS,
    MeitavParser,
)


class TestMeitavParserMetadata:
    """Test parser metadata methods."""

    def test_broker_type(self):
        """Test broker type identifier."""
        assert MeitavParser.broker_type() == "meitav"

    def test_broker_name(self):
        """Test broker display name."""
        assert MeitavParser.broker_name() == "Meitav Trade"

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert MeitavParser.supported_extensions() == [".xlsx"]

    def test_has_api(self):
        """Test API support flag."""
        assert MeitavParser.has_api() is False


class TestColumnMappings:
    """Test Hebrew column mappings."""

    def test_balance_columns_mapping(self):
        """Test balance file column mapping."""
        assert BALANCE_COLUMNS["שם נייר"] == "security_name"
        assert BALANCE_COLUMNS["מספר נייר"] == "security_number"
        assert BALANCE_COLUMNS["כמות נוכחית"] == "quantity"
        assert BALANCE_COLUMNS["שער"] == "price"
        assert BALANCE_COLUMNS["מטבע"] == "currency"

    def test_transaction_columns_mapping(self):
        """Test transaction file column mapping."""
        assert TRANSACTION_COLUMNS["תאריך"] == "date"
        assert TRANSACTION_COLUMNS["סוג פעולה"] == "action_type"
        assert TRANSACTION_COLUMNS["כמות"] == "quantity"
        assert TRANSACTION_COLUMNS["שער ביצוע"] == "price"

    def test_action_type_mapping(self):
        """Test Hebrew action type to normalized mapping."""
        assert ACTION_TYPE_MAP["קניה רצף"] == "Buy"
        assert ACTION_TYPE_MAP["קניה"] == "Buy"
        assert ACTION_TYPE_MAP["מכירה רצף"] == "Sell"
        assert ACTION_TYPE_MAP["מכירה"] == "Sell"
        assert ACTION_TYPE_MAP["דיבידנד"] == "Dividend"
        assert ACTION_TYPE_MAP["העברה מזומן בשח"] == "Deposit"
        assert ACTION_TYPE_MAP["ריבית בניע"] == "Interest"

    def test_security_type_mapping(self):
        """Test Hebrew security type to asset class mapping."""
        assert SECURITY_TYPE_MAP['מניות בש"ח'] == "Stock"
        assert SECURITY_TYPE_MAP["מניות"] == "Stock"
        assert SECURITY_TYPE_MAP["קרנות נאמנות"] == "MutualFund"
        assert SECURITY_TYPE_MAP["קרנות סל"] == "ETF"
        assert SECURITY_TYPE_MAP['אג"ח'] == "Bond"


class TestAgorotConversion:
    """Test Agorot to Shekel conversion."""

    def test_conversion_factor(self):
        """Test conversion factor is correct."""
        assert AGOROT_TO_ILS == Decimal("100")

    def test_price_conversion(self):
        """Test price conversion from Agorot to ILS."""
        price_agorot = Decimal("15000")  # 150 ILS in Agorot
        price_ils = price_agorot / AGOROT_TO_ILS
        assert price_ils == Decimal("150")


class TestCurrencyNormalization:
    """Test Hebrew currency normalization."""

    def test_normalize_hebrew_shekel(self):
        """Test normalizing Hebrew currency names."""
        parser = MeitavParser()
        assert parser._normalize_currency("שקל חדש") == "ILS"
        assert parser._normalize_currency("שקל") == "ILS"
        assert parser._normalize_currency("₪") == "ILS"

    def test_normalize_hebrew_dollar(self):
        """Test normalizing Hebrew dollar."""
        parser = MeitavParser()
        assert parser._normalize_currency("דולר") == "USD"
        assert parser._normalize_currency("$") == "USD"

    def test_normalize_hebrew_euro(self):
        """Test normalizing Hebrew euro."""
        parser = MeitavParser()
        assert parser._normalize_currency("אירו") == "EUR"
        assert parser._normalize_currency("€") == "EUR"

    def test_normalize_empty_string(self):
        """Test normalizing empty string defaults to ILS."""
        parser = MeitavParser()
        assert parser._normalize_currency("") == "ILS"
        assert parser._normalize_currency(None) == "ILS"

    def test_normalize_unknown_currency(self):
        """Test normalizing unknown currency defaults to ILS."""
        parser = MeitavParser()
        assert parser._normalize_currency("unknown") == "ILS"


class TestDateParsing:
    """Test date parsing from various formats."""

    def test_parse_date_object(self):
        """Test parsing date object returns itself."""
        parser = MeitavParser()
        test_date = date(2024, 1, 15)
        assert parser._parse_date(test_date) == test_date

    def test_parse_israeli_date_format(self):
        """Test parsing DD/MM/YYYY format (Israeli standard)."""
        parser = MeitavParser()
        result = parser._parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_iso_date_format(self):
        """Test parsing YYYY-MM-DD format."""
        parser = MeitavParser()
        result = parser._parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_invalid_date(self):
        """Test parsing invalid date returns None."""
        parser = MeitavParser()
        assert parser._parse_date("invalid") is None
        assert parser._parse_date("") is None


class TestPositionParsing:
    """Test position row parsing."""

    def test_parse_position_row(self):
        """Test parsing a valid position row."""
        parser = MeitavParser()
        row = {
            "מספר נייר": "1234567",
            "שם נייר": "Test Security",
            "כמות נוכחית": 100,
            "עלות": 5000.00,
            "סוג נייר": "מניות",
            "מטבע": "שקל חדש",
            "סימבול": "TEST",
        }

        position = parser._parse_position_row(row)

        assert position is not None
        assert position.symbol == "TASE:1234567"
        assert position.quantity == Decimal("100")
        assert position.cost_basis == Decimal("5000.00")
        assert position.currency == "ILS"
        assert position.asset_class == "Stock"

    def test_parse_position_row_missing_security_number(self):
        """Test parsing position row without security number returns None."""
        parser = MeitavParser()
        row = {
            "שם נייר": "Test Security",
            "כמות נוכחית": 100,
        }

        position = parser._parse_position_row(row)
        assert position is None

    def test_parse_position_row_missing_quantity(self):
        """Test parsing position row without quantity returns None."""
        parser = MeitavParser()
        row = {
            "מספר נייר": "1234567",
            "שם נייר": "Test Security",
        }

        position = parser._parse_position_row(row)
        assert position is None

    def test_parse_position_row_cash_position_skipped(self):
        """Test that cash positions (999xxx) are skipped."""
        parser = MeitavParser()
        row = {
            "מספר נייר": "9990001",
            "שם נייר": "Cash ILS",
            "כמות נוכחית": 10000,
        }

        position = parser._parse_position_row(row)
        assert position is None


class TestTransactionParsing:
    """Test transaction row parsing."""

    def test_parse_trade_row(self):
        """Test parsing a buy/sell transaction row."""
        parser = MeitavParser()
        row = {
            "תאריך": "15/01/2024",
            "סוג פעולה": "קניה רצף",
            "מס' נייר / סימבול": "1234567",
            "שם נייר": "Test Security",
            "כמות": 50,
            "שער ביצוע": 15000,  # 150 ILS in Agorot
            "מטבע": "שקל חדש",
            "עמלת פעולה": 25.00,
            "עמלות נלוות": 5.00,
            "תמורה בשקלים": 7530.00,
        }

        result = parser._parse_transaction_row(row)

        assert result is not None
        txn_type, txn = result
        assert txn_type == "trade"
        assert txn.trade_date == date(2024, 1, 15)
        assert txn.symbol == "TASE:1234567"
        assert txn.transaction_type == "Buy"
        assert txn.quantity == Decimal("50")
        assert txn.price_per_unit == Decimal("150")  # Converted from Agorot
        assert txn.fees == Decimal("30.00")

    def test_parse_dividend_row(self):
        """Test parsing a dividend transaction row."""
        parser = MeitavParser()
        row = {
            "תאריך": "15/01/2024",
            "סוג פעולה": "דיבידנד",
            "מס' נייר / סימבול": "1234567",
            "שם נייר": "Test Security",
            "מטבע": "שקל חדש",
            "תמורה בשקלים": 150.00,
        }

        result = parser._parse_transaction_row(row)

        assert result is not None
        txn_type, txn = result
        assert txn_type == "dividend"
        assert txn.transaction_type == "Dividend"
        assert txn.amount == Decimal("150.00")

    def test_parse_deposit_row(self):
        """Test parsing a deposit transaction row."""
        parser = MeitavParser()
        row = {
            "תאריך": "15/01/2024",
            "סוג פעולה": "העברה מזומן בשח",
            "מטבע": "שקל חדש",
            "תמורה בשקלים": 10000.00,
        }

        result = parser._parse_transaction_row(row)

        assert result is not None
        txn_type, txn = result
        assert txn_type == "cash"
        assert txn.transaction_type == "Deposit"
        assert txn.amount == Decimal("10000.00")

    def test_parse_transaction_row_missing_action(self):
        """Test parsing row without action type returns None."""
        parser = MeitavParser()
        row = {
            "תאריך": "15/01/2024",
            "מס' נייר / סימבול": "1234567",
        }

        result = parser._parse_transaction_row(row)
        assert result is None

    def test_parse_transaction_row_missing_date(self):
        """Test parsing row without date returns None."""
        parser = MeitavParser()
        row = {
            "סוג פעולה": "קניה רצף",
            "מס' נייר / סימבול": "1234567",
        }

        result = parser._parse_transaction_row(row)
        assert result is None


class TestFileTypeDetecion:
    """Test file type detection from columns."""

    @patch("polars.read_excel")
    def test_detect_balance_file(self, mock_read_excel):
        """Test detection of balance file type."""
        parser = MeitavParser()

        # Create mock DataFrame with balance columns
        mock_df = MagicMock()
        mock_df.columns = ["מספר נייר", "שם נייר", "כמות נוכחית", "שווי נוכחי"]
        mock_df.iter_rows.return_value = []
        mock_read_excel.return_value = mock_df

        result = parser.parse(b"fake_content")

        # Should detect as balance file and return positions
        assert result is not None
        # No transactions in balance file
        assert len(result.transactions) == 0

    @patch("polars.read_excel")
    def test_detect_transaction_file(self, mock_read_excel):
        """Test detection of transaction file type."""
        parser = MeitavParser()

        # Create mock DataFrame with transaction columns
        mock_df = MagicMock()
        mock_df.columns = ["תאריך", "סוג פעולה", "שם נייר", "כמות"]
        mock_df.iter_rows.return_value = []
        mock_read_excel.return_value = mock_df

        result = parser.parse(b"fake_content")

        # Should detect as transaction file
        assert result is not None


class TestBrokerParserRegistry:
    """Test that MeitavParser is registered correctly."""

    def test_meitav_in_registry(self):
        """Test that meitav parser is registered."""
        from app.services.brokers.broker_parser_registry import BrokerParserRegistry

        assert BrokerParserRegistry.is_supported("meitav")

    def test_get_meitav_parser(self):
        """Test getting meitav parser from registry."""
        from app.services.brokers.broker_parser_registry import BrokerParserRegistry

        parser = BrokerParserRegistry.get_parser("meitav")
        assert parser is not None
        assert parser.broker_type() == "meitav"
