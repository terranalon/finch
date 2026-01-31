"""Tests for Bank Hapoalim parser."""

import pytest

from app.services.bank_hapoalim_parser import BankHapoalimParser


class TestBankHapoalimParserMetadata:
    """Tests for parser metadata methods."""

    def test_broker_type(self):
        assert BankHapoalimParser.broker_type() == "bank_hapoalim"

    def test_broker_name(self):
        assert BankHapoalimParser.broker_name() == "Bank Hapoalim"

    def test_supported_extensions(self):
        assert BankHapoalimParser.supported_extensions() == [".xlsx"]

    def test_has_api(self):
        assert BankHapoalimParser.has_api() is False
