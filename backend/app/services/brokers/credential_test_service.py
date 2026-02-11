"""Broker credential testing service.

Validates broker API credentials by calling the external broker API.
"""

import logging
from typing import Any

from app.services.brokers.broker_config import BrokerConfig, CredentialType
from app.services.brokers.ibkr.flex_client import IBKRFlexClient

logger = logging.getLogger(__name__)


def test_credentials(config: BrokerConfig, cred_field1: str, cred_field2: str) -> dict[str, Any]:
    """Test credentials by calling the broker API.

    For FLEX_QUERY brokers (cred_field1=flex_token, cred_field2=flex_query_id),
    initiates a Flex Query request.
    For API_KEY_SECRET brokers (cred_field1=api_key, cred_field2=api_secret),
    fetches account balances.

    Returns a result dict with 'status' ('success'/'failed') and broker-specific fields.
    """
    if config.credential_type == CredentialType.FLEX_QUERY:
        reference_code = IBKRFlexClient.request_flex_query(cred_field1, cred_field2)
        if reference_code:
            return {
                "status": "success",
                "message": f"{config.name} credentials are valid",
                "reference_code": reference_code,
            }
        return {
            "status": "failed",
            "message": f"{config.name} credential test failed: invalid token or query ID",
        }

    client = config.create_client(cred_field1, cred_field2)
    balance_method = getattr(client, config.balance_method)
    balances = balance_method()

    return {
        "status": "success",
        "message": f"{config.name} credentials are valid",
        "balances": {k: str(v) for k, v in balances.items()},
        "assets_count": len(balances),
    }
