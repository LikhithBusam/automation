"""
Authentication and Authorization Module

Provides JWT-based authentication, API key management, and RBAC for the application.
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles for RBAC"""

    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    SERVICE = "service"


class Permission(str, Enum):
    """Granular permissions"""

    # GitHub operations
    GITHUB_READ = "github:read"
    GITHUB_WRITE = "github:write"
    GITHUB_ADMIN = "github:admin"

    # Filesystem operations
    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    FS_DELETE = "fs:delete"

    # Memory operations
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"

    # Agent operations
    AGENT_EXECUTE = "agent:execute"
    AGENT_ADMIN = "agent:admin"

    # System operations
    SYSTEM_CONFIG = "system:config"
    SYSTEM_ADMIN = "system:admin"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.DEVELOPER: [
        Permission.GITHUB_READ,
        Permission.GITHUB_WRITE,
        Permission.FS_READ,
        Permission.FS_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.AGENT_EXECUTE,
    ],
    Role.VIEWER: [
        Permission.GITHUB_READ,
        Permission.FS_READ,
        Permission.MEMORY_READ,
    ],
    Role.SERVICE: [
        Permission.GITHUB_READ,
        Permission.GITHUB_WRITE,
        Permission.FS_READ,
        Permission.FS_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.AGENT_EXECUTE,
    ],
}


@dataclass
class User:
    """User data model"""

    user_id: str
    username: str
    email: Optional[str]
    role: Role
    api_keys: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in ROLE_PERMISSIONS.get(self.role, [])

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(self.has_permission(p) for p in permissions)


class AuthManager:
    """Manages authentication and authorization"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiry_hours: int = 24,
        api_key_prefix: str = "ak_",
    ):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", self._generate_secret())
        self.token_expiry_hours = token_expiry_hours
        self.api_key_prefix = api_key_prefix
        self.algorithm = "HS256"

        # In-memory user store (replace with database in production)
        self._users: Dict[str, User] = {}
        self._api_key_to_user: Dict[str, str] = {}

        # Create default admin user
        self._create_default_admin()

    def _generate_secret(self) -> str:
        """Generate a random secret key"""
        return secrets.token_urlsafe(32)

    def _create_default_admin(self):
        """Create default admin user"""
        if not self._users:
            admin_user = User(
                user_id="admin_001",
                username="admin",
                email="admin@localhost",
                role=Role.ADMIN,
                api_keys=[],
                created_at=datetime.utcnow(),
                is_active=True,
            )
            self._users[admin_user.user_id] = admin_user
            logger.info("Default admin user created")

    def create_user(self, username: str, email: Optional[str], role: Role = Role.DEVELOPER) -> User:
        """Create a new user"""
        user_id = hashlib.sha256(f"{username}:{datetime.utcnow()}".encode()).hexdigest()[:16]

        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            api_keys=[],
            created_at=datetime.utcnow(),
        )

        self._users[user_id] = user
        logger.info(f"User created: {username} ({user_id}) with role {role}")
        return user

    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for user"""
        if user_id not in self._users:
            raise ValueError(f"User {user_id} not found")

        # Generate secure random key
        random_part = secrets.token_urlsafe(32)
        api_key = f"{self.api_key_prefix}{random_part}"

        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Store mapping
        self._api_key_to_user[key_hash] = user_id
        self._users[user_id].api_keys.append(key_hash)

        logger.info(f"API key generated for user {user_id}")
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[User]:
        """Validate API key and return user"""
        if not api_key or not api_key.startswith(self.api_key_prefix):
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        user_id = self._api_key_to_user.get(key_hash)

        if not user_id:
            logger.warning(f"Invalid API key attempt")
            return None

        user = self._users.get(user_id)
        if not user or not user.is_active:
            logger.warning(f"API key for inactive user: {user_id}")
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        return user

    def revoke_api_key(self, user_id: str, api_key: str) -> bool:
        """Revoke an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash in self._api_key_to_user:
            del self._api_key_to_user[key_hash]

            if user_id in self._users:
                user = self._users[user_id]
                if key_hash in user.api_keys:
                    user.api_keys.remove(key_hash)

            logger.info(f"API key revoked for user {user_id}")
            return True

        return False

    def generate_jwt_token(self, user_id: str) -> str:
        """Generate JWT token for user"""
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"JWT token generated for user {user_id}")
        return token

    def validate_jwt_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")

            if not user_id:
                return None

            user = self._users.get(user_id)
            if user and user.is_active:
                user.last_login = datetime.utcnow()
                return user

            return None

        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def authenticate(self, credentials: str, auth_type: str = "api_key") -> Optional[User]:
        """Authenticate user with credentials"""
        if auth_type == "api_key":
            return self.validate_api_key(credentials)
        elif auth_type == "jwt":
            return self.validate_jwt_token(credentials)
        else:
            logger.error(f"Unknown auth type: {auth_type}")
            return None

    def authorize(self, user: User, permission: Permission) -> bool:
        """Check if user is authorized for permission"""
        if not user.is_active:
            return False

        return user.has_permission(permission)

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)

    def list_users(self) -> List[User]:
        """List all users"""
        return list(self._users.values())

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user"""
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            logger.info(f"User deactivated: {user_id}")
            return True
        return False


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create global auth manager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def require_auth(auth_type: str = "api_key"):
    """Decorator to require authentication"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract credentials from kwargs
            credentials = kwargs.get("api_key") or kwargs.get("token")

            if not credentials:
                raise PermissionError("Authentication required")

            auth_manager = get_auth_manager()
            user = auth_manager.authenticate(credentials, auth_type)

            if not user:
                raise PermissionError("Invalid credentials")

            # Add user to kwargs
            kwargs["current_user"] = user
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission(permission: Permission):
    """Decorator to require specific permission"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")

            if not user:
                raise PermissionError("Authentication required")

            auth_manager = get_auth_manager()
            if not auth_manager.authorize(user, permission):
                raise PermissionError(f"Permission denied: {permission}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: Role):
    """Decorator to require specific role"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")

            if not user:
                raise PermissionError("Authentication required")

            if user.role != role and user.role != Role.ADMIN:
                raise PermissionError(f"Role required: {role}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
