"""Redis Pub/Sub publisher for 3D warehouse real-time events.

Used by BinReservationService to broadcast bin state changes to all
WebSocket clients watching a warehouse channel.  The subscribe side
lives in the WebSocket endpoint (wms_3d.py).

Channel naming:  warehouse:3d:{warehouse_id}

Message schema (JSON):
  {
    "type":              "bin_reserved" | "bin_released",
    "bin_id":            "<uuid>",
    "warehouse_id":      "<uuid>",
    "worker_id":         "<uuid>",          # present for bin_reserved
    "expires_in_seconds": 300,              # present for bin_reserved
    "fill_percentage":   42.5               # present when known
  }

Non-critical: all publish errors are swallowed so a Redis hiccup never
blocks the HTTP response that triggered the event.
"""

import json
import logging
from uuid import UUID

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Return a lazy, module-level sync Redis client (re-connect on failure)."""
    global _client
    try:
        if _client is not None:
            _client.ping()
            return _client
    except Exception:
        _client = None

    _client = redis.Redis.from_url(settings.redis_warehouse_url, decode_responses=True)
    return _client


def publish_bin_event(
    event_type: str,
    bin_id: UUID,
    warehouse_id: UUID,
    **extra,
) -> None:
    """Publish a bin state-change event to the warehouse Pub/Sub channel.

    Args:
        event_type:   'bin_reserved' or 'bin_released'
        bin_id:       The bin that changed.
        warehouse_id: Used to route to the correct channel.
        **extra:      Arbitrary extra fields (worker_id, expires_in_seconds …).
                      UUID values are auto-coerced to strings.
    """
    channel = f"warehouse:3d:{warehouse_id}"
    payload: dict = {
        "type": event_type,
        "bin_id": str(bin_id),
        "warehouse_id": str(warehouse_id),
    }
    for k, v in extra.items():
        payload[k] = str(v) if isinstance(v, UUID) else v

    try:
        _get_client().publish(channel, json.dumps(payload))
    except Exception as exc:
        logger.warning("redis pubsub publish failed (non-critical): %s", exc)
