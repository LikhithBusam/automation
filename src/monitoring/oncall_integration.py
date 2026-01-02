"""
On-Call Integration with Alertmanager
Manages on-call rotation and escalation policies
"""

import logging
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class OnCallManager:
    """Manages on-call rotation and escalation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize on-call manager.
        
        Args:
            config_path: Path to on-call configuration file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "monitoring" / "oncall" / "oncall_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.schedules = self.config.get("schedules", {})
        self.escalation_policies = self.config.get("escalation_policies", {})
        self.alert_routing = self.config.get("alert_routing", {})
    
    def _load_config(self) -> Dict[str, Any]:
        """Load on-call configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load on-call config: {e}")
            return {}
    
    def get_current_oncall(self, schedule_name: str) -> List[str]:
        """
        Get current on-call users for a schedule.
        
        Args:
            schedule_name: Name of the schedule
            
        Returns:
            List of on-call user emails
        """
        schedule = self.schedules.get(schedule_name, {})
        rotations = schedule.get("rotations", [])
        
        if not rotations:
            return []
        
        # For simplicity, return first rotation's users
        # In production, calculate based on current time and rotation type
        current_rotation = rotations[0]
        return current_rotation.get("users", [])
    
    def get_escalation_policy(self, policy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get escalation policy.
        
        Args:
            policy_name: Name of the escalation policy
            
        Returns:
            Escalation policy configuration
        """
        return self.escalation_policies.get(policy_name)
    
    def get_alert_routing(self, severity: str) -> Dict[str, Any]:
        """
        Get alert routing configuration for severity.
        
        Args:
            severity: Alert severity (critical, high, medium, low)
            
        Returns:
            Alert routing configuration
        """
        return self.alert_routing.get(severity, {})
    
    def should_escalate(self, alert_severity: str, alert_duration_minutes: int) -> bool:
        """
        Determine if alert should be escalated.
        
        Args:
            alert_severity: Alert severity
            alert_duration_minutes: How long alert has been active
            
        Returns:
            True if should escalate
        """
        routing = self.get_alert_routing(alert_severity)
        auto_escalate = routing.get("auto_escalate", False)
        
        if not auto_escalate:
            return False
        
        # Check escalation policy steps
        policy_name = routing.get("escalation_policy")
        if not policy_name:
            return False
        
        policy = self.get_escalation_policy(policy_name)
        if not policy:
            return False
        
        # Check if any escalation step should trigger
        steps = policy.get("steps", [])
        for step in steps:
            delay_minutes = step.get("delay_minutes", 0)
            if alert_duration_minutes >= delay_minutes:
                return True
        
        return False


# Global on-call manager instance
_oncall_manager: Optional[OnCallManager] = None


def get_oncall_manager() -> OnCallManager:
    """Get global on-call manager"""
    global _oncall_manager
    if _oncall_manager is None:
        _oncall_manager = OnCallManager()
    return _oncall_manager

