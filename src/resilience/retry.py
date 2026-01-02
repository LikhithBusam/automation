"""
Retry Logic with Idempotency
- Idempotency keys
- Exponential backoff
- Jitter to prevent thundering herd
- Maximum retry limits
"""

import asyncio
import logging
import random
import time
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Optional, Dict, Set
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_range: float = 0.1  # 10% jitter
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()
    idempotency_enabled: bool = True
    idempotency_ttl_seconds: int = 3600  # 1 hour


class IdempotencyStore:
    """Stores idempotency keys and results"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize idempotency store"""
        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds
    
    def _generate_key(self, func: Callable, args: tuple, kwargs: dict, idempotency_key: Optional[str]) -> str:
        """Generate idempotency key"""
        if idempotency_key:
            return idempotency_key
        
        # Generate from function signature
        key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result for idempotency key"""
        if key not in self._store:
            return None
        
        entry = self._store[key]
        
        # Check TTL
        if time.time() - entry["timestamp"] > self._ttl_seconds:
            del self._store[key]
            return None
        
        return entry["result"]
    
    def set(self, key: str, result: Any):
        """Store result for idempotency key"""
        self._store[key] = {
            "result": result,
            "timestamp": time.time()
        }
    
    def cleanup(self):
        """Cleanup expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._store.items()
            if current_time - entry["timestamp"] > self._ttl_seconds
        ]
        for key in expired_keys:
            del self._store[key]


class RetryExecutor:
    """Executes functions with retry logic"""
    
    def __init__(self, policy: RetryPolicy):
        """Initialize retry executor"""
        self.policy = policy
        self.idempotency_store = IdempotencyStore(policy.idempotency_ttl_seconds) if policy.idempotency_enabled else None
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self.policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.policy.initial_delay_seconds * (self.policy.multiplier ** (attempt - 1))
        elif self.policy.strategy == RetryStrategy.LINEAR:
            delay = self.policy.initial_delay_seconds * attempt
        else:  # FIXED
            delay = self.policy.initial_delay_seconds
        
        # Cap at max delay
        delay = min(delay, self.policy.max_delay_seconds)
        
        # Add jitter
        if self.policy.jitter:
            jitter_amount = delay * self.policy.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)
        
        return delay
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if should retry after exception"""
        # Check max attempts
        if attempt >= self.policy.max_attempts:
            return False
        
        # Check if exception is retryable
        if self.policy.non_retryable_exceptions and isinstance(exception, self.policy.non_retryable_exceptions):
            return False
        
        # Check if exception is in retryable list
        if self.policy.retryable_exceptions:
            return isinstance(exception, self.policy.retryable_exceptions)
        
        return True
    
    async def execute(
        self,
        func: Callable,
        *args,
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            idempotency_key: Optional idempotency key
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: Last exception if all retries fail
        """
        # Check idempotency
        if self.idempotency_store:
            store_key = self.idempotency_store._generate_key(func, args, kwargs, idempotency_key)
            cached_result = self.idempotency_store.get(store_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for idempotency key: {store_key[:16]}...")
                return cached_result
        
        last_exception = None
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                
                # Store result for idempotency
                if self.idempotency_store:
                    store_key = self.idempotency_store._generate_key(func, args, kwargs, idempotency_key)
                    self.idempotency_store.set(store_key, result)
                
                if attempt > 1:
                    logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, attempt):
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt} "
                        f"and will not retry: {e}"
                    )
                    raise
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt}/{self.policy.max_attempts}: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(
            f"Function {func.__name__} failed after {self.policy.max_attempts} attempts"
        )
        raise last_exception


def retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    max_delay_seconds: float = 60.0,
    multiplier: float = 2.0,
    jitter: bool = True,
    idempotency_key: Optional[str] = None
):
    """
    Decorator for retry logic.
    
    Usage:
        @retry(max_attempts=5, initial_delay_seconds=2.0)
        async def my_function():
            ...
    """
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            initial_delay_seconds=initial_delay_seconds,
            max_delay_seconds=max_delay_seconds,
            multiplier=multiplier,
            jitter=jitter
        )
    
    executor = RetryExecutor(policy)
    
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Use provided idempotency key or from kwargs
            key = idempotency_key or kwargs.pop("idempotency_key", None)
            return await executor.execute(func, *args, idempotency_key=key, **kwargs)
        
        return wrapper
    
    return decorator

