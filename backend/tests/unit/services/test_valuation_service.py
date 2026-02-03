"""Tests for PortfolioValuationService."""

from decimal import Decimal

from app.models import Asset, Holding
from app.services.portfolio.valuation_service import PortfolioValuationService


class TestValuationService:
    """Test PortfolioValuationService."""

    def test_calculate_holding_value_equity(self, db, test_holding, test_asset, test_account):
        """Calculate value for equity holding."""
        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(test_holding, test_asset, test_account)

        assert value.quantity == Decimal("10.0")
        assert value.cost_basis_native == Decimal("1400.00")
        # Market value = 10 * 150 = 1500
        assert value.market_value_native == Decimal("1500.00")
        # P&L = 1500 - 1400 = 100
        assert value.pnl_native == Decimal("100.00")
        # P&L % = 100 / 1400 * 100 = 7.14...
        assert value.pnl_pct is not None
        assert float(value.pnl_pct) > 7

    def test_calculate_holding_value_cash(self, db, test_account):
        """Cash holdings have value equal to quantity."""
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class="Cash",
            currency="USD",
        )
        db.add(cash_asset)
        db.flush()

        cash_holding = Holding(
            account_id=test_account.id,
            asset_id=cash_asset.id,
            quantity=Decimal("1000.00"),
            cost_basis=Decimal("1000.00"),
            is_active=True,
        )
        db.add(cash_holding)
        db.commit()

        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(cash_holding, cash_asset, test_account)

        # Cash value = quantity
        assert value.market_value_native == Decimal("1000.00")

    def test_calculate_holding_value_negative_cash(self, db, test_account):
        """Negative cash (liability) has zero market value."""
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class="Cash",
            currency="USD",
        )
        db.add(cash_asset)
        db.flush()

        cash_holding = Holding(
            account_id=test_account.id,
            asset_id=cash_asset.id,
            quantity=Decimal("-500.00"),
            cost_basis=Decimal("0.00"),
            is_active=True,
        )
        db.add(cash_holding)
        db.commit()

        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(cash_holding, cash_asset, test_account)

        # Negative cash returns zero market value
        assert value.market_value_native == Decimal("0")

    def test_calculate_holding_value_no_price(self, db, test_account):
        """Holding with no price returns None for market value."""
        asset = Asset(
            symbol="TEST",
            name="Test Asset",
            asset_class="Equity",
            currency="USD",
            last_fetched_price=None,
        )
        db.add(asset)
        db.flush()

        holding = Holding(
            account_id=test_account.id,
            asset_id=asset.id,
            quantity=Decimal("10.0"),
            cost_basis=Decimal("100.00"),
            is_active=True,
        )
        db.add(holding)
        db.commit()

        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(holding, asset, test_account)

        assert value.market_value_native is None
        assert value.pnl_native is None

    def test_calculate_holding_value_currency_conversion(self, db, test_account):
        """Values are converted to display currency."""
        # Create ILS asset
        asset = Asset(
            symbol="TEVA.TA",
            name="Teva",
            asset_class="Equity",
            currency="ILS",
            last_fetched_price=Decimal("50.00"),
        )
        db.add(asset)
        db.flush()

        holding = Holding(
            account_id=test_account.id,
            asset_id=asset.id,
            quantity=Decimal("100.0"),
            cost_basis=Decimal("4500.00"),  # in ILS
            is_active=True,
        )
        db.add(holding)
        db.commit()

        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(
            holding, asset, test_account, display_currency="USD"
        )

        # Native values should be in ILS
        assert value.cost_basis_native == Decimal("4500.00")
        assert value.market_value_native == Decimal("5000.00")  # 100 * 50

    def test_calculate_day_change_cash(self, db):
        """Cash has no day change."""
        cash_asset = Asset(
            symbol="USD",
            name="US Dollar",
            asset_class="Cash",
            currency="USD",
        )
        db.add(cash_asset)
        db.commit()

        service = PortfolioValuationService(db)
        result = service.calculate_day_change(cash_asset, None)

        assert result.day_change is None
        assert result.is_market_closed is False

    def test_service_initialization(self, db):
        """Service initializes correctly."""
        service = PortfolioValuationService(db)
        assert service._db == db
        assert service._price_repo is None  # Lazy loaded

    def test_price_repo_lazy_loading(self, db):
        """Price repo is lazy loaded on first access."""
        service = PortfolioValuationService(db)
        assert service._price_repo is None

        # Access the property
        repo = service.price_repo
        assert repo is not None
        assert service._price_repo is not None

        # Second access returns same instance
        assert service.price_repo is repo

    def test_holding_value_account_metadata(self, db, test_holding, test_asset, test_account):
        """HoldingValue includes account metadata."""
        service = PortfolioValuationService(db)
        value = service.calculate_holding_value(test_holding, test_asset, test_account)

        assert value.account_id == test_account.id
        assert value.account_name == test_account.name
        assert value.account_type == test_account.account_type
        assert value.institution == test_account.institution
