"""Tests that IBKRParser methods return typed dataclasses, not raw dicts."""

import xml.etree.ElementTree as ET
from datetime import date

import pytest

from app.services.brokers.ibkr.models import (
    IBKRAccountInfo,
    IBKRCashBalance,
    IBKRDividend,
    IBKRForexTransaction,
    IBKROtherCashTransaction,
    IBKRPosition,
    IBKRStatementOfFundsBalance,
    IBKRSymbolInfo,
    IBKRTransaction,
    IBKRTransfer,
)
from app.services.brokers.ibkr.parser import IBKRParser


def _build_xml(inner: str) -> ET.Element:
    """Wrap inner XML in the FlexQueryResponse / FlexStatement skeleton."""
    return ET.fromstring(
        f"<FlexQueryResponse><FlexStatements>"
        f'<FlexStatement accountId="U12345">{inner}</FlexStatement>'
        f"</FlexStatements></FlexQueryResponse>"
    )


class TestNormalizeSymbolReturnsDataclass:
    def test_us_stock(self):
        result = IBKRParser.normalize_symbol("AAPL", "STK", "NASDAQ")
        assert isinstance(result, IBKRSymbolInfo)
        assert result.yf_symbol == "AAPL"
        assert result.needs_validation is False

    def test_international_stock(self):
        result = IBKRParser.normalize_symbol("RR", "STK", "LSE")
        assert isinstance(result, IBKRSymbolInfo)
        assert result.yf_symbol == "RR.L"
        assert result.needs_validation is True

    def test_unknown_exchange(self):
        result = IBKRParser.normalize_symbol("XYZ", "BOND", "")
        assert isinstance(result, IBKRSymbolInfo)
        assert result.needs_validation is True


class TestExtractPositionsReturnsDataclass:
    def test_single_position(self):
        root = _build_xml(
            '<OpenPositions><OpenPosition symbol="AAPL" description="Apple" '
            'assetCategory="STK" listingExchange="NASDAQ" position="100" '
            'costBasisMoney="15000" currency="USD" accountId="U12345" '
            'cusip="037833100" isin="US0378331005" conid="265598" figi="" />'
            "</OpenPositions>"
        )
        positions = IBKRParser.extract_positions(root)
        assert len(positions) == 1
        assert isinstance(positions[0], IBKRPosition)
        assert positions[0].symbol == "AAPL"
        assert positions[0].cusip == "037833100"
        assert positions[0].figi is None


class TestExtractTransactionsReturnsDataclass:
    def test_single_trade(self):
        root = _build_xml(
            '<Trades><Trade symbol="AAPL" description="Apple" '
            'assetCategory="STK" listingExchange="NASDAQ" tradeDate="20240201" '
            'buySell="BUY" quantity="100" tradePrice="150" ibCommission="1" '
            'netCash="-15001" currency="USD" accountId="U12345" '
            'cusip="" isin="" conid="" figi="" tradeID="123" />'
            "</Trades>"
        )
        txns = IBKRParser.extract_transactions(root)
        assert len(txns) == 1
        assert isinstance(txns[0], IBKRTransaction)
        assert txns[0].transaction_type == "Buy"


class TestExtractDividendsReturnsDataclass:
    def test_single_dividend(self):
        root = _build_xml(
            '<CashTransactions><CashTransaction type="Dividends" symbol="AAPL" '
            'assetCategory="STK" listingExchange="NASDAQ" dateTime="20240315" '
            'amount="25.00" currency="USD" accountId="U12345" description="Apple div" />'
            "</CashTransactions>"
        )
        divs = IBKRParser.extract_dividends(root)
        assert len(divs) == 1
        assert isinstance(divs[0], IBKRDividend)


class TestExtractTransfersReturnsDataclass:
    def test_deposit(self):
        root = _build_xml(
            '<CashTransactions><CashTransaction type="Deposits &amp; Withdrawals" '
            'dateTime="20240101" amount="5000" currency="USD" '
            'description="Wire" accountId="U12345" /></CashTransactions>'
        )
        transfers = IBKRParser.extract_transfers(root)
        assert len(transfers) == 1
        assert isinstance(transfers[0], IBKRTransfer)
        assert transfers[0].type == "Deposit"


class TestExtractOtherCashReturnsDataclass:
    def test_interest(self):
        root = _build_xml(
            '<CashTransactions><CashTransaction type="Broker Interest Received" '
            'dateTime="20240101" amount="5.00" currency="USD" '
            'description="Interest" accountId="U12345" symbol="" />'
            "</CashTransactions>"
        )
        txns = IBKRParser.extract_other_cash_transactions(root)
        assert len(txns) == 1
        assert isinstance(txns[0], IBKROtherCashTransaction)
        assert txns[0].type == "Interest"


class TestExtractCashBalancesReturnsDataclass:
    def test_single_balance(self):
        root = _build_xml(
            '<CashReport><CashReport currency="USD" endingCash="10000" /></CashReport>'
        )
        balances = IBKRParser.extract_cash_balances(root)
        assert len(balances) == 1
        assert isinstance(balances[0], IBKRCashBalance)
        # Enrichment: parser now provides symbol, description, asset_class
        assert balances[0].symbol == "USD"
        assert balances[0].description == "US Dollar"
        assert balances[0].asset_class == "Cash"


