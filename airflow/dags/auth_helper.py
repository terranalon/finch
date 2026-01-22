"""JWT authentication helper for Airflow service account.

Manages token lifecycle for service-to-service authentication with the backend API.
"""

import logging
import os
from datetime import UTC, datetime, timedelta

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv("/opt/airflow/backend/.env")

# Token refresh buffer (refresh 5 minutes before expiry)
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)
# Token validity assumption (backend issues 30-min tokens, we assume 25 for safety)
TOKEN_VALIDITY = timedelta(minutes=25)


class ServiceAuthHelper:
    """Manages JWT authentication for Airflow service account."""

    def __init__(self) -> None:
        self.backend_url = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")
        self.email = os.getenv("AIRFLOW_SERVICE_EMAIL", "airflow-service@system.internal")
        self.password = os.getenv("AIRFLOW_SERVICE_PASSWORD", "")
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    def get_auth_headers(self) -> dict[str, str]:
        """Get Authorization header, refreshing token if needed."""
        if self._needs_refresh():
            self._login()
        return {"Authorization": f"Bearer {self._access_token}"}

    def force_refresh(self) -> None:
        """Force a token refresh."""
        self._login()

    def _needs_refresh(self) -> bool:
        """Check if token needs refresh (expired or expiring soon)."""
        if not self._access_token or not self._token_expiry:
            return True
        return datetime.now(UTC) >= self._token_expiry - TOKEN_REFRESH_BUFFER

    def _login(self) -> None:
        """Authenticate and store new access token."""
        if not self.password:
            raise ValueError(
                "AIRFLOW_SERVICE_PASSWORD not set. "
                "Please configure service account credentials in airflow/.env"
            )

        logger.info("Authenticating service account: %s", self.email)

        response = requests.post(
            f"{self.backend_url}/api/auth/login",
            json={"email": self.email, "password": self.password},
            timeout=30,
        )

        if response.status_code != 200:
            error_detail = response.json().get("detail", response.text)
            logger.error("Service account authentication failed: %s", error_detail)
            raise RuntimeError(f"Authentication failed: {error_detail}")

        data = response.json()
        self._access_token = data["access_token"]
        self._token_expiry = datetime.now(UTC) + TOKEN_VALIDITY

        logger.info("Service account authenticated successfully")


# Singleton instance for reuse across tasks within the same worker
_auth_helper: ServiceAuthHelper | None = None


def get_auth_helper() -> ServiceAuthHelper:
    """Get or create the singleton auth helper instance."""
    global _auth_helper
    if _auth_helper is None:
        _auth_helper = ServiceAuthHelper()
    return _auth_helper
