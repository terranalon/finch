"""Unified broker import API router.

This module provides a single router for all broker integrations (IBKR, Kraken, Bit2C, etc.)
using a registry pattern to minimize code duplication while supporting broker-specific features.
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_broker_credentials, get_user_account
from app.exceptions import AppError, BadRequestError, NotFoundError, UnprocessableEntityError
from app.models.account import Account
from app.models.user import User
from app.rate_limiter import limiter
from app.services.brokers.broker_config import (
    BrokerConfig,
    BrokerType,
    CredentialType,
    get_all_broker_configs,
    get_broker_config,
    get_credential_fields,
    has_credentials,
    remove_credential_fields,
)
from app.services.brokers.credential_test_service import test_credentials
from app.services.brokers.ibkr.flex_import_service import IBKRFlexImportService
from app.services.brokers.ibkr.import_orchestrator import (
    IBKRImportOrchestrator,
    MissingFlexSectionsError,
)
from app.services.brokers.ibkr.synthetic_import_service import IBKRSyntheticImportService
from app.services.brokers.import_service_registry import BrokerImportServiceRegistry
from app.services.portfolio.snapshot_service import (
    generate_snapshots_background,
    update_snapshot_status,
)
from app.services.shared.staged_import_service import StagedImportService

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Credentials
# =============================================================================


class ApiKeyCredentials(BaseModel):
    """Credentials for API key/secret based brokers (Kraken, Bit2C, etc.)."""

    api_key: str
    api_secret: str


class FlexQueryCredentials(BaseModel):
    """Credentials for IBKR Flex Query API."""

    flex_token: str
    flex_query_id: str


class KuCoinApiCredentials(BaseModel):
    """Credentials for KuCoin API (requires passphrase)."""

    api_key: str
    api_secret: str
    api_passphrase: str


class ApiConnectionResponse(BaseModel):
    """Response model for API connection entry."""

    account_id: int
    broker_type: str


class SnapshotImportStats(BaseModel):
    """Statistics from a synthetic snapshot import."""

    account_id: int
    source_type: str
    status: str
    positions_imported: int
    cash_balances: dict[str, Any]
    assets_created: int
    errors: list[str]
    start_time: str | None = None
    end_time: str | None = None
    holdings_reconstruction: dict[str, Any] | None = None


class SnapshotImportResponse(BaseModel):
    """Response model for POST /ibkr/snapshot/{account_id}."""

    status: str
    message: str
    account_id: int
    stats: SnapshotImportStats


class OnboardingImportResponse(BaseModel):
    """Response model for POST /ibkr/onboard/{account_id}."""

    status: str
    message: str
    account_id: int
    import_mode: Literal["full_history", "snapshot"]
    stats: dict[str, Any]


router = APIRouter(prefix="/api/brokers", tags=["brokers"])


def build_credential_data(
    credentials: ApiKeyCredentials | FlexQueryCredentials | KuCoinApiCredentials,
    credential_type: CredentialType,
) -> dict[str, str]:
    """Build credential data dict from Pydantic model."""
    fields = get_credential_fields(credential_type)
    if isinstance(credentials, KuCoinApiCredentials):
        values = {
            "api_key": credentials.api_key,
            "api_secret": credentials.api_secret,
            "api_passphrase": credentials.api_passphrase,
        }
    elif isinstance(credentials, ApiKeyCredentials):
        values = {"api_key": credentials.api_key, "api_secret": credentials.api_secret}
    else:
        values = {"flex_token": credentials.flex_token, "flex_query_id": credentials.flex_query_id}
    return {**{f: values[f] for f in fields}, "updated_at": datetime.now().isoformat()}


def _get_broker_config(broker_type: str) -> BrokerConfig:
    """Get broker config or raise 404."""
    config = get_broker_config(broker_type)
    if not config:
        registry = get_all_broker_configs()
        raise NotFoundError(
            "Broker type",
            f"{broker_type} (supported: {', '.join(registry.keys())})",
        )
    return config


def _get_validated_account(account_id: int, current_user: User, db: Session) -> Account:
    """Get account if it belongs to user, otherwise raise 404."""
    account = get_user_account(current_user, db, account_id)
    if not account:
        raise NotFoundError("Account", account_id)
    return account


def _get_api_key_credentials(
    account: Account, broker_key: str, broker_name: str
) -> tuple[str, str]:
    """Get api_key/api_secret credentials from account metadata."""
    api_key, api_secret = get_broker_credentials(account, broker_key)
    if not api_key or not api_secret:
        raise BadRequestError(
            f"No {broker_name} credentials configured. "
            f"Please add {broker_key}.api_key and {broker_key}.api_secret to account metadata.",
        )
    return api_key, api_secret


def _get_flex_query_credentials(
    account: Account, broker_key: str, broker_name: str, env_prefix: str | None
) -> tuple[str, str]:
    """Get flex_token/flex_query_id credentials from account metadata or env vars."""
    flex_token = None
    flex_query_id = None

    # Try account metadata first
    if account.meta_data and broker_key in account.meta_data:
        creds = account.meta_data[broker_key]
        flex_token = creds.get("flex_token")
        flex_query_id = creds.get("flex_query_id")

    # Fall back to environment variables
    if (not flex_token or not flex_query_id) and env_prefix:
        flex_token = flex_token or os.getenv(f"{env_prefix}_FLEX_TOKEN")
        flex_query_id = flex_query_id or os.getenv(f"{env_prefix}_FLEX_QUERY_ID")

    if not flex_token or not flex_query_id:
        env_hint = ""
        if env_prefix:
            env_hint = (
                f", or\n2. Set {env_prefix}_FLEX_TOKEN and {env_prefix}_FLEX_QUERY_ID in .env file"
            )
        raise BadRequestError(
            f"No {broker_name} credentials configured. Please either:\n"
            f"1. Use /brokers/{broker_key}/credentials endpoint to set credentials{env_hint}",
        )
    return flex_token, flex_query_id


def _update_last_import(account: Account, broker_key: str, db: Session) -> None:
    """Update last_import timestamp in account metadata."""
    meta: dict = account.meta_data or {}
    if broker_key not in meta:
        meta[broker_key] = {}
    meta[broker_key]["last_import"] = datetime.now().isoformat()
    account.meta_data = meta
    flag_modified(account, "meta_data")
    db.commit()


_INCREMENTAL_BUFFER_DAYS = 1


def _get_incremental_start_date(account: Account, broker_key: str) -> date | None:
    """Derive start_date for incremental import from last_import metadata.

    Returns a date 1 day before the last import, or None if no prior import exists.
    The buffer ensures no transactions are missed due to timezone edge cases.
    """
    last_import_str = (account.meta_data or {}).get(broker_key, {}).get("last_import")
    if not last_import_str:
        return None
    last_import_dt = datetime.fromisoformat(last_import_str)
    return (last_import_dt - timedelta(days=_INCREMENTAL_BUFFER_DAYS)).date()


def _get_ibkr_start_date(account: Account, broker_key: str) -> date | None:
    """Get start_date for IBKR incremental import.

    Uses last_import metadata if available, otherwise falls back to
    account.created_at for first-time imports.
    """
    incremental = _get_incremental_start_date(account, broker_key)
    if incremental is not None:
        return incremental
    if account.created_at:
        return account.created_at.date()
    return None


def _import_crypto_broker(
    account_id: int,
    config: BrokerConfig,
    api_key: str,
    api_secret: str,
    db: Session,
    start_date: date | None = None,
    api_passphrase: str | None = None,
) -> dict[str, Any]:
    """Import data from a crypto broker (Kraken, Bit2C, Binance, KuCoin)."""
    client = config.create_client(api_key, api_secret, api_passphrase=api_passphrase)

    mode = f"incremental from {start_date}" if start_date else "full history"
    logger.info(f"Fetching {config.name} data for account {account_id} ({mode})")
    broker_data = client.fetch_all_data(start_date=start_date)

    import_service = BrokerImportServiceRegistry.get_import_service(config.key, db)
    return import_service.import_data(account_id, broker_data, source_id=None)


def _import_ibkr(
    account_id: int,
    flex_token: str,
    flex_query_id: str,
    use_staging: bool,
    db: Session,
    start_date: date | None = None,
) -> dict[str, Any]:
    """Import data from IBKR using Flex Query API."""
    if use_staging:
        logger.info(f"Using staged import for account {account_id} (UI-responsive mode)")
        return StagedImportService.import_with_staging(
            db, account_id, flex_token, flex_query_id, start_date=start_date
        )

    logger.info(f"Using atomic import for account {account_id}")
    return IBKRFlexImportService.import_all(
        db, account_id, flex_token, flex_query_id, start_date=start_date
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=dict[str, Any])
async def list_brokers() -> dict[str, Any]:
    """List all supported brokers and their capabilities."""
    return {
        "brokers": [
            {
                "key": config.key,
                "name": config.name,
                "credential_type": config.credential_type.value,
                "supports_staging": config.supports_staging,
            }
            for config in get_all_broker_configs().values()
        ]
    }


@router.get("/api-connections", response_model=list[ApiConnectionResponse])
async def get_api_connections(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApiConnectionResponse]:
    """Get all accounts with broker API credentials configured.

    Returns account-broker pairs for all active accounts that have valid
    API credentials configured. Used by Airflow for automated imports.

    For service accounts: Returns all active accounts.
    For regular users: Returns only accounts in their portfolios.

    Returns:
        List of {account_id, broker_type} for accounts with API credentials.
    """
    from app.dependencies.user_scope import get_user_account_ids

    # Service accounts (Airflow) can see all accounts
    if user.is_service_account:
        accounts = (
            db.query(Account)
            .filter(
                Account.is_active == True,  # noqa: E712
                Account.meta_data.isnot(None),
            )
            .all()
        )
    else:
        # Regular users only see their own accounts
        allowed_account_ids = get_user_account_ids(user, db)
        if not allowed_account_ids:
            return []
        accounts = (
            db.query(Account)
            .filter(
                Account.id.in_(allowed_account_ids),
                Account.is_active == True,  # noqa: E712
                Account.meta_data.isnot(None),
            )
            .all()
        )

    results = []
    for account in accounts:
        if not account.meta_data:
            continue
        for broker_type, config in get_all_broker_configs().items():
            broker_data = account.meta_data.get(broker_type, {})
            if has_credentials(broker_data, config.credential_type):
                results.append(
                    ApiConnectionResponse(
                        account_id=account.id,
                        broker_type=broker_type,
                    )
                )

    return results


@router.post("/{broker_type}/import/{account_id}", response_model=dict[str, Any])
async def import_broker_data(
    broker_type: BrokerType,
    account_id: int,
    use_staging: bool = Query(
        default=True,
        description="Use staged import for better UI responsiveness (IBKR only)",
    ),
    full_import: bool = Query(
        default=False,
        description="Force full history import, ignoring last_import timestamp",
    ),
    background_tasks: BackgroundTasks = None,  # ty: ignore[invalid-parameter-default] — FastAPI injects BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Import data from a broker using stored credentials.

    This endpoint retrieves credentials from account metadata and imports
    all available data from the broker.

    For IBKR, credentials can also be stored in environment variables as fallback:
    - IBKR_FLEX_TOKEN
    - IBKR_FLEX_QUERY_ID

    Args:
        broker_type: The broker to import from (ibkr, kraken, bit2c)
        account_id: Account ID to import into (must belong to user)
        use_staging: Use staged import for IBKR (default: True, ignored for other brokers)

    Returns:
        Import statistics including status and counts
    """
    config = _get_broker_config(broker_type)
    account = _get_validated_account(account_id, current_user, db)

    try:
        if config.credential_type == CredentialType.API_KEY_SECRET:
            api_key, api_secret = _get_api_key_credentials(account, config.key, config.name)
            start_date = None if full_import else _get_incremental_start_date(account, config.key)
            stats = _import_crypto_broker(
                account_id, config, api_key, api_secret, db, start_date=start_date
            )
        elif config.credential_type == CredentialType.API_KEY_SECRET_PASSPHRASE:
            from app.dependencies.user_scope import get_broker_credentials_with_passphrase

            api_key, api_secret, api_passphrase = get_broker_credentials_with_passphrase(
                account, config.key
            )
            if not api_key or not api_secret or not api_passphrase:
                raise BadRequestError(
                    f"No {config.name} credentials configured. "
                    f"Please add {config.key}.api_key, {config.key}.api_secret, "
                    f"and {config.key}.api_passphrase to account metadata.",
                )
            start_date = None if full_import else _get_incremental_start_date(account, config.key)
            stats = _import_crypto_broker(
                account_id,
                config,
                api_key,
                api_secret,
                db,
                start_date=start_date,
                api_passphrase=api_passphrase,
            )
        elif config.credential_type == CredentialType.FLEX_QUERY:
            flex_token, flex_query_id = _get_flex_query_credentials(
                account, config.key, config.name, config.env_fallback_prefix
            )
            start_date = None if full_import else _get_ibkr_start_date(account, config.key)
            stats = _import_ibkr(
                account_id, flex_token, flex_query_id, use_staging, db, start_date=start_date
            )
        else:
            raise AppError(f"Unsupported credential type: {config.credential_type}")

        if stats.get("status") == "failed":
            raise AppError(
                f"{config.name} import failed: {stats.get('errors', ['Unknown error'])}",
            )

        _update_last_import(account, config.key, db)

        # Trigger background snapshot generation if date_range available
        if background_tasks and stats.get("date_range"):
            date_range = stats["date_range"]
            start_date_str = date_range.get("start_date")
            if start_date_str:
                # Parse ISO string to date object
                start_date = date.fromisoformat(start_date_str)
                update_snapshot_status(db, account_id, "generating")
                background_tasks.add_task(generate_snapshots_background, account_id, start_date)

        logger.info(f"{config.name} import completed for account {account_id}: {stats}")

        response = {
            "status": "completed",
            "message": f"{config.name} import completed for account {account.name}",
            "account_id": account_id,
            "account_name": account.name,
            "stats": stats,
        }

        # Add IBKR-specific response fields
        if config.credential_type == CredentialType.FLEX_QUERY:
            response["import_method"] = "staged" if use_staging else "atomic"
            response["credential_source"] = (
                "account_metadata"
                if account.meta_data and config.key in account.meta_data
                else "environment"
            )

        return response

    except AppError:
        raise
    except Exception as e:
        logger.exception(f"{config.name} import failed for account {account_id}")
        raise AppError(f"{config.name} import failed: {str(e)}")


