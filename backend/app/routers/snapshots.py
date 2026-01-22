"""Snapshots API router - historical portfolio snapshots."""

from datetime import date
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.services.currency_conversion_helper import CurrencyConversionHelper
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.snapshot_service import SnapshotService

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("/create")
async def create_snapshot(
    background_tasks: BackgroundTasks,
    snapshot_date: date | None = None,
    run_async: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a portfolio snapshot for user's accounts.

    Args:
        snapshot_date: Date for the snapshot (defaults to today)
        run_async: If True, run snapshot in background

    Returns:
        Snapshot creation statistics
    """
    allowed_account_ids = get_user_account_ids(current_user, db)
    if not allowed_account_ids:
        return {"status": "completed", "message": "No accounts to snapshot", "stats": {}}

    if run_async:
        # Run in background (pass account IDs for filtering)
        background_tasks.add_task(
            SnapshotService.create_portfolio_snapshot, db, snapshot_date, None, allowed_account_ids
        )
        return {
            "status": "started",
            "message": "Snapshot creation started in background",
            "date": snapshot_date.isoformat() if snapshot_date else date.today().isoformat(),
        }
    else:
        # Run synchronously
        stats = SnapshotService.create_portfolio_snapshot(
            db, snapshot_date, None, allowed_account_ids
        )
        return {"status": "completed", "message": "Snapshot created successfully", **stats}


@router.get("/account/{account_id}")
async def get_account_snapshots(
    account_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 90,
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Get historical snapshots for a specific account (must belong to user).

    Args:
        account_id: The account ID
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots (default: 90)
        display_currency: Currency code for displaying values (default: USD)

    Returns:
        List of historical snapshots
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    snapshots = SnapshotService.get_account_history(db, account_id, start_date, end_date, limit)

    # Convert to display currency
    converted_snapshots = [
        CurrencyConversionHelper.convert_snapshot_dict(db, snapshot, display_currency)
        for snapshot in snapshots
    ]

    return converted_snapshots


@router.get("/portfolio")
async def get_portfolio_snapshots(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 90,
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Get aggregated portfolio snapshots across user's accounts.

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots (default: 90)
        display_currency: Currency code for displaying values (default: USD)
        portfolio_id: Filter by specific portfolio (must belong to user)

    Returns:
        List of aggregated portfolio snapshots
    """
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    snapshots = SnapshotService.get_portfolio_history(
        db, start_date, end_date, limit, allowed_account_ids
    )

    # Convert to display currency
    converted_snapshots = [
        CurrencyConversionHelper.convert_snapshot_dict(db, snapshot, display_currency)
        for snapshot in snapshots
    ]

    return converted_snapshots


@router.get("/validate-reconstruction/{account_id}", response_model=dict[str, Any])
async def validate_reconstruction(
    account_id: int,
    as_of_date: date = Query(default=None, description="Date to validate (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate portfolio reconstruction accuracy (account must belong to user).

    Compares reconstructed holdings (from transaction replay) with actual holdings.
    This is useful for:
    - Ensuring transaction data is complete
    - Verifying FIFO logic is correct
    - Debugging discrepancies

    Args:
        account_id: Account to validate
        as_of_date: Date to reconstruct (defaults to today)
        db: Database session

    Returns:
        Validation results with any discrepancies found
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    validation = PortfolioReconstructionService.validate_reconstruction(db, account_id, as_of_date)

    return validation


@router.get("/portfolio-value/{account_id}", response_model=dict[str, Any])
async def get_portfolio_value(
    account_id: int,
    as_of_date: date = Query(..., description="Date for valuation"),
    currency: str = Query(default="USD", description="Target currency for valuation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate portfolio value for a specific date (account must belong to user).

    This endpoint:
    - Reconstructs holdings as they existed on the target date
    - Fetches prices for that date (or closest available)
    - Calculates total value in the target currency

    Args:
        account_id: Account to value
        as_of_date: Date for valuation
        currency: Target currency (default: USD)
        db: Database session

    Returns:
        Portfolio value breakdown with holdings detail
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    value = PortfolioReconstructionService.calculate_portfolio_value(
        db, account_id, as_of_date, currency
    )

    return value


@router.post("/backfill/{account_id}", response_model=dict[str, Any])
async def backfill_historical_snapshots(
    account_id: int,
    start_date: date = Query(..., description="Start date for backfill"),
    end_date: date = Query(default=None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backfill historical snapshots (account must belong to user).

    This endpoint generates portfolio snapshots for every day between start_date and end_date
    by reconstructing holdings from transaction history. This enables accurate historical
    performance charts even if snapshots weren't being captured at the time.

    WARNING: This can take a while for large date ranges!

    Args:
        account_id: Account to backfill
        start_date: First date to generate snapshots for
        end_date: Last date (defaults to today)
        db: Database session

    Returns:
        Backfill statistics (snapshots created, skipped, errors)
    """
    # Verify account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )
    if not end_date:
        end_date = date.today()

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date"
        )

    # Calculate date range
    total_days = (end_date - start_date).days + 1

    if total_days > 730:  # ~2 years max
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range too large ({total_days} days). Maximum is 730 days (2 years).",
        )

    # Execute backfill using reconstruction
    try:
        stats = SnapshotService.backfill_historical_snapshots(db, account_id, start_date, end_date)

        return {"status": "completed", "message": "Backfill completed successfully", **stats}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Backfill failed: {str(e)}"
        )