class TestExtractForexReturnsDataclass:
    def test_forex_conversion(self):
        root = _build_xml(
            '<FxTransactions><FxTransaction dateTime="20240101" '
            'quantity="-1000" proceeds="270" cost="0" realizedPL="0" '
            'fxCurrency="ILS" functionalCurrency="USD" '
            'activityDescription="CASH: -1000 ILS.USD" accountId="U12345" />'
            "</FxTransactions>"
        )
        forex = IBKRParser.extract_forex_transactions(root)
        assert len(forex) == 1
        assert isinstance(forex[0], IBKRForexTransaction)


class TestExtractStmtFundsBalancesReturnsDataclass:
    def test_single_balance(self):
        root = _build_xml(
            "<StmtFunds>"
            '<StatementOfFundsLine date="20240520" currency="USD" '
            'balance="1000.50" activityDescription="Deposit" />'
            "</StmtFunds>"
        )
        balances = IBKRParser.extract_statement_of_funds_balances(root)
        assert len(balances) == 1
        assert isinstance(balances[0], IBKRStatementOfFundsBalance)


class TestIBKRAccountInfoDataclass:
    def test_create_account_info(self):
        info = IBKRAccountInfo(
            account_id="U12345",
            date_opened=date(2025, 6, 15),
        )
        assert info.account_id == "U12345"
        assert info.date_opened == date(2025, 6, 15)

    def test_frozen(self):
        info = IBKRAccountInfo(account_id="U12345", date_opened=date(2025, 6, 15))
        with pytest.raises(AttributeError):
            info.account_id = "U99999"  # ty: ignore[invalid-assignment] -- verifying frozen behavior at runtime


class TestExtractAccountInfo:
    def test_extracts_date_opened(self):
        root = _build_xml('<AccountInformation accountId="U12345" dateOpened="2025-06-15" />')
        info = IBKRParser.extract_account_info(root)
        assert info is not None
        assert info.account_id == "U12345"
        assert info.date_opened == date(2025, 6, 15)

    def test_returns_none_when_section_missing(self):
        root = _build_xml("")
        info = IBKRParser.extract_account_info(root)
        assert info is None

    def test_returns_none_when_date_opened_empty(self):
        root = _build_xml('<AccountInformation accountId="U12345" dateOpened="" />')
        info = IBKRParser.extract_account_info(root)
        assert info is None

    def test_returns_none_when_date_opened_missing(self):
        root = _build_xml('<AccountInformation accountId="U12345" />')
        info = IBKRParser.extract_account_info(root)
        assert info is None

    def test_handles_yyyymmdd_format(self):
        """IBKR sometimes uses YYYYMMDD without dashes."""
        root = _build_xml('<AccountInformation accountId="U12345" dateOpened="20250615" />')
        info = IBKRParser.extract_account_info(root)
        assert info is not None
        assert info.date_opened == date(2025, 6, 15)


class TestValidateRequiredSections:
    def _build_complete_xml(self) -> ET.Element:
        """Build XML with all required sections present."""
        return _build_xml(
            '<AccountInformation accountId="U12345" dateOpened="2025-06-15" />'
            '<OpenPositions><OpenPosition symbol="AAPL" /></OpenPositions>'
            '<Trades><Trade symbol="AAPL" /></Trades>'
            '<CashTransactions><CashTransaction type="Dividends" /></CashTransactions>'
            '<FxPositions><FxPosition currency="USD" /></FxPositions>'
            "<FxTransactions><FxTransaction /></FxTransactions>"
        )

    def test_all_sections_present(self):
        root = self._build_complete_xml()
        missing = IBKRParser.validate_required_sections(root)
        assert missing == []

    def test_missing_account_info(self):
        root = _build_xml(
            "<OpenPositions><OpenPosition /></OpenPositions>"
            "<Trades><Trade /></Trades>"
            "<CashTransactions><CashTransaction /></CashTransactions>"
            "<FxPositions><FxPosition /></FxPositions>"
            "<FxTransactions><FxTransaction /></FxTransactions>"
        )
        missing = IBKRParser.validate_required_sections(root)
        assert "Account Information" in missing

    def test_missing_multiple_sections(self):
        root = _build_xml("<Trades><Trade /></Trades>")
        missing = IBKRParser.validate_required_sections(root)
        assert "Account Information" in missing
        assert "Open Positions" in missing
        assert "Forex Balances" in missing

    def test_empty_statement(self):
        root = _build_xml("")
        missing = IBKRParser.validate_required_sections(root)
        assert len(missing) == 6

    def test_empty_containers_are_present(self):
        """Sections configured but with no data should NOT be flagged as missing."""
        root = _build_xml(
            '<AccountInformation accountId="U12345" dateOpened="2025-06-15" />'
            "<OpenPositions />"
            "<Trades />"
            "<CashTransactions />"
            "<FxPositions />"
            "<FxTransactions />"
        )
        missing = IBKRParser.validate_required_sections(root)
        assert missing == []
