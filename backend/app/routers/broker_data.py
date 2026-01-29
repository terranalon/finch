"""Broker data management API router.

Provides endpoints for:
- Uploading historical broker data files
- Viewing data coverage and gaps
- Deleting data sources
- Listing supported brokers
"""

import logging
from datetime import date
from decimal import Decimal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import BrokerDataSource
from app.models.daily_cash_balance import DailyCashBalance
from app.models.historical_snapshot import HistoricalSnapshot
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.broker_file_storage import get_file_storage
from app.services.broker_overlap_detector import get_overlap_detector
from app.services.broker_parser_registry import BrokerParserRegistry
from app.services.import_service_registry import BrokerImportServiceRegistry
from app.services.portfolio_reconstruction_service import PortfolioReconstructionService
from app.services.snapshot_service import generate_snapshots_background, update_snapshot_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/broker-data", tags=["broker-data"])


def _validate_account_access(account_id: int, current_user: User, db: Session) -> None:
    """Verify account belongs to user, raise 404 if not."""
    allowed_account_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


def _validate_broker_type(broker_type: str) -> None:
    """Validate broker type is supported, raise 400 if not."""
    if not BrokerParserRegistry.is_supported(broker_type):
        supported = BrokerParserRegistry.get_supported_broker_types()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported broker type '{broker_type}'. Supported: {supported}",
        )


