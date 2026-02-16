"""Tests for _compute_cost_basis_by_currency helper."""

from decimal import Decimal

from app.services.brokers.ibkr.models import IBKRPosition
from app.services.brokers.ibkr.synthetic_import_service import _compute_cost_basis_by_currency

AAPL = IBKRPosition(
    symbol="AAPL",
    original_symbol="AAPL",
    description="Apple",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="NASDAQ",
    quantity=Decimal("100"),
    cost_basis=Decimal("15000"),
    currency="USD",
    account_id="U1",
    needs_validation=False,
)
MSFT = IBKRPosition(
    symbol="MSFT",
    original_symbol="MSFT",
    description="Microsoft",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="NASDAQ",
    quantity=Decimal("50"),
    cost_basis=Decimal("20000"),
    currency="USD",
    account_id="U1",
    needs_validation=False,
)
BMW = IBKRPosition(
    symbol="BMW.DE",
    original_symbol="BMW",
    description="BMW",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="IBIS",
    quantity=Decimal("10"),
    cost_basis=Decimal("5000"),
    currency="EUR",
    account_id="U1",
    needs_validation=False,
)
ZERO_POS = IBKRPosition(
    symbol="CLOSED",
    original_symbol="CLOSED",
    description="Closed",
    asset_category="STK",
    asset_class="Stock",
    listing_exchange="NASDAQ",
    quantity=Decimal("0"),
    cost_basis=Decimal("0"),
    currency="USD",
    account_id="U1",
    needs_validation=False,
)


class TestComputeCostBasisByCurrency:
    def test_single_currency(self):
        result = _compute_cost_basis_by_currency([AAPL, MSFT])
        assert result == {"USD": Decimal("35000")}

    def test_multi_currency(self):
        result = _compute_cost_basis_by_currency([AAPL, BMW])
        assert result == {"USD": Decimal("15000"), "EUR": Decimal("5000")}

    def test_skips_zero_quantity(self):
        result = _compute_cost_basis_by_currency([AAPL, ZERO_POS])
        assert result == {"USD": Decimal("15000")}

    def test_empty_positions(self):
        result = _compute_cost_basis_by_currency([])
        assert result == {}

    def test_uses_absolute_cost_basis(self):
        """Short positions have negative cost basis; we need abs()."""
        short = IBKRPosition(
            symbol="TSLA",
            original_symbol="TSLA",
            description="Tesla",
            asset_category="STK",
            asset_class="Stock",
            listing_exchange="NASDAQ",
            quantity=Decimal("-10"),
            cost_basis=Decimal("-5000"),
            currency="USD",
            account_id="U1",
            needs_validation=False,
        )
        result = _compute_cost_basis_by_currency([short])
        assert result == {"USD": Decimal("5000")}
