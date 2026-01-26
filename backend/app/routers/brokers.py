"""Unified broker import API router.

This module provides a single router for all broker integrations (IBKR, Kraken, Bit2C, etc.)
using a registry pattern to minimize code duplication while supporting broker-specific features.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_broker_credentials, get_user_account
from app.models.account import Account
from app.models.user import User

# Import broker clients and services at module level for testability
from app.services.binance_client import BinanceClient, BinanceCredentials
from app.services.bit2c_client import Bit2CClient, Bit2CCredentials
from app.services.ibkr_flex_client import IBKRFlexClient
from app.services.ibkr_flex_import_service import IBKRFlexImportService
from app.services.import_service_registry import BrokerImportServiceRegistry
from app.services.kraken_client import KrakenClient, KrakenCredentials
from app.services.staged_import_service import StagedImportService

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


router = APIRouter(prefix="/api/brokers", tags=["brokers"])


class BrokerType(str, Enum):
    """Supported broker types."""

    IBKR = "ibkr"
    KRAKEN = "kraken"
    BIT2C = "bit2c"
    BINANCE = "binance"


class CredentialType(str, Enum):
    """Types of credential schemes used by brokers."""

    API_KEY_SECRET = "api_key_secret"  # api_key + api_secret (Kraken, Bit2C)
    FLEX_QUERY = "flex_query"  # flex_token + flex_query_id (IBKR)


# =============================================================================
# Credential Field Helpers
# =============================================================================


def get_credential_fields(credential_type: CredentialType) -> tuple[str, str]:
    """Get the field names for a credential type."""
    if credential_type == CredentialType.API_KEY_SECRET:
        return ("api_key", "api_secret")
    return ("flex_token", "flex_query_id")


def has_credentials(broker_data: dict, credential_type: CredentialType) -> bool:
    """Check if credential fields are present and non-empty."""
    field1, field2 = get_credential_fields(credential_type)
    return bool(broker_data.get(field1) and broker_data.get(field2))


def remove_credential_fields(broker_data: dict, credential_type: CredentialType) -> None:
    """Remove credential fields from broker data dict (in place)."""
    field1, field2 = get_credential_fields(credential_type)
    broker_data.pop(field1, None)
    broker_data.pop(field2, None)
    broker_data.pop("updated_at", None)


def build_credential_data(
    credentials: ApiKeyCredentials | FlexQueryCredentials,
    credential_type: CredentialType,
) -> dict[str, str]:
    """Build credential data dict from Pydantic model."""
    field1, field2 = get_credential_fields(credential_type)
    if credential_type == CredentialType.API_KEY_SECRET:
        values = (credentials.api_key, credentials.api_secret)
    else:
        values = (credentials.flex_token, credentials.flex_query_id)
    return {
        field1: values[0],
        field2: values[1],
        "updated_at": datetime.now().isoformat(),
    }


# =============================================================================
# Broker Configuration
# =============================================================================


@dataclass
class BrokerConfig:
    """Configuration for a broker integration."""

    key: str
    name: str
    credential_type: CredentialType
    supports_staging: bool = False
    env_fallback_prefix: str | None = None  # e.g., "IBKR" for IBKR_FLEX_TOKEN
    # Client factory components (for API_KEY_SECRET brokers)
    client_class: type | None = None
    credentials_class: type | None = None
    balance_method: str = "get_balance"  # Method name to call for balance


# Broker registry - defines all supported brokers
BROKER_REGISTRY: dict[str, BrokerConfig] = {
    BrokerType.IBKR: BrokerConfig(
        key="ibkr",
        name="Interactive Brokers",
        credential_type=CredentialType.FLEX_QUERY,
        supports_staging=True,
        env_fallback_prefix="IBKR",
    ),
    BrokerType.KRAKEN: BrokerConfig(
        key="kraken",
        name="Kraken",
        credential_type=CredentialType.API_KEY_SECRET,
        client_class=KrakenClient,
        credentials_class=KrakenCredentials,
    ),
    BrokerType.BIT2C: BrokerConfig(
        key="bit2c",
        name="Bit2C",
        credential_type=CredentialType.API_KEY_SECRET,
        client_class=Bit2CClient,
        credentials_class=Bit2CCredentials,
    ),
    BrokerType.BINANCE: BrokerConfig(
        key="binance",
        name="Binance",
        credential_type=CredentialType.API_KEY_SECRET,
        client_class=BinanceClient,
        credentials_class=BinanceCredentials,
        balance_method="get_account_balances",
    ),
}


def _get_broker_config(broker_type: str) -> BrokerConfig:
    """Get broker config or raise 404."""
    config = BROKER_REGISTRY.get(broker_type)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown broker type: {broker_type}. "
            f"Supported: {', '.join(BROKER_REGISTRY.keys())}",
        )
    return config


def _get_validated_account(account_id: int, current_user: User, db: Session) -> Account:
    """Get account if it belongs to user, otherwise raise 404."""
    account = get_user_account(current_user, db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )
    return account


def _create_crypto_client(config: BrokerConfig, api_key: str, api_secret: str):
    """Create a crypto broker client using the registry configuration."""
    if not config.client_class or not config.credentials_class:
        raise ValueError(f"Broker {config.key} missing client_class or credentials_class")
    credentials = config.credentials_class(api_key=api_key, api_secret=api_secret)
    return config.client_class(credentials)


def _get_api_key_credentials(
    account: Account, broker_key: str, broker_name: str
) -> tuple[str, str]:
    """Get api_key/api_secret credentials from account metadata."""
    api_key, api_secret = get_broker_credentials(account, broker_key)
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {broker_name} credentials configured. "
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {broker_name} credentials configured. Please either:\n"
            f"1. Use /brokers/{broker_key}/credentials endpoint to set credentials{env_hint}",
        )
    return flex_token, flex_query_id


def _update_last_import(account: Account, broker_key: str, db: Session) -> None:
    """Update last_import timestamp in account metadata."""
    if not account.meta_data:
        account.meta_data = {}
    if broker_key not in account.meta_data:
        account.meta_data[broker_key] = {}
    account.meta_data[broker_key]["last_import"] = datetime.now().isoformat()
    flag_modified(account, "meta_data")
    db.commit()


def _import_crypto_broker(
    account_id: int,
    config: BrokerConfig,
    api_key: str,
    api_secret: str,
    db: Session,
) -> dict[str, Any]:
    """Import data from a crypto broker (Kraken, Bit2C, Binance)."""
    client = _create_crypto_client(config, api_key, api_secret)

    logger.info(f"Fetching {config.name} data for account {account_id}")
    broker_data = client.fetch_all_data()

    import_service = BrokerImportServiceRegistry.get_import_service(config.key, db)
    return import_service.import_data(account_id, broker_data, source_id=None)


def _import_ibkr(
    account_id: int,
    flex_token: str,
    flex_query_id: str,
    use_staging: bool,
    db: Session,
) -> dict[str, Any]:
    """Import data from IBKR using Flex Query API."""
    if use_staging:
        logger.info(f"Using staged import for account {account_id} (UI-responsive mode)")
        return StagedImportService.import_with_staging(db, account_id, flex_token, flex_query_id)

    logger.info(f"Using atomic import for account {account_id}")
    return IBKRFlexImportService.import_all(db, account_id, flex_token, flex_query_id)


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
            for config in BROKER_REGISTRY.values()
        ]
    }


@router.post("/{broker_type}/import/{account_id}", response_model=dict[str, Any])
async def import_broker_data(
    broker_type: BrokerType,
    account_id: int,
    use_staging: bool = Query(
        default=True,
        description="Use staged import for better UI responsiveness (IBKR only)",
    ),
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
            stats = _import_crypto_broker(account_id, config, api_key, api_secret, db)
        elif config.credential_type == CredentialType.FLEX_QUERY:
            flex_token, flex_query_id = _get_flex_query_credentials(
                account, config.key, config.name, config.env_fallback_prefix
            )
            stats = _import_ibkr(account_id, flex_token, flex_query_id, use_staging, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unsupported credential type: {config.credential_type}",
            )

        if stats.get("status") == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{config.name} import failed: {stats.get('errors', ['Unknown error'])}",
            )

        _update_last_import(account, config.key, db)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"{config.name} import failed for account {account_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{config.name} import failed: {str(e)}",
        )


@router.post("/{broker_type}/test-credentials/{account_id}", response_model=dict[str, Any])
async def test_broker_credentials(
    broker_type: BrokerType,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Test broker API credentials without importing data.

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
            # IBKR: Test by initiating a Flex Query request
            flex_token, flex_query_id = _get_flex_query_credentials(
                account, config.key, config.name, config.env_fallback_prefix
            )
            reference_code = IBKRFlexClient.request_flex_query(flex_token, flex_query_id)
            if reference_code:
                return {
                    "status": "success",
                    "message": f"{config.name} credentials are valid",
                    "account_id": account_id,
                    "reference_code": reference_code,
                }
            return {
                "status": "failed",
                "message": f"{config.name} credential test failed: invalid token or query ID",
                "account_id": account_id,
            }

        # Crypto brokers: Test by fetching balances
        api_key, api_secret = _get_api_key_credentials(account, config.key, config.name)
        client = _create_crypto_client(config, api_key, api_secret)
        balance_method = getattr(client, config.balance_method)
        balances = balance_method()

        return {
            "status": "success",
            "message": f"{config.name} credentials are valid",
            "account_id": account_id,
            "balances": {k: str(v) for k, v in balances.items()},
            "assets_count": len(balances),
        }

    except HTTPException:
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
    credentials: ApiKeyCredentials | FlexQueryCredentials = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Store API credentials for a broker.

    This endpoint stores credentials in account metadata for future imports.
    Use test-credentials to validate them, then import to fetch data.

    **For Kraken/Bit2C (api_key_secret):**
    ```json
    {
        "api_key": "your_api_key",
        "api_secret": "your_api_secret"
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
    expected_type = (
        ApiKeyCredentials
        if config.credential_type == CredentialType.API_KEY_SECRET
        else FlexQueryCredentials
    )
    if not isinstance(credentials, expected_type):
        field1, field2 = get_credential_fields(config.credential_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{config.name} requires {field1} and {field2}",
        )

    cred_data = build_credential_data(credentials, config.credential_type)

    # Store credentials in account metadata
    if not account.meta_data:
        account.meta_data = {}

    # Preserve existing broker data (like last_import) while updating credentials
    existing = account.meta_data.get(config.key, {})
    existing.update(cred_data)
    account.meta_data[config.key] = existing
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
