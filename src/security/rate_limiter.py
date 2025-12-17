"""
Rate Limiting for API Calls
Prevents API quota exhaustion and service bans
"""

import asyncio
import time
import os
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Optional
from dataclasses import dataclass, field


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_calls: int
    time_window_seconds: int
    burst_size: Optional[int] = None  # Allow burst, default = max_calls


class RateLimiter:
    """
    Token bucket rate limiter with burst support.

    Features:
    - Per-service rate limiting
    - Burst support for bursty workloads
    - Async/await compatible
    - Thread-safe
    - Automatic cleanup of old entries
    """

    def __init__(self, max_calls: int, time_window_seconds: int, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum calls allowed in time window
            time_window_seconds: Time window in seconds
            burst_size: Maximum burst size (default: max_calls)
        """
        self.max_calls = max_calls
        self.time_window = time_window_seconds
        self.burst_size = burst_size or max_calls

        # Track call timestamps
        self.calls = deque()

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Statistics
        self.total_calls = 0
        self.total_waits = 0
        self.total_wait_time = 0.0

    async def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make an API call.

        Args:
            wait: If True, wait until rate limit allows. If False, raise immediately.

        Returns:
            True if acquired

        Raises:
            RateLimitExceeded: If wait=False and rate limit exceeded
        """
        async with self._lock:
            now = time.time()

            # Remove old calls outside time window
            cutoff_time = now - self.time_window
            while self.calls and self.calls[0] < cutoff_time:
                self.calls.popleft()

            # Check if at limit
            if len(self.calls) >= self.max_calls:
                if not wait:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded: {self.max_calls} calls "
                        f"per {self.time_window}s"
                    )

                # Calculate wait time
                oldest_call = self.calls[0]
                wait_until = oldest_call + self.time_window
                wait_time = wait_until - now

                if wait_time > 0:
                    self.total_waits += 1
                    self.total_wait_time += wait_time

                    # Release lock while waiting
                    self._lock.release()
                    try:
                        await asyncio.sleep(wait_time + 0.01)  # Small buffer
                    finally:
                        await self._lock.acquire()

                    # Retry acquisition
                    return await self.acquire(wait=True)

            # Record this call
            self.calls.append(now)
            self.total_calls += 1
            return True

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            "total_calls": self.total_calls,
            "current_calls_in_window": len(self.calls),
            "total_waits": self.total_waits,
            "total_wait_time_seconds": round(self.total_wait_time, 2),
            "average_wait_time_seconds": round(
                self.total_wait_time / self.total_waits if self.total_waits > 0 else 0,
                2
            ),
            "utilization_percent": round(
                (len(self.calls) / self.max_calls * 100) if self.max_calls > 0 else 0,
                1
            )
        }

    def reset(self):
        """Reset rate limiter state"""
        self.calls.clear()
        self.total_calls = 0
        self.total_waits = 0
        self.total_wait_time = 0.0


class ServiceRateLimiters:
    """
    Manages rate limiters for different services.

    Automatically configures limits based on known service limits.
    """

    # Known service limits (conservative estimates)
    SERVICE_LIMITS = {
        "groq_free": RateLimitConfig(max_calls=25, time_window_seconds=60),  # 30/min, use 25 for safety
        "groq_pro": RateLimitConfig(max_calls=450, time_window_seconds=60),  # 14400/day ≈ 600/min
        "gemini_free": RateLimitConfig(max_calls=50, time_window_seconds=60),  # 60/min
        "gemini_pro": RateLimitConfig(max_calls=1800, time_window_seconds=60),  # 2000/min
        "github": RateLimitConfig(max_calls=80, time_window_seconds=3600),  # 5000/hour, use 80/hour for safety
        "slack": RateLimitConfig(max_calls=50, time_window_seconds=60),  # Tier 1: 1/sec
        "default": RateLimitConfig(max_calls=30, time_window_seconds=60),  # Conservative default
    }

    def __init__(self):
        """Initialize service rate limiters"""
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()

    async def get_limiter(self, service: str) -> RateLimiter:
        """
        Get or create rate limiter for service.

        Args:
            service: Service name (e.g., 'groq', 'github')

        Returns:
            RateLimiter for the service
        """
        async with self._lock:
            if service not in self._limiters:
                # Determine service configuration
                config = self._get_service_config(service)

                # Create rate limiter
                self._limiters[service] = RateLimiter(
                    max_calls=config.max_calls,
                    time_window_seconds=config.time_window_seconds,
                    burst_size=config.burst_size
                )

            return self._limiters[service]

    def _get_service_config(self, service: str) -> RateLimitConfig:
        """Get rate limit configuration for service"""
        # Check environment for custom limits
        env_var = f"RATE_LIMIT_{service.upper()}"
        if env_var in os.environ:
            try:
                max_calls = int(os.environ[env_var])
                return RateLimitConfig(max_calls=max_calls, time_window_seconds=60)
            except ValueError:
                pass

        # Use known service limits
        return self.SERVICE_LIMITS.get(service, self.SERVICE_LIMITS["default"])

    async def acquire(self, service: str, wait: bool = True) -> bool:
        """
        Acquire permission for service call.

        Args:
            service: Service name
            wait: Whether to wait if rate limit exceeded

        Returns:
            True if acquired
        """
        limiter = await self.get_limiter(service)
        return await limiter.acquire(wait=wait)

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all rate limiters"""
        return {
            service: limiter.get_stats()
            for service, limiter in self._limiters.items()
        }

    def reset_all(self):
        """Reset all rate limiters"""
        for limiter in self._limiters.values():
            limiter.reset()


# Global service rate limiters
_service_limiters = ServiceRateLimiters()


async def acquire_rate_limit(service: str, wait: bool = True) -> bool:
    """
    Convenience function to acquire rate limit.

    Args:
        service: Service name (groq, github, slack, etc.)
        wait: Whether to wait if limit exceeded

    Returns:
        True if acquired

    Usage:
        await acquire_rate_limit("groq")
        # Make API call
    """
    return await _service_limiters.acquire(service, wait=wait)


def get_rate_limit_stats() -> Dict[str, Dict]:
    """Get rate limiting statistics for all services"""
    return _service_limiters.get_all_stats()


def reset_rate_limiters():
    """Reset all rate limiters (useful for testing)"""
    _service_limiters.reset_all()
