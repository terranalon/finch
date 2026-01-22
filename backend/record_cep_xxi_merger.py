#!/usr/bin/env python3
"""Record the CEP→XXI SPAC merger as a corporate action."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import and_

from app.database import SessionLocal
from app.models import Asset, CorporateAction


def main():
    """Record CEP→XXI SPAC merger."""
    db = SessionLocal()

    try:
        print("=" * 100)
        print("Recording CEP → XXI SPAC Merger")
        print("=" * 100)
        print()

        # Get assets
        cep = db.query(Asset).filter(Asset.symbol == "CEP").first()
        xxi = db.query(Asset).filter(Asset.symbol == "XXI").first()

        if not cep:
            print("ERROR: CEP asset not found")
            return

        if not xxi:
            print("ERROR: XXI asset not found")
            return

        print(f"CEP Asset ID: {cep.id}")
        print(f"  ISIN: {cep.isin}")
        print(f"  CONID: {cep.conid}")
        print()

        print(f"XXI Asset ID: {xxi.id}")
        print(f"  CUSIP: {xxi.cusip}")
        print(f"  ISIN: {xxi.isin}")
        print(f"  CONID: {xxi.conid}")
        print()

        # Check if already exists
        existing = (
            db.query(CorporateAction)
            .filter(
                and_(
                    CorporateAction.old_asset_id == cep.id,
                    CorporateAction.new_asset_id == xxi.id,
                    CorporateAction.action_type == "SPAC_MERGER",
                )
            )
            .first()
        )

        if existing:
            print("✅ Corporate action already recorded:")
            print(f"   ID: {existing.id}")
            print(f"   Type: {existing.action_type}")
            print(f"   Effective Date: {existing.effective_date}")
            print(f"   Notes: {existing.notes}")
            return

        # Create new record
        print("Creating corporate action record...")
        print()

        action = CorporateAction(
            action_type="SPAC_MERGER",
            old_asset_id=cep.id,
            new_asset_id=xxi.id,
            effective_date=date(2025, 12, 9),
            ratio=1.0,  # 1:1 conversion
            notes=(
                "SPAC Merger: Cantor Equity Partners (CEP) merged with Twenty One Capital "
                "and changed to XXI. New CUSIP: 90138L109. Identifiers changed during merger: "
                f"old ISIN {cep.isin} → new ISIN {xxi.isin}. "
                "Source: OCC Memo #57830, dated December 8, 2025."
            ),
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        print("✅ Successfully recorded corporate action:")
        print(f"   ID: {action.id}")
        print(f"   Type: {action.action_type}")
        print(f"   Old Symbol: CEP (Asset ID: {cep.id})")
        print(f"   New Symbol: XXI (Asset ID: {xxi.id})")
        print(f"   Effective Date: {action.effective_date}")
        print(f"   Ratio: {action.ratio} (1:1 conversion)")
        print()
        print("=" * 100)
        print("IMPACT ON RECONSTRUCTION:")
        print("=" * 100)
        print()
        print("Before: CEP (96) + XXI (100) shown separately")
        print("After:  XXI (196) - CEP merged into XXI")
        print()
        print("This will be automatically applied during reconstruction.")
        print("=" * 100)

    finally:
        db.close()


if __name__ == "__main__":
    main()
