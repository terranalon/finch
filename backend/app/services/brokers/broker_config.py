"""Broker configuration and registry.

Domain objects shared between the broker router and broker services.
"""

from dataclasses import dataclass
from enum import Enum

from app.services.brokers.binance.client import BinanceClient, BinanceCredentials
from app.services.brokers.bit2c.client import Bit2CClient, Bit2CCredentials
from app.services.brokers.kraken.client import KrakenClient, KrakenCredentials


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

    def create_client(self, api_key: str, api_secret: str):
        """Create an authenticated broker API client."""
        if not self.client_class or not self.credentials_class:
            raise ValueError(f"Broker {self.key} missing client_class or credentials_class")
        credentials = self.credentials_class(api_key=api_key, api_secret=api_secret)
        return self.client_class(credentials)


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
