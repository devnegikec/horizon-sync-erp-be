"""Logging configuration for search service"""

import logging
import sys
from datetime import datetime
from typing import Any

from app.config import settings


class SearchLogger:
    """
    Custom logger for search service with structured logging support.

    Provides methods for logging search queries, performance metrics,
    and security events.
    """

    def __init__(self, name: str):
        """
        Initialize logger.

        Args:
            name: Logger name (typically module name)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

        # Configure handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(
                getattr(logging, settings.log_level.upper(), logging.INFO)
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_search_query(
        self,
        query_text: str,
        entity_types: list[str] | None,
        user_id: str,
        result_count: int,
        query_time_ms: int,
        cache_hit: bool = False,
    ):
        """
        Log search query execution.

        Args:
            query_text: Search query text
            entity_types: Entity types searched
            user_id: User who performed the search
            result_count: Number of results returned
            query_time_ms: Query execution time in milliseconds
            cache_hit: Whether result was served from cache
        """
        self.logger.info(
            f"Search query executed | "
            f"query='{query_text}' | "
            f"entity_types={entity_types or 'all'} | "
            f"user_id={user_id} | "
            f"results={result_count} | "
            f"time_ms={query_time_ms} | "
            f"cache_hit={cache_hit}"
        )

    def log_performance_warning(
        self, operation: str, duration_ms: int, threshold_ms: int
    ):
        """
        Log performance warning when operation exceeds threshold.

        Args:
            operation: Operation name
            duration_ms: Actual duration in milliseconds
            threshold_ms: Expected threshold in milliseconds
        """
        self.logger.warning(
            f"Performance warning | "
            f"operation={operation} | "
            f"duration_ms={duration_ms} | "
            f"threshold_ms={threshold_ms} | "
            f"exceeded_by_ms={duration_ms - threshold_ms}"
        )

    def log_security_event(
        self, event_type: str, user_id: str | None, details: dict[str, Any]
    ):
        """
        Log security-related event.

        Args:
            event_type: Type of security event
            user_id: User ID if available
            details: Additional event details
        """
        self.logger.warning(
            f"Security event | "
            f"type={event_type} | "
            f"user_id={user_id or 'unknown'} | "
            f"details={details}"
        )

    def log_cache_operation(
        self, operation: str, key: str, hit: bool = False, ttl: int | None = None
    ):
        """
        Log cache operation.

        Args:
            operation: Cache operation (get, set, delete, etc.)
            key: Cache key
            hit: Whether cache hit occurred (for get operations)
            ttl: Time to live in seconds (for set operations)
        """
        self.logger.debug(
            f"Cache operation | "
            f"operation={operation} | "
            f"key={key} | "
            f"hit={hit} | "
            f"ttl={ttl}"
        )

    def log_index_operation(
        self, operation: str, entity_type: str, entity_count: int, duration_ms: int
    ):
        """
        Log search index operation.

        Args:
            operation: Index operation (update, rebuild, etc.)
            entity_type: Type of entity being indexed
            entity_count: Number of entities processed
            duration_ms: Operation duration in milliseconds
        """
        self.logger.info(
            f"Index operation | "
            f"operation={operation} | "
            f"entity_type={entity_type} | "
            f"count={entity_count} | "
            f"duration_ms={duration_ms}"
        )

    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)


def get_logger(name: str) -> SearchLogger:
    """
    Get logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        SearchLogger instance
    """
    return SearchLogger(name)
