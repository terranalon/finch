"""Tests for import service registry."""

from unittest.mock import MagicMock

import pytest

from app.services.import_service_registry import BrokerImportServiceRegistry


class TestBrokerImportServiceRegistry:
    """Test BrokerImportServiceRegistry."""

    def setup_method(self):
        """Reset registry state before each test."""
        BrokerImportServiceRegistry._services = {}
        BrokerImportServiceRegistry._initialized = False

    def teardown_method(self):
        """Reset registry state after each test."""
        BrokerImportServiceRegistry._services = {}
        BrokerImportServiceRegistry._initialized = False

    def test_get_import_service_meitav(self):
        """Test getting import service for meitav broker."""
        mock_db = MagicMock()
        service = BrokerImportServiceRegistry.get_import_service("meitav", mock_db)

        assert service is not None
        assert service.broker_type == "meitav"
        assert service.db == mock_db

    def test_get_import_service_kraken(self):
        """Test getting import service for kraken broker."""
        mock_db = MagicMock()
        service = BrokerImportServiceRegistry.get_import_service("kraken", mock_db)

        assert service is not None
        assert service.broker_type == "kraken"

    def test_get_import_service_bit2c(self):
        """Test getting import service for bit2c broker."""
        mock_db = MagicMock()
        service = BrokerImportServiceRegistry.get_import_service("bit2c", mock_db)

        assert service is not None
        assert service.broker_type == "bit2c"

    def test_get_import_service_binance(self):
        """Test getting import service for binance broker."""
        mock_db = MagicMock()
        service = BrokerImportServiceRegistry.get_import_service("binance", mock_db)

        assert service is not None
        assert service.broker_type == "binance"

    def test_get_import_service_unsupported_raises(self):
        """Test that unsupported broker type raises ValueError."""
        mock_db = MagicMock()
        with pytest.raises(ValueError, match="No import service for broker type"):
            BrokerImportServiceRegistry.get_import_service("unsupported", mock_db)

    def test_is_supported_true(self):
        """Test is_supported returns True for supported brokers."""
        assert BrokerImportServiceRegistry.is_supported("meitav") is True
        assert BrokerImportServiceRegistry.is_supported("kraken") is True
        assert BrokerImportServiceRegistry.is_supported("bit2c") is True
        assert BrokerImportServiceRegistry.is_supported("binance") is True

    def test_is_supported_false(self):
        """Test is_supported returns False for unsupported brokers."""
        assert BrokerImportServiceRegistry.is_supported("unsupported") is False
        assert BrokerImportServiceRegistry.is_supported("ibkr") is False

    def test_get_supported_broker_types(self):
        """Test getting list of supported broker types."""
        broker_types = BrokerImportServiceRegistry.get_supported_broker_types()

        assert "meitav" in broker_types
        assert "kraken" in broker_types
        assert "bit2c" in broker_types
        assert "binance" in broker_types
        assert "ibkr" not in broker_types  # IBKR uses different pattern
