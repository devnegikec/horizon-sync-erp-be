"""Object storage helpers for QR artifacts and Product images."""

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.config import settings

logger = logging.getLogger(__name__)

PRODUCT_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
INBOUND_EVIDENCE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
PRODUCT_IMAGE_S3_KEY_PATTERN = re.compile(
    r"^qseal/organizations/[0-9a-f-]{36}/products/[0-9a-f-]{36}/"
    r"images/(?:logo|banner)/[0-9a-f]{32}\.(?:jpg|png|webp)$"
)

QR_ARTIFACT_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _get_client():
    """Return a GCS client, using explicit credentials if configured."""
    from google.cloud import storage  # type: ignore[import]

    if settings.gcs_credentials_path:
        return storage.Client.from_service_account_json(settings.gcs_credentials_path)
    return storage.Client()  # Application Default Credentials


def _get_s3_client():
    """Return an S3 client using the standard AWS credential provider chain."""
    import boto3  # type: ignore[import]

    kwargs = {"region_name": settings.aws_s3_region}
    if settings.aws_s3_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_s3_endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("s3", **kwargs)


def build_qr_artifact_key(
    organization_id: UUID,
    product_id: UUID,
    block_id: UUID,
) -> str:
    """Build a tenant-scoped, label-independent key for a QR workbook."""
    return (
        f"qseal/organizations/{organization_id}/products/{product_id}/"
        f"blocks/{block_id}/qr_codes.xlsx"
    )


def store_qr_artifact(data: bytes, object_key: str, filename: str) -> None:
    """Upload a private QR workbook to S3.

    A missing bucket is allowed only outside production, where the existing
    authenticated streaming fallback remains available.
    """
    if not settings.aws_s3_bucket:
        if settings.environment.lower() == "production":
            raise RuntimeError("AWS_S3_BUCKET is required for QR artifacts")
        return

    _get_s3_client().put_object(
        Bucket=settings.aws_s3_bucket,
        Key=object_key,
        Body=data,
        ContentType=QR_ARTIFACT_CONTENT_TYPE,
        ContentDisposition=f'attachment; filename="{filename}"',
        ServerSideEncryption="AES256",
    )


def get_qr_artifact_signed_url(object_key: str) -> tuple[str, datetime]:
    """Return a short-lived presigned GET URL for a private QR workbook."""
    if not settings.aws_s3_bucket:
        raise RuntimeError("AWS_S3_BUCKET is not configured")

    expires_in = settings.aws_s3_presigned_expiry_seconds
    url = _get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )
    return url, datetime.now(UTC) + timedelta(seconds=expires_in)


def delete_qr_artifact(object_key: str) -> None:
    """Delete a QR workbook after a failed generation transaction."""
    if not settings.aws_s3_bucket:
        return
    _get_s3_client().delete_object(
        Bucket=settings.aws_s3_bucket,
        Key=object_key,
    )


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


def _local_product_image_path(object_key: str) -> Path:
    root = Path(settings.product_image_upload_dir).resolve()
    path = (root / object_key).resolve()
    if root not in path.parents:
        raise ValueError("Invalid Product image path")
    return path


def store_product_image(
    data: bytes,
    content_type: str,
    organization_id: UUID,
    product_id: UUID,
    image_type: str,
) -> str:
    """Persist a Product image and return its opaque object key."""
    extension = PRODUCT_IMAGE_CONTENT_TYPES[content_type]
    object_key = (
        f"qseal/organizations/{organization_id}/products/{product_id}/"
        f"images/{image_type}/{uuid4().hex}{extension}"
    )

    if settings.aws_s3_bucket:
        _get_s3_client().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return object_key

    if settings.environment.lower() == "production":
        raise RuntimeError("AWS_S3_BUCKET is required for Product images in production")

    path = _local_product_image_path(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return object_key


def read_product_image(object_key: str) -> tuple[bytes, str]:
    """Read a Product image from S3 or a legacy Product image store."""
    if object_key.startswith("qseal/"):
        if not PRODUCT_IMAGE_S3_KEY_PATTERN.fullmatch(object_key):
            raise ValueError("Invalid Product image object key")
        if settings.aws_s3_bucket:
            try:
                response = _get_s3_client().get_object(
                    Bucket=settings.aws_s3_bucket,
                    Key=object_key,
                )
            except Exception as exc:
                error = getattr(exc, "response", {}).get("Error", {})
                if error.get("Code") in {"404", "NoSuchKey", "NotFound"}:
                    raise FileNotFoundError(object_key) from exc
                raise
            return (
                response["Body"].read(),
                response.get("ContentType") or "application/octet-stream",
            )

    # Backward compatibility for images uploaded before Product images moved to S3.
    if settings.gcs_bucket:
        client = _get_client()
        blob = client.bucket(settings.gcs_bucket).blob(f"product-images/{object_key}")
        if not blob.exists():
            raise FileNotFoundError(object_key)
        data = blob.download_as_bytes()
        return data, blob.content_type or "application/octet-stream"

    path = _local_product_image_path(object_key)
    if not path.is_file():
        raise FileNotFoundError(object_key)
    content_type = next(
        (
            candidate
            for candidate, extension in PRODUCT_IMAGE_CONTENT_TYPES.items()
            if path.suffix.lower() == extension
        ),
        "application/octet-stream",
    )
    return path.read_bytes(), content_type


def delete_product_image(object_key: str) -> None:
    """Delete a Product image if it exists."""
    if object_key.startswith("qseal/"):
        if not PRODUCT_IMAGE_S3_KEY_PATTERN.fullmatch(object_key):
            raise ValueError("Invalid Product image object key")
        if settings.aws_s3_bucket:
            _get_s3_client().delete_object(
                Bucket=settings.aws_s3_bucket,
                Key=object_key,
            )
            return

    # Backward compatibility for images uploaded before Product images moved to S3.
    if settings.gcs_bucket:
        client = _get_client()
        blob = client.bucket(settings.gcs_bucket).blob(f"product-images/{object_key}")
        if blob.exists():
            blob.delete()
        return

    path = _local_product_image_path(object_key)
    if path.is_file():
        path.unlink()


def store_inbound_exception_evidence(
    data: bytes,
    content_type: str,
    organization_id: UUID,
    exception_id: UUID,
) -> str:
    """Store private optional photo/PDF evidence for an inbound exception."""
    if content_type not in INBOUND_EVIDENCE_CONTENT_TYPES:
        raise ValueError("Unsupported inbound evidence content type")
    object_key = (
        f"inbound/organizations/{organization_id}/exceptions/{exception_id}/"
        f"evidence/{uuid4().hex}{INBOUND_EVIDENCE_CONTENT_TYPES[content_type]}"
    )
    if settings.aws_s3_bucket:
        _get_s3_client().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return object_key
    if settings.environment.lower() == "production":
        raise RuntimeError(
            "AWS_S3_BUCKET is required for inbound evidence in production"
        )
    path = _local_product_image_path(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return object_key
