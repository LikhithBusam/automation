"""
Log Sanitization - Filter Sensitive Data from Logs
Prevents API keys, tokens, passwords, and PII from appearing in logs
"""

import re
import logging
from typing import Any, Dict, List, Pattern
from functools import wraps


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that sanitizes sensitive data before it reaches log handlers.

    Protects:
    - API keys and tokens
    - Passwords and secrets
    - Email addresses (optional)
    - Credit card numbers
    - Social Security Numbers
    - IP addresses (optional)
    """

    # Patterns for sensitive data detection
    PATTERNS: List[Dict[str, Any]] = [
        # API Keys and Tokens
        {
            "name": "groq_api_key",
            "pattern": r"gsk_[a-zA-Z0-9]{40,}",
            "replacement": "gsk_***REDACTED***"
        },
        {
            "name": "github_token",
            "pattern": r"gh[ps]_[a-zA-Z0-9]{36,}",
            "replacement": "gh*_***REDACTED***"
        },
        {
            "name": "github_pat",
            "pattern": r"github_pat_[a-zA-Z0-9_]{82}",
            "replacement": "github_pat_***REDACTED***"
        },
        {
            "name": "slack_token",
            "pattern": r"xox[baprs]-[a-zA-Z0-9-]{10,}",
            "replacement": "xox*-***REDACTED***"
        },
        {
            "name": "huggingface_token",
            "pattern": r"hf_[a-zA-Z0-9]{30,}",
            "replacement": "hf_***REDACTED***"
        },
        {
            "name": "gemini_api_key",
            "pattern": r"AIzaSy[a-zA-Z0-9_-]{33}",
            "replacement": "AIzaSy***REDACTED***"
        },
        {
            "name": "openai_api_key",
            "pattern": r"sk-[a-zA-Z0-9]{48}",
            "replacement": "sk-***REDACTED***"
        },
        {
            "name": "anthropic_api_key",
            "pattern": r"sk-ant-[a-zA-Z0-9-]{95}",
            "replacement": "sk-ant-***REDACTED***"
        },
        {
            "name": "aws_access_key",
            "pattern": r"AKIA[0-9A-Z]{16}",
            "replacement": "AKIA***REDACTED***"
        },

        # Generic API key patterns
        {
            "name": "generic_api_key",
            "pattern": r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_-]{20,})['\"]",
            "replacement": r"api_key='***REDACTED***'"
        },
        {
            "name": "generic_token",
            "pattern": r"['\"]?token['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_.-]{20,})['\"]",
            "replacement": r"token='***REDACTED***'"
        },
        {
            "name": "bearer_token",
            "pattern": r"Bearer\s+[a-zA-Z0-9_.-]{20,}",
            "replacement": "Bearer ***REDACTED***"
        },

        # Passwords and Secrets
        {
            "name": "password",
            "pattern": r"['\"]?password['\"]?\s*[:=]\s*['\"]([^'\"]{3,})['\"]",
            "replacement": r"password='***REDACTED***'"
        },
        {
            "name": "secret",
            "pattern": r"['\"]?secret['\"]?\s*[:=]\s*['\"]([a-zA-Z0-9_.-]{8,})['\"]",
            "replacement": r"secret='***REDACTED***'"
        },
        {
            "name": "private_key",
            "pattern": r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(RSA\s+)?PRIVATE\s+KEY-----",
            "replacement": "-----BEGIN PRIVATE KEY-----\n***REDACTED***\n-----END PRIVATE KEY-----"
        },

        # Credit Cards (basic pattern)
        {
            "name": "credit_card",
            "pattern": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            "replacement": "****-****-****-****"
        },

        # Social Security Numbers (US)
        {
            "name": "ssn",
            "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
            "replacement": "***-**-****"
        },

        # Email addresses (optional - can be disabled)
        {
            "name": "email",
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "replacement": "***@***.***",
            "enabled": False  # Disabled by default
        },

        # IP addresses (optional - can be disabled)
        {
            "name": "ipv4",
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "replacement": "*.*.*.*",
            "enabled": False  # Disabled by default
        },
    ]

    def __init__(self, name: str = "", redact_emails: bool = False, redact_ips: bool = False):
        """
        Initialize sensitive data filter.

        Args:
            name: Filter name
            redact_emails: Whether to redact email addresses
            redact_ips: Whether to redact IP addresses
        """
        super().__init__(name)

        # Compile patterns for performance
        self.compiled_patterns: List[tuple] = []

        for pattern_config in self.PATTERNS:
            # Check if pattern should be enabled
            if not pattern_config.get("enabled", True):
                # Handle optional patterns
                if pattern_config["name"] == "email" and not redact_emails:
                    continue
                if pattern_config["name"] == "ipv4" and not redact_ips:
                    continue

            compiled = re.compile(pattern_config["pattern"], re.IGNORECASE)
            self.compiled_patterns.append((
                pattern_config["name"],
                compiled,
                pattern_config["replacement"]
            ))

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Sanitize log record message.

        Args:
            record: Log record to filter

        Returns:
            True to allow record to pass through
        """
        # Sanitize message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)

        # Sanitize args if present
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self.sanitize(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self.sanitize(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def sanitize(self, text: str) -> str:
        """
        Sanitize text by replacing sensitive data patterns.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text with sensitive data redacted
        """
        if not text:
            return text

        result = text

        for name, pattern, replacement in self.compiled_patterns:
            result = pattern.sub(replacement, result)

        return result


# Global filter instance
_default_filter = SensitiveDataFilter(
    name="sensitive_data_filter",
    redact_emails=False,  # Don't redact emails by default
    redact_ips=False      # Don't redact IPs by default
)


def install_log_filter(
    logger: logging.Logger = None,
    redact_emails: bool = False,
    redact_ips: bool = False
):
    """
    Install sensitive data filter on logger.

    Args:
        logger: Logger to install filter on (None = root logger)
        redact_emails: Whether to redact email addresses
        redact_ips: Whether to redact IP addresses

    Example:
        # Install on root logger
        install_log_filter()

        # Install on specific logger
        import logging
        logger = logging.getLogger("my_app")
        install_log_filter(logger, redact_emails=True)
    """
    if logger is None:
        logger = logging.getLogger()

    # Remove existing filters with same name
    logger.filters = [f for f in logger.filters if not isinstance(f, SensitiveDataFilter)]

    # Add new filter
    filter_instance = SensitiveDataFilter(
        name="sensitive_data_filter",
        redact_emails=redact_emails,
        redact_ips=redact_ips
    )
    logger.addFilter(filter_instance)

    logger.debug("Sensitive data filter installed on logger")


def sanitize_dict(data: Dict[str, Any], keys_to_redact: List[str] = None) -> Dict[str, Any]:
    """
    Sanitize dictionary by redacting sensitive keys.

    Args:
        data: Dictionary to sanitize
        keys_to_redact: List of keys to redact (default: common sensitive keys)

    Returns:
        Sanitized dictionary copy

    Example:
        config = {"api_key": "secret123", "name": "John"}
        safe_config = sanitize_dict(config)
        # Result: {"api_key": "***REDACTED***", "name": "John"}
    """
    if keys_to_redact is None:
        keys_to_redact = [
            "api_key", "apikey", "api-key",
            "token", "access_token", "auth_token",
            "password", "passwd", "pwd",
            "secret", "secret_key",
            "private_key", "privatekey",
            "authorization", "auth",
        ]

    sanitized = data.copy()

    for key in sanitized.keys():
        key_lower = key.lower()

        # Check if key should be redacted
        if any(sensitive_key in key_lower for sensitive_key in keys_to_redact):
            sanitized[key] = "***REDACTED***"

        # Recursively sanitize nested dictionaries
        elif isinstance(sanitized[key], dict):
            sanitized[key] = sanitize_dict(sanitized[key], keys_to_redact)

        # Sanitize string values
        elif isinstance(sanitized[key], str):
            sanitized[key] = _default_filter.sanitize(sanitized[key])

    return sanitized


def sanitize_string(text: str) -> str:
    """
    Sanitize string by removing sensitive data patterns.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text

    Example:
        log_message = "API key: gsk_abc123..."
        safe_message = sanitize_string(log_message)
        # Result: "API key: gsk_***REDACTED***"
    """
    return _default_filter.sanitize(text)


def safe_log_decorator(func):
    """
    Decorator to sanitize function arguments before logging.

    Example:
        @safe_log_decorator
        def make_api_call(api_key: str, endpoint: str):
            logger.info(f"Calling {endpoint} with key {api_key}")
            # Logs: "Calling /api/data with key gsk_***REDACTED***"
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Sanitize kwargs for logging
        if kwargs:
            safe_kwargs = sanitize_dict(kwargs)
            logging.getLogger(func.__module__).debug(
                f"Calling {func.__name__} with args: {safe_kwargs}"
            )

        return func(*args, **kwargs)

    return wrapper


# Auto-install on import for root logger (can be disabled if needed)
def auto_install(enabled: bool = True):
    """
    Auto-install sensitive data filter on root logger.

    Args:
        enabled: Whether to auto-install (default: True)
    """
    if enabled:
        install_log_filter(
            logger=None,  # Root logger
            redact_emails=False,
            redact_ips=False
        )
