"""
Attribute-Based Access Control (ABAC)
Fine-grained permissions based on attributes
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AttributeType(str, Enum):
    """Attribute types"""
    USER = "user"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"
    ACTION = "action"
    TIME = "time"
    LOCATION = "location"


@dataclass
class Policy:
    """ABAC policy definition"""
    name: str
    description: str
    effect: str  # "allow" or "deny"
    conditions: Dict[str, Any]  # Attribute conditions
    priority: int = 100  # Lower = higher priority


class ABACEngine:
    """ABAC policy engine"""
    
    def __init__(self):
        self.policies: List[Policy] = []
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default policies"""
        # Default deny policy
        self.policies.append(Policy(
            name="default_deny",
            description="Default deny all",
            effect="deny",
            conditions={},
            priority=1000,
        ))
    
    def add_policy(self, policy: Policy):
        """Add a policy"""
        self.policies.append(policy)
        # Sort by priority
        self.policies.sort(key=lambda p: p.priority)
    
    def remove_policy(self, policy_name: str):
        """Remove a policy"""
        self.policies = [p for p in self.policies if p.name != policy_name]
    
    def evaluate(
        self,
        user_attributes: Dict[str, Any],
        resource_attributes: Dict[str, Any],
        action: str,
        environment_attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Evaluate access based on attributes.
        
        Args:
            user_attributes: User attributes (roles, department, etc.)
            resource_attributes: Resource attributes (owner, type, etc.)
            action: Action being performed
            environment_attributes: Environment attributes (time, location, etc.)
        
        Returns:
            True if access allowed, False otherwise
        """
        environment_attributes = environment_attributes or {}
        
        # Evaluate policies in priority order
        for policy in self.policies:
            if self._matches_policy(policy, user_attributes, resource_attributes, action, environment_attributes):
                return policy.effect == "allow"
        
        # Default deny
        return False
    
    def _matches_policy(
        self,
        policy: Policy,
        user_attributes: Dict[str, Any],
        resource_attributes: Dict[str, Any],
        action: str,
        environment_attributes: Dict[str, Any],
    ) -> bool:
        """Check if attributes match policy conditions"""
        conditions = policy.conditions
        
        # Check user attributes
        if "user" in conditions:
            user_conds = conditions["user"]
            for key, value in user_conds.items():
                if key not in user_attributes:
                    return False
                if not self._match_value(user_attributes[key], value):
                    return False
        
        # Check resource attributes
        if "resource" in conditions:
            resource_conds = conditions["resource"]
            for key, value in resource_conds.items():
                if key not in resource_attributes:
                    return False
                if not self._match_value(resource_attributes[key], value):
                    return False
        
        # Check action
        if "action" in conditions:
            action_conds = conditions["action"]
            if isinstance(action_conds, str):
                if action != action_conds:
                    return False
            elif isinstance(action_conds, list):
                if action not in action_conds:
                    return False
        
        # Check environment attributes
        if "environment" in conditions:
            env_conds = conditions["environment"]
            for key, value in env_conds.items():
                if key not in environment_attributes:
                    return False
                if not self._match_value(environment_attributes[key], value):
                    return False
        
        return True
    
    def _match_value(self, actual: Any, expected: Any) -> bool:
        """Match attribute value with expected value"""
        if isinstance(expected, str):
            # Support wildcards
            if expected.startswith("*"):
                return actual.endswith(expected[1:])
            elif expected.endswith("*"):
                return actual.startswith(expected[:-1])
            else:
                return actual == expected
        elif isinstance(expected, list):
            return actual in expected
        elif isinstance(expected, dict):
            # Support operators
            if "eq" in expected:
                return actual == expected["eq"]
            elif "ne" in expected:
                return actual != expected["ne"]
            elif "gt" in expected:
                return actual > expected["gt"]
            elif "lt" in expected:
                return actual < expected["lt"]
            elif "in" in expected:
                return actual in expected["in"]
            elif "not_in" in expected:
                return actual not in expected["not_in"]
        else:
            return actual == expected
        
        return False


class ABACManager:
    """ABAC manager with policy management"""
    
    def __init__(self):
        self.engine = ABACEngine()
    
    def check_access(
        self,
        user_attributes: Dict[str, Any],
        resource_attributes: Dict[str, Any],
        action: str,
        environment_attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check access using ABAC"""
        return self.engine.evaluate(
            user_attributes,
            resource_attributes,
            action,
            environment_attributes,
        )
    
    def add_policy(self, policy: Policy):
        """Add a policy"""
        self.engine.add_policy(policy)
    
    def remove_policy(self, policy_name: str):
        """Remove a policy"""
        self.engine.remove_policy(policy_name)
    
    def create_policy(
        self,
        name: str,
        description: str,
        effect: str,
        conditions: Dict[str, Any],
        priority: int = 100,
    ) -> Policy:
        """Create and add a policy"""
        policy = Policy(
            name=name,
            description=description,
            effect=effect,
            conditions=conditions,
            priority=priority,
        )
        self.add_policy(policy)
        return policy


# Global ABAC manager instance
_abac_manager: Optional[ABACManager] = None


def get_abac_manager() -> ABACManager:
    """Get global ABAC manager"""
    global _abac_manager
    if _abac_manager is None:
        _abac_manager = ABACManager()
    return _abac_manager

