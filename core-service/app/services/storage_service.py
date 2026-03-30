"""GCS storage service for QR block Excel downloads"""

import logging
from datetime import UTC, datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return a GCS client, using explicit credentials if configured."""
    from google.cloud import storage  # type: ignore[import]

    if settings.gcs_credentials_path:
        return storage.Client.from_service_account_json(settings.gcs_credentials_path)
    return storage.Client()  # Application Default Credentials


def get_signed_url(gcs_path: str, expiry_minutes: int = 60) -> str:
    """
    Generate a V4 signed download URL for a GCS object.

    Falls back to returning the path as-is if GCS is not configured
    (e.g. in development where download_url is already a full URL).
    """
    if not settings.gcs_bucket:
        # No GCS configured — assume download_url is already a usable URL
        logger.warning("GCS_BUCKET not configured; returning raw path as download URL")
        return gcs_path

    try:
        client = _get_client()
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


def is_full_url(value: str) -> bool:
    """Check if a stored download_url is already a full HTTP URL (not a GCS path)."""
    return value.startswith("http://") or value.startswith("https://")
