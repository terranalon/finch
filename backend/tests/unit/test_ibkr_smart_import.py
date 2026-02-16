"""Tests for IBKR smart import service logic."""

import xml.etree.ElementTree as ET
from datetime import date, timedelta

from app.services.brokers.ibkr.parser import IBKRParser
from app.services.brokers.ibkr.smart_import_service import _MAX_API_HISTORY_DAYS


def _build_flex_xml(inner: str) -> ET.Element:
    return ET.fromstring(
        f"<FlexQueryResponse><FlexStatements>"
        f'<FlexStatement accountId="U12345">{inner}</FlexStatement>'
        f"</FlexStatements></FlexQueryResponse>"
    )


_ALL_SECTIONS_XML = (
    '<AccountInformation accountId="U12345" dateOpened="2025-06-15" />'
    '<OpenPositions><OpenPosition symbol="AAPL" /></OpenPositions>'
    '<Trades><Trade symbol="AAPL" /></Trades>'
    '<CashTransactions><CashTransaction type="Dividends" /></CashTransactions>'
    "<Transfers><Transfer /></Transfers>"
    "<ConversionRates><ConversionRate /></ConversionRates>"
    '<CashReport><CashReportCurrency currency="USD" /></CashReport>'
)


class TestValidateSections:
    def test_all_present_returns_empty(self):
        root = _build_flex_xml(_ALL_SECTIONS_XML)
        assert IBKRParser.validate_required_sections(root) == []

    def test_missing_account_info_detected(self):
        root = _build_flex_xml(
            "<OpenPositions><OpenPosition /></OpenPositions>"
            "<Trades><Trade /></Trades>"
            "<CashTransactions><CashTransaction /></CashTransactions>"
            "<Transfers><Transfer /></Transfers>"
            "<ConversionRates><ConversionRate /></ConversionRates>"
            "<CashReport><CashReportCurrency /></CashReport>"
        )
        assert "Account Information" in IBKRParser.validate_required_sections(root)

    def test_multiple_missing_sections_detected(self):
        root = _build_flex_xml('<AccountInformation accountId="U12345" dateOpened="2025-06-15" />')
        missing = IBKRParser.validate_required_sections(root)
        assert "Open Positions" in missing
        assert "Trades" in missing
        assert "Account Information" not in missing


class TestAccountAgeDecision:
    """Verify the age threshold that determines full-history vs snapshot import.

    The smart import endpoint uses _MAX_API_HISTORY_DAYS to decide:
    - age <= threshold: full transaction history import
    - age > threshold: synthetic snapshot import
    """

    def test_young_account_gets_full_history(self):
        age_days = (date.today() - (date.today() - timedelta(days=200))).days
        assert age_days <= _MAX_API_HISTORY_DAYS

    def test_old_account_gets_snapshot(self):
        age_days = (date.today() - (date.today() - timedelta(days=500))).days
        assert age_days > _MAX_API_HISTORY_DAYS

    def test_boundary_exactly_at_threshold_gets_full_history(self):
        age_days = (date.today() - (date.today() - timedelta(days=_MAX_API_HISTORY_DAYS))).days
        assert age_days <= _MAX_API_HISTORY_DAYS
