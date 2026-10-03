"""Feature flag gate for the Identity Service.

Fetches GLOBAL feature flags from the Core Service and computes the set of
disabled module (permission-code prefix) names used to filter role and
permission responses.

The flags are cached briefly so a burst of requests does not fan out to the
Core Service on every call. A single asyncio lock serializes refreshes so
concurrent requests after cache expiry perform at most one HTTP lookup. The
cache is in-process and short-lived — fine for the single-replica dev/deploy
topology used here.
"""

import asyncio
import logging
import time

from app.config import settings
from app.core.feature_flags import disabled_resource_prefixes
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)

# How long a successful flag fetch is reused.
_CACHE_TTL_SECONDS = 30
# How soon to retry after a failed lookup (Core Service down). Kept short so
# permission endpoints are not stalled repeatedly during an outage.
_FAILURE_RETRY_SECONDS = 5
# Dedicated, short timeout for the flag lookup — the default client timeout is
# generous for long-running seed jobs, but a flag refresh must never block a
# role/permission request for that long.
_FLAG_FETCH_TIMEOUT_SECONDS = 2

_cache: dict = {
    "fetched_at": 0.0,
    "disabled": set(),
}
_lock = asyncio.Lock()


def _client() -> CoreServiceClient:
    """Build a Core Service client configured for fast flag lookups."""
    return CoreServiceClient(
        base_url=settings.core_service_url,
        timeout=_FLAG_FETCH_TIMEOUT_SECONDS,
    )


async def get_disabled_resource_prefixes(force: bool = False) -> set[str]:
    """Return the set of permission-code prefixes disabled by feature flags.

    Fails open (keeps the last known set, or an empty set when nothing has
    been fetched yet) whenever the Core Service cannot be reached, so a
    transient outage never hides legitimate permissions.
    """
    now = time.monotonic()
    if not force and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["disabled"]

    async with _lock:
        # Re-check inside the lock — another request may have refreshed while
        # we were waiting to acquire it.
        now = time.monotonic()
        if not force and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
            return _cache["disabled"]

        flags = None
        try:
            flags = await _client().list_global_feature_flags()
        except Exception as e:  # noqa: BLE001 - fail open on any transport error
            logger.warning("Feature flag lookup failed; failing open: %s", e)
            flags = None

        if flags is None:
            # Fail open: keep the previously computed set (or empty) and retry
            # soon instead of waiting the full cache TTL.
            _cache["fetched_at"] = (
                time.monotonic() - (_CACHE_TTL_SECONDS - _FAILURE_RETRY_SECONDS)
            )
            return _cache["disabled"]

        disabled = disabled_resource_prefixes(flags)
        _cache["fetched_at"] = time.monotonic()
        _cache["disabled"] = disabled

        if disabled:
            logger.info("Feature-flag disabled modules: %s", sorted(disabled))
        return disabled
