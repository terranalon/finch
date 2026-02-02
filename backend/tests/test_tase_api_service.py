"""Tests for TASE API service."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.brokers.shared.tase_api_service import TASEApiService, TASESecurityInfo


class TestTASESecurityInfo:
    """Test TASESecurityInfo dataclass."""

    def test_create_security_info(self):
        """Test creating security info object."""
        info = TASESecurityInfo(
            security_id=1234567,
            symbol="TEVA",
            yahoo_symbol="TEVA.TA",
            isin="IL0006290147",
            security_name="טבע",
            security_name_en="Teva Pharmaceutical",
            security_type_code="1",
            company_name="Teva Pharmaceutical Industries",
            company_sector="Health Care",
        )

        assert info.security_id == 1234567
        assert info.symbol == "TEVA"
        assert info.yahoo_symbol == "TEVA.TA"
        assert info.isin == "IL0006290147"


class TestTASEApiServiceInit:
    """Test TASEApiService initialization."""

    @patch("app.services.brokers.shared.tase_api_service.settings")
    def test_init_with_settings(self, mock_settings):
        """Test initialization with settings."""
        mock_settings.tase_api_key = "test_key"
        mock_settings.tase_api_url = "https://test.api.com/v1/"

        service = TASEApiService()

        assert service.api_key == "test_key"
        assert service.base_url == "https://test.api.com/v1"  # Trailing slash removed

    def test_init_with_explicit_params(self):
        """Test initialization with explicit parameters."""
        service = TASEApiService(
            api_key="explicit_key",
            base_url="https://explicit.api.com/v1",
        )

        assert service.api_key == "explicit_key"
        assert service.base_url == "https://explicit.api.com/v1"


class TestTASEApiServiceLookup:
    """Test TASE API service local lookup methods."""

    def test_get_security_by_number_found(self):
        """Test looking up security by number when found."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        mock_db = MagicMock()

        # Mock the query result
        mock_security = MagicMock()
        mock_security.security_id = 1234567
        mock_security.symbol = "TEVA"
        mock_security.yahoo_symbol = "TEVA.TA"
        mock_security.isin = "IL0006290147"
        mock_security.security_name = "טבע"
        mock_security.security_name_en = "Teva"
        mock_security.security_type_code = "1"
        mock_security.company_name = "Teva"
        mock_security.company_sector = "Health Care"

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_security

        result = service.get_security_by_number(mock_db, "1234567")

        assert result is not None
        assert result.security_id == 1234567
        assert result.yahoo_symbol == "TEVA.TA"

    def test_get_security_by_number_not_found(self):
        """Test looking up security by number when not found."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        mock_db = MagicMock()

        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = service.get_security_by_number(mock_db, "9999999")

        assert result is None

    def test_get_yahoo_symbol_found(self):
        """Test getting Yahoo symbol when security is found."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        mock_db = MagicMock()

        # Mock the query result
        mock_security = MagicMock()
        mock_security.security_id = 1234567
        mock_security.symbol = "TEVA"
        mock_security.yahoo_symbol = "TEVA.TA"
        mock_security.isin = None
        mock_security.security_name = None
        mock_security.security_name_en = None
        mock_security.security_type_code = None
        mock_security.company_name = None
        mock_security.company_sector = None

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_security

        result = service.get_yahoo_symbol(mock_db, "1234567")

        assert result == "TEVA.TA"

    def test_get_yahoo_symbol_not_found(self):
        """Test getting Yahoo symbol when security is not found."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        mock_db = MagicMock()

        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = service.get_yahoo_symbol(mock_db, "9999999")

        assert result is None


class TestTASEApiServiceSync:
    """Test TASE API service sync methods."""

    @patch("app.services.brokers.shared.tase_api_service.requests.get")
    def test_fetch_securities_list(self, mock_get):
        """Test fetching securities list from API."""
        service = TASEApiService(api_key="test_key", base_url="https://test.com")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tradeSecuritiesList": {
                "result": [
                    {
                        "securityId": 1234567,
                        "symbol": "TEVA",
                        "isin": "IL0006290147",
                        "securityName": "טבע",
                    },
                    {
                        "securityId": 2345678,
                        "symbol": "LEUMI",
                        "isin": "IL0006046119",
                        "securityName": "לאומי",
                    },
                ],
                "total": 2,
            }
        }
        mock_get.return_value = mock_response

        result = service._fetch_securities_list(date(2024, 1, 15))

        assert len(result) == 2
        assert result[0]["securityId"] == 1234567
        assert result[0]["symbol"] == "TEVA"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "2024/1/15" in call_args[0][0]
        assert call_args[1]["headers"]["Ocp-Apim-Subscription-Key"] == "test_key"

    def test_sync_without_api_key_raises(self):
        """Test sync raises error without API key."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        # Explicitly set api_key to None after init to bypass settings fallback
        service.api_key = None
        mock_db = MagicMock()

        with pytest.raises(ValueError, match="API key not configured"):
            service.sync_securities_list(mock_db)

    @patch("app.services.brokers.shared.tase_api_service.requests.get")
    def test_sync_securities_list(self, mock_get):
        """Test syncing securities list to database."""
        service = TASEApiService(api_key="test_key", base_url="https://test.com")
        mock_db = MagicMock()

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tradeSecuritiesList": {
                "result": [
                    {
                        "securityId": 1234567,
                        "symbol": "TEVA",
                        "isin": "IL0006290147",
                        "securityName": "טבע",
                        "securityNameEn": "Teva",
                        "securityFullTypeCode": "1",
                        "companyName": "Teva",
                        "companySector": "Health",
                        "companySubSector": "Pharma",
                    },
                ],
                "total": 1,
            }
        }
        mock_get.return_value = mock_response

        # Mock database execute to return rowcount
        mock_db.execute.return_value.rowcount = 1

        stats = service.sync_securities_list(mock_db)

        assert stats["fetched"] == 1
        assert stats["errors"] == 0
        mock_db.commit.assert_called_once()


class TestTASEApiServiceCacheStats:
    """Test cache statistics methods."""

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        service = TASEApiService(api_key="test", base_url="https://test.com")
        mock_db = MagicMock()

        mock_db.query.return_value.scalar.side_effect = [
            500,  # total count
            datetime(2024, 1, 15, 21, 0),  # last sync time
        ]

        stats = service.get_cache_stats(mock_db)

        assert stats["total_securities"] == 500
        assert stats["last_synced_at"] == datetime(2024, 1, 15, 21, 0)
