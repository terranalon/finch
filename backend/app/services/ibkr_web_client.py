"""IBKR Client Portal Web API client."""

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class IBKRWebClient:
    """Client for IBKR Client Portal Web API."""

    def __init__(self, base_url: str = "https://host.docker.internal:5000/v1/api"):
        """
        Initialize IBKR Web API client.

        Args:
            base_url: Base URL for IB Gateway (default: https://host.docker.internal:5000/v1/api)
        """
        self.base_url = base_url
        self.session = requests.Session()
        # Disable SSL verification for localhost
        self.session.verify = False

    def check_auth_status(self) -> bool:
        """
        Check if authenticated to IB Gateway.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            url = f"{self.base_url}/iserver/auth/status"
            response = self.session.post(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            authenticated = data.get("authenticated", False)
            connected = data.get("connected", False)

            logger.info(f"Auth status: authenticated={authenticated}, connected={connected}")
            return authenticated and connected

        except Exception as e:
            logger.error(f"Error checking auth status: {str(e)}")
            return False

    def reauthenticate(self) -> bool:
        """
        Re-authenticate if session expired.

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/iserver/reauthenticate"
            response = self.session.post(url, timeout=10)
            response.raise_for_status()

            logger.info("Re-authentication successful")
            return True

        except Exception as e:
            logger.error(f"Error re-authenticating: {str(e)}")
            return False

    def tickle(self) -> bool:
        """
        Keep session alive by calling tickle endpoint.

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/tickle"
            response = self.session.post(url, timeout=10)
            response.raise_for_status()

            logger.debug("Session tickle successful")
            return True

        except Exception as e:
            logger.error(f"Error calling tickle: {str(e)}")
            return False

    def get_accounts(self) -> list[str]:
        """
        Get list of account IDs.

        Returns:
            List of account IDs
        """
        try:
            url = f"{self.base_url}/portfolio/accounts"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            accounts = response.json()
            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts

        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return []

    def get_positions(self, account_id: str) -> list[dict]:
        """
        Get current positions for an account.

        Args:
            account_id: IBKR account ID

        Returns:
            List of position dictionaries
        """
        try:
            url = f"{self.base_url}/portfolio/{account_id}/positions/0"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            positions = response.json()
            logger.info(f"Retrieved {len(positions)} positions for account {account_id}")
            return positions

        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []

    def get_ledger(self, account_id: str) -> dict:
        """
        Get account ledger (cash balances).

        Args:
            account_id: IBKR account ID

        Returns:
            Ledger dictionary with cash balances
        """
        try:
            url = f"{self.base_url}/portfolio/{account_id}/ledger"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            ledger = response.json()
            logger.info(f"Retrieved ledger for account {account_id}")
            return ledger

        except Exception as e:
            logger.error(f"Error getting ledger: {str(e)}")
            return {}

    def get_trades(self, days: int = 30) -> list[dict]:
        """
        Get recent trades.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            List of trade dictionaries
        """
        try:
            url = f"{self.base_url}/iserver/account/trades"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            trades = response.json()
            logger.info(f"Retrieved {len(trades)} trades")
            return trades

        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return []

    def fetch_portfolio_data(self, account_id: str) -> dict | None:
        """
        Fetch all portfolio data for an account.

        Args:
            account_id: IBKR account ID

        Returns:
            Dictionary with positions, ledger, and trades
        """
        try:
            # Check auth status first
            if not self.check_auth_status():
                logger.warning("Not authenticated to IB Gateway, attempting to re-authenticate")
                if not self.reauthenticate():
                    logger.error("Failed to authenticate to IB Gateway")
                    return None

            # Tickle to keep session alive
            self.tickle()

            # Get data
            positions = self.get_positions(account_id)
            ledger = self.get_ledger(account_id)
            trades = self.get_trades()

            return {
                "positions": positions,
                "ledger": ledger,
                "trades": trades,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching portfolio data: {str(e)}")
            return None
