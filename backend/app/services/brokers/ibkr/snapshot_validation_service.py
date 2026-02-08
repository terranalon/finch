"""Validate reconstructed holdings against original IBKR snapshot data.

After a user uploads historical transaction files to replace synthetic snapshot
data, this module compares the reconstructed holdings against the original
snapshot positions to verify that the historical data is complete and accurate.

Tolerance rules:
- Quantity: exact match required
- Cost basis: 2% tolerance (IBKR rounding and fee allocation differences)
- Missing positions: flagged as discrepancy (invalidates result)
- Extra zero-quantity positions: acceptable (closed positions from history)
"""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

COST_BASIS_TOLERANCE = Decimal("0.02")  # 2% tolerance
INVALIDATING_TYPES = {"missing_position", "quantity_mismatch"}


def validate_against_snapshot(
    snapshot_positions: list[dict],
    reconstructed_holdings: list[dict],
) -> dict:
    """Compare reconstructed holdings against the original snapshot.

    Args:
        snapshot_positions: Original positions from synthetic import.
            Each dict has string values:
            [{"symbol": "AAPL", "quantity": "100", "cost_basis": "15000", "currency": "USD"}]
        reconstructed_holdings: Holdings from reconstruction.
            Each dict has Decimal values:
            [{"symbol": "AAPL", "quantity": Decimal("100"), "cost_basis": Decimal("15000")}]

    Returns:
        Validation result dictionary with keys:
        - is_valid: True if no missing_position or quantity_mismatch discrepancies
        - discrepancies: list of discrepancy dicts
        - positions_checked: number of non-zero snapshot positions examined
        - positions_matched: number of positions that passed validation
    """
    discrepancies: list[dict] = []

    # Build lookup from reconstructed holdings, skipping zero-quantity entries
    recon_map: dict[str, dict] = {
        h["symbol"]: h
        for h in reconstructed_holdings
        if h.get("quantity", Decimal("0")) != Decimal("0")
    }

    # Count non-zero snapshot positions for stats
    active_snapshot_positions = [
        s for s in snapshot_positions if Decimal(s["quantity"]) != Decimal("0")
    ]

    for snap in active_snapshot_positions:
        symbol = snap["symbol"]
        snap_qty = Decimal(snap["quantity"])
        snap_cost = Decimal(snap["cost_basis"])

        recon = recon_map.get(symbol)

        if recon is None:
            discrepancies.append(
                {
                    "type": "missing_position",
                    "symbol": symbol,
                    "expected_quantity": str(snap_qty),
                    "actual_quantity": "0",
                    "message": (
                        f"{symbol}: position missing from reconstructed holdings "
                        f"(expected {snap_qty} shares). Likely missing historical files."
                    ),
                }
            )
            continue

        recon_qty = recon["quantity"]
        recon_cost = recon["cost_basis"]

        # Quantity must match exactly
        if recon_qty != snap_qty:
            discrepancies.append(
                {
                    "type": "quantity_mismatch",
                    "symbol": symbol,
                    "expected_quantity": str(snap_qty),
                    "actual_quantity": str(recon_qty),
                    "message": (
                        f"{symbol}: expected {snap_qty} shares, "
                        f"reconstructed {recon_qty}. Likely missing historical files."
                    ),
                }
            )
            continue

        # Cost basis comparison -- skip if snapshot cost is zero
        if snap_cost != Decimal("0"):
            diff_ratio = abs(recon_cost - snap_cost) / abs(snap_cost)
            if diff_ratio > COST_BASIS_TOLERANCE:
                discrepancies.append(
                    {
                        "type": "cost_basis_mismatch",
                        "symbol": symbol,
                        "expected_cost_basis": str(snap_cost),
                        "actual_cost_basis": str(recon_cost),
                        "diff_percent": str(round(diff_ratio * 100, 2)),
                        "message": (
                            f"{symbol}: cost basis differs by "
                            f"{round(diff_ratio * 100, 1)}% "
                            f"(expected {snap_cost}, got {recon_cost})."
                        ),
                    }
                )

    invalidating_count = sum(1 for d in discrepancies if d["type"] in INVALIDATING_TYPES)

    positions_checked = len(active_snapshot_positions)

    return {
        "is_valid": invalidating_count == 0,
        "discrepancies": discrepancies,
        "positions_checked": positions_checked,
        "positions_matched": positions_checked - invalidating_count,
    }
