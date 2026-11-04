"""Storage helpers for user profile images (avatars).

Backends, in order of preference:

1. **S3-compatible bucket** (``AWS_S3_BUCKET``) — the only durable option. Keys
   are read back through the identity-service, so the bucket can stay private.
2. **Local directory** (``avatar_storage_dir``) — development fallback. Container
   filesystems are ephemeral, so deployed environments must configure a bucket.

Stored values are *keys*, never URLs: the public URL is built by the endpoint so
it always matches the host the API is actually served from.
"""

import base64
import logging
import re
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from app.config import settings

logger = logging.getLogger(__name__)

AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_EXTENSION_CONTENT_TYPES = {ext: ctype for ctype, ext in AVATAR_CONTENT_TYPES.items()}

# Browsers that POST the image inline send ``data:image/png;base64,<payload>``.
# Older clients still use the non-standard ``image/jpg``.
AVATAR_DATA_URL_PATTERN = re.compile(
    r"^data:(image/(?:png|jpe?g|webp));base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Only keys produced by build_avatar_key() may be read or deleted, which keeps
# traversal attempts and arbitrary bucket objects out of the public route.
AVATAR_KEY_PATTERN = re.compile(
    r"^users/[0-9a-f-]{36}/avatars/[0-9a-f]{32}\.(?:jpg|png|webp)$"
)


def build_avatar_key(user_id: UUID | str, extension: str) -> str:
    """Build a per-user, non-guessable storage key for an avatar."""
    return f"users/{user_id}/avatars/{uuid4().hex}{extension}"


def is_avatar_key(key: str) -> bool:
    return bool(AVATAR_KEY_PATTERN.match(key or ""))


def is_avatar_data_url(value: str | None) -> bool:
    """True when the value is an inline base64 image data URL."""
    return bool(value) and value.strip().lower().startswith("data:")


def avatar_max_bytes() -> int:
    return settings.avatar_max_bytes


def max_base64_length() -> int:
    """Characters needed to base64-encode an image of the maximum size."""
    return (settings.avatar_max_bytes * 4 // 3) + 8


def decode_avatar_data_url(value: str) -> tuple[bytes, str]:
    """Decode an inline ``data:image/...;base64,...`` avatar payload.

    Returns:
        ``(image_bytes, content_type)``.

    Raises:
        ValueError: unsupported image type, invalid base64, empty or too large.
    """
    match = AVATAR_DATA_URL_PATTERN.match((value or "").strip())
    if match is None:
        raise ValueError(
            "avatar_url must be an absolute http(s) URL or a base64 data URL "
            "of a PNG, JPEG or WebP image"
        )

    content_type = match.group(1).lower()
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    if content_type not in AVATAR_CONTENT_TYPES:
        raise ValueError("Only PNG, JPEG and WebP images are supported")

    limit_mb = settings.avatar_max_bytes // (1024 * 1024)
    encoded = match.group(2)
    if len(encoded) > max_base64_length():
        raise ValueError(f"Image exceeds the {limit_mb} MB limit")

    try:
        data = base64.b64decode(encoded)
    except Exception as exc:  # noqa: BLE001 — any decode failure is a client error
        raise ValueError("avatar_url data URL is not valid base64") from exc

    if not data:
        raise ValueError("Image file is empty")
    if len(data) > settings.avatar_max_bytes:
        raise ValueError(f"Image exceeds the {limit_mb} MB limit")

    return data, content_type


def _local_path(key: str) -> Path:
    root = Path(settings.avatar_storage_dir).resolve()
    path = (root / key).resolve()
    if root != path and root not in path.parents:
        raise ValueError("Avatar key escapes the storage directory")
    return path


def _s3_client():
    """S3 client using the standard credential chain (boto3 is already a dep)."""
    import boto3  # type: ignore[import]
    from botocore.config import Config  # type: ignore[import]

    config_kwargs: dict = {
        "region_name": settings.aws_s3_region,
        "signature_version": "s3v4",
    }
    addressing_style = (settings.aws_s3_addressing_style or "").strip().lower()
    if addressing_style in {"path", "virtual", "auto"}:
        config_kwargs["s3"] = {"addressing_style": addressing_style}

    kwargs: dict = {
        "region_name": settings.aws_s3_region,
        "config": Config(**config_kwargs),
    }
    if settings.aws_s3_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_s3_endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("s3", **kwargs)


def _sse_kwargs() -> dict:
    algorithm = (settings.aws_s3_server_side_encryption or "").strip()
    if algorithm.lower() in {"none", "off", "disabled", "false"}:
        return {}
    return {"ServerSideEncryption": algorithm} if algorithm else {}


def store_avatar(user_id: UUID, data: bytes, content_type: str) -> str:
    """Persist an avatar image and return its storage key.

    Raises:
        ValueError: the content type is not a supported image format.
    """
    extension = AVATAR_CONTENT_TYPES.get(content_type)
    if extension is None:
        raise ValueError(f"Unsupported avatar content type: {content_type}")

    key = build_avatar_key(user_id, extension)
    if settings.aws_s3_bucket:
        _s3_client().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
            **_sse_kwargs(),
        )
        return key

    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    logger.warning(
        "Avatar stored on the local filesystem (%s); configure AWS_S3_BUCKET "
        "for durable storage",
        path,
    )
    return key


def read_avatar(key: str) -> tuple[bytes, str]:
    """Return ``(bytes, content_type)`` for a stored avatar.

    Raises:
        ValueError: the key is not a valid avatar key.
        FileNotFoundError: nothing is stored under that key.
    """
    if not is_avatar_key(key):
        raise ValueError("Invalid avatar key")

    if settings.aws_s3_bucket:
        response = _s3_client().get_object(Bucket=settings.aws_s3_bucket, Key=key)
        content_type = response.get("ContentType") or _content_type_for(key)
        return response["Body"].read(), content_type

    path = _local_path(key)
    if not path.is_file():
        raise FileNotFoundError(key)
    return path.read_bytes(), _content_type_for(key)


def delete_avatar(key: str) -> None:
    """Delete a stored avatar. Best effort — never raises."""
    if not is_avatar_key(key):
        return
    try:
        if settings.aws_s3_bucket:
            _s3_client().delete_object(Bucket=settings.aws_s3_bucket, Key=key)
            return
        path = _local_path(key)
        if path.is_file():
            path.unlink()
    except Exception:  # noqa: BLE001 — cleanup must not break the request
        logger.warning("Could not delete avatar %s", key, exc_info=True)


def _content_type_for(key: str) -> str:
    return _EXTENSION_CONTENT_TYPES.get(
        Path(key).suffix.lower(), "application/octet-stream"
    )


def clear_local_storage() -> None:
    """Remove the whole local avatar directory (used by tests)."""
    shutil.rmtree(settings.avatar_storage_dir, ignore_errors=True)
