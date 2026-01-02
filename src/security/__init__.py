"""Security module for authentication, authorization, and input validation"""

# Import from auth.py file using importlib to avoid conflict with auth/ package
import importlib.util
import sys
from pathlib import Path

# Load auth.py module directly
_auth_file = Path(__file__).parent / "auth.py"
if _auth_file.exists():
    spec = importlib.util.spec_from_file_location("security_auth", _auth_file)
    auth_module = importlib.util.module_from_spec(spec)
    sys.modules["security_auth"] = auth_module
    spec.loader.exec_module(auth_module)
else:
    auth_module = None

# Import from auth package (directory)
from .auth import (
    RBACManager,
    Role as RBACRole,
    Permission as RBACPermission,
)
from .validation import InputValidator, ValidationResult, get_validator, validate_and_raise

# Re-export from auth.py module for backward compatibility
if auth_module:
    ROLE_PERMISSIONS = auth_module.ROLE_PERMISSIONS
    AuthManager = auth_module.AuthManager
    Permission = auth_module.Permission
    Role = auth_module.Role
    User = auth_module.User
    get_auth_manager = auth_module.get_auth_manager
    require_auth = auth_module.require_auth
    require_permission = auth_module.require_permission
    require_role = auth_module.require_role
else:
    # Fallback if auth.py doesn't exist
    ROLE_PERMISSIONS = {}
    AuthManager = None
    Permission = None
    Role = None
    User = None
    get_auth_manager = None
    require_auth = None
    require_permission = None
    require_role = None

__all__ = [
    # Auth
    "AuthManager",
    "User",
    "Role",
    "Permission",
    "get_auth_manager",
    "require_auth",
    "require_permission",
    "require_role",
    "ROLE_PERMISSIONS",
    # Validation
    "InputValidator",
    "ValidationResult",
    "get_validator",
    "validate_and_raise",
]
