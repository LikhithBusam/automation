"""
Prometheus Metrics Collection
Custom application, system, and business metrics
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    REGISTRY,
    start_http_server,
)

logger = logging.getLogger(__name__)


class ApplicationMetrics:
    """Application-specific metrics"""
    
    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            "automaton_requests_total",
            "Total number of requests",
            ["endpoint", "method", "status"],
        )
        
        self.request_duration = Histogram(
            "automaton_request_duration_seconds",
            "Request duration in seconds",
            ["endpoint", "method"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )
        
        # Workflow metrics
        self.workflow_executions = Counter(
            "automaton_workflow_executions_total",
            "Total workflow executions",
            ["workflow_name", "status"],
        )
        
        self.workflow_duration = Histogram(
            "automaton_workflow_duration_seconds",
            "Workflow execution duration",
            ["workflow_name"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
        )
        
        self.workflow_tasks_completed = Counter(
            "automaton_workflow_tasks_completed_total",
            "Total tasks completed",
            ["workflow_name", "task_type"],
        )
        
        # Agent metrics
        self.agent_invocations = Counter(
            "automaton_agent_invocations_total",
            "Total agent invocations",
            ["agent_name", "status"],
        )
        
        self.agent_duration = Histogram(
            "automaton_agent_duration_seconds",
            "Agent execution duration",
            ["agent_name"],
        )
        
        self.agent_token_usage = Counter(
            "automaton_agent_tokens_total",
            "Total tokens used by agents",
            ["agent_name", "model"],
        )
        
        # MCP tool metrics
        self.mcp_calls = Counter(
            "automaton_mcp_calls_total",
            "Total MCP tool calls",
            ["tool_name", "operation", "status"],
        )
        
        self.mcp_call_duration = Histogram(
            "automaton_mcp_call_duration_seconds",
            "MCP call duration",
            ["tool_name", "operation"],
        )
        
        # Memory metrics
        self.memory_operations = Counter(
            "automaton_memory_operations_total",
            "Total memory operations",
            ["operation", "tier", "type"],
        )
        
        self.memory_entries = Gauge(
            "automaton_memory_entries",
            "Number of memory entries",
            ["tier", "type"],
        )
        
        # Business metrics
        self.active_workflows = Gauge(
            "automaton_active_workflows",
            "Number of currently active workflows",
        )
        
        self.queue_depth = Gauge(
            "automaton_queue_depth",
            "Current queue depth",
            ["queue_name"],
        )
        
        self.user_sessions = Gauge(
            "automaton_user_sessions_active",
            "Number of active user sessions",
        )


class SystemMetrics:
    """System resource metrics"""
    
    def __init__(self):
        import psutil
        
        self.cpu_usage = Gauge(
            "automaton_system_cpu_usage_percent",
            "CPU usage percentage",
        )
        
        self.memory_usage = Gauge(
            "automaton_system_memory_usage_bytes",
            "Memory usage in bytes",
        )
        
        self.memory_available = Gauge(
            "automaton_system_memory_available_bytes",
            "Available memory in bytes",
        )
        
        self.disk_usage = Gauge(
            "automaton_system_disk_usage_bytes",
            "Disk usage in bytes",
            ["device", "mountpoint"],
        )
        
        self.disk_available = Gauge(
            "automaton_system_disk_available_bytes",
            "Available disk space in bytes",
            ["device", "mountpoint"],
        )
        
        self.network_bytes_sent = Counter(
            "automaton_system_network_bytes_sent_total",
            "Total bytes sent",
            ["interface"],
        )
        
        self.network_bytes_recv = Counter(
            "automaton_system_network_bytes_recv_total",
            "Total bytes received",
            ["interface"],
        )
        
        self.psutil = psutil
    
    def update_metrics(self):
        """Update system metrics"""
        try:
            # CPU
            self.cpu_usage.set(self.psutil.cpu_percent(interval=1))
            
            # Memory
            memory = self.psutil.virtual_memory()
            self.memory_usage.set(memory.used)
            self.memory_available.set(memory.available)
            
            # Disk
            for partition in self.psutil.disk_partitions():
                try:
                    usage = self.psutil.disk_usage(partition.mountpoint)
                    self.disk_usage.labels(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                    ).set(usage.used)
                    self.disk_available.labels(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                    ).set(usage.free)
                except PermissionError:
                    pass
            
            # Network
            net_io = self.psutil.net_io_counters(pernic=True)
            for interface, stats in net_io.items():
                self.network_bytes_sent.labels(interface=interface).inc(stats.bytes_sent)
                self.network_bytes_recv.labels(interface=interface).inc(stats.bytes_recv)
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")


class BusinessMetrics:
    """Business KPI metrics"""
    
    def __init__(self):
        # Workflow success rate
        self.workflow_success_rate = Gauge(
            "automaton_business_workflow_success_rate",
            "Workflow success rate (0-1)",
            ["workflow_name"],
        )
        
        # Agent success rate
        self.agent_success_rate = Gauge(
            "automaton_business_agent_success_rate",
            "Agent success rate (0-1)",
            ["agent_name"],
        )
        
        # Average response time
        self.avg_response_time = Gauge(
            "automaton_business_avg_response_time_seconds",
            "Average response time",
            ["endpoint"],
        )
        
        # User engagement
        self.active_users = Gauge(
            "automaton_business_active_users",
            "Number of active users",
            ["time_period"],  # "1h", "24h", "7d"
        )
        
        # Cost metrics
        self.api_cost = Counter(
            "automaton_business_api_cost_total",
            "Total API cost",
            ["provider", "model"],
        )
        
        self.storage_cost = Gauge(
            "automaton_business_storage_cost",
            "Current storage cost",
        )


class MetricsCollector:
    """Unified metrics collector"""
    
    def __init__(self):
        self.app_metrics = ApplicationMetrics()
        self.system_metrics = SystemMetrics()
        self.business_metrics = BusinessMetrics()
        self._update_interval = 30  # seconds
    
    def start_collection(self, port: int = 9090):
        """Start metrics collection server"""
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    
    def update_system_metrics(self):
        """Update system metrics"""
        self.system_metrics.update_metrics()
    
    def get_metrics(self) -> bytes:
        """Get all metrics in Prometheus format"""
        return generate_latest(REGISTRY)


def track_request(endpoint: str, method: str):
    """Decorator to track request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                metrics = ApplicationMetrics()
                metrics.request_count.labels(
                    endpoint=endpoint,
                    method=method,
                    status=status,
                ).inc()
                metrics.request_duration.labels(
                    endpoint=endpoint,
                    method=method,
                ).observe(duration)
        
        return wrapper
    return decorator


def track_workflow(workflow_name: str):
    """Decorator to track workflow metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                metrics = ApplicationMetrics()
                metrics.workflow_executions.labels(
                    workflow_name=workflow_name,
                    status=status,
                ).inc()
                metrics.workflow_duration.labels(
                    workflow_name=workflow_name,
                ).observe(duration)
        
        return wrapper
    return decorator


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

