"""
Centralized Logging Configuration
Structured logging with ELK stack integration
"""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGING_AVAILABLE = True
except ImportError:
    JSON_LOGGING_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "workflow_name"):
            log_data["workflow_name"] = record.workflow_name
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name
        
        return json.dumps(log_data)


class ELKHandler(logging.Handler):
    """Handler for sending logs to ELK stack"""
    
    def __init__(self, elk_config: Dict[str, Any]):
        super().__init__()
        self.elk_config = elk_config
        self.elk_type = elk_config.get("type", "elasticsearch")
        
        if self.elk_type == "elasticsearch":
            self._init_elasticsearch()
        elif self.elk_type == "logstash":
            self._init_logstash()
        else:
            self.client = None
    
    def _init_elasticsearch(self):
        """Initialize Elasticsearch client"""
        try:
            from elasticsearch import Elasticsearch
            
            es_config = self.elk_config.get("elasticsearch", {})
            self.client = Elasticsearch(
                hosts=es_config.get("hosts", ["localhost:9200"]),
                http_auth=es_config.get("auth"),
            )
            self.index_name = es_config.get("index", "automaton-logs")
        except ImportError:
            logging.warning("elasticsearch not installed, ELK logging disabled")
            self.client = None
    
    def _init_logstash(self):
        """Initialize Logstash handler"""
        try:
            from logstash_async.handler import AsynchronousLogstashHandler
            
            logstash_config = self.elk_config.get("logstash", {})
            self.client = AsynchronousLogstashHandler(
                host=logstash_config.get("host", "localhost"),
                port=logstash_config.get("port", 5000),
                database_path=logstash_config.get("database_path", None),
            )
        except ImportError:
            logging.warning("logstash_async not installed, Logstash logging disabled")
            self.client = None
    
    def emit(self, record: logging.LogRecord):
        """Emit log record to ELK"""
        if not self.client:
            return
        
        try:
            log_data = self.format(record)
            
            if self.elk_type == "elasticsearch":
                # Parse JSON if formatter is JSON
                try:
                    log_dict = json.loads(log_data)
                except json.JSONDecodeError:
                    log_dict = {"message": log_data}
                
                self.client.index(
                    index=self.index_name,
                    body=log_dict,
                )
            elif self.elk_type == "logstash":
                self.client.emit(record)
        except Exception as e:
            logging.error(f"Error sending log to ELK: {e}")


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    elk_config: Optional[Dict[str, Any]] = None,
    json_format: bool = True,
):
    """
    Setup centralized logging.
    
    Args:
        log_level: Logging level
        log_file: Path to log file
        elk_config: ELK stack configuration
        json_format: Use JSON formatting
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format and JSON_LOGGING_AVAILABLE:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
        )
        if json_format and JSON_LOGGING_AVAILABLE:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        root_logger.addHandler(file_handler)
    
    # ELK handler
    if elk_config:
        elk_handler = ELKHandler(elk_config)
        if json_format and JSON_LOGGING_AVAILABLE:
            elk_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(elk_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get logger with structured logging support"""
    logger = logging.getLogger(name)
    
    if STRUCTLOG_AVAILABLE:
        # Use structlog for better structured logging
        return structlog.get_logger(name)
    
    return logger

