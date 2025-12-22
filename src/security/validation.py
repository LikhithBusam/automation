"""
Input Validation Module

Provides comprehensive input validation and sanitization to prevent security vulnerabilities.
"""

import re
import os
from pathlib import Path
from typing import Any, Optional, List, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation check"""

    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Optional[Any] = None


class InputValidator:
    """Comprehensive input validation"""

    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(;.*--)",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"(\.\./|\.\.\\)",
        r"(\r\n|\n|\r)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    # File path patterns
    DANGEROUS_PATH_PATTERNS = [
        r"\.\./",  # Directory traversal
        r"\.\./",
        r"~",  # Home directory
        r"^/etc/",  # System configs
        r"^/proc/",  # System process info
        r"^/sys/",  # System info
        r"^C:\\Windows\\",  # Windows system
        r"^C:\\Program Files\\",  # Windows programs
    ]

    SENSITIVE_FILE_PATTERNS = [
        r"\.env$",
        r"\.env\..*$",
        r"\.ssh/",
        r"id_rsa",
        r"\.pem$",
        r"\.key$",
        r"password",
        r"secret",
        r"credentials",
        r"\.git/config$",
    ]

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self.sql_regex = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.cmd_regex = [re.compile(p) for p in self.COMMAND_INJECTION_PATTERNS]
        self.xss_regex = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_regex = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATH_PATTERNS]
        self.sensitive_regex = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_FILE_PATTERNS]

    def validate_sql_input(self, value: str) -> ValidationResult:
        """Validate input for SQL injection attempts"""
        if not value:
            return ValidationResult(is_valid=True, sanitized_value=value)

        for pattern in self.sql_regex:
            if pattern.search(value):
                logger.warning(f"Potential SQL injection detected: {value[:50]}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Input contains potentially dangerous SQL patterns",
                )

        return ValidationResult(is_valid=True, sanitized_value=value)

    def validate_command_input(self, value: str) -> ValidationResult:
        """Validate input for command injection attempts"""
        if not value:
            return ValidationResult(is_valid=True, sanitized_value=value)

        for pattern in self.cmd_regex:
            if pattern.search(value):
                logger.warning(f"Potential command injection detected: {value[:50]}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Input contains potentially dangerous command characters",
                )

        return ValidationResult(is_valid=True, sanitized_value=value)

    def validate_xss_input(self, value: str) -> ValidationResult:
        """Validate input for XSS attempts"""
        if not value:
            return ValidationResult(is_valid=True, sanitized_value=value)

        for pattern in self.xss_regex:
            if pattern.search(value):
                logger.warning(f"Potential XSS detected: {value[:50]}")
                return ValidationResult(
                    is_valid=False,
                    error_message="Input contains potentially dangerous HTML/JavaScript",
                )

        # Sanitize by escaping HTML
        sanitized = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        return ValidationResult(is_valid=True, sanitized_value=sanitized)

    def validate_file_path(
        self, path: str, allowed_paths: Optional[List[str]] = None, allow_creation: bool = False
    ) -> ValidationResult:
        """Validate file path for security issues"""
        if not path:
            return ValidationResult(is_valid=False, error_message="Path cannot be empty")

        try:
            # Normalize path
            normalized_path = os.path.normpath(path)

            # Check for dangerous patterns
            for pattern in self.path_regex:
                if pattern.search(normalized_path):
                    logger.warning(f"Dangerous path pattern detected: {normalized_path}")
                    return ValidationResult(
                        is_valid=False, error_message="Path contains dangerous patterns"
                    )

            # Check for sensitive files
            for pattern in self.sensitive_regex:
                if pattern.search(normalized_path):
                    logger.warning(f"Sensitive file access attempt: {normalized_path}")
                    return ValidationResult(
                        is_valid=False, error_message="Access to sensitive files is not allowed"
                    )

            # Check against whitelist
            if allowed_paths:
                path_obj = Path(normalized_path).resolve()
                is_allowed = False

                for allowed in allowed_paths:
                    allowed_obj = Path(allowed).resolve()
                    try:
                        path_obj.relative_to(allowed_obj)
                        is_allowed = True
                        break
                    except ValueError:
                        continue

                if not is_allowed:
                    logger.warning(f"Path not in whitelist: {normalized_path}")
                    return ValidationResult(
                        is_valid=False, error_message="Path is not in allowed directories"
                    )

            # Check if path exists (unless creation is allowed)
            if not allow_creation and not os.path.exists(normalized_path):
                return ValidationResult(is_valid=False, error_message="Path does not exist")

            return ValidationResult(is_valid=True, sanitized_value=normalized_path)

        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return ValidationResult(is_valid=False, error_message=str(e))

    def validate_integer(
        self, value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None
    ) -> ValidationResult:
        """Validate integer input"""
        try:
            int_value = int(value)

            if min_value is not None and int_value < min_value:
                return ValidationResult(
                    is_valid=False, error_message=f"Value must be at least {min_value}"
                )

            if max_value is not None and int_value > max_value:
                return ValidationResult(
                    is_valid=False, error_message=f"Value must be at most {max_value}"
                )

            return ValidationResult(is_valid=True, sanitized_value=int_value)

        except (ValueError, TypeError):
            return ValidationResult(is_valid=False, error_message="Invalid integer value")

    def validate_string(
        self,
        value: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ) -> ValidationResult:
        """Validate string input"""
        if not isinstance(value, str):
            return ValidationResult(is_valid=False, error_message="Value must be a string")

        if min_length is not None and len(value) < min_length:
            return ValidationResult(
                is_valid=False, error_message=f"String must be at least {min_length} characters"
            )

        if max_length is not None and len(value) > max_length:
            return ValidationResult(
                is_valid=False, error_message=f"String must be at most {max_length} characters"
            )

        if pattern:
            if not re.match(pattern, value):
                return ValidationResult(
                    is_valid=False, error_message="String does not match required pattern"
                )

        return ValidationResult(is_valid=True, sanitized_value=value)

    def validate_email(self, email: str) -> ValidationResult:
        """Validate email address"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            return ValidationResult(is_valid=False, error_message="Invalid email address")

        return ValidationResult(is_valid=True, sanitized_value=email.lower())

    def validate_url(
        self, url: str, allowed_schemes: Optional[List[str]] = None
    ) -> ValidationResult:
        """Validate URL"""
        url_pattern = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"

        if not re.match(url_pattern, url, re.IGNORECASE):
            return ValidationResult(is_valid=False, error_message="Invalid URL format")

        if allowed_schemes:
            scheme = url.split("://")[0].lower()
            if scheme not in allowed_schemes:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"URL scheme must be one of: {', '.join(allowed_schemes)}",
                )

        return ValidationResult(is_valid=True, sanitized_value=url)

    def sanitize_filename(self, filename: str) -> ValidationResult:
        """Sanitize filename to prevent issues"""
        # Remove path components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[: 255 - len(ext)] + ext

        if not sanitized:
            return ValidationResult(is_valid=False, error_message="Invalid filename")

        return ValidationResult(is_valid=True, sanitized_value=sanitized)

    def validate_json_keys(self, data: Dict[str, Any], allowed_keys: List[str]) -> ValidationResult:
        """Validate JSON object keys against whitelist"""
        invalid_keys = set(data.keys()) - set(allowed_keys)

        if invalid_keys:
            return ValidationResult(
                is_valid=False, error_message=f"Invalid keys: {', '.join(invalid_keys)}"
            )

        return ValidationResult(is_valid=True, sanitized_value=data)


# Global validator instance
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get or create global validator"""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def validate_and_raise(result: ValidationResult):
    """Validate result and raise exception if invalid"""
    if not result.is_valid:
        raise ValueError(result.error_message or "Validation failed")
    return result.sanitized_value
