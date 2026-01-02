"""
Timeout Management
- Per-service timeout configurations
- Cascading timeout prevention
- Timeout monitoring and alerting
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict
from enum import Enum

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when operation times out"""
    pass


@dataclass
class TimeoutConfig:
    """Timeout configuration for a service"""
    default_timeout_seconds: float = 30.0
    max_timeout_seconds: float = 300.0
    min_timeout_seconds: float = 0.1
    enable_monitoring: bool = True
    service_name: str = "unknown"


class TimeoutManager:
    """Manages timeouts for different services"""
    
    def __init__(self):
        """Initialize timeout manager"""
        self._configs: Dict[str, TimeoutConfig] = {}
        self._active_timeouts: Dict[str, int] = {}
        self._timeout_history: Dict[str, list] = {}
        
        # Metrics
        self._metrics = {
            "timeouts_total": Counter(
                "timeout_occurrences_total",
                "Total timeout occurrences",
                ["service"]
            ),
            "timeout_duration": Histogram(
                "timeout_duration_seconds",
                "Timeout duration in seconds",
                ["service"],
                buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0]
            ),
            "active_timeouts": Counter(
                "active_timeouts",
                "Number of active timeouts",
                ["service"]
            ),
        }
    
    def register_service(self, service_name: str, config: Optional[TimeoutConfig] = None):
        """Register a service with timeout configuration"""
        if config is None:
            config = TimeoutConfig(service_name=service_name)
        else:
            config.service_name = service_name
        
        self._configs[service_name] = config
        self._timeout_history[service_name] = []
    
    def get_timeout(self, service_name: str) -> float:
        """Get timeout for service"""
        config = self._configs.get(service_name)
        if config:
            return config.default_timeout_seconds
        
        # Default timeout
        return 30.0
    
    async def execute_with_timeout(
        self,
        func: Callable,
        service_name: str,
        timeout_seconds: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout.
        
        Args:
            func: Async function to execute
            service_name: Service name for configuration
            timeout_seconds: Optional timeout override
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            TimeoutError: If operation times out
        """
        # Get timeout
        if timeout_seconds is None:
            timeout_seconds = self.get_timeout(service_name)
        
        # Validate timeout
        config = self._configs.get(service_name)
        if config:
            timeout_seconds = max(
                config.min_timeout_seconds,
                min(timeout_seconds, config.max_timeout_seconds)
            )
        
        # Track active timeout
        self._active_timeouts[service_name] = self._active_timeouts.get(service_name, 0) + 1
        
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds
            )
            
            duration = time.time() - start_time
            
            # Check for cascading timeout (operation took too long even if didn't timeout)
            if config and config.enable_monitoring:
                if duration > timeout_seconds * 0.9:  # 90% of timeout
                    logger.warning(
                        f"Service {service_name} operation took {duration:.2f}s "
                        f"(90% of timeout {timeout_seconds}s). Potential cascading timeout."
                    )
            
            return result
        
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            
            # Record timeout
            if config and config.enable_monitoring:
                self._timeout_history[service_name].append({
                    "timestamp": time.time(),
                    "duration": duration,
                    "timeout_seconds": timeout_seconds
                })
                
                # Keep only last 100
                if len(self._timeout_history[service_name]) > 100:
                    self._timeout_history[service_name] = self._timeout_history[service_name][-100:]
                
                # Update metrics
                self._metrics["timeouts_total"].labels(service=service_name).inc()
                self._metrics["timeout_duration"].labels(service=service_name).observe(duration)
            
            logger.error(
                f"Timeout for service {service_name} after {timeout_seconds}s"
            )
            
            raise TimeoutError(
                f"Operation timed out after {timeout_seconds}s for service {service_name}"
            )
        
        finally:
            # Decrement active timeout
            self._active_timeouts[service_name] = max(
                0,
                self._active_timeouts.get(service_name, 0) - 1
            )
    
    def get_timeout_stats(self, service_name: str) -> Dict[str, Any]:
        """Get timeout statistics for service"""
        history = self._timeout_history.get(service_name, [])
        
        if not history:
            return {
                "total_timeouts": 0,
                "recent_timeouts": [],
                "active_timeouts": self._active_timeouts.get(service_name, 0)
            }
        
        recent = history[-10:]  # Last 10 timeouts
        
        return {
            "total_timeouts": len(history),
            "recent_timeouts": recent,
            "active_timeouts": self._active_timeouts.get(service_name, 0),
            "avg_timeout_duration": sum(t["duration"] for t in history) / len(history) if history else 0
        }
    
    def detect_cascading_timeouts(self, service_name: str, threshold: int = 5) -> bool:
        """Detect if service has cascading timeout issues"""
        history = self._timeout_history.get(service_name, [])
        
        if len(history) < threshold:
            return False
        
        # Check if recent timeouts are increasing
        recent = history[-threshold:]
        durations = [t["duration"] for t in recent]
        
        # Check if durations are increasing (potential cascading)
        if len(durations) >= 2:
            return durations[-1] > durations[0] * 1.5
        
        return False


# Global timeout manager
_timeout_manager = TimeoutManager()


def with_timeout(
    service_name: str,
    timeout_seconds: Optional[float] = None
):
    """
    Decorator for timeout management.
    
    Usage:
        @with_timeout("api-service", timeout_seconds=10.0)
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            return await _timeout_manager.execute_with_timeout(
                func,
                service_name,
                timeout_seconds,
                *args,
                **kwargs
            )
        
        return wrapper
    
    return decorator

