"""
Role-Based Access Control (RBAC) System
Supports multiple roles with hierarchical permissions
"""

import logging
from enum import Enum
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """System roles"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    CUSTOM = "custom"


class Permission(str, Enum):
    """System permissions"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Workflow management
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"
    
    # Agent management
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    
    # Configuration management
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    
    # Memory management
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    
    # Codebase access
    CODEBASE_READ = "codebase:read"
    CODEBASE_WRITE = "codebase:write"


@dataclass
class RoleDefinition:
    """Role definition with permissions"""
    name: str
    permissions: Set[Permission]
    inherits_from: Optional[List[str]] = None
    description: str = ""


class RBACManager:
    """RBAC manager for permission checking"""
    
    def __init__(self):
        self.roles: Dict[str, RoleDefinition] = {}
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize default system roles"""
        # Super Admin - All permissions
        self.roles[Role.SUPER_ADMIN] = RoleDefinition(
            name=Role.SUPER_ADMIN,
            permissions=set(Permission),
            description="Full system access"
        )
        
        # Admin - Most permissions except system admin
        self.roles[Role.ADMIN] = RoleDefinition(
            name=Role.ADMIN,
            permissions={
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.WORKFLOW_CREATE,
                Permission.WORKFLOW_READ,
                Permission.WORKFLOW_UPDATE,
                Permission.WORKFLOW_DELETE,
                Permission.WORKFLOW_EXECUTE,
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_DELETE,
                Permission.CONFIG_READ,
                Permission.CONFIG_UPDATE,
                Permission.SYSTEM_MONITOR,
                Permission.MEMORY_READ,
                Permission.MEMORY_WRITE,
                Permission.MEMORY_DELETE,
                Permission.CODEBASE_READ,
                Permission.CODEBASE_WRITE,
            },
            description="Administrative access"
        )
        
        # Developer - Workflow and agent management
        self.roles[Role.DEVELOPER] = RoleDefinition(
            name=Role.DEVELOPER,
            permissions={
                Permission.WORKFLOW_CREATE,
                Permission.WORKFLOW_READ,
                Permission.WORKFLOW_UPDATE,
                Permission.WORKFLOW_EXECUTE,
                Permission.AGENT_READ,
                Permission.MEMORY_READ,
                Permission.MEMORY_WRITE,
                Permission.CODEBASE_READ,
                Permission.CODEBASE_WRITE,
            },
            description="Developer access for workflows and agents"
        )
        
        # Viewer - Read-only access
        self.roles[Role.VIEWER] = RoleDefinition(
            name=Role.VIEWER,
            permissions={
                Permission.WORKFLOW_READ,
                Permission.AGENT_READ,
                Permission.CONFIG_READ,
                Permission.MEMORY_READ,
                Permission.CODEBASE_READ,
            },
            description="Read-only access"
        )
    
    def create_custom_role(
        self,
        name: str,
        permissions: Set[Permission],
        inherits_from: Optional[List[str]] = None,
        description: str = "",
    ) -> RoleDefinition:
        """Create a custom role"""
        # Collect permissions from inherited roles
        all_permissions = set(permissions)
        if inherits_from:
            for role_name in inherits_from:
                if role_name in self.roles:
                    all_permissions.update(self.roles[role_name].permissions)
        
        role_def = RoleDefinition(
            name=name,
            permissions=all_permissions,
            inherits_from=inherits_from,
            description=description,
        )
        
        self.roles[name] = role_def
        return role_def
    
    def has_permission(self, user_roles: List[str], permission: Permission) -> bool:
        """Check if user has permission"""
        for role_name in user_roles:
            if role_name in self.roles:
                role = self.roles[role_name]
                if permission in role.permissions:
                    return True
        return False
    
    def has_any_permission(self, user_roles: List[str], permissions: List[Permission]) -> bool:
        """Check if user has any of the permissions"""
        return any(self.has_permission(user_roles, perm) for perm in permissions)
    
    def has_all_permissions(self, user_roles: List[str], permissions: List[Permission]) -> bool:
        """Check if user has all permissions"""
        return all(self.has_permission(user_roles, perm) for perm in permissions)
    
    def get_user_permissions(self, user_roles: List[str]) -> Set[Permission]:
        """Get all permissions for user roles"""
        permissions = set()
        for role_name in user_roles:
            if role_name in self.roles:
                permissions.update(self.roles[role_name].permissions)
        return permissions
    
    def get_role(self, role_name: str) -> Optional[RoleDefinition]:
        """Get role definition"""
        return self.roles.get(role_name)


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager

