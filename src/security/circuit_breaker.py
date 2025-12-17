"""
Circuit Breaker Pattern for Resilience
Prevents cascading failures in distributed systems
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: int = 60   # Time before attempting reset
    half_open_max_calls: int = 1  # Max calls in half-open state


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    time_in_open_state: float = 0.0
    state_transitions: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject all requests
    - HALF_OPEN: Testing if service recovered, allow limited requests

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

        async with breaker:
            result = await some_api_call()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 1,
        excluded_exceptions: tuple = None
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening
            success_threshold: Number of successes to close from half-open
            timeout_seconds: Seconds before attempting reset
            half_open_max_calls: Max calls allowed in half-open state
            excluded_exceptions: Exceptions that don't trigger circuit breaker
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout_seconds=timeout_seconds,
            half_open_max_calls=half_open_max_calls
        )

        self.excluded_exceptions = excluded_exceptions or tuple()

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.open_state_start_time: Optional[float] = None

        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_transitions = 0
        self.half_open_calls = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self.total_calls += 1

            # Check state and transition if needed
            await self._check_state()

            # If open, reject immediately
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Failures: {self.failure_count}/{self.config.failure_threshold}. "
                    f"Retry after {self._time_until_half_open():.1f}s"
                )

            # If half-open, limit concurrent calls
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is HALF_OPEN and at capacity"
                    )
                self.half_open_calls += 1

        # Execute function (outside lock to avoid blocking)
        try:
            result = await func(*args, **kwargs)

            # Success
            async with self._lock:
                await self._on_success()

            return result

        except Exception as e:
            # Check if exception should be excluded
            if isinstance(e, self.excluded_exceptions):
                raise

            # Failure
            async with self._lock:
                await self._on_failure()

            raise

        finally:
            # Decrement half-open calls
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self.half_open_calls = max(0, self.half_open_calls - 1)

    async def _check_state(self):
        """Check and update circuit breaker state"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to_half_open()

    async def _on_success(self):
        """Handle successful call"""
        self.total_successes += 1
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            # Close circuit if enough successes
            if self.success_count >= self.config.success_threshold:
                await self._transition_to_closed()

    async def _on_failure(self):
        """Handle failed call"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        # Open circuit if too many failures
        if self.failure_count >= self.config.failure_threshold:
            await self._transition_to_open()

    async def _transition_to_open(self):
        """Transition to OPEN state"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.open_state_start_time = time.time()
            self.state_transitions += 1

    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_calls = 0
        self.state_transitions += 1

    async def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_transitions += 1

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset from OPEN state"""
        if not self.last_failure_time:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout_seconds

    def _time_until_half_open(self) -> float:
        """Calculate time until half-open state"""
        if not self.last_failure_time:
            return 0.0

        elapsed = time.time() - self.last_failure_time
        remaining = self.config.timeout_seconds - elapsed
        return max(0.0, remaining)

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        time_in_open = 0.0
        if self.state == CircuitState.OPEN and self.open_state_start_time:
            time_in_open = time.time() - self.open_state_start_time

        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            total_calls=self.total_calls,
            total_failures=self.total_failures,
            total_successes=self.total_successes,
            last_failure_time=datetime.fromtimestamp(self.last_failure_time) if self.last_failure_time else None,
            time_in_open_state=time_in_open,
            state_transitions=self.state_transitions
        )

    def reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.open_state_start_time = None
        self.half_open_calls = 0

    async def __aenter__(self):
        """Async context manager entry"""
        async with self._lock:
            self.total_calls += 1
            await self._check_state()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry after {self._time_until_half_open():.1f}s"
                )

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError("Circuit breaker is HALF_OPEN and at capacity")
                self.half_open_calls += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        async with self._lock:
            if exc_type is None:
                # Success
                await self._on_success()
            elif not isinstance(exc_val, self.excluded_exceptions):
                # Failure
                await self._on_failure()

            # Decrement half-open calls
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls = max(0, self.half_open_calls - 1)

        return False  # Don't suppress exceptions


class ServiceCircuitBreakers:
    """Manages circuit breakers for different services"""

    def __init__(self):
        """Initialize service circuit breakers"""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self,
        service: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60
    ) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        async with self._lock:
            if service not in self._breakers:
                self._breakers[service] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    timeout_seconds=timeout_seconds
                )
            return self._breakers[service]

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers"""
        return {
            service: breaker.get_stats()
            for service, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()


# Global service circuit breakers
_service_breakers = ServiceCircuitBreakers()


async def get_circuit_breaker(service: str, **kwargs) -> CircuitBreaker:
    """Get circuit breaker for service"""
    return await _service_breakers.get_breaker(service, **kwargs)


def get_circuit_breaker_stats() -> dict[str, CircuitBreakerStats]:
    """Get all circuit breaker statistics"""
    return _service_breakers.get_all_stats()
