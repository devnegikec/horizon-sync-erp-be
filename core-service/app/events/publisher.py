"""Event publisher for Redis Streams"""

import json
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import redis
from redis.exceptions import RedisError

from app.config import settings
from app.events.schemas import EntityEvent, EventType

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes entity change events to Redis Streams"""

    def __init__(self, redis_client: redis.Redis | None = None):
        """
        Initialize event publisher.

        Args:
            redis_client: Optional Redis client. If not provided, creates new one.
        """
        if redis_client:
            self.redis = redis_client
        else:
            # Parse Redis URL from settings
            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url, decode_responses=True)

        self.stream_name = getattr(settings, "redis_stream_name", "search:events")

    def _serialize_data(self, data: Any) -> dict[str, Any]:
        """
        Serialize data for JSON encoding, handling special types.

        Args:
            data: Data to serialize

        Returns:
            Serialized data dictionary
        """
        if isinstance(data, dict):
            return {k: self._serialize_value(v) for k, v in data.items()}
        return data

    def _serialize_value(self, value: Any) -> Any:
        """Serialize individual values"""
        if value is None:
            return None
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, "isoformat"):  # datetime, date
            return value.isoformat()
        elif hasattr(value, "__dict__"):  # SQLAlchemy models
            # Get model attributes
            return {
                k: self._serialize_value(v)
                for k, v in value.__dict__.items()
                if not k.startswith("_")
            }
        return value

    def publish_event(self, event: EntityEvent) -> bool:
        """
        Publish an event to Redis Stream.

        Args:
            event: EntityEvent to publish

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Serialize event to JSON
            event_data = event.model_dump()
            event_data["data"] = self._serialize_data(event_data["data"])

            # Convert to flat dict for Redis Stream
            redis_data = {
                "event_type": event_data["event_type"],
                "entity_type": event_data["entity_type"],
                "entity_id": event_data["entity_id"],
                "organization_id": event_data["organization_id"],
                "timestamp": event_data["timestamp"].isoformat()
                if hasattr(event_data["timestamp"], "isoformat")
                else str(event_data["timestamp"]),
                "data": json.dumps(event_data["data"]),
            }

            # Publish to Redis Stream
            message_id = self.redis.xadd(self.stream_name, redis_data)
            logger.info(
                f"Published {event.event_type} event for {event.entity_type}:{event.entity_id} "
                f"to stream {self.stream_name} with ID {message_id}"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to publish event to Redis: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing event: {e}", exc_info=True)
            return False

    def publish_entity_created(
        self,
        entity_type: str,
        entity_id: str,
        organization_id: str,
        data: dict[str, Any],
    ) -> bool:
        """
        Publish entity created event.

        Args:
            entity_type: Type of entity (items, customers, etc.)
            entity_id: Entity unique identifier
            organization_id: Organization ID
            data: Full entity data

        Returns:
            True if published successfully
        """
        event = EntityEvent(
            event_type=EventType.CREATED,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
            data=data,
        )
        return self.publish_event(event)

    def publish_entity_updated(
        self,
        entity_type: str,
        entity_id: str,
        organization_id: str,
        data: dict[str, Any],
    ) -> bool:
        """
        Publish entity updated event.

        Args:
            entity_type: Type of entity (items, customers, etc.)
            entity_id: Entity unique identifier
            organization_id: Organization ID
            data: Full updated entity data

        Returns:
            True if published successfully
        """
        event = EntityEvent(
            event_type=EventType.UPDATED,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
            data=data,
        )
        return self.publish_event(event)

    def publish_entity_deleted(
        self, entity_type: str, entity_id: str, organization_id: str
    ) -> bool:
        """
        Publish entity deleted event.

        Args:
            entity_type: Type of entity (items, customers, etc.)
            entity_id: Entity unique identifier
            organization_id: Organization ID

        Returns:
            True if published successfully
        """
        event = EntityEvent(
            event_type=EventType.DELETED,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
            data={},  # No data needed for deletion
        )
        return self.publish_event(event)


# Global event publisher instance
_event_publisher: EventPublisher | None = None


def get_event_publisher() -> EventPublisher:
    """Get or create global event publisher instance"""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher
