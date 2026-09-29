"""Feature flag gate for the Identity Service.

Fetches GLOBAL feature flags from the Core Service and computes the set of
disabled module (permission-code prefix) names used to filter role and
permission responses.

The flags are cached briefly so a burst of requests does not fan out to the
Core Service on every call. The cache is in-process and short-lived — fine for
the single-replica dev/deploy topology used here.
"""

import logging
import time

from app.config import settings
from app.core.feature_flags import disabled_resource_prefixes
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)

# Cache TTL in seconds.
_CACHE_TTL_SECONDS = 30

_cache: dict = {
    "fetched_at": 0.0,
    "disabled": set(),
}


def _client() -> CoreServiceClient:
    """Build a Core Service client from current settings."""
    return CoreServiceClient(
        base_url=settings.core_service_url,
        timeout=settings.core_service_timeout,
    )


async def get_disabled_resource_prefixes(force: bool = False) -> set[str]:
    """Return the set of permission-code prefixes disabled by feature flags.

    Fails open (returns an empty set) whenever the Core Service cannot be
    reached, so a transient outage never hides legitimate permissions.
    """
    now = time.monotonic()
    if not force and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["disabled"]

    try:
        flags = await _client().list_global_feature_flags()
    except Exception as e:  # noqa: BLE001 - fail open on any transport error
        logger.warning("Feature flag lookup failed; failing open: %s", e)
        flags = {}

    disabled = disabled_resource_prefixes(flags)

    _cache["fetched_at"] = time.monotonic()
    _cache["disabled"] = disabled

    if disabled:
        logger.info("Feature-flag disabled modules: %s", sorted(disabled))
    return disabled
