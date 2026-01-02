"""
Bulkhead Pattern for Resource Isolation
Isolates resources to prevent cascading failures
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Dict
from enum import Enum

from prometheus_client import Gauge, Counter

logger = logging.getLogger(__name__)


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity"""
    pass


@dataclass
class BulkheadConfig:
    """Bulkhead configuration"""
    max_concurrent: int = 10
    max_queue_size: int = 100
    queue_timeout_seconds: float = 30.0
    enable_metrics: bool = True
    pool_name: str = "default"


class Bulkhead:
    """
    Bulkhead pattern for resource isolation.
    Limits concurrent operations to prevent resource exhaustion.
    """
    
    def __init__(self, config: BulkheadConfig):
        """Initialize bulkhead"""
        self.config = config
        
        # Semaphore for concurrent operations
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        
        # Queue for waiting operations
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        
        # Statistics
        self.active_operations = 0
        self.total_operations = 0
        self.rejected_operations = 0
        self.queue_full_count = 0
        
        # Metrics
        if config.enable_metrics:
            self._init_metrics()
        else:
            self._metrics = None
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        pool = self.config.pool_name
        self._metrics = {
            "active_operations": Gauge(
                "bulkhead_active_operations",
                "Number of active operations in bulkhead",
                ["pool"]
            ),
            "queue_size": Gauge(
                "bulkhead_queue_size",
                "Number of operations waiting in queue",
                ["pool"]
            ),
            "rejected_operations": Counter(
                "bulkhead_rejected_operations_total",
                "Total rejected operations",
                ["pool"]
            ),
            "total_operations": Counter(
                "bulkhead_total_operations_total",
                "Total operations through bulkhead",
                ["pool"]
            ),
        }
    
    def _update_metrics(self):
        """Update Prometheus metrics"""
        if not self._metrics:
            return
        
        pool = self.config.pool_name
        self._metrics["active_operations"].labels(pool=pool).set(self.active_operations)
        self._metrics["queue_size"].labels(pool=pool).set(self._queue.qsize())
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with bulkhead protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            BulkheadFullError: If bulkhead is at capacity
        """
        self.total_operations += 1
        
        if self._metrics:
            self._metrics["total_operations"].labels(pool=self.config.pool_name).inc()
        
        # Try to acquire semaphore
        try:
            # Try to add to queue if semaphore is not available
            if self._semaphore.locked():
                # Try to add to queue
                try:
                    await asyncio.wait_for(
                        self._queue.put((func, args, kwargs)),
                        timeout=self.config.queue_timeout_seconds
                    )
                except asyncio.TimeoutError:
                    self.rejected_operations += 1
                    self.queue_full_count += 1
                    
                    if self._metrics:
                        self._metrics["rejected_operations"].labels(
                            pool=self.config.pool_name
                        ).inc()
                    
                    raise BulkheadFullError(
                        f"Bulkhead {self.config.pool_name} is at capacity. "
                        f"Queue timeout after {self.config.queue_timeout_seconds}s"
                    )
                
                # Wait for semaphore
                await self._semaphore.acquire()
                
                # Get from queue
                func, args, kwargs = await self._queue.get()
            else:
                # Acquire semaphore directly
                await self._semaphore.acquire()
            
            # Execute function
            self.active_operations += 1
            self._update_metrics()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self.active_operations -= 1
                self._semaphore.release()
                self._update_metrics()
        
        except Exception as e:
            # Release semaphore on error if we acquired it
            if not self._semaphore.locked():
                # We had acquired it, release it
                try:
                    self._semaphore.release()
                    self.active_operations = max(0, self.active_operations - 1)
                    self._update_metrics()
                except:
                    pass
            
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics"""
        return {
            "active_operations": self.active_operations,
            "queue_size": self._queue.qsize(),
            "total_operations": self.total_operations,
            "rejected_operations": self.rejected_operations,
            "queue_full_count": self.queue_full_count,
            "max_concurrent": self.config.max_concurrent,
            "max_queue_size": self.config.max_queue_size,
        }


class BulkheadManager:
    """Manages bulkheads for different resource pools"""
    
    def __init__(self):
        """Initialize bulkhead manager"""
        self._bulkheads: Dict[str, Bulkhead] = {}
        self._configs: Dict[str, BulkheadConfig] = {}
    
    def register_pool(
        self,
        pool_name: str,
        config: Optional[BulkheadConfig] = None
    ):
        """Register a resource pool with bulkhead configuration"""
        if config is None:
            config = BulkheadConfig(pool_name=pool_name)
        else:
            config.pool_name = pool_name
        
        self._configs[pool_name] = config
        self._bulkheads[pool_name] = Bulkhead(config)
    
    def get_bulkhead(self, pool_name: str) -> Bulkhead:
        """Get bulkhead for resource pool"""
        if pool_name not in self._bulkheads:
            config = self._configs.get(
                pool_name,
                BulkheadConfig(pool_name=pool_name)
            )
            self._bulkheads[pool_name] = Bulkhead(config)
        
        return self._bulkheads[pool_name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all bulkheads"""
        return {
            pool: bulkhead.get_stats()
            for pool, bulkhead in self._bulkheads.items()
        }


# Global bulkhead manager
_bulkhead_manager = BulkheadManager()


def get_bulkhead(pool_name: str) -> Bulkhead:
    """Get bulkhead for resource pool"""
    return _bulkhead_manager.get_bulkhead(pool_name)

