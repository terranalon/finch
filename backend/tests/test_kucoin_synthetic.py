"""Tests for KuCoin synthetic snapshot import service."""

import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.services.brokers.kucoin.client import KuCoinClient, KuCoinCredentials


def _make_mock_http(response_data: dict) -> MagicMock:
    """Create a mock httpx.Client context manager returning the given JSON data."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_http = MagicMock()
    mock_http.get.return_value = mock_response
    mock_http.__enter__ = MagicMock(return_value=mock_http)
    mock_http.__exit__ = MagicMock(return_value=False)
    return mock_http


class TestKuCoinSyntheticImportService:
    """Tests for KuCoinSyntheticImportService."""

    @pytest.fixture
    def db(self):
        """Mock database session."""
        session = MagicMock(spec=Session)
        account = MagicMock()
        account.id = 1
        session.query.return_value.filter.return_value.first.return_value = account
        return session

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("key", "secret", "pass"))

    @pytest.fixture
    def import_service(self):
        """Lazy-import KuCoinSyntheticImportService to avoid circular imports."""
        from app.services.brokers.kucoin.synthetic_import_service import (
            KuCoinSyntheticImportService,
        )

        return KuCoinSyntheticImportService

    def _run_with_balances(self, db, client, import_service, balances):
        """Run import_snapshot with standard mocks for the given balances.

        Patches at definition site for lazy-import compatibility (see MEMORY.md).
        """
        from app.services.shared.transaction_hash_service import DedupResult

        mock_holding = MagicMock()
        mock_holding.id = 1

        with (
            patch.object(client, "get_account_balances", return_value=balances),
            patch(
                "app.services.brokers.shared.crypto_import_service.CryptoImportService._get_or_create_holding",
                return_value=(mock_holding, False),
            ),
            patch(
                "app.services.brokers.kucoin.synthetic_import_service.create_or_transfer_transaction",
                return_value=(DedupResult.NEW, MagicMock()),
            ),
            patch(
                "app.services.brokers.kucoin.synthetic_import_service.reconstruct_and_update_holdings",
                return_value={},
            ),
        ):
            return import_service.import_snapshot(db, 1, client)

    def test_import_snapshot_creates_source(self, db, client, import_service):
        """Synthetic import creates a BrokerDataSource with source_type='synthetic'."""
        with (
            patch.object(client, "get_account_balances", return_value={}),
            patch(
                "app.services.brokers.kucoin.synthetic_import_service.reconstruct_and_update_holdings",
                return_value={},
            ),
        ):
            stats = import_service.import_snapshot(db, 1, client)

        assert stats["source_type"] == "synthetic"

    def test_import_snapshot_creates_buy_transactions(self, db, client, import_service):
        """Each non-zero balance produces a synthetic Buy transaction."""
        balances = {"BTC": Decimal("1.5"), "ETH": Decimal("10.0")}
        stats = self._run_with_balances(db, client, import_service, balances)

        assert stats["positions_imported"] == 2

    def test_import_snapshot_stores_snapshot_positions(self, db, client, import_service):
        """Snapshot positions are stored in import_stats."""
        balances = {"BTC": Decimal("0.5")}
        stats = self._run_with_balances(db, client, import_service, balances)

        assert stats["status"] == "completed"
        assert len(stats.get("snapshot_positions", [])) == 1
        assert stats["snapshot_positions"][0]["symbol"] == "BTC"

    def test_import_snapshot_skips_zero_balances(self, db, client, import_service):
        """Zero-balance positions are not imported."""
        balances = {"BTC": Decimal("0"), "ETH": Decimal("5.0")}
        stats = self._run_with_balances(db, client, import_service, balances)

        assert stats["positions_imported"] == 1

    def test_import_snapshot_handles_api_error(self, db, client, import_service):
        """API errors produce a failed status, not an exception."""
        from app.services.brokers.kucoin.client import KuCoinAPIError

        with patch.object(
            client, "get_account_balances", side_effect=KuCoinAPIError("Network error")
        ):
            stats = import_service.import_snapshot(db, 1, client)

        assert stats["status"] == "failed"
        assert any("Network error" in e for e in stats["errors"])


class TestKuCoinImportOrchestrator:
    """Tests for KuCoinImportOrchestrator."""

    @pytest.fixture
    def db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("key", "secret", "pass"))

    @pytest.fixture
    def orchestrator(self):
        """Lazy-import KuCoinImportOrchestrator to avoid circular imports."""
        from app.services.brokers.kucoin.import_orchestrator import KuCoinImportOrchestrator

        return KuCoinImportOrchestrator

    def test_full_history_mode(self, db, client, orchestrator):
        """When history is 'full', orchestrator uses CryptoImportService."""
        mock_broker_data = MagicMock()
        mock_broker_data.start_date = MagicMock()

        with (
            patch.object(client, "probe_history_coverage", return_value="full"),
            patch.object(client, "fetch_all_data", return_value=mock_broker_data),
            patch(
                "app.services.brokers.kucoin.import_orchestrator.BrokerImportServiceRegistry"
            ) as mock_registry,
        ):
            mock_service = MagicMock()
            mock_service.import_data.return_value = {"status": "completed", "date_range": {}}
            mock_registry.get_import_service.return_value = mock_service

            result = orchestrator.execute(db, 1, client)

        assert result.import_mode == "full_history"

    def test_snapshot_mode(self, db, client, orchestrator):
        """When history is 'truncated', orchestrator uses synthetic import."""
        with (
            patch.object(client, "probe_history_coverage", return_value="truncated"),
            patch(
                "app.services.brokers.kucoin.import_orchestrator.KuCoinSyntheticImportService"
            ) as mock_synthetic,
        ):
            mock_synthetic.import_snapshot.return_value = {
                "status": "completed",
                "positions_imported": 3,
            }

            result = orchestrator.execute(db, 1, client)

        assert result.import_mode == "snapshot"

    def test_empty_history_uses_snapshot_when_balances_exist(self, db, client, orchestrator):
        """When no fills exist but balances do, use snapshot mode."""
        with (
            patch.object(client, "probe_history_coverage", return_value="empty"),
            patch.object(client, "get_account_balances", return_value={"BTC": Decimal("1.0")}),
            patch(
                "app.services.brokers.kucoin.import_orchestrator.KuCoinSyntheticImportService"
            ) as mock_synthetic,
        ):
            mock_synthetic.import_snapshot.return_value = {"status": "completed"}

            result = orchestrator.execute(db, 1, client)

        assert result.import_mode == "snapshot"

    def test_empty_history_no_balances_uses_full_history(self, db, client, orchestrator):
        """When no fills and no balances, treat as full_history (new/empty account)."""
        mock_broker_data = MagicMock()
        mock_broker_data.start_date = MagicMock()

        with (
            patch.object(client, "probe_history_coverage", return_value="empty"),
            patch.object(client, "get_account_balances", return_value={}),
            patch.object(client, "fetch_all_data", return_value=mock_broker_data),
            patch(
                "app.services.brokers.kucoin.import_orchestrator.BrokerImportServiceRegistry"
            ) as mock_registry,
        ):
            mock_service = MagicMock()
            mock_service.import_data.return_value = {"status": "completed", "date_range": {}}
            mock_registry.get_import_service.return_value = mock_service

            result = orchestrator.execute(db, 1, client)

        assert result.import_mode == "full_history"


class TestProbeHistoryCoverage:
    """Tests for KuCoinClient.probe_history_coverage()."""

    @pytest.fixture
    def client(self):
        return KuCoinClient(KuCoinCredentials("key", "secret", "pass"))

    @patch("app.services.brokers.kucoin.client.httpx.Client")
    def test_empty_fills_returns_empty(self, mock_client_class, client):
        mock_client_class.return_value = _make_mock_http(
            {"code": "200000", "data": {"items": [], "totalPage": 1}}
        )

        assert client.probe_history_coverage() == "empty"

    @patch("app.services.brokers.kucoin.client.httpx.Client")
    def test_recent_fills_returns_full(self, mock_client_class, client):
        """Oldest fill is 30 days ago -- well within the window."""
        thirty_days_ago_ms = int((time.time() - 30 * 86400) * 1000)

        mock_client_class.return_value = _make_mock_http(
            {
                "code": "200000",
                "data": {
                    "items": [{"createdAt": thirty_days_ago_ms, "symbol": "BTC-USDT"}],
                    "totalPage": 1,
                },
            }
        )

        assert client.probe_history_coverage() == "full"

    @patch("app.services.brokers.kucoin.client.httpx.Client")
    def test_boundary_fills_returns_truncated(self, mock_client_class, client):
        """Oldest fill is 178 days ago -- near the boundary."""
        boundary_ms = int((time.time() - 178 * 86400) * 1000)

        mock_client_class.return_value = _make_mock_http(
            {
                "code": "200000",
                "data": {
                    "items": [{"createdAt": boundary_ms, "symbol": "BTC-USDT"}],
                    "totalPage": 1,
                },
            }
        )

        assert client.probe_history_coverage() == "truncated"
