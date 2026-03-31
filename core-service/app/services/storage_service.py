"""GCS storage service for QR block Excel downloads"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage in Google Cloud Storage."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Return a GCS client, using explicit credentials if configured."""
        if self._client is None:
            from google.cloud import storage  # type: ignore[import]

            if settings.gcs_credentials_path:
                self._client = storage.Client.from_service_account_json(
                    settings.gcs_credentials_path
                )
            else:
                self._client = storage.Client()  # Application Default Credentials
        return self._client

    def upload_file(
        self,
        gcs_path: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file to GCS.

        Args:
            gcs_path: Path within the bucket (e.g., "qr-blocks/org-id/block-id/file.xlsx")
            file_content: File content as bytes
            content_type: MIME type of the file

        Returns:
            The GCS path of the uploaded file
        """
        if not settings.gcs_bucket:
            logger.warning("GCS_BUCKET not configured; skipping upload")
            return gcs_path

        try:
            client = self._get_client()
            bucket = client.bucket(settings.gcs_bucket)
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(file_content, content_type=content_type)
            logger.info(f"Uploaded file to GCS: {gcs_path}")
            return gcs_path
        except Exception:
            logger.exception("Failed to upload file to GCS: %s", gcs_path)
            raise

    def get_signed_url(self, gcs_path: str, expiry_minutes: int = 60) -> str:
        """
        Generate a V4 signed download URL for a GCS object.

        Falls back to returning the path as-is if GCS is not configured
        (e.g. in development where download_url is already a full URL).
        """
        if not settings.gcs_bucket:
            # No GCS configured — assume download_url is already a usable URL
            logger.warning(
                "GCS_BUCKET not configured; returning raw path as download URL"
            )
            return gcs_path

        try:
            client = self._get_client()
            bucket = client.bucket(settings.gcs_bucket)
            blob = bucket.blob(gcs_path)
            return blob.generate_signed_url(
                expiration=timedelta(minutes=expiry_minutes),
                method="GET",
                version="v4",
            )
        except Exception:
            logger.exception("Failed to generate signed URL for %s", gcs_path)
            raise

    @staticmethod
    def is_full_url(value: str) -> bool:
        """Check if a stored download_url is already a full HTTP URL (not a GCS path)."""
        return value.startswith("http://") or value.startswith("https://")


# Singleton instance
storage_service = StorageService()


# Legacy function exports for backward compatibility
def get_signed_url(gcs_path: str, expiry_minutes: int = 60) -> str:
    """Legacy function - use storage_service.get_signed_url() instead."""
    return storage_service.get_signed_url(gcs_path, expiry_minutes)


def is_full_url(value: str) -> bool:
    """Legacy function - use storage_service.is_full_url() instead."""
    return storage_service.is_full_url(value)
