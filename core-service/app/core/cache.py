"""Redis cache utility for balance caching"""

import json
import logging
from typing import Any, Optional
from uuid import UUID

import redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for caching account balances and other data"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self._client: Optional[redis.Redis] = None
        self._connected = False
        
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self._client.ping()
                self._connected = True
                logger.info(f"Connected to Redis at {settings.redis_url}")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
                raise
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or error
        """
        try:
            client = self._get_client()
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            serialized = json.dumps(value, default=str)
            client.setex(key, ttl, serialized)
            return True
        except (RedisError, TypeError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            client.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., "balance:account:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = self._get_client()
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except RedisError as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected
    
    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False
            logger.info("Redis connection closed")


# Global cache instance
cache = RedisCache()


def get_balance_cache_key(account_id: UUID, as_of_date: Optional[str] = None) -> str:
    """
    Generate cache key for account balance
    
    Args:
        account_id: Account UUID
        as_of_date: Optional date string (YYYY-MM-DD), defaults to "current"
        
    Returns:
        Cache key string
    """
    date_str = as_of_date or "current"
    return f"balance:account:{account_id}:{date_str}"


def invalidate_account_balance_cache(account_id: UUID) -> int:
    """
    Invalidate all cached balances for an account
    
    Args:
        account_id: Account UUID
        
    Returns:
        Number of cache entries deleted
    """
    pattern = f"balance:account:{account_id}:*"
    return cache.delete_pattern(pattern)


def get_account_cache_key(account_id: UUID) -> str:
    """
    Generate cache key for account data
    
    Args:
        account_id: Account UUID
        
    Returns:
        Cache key string
    """
    return f"account:{account_id}"


def get_account_tree_cache_key(organization_id: UUID) -> str:
    """
    Generate cache key for account tree
    
    Args:
        organization_id: Organization UUID
        
    Returns:
        Cache key string
    """
    return f"account:tree:{organization_id}"


def get_account_children_cache_key(account_id: UUID) -> str:
    """
    Generate cache key for account children
    
    Args:
        account_id: Account UUID
        
    Returns:
        Cache key string
    """
    return f"account:children:{account_id}"


def invalidate_account_cache(account_id: UUID, organization_id: UUID) -> int:
    """
    Invalidate all cached data for an account
    
    Args:
        account_id: Account UUID
        organization_id: Organization UUID
        
    Returns:
        Number of cache entries deleted
    """
    count = 0
    # Invalidate account data
    count += 1 if cache.delete(get_account_cache_key(account_id)) else 0
    # Invalidate account children
    count += 1 if cache.delete(get_account_children_cache_key(account_id)) else 0
    # Invalidate organization tree
    count += 1 if cache.delete(get_account_tree_cache_key(organization_id)) else 0
    # Invalidate balances
    count += invalidate_account_balance_cache(account_id)
    return count

