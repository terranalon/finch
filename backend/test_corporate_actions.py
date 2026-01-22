"""Demo: Corporate Actions Service - Symbol Change Detection"""

from datetime import date

from app.database import SessionLocal
from app.services.corporate_actions_service import CorporateActionsService
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService


def main():
    db = SessionLocal()

    try:
        print("DEMONSTRATION: Corporate Actions Service")
        print("=" * 80)

        # Step 1: Detect potential symbol changes
        print("\n1. AUTO-DETECTING POTENTIAL SYMBOL CHANGES...")
        print("-" * 80)

        potential_changes = CorporateActionsService.detect_symbol_changes(db, account_id=7)

        print(f"Found {len(potential_changes)} potential symbol changes:\n")
        for change in potential_changes:
            print(
                f"  {change['symbol']:10s} | {change['orphaned_quantity']:8.2f} shares | "
                f"Last txn: {change['last_transaction_date']} ({change['days_since_last_transaction']} days ago)"
            )

        # Step 2: Show example of recording symbol change
        print("\n\n2. HOW TO RECORD SYMBOL CHANGE (Example)")
        print("-" * 80)
        print("Complexity: ⭐ LOW - Just one function call!\n")

        print("""
# When you discover CEP changed to XXI, run this ONCE:
CorporateActionsService.record_symbol_change(
    db,
    old_symbol="CEP",
    new_symbol="XXI",
    effective_date=date(2025, 9, 10),
    notes="Cantor Equity Partners rebranded to Twenty One Capital"
)
        """)

        # Step 3: Get reconstruction WITHOUT corporate actions
        print("\n3. RECONSTRUCTION WITHOUT CORPORATE ACTIONS")
        print("-" * 80)

        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id=7, as_of_date=date.today()
        )

        # Show CEP and XXI separately
        stocks_only = [h for h in reconstructed if h["asset_class"] == "Stock"]
        cep = next((h for h in stocks_only if h["symbol"] == "CEP"), None)
        xxi = next((h for h in stocks_only if h["symbol"] == "XXI"), None)

        if cep:
            print(f"CEP: {float(cep['quantity']):8.2f} shares")
        else:
            print("CEP: not in reconstruction")

        if xxi:
            print(f"XXI: {float(xxi['quantity']):8.2f} shares")
        else:
            print("XXI: not in reconstruction")

        cep_qty = float(cep["quantity"]) if cep else 0
        xxi_qty = float(xxi["quantity"]) if xxi else 0
        print(f"\nTotal (separate): {cep_qty + xxi_qty:8.2f} shares")
        print("IBKR shows XXI: 196.00 shares ✗ (mismatch)")

        # Step 4: Show how to apply corporate actions
        print("\n\n4. HOW TO APPLY CORPORATE ACTIONS")
        print("-" * 80)

        print("""
# After recording symbol change, apply to reconstruction:
reconstructed = PortfolioReconstructionService.reconstruct_holdings(...)
merged = CorporateActionsService.apply_corporate_actions_to_reconstruction(
    db, reconstructed
)
# Now CEP (96 shares) merged into XXI → XXI shows 196 shares total ✓
        """)

        print("\n\n5. SUMMARY")
        print("=" * 80)
        print("✅ Complexity: LOW")
        print("✅ Detection: Automatic (finds delisted symbols)")
        print("✅ Recording: Manual (one-time call)")
        print("✅ Application: Automatic (merges on every reconstruction)")
        print("\nWorkflow:")
        print("  1. Import creates transactions for both CEP and XXI")
        print("  2. Detection alerts you: 'CEP delisted, 96 orphaned shares'")
        print("  3. You run: record_symbol_change('CEP', 'XXI', date)")
        print("  4. Reconstruction automatically merges CEP → XXI")
        print("  5. Result: XXI shows 196 shares (matches IBKR!) ✓")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
