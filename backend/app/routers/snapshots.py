"""Snapshots API router - historical portfolio snapshots."""

from datetime import date
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.exceptions import NotFoundError
from app.models.user import User
from app.schemas.snapshot import SnapshotCreateResponse, SnapshotPointResponse
from app.services.portfolio.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.portfolio.snapshot_service import SnapshotService
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotCreateResponse)
async def create_snapshot(
    background_tasks: BackgroundTasks,
    snapshot_date: date | None = None,
    run_async: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    svc = SnapshotService(db)
    if run_async:
        background_tasks.add_task(svc.create_portfolio_snapshot, snapshot_date, allowed_account_ids)
        return {
            "status": "started",
            "message": "Snapshot creation started in background",
            "date": snapshot_date.isoformat() if snapshot_date else date.today().isoformat(),
        }

    stats = svc.create_portfolio_snapshot(snapshot_date, allowed_account_ids)
    return {"status": "completed", "message": "Snapshot created successfully", **stats}


@router.get("/account/{account_id}", response_model=list[SnapshotPointResponse])
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
):
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
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise NotFoundError("Account", account_id)

    snapshots = SnapshotService.get_account_history(db, account_id, start_date, end_date, limit)

    return [
        CurrencyConversionHelper.convert_snapshot_dict(db, snapshot, display_currency)
        for snapshot in snapshots
    ]


@router.get("/portfolio", response_model=list[SnapshotPointResponse])
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
):
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

    return [
        CurrencyConversionHelper.convert_snapshot_dict(db, snapshot, display_currency)
        for snapshot in snapshots
    ]


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
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise NotFoundError("Account", account_id)

    return PortfolioReconstructionService.calculate_portfolio_value(
        db, account_id, as_of_date, currency
    )
