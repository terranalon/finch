"""Tests for AssetMetricsService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.models import Asset
from app.services.asset_metrics_service import AssetMetricsService


class TestUpsertDailyMetrics:
    """Tests for AssetMetricsService.upsert_daily_metrics."""

    def test_executes_upsert_statement(self):
        db = MagicMock()
        AssetMetricsService.upsert_daily_metrics(
            db,
            asset_id=1,
            target_date=date(2026, 2, 18),
            open=Decimal("174.00"),
            high=Decimal("176.80"),
            low=Decimal("173.50"),
            close=Decimal("175.50"),
            volume=58700000,
            market_cap=Decimal("2700000000000"),
            pe_ratio=Decimal("28.5"),
            source="Yahoo Finance",
        )
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_handles_all_none_optional_fields(self):
        """Should still execute upsert when all optional fields are None."""
        db = MagicMock()
        AssetMetricsService.upsert_daily_metrics(
            db,
            asset_id=1,
            target_date=date(2026, 2, 18),
            source="Yahoo Finance",
        )
        db.execute.assert_called_once()

    def test_crypto_fields(self):
        """Should handle crypto-specific fields."""
        db = MagicMock()
        AssetMetricsService.upsert_daily_metrics(
            db,
            asset_id=42,
            target_date=date(2026, 2, 18),
            high=Decimal("98200"),
            low=Decimal("96800"),
            close=Decimal("97500"),
            volume=35000000000,
            market_cap=Decimal("1930000000000"),
            circulating_supply=Decimal("19800000"),
            market_cap_rank=1,
            source="CoinGecko",
        )
        db.execute.assert_called_once()


class TestUpdateSlowChangingFields:
    """Tests for AssetMetricsService.update_slow_changing_fields."""

    def _make_asset(self, **overrides: object) -> Asset:
        asset = MagicMock(spec=Asset)
        asset.symbol = "AAPL"
        for field in (
            "description",
            "exchange",
            "website",
            "ceo",
            "employees",
            "beta",
            "avg_volume",
            "earnings_date",
            "ex_dividend_date",
            "target_est",
            "week_52_high",
            "week_52_low",
            "peg_ratio",
            "expense_ratio",
            "fund_family",
            "nav",
            "max_supply",
            "ath",
            "ath_date",
            "atl",
            "atl_date",
        ):
            setattr(asset, field, None)
        for k, v in overrides.items():
            setattr(asset, k, v)
        return asset

    def test_updates_changed_fields(self) -> None:
        asset = self._make_asset(beta=Decimal("1.20"))
        db = MagicMock()
        changed = AssetMetricsService.update_slow_changing_fields(
            db, asset, beta=Decimal("1.24"), website="https://apple.com"
        )
        assert changed is True
        assert asset.beta == Decimal("1.24")
        assert asset.website == "https://apple.com"

    def test_no_change_returns_false(self) -> None:
        asset = self._make_asset(beta=Decimal("1.24"))
        db = MagicMock()
        changed = AssetMetricsService.update_slow_changing_fields(db, asset, beta=Decimal("1.24"))
        assert changed is False
        db.commit.assert_not_called()

    def test_skips_none_values(self) -> None:
        """Should not overwrite existing values with None."""
        asset = self._make_asset(beta=Decimal("1.24"))
        db = MagicMock()
        changed = AssetMetricsService.update_slow_changing_fields(db, asset, beta=None)
        assert changed is False
        assert asset.beta == Decimal("1.24")

    def test_commits_when_changed(self) -> None:
        asset = self._make_asset()
        db = MagicMock()
        AssetMetricsService.update_slow_changing_fields(db, asset, description="New description")
        db.commit.assert_called_once()

    def test_sets_none_to_value(self) -> None:
        """Should set a field from None to a real value."""
        asset = self._make_asset(ceo=None)
        db = MagicMock()
        changed = AssetMetricsService.update_slow_changing_fields(db, asset, ceo="Tim Cook")
        assert changed is True
        assert asset.ceo == "Tim Cook"

    def test_ignores_unknown_fields(self) -> None:
        """Should not crash on fields not in _SLOW_CHANGING_FIELDS."""
        asset = self._make_asset()
        db = MagicMock()
        changed = AssetMetricsService.update_slow_changing_fields(db, asset, unknown_field="value")
        assert changed is False
