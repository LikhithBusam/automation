"""
Enhanced Circuit Breaker Implementation
- Configurable failure thresholds per service
- Exponential backoff strategies
- Half-open state with gradual traffic increase
- Metrics and monitoring integration
"""

import asyncio
import logging
import time
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Dict
from collections import deque

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


@dataclass
class CircuitBreakerConfig:
    """Enhanced circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 1
    excluded_exceptions: tuple = field(default_factory=tuple)
    
    # Exponential backoff configuration
    use_exponential_backoff: bool = True
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 300.0
    backoff_multiplier: float = 2.0
    
    # Gradual traffic increase in half-open
    gradual_traffic_increase: bool = True
    initial_traffic_percentage: float = 0.1  # Start with 10% traffic
    traffic_increase_rate: float = 0.1  # Increase by 10% per success
    max_traffic_percentage: float = 1.0  # Max 100% traffic
    
    # Metrics
    enable_metrics: bool = True
    service_name: str = "unknown"


class EnhancedCircuitBreaker:
    """
    Enhanced circuit breaker with exponential backoff and gradual traffic increase.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize enhanced circuit breaker"""
        self.config = config
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.open_state_start_time: Optional[float] = None
        self.consecutive_failures = 0
        
        # Exponential backoff
        self.current_backoff_seconds = config.base_backoff_seconds
        self.backoff_attempts = 0
        
        # Gradual traffic increase
        self.current_traffic_percentage = config.initial_traffic_percentage if config.gradual_traffic_increase else 1.0
        self.half_open_calls = 0
        self.half_open_successes = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_transitions = 0
        self.failure_history = deque(maxlen=100)  # Track recent failures
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Metrics
        if config.enable_metrics:
            self._init_metrics()
        else:
            self._metrics = None
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        service = self.config.service_name
        self._metrics = {
            "calls_total": Counter(
                f"circuit_breaker_calls_total",
                "Total circuit breaker calls",
                ["service", "state"]
            ),
            "failures_total": Counter(
                f"circuit_breaker_failures_total",
                "Total circuit breaker failures",
                ["service"]
            ),
            "state": Gauge(
                f"circuit_breaker_state",
                "Circuit breaker state (0=closed, 1=open, 2=half_open)",
                ["service"]
            ),
            "failure_count": Gauge(
                f"circuit_breaker_failure_count",
                "Current failure count",
                ["service"]
            ),
            "backoff_seconds": Gauge(
                f"circuit_breaker_backoff_seconds",
                "Current backoff time in seconds",
                ["service"]
            ),
            "traffic_percentage": Gauge(
                f"circuit_breaker_traffic_percentage",
                "Current traffic percentage in half-open state",
                ["service"]
            ),
        }
    
    def _update_metrics(self):
        """Update Prometheus metrics"""
        if not self._metrics:
            return
        
        service = self.config.service_name
        state_value = {"closed": 0, "open": 1, "half_open": 2}[self.state.value]
        
        self._metrics["state"].labels(service=service).set(state_value)
        self._metrics["failure_count"].labels(service=service).set(self.failure_count)
        self._metrics["backoff_seconds"].labels(service=service).set(self.current_backoff_seconds)
        self._metrics["traffic_percentage"].labels(service=service).set(self.current_traffic_percentage)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            self.total_calls += 1
            await self._check_state()
            
            # Update metrics
            if self._metrics:
                self._metrics["calls_total"].labels(
                    service=self.config.service_name,
                    state=self.state.value
                ).inc()
            
            # If open, reject immediately
            if self.state == CircuitState.OPEN:
                self._update_metrics()
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Failures: {self.failure_count}/{self.config.failure_threshold}. "
                    f"Retry after {self._time_until_half_open():.1f}s"
                )
            
            # If half-open, check traffic percentage
            if self.state == CircuitState.HALF_OPEN:
                # Gradual traffic increase: allow based on percentage
                import random
                if random.random() > self.current_traffic_percentage:
                    self._update_metrics()
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is HALF_OPEN. "
                        f"Traffic limited to {self.current_traffic_percentage*100:.1f}%"
                    )
                
                if self.half_open_calls >= self.config.half_open_max_calls:
                    self._update_metrics()
                    raise CircuitBreakerOpenError("Circuit breaker is HALF_OPEN and at capacity")
                
                self.half_open_calls += 1
        
        # Execute function (outside lock)
        try:
            result = await func(*args, **kwargs)
            
            # Success
            async with self._lock:
                await self._on_success()
                self._update_metrics()
            
            return result
        
        except Exception as e:
            # Check if exception should be excluded
            if isinstance(e, self.config.excluded_exceptions):
                raise
            
            # Failure
            async with self._lock:
                await self._on_failure()
                self._update_metrics()
            
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
        self.consecutive_failures = 0
        
        # Reset backoff on success
        if self.config.use_exponential_backoff:
            self.current_backoff_seconds = self.config.base_backoff_seconds
            self.backoff_attempts = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_successes += 1
            
            # Gradual traffic increase
            if self.config.gradual_traffic_increase:
                self.current_traffic_percentage = min(
                    self.config.max_traffic_percentage,
                    self.current_traffic_percentage + self.config.traffic_increase_rate
                )
            
            # Close circuit if enough successes
            if self.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
    
    async def _on_failure(self):
        """Handle failed call"""
        self.total_failures += 1
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        self.failure_history.append(time.time())
        
        if self._metrics:
            self._metrics["failures_total"].labels(service=self.config.service_name).inc()
        
        # Update exponential backoff
        if self.config.use_exponential_backoff:
            self.backoff_attempts += 1
            self.current_backoff_seconds = min(
                self.config.max_backoff_seconds,
                self.config.base_backoff_seconds * (self.config.backoff_multiplier ** self.backoff_attempts)
            )
        
        # Open circuit if too many failures
        if self.failure_count >= self.config.failure_threshold:
            await self._transition_to_open()
        
        # If in half-open and failed, reset traffic percentage
        if self.state == CircuitState.HALF_OPEN:
            if self.config.gradual_traffic_increase:
                self.current_traffic_percentage = self.config.initial_traffic_percentage
            self.half_open_successes = 0
    
    async def _transition_to_open(self):
        """Transition to OPEN state"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.open_state_start_time = time.time()
            self.state_transitions += 1
            self.success_count = 0
            
            # Reset traffic percentage
            if self.config.gradual_traffic_increase:
                self.current_traffic_percentage = self.config.initial_traffic_percentage
            
            logger.warning(
                f"Circuit breaker OPEN for {self.config.service_name}. "
                f"Failures: {self.failure_count}"
            )
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_calls = 0
        self.half_open_successes = 0
        self.state_transitions += 1
        
        # Reset traffic percentage
        if self.config.gradual_traffic_increase:
            self.current_traffic_percentage = self.config.initial_traffic_percentage
        
        logger.info(
            f"Circuit breaker HALF_OPEN for {self.config.service_name}. "
            f"Testing recovery with {self.current_traffic_percentage*100:.1f}% traffic"
        )
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_transitions += 1
        self.current_traffic_percentage = 1.0
        
        logger.info(f"Circuit breaker CLOSED for {self.config.service_name}. Service recovered")
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset from OPEN state"""
        if not self.last_failure_time:
            return True
        
        elapsed = time.time() - self.last_failure_time
        
        # Use exponential backoff if enabled
        if self.config.use_exponential_backoff:
            return elapsed >= self.current_backoff_seconds
        
        return elapsed >= self.config.timeout_seconds
    
    def _time_until_half_open(self) -> float:
        """Calculate time until half-open state"""
        if not self.last_failure_time:
            return 0.0
        
        elapsed = time.time() - self.last_failure_time
        
        if self.config.use_exponential_backoff:
            remaining = self.current_backoff_seconds - elapsed
        else:
            remaining = self.config.timeout_seconds - elapsed
        
        return max(0.0, remaining)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        time_in_open = 0.0
        if self.state == CircuitState.OPEN and self.open_state_start_time:
            time_in_open = time.time() - self.open_state_start_time
        
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "state_transitions": self.state_transitions,
            "time_in_open_state": time_in_open,
            "current_backoff_seconds": self.current_backoff_seconds,
            "current_traffic_percentage": self.current_traffic_percentage,
            "half_open_successes": self.half_open_successes,
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.open_state_start_time = None
        self.half_open_calls = 0
        self.current_backoff_seconds = self.config.base_backoff_seconds
        self.current_traffic_percentage = 1.0


class CircuitBreakerManager:
    """Manages circuit breakers for different services with per-service configuration"""
    
    def __init__(self):
        """Initialize circuit breaker manager"""
        self._breakers: Dict[str, EnhancedCircuitBreaker] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}
        self._lock = asyncio.Lock()
    
    def register_service(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """Register a service with custom circuit breaker configuration"""
        if config is None:
            config = CircuitBreakerConfig(service_name=service_name)
        else:
            config.service_name = service_name
        
        self._configs[service_name] = config
    
    async def get_breaker(self, service_name: str) -> EnhancedCircuitBreaker:
        """Get or create circuit breaker for service"""
        async with self._lock:
            if service_name not in self._breakers:
                config = self._configs.get(
                    service_name,
                    CircuitBreakerConfig(service_name=service_name)
                )
                self._breakers[service_name] = EnhancedCircuitBreaker(config)
            
            return self._breakers[service_name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            service: breaker.get_stats()
            for service, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker manager
_circuit_breaker_manager = CircuitBreakerManager()


async def get_circuit_breaker(service_name: str) -> EnhancedCircuitBreaker:
    """Get circuit breaker for service"""
    return await _circuit_breaker_manager.get_breaker(service_name)

