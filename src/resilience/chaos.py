"""
Chaos Engineering Tests
- Random service failures
- Network latency injection
- Resource exhaustion scenarios
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class ChaosScenario(Enum):
    """Chaos engineering scenarios"""
    RANDOM_FAILURE = "random_failure"
    LATENCY_INJECTION = "latency_injection"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PARTIAL_FAILURE = "partial_failure"
    CASCADING_FAILURE = "cascading_failure"


@dataclass
class ChaosConfig:
    """Chaos engineering configuration"""
    enabled: bool = False
    failure_rate: float = 0.1  # 10% failure rate
    min_latency_ms: float = 0.0
    max_latency_ms: float = 1000.0
    latency_probability: float = 0.2  # 20% chance of latency injection
    resource_exhaustion_probability: float = 0.05  # 5% chance
    scenarios: List[ChaosScenario] = None


class ChaosEngine:
    """
    Chaos engineering engine for testing resilience.
    Injects failures, latency, and resource issues.
    """
    
    def __init__(self, config: Optional[ChaosConfig] = None):
        """Initialize chaos engine"""
        self.config = config or ChaosConfig()
        self._active_scenarios: Dict[str, ChaosScenario] = {}
        self._failure_count = 0
        self._latency_injections = 0
        self._resource_exhaustions = 0
    
    def enable(self):
        """Enable chaos engineering"""
        self.config.enabled = True
        logger.warning("Chaos engineering ENABLED - system may experience failures")
    
    def disable(self):
        """Disable chaos engineering"""
        self.config.enabled = False
        logger.info("Chaos engineering DISABLED")
    
    def inject_failure(self, service_name: str, probability: Optional[float] = None) -> bool:
        """
        Inject random failure for service.
        
        Args:
            service_name: Service name
            probability: Optional failure probability override
        
        Returns:
            True if failure should be injected
        """
        if not self.config.enabled:
            return False
        
        prob = probability or self.config.failure_rate
        should_fail = random.random() < prob
        
        if should_fail:
            self._failure_count += 1
            logger.warning(f"Chaos: Injecting failure for {service_name}")
            return True
        
        return False
    
    async def inject_latency(
        self,
        service_name: str,
        min_ms: Optional[float] = None,
        max_ms: Optional[float] = None,
        probability: Optional[float] = None
    ) -> float:
        """
        Inject network latency.
        
        Args:
            service_name: Service name
            min_ms: Minimum latency in milliseconds
            max_ms: Maximum latency in milliseconds
            probability: Optional latency injection probability
        
        Returns:
            Latency in seconds
        """
        if not self.config.enabled:
            return 0.0
        
        prob = probability or self.config.latency_probability
        should_inject = random.random() < prob
        
        if should_inject:
            min_latency = min_ms or self.config.min_latency_ms
            max_latency = max_ms or self.config.max_latency_ms
            latency_ms = random.uniform(min_latency, max_latency)
            latency_seconds = latency_ms / 1000.0
            
            self._latency_injections += 1
            logger.warning(
                f"Chaos: Injecting {latency_ms:.2f}ms latency for {service_name}"
            )
            
            await asyncio.sleep(latency_seconds)
            return latency_seconds
        
        return 0.0
    
    def inject_resource_exhaustion(
        self,
        service_name: str,
        probability: Optional[float] = None
    ) -> bool:
        """
        Inject resource exhaustion scenario.
        
        Args:
            service_name: Service name
            probability: Optional probability override
        
        Returns:
            True if resource exhaustion should be injected
        """
        if not self.config.enabled:
            return False
        
        prob = probability or self.config.resource_exhaustion_probability
        should_exhaust = random.random() < prob
        
        if should_exhaust:
            self._resource_exhaustions += 1
            logger.warning(f"Chaos: Injecting resource exhaustion for {service_name}")
            return True
        
        return False
    
    async def execute_with_chaos(
        self,
        service_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with chaos engineering.
        
        Args:
            service_name: Service name
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If chaos injection causes failure
        """
        if not self.config.enabled:
            return await func(*args, **kwargs)
        
        # Inject latency
        await self.inject_latency(service_name)
        
        # Inject resource exhaustion
        if self.inject_resource_exhaustion(service_name):
            raise Exception(f"Resource exhaustion simulated for {service_name}")
        
        # Inject random failure
        if self.inject_failure(service_name):
            raise Exception(f"Random failure simulated for {service_name}")
        
        # Execute function
        return await func(*args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chaos engineering statistics"""
        return {
            "enabled": self.config.enabled,
            "failure_count": self._failure_count,
            "latency_injections": self._latency_injections,
            "resource_exhaustions": self._resource_exhaustions,
            "active_scenarios": len(self._active_scenarios),
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self._failure_count = 0
        self._latency_injections = 0
        self._resource_exhaustions = 0


# Global chaos engine
_chaos_engine = ChaosEngine()


def get_chaos_engine() -> ChaosEngine:
    """Get global chaos engine"""
    return _chaos_engine

