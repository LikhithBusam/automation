"""
Health Check and Monitoring Endpoints

Provides health checks for Kubernetes liveness/readiness probes
and Prometheus metrics endpoints.
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a component"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    metadata: Dict[str, Any] = None


@dataclass
class HealthCheckResponse:
    """Overall health check response"""
    status: HealthStatus
    timestamp: str
    uptime_seconds: float
    version: str
    components: List[ComponentHealth]
    system: Dict[str, Any]


class PrometheusMetrics:
    """Prometheus metrics collector"""

    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            'automaton_requests_total',
            'Total number of requests',
            ['endpoint', 'method', 'status']
        )

        self.request_duration = Histogram(
            'automaton_request_duration_seconds',
            'Request duration in seconds',
            ['endpoint', 'method']
        )

        # Agent metrics
        self.agent_task_count = Counter(
            'automaton_agent_tasks_total',
            'Total number of agent tasks',
            ['agent', 'status']
        )

        self.agent_task_duration = Histogram(
            'automaton_agent_task_duration_seconds',
            'Agent task duration in seconds',
            ['agent']
        )

        # MCP tool metrics
        self.mcp_call_count = Counter(
            'automaton_mcp_calls_total',
            'Total number of MCP tool calls',
            ['tool', 'operation', 'status']
        )

        self.mcp_call_duration = Histogram(
            'automaton_mcp_call_duration_seconds',
            'MCP call duration in seconds',
            ['tool', 'operation']
        )

        # Memory metrics
        self.memory_entries = Gauge(
            'automaton_memory_entries',
            'Number of memory entries',
            ['tier', 'type']
        )

        self.memory_access_count = Counter(
            'automaton_memory_accesses_total',
            'Total number of memory accesses',
            ['tier', 'operation']
        )

        # Model metrics
        self.model_inference_count = Counter(
            'automaton_model_inferences_total',
            'Total number of model inferences',
            ['model', 'status']
        )

        self.model_inference_duration = Histogram(
            'automaton_model_inference_duration_seconds',
            'Model inference duration in seconds',
            ['model']
        )

        self.model_tokens_generated = Counter(
            'automaton_model_tokens_total',
            'Total number of tokens generated',
            ['model']
        )

        # System metrics
        self.cpu_usage = Gauge(
            'automaton_cpu_usage_percent',
            'CPU usage percentage'
        )

        self.memory_usage = Gauge(
            'automaton_memory_usage_bytes',
            'Memory usage in bytes'
        )

        self.gpu_usage = Gauge(
            'automaton_gpu_usage_percent',
            'GPU usage percentage',
            ['device']
        )

        self.gpu_memory_usage = Gauge(
            'automaton_gpu_memory_usage_bytes',
            'GPU memory usage in bytes',
            ['device']
        )

        # Error metrics
        self.error_count = Counter(
            'automaton_errors_total',
            'Total number of errors',
            ['component', 'error_type']
        )

        # Cache metrics
        self.cache_hits = Counter(
            'automaton_cache_hits_total',
            'Total number of cache hits',
            ['cache_name']
        )

        self.cache_misses = Counter(
            'automaton_cache_misses_total',
            'Total number of cache misses',
            ['cache_name']
        )

    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU usage
            self.cpu_usage.set(psutil.cpu_percent(interval=1))

            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.used)

            # GPU usage (if available)
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()

                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    self.gpu_usage.labels(device=str(i)).set(utilization.gpu)
                    self.gpu_memory_usage.labels(device=str(i)).set(memory_info.used)

                pynvml.nvmlShutdown()
            except (ImportError, Exception):
                pass  # GPU monitoring not available

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")


class HealthChecker:
    """Health check manager"""

    def __init__(self):
        self.start_time = time.time()
        self.version = "2.0.0"
        self.metrics = PrometheusMetrics()

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity"""
        start_time = time.time()

        try:
            from sqlalchemy import create_engine, text
            import os

            db_url = os.getenv("DATABASE_URL", "sqlite:///./dev_assistant.db")
            engine = create_engine(db_url)

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            response_time = (time.time() - start_time) * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database is accessible",
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")

            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)[:100]}",
                response_time_ms=response_time
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity"""
        start_time = time.time()

        try:
            import redis.asyncio as redis
            import os

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)

            await r.ping()
            await r.close()

            response_time = (time.time() - start_time) * 1000

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis is accessible",
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"Redis health check failed: {e}")

            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis unavailable: {str(e)[:100]}",
                response_time_ms=response_time
            )

    async def check_mcp_servers(self) -> List[ComponentHealth]:
        """Check MCP server connectivity"""
        servers = {
            "github": "http://localhost:3000/health",
            "filesystem": "http://localhost:3001/health",
            "memory": "http://localhost:3002/health",
        }

        results = []

        for name, url in servers.items():
            start_time = time.time()

            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        response_time = (time.time() - start_time) * 1000

                        if response.status == 200:
                            results.append(ComponentHealth(
                                name=f"mcp_{name}",
                                status=HealthStatus.HEALTHY,
                                message=f"{name.capitalize()} MCP server is healthy",
                                response_time_ms=response_time
                            ))
                        else:
                            results.append(ComponentHealth(
                                name=f"mcp_{name}",
                                status=HealthStatus.UNHEALTHY,
                                message=f"{name.capitalize()} MCP server returned {response.status}",
                                response_time_ms=response_time
                            ))

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                logger.warning(f"MCP server {name} health check failed: {e}")

                results.append(ComponentHealth(
                    name=f"mcp_{name}",
                    status=HealthStatus.DEGRADED,
                    message=f"{name.capitalize()} MCP server unavailable",
                    response_time_ms=response_time
                ))

        return results

    async def liveness_check(self) -> Dict[str, Any]:
        """Kubernetes liveness probe - checks if application is running"""
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": time.time() - self.start_time
        }

    async def readiness_check(self) -> HealthCheckResponse:
        """Kubernetes readiness probe - checks if application is ready to serve traffic"""
        components = []

        # Check database
        db_health = await self.check_database()
        components.append(db_health)

        # Check Redis
        redis_health = await self.check_redis()
        components.append(redis_health)

        # Check MCP servers
        mcp_health = await self.check_mcp_servers()
        components.extend(mcp_health)

        # Determine overall status
        if all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        system_info = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024 ** 3)
        }

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=time.time() - self.start_time,
            version=self.version,
            components=components,
            system=system_info
        )

    def get_metrics(self) -> bytes:
        """Get Prometheus metrics"""
        # Update system metrics before returning
        self.metrics.update_system_metrics()
        return generate_latest()


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
