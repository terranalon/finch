"""Tests for Bank Leumi parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

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
