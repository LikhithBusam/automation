"""
Distributed Tracing with OpenTelemetry
Trace workflow executions, agent interactions, MCP tool calls
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    logger.warning("OpenTelemetry not installed, tracing disabled")


class TracingManager:
    """Distributed tracing manager"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize tracing manager.
        
        Args:
            config: Tracing configuration
        """
        if not TRACING_AVAILABLE:
            self.enabled = False
            return
        
        self.config = config
        self.enabled = config.get("enabled", True)
        
        if not self.enabled:
            return
        
        # Initialize tracer provider
        resource = Resource.create({
            "service.name": config.get("service_name", "automaton"),
            "service.version": config.get("service_version", "2.0.0"),
        })
        
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Configure exporter
        exporter_type = config.get("exporter", "jaeger")
        if exporter_type == "jaeger":
            jaeger_endpoint = config.get("jaeger_endpoint", "http://localhost:14268/api/traces")
            exporter = JaegerExporter(
                agent_host_name=config.get("jaeger_agent_host", "localhost"),
                agent_port=config.get("jaeger_agent_port", 6831),
                endpoint=jaeger_endpoint,
            )
        elif exporter_type == "zipkin":
            from opentelemetry.exporter.zipkin.json import ZipkinExporter
            zipkin_endpoint = config.get("zipkin_endpoint", "http://localhost:9411/api/v2/spans")
            exporter = ZipkinExporter(endpoint=zipkin_endpoint)
        else:
            # Console exporter for development
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        
        # Add span processor
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        self.tracer = trace.get_tracer(__name__)
        
        # Instrument libraries
        self._instrument_libraries()
    
    def _instrument_libraries(self):
        """Instrument libraries for automatic tracing"""
        try:
            FastAPIInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            Psycopg2Instrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument libraries: {e}")
    
    @contextmanager
    def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a trace span"""
        if not self.enabled:
            yield
            return
        
        span = self.tracer.start_as_current_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()
    
    def trace_workflow(self, workflow_name: str):
        """Decorator to trace workflow execution"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.trace_span(
                    f"workflow.{workflow_name}",
                    attributes={
                        "workflow.name": workflow_name,
                        "workflow.parameters": str(kwargs),
                    },
                ):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def trace_agent(self, agent_name: str):
        """Decorator to trace agent execution"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.trace_span(
                    f"agent.{agent_name}",
                    attributes={
                        "agent.name": agent_name,
                    },
                ):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def trace_mcp_call(self, tool_name: str, operation: str):
        """Decorator to trace MCP tool calls"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.trace_span(
                    f"mcp.{tool_name}.{operation}",
                    attributes={
                        "mcp.tool": tool_name,
                        "mcp.operation": operation,
                    },
                ):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


# Global tracing manager
_tracing_manager: Optional[TracingManager] = None


def get_tracing_manager() -> Optional[TracingManager]:
    """Get global tracing manager"""
    return _tracing_manager


def initialize_tracing(config: Dict[str, Any]):
    """Initialize global tracing"""
    global _tracing_manager
    _tracing_manager = TracingManager(config)
    return _tracing_manager

