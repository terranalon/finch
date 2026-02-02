#!/usr/bin/env python3
"""Comprehensive validation of reconstruction accuracy vs IBKR holdings."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.portfolio_reconstruction_service import PortfolioReconstructionService

from app.database import SessionLocal
from app.models import Asset, Holding


def main():
    """Validate reconstruction accuracy against current IBKR holdings."""
    db = SessionLocal()
    account_id = 7

    try:
        print("=" * 120)
        print("RECONSTRUCTION VALIDATION REPORT")
        print("=" * 120)
        print()

        # Get current holdings from database (from IBKR)
        print("1. Fetching current IBKR holdings from database...")
        current_holdings = (
            db.query(Holding, Asset)
            .join(Asset)
            .filter(
                Holding.account_id == account_id,
                Holding.is_active == True,
                Asset.asset_class == "Stock",  # Only stocks for now
            )
            .all()
        )

        ibkr_map = {}
        for holding, asset in current_holdings:
            ibkr_map[asset.symbol] = {
                "quantity": holding.quantity,
                "cost_basis": holding.cost_basis,
                "asset_id": asset.id,
            }

        print(f"   Found {len(ibkr_map)} stock holdings in IBKR")
        print()

        # Run reconstruction
        print("2. Running transaction-based reconstruction...")
        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, date.today(), apply_ticker_changes=True
        )

        # Filter to stocks only
        recon_stocks = [h for h in reconstructed if h["asset_class"] == "Stock"]

        recon_map = {}
        for h in recon_stocks:
            recon_map[h["symbol"]] = {
                "quantity": h["quantity"],
                "cost_basis": h["cost_basis"],
                "asset_id": h["asset_id"],
            }

        print(f"   Reconstructed {len(recon_map)} stock holdings")
        print()

        # Compare
        print("3. Comparing holdings...")
        print()

        all_symbols = sorted(set(list(ibkr_map.keys()) + list(recon_map.keys())))

        matches = []
        mismatches = []
        ibkr_only = []
        recon_only = []

        for symbol in all_symbols:
            ibkr_qty = ibkr_map.get(symbol, {}).get("quantity", Decimal("0"))
            recon_qty = recon_map.get(symbol, {}).get("quantity", Decimal("0"))

            if symbol not in ibkr_map:
                recon_only.append({"symbol": symbol, "recon_qty": float(recon_qty)})
            elif symbol not in recon_map:
                ibkr_only.append({"symbol": symbol, "ibkr_qty": float(ibkr_qty)})
            else:
                # Both have it - check if quantities match
                diff = abs(ibkr_qty - recon_qty)
                if diff < Decimal("0.01"):  # Allow tiny floating point differences
                    matches.append({"symbol": symbol, "quantity": float(ibkr_qty)})
                else:
                    mismatches.append(
                        {
                            "symbol": symbol,
                            "ibkr_qty": float(ibkr_qty),
                            "recon_qty": float(recon_qty),
                            "diff": float(diff),
                        }
                    )

        # Print results
        print("=" * 120)
        print("RESULTS")
        print("=" * 120)
        print()

        total_positions = len(all_symbols)
        accuracy = (len(matches) / total_positions * 100) if total_positions > 0 else 0

        print(f"Total Positions:      {total_positions}")
        print(f"Perfect Matches:      {len(matches)} ({len(matches) / total_positions * 100:.1f}%)")
        print(f"Mismatches:           {len(mismatches)}")
        print(f"IBKR Only:            {len(ibkr_only)}")
        print(f"Reconstruction Only:  {len(recon_only)}")
        print()
        print(f"Overall Accuracy:     {accuracy:.1f}%")
        print()

        if matches:
            print("=" * 120)
            print("✅ PERFECT MATCHES")
            print("=" * 120)
            print(f"{'Symbol':12s} | {'Quantity':>15s}")
            print("-" * 120)
            for match in matches:
                print(f"{match['symbol']:12s} | {match['quantity']:>15.8f}")
            print()

        if mismatches:
            print("=" * 120)
            print("❌ MISMATCHES (Quantity Differences)")
            print("=" * 120)
            print(f"{'Symbol':12s} | {'IBKR':>15s} | {'Reconstruction':>15s} | {'Difference':>15s}")
            print("-" * 120)
            for mm in mismatches:
                print(
                    f"{mm['symbol']:12s} | {mm['ibkr_qty']:>15.8f} | {mm['recon_qty']:>15.8f} | {mm['diff']:>15.8f}"
                )
            print()

        if ibkr_only:
            print("=" * 120)
            print("⚠️  IN IBKR BUT NOT IN RECONSTRUCTION")
            print("=" * 120)
            print(f"{'Symbol':12s} | {'IBKR Quantity':>15s}")
            print("-" * 120)
            for item in ibkr_only:
                print(f"{item['symbol']:12s} | {item['ibkr_qty']:>15.8f}")
            print()

        if recon_only:
            print("=" * 120)
            print("⚠️  IN RECONSTRUCTION BUT NOT IN IBKR")
            print("=" * 120)
            print(f"{'Symbol':12s} | {'Reconstructed Quantity':>15s}")
            print("-" * 120)
            for item in recon_only:
                print(f"{item['symbol']:12s} | {item['recon_qty']:>15.8f}")
            print()

        # Final verdict
        print("=" * 120)
        print("VERDICT")
        print("=" * 120)
        if accuracy == 100:
            print("✅ PERFECT! Reconstruction matches IBKR 100%")
        elif accuracy >= 90:
            print(f"✅ EXCELLENT! Reconstruction accuracy: {accuracy:.1f}%")
        elif accuracy >= 75:
            print(f"⚠️  GOOD but needs investigation: {accuracy:.1f}%")
        else:
            print(f"❌ POOR accuracy: {accuracy:.1f}% - needs significant work")
        print("=" * 120)

    finally:
        db.close()


if __name__ == "__main__":
    main()
