"""
Redis Caching Layer for Expensive Operations

Provides caching decorators for:
- MCP tool responses (web search, NHS lookup, weather)
- LLM responses
- External API calls

Features:
- Automatic cache invalidation (TTL-based)
- Cache hit/miss metrics
- JSON serialization
- Async/await support

Author: Claude Code
Date: 2025-11-18
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Optional
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based cache manager for expensive operations

    Automatically caches function results with configurable TTL
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"

        # Cache statistics
        self.hits = 0
        self.misses = 0

    async def get_client(self) -> redis.Redis:
        """Get or create Redis connection"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate deterministic cache key from function arguments

        Args:
            prefix: Function name or custom prefix
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Convert args and kwargs to stable string representation
        key_parts = [prefix]

        # Add positional args
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))

        # Add keyword args (sorted for consistency)
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, (dict, list)):
                key_parts.append(f"{key}:{json.dumps(value, sort_keys=True)}")
            else:
                key_parts.append(f"{key}:{value}")

        # Create hash of the key for consistent length
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"cache:{prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            client = await self.get_client()
            value = await client.get(key)

            if value:
                self.hits += 1
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                self.misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.enabled:
            return

        try:
            client = await self.get_client()
            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache SET error: {e}")

    async def delete(self, key: str):
        """Delete value from cache"""
        if not self.enabled:
            return

        try:
            client = await self.get_client()
            await client.delete(key)
            logger.debug(f"Cache DELETE: {key}")

        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")

    async def clear_pattern(self, pattern: str):
        """
        Clear all keys matching pattern

        Args:
            pattern: Redis key pattern (e.g., "cache:weather:*")
        """
        if not self.enabled:
            return

        try:
            client = await self.get_client()
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Cache CLEAR: {pattern} ({deleted_count} keys deleted)")

        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "enabled": self.enabled
        }


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int = 3600, prefix: Optional[str] = None):
    """
    Decorator to cache function results in Redis

    Args:
        ttl: Time to live in seconds (default: 1 hour)
        prefix: Custom cache key prefix (default: function name)

    Usage:
        @cached(ttl=1800, prefix="weather")
        async def get_weather(location: str):
            # Expensive API call
            return weather_data

    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        cache_prefix = prefix or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_mgr = await get_cache_manager()

            # Generate cache key
            cache_key = cache_mgr._generate_cache_key(cache_prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = await cache_mgr.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call original function
            result = await func(*args, **kwargs)

            # Cache the result
            await cache_mgr.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# Common TTL presets
class CacheTTL:
    """Predefined TTL values for common use cases"""
    MINUTE_5 = 300
    MINUTE_15 = 900
    MINUTE_30 = 1800
    HOUR_1 = 3600
    HOUR_6 = 21600
    HOUR_24 = 86400
    DAY_7 = 604800
    MONTH_1 = 2592000
