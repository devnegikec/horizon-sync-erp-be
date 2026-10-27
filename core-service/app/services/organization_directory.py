"""Resolve organization slugs for human-readable object-storage folders.

Object keys are stored in the database, so the folder name is resolved once at
write time. Lookups go through identity-service's internal endpoint and are
cached in-process; a failure falls back to a stable ``org-<uuid>`` folder so an
upload never fails because identity-service is unreachable.
"""

import logging
import re
import time
from uuid import UUID

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_UNSAFE_SLUG_CHARS = re.compile(r"[^a-z0-9-]+")
_CACHE_TTL_SECONDS = 300
_FAILURE_TTL_SECONDS = 30
_MAX_FOLDER_LENGTH = 80


def sanitize_org_slug(value: str | None) -> str | None:
    """Return a path-safe folder name for an organization slug."""
    if not value:
        return None
    slug = _UNSAFE_SLUG_CHARS.sub("-", str(value).strip().lower()).strip("-")
    if not slug:
        return None
    return slug[:_MAX_FOLDER_LENGTH].strip("-") or None


class OrganizationDirectory:
    """In-process cache of ``organization_id -> slug``."""

    _cache: dict[UUID, tuple[float, str | None]] = {}

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    @classmethod
    def slug_for(cls, organization_id: UUID) -> str | None:
        now = time.monotonic()
        cached = cls._cache.get(organization_id)
        if cached is not None and cached[0] > now:
            return cached[1]

        slug = cls._fetch_slug(organization_id)
        ttl = _CACHE_TTL_SECONDS if slug else _FAILURE_TTL_SECONDS
        cls._cache[organization_id] = (now + ttl, slug)
        return slug

    @staticmethod
    def _fetch_slug(organization_id: UUID) -> str | None:
        base_url = (settings.identity_service_url or "").rstrip("/")
        secret = settings.internal_service_secret or ""
        if not base_url or not secret:
            return None

        url = (
            f"{base_url}/api/v1/identity/internal/organizations/{organization_id}/slug"
        )
        try:
            response = httpx.get(
                url,
                headers={"X-Internal-Secret": secret},
                timeout=2.0,
            )
        except Exception:
            logger.warning(
                "Organization slug lookup failed org=%s; using UUID folder",
                organization_id,
                exc_info=True,
            )
            return None

        if response.status_code != 200:
            logger.warning(
                "Organization slug lookup returned %s for org=%s; using UUID folder",
                response.status_code,
                organization_id,
            )
            return None

        try:
            slug = response.json().get("slug")
        except Exception:
            logger.warning(
                "Organization slug response was not JSON for org=%s",
                organization_id,
                exc_info=True,
            )
            return None
        return sanitize_org_slug(slug)


def organization_folder(organization_id: UUID) -> str:
    """Return the bucket folder for an organization (``orgs/<slug>``)."""
    slug = OrganizationDirectory.slug_for(organization_id)
    if slug:
        return f"orgs/{slug}"
    return f"orgs/org-{organization_id}"
