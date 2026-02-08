"""Tests for snapshot validation service.

Validates that validate_against_snapshot() correctly compares reconstructed
holdings against original IBKR snapshot data with appropriate tolerances:
- Quantity: exact match required
- Cost basis: 2% tolerance
- Missing positions: flagged as discrepancy
- Extra zero-quantity positions: acceptable (closed positions)
"""

from decimal import Decimal

from app.services.brokers.ibkr.snapshot_validation_service import validate_against_snapshot


class TestSnapshotValidationPerfectMatch:
    """Cases where reconstructed holdings match the snapshot exactly."""

    def test_single_position_perfect_match(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0
        assert result["positions_checked"] == 1
        assert result["positions_matched"] == 1

    def test_multiple_positions_perfect_match(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
            {
                "symbol": "MSFT",
                "quantity": "50",
                "cost_basis": "20000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
            {
                "symbol": "MSFT",
                "quantity": Decimal("50"),
                "cost_basis": Decimal("20000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0
        assert result["positions_checked"] == 2
        assert result["positions_matched"] == 2


class TestSnapshotValidationMissingPositions:
    """Cases where reconstructed holdings are missing positions from the snapshot."""

    def test_missing_single_position(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
            {
                "symbol": "MSFT",
                "quantity": "50",
                "cost_basis": "20000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        assert len(result["discrepancies"]) == 1
        discrepancy = result["discrepancies"][0]
        assert discrepancy["type"] == "missing_position"
        assert discrepancy["symbol"] == "MSFT"
        assert discrepancy["expected_quantity"] == "50"
        assert discrepancy["actual_quantity"] == "0"

    def test_all_positions_missing(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
            {
                "symbol": "MSFT",
                "quantity": "50",
                "cost_basis": "20000",
                "currency": "USD",
            },
        ]
        reconstructed = []

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        assert len(result["discrepancies"]) == 2
        assert all(d["type"] == "missing_position" for d in result["discrepancies"])
        assert result["positions_checked"] == 2
        assert result["positions_matched"] == 0


class TestSnapshotValidationQuantityMismatch:
    """Cases where quantity does not match exactly."""

    def test_quantity_mismatch_fewer_shares(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("85"),
                "cost_basis": Decimal("12750"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        discrepancy = result["discrepancies"][0]
        assert discrepancy["type"] == "quantity_mismatch"
        assert discrepancy["symbol"] == "AAPL"
        assert discrepancy["expected_quantity"] == "100"
        assert discrepancy["actual_quantity"] == "85"

    def test_quantity_mismatch_more_shares(self):
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("120"),
                "cost_basis": Decimal("18000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        discrepancy = result["discrepancies"][0]
        assert discrepancy["type"] == "quantity_mismatch"
        assert discrepancy["expected_quantity"] == "100"
        assert discrepancy["actual_quantity"] == "120"

    def test_fractional_quantity_exact_match(self):
        """Fractional shares should also require exact match."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "10.5",
                "cost_basis": "1575",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("10.5"),
                "cost_basis": Decimal("1575"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0


class TestSnapshotValidationCostBasisTolerance:
    """Cases testing the 2% cost basis tolerance."""

    def test_cost_basis_within_tolerance_1_percent(self):
        """1% difference should be tolerated (under 2% threshold)."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("14850"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0

    def test_cost_basis_at_exact_tolerance_boundary(self):
        """Exactly 2% difference should be tolerated (<=)."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "10000",
                "currency": "USD",
            },
        ]
        # Exactly 2% difference: 10000 * 0.02 = 200 -> 9800
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("9800"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True

    def test_cost_basis_exceeds_tolerance(self):
        """More than 2% difference should generate a cost_basis_mismatch."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        # 5% difference: 15000 * 0.05 = 750 -> 14250
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("14250"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        # cost_basis_mismatch alone does NOT make is_valid False
        # (only missing_position and quantity_mismatch invalidate)
        assert any(d["type"] == "cost_basis_mismatch" for d in result["discrepancies"])
        discrepancy = result["discrepancies"][0]
        assert discrepancy["symbol"] == "AAPL"
        assert discrepancy["expected_cost_basis"] == "15000"
        assert discrepancy["actual_cost_basis"] == "14250"
        assert "diff_percent" in discrepancy

    def test_cost_basis_higher_than_snapshot(self):
        """Cost basis can also be higher than snapshot."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        # 5% higher
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15750"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert any(d["type"] == "cost_basis_mismatch" for d in result["discrepancies"])

    def test_cost_basis_mismatch_does_not_invalidate(self):
        """Cost basis mismatch alone should not set is_valid to False."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        # 10% difference in cost basis
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("13500"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 1
        assert result["discrepancies"][0]["type"] == "cost_basis_mismatch"


class TestSnapshotValidationExtraPositions:
    """Extra positions in reconstructed data (closed positions) are acceptable."""

    def test_extra_zero_quantity_position_is_acceptable(self):
        """Positions closed between snapshot and history upload are fine."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
            {
                "symbol": "TSLA",
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0

    def test_multiple_extra_zero_quantity_positions(self):
        """Multiple closed positions should all be fine."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
            {
                "symbol": "TSLA",
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
            },
            {
                "symbol": "GOOG",
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
            },
            {
                "symbol": "META",
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True


class TestSnapshotValidationEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_snapshot_and_reconstructed(self):
        """Both empty should be valid."""
        result = validate_against_snapshot([], [])
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0
        assert result["positions_checked"] == 0
        assert result["positions_matched"] == 0

    def test_empty_snapshot_with_reconstructed_zero_positions(self):
        """Reconstructed zero-quantity positions with empty snapshot should be valid."""
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
            },
        ]

        result = validate_against_snapshot([], reconstructed)
        assert result["is_valid"] is True

    def test_zero_quantity_snapshot_position_is_skipped(self):
        """Snapshot positions with zero quantity should be skipped."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "0",
                "cost_basis": "0",
                "currency": "USD",
            },
            {
                "symbol": "MSFT",
                "quantity": "50",
                "cost_basis": "20000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "MSFT",
                "quantity": Decimal("50"),
                "cost_basis": Decimal("20000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert result["positions_checked"] == 1
        assert result["positions_matched"] == 1

    def test_zero_cost_basis_in_snapshot_skips_cost_check(self):
        """When snapshot has zero cost basis, should not trigger cost_basis_mismatch."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "0",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        # No cost basis discrepancy because snapshot cost is zero
        assert not any(d["type"] == "cost_basis_mismatch" for d in result["discrepancies"])

    def test_negative_quantity_in_snapshot(self):
        """Negative quantity (short position) should still compare correctly."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "-50",
                "cost_basis": "-7500",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("-50"),
                "cost_basis": Decimal("-7500"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0

    def test_message_field_present_in_discrepancy(self):
        """Each discrepancy should include a human-readable message."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
        ]
        reconstructed = []

        result = validate_against_snapshot(snapshot, reconstructed)
        assert len(result["discrepancies"]) == 1
        assert "message" in result["discrepancies"][0]
        assert "AAPL" in result["discrepancies"][0]["message"]

    def test_combined_discrepancies_quantity_and_missing(self):
        """Multiple types of discrepancies across positions."""
        snapshot = [
            {
                "symbol": "AAPL",
                "quantity": "100",
                "cost_basis": "15000",
                "currency": "USD",
            },
            {
                "symbol": "MSFT",
                "quantity": "50",
                "cost_basis": "20000",
                "currency": "USD",
            },
            {
                "symbol": "GOOG",
                "quantity": "25",
                "cost_basis": "40000",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "AAPL",
                "quantity": Decimal("100"),
                "cost_basis": Decimal("15000"),
            },
            # MSFT is missing
            {
                "symbol": "GOOG",
                "quantity": Decimal("20"),
                "cost_basis": Decimal("32000"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is False
        assert result["positions_checked"] == 3
        assert result["positions_matched"] == 1  # Only AAPL matches

        types = {d["type"] for d in result["discrepancies"]}
        assert "missing_position" in types
        assert "quantity_mismatch" in types

    def test_snapshot_quantity_as_string_decimal(self):
        """Snapshot quantities come as strings and should be converted properly."""
        snapshot = [
            {
                "symbol": "BTC",
                "quantity": "1.23456789",
                "cost_basis": "50000.50",
                "currency": "USD",
            },
        ]
        reconstructed = [
            {
                "symbol": "BTC",
                "quantity": Decimal("1.23456789"),
                "cost_basis": Decimal("50000.50"),
            },
        ]

        result = validate_against_snapshot(snapshot, reconstructed)
        assert result["is_valid"] is True
        assert len(result["discrepancies"]) == 0