def _get_parser_for_file(broker_type: str, filename: str):
    """Get parser for file, raise 400 on error."""
    try:
        return BrokerParserRegistry.get_parser_for_file(broker_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Response Models


class BrokerSourceResponse(BaseModel):
    """Response model for a data source."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_identifier: str
    start_date: date
    end_date: date
    status: str
    stats: dict | None
    transaction_count: int | None = None  # Count of linked transactions


class GapResponse(BaseModel):
    """Response model for a coverage gap."""

    start_date: date
    end_date: date
    days: int


class BrokerCoverageResponse(BaseModel):
    """Response model for broker coverage."""

    has_data: bool
    sources: list[BrokerSourceResponse]
    coverage: dict | None  # start_date, end_date, total_days
    gaps: list[GapResponse]
    totals: dict  # sources, transactions


class CoverageResponse(BaseModel):
    """Response model for all broker coverage."""

    brokers: dict[str, BrokerCoverageResponse]


class SupportedBrokerResponse(BaseModel):
    """Response model for supported broker info."""

    type: str
    name: str
    supported_formats: list[str]
    has_api: bool
    api_enabled: bool


class UploadResponse(BaseModel):
    """Response model for successful upload."""

    status: str
    message: str
    source_id: int
    date_range: dict  # start_date, end_date
    stats: dict  # transactions, etc.


class ConflictResponse(BaseModel):
    """Response model for overlap conflict."""

    error: str
    broker_type: str
    message: str
    conflicting_source: dict


class OverlapWarning(BaseModel):
    """Response model for overlap warning details."""

    overlap_type: str  # 'none', 'partial', 'full_contains', 'subset'
    affected_sources: list[dict]  # List of overlapping source info
    affected_transaction_count: int
    sources_to_delete: list[dict]  # Sources fully contained (can be auto-deleted)
    message: str


class PreImportAnalysis(BaseModel):
    """Response model for pre-import file analysis."""

    file_valid: bool
    date_range: dict  # start_date, end_date
    overlap_warning: OverlapWarning | None
    requires_confirmation: bool


class DetailedImportResult(BaseModel):
    """Response model for import with ownership transfer details."""

    status: str
    message: str
    source_id: int
    date_range: dict
    stats: dict
    breakdown: dict  # new, transferred, skipped counts
    old_sources_affected: list[int]  # Sources that had transactions transferred


# Endpoints


@router.post("/upload/{account_id}/analyze", response_model=PreImportAnalysis)
async def analyze_upload(
    account_id: int,
    broker_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreImportAnalysis:
    """Analyze a broker file before import to detect overlaps.

    Does NOT modify the database - only validates and analyzes.

    Args:
        account_id: Account to analyze for
        broker_type: Broker type (e.g., 'ibkr', 'kraken')
        file: Uploaded file to analyze

    Returns:
        Analysis including date range, overlap warnings, and confirmation requirements
    """
    _validate_account_access(account_id, current_user, db)
    _validate_broker_type(broker_type)
    parser = _get_parser_for_file(broker_type, file.filename or "")

    # Read and validate file
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    is_valid, error = parser.validate_file(content, file.filename or "")
    if not is_valid:
        return PreImportAnalysis(
            file_valid=False,
            date_range={},
            overlap_warning=None,
            requires_confirmation=False,
        )

    # Extract date range
    try:
        start_date, end_date = parser.extract_date_range(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not determine date range: {e}",
        )

    # Analyze overlaps
    overlap_detector = get_overlap_detector()
    analysis = overlap_detector.analyze_overlap(db, account_id, broker_type, start_date, end_date)

    overlap_warning = None
    if analysis.overlapping_sources:
        overlap_warning = OverlapWarning(
            overlap_type=analysis.overlap_type,
            affected_sources=[
                {
                    "id": s.id,
                    "identifier": s.source_identifier,
                    "start_date": str(s.start_date),
                    "end_date": str(s.end_date),
                }
                for s in analysis.overlapping_sources
            ],
            affected_transaction_count=analysis.affected_transaction_count,
            sources_to_delete=[
                {"id": s.id, "identifier": s.source_identifier} for s in analysis.sources_to_delete
            ],
            message=analysis.message,
        )

    return PreImportAnalysis(
        file_valid=True,
        date_range={"start_date": str(start_date), "end_date": str(end_date)},
        overlap_warning=overlap_warning,
        requires_confirmation=analysis.requires_confirmation,
    )


@router.post("/upload/{account_id}", response_model=UploadResponse)
async def upload_broker_file(
    account_id: int,
    broker_type: str = Form(...),
    file: UploadFile = File(...),
    confirm_overlap: bool = Form(False),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload a historical broker data file (account must belong to user).

    The file is validated, checked for duplicates and overlaps,
    then imported into the database.

    With confirm_overlap=True, overlapping imports are allowed and transactions
    from previous imports will have their ownership transferred to this new source
    (latest-wins policy).

    Args:
        account_id: Account to import into
        broker_type: Broker type (e.g., 'ibkr', 'binance')
        file: Uploaded file
        confirm_overlap: If True, allow overlapping imports with ownership transfer

    Returns:
        Import statistics and source ID

    Raises:
        400: Invalid file or unsupported broker
        404: Account not found
        409: Date range overlaps with existing source (when confirm_overlap=False)
    """
    _validate_account_access(account_id, current_user, db)
    _validate_broker_type(broker_type)
    parser = _get_parser_for_file(broker_type, file.filename or "")

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    # Validate file can be parsed
    is_valid, error = parser.validate_file(content, file.filename or "")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Check for duplicate file
    file_storage = get_file_storage()
    file_hash = file_storage.calculate_hash(content)
    existing_file = file_storage.check_duplicate(db, file_hash, account_id)
    if existing_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This file was already uploaded on {existing_file.created_at.date()}",
        )

    # Extract date range
    try:
        start_date, end_date = parser.extract_date_range(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not determine date range: {e}",
        )

    # Check for overlaps
    overlap_detector = get_overlap_detector()
    overlap_analysis = overlap_detector.analyze_overlap(
        db, account_id, broker_type, start_date, end_date
    )

    # If there are overlaps and user hasn't confirmed, reject
    if overlap_analysis.overlapping_sources and not confirm_overlap:
        conflicting = overlap_analysis.overlapping_sources[0]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Date range overlap detected",
                "broker_type": broker_type,
                "message": f"Upload covers {start_date} to {end_date}, "
                f"overlaps with existing source '{conflicting.source_identifier}'",
                "conflicting_source": {
                    "id": conflicting.id,
                    "identifier": conflicting.source_identifier,
                    "start_date": str(conflicting.start_date),
                    "end_date": str(conflicting.end_date),
                },
                "hint": "Use confirm_overlap=true to proceed with ownership transfer",
            },
        )

    # Save file to disk
    file_path, file_hash, file_size = file_storage.save_file(
        account_id, broker_type, content, file.filename or "upload"
    )

    # Get file extension
    extension = file_storage.get_extension(file.filename or "")

    # Create pending source record
    source = BrokerDataSource(
        account_id=account_id,
        broker_type=broker_type,
        source_type="file_upload",
        source_identifier=file.filename or "upload",
        start_date=start_date,
        end_date=end_date,
        status="pending",
        file_path=file_path,
        file_hash=file_hash,
        file_format=extension.lstrip(".") if extension else None,
    )
    db.add(source)
    db.flush()

    # Parse and import data
    try:
        # For IBKR, use the existing parser and import service
        if broker_type == "ibkr":
            from app.services.ibkr_import_service import IBKRImportService
            from app.services.ibkr_parser import IBKRParser

            # Parse XML using IBKRParser
            root = IBKRParser.parse_xml(content)
            if root is None:
                raise ValueError("Failed to parse IBKR XML file")

            # Extract data
            positions_data = IBKRParser.extract_positions(root)
            transactions_data = IBKRParser.extract_transactions(root)
            dividends_data = IBKRParser.extract_dividends(root)
            transfers_data = IBKRParser.extract_transfers(root)
            forex_data = IBKRParser.extract_forex_transactions(root)
            cash_data = IBKRParser.extract_cash_balances(root)
            other_cash_data = IBKRParser.extract_other_cash_transactions(root)
            fx_positions = IBKRParser.extract_fx_positions(root)
            stmt_funds_balances = IBKRParser.extract_statement_of_funds_balances(root)

            # Get current position symbols for stale holdings cleanup
            current_symbols = {pos["symbol"] for pos in positions_data}

            # Import all data types
            pos_stats = IBKRImportService._import_positions(db, account_id, positions_data)

            # Mark stale holdings as inactive (positions we had before but not in current data)
            stale_stats = IBKRImportService._mark_stale_holdings_inactive(
                db, account_id, current_symbols
            )

            # Import cash from FxPositions (authoritative source)
            fx_cash_stats = IBKRImportService._import_fx_positions(db, account_id, fx_positions)

            # Import daily cash balances from StmtFunds (for historical reconstruction)
            stmt_funds_stats = IBKRImportService._import_stmt_funds_balances(
                db, account_id, stmt_funds_balances, source.id
            )

            # Also import from CashReport if available (legacy support)
            cash_stats = IBKRImportService._import_cash_balances(db, account_id, cash_data)

            txn_stats = IBKRImportService._import_transactions(
                db, account_id, transactions_data, source.id
            )
            div_stats = IBKRImportService._import_dividends(
                db, account_id, dividends_data, source.id
            )
            transfer_stats = IBKRImportService._import_transfers(
                db, account_id, transfers_data, source.id
            )
            forex_stats = IBKRImportService._import_forex_transactions(
                db, account_id, forex_data, source.id
            )
            other_cash_stats = IBKRImportService._import_other_cash_transactions(
                db, account_id, other_cash_data, source.id
            )
            div_cash_stats = IBKRImportService._import_dividend_cash(
                db, account_id, dividends_data, source.id
            )

            # Run validation against IBKR's authoritative cash positions
            from app.services.ibkr_validation_service import validate_ibkr_import

            validation_result = validate_ibkr_import(
                transactions=transactions_data,
                dividends=dividends_data,
                transfers=transfers_data,
                forex=forex_data,
                other_cash=other_cash_data,
                fx_positions=fx_positions,
            )

            # Log validation warnings
            if not validation_result["is_valid"]:
                for warning in validation_result["warnings"]:
                    logger.warning("IBKR validation: %s", warning)

            source.import_stats = {
                "positions": pos_stats,
                "stale_cleanup": stale_stats,
                "fx_cash": fx_cash_stats,
                "stmt_funds": stmt_funds_stats,
                "cash": cash_stats,
                "transactions": txn_stats,
                "dividends": div_stats,
                "transfers": transfer_stats,
                "forex": forex_stats,
                "other_cash": other_cash_stats,
                "dividend_cash": div_cash_stats,
                "validation": validation_result,
                "total_records": (
                    len(positions_data)
                    + len(transactions_data)
                    + len(dividends_data)
                    + len(transfers_data)
                    + len(forex_data)
                    + len(cash_data)
                    + len(other_cash_data)
                    + len(stmt_funds_balances)
                ),
            }
        elif BrokerImportServiceRegistry.is_supported(broker_type):
            # Use registry for all supported import services (meitav, kraken, bit2c, binance)
            parsed_data = parser.parse(content)
            import_service = BrokerImportServiceRegistry.get_import_service(broker_type, db)
            import_stats = import_service.import_data(account_id, parsed_data, source_id=source.id)

            # Pass through all stats from service (unified structure)
            source.import_stats = {
                **import_stats,
                "total_records": parsed_data.total_records,
            }
        else:
            # For other broker types, use the generic parser (future)
            parsed_data = parser.parse(content)
            source.import_stats = {
                "transactions": len(parsed_data.transactions),
                "positions": len(parsed_data.positions),
                "cash_transactions": len(parsed_data.cash_transactions),
                "dividends": len(parsed_data.dividends),
                "total_records": parsed_data.total_records,
            }

        source.status = "completed"
        db.commit()

        # Trigger background snapshot generation
        if background_tasks:
            # Prefer import service date_range, fall back to parser's date
            snapshot_start = start_date  # from parser (already a date object)
            if isinstance(source.import_stats, dict):
                date_range_stats = source.import_stats.get("date_range", {})
                if date_range_stats.get("start_date"):
                    # Parse ISO string to date object
                    snapshot_start = date.fromisoformat(date_range_stats["start_date"])

            update_snapshot_status(db, account_id, "generating")
            background_tasks.add_task(generate_snapshots_background, account_id, snapshot_start)

        logger.info(
            "Uploaded %s file for account %d: %d records from %s to %s",
            broker_type,
            account_id,
            source.import_stats.get("total_records", 0),
            start_date,
            end_date,
        )

        return UploadResponse(
            status="completed",
            message=f"Successfully imported {source.import_stats.get('total_records', 0)} records",
            source_id=source.id,
            date_range={"start_date": str(start_date), "end_date": str(end_date)},
            stats=source.import_stats or {},
        )

    except Exception as e:
        source.status = "failed"
        source.errors = [str(e)]
        db.commit()
        logger.exception("Failed to import file for account %d: %s", account_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {e}",
        )


