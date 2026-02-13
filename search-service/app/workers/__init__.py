"""Event consumer workers for search service"""

from app.workers.event_consumer import SearchIndexEventConsumer

__all__ = ["SearchIndexEventConsumer"]
