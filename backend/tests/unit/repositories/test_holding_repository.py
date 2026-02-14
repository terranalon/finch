"""Tests for HoldingRepository new join-based methods."""

from decimal import Decimal

from app.models import Holding
from app.services.repositories.holding_repository import HoldingRepository


class TestHoldingRepositoryJoinMethods:
    """Test cases for new HoldingRepository methods with joins."""

    def test_find_active_with_assets(self, db, test_account, test_asset, test_holding):
        """Returns (Holding, Asset) tuples for active holdings."""
        repo = HoldingRepository(db)
        results = repo.find_active_with_assets([test_account.id])
        assert len(results) >= 1
        holding, asset = results[0]
        assert holding.is_active is True
        assert asset.id == test_asset.id

    def test_find_active_with_assets_filters_inactive(self, db, test_account, test_asset):
        """Excludes inactive holdings."""
        inactive = Holding(
            account_id=test_account.id,
            asset_id=test_asset.id,
            quantity=Decimal("0"),
            cost_basis=Decimal("0"),
            is_active=False,
        )
        db.add(inactive)
        db.commit()

        repo = HoldingRepository(db)
        results = repo.find_active_with_assets([test_account.id])
        for holding, asset in results:
            assert holding.is_active is True

    def test_find_active_with_assets_and_accounts(self, db, test_account, test_asset, test_holding):
        """Returns (Holding, Asset, account_name) tuples."""
        repo = HoldingRepository(db)
        results = repo.find_active_with_assets_and_accounts([test_account.id])
        assert len(results) >= 1
        holding, asset, account_name = results[0]
        assert account_name == test_account.name

    def test_find_with_assets_by_account_nonzero(self, db, test_account, test_asset, test_holding):
        """Returns holdings with non-zero quantity."""
        repo = HoldingRepository(db)
        results = repo.find_with_assets_by_account_nonzero(test_account.id)
        assert len(results) >= 1
        for holding, asset in results:
            assert holding.quantity != 0