@router.get("/coverage/{account_id}", response_model=CoverageResponse)
async def get_data_coverage(
    account_id: int,
    broker_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoverageResponse:
    """Get data coverage information for an account (must belong to user).

    Returns coverage stats per broker type, including:
    - Date ranges covered
    - Number of sources
    - Coverage gaps

    Args:
        account_id: Account to get coverage for
        broker_type: Optional filter by broker type

    Returns:
        Coverage information per broker
    """
    _validate_account_access(account_id, current_user, db)

    overlap_detector = get_overlap_detector()
    result: dict[str, BrokerCoverageResponse] = {}

    # Get broker types to check
    if broker_type:
        broker_types = [broker_type]
    else:
        # Get all broker types that have sources for this account
        broker_types_query = (
            db.query(BrokerDataSource.broker_type)
            .filter(BrokerDataSource.account_id == account_id)
            .distinct()
            .all()
        )
        broker_types = [bt[0] for bt in broker_types_query]

    for bt in broker_types:
        sources = overlap_detector.get_all_sources(db, account_id, bt)
        summary = overlap_detector.get_coverage_summary(db, account_id, bt)

        # Query actual transaction counts linked to each source
        source_ids = [s.id for s in sources]
        tx_counts_query = (
            db.query(Transaction.broker_source_id, func.count(Transaction.id).label("count"))
            .filter(Transaction.broker_source_id.in_(source_ids))
            .group_by(Transaction.broker_source_id)
            .all()
        )
        tx_counts_map = {row.broker_source_id: row.count for row in tx_counts_query}

        # Calculate totals - handle both old format (int) and new format (dict with stats)
        def get_transaction_count(stats: dict | None) -> int:
            if not stats:
                return 0
            txn = stats.get("transactions", 0)
            if isinstance(txn, dict):
                return txn.get("total", 0)
            return txn if isinstance(txn, int) else 0

        total_transactions = sum(
            get_transaction_count(s.import_stats) + (s.import_stats or {}).get("total_records", 0)
            for s in sources
        )

        result[bt] = BrokerCoverageResponse(
            has_data=len(sources) > 0,
            sources=[
                BrokerSourceResponse(
                    id=s.id,
                    source_type=s.source_type,
                    source_identifier=s.source_identifier,
                    start_date=s.start_date,
                    end_date=s.end_date,
                    status=s.status,
                    stats=s.import_stats,
                    transaction_count=tx_counts_map.get(s.id, 0),
                )
                for s in sources
            ],
            coverage={
                "start_date": str(summary.start_date) if summary.start_date else None,
                "end_date": str(summary.end_date) if summary.end_date else None,
                "total_days": summary.total_days,
            }
            if summary.start_date
            else None,
            gaps=[
                GapResponse(start_date=g.start_date, end_date=g.end_date, days=g.days)
                for g in summary.gaps
            ],
            totals={
                "sources": summary.sources_count,
                "transactions": total_transactions,
            },
        )

    return CoverageResponse(brokers=result)


@router.delete("/source/{source_id}")
async def delete_data_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a data source and all associated data (must belong to user's account).

    This performs a CASCADE DELETE:
    - Deletes all transactions linked to this source
    - Deletes all daily cash balances linked to this source
    - Deletes the uploaded file from disk
    - Deletes the source record

    Args:
        source_id: Source ID to delete

    Returns:
        Deletion confirmation with stats on what was deleted
    """
    source = db.query(BrokerDataSource).filter(BrokerDataSource.id == source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    # Verify source's account belongs to user
    allowed_account_ids = get_user_account_ids(current_user, db)
    if source.account_id not in allowed_account_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    source_identifier = source.source_identifier
    account_id = source.account_id

    # CASCADE DELETE: Delete associated transactions first
    transactions_deleted = (
        db.query(Transaction)
        .filter(Transaction.broker_source_id == source_id)
        .delete(synchronize_session=False)
    )

    # CASCADE DELETE: Delete associated daily cash balances
    cash_balances_deleted = (
        db.query(DailyCashBalance)
        .filter(DailyCashBalance.broker_source_id == source_id)
        .delete(synchronize_session=False)
    )

    # Delete file if it exists
    if source.file_path:
        file_storage = get_file_storage()
        file_storage.delete_file(source.file_path)

    # Delete the source record
    db.delete(source)
    db.commit()

    # Recalculate holdings from remaining transactions
    holdings_stats = {"updated": 0, "zeroed": 0}
    if transactions_deleted > 0:
        today = date.today()
        reconstructed = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, today, apply_ticker_changes=False
        )
        reconstructed_map = {h["asset_id"]: h for h in reconstructed}

        # Update all holdings for this account
        holdings = db.query(Holding).filter(Holding.account_id == account_id).all()
        for holding in holdings:
            recon = reconstructed_map.get(holding.asset_id)
            if recon:
                holding.quantity = recon["quantity"]
                holding.cost_basis = recon["cost_basis"]
                holding.is_active = recon["quantity"] != Decimal("0")
                holdings_stats["updated"] += 1
            else:
                # No transactions left for this holding - zero it out
                holding.quantity = Decimal("0")
                holding.cost_basis = Decimal("0")
                holding.is_active = False
                holdings_stats["zeroed"] += 1

        db.commit()

    logger.info(
        "Deleted data source %d (%s): %d transactions, %d cash balances, "
        "%d holdings updated, %d holdings zeroed",
        source_id,
        source_identifier,
        transactions_deleted,
        cash_balances_deleted,
        holdings_stats["updated"],
        holdings_stats["zeroed"],
    )

    # Trigger snapshot regeneration or cleanup
    earliest_txn = (
        db.query(func.min(Transaction.date))
        .filter(
            Transaction.holding_id.in_(
                db.query(Holding.id).filter(Holding.account_id == account_id)
            )
        )
        .scalar()
    )

    if earliest_txn:
        # Transactions remain - regenerate snapshots from earliest date
        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(generate_snapshots_background, account_id, earliest_txn)
    else:
        # No transactions remain - delete all snapshots and clear status
        db.query(HistoricalSnapshot).filter(HistoricalSnapshot.account_id == account_id).delete(
            synchronize_session=False
        )
        update_snapshot_status(db, account_id, None)

    return {
        "status": "deleted",
        "message": f"Deleted data source '{source_identifier}'",
        "source_id": source_id,
        "deleted": {
            "transactions": transactions_deleted,
            "cash_balances": cash_balances_deleted,
        },
        "holdings": holdings_stats,
    }


@router.get("/supported-brokers", response_model=list[SupportedBrokerResponse])
async def get_supported_brokers() -> list[SupportedBrokerResponse]:
    """Get list of supported broker types.

    Returns information about each broker including:
    - Supported file formats
    - Whether API import is available
    """
    brokers = BrokerParserRegistry.get_supported_brokers()
    return [
        SupportedBrokerResponse(
            type=b.type,
            name=b.name,
            supported_formats=b.supported_formats,
            has_api=b.has_api,
            api_enabled=b.api_enabled,
        )
        for b in brokers
    ]
