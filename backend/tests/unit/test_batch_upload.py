"""Tests for batch upload sessions with deferred reconstruction.

Batch upload mode allows multiple files to be uploaded with a shared session_id.
Each upload stages the source (status='staged') and imports transactions without
running reconstruction. When all files are uploaded, the finalize endpoint runs
a single reconstruction for all staged sources.

Tests cover:
1. Upload endpoint: session_id parameter sets status='staged' and skips reconstruction
2. Finalize endpoint: finds staged sources, deletes synthetics, marks completed,
   runs single reconstruction, and triggers snapshot generation
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.broker_data_source import BrokerDataSource


def _make_db_mock_with_auto_id():
    """Create a mock DB session that auto-assigns source.id on flush."""
    mock_db = MagicMock()
    _added_objects = []

    def _track_add(obj):
        _added_objects.append(obj)

    def _auto_set_id():
        for obj in _added_objects:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 1

    mock_db.add.side_effect = _track_add
    mock_db.flush.side_effect = _auto_set_id
    return mock_db


class TestBatchUploadStaging:
    """Upload endpoint with session_id should stage sources and skip reconstruction."""

    def test_staged_source_has_correct_status(self):
        """A source created with status='staged' should retain that status."""
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="file_upload",
            source_identifier="test.xml",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            status="staged",
        )
        assert source.status == "staged"

    def test_staged_source_stores_session_id_in_import_stats(self):
        """A staged source should have the session_id in import_stats."""
        session_id = str(uuid.uuid4())
        source = BrokerDataSource(
            account_id=1,
            broker_type="ibkr",
            source_type="file_upload",
            source_identifier="test.xml",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            status="staged",
            import_stats={"session_id": session_id, "total_records": 50},
        )
        assert source.import_stats["session_id"] == session_id

    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data.get_overlap_detector")
    @patch("app.routers.broker_data.get_file_storage")
    @patch("app.routers.broker_data._get_parser_for_file")
    @patch("app.routers.broker_data._validate_broker_type")
    @patch("app.routers.broker_data._validate_account_access")
    def test_upload_with_session_id_returns_staged_status(
        self,
        mock_validate_access,
        mock_validate_broker,
        mock_get_parser,
        mock_get_storage,
        mock_get_overlap,
        mock_delete_synthetic,
    ):
        """When session_id is provided, upload should return status='staged'."""
        import asyncio

        from app.routers.broker_data import upload_broker_file

        # Setup mocks
        mock_parser = MagicMock()
        mock_parser.validate_file.return_value = (True, None)
        mock_parser.extract_date_range.return_value = (
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        mock_get_parser.return_value = mock_parser

        mock_storage = MagicMock()
        mock_storage.calculate_hash.return_value = "abc123"
        mock_storage.check_duplicate.return_value = None
        mock_storage.save_file.return_value = ("/tmp/test.xml", "abc123", 1024)
        mock_storage.get_extension.return_value = ".xml"
        mock_get_storage.return_value = mock_storage

        mock_overlap = MagicMock()
        mock_overlap.analyze_overlap.return_value = MagicMock(overlapping_sources=[])
        mock_get_overlap.return_value = mock_overlap

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }

        mock_db = _make_db_mock_with_auto_id()
        mock_user = MagicMock()

        mock_file = MagicMock()
        mock_file.filename = "activity_2023.xml"
        mock_file.read = AsyncMock(return_value=b"<xml>data</xml>")

        # Use a non-IBKR broker type to use the generic parser path
        # which is simpler to mock
        mock_import_service = MagicMock()
        mock_import_service.import_data.return_value = {"transactions": {"imported": 5}}

        session_id = str(uuid.uuid4())

        with (
            patch("app.routers.broker_data.BrokerImportServiceRegistry") as mock_registry,
        ):
            mock_registry.is_supported.return_value = True
            mock_registry.get_import_service.return_value = mock_import_service
            mock_parser.parse.return_value = MagicMock(total_records=5)

            result = asyncio.run(
                upload_broker_file(
                    account_id=1,
                    broker_type="kraken",
                    file=mock_file,
                    confirm_overlap=False,
                    session_id=session_id,
                    background_tasks=None,
                    db=mock_db,
                    current_user=mock_user,
                )
            )

        assert result.status == "staged"
        assert "staged" in result.message.lower() or "batch" in result.message.lower()

    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data.get_overlap_detector")
    @patch("app.routers.broker_data.get_file_storage")
    @patch("app.routers.broker_data._get_parser_for_file")
    @patch("app.routers.broker_data._validate_broker_type")
    @patch("app.routers.broker_data._validate_account_access")
    def test_upload_without_session_id_returns_completed_status(
        self,
        mock_validate_access,
        mock_validate_broker,
        mock_get_parser,
        mock_get_storage,
        mock_get_overlap,
        mock_delete_synthetic,
    ):
        """Without session_id, upload should return status='completed' as before."""
        import asyncio

        from app.routers.broker_data import upload_broker_file

        # Setup mocks
        mock_parser = MagicMock()
        mock_parser.validate_file.return_value = (True, None)
        mock_parser.extract_date_range.return_value = (
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        mock_get_parser.return_value = mock_parser

        mock_storage = MagicMock()
        mock_storage.calculate_hash.return_value = "abc123"
        mock_storage.check_duplicate.return_value = None
        mock_storage.save_file.return_value = ("/tmp/test.xml", "abc123", 1024)
        mock_storage.get_extension.return_value = ".xml"
        mock_get_storage.return_value = mock_storage

        mock_overlap = MagicMock()
        mock_overlap.analyze_overlap.return_value = MagicMock(overlapping_sources=[])
        mock_get_overlap.return_value = mock_overlap

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }

        mock_db = _make_db_mock_with_auto_id()
        mock_user = MagicMock()

        mock_file = MagicMock()
        mock_file.filename = "activity_2023.csv"
        mock_file.read = AsyncMock(return_value=b"data")

        mock_import_service = MagicMock()
        mock_import_service.import_data.return_value = {"transactions": {"imported": 5}}

        with (
            patch("app.routers.broker_data.BrokerImportServiceRegistry") as mock_registry,
        ):
            mock_registry.is_supported.return_value = True
            mock_registry.get_import_service.return_value = mock_import_service
            mock_parser.parse.return_value = MagicMock(total_records=5)

            result = asyncio.run(
                upload_broker_file(
                    account_id=1,
                    broker_type="kraken",
                    file=mock_file,
                    confirm_overlap=False,
                    session_id=None,
                    background_tasks=None,
                    db=mock_db,
                    current_user=mock_user,
                )
            )

        assert result.status == "completed"

    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data.get_overlap_detector")
    @patch("app.routers.broker_data.get_file_storage")
    @patch("app.routers.broker_data._get_parser_for_file")
    @patch("app.routers.broker_data._validate_broker_type")
    @patch("app.routers.broker_data._validate_account_access")
    def test_upload_with_session_id_skips_background_snapshot(
        self,
        mock_validate_access,
        mock_validate_broker,
        mock_get_parser,
        mock_get_storage,
        mock_get_overlap,
        mock_delete_synthetic,
    ):
        """When session_id is provided, background snapshot generation should be skipped."""
        import asyncio

        from app.routers.broker_data import upload_broker_file

        mock_parser = MagicMock()
        mock_parser.validate_file.return_value = (True, None)
        mock_parser.extract_date_range.return_value = (
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        mock_get_parser.return_value = mock_parser

        mock_storage = MagicMock()
        mock_storage.calculate_hash.return_value = "abc123"
        mock_storage.check_duplicate.return_value = None
        mock_storage.save_file.return_value = ("/tmp/test.xml", "abc123", 1024)
        mock_storage.get_extension.return_value = ".xml"
        mock_get_storage.return_value = mock_storage

        mock_overlap = MagicMock()
        mock_overlap.analyze_overlap.return_value = MagicMock(overlapping_sources=[])
        mock_get_overlap.return_value = mock_overlap

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }

        mock_db = _make_db_mock_with_auto_id()
        mock_user = MagicMock()
        mock_bg_tasks = MagicMock()

        mock_file = MagicMock()
        mock_file.filename = "activity_2023.csv"
        mock_file.read = AsyncMock(return_value=b"data")

        mock_import_service = MagicMock()
        mock_import_service.import_data.return_value = {"transactions": {"imported": 5}}

        session_id = str(uuid.uuid4())

        with (
            patch("app.routers.broker_data.BrokerImportServiceRegistry") as mock_registry,
        ):
            mock_registry.is_supported.return_value = True
            mock_registry.get_import_service.return_value = mock_import_service
            mock_parser.parse.return_value = MagicMock(total_records=5)

            result = asyncio.run(
                upload_broker_file(
                    account_id=1,
                    broker_type="kraken",
                    file=mock_file,
                    confirm_overlap=False,
                    session_id=session_id,
                    background_tasks=mock_bg_tasks,
                    db=mock_db,
                    current_user=mock_user,
                )
            )

        # Background tasks should NOT have been used for staged uploads
        mock_bg_tasks.add_task.assert_not_called()
        assert result.status == "staged"


class TestFinalizeBatchEndpoint:
    """Tests for the POST /api/broker-data/finalize-batch/{account_id} endpoint."""

    def test_finalize_endpoint_exists(self):
        """The finalize-batch endpoint should be importable."""
        from app.routers.broker_data import finalize_batch_upload

        assert callable(finalize_batch_upload)

    @patch("app.routers.broker_data.generate_snapshots_background")
    @patch("app.routers.broker_data.update_snapshot_status")
    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_marks_sources_completed(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
        mock_update_status,
        mock_gen_snapshots,
    ):
        """Finalize should mark all staged sources as 'completed'."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source1 = MagicMock(spec=BrokerDataSource)
        mock_source1.status = "staged"
        mock_source1.broker_type = "ibkr"
        mock_source1.import_stats = {"session_id": session_id}
        mock_source1.start_date = date(2022, 1, 1)
        mock_source1.end_date = date(2022, 12, 31)

        mock_source2 = MagicMock(spec=BrokerDataSource)
        mock_source2.status = "staged"
        mock_source2.broker_type = "ibkr"
        mock_source2.import_stats = {"session_id": session_id}
        mock_source2.start_date = date(2023, 1, 1)
        mock_source2.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_source1,
            mock_source2,
        ]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 5}

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        assert result["status"] == "completed"
        assert result["sources_finalized"] == 2
        assert mock_source1.status == "completed"
        assert mock_source2.status == "completed"

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_runs_single_reconstruction(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize should call reconstruct_and_update_holdings exactly once."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 3}

        asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        mock_reconstruct.assert_called_once_with(mock_db, 1)

    @patch("app.routers.broker_data.PortfolioReconstructionService")
    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_deletes_synthetic_sources(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
        mock_recon_service,
    ):
        """Finalize should call _delete_synthetic_sources before reconstruction."""
        import asyncio
        from decimal import Decimal

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 1,
            "deleted_transactions": 5,
            "deleted_cash_balances": 2,
            "snapshot_positions": [{"symbol": "AAPL", "quantity": "100", "cost_basis": "15000"}],
        }
        mock_reconstruct.return_value = {"holdings_updated": 3}
        mock_recon_service.reconstruct_holdings.return_value = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        mock_delete_synthetic.assert_called_once_with(mock_db, 1, "ibkr")
        assert result["synthetic_cleanup"]["deleted_sources"] == 1

    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_raises_404_for_unknown_session(self, mock_validate_access):
        """Finalize should raise 404 when no staged sources match the session_id."""
        import asyncio

        from fastapi import HTTPException

        from app.routers.broker_data import finalize_batch_upload

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_user = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                finalize_batch_upload(
                    account_id=1,
                    session_id="nonexistent-session-id",
                    background_tasks=None,
                    db=mock_db,
                    current_user=mock_user,
                )
            )

        assert exc_info.value.status_code == 404

    @patch("app.routers.broker_data.generate_snapshots_background")
    @patch("app.routers.broker_data.update_snapshot_status")
    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_triggers_snapshot_generation(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
        mock_update_status,
        mock_gen_snapshots,
    ):
        """Finalize should trigger background snapshot generation when background_tasks is provided."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()
        mock_bg_tasks = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 3}

        asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=mock_bg_tasks,
                db=mock_db,
                current_user=mock_user,
            )
        )

        mock_update_status.assert_called_once()
        mock_bg_tasks.add_task.assert_called_once()

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_returns_correct_date_range(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize should return the overall date range spanning all staged sources."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source1 = MagicMock(spec=BrokerDataSource)
        mock_source1.status = "staged"
        mock_source1.broker_type = "ibkr"
        mock_source1.import_stats = {"session_id": session_id}
        mock_source1.start_date = date(2022, 3, 15)
        mock_source1.end_date = date(2022, 12, 31)

        mock_source2 = MagicMock(spec=BrokerDataSource)
        mock_source2.status = "staged"
        mock_source2.broker_type = "ibkr"
        mock_source2.import_stats = {"session_id": session_id}
        mock_source2.start_date = date(2023, 1, 1)
        mock_source2.end_date = date(2023, 9, 30)

        mock_source3 = MagicMock(spec=BrokerDataSource)
        mock_source3.status = "staged"
        mock_source3.broker_type = "ibkr"
        mock_source3.import_stats = {"session_id": session_id}
        mock_source3.start_date = date(2024, 1, 1)
        mock_source3.end_date = date(2024, 6, 15)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_source1,
            mock_source2,
            mock_source3,
        ]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 10}

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        assert result["date_range"]["start_date"] == "2022-03-15"
        assert result["date_range"]["end_date"] == "2024-06-15"
        assert result["sources_finalized"] == 3

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_only_matches_correct_session_id(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize should only process sources matching the given session_id."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())
        other_session_id = str(uuid.uuid4())

        # Source with matching session_id
        mock_source_match = MagicMock(spec=BrokerDataSource)
        mock_source_match.status = "staged"
        mock_source_match.broker_type = "ibkr"
        mock_source_match.import_stats = {"session_id": session_id}
        mock_source_match.start_date = date(2023, 1, 1)
        mock_source_match.end_date = date(2023, 12, 31)

        # Source with different session_id
        mock_source_other = MagicMock(spec=BrokerDataSource)
        mock_source_other.status = "staged"
        mock_source_other.broker_type = "ibkr"
        mock_source_other.import_stats = {"session_id": other_session_id}
        mock_source_other.start_date = date(2022, 1, 1)
        mock_source_other.end_date = date(2022, 12, 31)

        mock_db = MagicMock()
        # Return both sources from the DB query (both are staged for account 1)
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_source_match,
            mock_source_other,
        ]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 3}

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        # Only the matching source should be finalized
        assert result["sources_finalized"] == 1
        assert mock_source_match.status == "completed"
        # The other source should remain staged
        assert mock_source_other.status == "staged"

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_includes_reconstruction_stats(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize response should include holdings_reconstruction stats."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        reconstruction_result = {"holdings_updated": 7, "holdings_zeroed": 1}
        mock_reconstruct.return_value = reconstruction_result

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        assert result["holdings_reconstruction"] == reconstruction_result

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_commits_changes(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize should commit the database transaction."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 1}

        asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        mock_db.commit.assert_called()

    @patch("app.routers.broker_data.PortfolioReconstructionService")
    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_runs_validation_when_snapshot_positions_exist(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
        mock_recon_service,
    ):
        """Finalize should validate reconstructed holdings against snapshot data."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        snapshot_positions = [
            {"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"},
        ]
        mock_delete_synthetic.return_value = {
            "deleted_sources": 1,
            "deleted_transactions": 1,
            "deleted_cash_balances": 0,
            "snapshot_positions": snapshot_positions,
        }
        mock_reconstruct.return_value = {"holdings_updated": 1}

        # Mock the reconstruction service to return matching holdings
        from decimal import Decimal

        mock_recon_service.reconstruct_holdings.return_value = [
            {"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")},
        ]

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        assert result["validation"] is not None
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["positions_matched"] == 1

    @patch("app.routers.broker_data.reconstruct_and_update_holdings")
    @patch("app.routers.broker_data._delete_synthetic_sources")
    @patch("app.routers.broker_data._validate_account_access")
    def test_finalize_skips_validation_when_no_snapshot_positions(
        self,
        mock_validate_access,
        mock_delete_synthetic,
        mock_reconstruct,
    ):
        """Finalize should skip validation when no synthetic cleanup happened."""
        import asyncio

        from app.routers.broker_data import finalize_batch_upload

        session_id = str(uuid.uuid4())

        mock_source = MagicMock(spec=BrokerDataSource)
        mock_source.status = "staged"
        mock_source.broker_type = "ibkr"
        mock_source.import_stats = {"session_id": session_id}
        mock_source.start_date = date(2023, 1, 1)
        mock_source.end_date = date(2023, 12, 31)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_source]
        mock_user = MagicMock()

        mock_delete_synthetic.return_value = {
            "deleted_sources": 0,
            "deleted_transactions": 0,
            "deleted_cash_balances": 0,
            "snapshot_positions": [],
        }
        mock_reconstruct.return_value = {"holdings_updated": 1}

        result = asyncio.run(
            finalize_batch_upload(
                account_id=1,
                session_id=session_id,
                background_tasks=None,
                db=mock_db,
                current_user=mock_user,
            )
        )

        assert result["validation"] is None
