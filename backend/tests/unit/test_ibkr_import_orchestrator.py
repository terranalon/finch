"""Tests for IBKR import orchestrator logic.

Section validation tests live in test_ibkr_parser_types.py alongside the
parser. This file focuses on orchestration-specific logic (age decision).
"""

from datetime import date, timedelta

from app.services.brokers.ibkr.import_orchestrator import _account_is_young


class TestAccountAgeDecision:
    """Verify _account_is_young determines full-history vs snapshot import.

    - young (within threshold): full transaction history import
    - old (beyond threshold): synthetic snapshot import
    """

    def test_young_account(self):
        opened = date.today() - timedelta(days=200)
        assert _account_is_young(opened) is True

    def test_old_account(self):
        opened = date.today() - timedelta(days=500)
        assert _account_is_young(opened) is False

    def test_boundary_exactly_at_threshold(self):
        opened = date.today() - timedelta(days=365)
        assert _account_is_young(opened) is True
