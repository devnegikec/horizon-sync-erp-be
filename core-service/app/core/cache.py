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



# Payment-specific cache utilities

def get_payment_cache_key(payment_id: UUID) -> str:
    """
    Generate cache key for payment entry data.
    
    Args:
        payment_id: Payment UUID
        
    Returns:
        Cache key string
    """
    return f"payment:entry:{payment_id}"


def get_payment_list_cache_key(
    organization_id: UUID,
    status: Optional[str] = None,
    payment_mode: Optional[str] = None,
    party_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """
    Generate cache key for payment list queries.
    
    Args:
        organization_id: Organization UUID
        status: Payment status filter
        payment_mode: Payment mode filter
        party_id: Party ID filter
        page: Page number
        page_size: Page size
        
    Returns:
        Cache key string
    """
    filters = []
    if status:
        filters.append(f"status:{status}")
    if payment_mode:
        filters.append(f"mode:{payment_mode}")
    if party_id:
        filters.append(f"party:{party_id}")
    
    filter_str = ":".join(filters) if filters else "all"
    return f"payment:list:{organization_id}:{filter_str}:page:{page}:size:{page_size}"


def get_unpaid_invoices_cache_key(party_id: UUID, organization_id: UUID) -> str:
    """
    Generate cache key for unpaid invoices list.
    
    This is used when loading invoices for payment allocation.
    
    Args:
        party_id: Customer or Supplier UUID
        organization_id: Organization UUID
        
    Returns:
        Cache key string
    """
    return f"invoices:unpaid:{organization_id}:{party_id}"


def invalidate_payment_cache(payment_id: UUID, organization_id: UUID) -> int:
    """
    Invalidate all cached data for a payment.
    
    This should be called when a payment is created, updated, confirmed, or cancelled.
    
    Args:
        payment_id: Payment UUID
        organization_id: Organization UUID
        
    Returns:
        Number of cache entries deleted
    """
    count = 0
    # Invalidate payment data
    count += 1 if cache.delete(get_payment_cache_key(payment_id)) else 0
    # Invalidate payment lists for this organization
    pattern = f"payment:list:{organization_id}:*"
    count += cache.delete_pattern(pattern)
    return count


def invalidate_invoice_cache(invoice_id: UUID, party_id: UUID, organization_id: UUID) -> int:
    """
    Invalidate cached data for an invoice.
    
    This should be called when invoice payment status changes.
    
    Args:
        invoice_id: Invoice UUID
        party_id: Customer or Supplier UUID
        organization_id: Organization UUID
        
    Returns:
        Number of cache entries deleted
    """
    count = 0
    # Invalidate unpaid invoices list for this party
    count += 1 if cache.delete(get_unpaid_invoices_cache_key(party_id, organization_id)) else 0
    return count


def cache_payment_entry(payment_id: UUID, payment_data: dict, ttl: int = 300) -> bool:
    """
    Cache payment entry data.
    
    Args:
        payment_id: Payment UUID
        payment_data: Payment data dictionary
        ttl: Time to live in seconds (default: 5 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    key = get_payment_cache_key(payment_id)
    return cache.set(key, payment_data, ttl)


def get_cached_payment_entry(payment_id: UUID) -> Optional[dict]:
    """
    Get cached payment entry data.
    
    Args:
        payment_id: Payment UUID
        
    Returns:
        Cached payment data or None if not found
    """
    key = get_payment_cache_key(payment_id)
    return cache.get(key)


def cache_payment_list(
    organization_id: UUID,
    filters: dict,
    page: int,
    page_size: int,
    payment_data: dict,
    ttl: int = 180,
) -> bool:
    """
    Cache payment list query results.
    
    Args:
        organization_id: Organization UUID
        filters: Filter parameters
        page: Page number
        page_size: Page size
        payment_data: Payment list data dictionary
        ttl: Time to live in seconds (default: 3 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    key = get_payment_list_cache_key(
        organization_id=organization_id,
        status=filters.get("status"),
        payment_mode=filters.get("payment_mode"),
        party_id=filters.get("party_id"),
        page=page,
        page_size=page_size,
    )
    return cache.set(key, payment_data, ttl)


def get_cached_payment_list(
    organization_id: UUID,
    filters: dict,
    page: int,
    page_size: int,
) -> Optional[dict]:
    """
    Get cached payment list query results.
    
    Args:
        organization_id: Organization UUID
        filters: Filter parameters
        page: Page number
        page_size: Page size
        
    Returns:
        Cached payment list data or None if not found
    """
    key = get_payment_list_cache_key(
        organization_id=organization_id,
        status=filters.get("status"),
        payment_mode=filters.get("payment_mode"),
        party_id=filters.get("party_id"),
        page=page,
        page_size=page_size,
    )
    return cache.get(key)


def cache_unpaid_invoices(
    party_id: UUID,
    organization_id: UUID,
    invoice_data: list,
    ttl: int = 300,
) -> bool:
    """
    Cache unpaid invoices list for a party.
    
    Args:
        party_id: Customer or Supplier UUID
        organization_id: Organization UUID
        invoice_data: List of invoice dictionaries
        ttl: Time to live in seconds (default: 5 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    key = get_unpaid_invoices_cache_key(party_id, organization_id)
    return cache.set(key, invoice_data, ttl)


def get_cached_unpaid_invoices(
    party_id: UUID,
    organization_id: UUID,
) -> Optional[list]:
    """
    Get cached unpaid invoices list for a party.
    
    Args:
        party_id: Customer or Supplier UUID
        organization_id: Organization UUID
        
    Returns:
        Cached invoice list or None if not found
    """
    key = get_unpaid_invoices_cache_key(party_id, organization_id)
    return cache.get(key)
