"""Tests for base import service."""

from unittest.mock import MagicMock

import pytest

from app.services.brokers.base_import_service import BaseBrokerImportService


class TestBaseBrokerImportService:
    """Test BaseBrokerImportService abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseBrokerImportService cannot be instantiated directly."""
        mock_db = MagicMock()
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseBrokerImportService(mock_db, "test")

    def test_subclass_must_implement_supported_broker_types(self):
        """Test that subclasses must implement supported_broker_types."""

        class IncompleteService(BaseBrokerImportService):
            def import_data(self, account_id, data, source_id=None):
                return {}

        mock_db = MagicMock()
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteService(mock_db, "test")

    def test_subclass_must_implement_import_data(self):
        """Test that subclasses must implement import_data."""

        class IncompleteService(BaseBrokerImportService):
            @classmethod
            def supported_broker_types(cls):
                return ["test"]

        mock_db = MagicMock()
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteService(mock_db, "test")

    def test_complete_subclass_can_be_instantiated(self):
        """Test that a complete subclass can be instantiated."""

        class CompleteService(BaseBrokerImportService):
            @classmethod
            def supported_broker_types(cls):
                return ["test"]

            def import_data(self, account_id, data, source_id=None):
                return {"status": "completed"}

        mock_db = MagicMock()
        service = CompleteService(mock_db, "test")

        assert service.db == mock_db
        assert service.broker_type == "test"
        assert CompleteService.supported_broker_types() == ["test"]
