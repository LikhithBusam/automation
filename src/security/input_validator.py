"""
Input Validation and Sanitization
Protects against injection attacks and malicious input
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Set
from dataclasses import dataclass


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


@dataclass
class ValidationRule:
    """Validation rule configuration"""
    max_length: int = 1000
    allowed_pattern: str = None
    disallowed_patterns: List[str] = None
    allowed_values: Set[str] = None


class InputValidator:
    """
    Comprehensive input validation for security.

    Protects against:
    - Path traversal attacks
    - Command injection
    - SQL injection
    - Template injection
    - DoS via large inputs
    """

    # Allowed workflow parameters
    ALLOWED_PARAMS = {
        'code_path', 'focus_areas', 'target_path', 'module_path',
        'output_path', 'environment', 'branch', 'additional_requirements'
    }

    # Shell metacharacters to block
    SHELL_METACHARACTERS = r'[;&|`$<>()\[\]{}\\]'

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(--)|(\/\*))",  # SQL comments and delimiters
        r"(union\s+select)",            # UNION attacks
        r"(drop\s+table)",              # DROP TABLE
        r"(insert\s+into)",             # INSERT attacks
        r"(update\s+.*\s+set)",         # UPDATE attacks
        r"(delete\s+from)",             # DELETE attacks
    ]

    # Maximum input lengths
    MAX_PARAM_LENGTH = 1000
    MAX_STRING_LENGTH = 10000
    MAX_TOTAL_PARAMS = 20

    def __init__(self):
        """Initialize validator"""
        self.validation_rules = self._setup_rules()

    def _setup_rules(self) -> Dict[str, ValidationRule]:
        """Setup parameter-specific validation rules"""
        return {
            'code_path': ValidationRule(
                max_length=500,
                allowed_pattern=r'^[a-zA-Z0-9._/\\-]+$'
            ),
            'target_path': ValidationRule(
                max_length=500,
                allowed_pattern=r'^[a-zA-Z0-9._/\\-]+$'
            ),
            'module_path': ValidationRule(
                max_length=500,
                allowed_pattern=r'^[a-zA-Z0-9._/\\-]+$'
            ),
            'output_path': ValidationRule(
                max_length=500,
                allowed_pattern=r'^[a-zA-Z0-9._/\\-]+$'
            ),
            'focus_areas': ValidationRule(
                max_length=500,
                allowed_pattern=r'^[a-zA-Z0-9, _-]+$'
            ),
            'environment': ValidationRule(
                max_length=50,
                allowed_values={'development', 'staging', 'production', 'test'}
            ),
            'branch': ValidationRule(
                max_length=100,
                allowed_pattern=r'^[a-zA-Z0-9._/-]+$'
            ),
            'additional_requirements': ValidationRule(
                max_length=1000,
                allowed_pattern=r'^[a-zA-Z0-9, _.-]+$'
            ),
        }

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all workflow parameters.

        Args:
            parameters: Dictionary of parameter_name -> value

        Returns:
            Validated and sanitized parameters

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(parameters, dict):
            raise ValidationError("Parameters must be a dictionary")

        # Check total number of parameters
        if len(parameters) > self.MAX_TOTAL_PARAMS:
            raise ValidationError(
                f"Too many parameters: {len(parameters)} "
                f"(max {self.MAX_TOTAL_PARAMS})"
            )

        validated = {}

        for key, value in parameters.items():
            # Validate parameter key
            validated_key = self.validate_parameter_key(key)

            # Validate parameter value
            validated_value = self.validate_parameter_value(validated_key, value)

            validated[validated_key] = validated_value

        return validated

    def validate_parameter_key(self, key: str) -> str:
        """
        Validate parameter key.

        Args:
            key: Parameter name

        Returns:
            Validated key

        Raises:
            ValidationError: If key is invalid
        """
        if not isinstance(key, str):
            raise ValidationError(f"Parameter key must be string, got {type(key)}")

        if not key:
            raise ValidationError("Parameter key cannot be empty")

        if key not in self.ALLOWED_PARAMS:
            raise ValidationError(
                f"Invalid parameter: {key}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_PARAMS))}"
            )

        return key

    def validate_parameter_value(self, key: str, value: Any) -> str:
        """
        Validate parameter value.

        Args:
            key: Parameter name
            value: Parameter value

        Returns:
            Validated and sanitized value

        Raises:
            ValidationError: If value is invalid
        """
        # Convert to string
        if not isinstance(value, str):
            value = str(value)

        # Check length
        if len(value) > self.MAX_PARAM_LENGTH:
            raise ValidationError(
                f"Parameter '{key}' too long: {len(value)} "
                f"(max {self.MAX_PARAM_LENGTH})"
            )

        # Get validation rule
        rule = self.validation_rules.get(key)
        if not rule:
            # Default validation
            return self._default_validation(value)

        # Check against allowed values
        if rule.allowed_values:
            if value not in rule.allowed_values:
                raise ValidationError(
                    f"Invalid value for '{key}': {value}. "
                    f"Allowed: {', '.join(sorted(rule.allowed_values))}"
                )

        # Check against pattern
        if rule.allowed_pattern:
            if not re.match(rule.allowed_pattern, value):
                raise ValidationError(
                    f"Invalid format for '{key}': {value}"
                )

        # Path-specific validation
        if key.endswith('_path'):
            return self.validate_path(value)

        return value

    def validate_path(self, path: str) -> str:
        """
        Validate file path to prevent path traversal.

        Args:
            path: File path to validate

        Returns:
            Validated path

        Raises:
            ValidationError: If path is unsafe
        """
        # Check for path traversal
        if '../' in path or '..\\' in path:
            raise ValidationError(f"Path traversal detected: {path}")

        # Check for absolute paths (only allow relative)
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            # Allow if within project directory
            try:
                resolved_path = Path(path).resolve()
                project_root = Path.cwd().resolve()

                if not str(resolved_path).startswith(str(project_root)):
                    raise ValidationError(f"Path outside project directory: {path}")
            except (ValueError, OSError) as e:
                raise ValidationError(f"Invalid path: {path} ({e})")

        # Check for shell metacharacters
        if re.search(self.SHELL_METACHARACTERS, path):
            raise ValidationError(f"Invalid characters in path: {path}")

        return path

    def _default_validation(self, value: str) -> str:
        """
        Default validation for values without specific rules.

        Args:
            value: Value to validate

        Returns:
            Validated value

        Raises:
            ValidationError: If value is unsafe
        """
        # Check for shell metacharacters
        if re.search(self.SHELL_METACHARACTERS, value):
            raise ValidationError(f"Invalid characters detected: {value}")

        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(f"Potentially malicious input detected")

        # Check for null bytes
        if '\x00' in value:
            raise ValidationError("Null bytes not allowed")

        return value

    def validate_workflow_name(self, workflow_name: str) -> str:
        """
        Validate workflow name.

        Args:
            workflow_name: Name of workflow

        Returns:
            Validated workflow name

        Raises:
            ValidationError: If name is invalid
        """
        if not isinstance(workflow_name, str):
            raise ValidationError(f"Workflow name must be string, got {type(workflow_name)}")

        if not workflow_name:
            raise ValidationError("Workflow name cannot be empty")

        if len(workflow_name) > 100:
            raise ValidationError(f"Workflow name too long: {len(workflow_name)}")

        # Only allow alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', workflow_name):
            raise ValidationError(f"Invalid workflow name: {workflow_name}")

        return workflow_name

    def sanitize_string(self, value: str, max_length: int = None) -> str:
        """
        Sanitize string for safe display/logging.

        Args:
            value: String to sanitize
            max_length: Maximum length (optional)

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)

        # Remove control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

        # Truncate if needed
        if max_length and len(value) > max_length:
            value = value[:max_length] + '...'

        return value


# Global validator instance
validator = InputValidator()


# Convenience functions
def validate_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate workflow parameters"""
    return validator.validate_parameters(parameters)


def validate_workflow_name(workflow_name: str) -> str:
    """Validate workflow name"""
    return validator.validate_workflow_name(workflow_name)


def sanitize_string(value: str, max_length: int = None) -> str:
    """Sanitize string"""
    return validator.sanitize_string(value, max_length)
