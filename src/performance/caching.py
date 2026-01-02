"""
Caching Strategy with Redis
Caches frequently accessed code patterns, API responses, and user sessions
"""

import asyncio
import hashlib
import json
import logging
import pickle
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCache:
    """Redis-based caching with TTL and serialization"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_ttl: int = 3600,  # 1 hour
        key_prefix: str = "cache",
    ):
        """
        Initialize Redis cache.
        
        Args:
            redis_client: Redis client
            default_ttl: Default TTL in seconds
            key_prefix: Key prefix for all cache keys
        """
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
    
    def _make_key(self, key: str) -> str:
        """Create full cache key"""
        return f"{self.key_prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        full_key = self._make_key(key)
        try:
            data = await self.redis_client.get(full_key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache"""
        full_key = self._make_key(key)
        try:
            data = pickle.dumps(value)
            ttl = ttl or self.default_ttl
            return await self.redis_client.setex(full_key, ttl, data)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        full_key = self._make_key(key)
        try:
            return await self.redis_client.delete(full_key) > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        full_key = self._make_key(key)
        try:
            return await self.redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            keys = await self.redis_client.keys(self._make_key(pattern))
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0


class CodePatternCache:
    """Cache for frequently accessed code patterns"""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.pattern_ttl = 86400  # 24 hours
    
    def _make_pattern_key(self, pattern_hash: str) -> str:
        """Create key for code pattern"""
        return f"code_pattern:{pattern_hash}"
    
    async def get_pattern(self, pattern_hash: str) -> Optional[dict]:
        """Get cached code pattern"""
        key = self._make_pattern_key(pattern_hash)
        return await self.cache.get(key)
    
    async def cache_pattern(
        self,
        pattern_hash: str,
        pattern_data: dict,
        ttl: Optional[int] = None,
    ):
        """Cache code pattern"""
        key = self._make_pattern_key(pattern_hash)
        await self.cache.set(key, pattern_data, ttl or self.pattern_ttl)
    
    @staticmethod
    def hash_pattern(pattern: str) -> str:
        """Generate hash for code pattern"""
        return hashlib.sha256(pattern.encode()).hexdigest()


class APIResponseCache:
    """Cache for API responses"""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.default_ttl = 300  # 5 minutes
    
    def _make_response_key(self, endpoint: str, params: dict) -> str:
        """Create key for API response"""
        # Sort params for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"api_response:{endpoint}:{params_hash}"
    
    async def get_response(self, endpoint: str, params: dict) -> Optional[Any]:
        """Get cached API response"""
        key = self._make_response_key(endpoint, params)
        return await self.cache.get(key)
    
    async def cache_response(
        self,
        endpoint: str,
        params: dict,
        response: Any,
        ttl: Optional[int] = None,
    ):
        """Cache API response"""
        key = self._make_response_key(endpoint, params)
        await self.cache.set(key, response, ttl or self.default_ttl)
    
    async def invalidate_endpoint(self, endpoint: str):
        """Invalidate all cached responses for endpoint"""
        pattern = f"api_response:{endpoint}:*"
        await self.cache.clear_pattern(pattern)


class SessionCache:
    """Cache for user sessions"""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.session_ttl = 3600  # 1 hour
    
    def _make_session_key(self, session_id: str) -> str:
        """Create key for session"""
        return f"session:{session_id}"
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get cached session"""
        key = self._make_session_key(session_id)
        return await self.cache.get(key)
    
    async def cache_session(
        self,
        session_id: str,
        session_data: dict,
        ttl: Optional[int] = None,
    ):
        """Cache session"""
        key = self._make_session_key(session_id)
        await self.cache.set(key, session_data, ttl or self.session_ttl)
    
    async def delete_session(self, session_id: str):
        """Delete session from cache"""
        key = self._make_session_key(session_id)
        await self.cache.delete(key)
    
    async def extend_session(self, session_id: str, ttl: Optional[int] = None):
        """Extend session TTL"""
        key = self._make_session_key(session_id)
        if await self.cache.exists(key):
            # Get current session data
            session_data = await self.cache.get(key)
            if session_data:
                # Re-cache with new TTL
                await self.cache.set(key, session_data, ttl or self.session_ttl)


def cached(
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
    cache: Optional[RedisCache] = None,
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Cache TTL in seconds
        key_func: Function to generate cache key from args
        cache: RedisCache instance (uses global if not provided)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance
            if cache is None:
                from src.performance.caching import get_redis_cache
                cache_instance = get_redis_cache()
            else:
                cache_instance = cache
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash of function name + args + kwargs
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items())),
                }
                cache_key = hashlib.md5(
                    json.dumps(key_data, sort_keys=True).encode()
                ).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_instance.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache instances
_redis_cache: Optional[RedisCache] = None
_code_pattern_cache: Optional[CodePatternCache] = None
_api_response_cache: Optional[APIResponseCache] = None
_session_cache: Optional[SessionCache] = None


def get_redis_cache() -> RedisCache:
    """Get global Redis cache instance"""
    global _redis_cache
    if _redis_cache is None:
        import os
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        _redis_cache = RedisCache(redis_client)
    return _redis_cache


def get_code_pattern_cache() -> CodePatternCache:
    """Get global code pattern cache"""
    global _code_pattern_cache
    if _code_pattern_cache is None:
        _code_pattern_cache = CodePatternCache(get_redis_cache())
    return _code_pattern_cache


def get_api_response_cache() -> APIResponseCache:
    """Get global API response cache"""
    global _api_response_cache
    if _api_response_cache is None:
        _api_response_cache = APIResponseCache(get_redis_cache())
    return _api_response_cache


def get_session_cache() -> SessionCache:
    """Get global session cache"""
    global _session_cache
    if _session_cache is None:
        _session_cache = SessionCache(get_redis_cache())
    return _session_cache

