"""Tests for position schemas."""


from app.schemas.position import PositionAccountDetail, PositionResponse


class TestPositionAccountDetail:
    """Tests for PositionAccountDetail schema."""

    def test_minimal_fields(self):
        """Create with only required fields."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=10.0,
            cost_basis_native=1400.0,
            cost_basis=1400.0,
        )
        assert account_detail.holding_id == 1
        assert account_detail.account_id == 1
        assert account_detail.account_name == "Test Account"
        assert account_detail.quantity == 10.0
        assert account_detail.cost_basis_native == 1400.0
        assert account_detail.cost_basis == 1400.0

    def test_all_fields(self):
        """Create with all fields populated."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            account_type="brokerage",
            institution="Test Broker",
            quantity=10.0,
            cost_basis_native=1400.0,
            market_value_native=1500.0,
            pnl_native=100.0,
            cost_basis=1400.0,
            market_value=1500.0,
            pnl=100.0,
            pnl_pct=7.14,
            strategy_horizon="LongTerm",
        )
        assert account_detail.account_type == "brokerage"
        assert account_detail.institution == "Test Broker"
        assert account_detail.market_value_native == 1500.0
        assert account_detail.pnl_native == 100.0
        assert account_detail.market_value == 1500.0
        assert account_detail.pnl == 100.0
        assert account_detail.pnl_pct == 7.14
        assert account_detail.strategy_horizon == "LongTerm"

    def test_optional_fields_default_to_none(self):
        """Optional fields default to None when not provided."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=10.0,
            cost_basis_native=1400.0,
            cost_basis=1400.0,
        )
        assert account_detail.account_type is None
        assert account_detail.institution is None
        assert account_detail.market_value_native is None
        assert account_detail.pnl_native is None
        assert account_detail.market_value is None
        assert account_detail.pnl is None
        assert account_detail.pnl_pct is None
        assert account_detail.strategy_horizon is None

    def test_serialization(self):
        """Schema serializes correctly to dict."""
        account_detail = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=10.0,
            cost_basis_native=1400.0,
            cost_basis=1400.0,
            pnl=100.0,
        )
        data = account_detail.model_dump()
        assert data["holding_id"] == 1
        assert data["account_name"] == "Test Account"
        assert data["pnl"] == 100.0
        assert "cost_basis_native" in data


class TestPositionResponse:
    """Tests for PositionResponse schema."""

    def test_minimal_fields(self):
        """Create with only required fields."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
        )
        assert position.asset_id == 1
        assert position.symbol == "AAPL"
        assert position.total_quantity == 10.0
        assert position.total_cost_basis_native == 1400.0
        assert position.total_cost_basis == 1400.0

    def test_all_fields(self):
        """Create with all fields populated."""
        account = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Test Account",
            quantity=10.0,
            cost_basis_native=1400.0,
            cost_basis=1400.0,
        )
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="Equity",
            category="Technology",
            industry="Consumer Electronics",
            currency="USD",
            is_favorite=True,
            current_price=150.0,
            current_price_display=150.0,
            previous_close_price=148.0,
            day_change=2.0,
            day_change_pct=1.35,
            day_change_date="2026-02-03",
            is_market_closed=False,
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_market_value_native=1500.0,
            total_pnl_native=100.0,
            avg_cost_per_unit_native=140.0,
            total_cost_basis=1400.0,
            total_market_value=1500.0,
            current_value=1500.0,
            total_pnl=100.0,
            total_pnl_pct=7.14,
            avg_cost_per_unit=140.0,
            display_currency="USD",
            account_count=1,
            accounts=[account],
        )
        assert position.name == "Apple Inc."
        assert position.asset_class == "Equity"
        assert position.category == "Technology"
        assert position.industry == "Consumer Electronics"
        assert position.is_favorite is True
        assert position.current_price == 150.0
        assert position.day_change == 2.0
        assert position.day_change_pct == 1.35
        assert position.total_market_value == 1500.0
        assert position.total_pnl == 100.0
        assert position.total_pnl_pct == 7.14
        assert position.account_count == 1
        assert len(position.accounts) == 1

    def test_default_values(self):
        """Default values are set correctly."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
        )
        assert position.name is None
        assert position.asset_class is None
        assert position.currency == "USD"
        assert position.is_favorite is False
        assert position.is_market_closed is False
        assert position.avg_cost_per_unit_native == 0
        assert position.avg_cost_per_unit == 0
        assert position.display_currency == "USD"
        assert position.account_count == 0
        assert position.accounts == []

    def test_with_multiple_accounts(self):
        """Position with holdings from multiple accounts."""
        account1 = PositionAccountDetail(
            holding_id=1,
            account_id=1,
            account_name="Account A",
            quantity=5.0,
            cost_basis_native=700.0,
            cost_basis=700.0,
        )
        account2 = PositionAccountDetail(
            holding_id=2,
            account_id=2,
            account_name="Account B",
            quantity=5.0,
            cost_basis_native=700.0,
            cost_basis=700.0,
        )
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
            account_count=2,
            accounts=[account1, account2],
        )
        assert position.account_count == 2
        assert len(position.accounts) == 2
        assert position.accounts[0].account_name == "Account A"
        assert position.accounts[1].account_name == "Account B"

    def test_serialization(self):
        """Schema serializes correctly to dict."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            name="Apple Inc.",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
            total_pnl=100.0,
            accounts=[],
        )
        data = position.model_dump()
        assert data["asset_id"] == 1
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc."
        assert data["total_pnl"] == 100.0
        assert "accounts" in data
        assert isinstance(data["accounts"], list)

    def test_current_value_alias(self):
        """current_value is an alias for total_market_value."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
            total_market_value=1500.0,
            current_value=1500.0,
        )
        assert position.current_value == 1500.0
        assert position.total_market_value == 1500.0

    def test_pnl_calculations_nullable(self):
        """P&L fields can be null when price data unavailable."""
        position = PositionResponse(
            asset_id=1,
            symbol="AAPL",
            total_quantity=10.0,
            total_cost_basis_native=1400.0,
            total_cost_basis=1400.0,
            total_market_value=None,
            total_pnl=None,
            total_pnl_pct=None,
        )
        assert position.total_market_value is None
        assert position.total_pnl is None
        assert position.total_pnl_pct is None
