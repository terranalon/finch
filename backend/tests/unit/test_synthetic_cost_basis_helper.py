"""Tests for _compute_cost_basis_by_currency helper."""

from decimal import Decimal

from app.services.brokers.ibkr.models import IBKRPosition
from app.services.brokers.ibkr.synthetic_import_service import _compute_cost_basis_by_currency


def _position(
    symbol: str = "SYM",
    quantity: Decimal = Decimal("100"),
    cost_basis: Decimal = Decimal("10000"),
    currency: str = "USD",
) -> IBKRPosition:
    """Build an IBKRPosition with only the fields relevant to cost basis grouping."""
    return IBKRPosition(
        symbol=symbol,
        original_symbol=symbol,
        description=symbol,
        asset_category="STK",
        asset_class="Stock",
        listing_exchange="NASDAQ",
        quantity=quantity,
        cost_basis=cost_basis,
        currency=currency,
        account_id="U1",
        needs_validation=False,
    )


AAPL = _position(symbol="AAPL", quantity=Decimal("100"), cost_basis=Decimal("15000"))
MSFT = _position(symbol="MSFT", quantity=Decimal("50"), cost_basis=Decimal("20000"))
BMW = _position(symbol="BMW.DE", quantity=Decimal("10"), cost_basis=Decimal("5000"), currency="EUR")
ZERO_POS = _position(symbol="CLOSED", quantity=Decimal("0"), cost_basis=Decimal("0"))


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
        short = _position(symbol="TSLA", quantity=Decimal("-10"), cost_basis=Decimal("-5000"))
        result = _compute_cost_basis_by_currency([short])
        assert result == {"USD": Decimal("5000")}
