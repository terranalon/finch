"""Manual import service for persisting user-provided CSV/XLSX data."""

import logging
from datetime import datetime

from app.models import Asset
from app.services.brokers.base_broker_parser import (
    BrokerImportData,
    ParsedCashTransaction,
    ParsedTransaction,
)
from app.services.brokers.base_import_service import (
    BaseBrokerImportService,
    extract_date_range_serializable,
)
from app.services.shared.transaction_hash_service import create_or_transfer_transaction

logger = logging.getLogger(__name__)


class ManualImportService(BaseBrokerImportService):
    """Import service for manually created CSV/XLSX files.

    Handles mixed asset classes (stocks, crypto, cash) in a single file.
    Uses cascading asset resolution: DB -> yfinance -> CoinGecko -> fallback.
    """

    @classmethod
    def supported_broker_types(cls) -> list[str]:
        return ["manual"]

    def import_data(
        self,
        account_id: int,
        data: BrokerImportData,
        source_id: int | None = None,
        skip_reconstruction: bool = False,
    ) -> dict:
        stats = {
            "account_id": account_id,
            "broker": "Manual Import",
            "start_time": datetime.now().isoformat(),
            "transactions": {},
            "cash_transactions": {},
            "dividends": {},
            "holdings_reconstruction": {},
            "errors": [],
        }

        all_items = (data.transactions or []) + (data.dividends or [])
        unique_symbols = {item.symbol for item in all_items if item.symbol}
        stats["unique_assets_in_file"] = len(unique_symbols)
        stats["symbols_in_file"] = list(unique_symbols)

        try:
            if data.cash_transactions:
                stats["cash_transactions"] = self._import_cash_transactions(
                    account_id, data.cash_transactions, source_id
                )
            if data.transactions:
                stats["transactions"] = self._import_asset_transactions(
                    account_id, data.transactions, source_id
                )
            if data.dividends:
                stats["dividends"] = self._import_asset_transactions(
                    account_id, data.dividends, source_id
                )

            self.db.commit()

            if not skip_reconstruction and (
                data.transactions or data.dividends or data.cash_transactions
            ):
                stats["holdings_reconstruction"] = self._reconstruct_holdings(account_id)
                self.db.commit()

            all_dates = (
                [txn.trade_date for txn in data.transactions]
                + [cash_txn.date for cash_txn in data.cash_transactions]
                + [div.trade_date for div in data.dividends]
            )
            date_range = extract_date_range_serializable(all_dates)
            if date_range:
                stats["date_range"] = date_range

            stats["status"] = "completed"

        except Exception as e:
            logger.exception("Manual import failed")
            self.db.rollback()
            stats["status"] = "failed"
            stats["errors"].append(str(e))

        stats["end_time"] = datetime.now().isoformat()
        return stats

    def _import_asset_transactions(
        self,
        account_id: int,
        transactions: list[ParsedTransaction],
        source_id: int | None = None,
    ) -> dict:
        """Import transactions that require asset resolution (trades and dividends)."""
        stats = {
            "total": len(transactions),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "assets_created": 0,
            "errors": [],
        }

        for txn in transactions:
            try:
                asset, created = self._find_or_create_asset(txn.symbol, txn.currency)
                if created:
                    stats["assets_created"] += 1

                holding = self._find_or_create_holding_for_asset(account_id, asset)

                result, _ = create_or_transfer_transaction(
                    db=self.db,
                    holding_id=holding.id,
                    source_id=source_id,
                    txn_date=txn.trade_date,
                    txn_type=txn.transaction_type,
                    symbol=txn.symbol,
                    quantity=txn.quantity,
                    price=txn.price_per_unit,
                    fees=txn.fees,
                    amount=txn.amount,
                    notes=f"Manual Import - {txn.notes or txn.transaction_type}",
                    account_id=account_id,
                )
                result.update_stats(stats)

            except Exception as e:
                logger.error("Error importing %s for %s: %s", txn.transaction_type, txn.symbol, e)
                stats["errors"].append(f"{txn.symbol}: {e!s}")

        return stats

    def _import_cash_transactions(
        self,
        account_id: int,
        cash_transactions: list[ParsedCashTransaction],
        source_id: int | None = None,
    ) -> dict:
        stats = {
            "total": len(cash_transactions),
            "imported": 0,
            "transferred": 0,
            "skipped": 0,
            "errors": [],
        }

        for cash_txn in cash_transactions:
            try:
                asset, _ = self._find_or_create_cash_asset(cash_txn.currency)
                holding = self._find_or_create_holding_for_asset(account_id, asset)

                result, _ = create_or_transfer_transaction(
                    db=self.db,
                    holding_id=holding.id,
                    source_id=source_id,
                    txn_date=cash_txn.date,
                    txn_type=cash_txn.transaction_type,
                    symbol=cash_txn.currency,
                    amount=cash_txn.amount,
                    fees=cash_txn.fees,
                    notes=f"Manual Import - {cash_txn.notes or cash_txn.transaction_type}",
                    account_id=account_id,
                )
                result.update_stats(stats)

            except Exception as e:
                logger.error("Error importing cash transaction: %s", e)
                stats["errors"].append(str(e))

        return stats

    # -- Asset resolution ------------------------------------------------------

    def _find_or_create_asset(self, symbol: str, currency: str) -> tuple[Asset, bool]:
        """Cascading asset resolution: DB -> yfinance -> CoinGecko -> fallback."""
        existing = self.asset_repo.find_by_symbol(symbol)
        if existing:
            return existing, False

        asset_class, name, category, industry = self._try_yfinance(symbol)
        if asset_class:
            return self.asset_repo.find_or_create(
                symbol,
                name=name or symbol,
                asset_class=asset_class,
                currency=currency,
                category=category,
                industry=industry,
                data_source="manual",
            )

        crypto_name = self._try_coingecko(symbol)
        if crypto_name:
            return self.asset_repo.find_or_create(
                symbol,
                name=crypto_name,
                asset_class="Crypto",
                currency=currency,
                category="Cryptocurrency",
                data_source="manual",
            )

        logger.warning("Could not resolve asset type for %s, defaulting to Stock", symbol)
        return self.asset_repo.find_or_create(
            symbol,
            name=symbol,
            asset_class="Stock",
            currency=currency,
            data_source="manual",
        )

    def _find_or_create_cash_asset(self, currency: str) -> tuple[Asset, bool]:
        return self.asset_repo.find_or_create(
            currency,
            name=f"{currency} Cash",
            asset_class="Cash",
            currency=currency,
            data_source="manual",
        )

    @staticmethod
    def _try_yfinance(symbol: str) -> tuple[str | None, str | None, str | None, str | None]:
        """Returns (asset_class, name, category, industry) or (None, None, None, None)."""
        from app.services.shared.asset_metadata_service import AssetMetadataService
        from app.services.shared.asset_type_detector import AssetTypeDetector

        try:
            type_result = AssetTypeDetector.detect_asset_type(symbol)
            if not type_result.detected_type:
                return None, None, None, None

            metadata = AssetMetadataService.fetch_name_from_yfinance(
                symbol, type_result.detected_type
            )
            return (
                type_result.detected_type,
                metadata.name,
                metadata.category,
                metadata.industry,
            )
        except Exception as e:
            logger.debug("yfinance lookup failed for %s: %s", symbol, e)
            return None, None, None, None

    @staticmethod
    def _try_coingecko(symbol: str) -> str | None:
        """Returns coin name or None."""
        from app.services.market_data.coingecko_client import CoinGeckoClient

        try:
            client = CoinGeckoClient()
            coin_info = client.get_coin_info(symbol)
            if coin_info:
                return coin_info["name"]  # ty: ignore[invalid-return-type] — "name" key is always str
        except Exception as e:
            logger.debug("CoinGecko lookup failed for %s: %s", symbol, e)
        return None
