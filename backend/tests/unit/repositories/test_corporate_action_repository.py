"""Tests for CorporateActionRepository."""

from datetime import date

from app.models import CorporateAction
from app.services.repositories.corporate_action_repository import CorporateActionRepository


class TestCorporateActionRepository:
    """Test cases for CorporateActionRepository."""

    def test_find_effective_before_returns_actions(self, db, test_asset):
        """Returns corporate actions effective on or before date."""
        action = CorporateAction(
            old_asset_id=test_asset.id,
            new_asset_id=test_asset.id,
            action_type="ticker_change",
            effective_date=date(2024, 6, 15),
        )
        db.add(action)
        db.commit()

        repo = CorporateActionRepository(db)
        results = repo.find_effective_before(date(2024, 6, 15))
        assert len(results) == 1

    def test_find_effective_before_excludes_future(self, db, test_asset):
        """Excludes actions after the given date."""
        action = CorporateAction(
            old_asset_id=test_asset.id,
            new_asset_id=test_asset.id,
            action_type="ticker_change",
            effective_date=date(2024, 6, 20),
        )
        db.add(action)
        db.commit()

        repo = CorporateActionRepository(db)
        results = repo.find_effective_before(date(2024, 6, 15))
        assert len(results) == 0

    def test_find_effective_before_ordered(self, db, test_asset):
        """Returns actions ordered by effective_date."""
        for day in [20, 10, 15]:
            db.add(
                CorporateAction(
                    old_asset_id=test_asset.id,
                    new_asset_id=test_asset.id,
                    action_type="ticker_change",
                    effective_date=date(2024, 6, day),
                )
            )
        db.commit()

        repo = CorporateActionRepository(db)
        results = repo.find_effective_before_ordered(date(2024, 6, 25))
        assert len(results) == 3
        assert results[0].effective_date == date(2024, 6, 10)
        assert results[1].effective_date == date(2024, 6, 15)
        assert results[2].effective_date == date(2024, 6, 20)

    def test_find_effective_before_empty(self, db):
        """Returns empty when no actions exist."""
        repo = CorporateActionRepository(db)
        results = repo.find_effective_before(date(2024, 6, 15))
        assert len(results) == 0
