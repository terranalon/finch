"""File storage service for broker data uploads.

Manages the storage and retrieval of uploaded broker data files on disk.
Files are organized by broker type and account ID.
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import BrokerDataSource

logger = logging.getLogger(__name__)

# Base directory for broker uploads (can be overridden via environment variable)
DEFAULT_UPLOAD_DIR = "/app/data/broker_uploads"


class BrokerFileStorage:
    """Manages storage of uploaded broker data files.

    Storage structure:
        /data/broker_uploads/
        ├── ibkr/
        │   └── account_7/
        │       └── 20260111_143022_Portfolio_Query.xml
        ├── binance/
        │   └── account_12/
        │       └── 20260115_091500_trades_export.csv
    """

    def __init__(self, base_dir: str | None = None):
        """Initialize the file storage service.

        Args:
            base_dir: Base directory for uploads. Defaults to /app/data/broker_uploads
        """
        self.base_dir = Path(base_dir or os.getenv("BROKER_UPLOAD_DIR", DEFAULT_UPLOAD_DIR))

    def _ensure_directory(self, path: Path) -> None:
        """Ensure directory exists, creating it if necessary."""
        path.mkdir(parents=True, exist_ok=True)

    def _get_account_dir(self, broker_type: str, account_id: int) -> Path:
        """Get the directory path for a specific account's uploads."""
        return self.base_dir / broker_type / f"account_{account_id}"

    @staticmethod
    def calculate_hash(content: bytes) -> str:
        """Calculate SHA256 hash of file content.

        Args:
            content: File content as bytes

        Returns:
            Hex-encoded SHA256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def save_file(
        self,
        account_id: int,
        broker_type: str,
        content: bytes,
        filename: str,
    ) -> tuple[str, str, int]:
        """Save uploaded file to disk.

        Args:
            account_id: The account this file belongs to
            broker_type: Broker type identifier (e.g., 'ibkr')
            content: File content as bytes
            filename: Original filename

        Returns:
            Tuple of (file_path, file_hash, file_size)
        """
        # Calculate hash
        file_hash = self.calculate_hash(content)
        file_size = len(content)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = self._sanitize_filename(filename)
        new_filename = f"{timestamp}_{safe_filename}"

        # Ensure directory exists
        account_dir = self._get_account_dir(broker_type, account_id)
        self._ensure_directory(account_dir)

        # Save file
        file_path = account_dir / new_filename
        with open(file_path, "wb") as f:
            f.write(content)

        # Return relative path from base_dir for database storage
        relative_path = str(file_path.relative_to(self.base_dir))

        logger.info(
            "Saved file: %s (hash=%s, size=%d bytes)",
            relative_path,
            file_hash[:16] + "...",
            file_size,
        )

        return relative_path, file_hash, file_size

    def read_file(self, file_path: str) -> bytes:
        """Read a stored file.

        Args:
            file_path: Relative path from base_dir (as stored in database)

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.base_dir / file_path
        with open(full_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        """Delete a stored file.

        Args:
            file_path: Relative path from base_dir

        Returns:
            True if file was deleted, False if it didn't exist
        """
        full_path = self.base_dir / file_path
        try:
            full_path.unlink()
            logger.info("Deleted file: %s", file_path)
            return True
        except FileNotFoundError:
            logger.warning("File not found for deletion: %s", file_path)
            return False

    def check_duplicate(
        self,
        db: Session,
        file_hash: str,
        account_id: int,
    ) -> BrokerDataSource | None:
        """Check if a file with the same hash already exists for this account.

        Args:
            db: Database session
            file_hash: SHA256 hash of the file
            account_id: Account ID to check within

        Returns:
            Existing BrokerDataSource if duplicate found, None otherwise
        """
        return (
            db.query(BrokerDataSource)
            .filter(
                BrokerDataSource.file_hash == file_hash,
                BrokerDataSource.account_id == account_id,
            )
            .first()
        )

    def get_file_size(self, file_path: str) -> int | None:
        """Get the size of a stored file.

        Args:
            file_path: Relative path from base_dir

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        full_path = self.base_dir / file_path
        try:
            return full_path.stat().st_size
        except FileNotFoundError:
            return None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to remove potentially dangerous characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem use
        """
        # Remove path separators and other dangerous characters
        dangerous_chars = ["/", "\\", "..", "\x00", "\n", "\r"]
        result = filename
        for char in dangerous_chars:
            result = result.replace(char, "_")

        # Limit length
        if len(result) > 100:
            name, ext = os.path.splitext(result)
            result = name[:90] + ext

        return result

    @staticmethod
    def get_extension(filename: str) -> str:
        """Get file extension with leading dot.

        Args:
            filename: Original filename

        Returns:
            Extension with leading dot (e.g., '.xml'), or empty string
        """
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""


# Singleton instance for convenience
_default_storage: BrokerFileStorage | None = None


def get_file_storage() -> BrokerFileStorage:
    """Get the default file storage instance."""
    global _default_storage
    if _default_storage is None:
        _default_storage = BrokerFileStorage()
    return _default_storage
