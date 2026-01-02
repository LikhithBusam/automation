"""
Advanced Rate Limiting at Multiple Levels
Application, API Gateway, and Load Balancer levels
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token bucket rate limiter with Redis backend"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        rate: float = 10.0,  # tokens per second
        capacity: int = 100,  # bucket capacity
        key_prefix: str = "rate_limit",
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            redis_client: Redis client for distributed rate limiting
            rate: Tokens added per second
            capacity: Maximum bucket capacity
            key_prefix: Redis key prefix
        """
        self.redis_client = redis_client
        self.rate = rate
        self.capacity = capacity
        self.key_prefix = key_prefix
    
    async def is_allowed(
        self,
        identifier: str,
        tokens: int = 1,
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Check if request is allowed.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            tokens: Number of tokens to consume
        
        Returns:
            (is_allowed, metadata) tuple
        """
        key = f"{self.key_prefix}:{identifier}"
        now = time.time()
        
        # Use Redis Lua script for atomic operations
        lua_script = """
        local key = KEYS[1]
        local rate = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local tokens = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_update = tonumber(bucket[2]) or now
        
        -- Add tokens based on elapsed time
        local elapsed = now - last_update
        local tokens_to_add = elapsed * rate
        current_tokens = math.min(capacity, current_tokens + tokens_to_add)
        
        -- Check if enough tokens available
        if current_tokens >= tokens then
            current_tokens = current_tokens - tokens
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
            redis.call('EXPIRE', key, 3600)  -- Expire after 1 hour
            return {1, current_tokens, capacity - current_tokens}
        else
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
            redis.call('EXPIRE', key, 3600)
            return {0, current_tokens, capacity - current_tokens}
        end
        """
        
        result = await self.redis_client.eval(
            lua_script,
            1,
            key,
            str(self.rate),
            str(self.capacity),
            str(tokens),
            str(now),
        )
        
        is_allowed = bool(result[0])
        current_tokens = float(result[1])
        remaining = float(result[2])
        
        metadata = {
            "allowed": is_allowed,
            "tokens_remaining": remaining,
            "tokens_current": current_tokens,
            "capacity": self.capacity,
            "rate": self.rate,
        }
        
        return is_allowed, metadata


class SlidingWindowRateLimiter:
    """Sliding window rate limiter"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        window_seconds: int = 60,
        max_requests: int = 100,
        key_prefix: str = "sliding_window",
    ):
        """
        Initialize sliding window rate limiter.
        
        Args:
            redis_client: Redis client
            window_seconds: Time window in seconds
            max_requests: Maximum requests per window
            key_prefix: Redis key prefix
        """
        self.redis_client = redis_client
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.key_prefix = key_prefix
    
    async def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed in sliding window.
        
        Args:
            identifier: Unique identifier
        
        Returns:
            (is_allowed, metadata) tuple
        """
        key = f"{self.key_prefix}:{identifier}"
        now = int(time.time())
        window_start = now - self.window_seconds
        
        # Remove old entries
        await self.redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_count = await self.redis_client.zcard(key)
        
        if current_count < self.max_requests:
            # Add current request
            await self.redis_client.zadd(key, {str(now): now})
            await self.redis_client.expire(key, self.window_seconds)
            
            return True, {
                "allowed": True,
                "requests_remaining": self.max_requests - current_count - 1,
                "requests_current": current_count + 1,
                "window_seconds": self.window_seconds,
            }
        else:
            # Get oldest request time
            oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1]) + self.window_seconds - now if oldest else 0
            
            return False, {
                "allowed": False,
                "requests_remaining": 0,
                "requests_current": current_count,
                "retry_after": retry_after,
                "window_seconds": self.window_seconds,
            }


class MultiLevelRateLimiter:
    """Multi-level rate limiter (IP, User, Endpoint)"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        ip_limits: Dict[str, int] = None,
        user_limits: Dict[str, int] = None,
        endpoint_limits: Dict[str, int] = None,
    ):
        """
        Initialize multi-level rate limiter.
        
        Args:
            redis_client: Redis client
            ip_limits: Rate limits per IP (requests per minute)
            user_limits: Rate limits per user (requests per minute)
            endpoint_limits: Rate limits per endpoint (requests per minute)
        """
        self.redis_client = redis_client
        
        # Default limits
        self.ip_limits = ip_limits or {"default": 100}
        self.user_limits = user_limits or {"default": 200}
        self.endpoint_limits = endpoint_limits or {
            "/api/v1/": 1000,
            "/api/v1/agents": 100,
            "/api/v1/workflows": 200,
        }
        
        # Create limiters for each level
        self.ip_limiter = SlidingWindowRateLimiter(
            redis_client, window_seconds=60, max_requests=self.ip_limits["default"]
        )
        self.user_limiter = SlidingWindowRateLimiter(
            redis_client, window_seconds=60, max_requests=self.user_limits["default"]
        )
        self.endpoint_limiters = {
            endpoint: SlidingWindowRateLimiter(
                redis_client, window_seconds=60, max_requests=max_req
            )
            for endpoint, max_req in self.endpoint_limits.items()
        }
    
    async def check_rate_limit(
        self,
        ip_address: str,
        user_id: Optional[str] = None,
        endpoint: str = "/",
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check rate limits at all levels.
        
        Args:
            ip_address: Client IP address
            user_id: User ID (if authenticated)
            endpoint: API endpoint
        
        Returns:
            (is_allowed, metadata) tuple
        """
        results = {}
        
        # Check IP-level limit
        ip_allowed, ip_meta = await self.ip_limiter.is_allowed(f"ip:{ip_address}")
        results["ip"] = ip_meta
        
        if not ip_allowed:
            return False, {
                "allowed": False,
                "reason": "ip_rate_limit_exceeded",
                "details": results,
            }
        
        # Check user-level limit (if authenticated)
        if user_id:
            user_allowed, user_meta = await self.user_limiter.is_allowed(f"user:{user_id}")
            results["user"] = user_meta
            
            if not user_allowed:
                return False, {
                    "allowed": False,
                    "reason": "user_rate_limit_exceeded",
                    "details": results,
                }
        
        # Check endpoint-level limit
        endpoint_limiter = None
        for ep_pattern, limiter in self.endpoint_limiters.items():
            if endpoint.startswith(ep_pattern):
                endpoint_limiter = limiter
                break
        
        if endpoint_limiter:
            endpoint_allowed, endpoint_meta = await endpoint_limiter.is_allowed(
                f"endpoint:{endpoint}"
            )
            results["endpoint"] = endpoint_meta
            
            if not endpoint_allowed:
                return False, {
                    "allowed": False,
                    "reason": "endpoint_rate_limit_exceeded",
                    "details": results,
                }
        
        return True, {
            "allowed": True,
            "details": results,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: MultiLevelRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        ip_address = request.client.host if request.client else "unknown"
        
        # Get user ID (if authenticated)
        user_id = request.headers.get("X-User-ID") or request.state.get("user_id")
        
        # Get endpoint
        endpoint = request.url.path
        
        # Check rate limit
        is_allowed, metadata = await self.rate_limiter.check_rate_limit(
            ip_address, user_id, endpoint
        )
        
        if not is_allowed:
            retry_after = metadata.get("details", {}).get("ip", {}).get("retry_after", 60)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "reason": metadata.get("reason"),
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        # Add rate limit headers
        response = await call_next(request)
        
        # Add rate limit info to headers
        if "ip" in metadata.get("details", {}):
            ip_meta = metadata["details"]["ip"]
            response.headers["X-RateLimit-Limit"] = str(ip_meta.get("requests_current", 0))
            response.headers["X-RateLimit-Remaining"] = str(
                ip_meta.get("requests_remaining", 0)
            )
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time()) + ip_meta.get("window_seconds", 60)
            )
        
        return response

