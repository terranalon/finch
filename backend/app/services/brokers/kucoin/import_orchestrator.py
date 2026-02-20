"""KuCoin import orchestration service.

Probes the API to detect history truncation, then delegates to either
CryptoImportService (full history) or KuCoinSyntheticImportService (snapshot).
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.services.brokers.import_service_registry import BrokerImportServiceRegistry
from app.services.brokers.kucoin.client import KuCoinAPIError, KuCoinClient
from app.services.brokers.kucoin.synthetic_import_service import KuCoinSyntheticImportService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    """Result of a KuCoin import orchestration operation."""

    import_mode: Literal["full_history", "snapshot"]
    stats: dict[str, Any]
    snapshot_start: date


class KuCoinImportOrchestrator:
    """Orchestrates KuCoin import: probe history, decide strategy, import."""

    @staticmethod
    def execute(
        db: Session,
        account_id: int,
        client: KuCoinClient,
    ) -> ImportResult:
        """Probe API history coverage and import based on account age.

        Strategy:
        - "full" coverage -> full_history: fetch all fills/deposits/withdrawals
        - "truncated" coverage -> snapshot: create synthetic transactions from balances
        - "empty" + balances exist -> snapshot: account has assets but no visible history
        - "empty" + no balances -> full_history: new/empty account, nothing to import

        Returns:
            ImportResult with the chosen mode and import stats.
        """
        coverage = client.probe_history_coverage()

        if coverage == "full":
            return KuCoinImportOrchestrator._do_full_history(db, account_id, client)

        if coverage == "truncated":
            return KuCoinImportOrchestrator._do_snapshot(db, account_id, client)

        # coverage == "empty": check if there are balances to snapshot
        try:
            balances = client.get_account_balances()
        except KuCoinAPIError:
            balances = {}

        if balances:
            return KuCoinImportOrchestrator._do_snapshot(db, account_id, client, balances)

        return KuCoinImportOrchestrator._do_full_history(db, account_id, client)

    @staticmethod
    def _do_full_history(db: Session, account_id: int, client: KuCoinClient) -> ImportResult:
        """Import full transaction history via CryptoImportService."""
        logger.info("Account %d: using full history import", account_id)

        broker_data = client.fetch_all_data()
        import_service = BrokerImportServiceRegistry.get_import_service("kucoin", db)
        stats = import_service.import_data(account_id, broker_data, source_id=None)

        snapshot_start = (
            date.fromisoformat(stats["date_range"]["start_date"])
            if stats.get("date_range", {}).get("start_date")
            else broker_data.start_date
        )

        return ImportResult(
            import_mode="full_history",
            stats=stats,
            snapshot_start=snapshot_start,
        )

    @staticmethod
    def _do_snapshot(
        db: Session,
        account_id: int,
        client: KuCoinClient,
        balances: dict | None = None,
    ) -> ImportResult:
        """Create synthetic snapshot from current positions."""
        logger.info("Account %d: using snapshot import", account_id)

        stats = KuCoinSyntheticImportService.import_snapshot(db, account_id, client, balances)

        return ImportResult(
            import_mode="snapshot",
            stats=stats,
            snapshot_start=date.today(),
        )