@router.post("/ibkr/onboard/{account_id}", response_model=OnboardingImportResponse)
async def onboard_ibkr(
    account_id: int,
    background_tasks: BackgroundTasks = None,  # ty: ignore[invalid-parameter-default] -- FastAPI injects BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingImportResponse:
    """IBKR onboarding import: validates Flex Query sections, then imports based on account age.

    For accounts younger than 365 days, fetches full transaction history.
    For older accounts, creates a synthetic snapshot of current positions.

    Returns 422 if the Flex Query is missing required sections, with a list
    of missing section names for the frontend to display.
    """
    config = _get_broker_config(BrokerType.IBKR)
    account = _get_validated_account(account_id, current_user, db)

    flex_token, flex_query_id = _get_flex_query_credentials(
        account, config.key, config.name, config.env_fallback_prefix
    )

    try:
        result = IBKRImportOrchestrator.execute(db, account_id, flex_token, flex_query_id)
    except MissingFlexSectionsError as e:
        raise UnprocessableEntityError(
            "Your Flex Query is missing required sections. Please update it in IBKR and try again.",
            extra={
                "error_code": "MISSING_FLEX_SECTIONS",
                "missing_sections": e.missing_sections,
                "required_sections": e.required_sections,
            },
        )
    except RuntimeError as e:
        raise AppError(str(e))

    _update_last_import(account, config.key, db)

    if background_tasks:
        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(generate_snapshots_background, account_id, result.snapshot_start)

    if result.import_mode == "full_history":
        message = f"Full transaction history imported for account {account.name}"
    else:
        message = f"Synthetic snapshot created for account {account.name}"

    return OnboardingImportResponse(
        status="completed",
        message=message,
        account_id=account_id,
        import_mode=result.import_mode,
        stats=result.stats,
    )


@router.post("/kucoin/onboard/{account_id}", response_model=OnboardingImportResponse)
async def onboard_kucoin(
    account_id: int,
    background_tasks: BackgroundTasks = None,  # ty: ignore[invalid-parameter-default] -- FastAPI injects BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingImportResponse:
    """KuCoin onboarding import: probes API history, then imports based on coverage.

    For accounts with < 6 months of fill history, fetches full transaction history.
    For older accounts where the fill history is truncated, creates a synthetic snapshot
    of current positions. The user can then upload CSV files for full historical data.
    """
    from app.dependencies.user_scope import get_broker_credentials_with_passphrase
    from app.services.brokers.kucoin.import_orchestrator import KuCoinImportOrchestrator

    config = _get_broker_config(BrokerType.KUCOIN)
    account = _get_validated_account(account_id, current_user, db)

    api_key, api_secret, api_passphrase = get_broker_credentials_with_passphrase(
        account, config.key
    )
    if not api_key or not api_secret or not api_passphrase:
        raise BadRequestError(
            f"No {config.name} credentials configured. "
            f"Please add {config.key}.api_key, {config.key}.api_secret, "
            f"and {config.key}.api_passphrase to account metadata.",
        )

    client = config.create_client(api_key, api_secret, api_passphrase=api_passphrase)

    try:
        result = KuCoinImportOrchestrator.execute(db, account_id, client)
    except AppError:
        raise
    except Exception as e:
        logger.exception("KuCoin onboarding failed for account %d", account_id)
        raise AppError(f"KuCoin onboarding failed: {e}")

    if result.stats.get("status") == "failed":
        raise AppError(
            f"KuCoin import failed: {result.stats.get('errors', ['Unknown error'])}",
        )

    _update_last_import(account, config.key, db)

    if background_tasks:
        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(generate_snapshots_background, account_id, result.snapshot_start)

    if result.import_mode == "full_history":
        message = f"Full transaction history imported for account {account.name}"
    else:
        message = (
            f"Synthetic snapshot created for account {account.name}. "
            f"Upload CSV files from KuCoin for full historical data."
        )

    return OnboardingImportResponse(
        status="completed",
        message=message,
        account_id=account_id,
        import_mode=result.import_mode,
        stats=result.stats,
    )


@router.post("/ibkr/snapshot/{account_id}", response_model=SnapshotImportResponse)
async def import_ibkr_snapshot(
    account_id: int,
    background_tasks: BackgroundTasks = None,  # ty: ignore[invalid-parameter-default] — FastAPI injects BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a synthetic snapshot from current IBKR positions.

    This fetches the user's current IBKR positions and cash balances,
    then creates synthetic transactions representing the current state.
    Use this for instant onboarding -- the user can upload full history later.

    The synthetic data is automatically replaced when historical files are uploaded.

    Args:
        account_id: Account with stored IBKR credentials

    Returns:
        Snapshot import statistics
    """
    config = _get_broker_config(BrokerType.IBKR)
    account = _get_validated_account(account_id, current_user, db)

    flex_token, flex_query_id = _get_flex_query_credentials(
        account, config.key, config.name, config.env_fallback_prefix
    )

    stats = IBKRSyntheticImportService.import_snapshot(db, account_id, flex_token, flex_query_id)

    if stats.get("status") == "failed":
        raise AppError(
            f"Snapshot import failed: {stats.get('errors', ['Unknown error'])}",
        )

    _update_last_import(account, config.key, db)

    # Trigger background snapshot generation
    if background_tasks:
        update_snapshot_status(db, account_id, "generating")
        background_tasks.add_task(generate_snapshots_background, account_id, date.today())

    return {
        "status": "completed",
        "message": f"Synthetic snapshot created for account {account.name}",
        "account_id": account_id,
        "stats": stats,
    }


@router.post("/{broker_type}/test-credentials", response_model=dict[str, Any])
@limiter.limit("10/minute")
async def test_credentials_stateless(
    request: Request,
    broker_type: BrokerType,
    credentials: ApiKeyCredentials | FlexQueryCredentials | KuCoinApiCredentials = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test broker API credentials without requiring an account.

    Accepts credentials directly in the request body and validates them
    against the broker API. Used during account creation wizard before
    the account is persisted.
    """
    config = _get_broker_config(broker_type)

    try:
        if isinstance(credentials, KuCoinApiCredentials):
            return test_credentials(
                config,
                credentials.api_key,
                credentials.api_secret,
                api_passphrase=credentials.api_passphrase,
            )
        fields = get_credential_fields(config.credential_type)
        return test_credentials(
            config, getattr(credentials, fields[0]), getattr(credentials, fields[1])
        )
    except AppError:
        raise
    except Exception:
        logger.exception(f"{config.name} stateless credential test failed")
        return {
            "status": "failed",
            "message": f"{config.name} credential test failed. Check your credentials and try again.",
        }


@router.post("/{broker_type}/test-credentials/{account_id}", response_model=dict[str, Any])
async def test_broker_credentials(
    broker_type: BrokerType,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test broker API credentials without importing data.

    For crypto brokers (Kraken, Bit2C, Binance), returns account balances.
    For IBKR, validates the Flex Query credentials by initiating a request.

    Args:
        broker_type: The broker to test credentials for
        account_id: Account ID with stored credentials

    Returns:
        Credential test result with balance information (crypto) or validation status (IBKR)
    """
    config = _get_broker_config(broker_type)
    account = _get_validated_account(account_id, current_user, db)

    try:
        if config.credential_type == CredentialType.FLEX_QUERY:
            cred1, cred2 = _get_flex_query_credentials(
                account, config.key, config.name, config.env_fallback_prefix
            )
            result = test_credentials(config, cred1, cred2)
        elif config.credential_type == CredentialType.API_KEY_SECRET_PASSPHRASE:
            from app.dependencies.user_scope import get_broker_credentials_with_passphrase

            api_key, api_secret, api_passphrase = get_broker_credentials_with_passphrase(
                account, config.key
            )
            if not api_key or not api_secret or not api_passphrase:
                raise BadRequestError(f"No {config.name} credentials configured.")
            result = test_credentials(config, api_key, api_secret, api_passphrase=api_passphrase)
        else:
            cred1, cred2 = _get_api_key_credentials(account, config.key, config.name)
            result = test_credentials(config, cred1, cred2)

        result["account_id"] = account_id
        return result

    except AppError:
        raise
    except Exception as e:
        logger.error(f"{config.name} credential test failed for account {account_id}: {e}")
        return {
            "status": "failed",
            "message": f"{config.name} credential test failed: {str(e)}",
            "account_id": account_id,
        }


# =============================================================================
# Credential Management Endpoints
# =============================================================================


@router.put("/{broker_type}/credentials/{account_id}", response_model=dict[str, Any])
async def set_broker_credentials(
    broker_type: BrokerType,
    account_id: int,
    credentials: ApiKeyCredentials | FlexQueryCredentials | KuCoinApiCredentials = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Store API credentials for a broker.

    This endpoint stores credentials in account metadata for future imports.
    Use test-credentials to validate them, then import to fetch data.

    **For Kraken/Bit2C/Binance (api_key_secret):**
    ```json
    {
        "api_key": "your_api_key",
        "api_secret": "your_api_secret"
    }
    ```

    **For KuCoin (api_key_secret_passphrase):**
    ```json
    {
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "api_passphrase": "your_api_passphrase"
    }
    ```

    **For IBKR (flex_query):**
    ```json
    {
        "flex_token": "your_flex_token",
        "flex_query_id": "your_query_id"
    }
    ```

    Args:
        broker_type: The broker to store credentials for
        account_id: Account ID to associate credentials with
        credentials: Credential object (varies by broker type)

    Returns:
        Confirmation of credential storage
    """
    config = _get_broker_config(broker_type)
    account = _get_validated_account(account_id, current_user, db)

    # Validate credential type matches expected model
    if config.credential_type == CredentialType.API_KEY_SECRET_PASSPHRASE:
        expected_type = KuCoinApiCredentials
    elif config.credential_type == CredentialType.API_KEY_SECRET:
        expected_type = ApiKeyCredentials
    else:
        expected_type = FlexQueryCredentials

    if not isinstance(credentials, expected_type):
        fields = get_credential_fields(config.credential_type)
        raise BadRequestError(f"{config.name} requires {', '.join(fields)}")

    cred_data = build_credential_data(credentials, config.credential_type)

    # Store credentials in account metadata
    meta: dict = account.meta_data or {}

    # Preserve existing broker data (like last_import) while updating credentials
    existing = meta.get(config.key, {})
    existing.update(cred_data)
    meta[config.key] = existing
    account.meta_data = meta
    flag_modified(account, "meta_data")
    db.commit()

    logger.info(f"Credentials stored for {config.name} account {account_id}")

    return {
        "status": "stored",
        "message": f"{config.name} credentials stored for account {account.name}",
        "broker": config.key,
        "account_id": account_id,
        "account_name": account.name,
    }


@router.get("/{broker_type}/credentials/{account_id}", response_model=dict[str, Any])
async def get_broker_credentials_status(
    broker_type: BrokerType,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check if credentials are configured for a broker (does not expose secrets).

    Returns:
        Credential status including whether configured and last update time
    """
    config = _get_broker_config(broker_type)
    account = _get_validated_account(account_id, current_user, db)

    # Check if credentials exist
    credentials_configured = False
    updated_at = None
    last_import = None

    if account.meta_data and config.key in account.meta_data:
        broker_data = account.meta_data[config.key]
        credentials_configured = has_credentials(broker_data, config.credential_type)
        updated_at = broker_data.get("updated_at")
        last_import = broker_data.get("last_import")

    return {
        "broker": config.key,
        "broker_name": config.name,
        "account_id": account_id,
        "account_name": account.name,
        "has_credentials": credentials_configured,
        "credential_type": config.credential_type.value,
        "updated_at": updated_at,
        "last_import": last_import,
    }


@router.delete("/{broker_type}/credentials/{account_id}", response_model=dict[str, Any])
async def delete_broker_credentials(
    broker_type: BrokerType,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Remove stored credentials for a broker.

    This removes the credential fields but preserves other metadata like last_import.

    Returns:
        Confirmation of credential deletion
    """
    config = _get_broker_config(broker_type)
    account = _get_validated_account(account_id, current_user, db)

    # Check if broker data exists
    if not account.meta_data or config.key not in account.meta_data:
        return {
            "status": "not_found",
            "message": f"No {config.name} credentials found for account {account.name}",
            "broker": config.key,
            "account_id": account_id,
        }

    # Remove credential fields but preserve other data (like last_import)
    broker_data = account.meta_data[config.key]
    remove_credential_fields(broker_data, config.credential_type)

    # If no data left, remove the broker key entirely
    if not broker_data:
        del account.meta_data[config.key]

    flag_modified(account, "meta_data")
    db.commit()
    logger.info(f"Credentials removed for {config.name} account {account_id}")

    return {
        "status": "deleted",
        "message": f"{config.name} credentials removed from account {account.name}",
        "broker": config.key,
        "account_id": account_id,
    }
