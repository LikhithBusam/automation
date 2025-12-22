"""
Base MCP Tool Class
Provides common functionality for all MCP tool wrappers

Features:
- Retry logic with exponential backoff (3 attempts, 1s/2s/4s delays)
- Token bucket rate limiting (configurable per tool)
- TTL-based caching with expiry timestamps
- Statistics tracking: total_calls, successful_calls, failed_calls, cache_hits
- Abstract methods: execute(), validate_params(), handle_error()
- Async context manager support
- Comprehensive logging
"""

from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod
import logging
import asyncio
import time
import hashlib
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager


# =============================================================================
# Exception Classes (Importing from standardized hierarchy)
# =============================================================================

from src.exceptions import (
    MCPToolError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPAuthenticationError,
    MCPOperationError,
    RateLimitError as MCPRateLimitError,
    ValidationError as MCPValidationError
)


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================

@dataclass
class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows bursts up to bucket capacity while maintaining
    average rate over time.
    """
    capacity: float  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    
    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.time()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens. Returns True if successful.
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait_time(self, tokens: float = 1.0) -> float:
        """Calculate wait time needed for tokens to be available"""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate
    
    async def acquire(self, tokens: float = 1.0):
        """Async acquire tokens, waiting if necessary"""
        wait = self.wait_time(tokens)
        if wait > 0:
            await asyncio.sleep(wait)
        self.consume(tokens)


# =============================================================================
# TTL Cache with Expiry Timestamps
# =============================================================================

@dataclass
class CacheEntry:
    """Cache entry with expiry timestamp"""
    data: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = field(init=False)
    
    def __post_init__(self):
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def touch(self):
        """Update access time and count"""
        self.access_count += 1
        self.last_accessed = time.time()


class TTLCache:
    """
    TTL-based cache with expiry timestamps.
    
    Features:
    - Automatic expiry based on TTL
    - Max size limit with LRU eviction
    - Statistics tracking
    """
    
    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def _generate_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key from operation and params"""
        key_data = json.dumps({"op": operation, "params": params}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get value from cache if not expired"""
        key = self._generate_key(operation, params)
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None
        
        entry.touch()
        self._stats["hits"] += 1
        return entry.data
    
    def set(self, operation: str, params: Dict[str, Any], data: Any, ttl: float = None):
        """Store value in cache with TTL"""
        # Enforce max size with LRU eviction
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        key = self._generate_key(operation, params)
        now = time.time()
        ttl = ttl or self.default_ttl
        
        self._cache[key] = CacheEntry(
            data=data,
            created_at=now,
            expires_at=now + ttl
        )
    
    def _evict_lru(self, count: int = 100):
        """Evict least recently used entries"""
        if not self._cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest entries
        for key, _ in sorted_entries[:count]:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self._stats,
            "size": len(self._cache),
            "hit_rate": f"{hit_rate:.1f}%"
        }


# =============================================================================
# Statistics Tracker
# =============================================================================

@dataclass
class ToolStatistics:
    """Track tool usage statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_uses: int = 0
    total_latency_ms: float = 0.0
    retry_count: int = 0
    
    # Per-operation stats
    operation_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    max_errors: int = 100
    
    def record_call(self, operation: str, success: bool, latency_ms: float):
        """Record a tool call"""
        self.total_calls += 1
        self.total_latency_ms += latency_ms
        
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        # Per-operation tracking
        if operation not in self.operation_stats:
            self.operation_stats[operation] = {"calls": 0, "success": 0, "failed": 0}
        
        self.operation_stats[operation]["calls"] += 1
        if success:
            self.operation_stats[operation]["success"] += 1
        else:
            self.operation_stats[operation]["failed"] += 1
    
    def record_error(self, operation: str, error: Exception):
        """Record an error"""
        if len(self.errors) >= self.max_errors:
            self.errors.pop(0)
        
        self.errors.append({
            "operation": operation,
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        })
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    def record_retry(self):
        self.retry_count += 1
    
    def record_fallback(self):
        self.fallback_uses += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        success_rate = (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0
        avg_latency = (self.total_latency_ms / self.total_calls) if self.total_calls > 0 else 0
        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": f"{success_rate:.1f}%",
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "fallback_uses": self.fallback_uses,
            "retry_count": self.retry_count,
            "avg_latency_ms": f"{avg_latency:.2f}",
            "operation_stats": self.operation_stats,
            "recent_errors": self.errors[-5:]  # Last 5 errors
        }


# =============================================================================
# Exponential Backoff Retry
# =============================================================================

class ExponentialBackoff:
    """
    Exponential backoff retry logic.
    
    Delays: 1s, 2s, 4s (configurable)
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt (0-indexed)"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def execute(
        self,
        func: Callable,
        *args,
        retryable_exceptions: tuple = (MCPConnectionError, MCPTimeoutError),
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry.
        
        Args:
            func: Async function to execute
            retryable_exceptions: Exceptions that trigger retry
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self.get_delay(attempt)
                    await asyncio.sleep(delay)
                continue
            except Exception as e:
                # Non-retryable exception
                raise
        
        raise last_exception


# =============================================================================
# Base MCP Tool (Abstract)
# =============================================================================

class BaseMCPTool(ABC):
    """
    Abstract base class for MCP tool wrappers.
    
    Provides:
    - Retry logic with exponential backoff (3 attempts, 1s/2s/4s delays)
    - Token bucket rate limiting (configurable per tool)
    - TTL-based caching with expiry timestamps
    - Statistics tracking
    - Async context manager support
    - Comprehensive logging
    """

    def __init__(
        self,
        name: str,
        server_url: str,
        config: Dict[str, Any],
        fallback_handler: Optional[Callable] = None
    ):
        self.name = name
        self.server_url = server_url
        self.config = config
        self.fallback_handler = fallback_handler
        self.logger = logging.getLogger(f"mcp.{name}")
        
        # Connection state
        self._connected = False
        self._connection_lock = asyncio.Lock()

        # Rate limiting with token bucket
        rate_per_minute = config.get("rate_limit_minute", 60)
        rate_per_hour = config.get("rate_limit_hour", 1000)
        self.rate_limiter_minute = TokenBucket(
            capacity=rate_per_minute,
            refill_rate=rate_per_minute / 60.0  # tokens per second
        )
        self.rate_limiter_hour = TokenBucket(
            capacity=rate_per_hour,
            refill_rate=rate_per_hour / 3600.0
        )

        # TTL-based caching
        cache_ttl = config.get("cache_ttl", 300)  # 5 minutes default
        cache_enabled = config.get("cache_enabled", True)
        self.cache = TTLCache(default_ttl=cache_ttl, max_size=1000)
        self.cache_enabled = cache_enabled

        # Retry configuration (1s, 2s, 4s delays)
        self.retry_handler = ExponentialBackoff(
            max_attempts=config.get("retry_attempts", 3),
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        self.timeout = config.get("timeout", 30)

        # Statistics tracking
        self.stats = ToolStatistics()
        
        # Legacy stats compatibility
        self._legacy_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_uses": 0
        }

    # =========================================================================
    # Async Context Manager Support
    # =========================================================================
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        return False
    
    async def connect(self):
        """Establish connection to MCP server"""
        async with self._connection_lock:
            if not self._connected:
                self.logger.info(f"Connecting to {self.server_url}")
                # Subclasses can override _do_connect for custom connection logic
                await self._do_connect()
                self._connected = True
                self.logger.info(f"Connected to {self.name} MCP server")
    
    async def disconnect(self):
        """Close connection to MCP server"""
        async with self._connection_lock:
            if self._connected:
                await self._do_disconnect()
                self._connected = False
                self.logger.info(f"Disconnected from {self.name} MCP server")
    
    async def _do_connect(self):
        """Override in subclasses for custom connection logic"""
        pass
    
    async def _do_disconnect(self):
        """Override in subclasses for custom disconnection logic"""
        pass

    # =========================================================================
    # Main Execute Method
    # =========================================================================

    async def execute(
        self,
        operation: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> Any:
        """
        Execute an operation with error handling and retry logic.
        
        Args:
            operation: Name of the operation to execute
            params: Parameters for the operation
            use_cache: Whether to use cache for this operation
            
        Returns:
            Operation result
            
        Raises:
            MCPToolError: If operation fails after retries
        """
        start_time = time.time()
        self._legacy_stats["total_requests"] += 1

        try:
            # Check cache first
            if use_cache and self.cache_enabled:
                cached_result = self.cache.get(operation, params)
                if cached_result is not None:
                    self.stats.record_cache_hit()
                    self._legacy_stats["cache_hits"] += 1
                    self.logger.debug(f"Cache hit for {operation}")
                    return cached_result
                self.stats.record_cache_miss()
                self._legacy_stats["cache_misses"] += 1

            # Check rate limits (token bucket)
            await self._check_rate_limit()

            # Validate parameters
            self.validate_params(operation, params)

            # Execute operation with exponential backoff retry
            result = await self._execute_with_retry(operation, params)

            # Cache result for read operations
            if use_cache and self.cache_enabled and self._is_cacheable_operation(operation):
                ttl = self._get_cache_ttl(operation)
                self.cache.set(operation, params, result, ttl)

            # Record success
            latency_ms = (time.time() - start_time) * 1000
            self.stats.record_call(operation, success=True, latency_ms=latency_ms)
            self._legacy_stats["successful_requests"] += 1
            self.logger.info(f"Successfully executed {operation} in {latency_ms:.2f}ms")

            return result

        except Exception as e:
            # Record failure
            latency_ms = (time.time() - start_time) * 1000
            self.stats.record_call(operation, success=False, latency_ms=latency_ms)
            self.stats.record_error(operation, e)
            self._legacy_stats["failed_requests"] += 1
            self.logger.error(f"Failed to execute {operation}: {str(e)}")

            # Handle error (can be overridden by subclasses)
            handled_result = await self.handle_error(operation, params, e)
            if handled_result is not None:
                return handled_result

            # Try fallback if available
            if self.fallback_handler:
                self.logger.info(f"Attempting fallback for {operation}")
                try:
                    result = await self.fallback_handler(operation, params)
                    self.stats.record_fallback()
                    self._legacy_stats["fallback_uses"] += 1
                    return result
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {str(fallback_error)}")

            raise MCPToolError(
                f"Operation {operation} failed: {str(e)}",
                operation=operation,
                details={"params": params, "error_type": type(e).__name__}
            ) from e

    async def _execute_with_retry(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute operation with exponential backoff retry (1s, 2s, 4s)"""
        
        async def _do_execute():
            try:
                result = await asyncio.wait_for(
                    self._execute_operation(operation, params),
                    timeout=self.timeout
                )
                return result
            except asyncio.TimeoutError:
                raise MCPTimeoutError(
                    f"Operation {operation} timed out after {self.timeout}s",
                    operation=operation
                )
            except Exception as e:
                # Wrap in appropriate exception type
                error_msg = str(e).lower()
                if "connection" in error_msg or "connect" in error_msg:
                    raise MCPConnectionError(str(e), operation=operation)
                elif "rate limit" in error_msg:
                    raise MCPRateLimitError(str(e), operation=operation)
                elif "auth" in error_msg or "unauthorized" in error_msg:
                    raise MCPAuthenticationError(str(e), operation=operation)
                raise
        
        # Use exponential backoff retry
        try:
            return await self.retry_handler.execute(
                _do_execute,
                retryable_exceptions=(MCPConnectionError, MCPTimeoutError)
            )
        except (MCPConnectionError, MCPTimeoutError):
            self.stats.record_retry()
            raise

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    async def _execute_operation(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Execute the actual operation (implemented by subclasses).

        Args:
            operation: Operation name
            params: Operation parameters

        Returns:
            Operation result
        """
        pass

    async def call_mcp_server(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Alias for _execute_operation for backward compatibility.

        This method allows tools to use call_mcp_server() instead of
        _execute_operation() for better clarity.

        Args:
            operation: Operation name
            params: Operation parameters

        Returns:
            Operation result
        """
        return await self._execute_operation(operation, params)

    @abstractmethod
    def validate_params(self, operation: str, params: Dict[str, Any]):
        """
        Validate operation parameters (must be implemented by subclasses).
        
        Args:
            operation: Operation name
            params: Parameters to validate
            
        Raises:
            MCPValidationError: If validation fails
        """
        pass

    async def handle_error(
        self,
        operation: str,
        params: Dict[str, Any],
        error: Exception
    ) -> Optional[Any]:
        """
        Handle errors (can be overridden by subclasses).
        
        Args:
            operation: Failed operation name
            params: Operation parameters
            error: The exception that occurred
            
        Returns:
            Optional recovery result, or None to proceed with fallback/raise
        """
        return None

    # =========================================================================
    # Rate Limiting (Token Bucket)
    # =========================================================================

    async def _check_rate_limit(self):
        """Check and enforce rate limits using token bucket algorithm"""
        # Check minute bucket
        if not self.rate_limiter_minute.consume():
            wait_time = self.rate_limiter_minute.wait_time()
            self.logger.warning(f"Rate limit reached (per-minute), waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            self.rate_limiter_minute.consume()
        
        # Check hour bucket
        if not self.rate_limiter_hour.consume():
            raise MCPRateLimitError(
                "Hourly rate limit exceeded",
                operation="rate_check"
            )

    # =========================================================================
    # Caching Helpers
    # =========================================================================

    def _is_cacheable_operation(self, operation: str) -> bool:
        """Determine if an operation should be cached (override in subclasses)"""
        # By default, cache read-like operations
        read_operations = {"get", "read", "list", "search", "retrieve", "fetch"}
        return any(op in operation.lower() for op in read_operations)

    def _get_cache_ttl(self, operation: str) -> float:
        """Get TTL for specific operation (override in subclasses)"""
        return self.cache.default_ttl

    # =========================================================================
    # Statistics and Monitoring
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get tool statistics"""
        return self.stats.to_dict()

    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        self.logger.info("Cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """Check if the MCP server is healthy"""
        try:
            start_time = time.time()
            await self._execute_operation("health_check", {})
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "server": self.server_url,
                "latency_ms": f"{latency_ms:.2f}",
                "connected": self._connected,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "server": self.server_url,
                "error": str(e),
                "connected": self._connected,
                "timestamp": datetime.now().isoformat()
            }

    # =========================================================================
    # Deprecated Methods (for backward compatibility)
    # =========================================================================

    def _validate_params(self, operation: str, params: Dict[str, Any]):
        """Deprecated: Use validate_params instead"""
        return self.validate_params(operation, params)

    def _get_from_cache(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """Deprecated: Use self.cache.get instead"""
        return self.cache.get(operation, params)

    def _store_in_cache(
        self,
        operation: str,
        params: Dict[str, Any],
        result: Any
    ):
        """Deprecated: Use self.cache.set instead"""
        self.cache.set(operation, params, result)

    def _get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Deprecated: Cache key generation moved to TTLCache"""
        key_data = json.dumps({"op": operation, "params": params}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
