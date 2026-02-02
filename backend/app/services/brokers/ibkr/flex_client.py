"""IBKR Flex Web Service client."""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)


class IBKRFlexClient:
    """Client for IBKR Flex Web Service API."""

    BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet"

    @staticmethod
    def request_flex_query(
        token: str, query_id: str, from_date: date | None = None, to_date: date | None = None
    ) -> str | None:
        """
        Request flex query execution with optional date range override.

        Args:
            token: IBKR Flex Web Service token
            query_id: Flex Query ID
            from_date: Optional start date (fd parameter) - overrides query config
            to_date: Optional end date (td parameter) - overrides query config

        Returns:
            reference_code for polling, or None if request failed
        """
        try:
            url = f"{IBKRFlexClient.BASE_URL}/FlexStatementService.SendRequest"
            params = {
                "t": token,
                "q": query_id,
                "v": "3",  # API version
            }

            # Add date override parameters if provided
            if from_date:
                params["fd"] = from_date.strftime("%Y%m%d")
            if to_date:
                params["td"] = to_date.strftime("%Y%m%d")

            date_range = ""
            if from_date and to_date:
                date_range = f" (date range: {from_date} to {to_date})"
            logger.info(f"Requesting IBKR Flex Query {query_id}{date_range}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Check for errors
            if root.tag == "Status":
                error_code = root.findtext("ErrorCode")
                error_message = root.findtext("ErrorMessage")
                logger.error(f"IBKR Flex Query request failed: {error_code} - {error_message}")
                return None

            # Extract reference code
            if root.tag == "FlexStatementResponse":
                status = root.findtext("Status")
                if status == "Success":
                    reference_code = root.findtext("ReferenceCode")
                    logger.info(f"Flex Query request successful. Reference code: {reference_code}")
                    return reference_code
                else:
                    error_code = root.findtext("ErrorCode")
                    error_message = root.findtext("ErrorMessage")
                    logger.error(f"Flex Query request failed: {error_code} - {error_message}")
                    return None

            logger.error(f"Unexpected XML response: {response.text}")
            return None

        except requests.ConnectionError as e:
            logger.error(f"Connection error to IBKR Flex Service: {str(e)}")
            return None
        except requests.Timeout as e:
            logger.error(f"Timeout connecting to IBKR Flex Service: {str(e)}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing IBKR XML response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting Flex Query: {str(e)}")
            return None

    @staticmethod
    def get_flex_query_status(token: str, reference_code: str) -> str | None:
        """
        Poll for query completion status.

        Args:
            token: IBKR Flex Web Service token
            reference_code: Reference code from request_flex_query

        Returns:
            'success' if ready, 'pending' if still processing, or None if error
        """
        try:
            url = f"{IBKRFlexClient.BASE_URL}/FlexStatementService.GetStatement"
            params = {"t": token, "q": reference_code, "v": "3"}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            if root.tag == "Status":
                error_code = root.findtext("ErrorCode")
                if error_code == "1019":
                    # Statement generation in progress
                    return "pending"
                else:
                    error_message = root.findtext("ErrorMessage")
                    logger.error(f"IBKR Flex Query status error: {error_code} - {error_message}")
                    return None

            if root.tag == "FlexStatementResponse":
                # Successfully generated, data is ready
                return "success"

            if root.tag == "FlexQueryResponse":
                # Full statement is ready
                return "success"

            logger.warning(f"Unknown status response: {response.text[:200]}")
            return "pending"

        except Exception as e:
            logger.error(f"Error checking Flex Query status: {str(e)}")
            return None

    @staticmethod
    def download_flex_query(token: str, reference_code: str) -> bytes | None:
        """
        Download completed query results.

        Args:
            token: IBKR Flex Web Service token
            reference_code: Reference code from request_flex_query

        Returns:
            XML data as bytes, or None if download failed
        """
        try:
            url = f"{IBKRFlexClient.BASE_URL}/FlexStatementService.GetStatement"
            params = {"t": token, "q": reference_code, "v": "3"}

            logger.info(f"Downloading IBKR Flex Query data for reference {reference_code}")
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # Check if response is XML error or data
            try:
                root = ET.fromstring(response.content)
                if root.tag == "Status":
                    error_code = root.findtext("ErrorCode")
                    error_message = root.findtext("ErrorMessage")
                    logger.error(f"Download error: {error_code} - {error_message}")
                    return None
            except ET.ParseError:
                # Not parseable as Status, might be full data
                pass

            logger.info(f"Successfully downloaded Flex Query data ({len(response.content)} bytes)")
            return response.content

        except Exception as e:
            logger.error(f"Error downloading Flex Query: {str(e)}")
            return None

    @staticmethod
    def fetch_flex_report(
        token: str,
        query_id: str,
        from_date: date | None = None,
        to_date: date | None = None,
        timeout: int = 60,
        poll_interval: int = 2,
    ) -> bytes | None:
        """
        Orchestrator: Request, poll, and download flex query with optional date override.

        Handles polling with exponential backoff.

        Args:
            token: IBKR Flex Web Service token
            query_id: Flex Query ID
            from_date: Optional start date - overrides query config (max 365 days)
            to_date: Optional end date - overrides query config (max 365 days)
            timeout: Maximum wait time in seconds (default: 60)
            poll_interval: Initial polling interval in seconds (default: 2)

        Returns:
            XML data as bytes, or None if failed
        """
        # Step 1: Request query execution with date parameters
        reference_code = IBKRFlexClient.request_flex_query(token, query_id, from_date, to_date)
        if not reference_code:
            logger.error("Failed to request Flex Query")
            return None

        # Step 2: Poll for completion
        start_time = time.time()
        current_interval = poll_interval

        while time.time() - start_time < timeout:
            status = IBKRFlexClient.get_flex_query_status(token, reference_code)

            if status == "success":
                # Step 3: Download data
                return IBKRFlexClient.download_flex_query(token, reference_code)

            if status is None:
                logger.error("Error checking Flex Query status")
                return None

            if status == "pending":
                logger.debug(f"Flex Query still processing, waiting {current_interval}s...")
                time.sleep(current_interval)
                # Exponential backoff, max 10 seconds
                current_interval = min(current_interval * 1.5, 10)
                continue

        logger.error(f"Flex Query timeout after {timeout} seconds")
        return None

    @staticmethod
    def fetch_multi_period_report(
        token: str, query_id: str, start_date: date, end_date: date | None = None
    ) -> list[bytes]:
        """
        Fetch complete historical data by splitting into 365-day chunks.

        IBKR limits each Flex Query to 365 days, so this method:
        1. Splits the date range into 365-day periods
        2. Makes multiple API calls
        3. Returns list of XML data for merging

        Args:
            token: IBKR Flex Web Service token
            query_id: Flex Query ID
            start_date: First date to fetch (e.g., account opening date)
            end_date: Last date to fetch (defaults to today)

        Returns:
            List of XML data bytes for each period, or empty list if failed
        """
        if not end_date:
            end_date = date.today()

        # Calculate total days
        total_days = (end_date - start_date).days + 1
        logger.info(f"Fetching {total_days} days of data from {start_date} to {end_date}")

        # Split into 365-day chunks
        periods = []
        current_start = start_date

        while current_start <= end_date:
            # Calculate end of this period (max 365 days)
            current_end = min(current_start + timedelta(days=364), end_date)
            periods.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)

        logger.info(f"Split into {len(periods)} periods (365-day chunks)")

        # Fetch each period
        results = []
        for i, (period_start, period_end) in enumerate(periods, 1):
            logger.info(f"Fetching period {i}/{len(periods)}: {period_start} to {period_end}")

            xml_data = IBKRFlexClient.fetch_flex_report(
                token, query_id, from_date=period_start, to_date=period_end
            )

            if xml_data:
                results.append(xml_data)
                logger.info(f"Period {i}/{len(periods)} completed ({len(xml_data)} bytes)")
            else:
                logger.error(f"Failed to fetch period {i}/{len(periods)}")
                # Continue with other periods instead of failing completely

        logger.info(f"Fetched {len(results)}/{len(periods)} periods successfully")
        return results
