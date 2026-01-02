"""
Monitoring Initialization
Initialize all monitoring components at application startup
"""

import logging
import os
from typing import Dict, Any, Optional
import asyncio

from src.monitoring.prometheus_metrics import MetricsCollector, get_metrics_collector
from src.monitoring.tracing import initialize_tracing
from src.monitoring.logging_config import setup_logging
from src.monitoring.oncall_integration import get_oncall_manager

logger = logging.getLogger(__name__)


def initialize_monitoring(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Initialize all monitoring components.
    
    Args:
        config: Optional monitoring configuration
        
    Returns:
        Dictionary with initialized components
    """
    if config is None:
        config = {}
    
    # Setup logging first
    log_level = config.get("log_level", os.getenv("LOG_LEVEL", "INFO"))
    log_file = config.get("log_file", os.getenv("LOG_FILE"))
    elk_config = config.get("elk_config")
    json_format = config.get("json_format", True)
    
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        elk_config=elk_config,
        json_format=json_format,
    )
    
    logger.info("Logging initialized")
    
    # Initialize metrics collector
    metrics_collector = get_metrics_collector()
    metrics_port = config.get("metrics_port", int(os.getenv("METRICS_PORT", "9090")))
    metrics_collector.start_collection(port=metrics_port)
    logger.info(f"Prometheus metrics server started on port {metrics_port}")
    
    # Start system metrics update loop
    async def update_system_metrics():
        """Background task to update system metrics"""
        while True:
            try:
                metrics_collector.update_system_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error updating system metrics: {e}")
                await asyncio.sleep(30)
    
    # Start background task (if in async context)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(update_system_metrics())
        else:
            loop.run_until_complete(update_system_metrics())
    except RuntimeError:
        # No event loop, skip background task
        pass
    
    # Initialize distributed tracing
    tracing_config = config.get("tracing", {})
    tracing_manager = None
    if tracing_config.get("enabled", True):
        tracing_manager = initialize_tracing(tracing_config)
        if tracing_manager and tracing_manager.enabled:
            logger.info("Distributed tracing initialized")
        else:
            logger.info("Distributed tracing disabled or unavailable")
    else:
        logger.info("Distributed tracing disabled in config")
    
    # Initialize on-call manager
    try:
        oncall_manager = get_oncall_manager()
        logger.info("On-call manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize on-call manager: {e}")
        oncall_manager = None
    
    return {
        "metrics_collector": metrics_collector,
        "tracing_manager": tracing_manager,
        "oncall_manager": oncall_manager,
    }


def get_monitoring_config() -> Dict[str, Any]:
    """
    Get monitoring configuration from environment variables.
    
    Returns:
        Monitoring configuration dictionary
    """
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_file": os.getenv("LOG_FILE"),
        "metrics_port": int(os.getenv("METRICS_PORT", "9090")),
        "tracing": {
            "enabled": os.getenv("TRACING_ENABLED", "true").lower() == "true",
            "exporter": os.getenv("TRACING_EXPORTER", "jaeger"),
            "jaeger_endpoint": os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces"),
            "jaeger_agent_host": os.getenv("JAEGER_AGENT_HOST", "jaeger"),
            "jaeger_agent_port": int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            "service_name": os.getenv("SERVICE_NAME", "automaton"),
            "service_version": os.getenv("SERVICE_VERSION", "2.0.0"),
        },
        "elk_config": {
            "type": os.getenv("ELK_TYPE", "elasticsearch"),
            "elasticsearch": {
                "hosts": os.getenv("ELASTICSEARCH_HOSTS", "http://elasticsearch:9200").split(","),
                "index": os.getenv("ELASTICSEARCH_INDEX", "automaton-logs"),
            },
            "logstash": {
                "host": os.getenv("LOGSTASH_HOST", "logstash"),
                "port": int(os.getenv("LOGSTASH_PORT", "5000")),
            },
        },
        "json_format": os.getenv("LOG_JSON_FORMAT", "true").lower() == "true",
    }

