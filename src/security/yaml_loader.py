"""
Secure YAML Loading Utilities
Provides safe YAML loading with size limits and validation
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class YAMLSecurityError(Exception):
    """Raised when YAML loading security checks fail"""
    pass


class SecureYAMLLoader:
    """
    Secure YAML loader with safety features:
    - Uses yaml.safe_load() to prevent code execution
    - File size limits to prevent DoS
    - Path validation to prevent directory traversal
    - Schema validation (optional)
    """

    def __init__(
        self,
        max_file_size_mb: int = 10,
        allowed_directories: Optional[list] = None
    ):
        """
        Initialize secure YAML loader.

        Args:
            max_file_size_mb: Maximum allowed file size in MB
            allowed_directories: List of allowed directory paths (None = no restriction)
        """
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.allowed_directories = allowed_directories

    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Securely load YAML file with validation.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML content as dictionary

        Raises:
            YAMLSecurityError: If security checks fail
            yaml.YAMLError: If YAML parsing fails
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")

        # Check file is actually a file (not a directory)
        if not path.is_file():
            raise YAMLSecurityError(f"Path is not a file: {file_path}")

        # Validate path is in allowed directories
        if self.allowed_directories:
            path_resolved = path.resolve()
            allowed = False
            for allowed_dir in self.allowed_directories:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    path_resolved.relative_to(allowed_path)
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                raise YAMLSecurityError(
                    f"File path outside allowed directories: {file_path}"
                )

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size_bytes:
            raise YAMLSecurityError(
                f"YAML file too large: {file_size / 1024 / 1024:.2f}MB "
                f"(max: {self.max_file_size_bytes / 1024 / 1024:.2f}MB)"
            )

        # Load YAML using safe_load (prevents code execution)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                logger.warning(f"YAML file is empty: {file_path}")
                return {}

            if not isinstance(data, dict):
                raise YAMLSecurityError(
                    f"YAML root must be a dictionary, got {type(data).__name__}"
                )

            logger.debug(f"Successfully loaded YAML: {file_path}")
            return data

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise

    def load_string(self, yaml_string: str, max_length: int = 100000) -> Dict[str, Any]:
        """
        Securely load YAML from string with size limit.

        Args:
            yaml_string: YAML content as string
            max_length: Maximum string length (default: 100KB)

        Returns:
            Parsed YAML content as dictionary

        Raises:
            YAMLSecurityError: If security checks fail
            yaml.YAMLError: If YAML parsing fails
        """
        # Check string length
        if len(yaml_string) > max_length:
            raise YAMLSecurityError(
                f"YAML string too large: {len(yaml_string)} chars "
                f"(max: {max_length})"
            )

        # Load YAML using safe_load
        try:
            data = yaml.safe_load(yaml_string)

            if data is None:
                return {}

            if not isinstance(data, dict):
                raise YAMLSecurityError(
                    f"YAML root must be a dictionary, got {type(data).__name__}"
                )

            return data

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise

    def validate_schema(self, data: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate YAML data contains required keys.

        Args:
            data: Parsed YAML data
            required_keys: List of required top-level keys

        Returns:
            True if valid

        Raises:
            YAMLSecurityError: If validation fails
        """
        missing_keys = []
        for key in required_keys:
            if key not in data:
                missing_keys.append(key)

        if missing_keys:
            raise YAMLSecurityError(
                f"YAML missing required keys: {', '.join(missing_keys)}"
            )

        return True


# Global loader instance with default settings
_default_loader = SecureYAMLLoader(
    max_file_size_mb=10,
    allowed_directories=None  # No restriction by default
)


# Convenience functions
def load_yaml_file(
    file_path: str,
    max_size_mb: int = 10,
    allowed_dirs: Optional[list] = None
) -> Dict[str, Any]:
    """
    Load YAML file securely.

    Args:
        file_path: Path to YAML file
        max_size_mb: Maximum file size in MB
        allowed_dirs: Allowed directories (None = no restriction)

    Returns:
        Parsed YAML content

    Raises:
        YAMLSecurityError: If security checks fail

    Example:
        config = load_yaml_file("config/agents.yaml")
    """
    loader = SecureYAMLLoader(max_size_mb, allowed_dirs)
    return loader.load_file(file_path)


def load_yaml_string(yaml_string: str, max_length: int = 100000) -> Dict[str, Any]:
    """
    Load YAML from string securely.

    Args:
        yaml_string: YAML content as string
        max_length: Maximum string length

    Returns:
        Parsed YAML content

    Raises:
        YAMLSecurityError: If security checks fail

    Example:
        config = load_yaml_string("key: value")
    """
    return _default_loader.load_string(yaml_string, max_length)


def validate_yaml_schema(data: Dict[str, Any], required_keys: list) -> bool:
    """
    Validate YAML data schema.

    Args:
        data: Parsed YAML data
        required_keys: Required top-level keys

    Returns:
        True if valid

    Raises:
        YAMLSecurityError: If validation fails

    Example:
        validate_yaml_schema(config, ["agents", "workflows"])
    """
    return _default_loader.validate_schema(data, required_keys)
