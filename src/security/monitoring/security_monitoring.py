"""
Security Monitoring System
IDS, anomaly detection, real-time alerts, SIEM integration
"""

import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class SecurityAlert:
    """Security alert"""
    alert_id: str
    alert_type: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    source_ip: Optional[str]
    user_id: Optional[str]
    description: str
    metadata: Dict[str, Any]


class AnomalyDetector:
    """Anomaly detection for unusual access patterns"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.baseline_window = timedelta(hours=24)
        self.anomaly_threshold = 3.0  # Standard deviations
    
    async def detect_anomaly(
        self,
        user_id: str,
        action: str,
        ip_address: str,
        timestamp: datetime,
    ) -> bool:
        """Detect anomalous behavior"""
        # Check multiple anomaly patterns
        anomalies = [
            await self._check_rate_anomaly(user_id, action, timestamp),
            await self._check_location_anomaly(user_id, ip_address, timestamp),
            await self._check_time_anomaly(user_id, timestamp),
            await self._check_behavior_anomaly(user_id, action, timestamp),
        ]
        
        return any(anomalies)
    
    async def _check_rate_anomaly(self, user_id: str, action: str, timestamp: datetime) -> bool:
        """Check for rate anomalies"""
        key = f"anomaly:rate:{user_id}:{action}"
        
        # Get recent activity count
        window_start = timestamp - timedelta(minutes=5)
        count = await self._count_events_in_window(key, window_start, timestamp)
        
        # Get baseline
        baseline_key = f"baseline:rate:{user_id}:{action}"
        baseline = await self._get_baseline(baseline_key)
        
        if baseline:
            mean, std = baseline
            if count > mean + (self.anomaly_threshold * std):
                return True
        
        # Update baseline
        await self._update_baseline(baseline_key, count)
        
        return False
    
    async def _check_location_anomaly(self, user_id: str, ip_address: str, timestamp: datetime) -> bool:
        """Check for location anomalies"""
        key = f"anomaly:location:{user_id}"
        
        # Get recent locations
        recent_locations = await self._get_recent_locations(key, timestamp - timedelta(hours=1))
        
        # Check if new location is far from recent locations
        if recent_locations and ip_address not in recent_locations:
            # Simple check: if user accessed from multiple countries in short time
            if len(recent_locations) > 2:
                return True
        
        # Update location history
        await self._add_location(key, ip_address, timestamp)
        
        return False
    
    async def _check_time_anomaly(self, user_id: str, timestamp: datetime) -> bool:
        """Check for time-based anomalies"""
        hour = timestamp.hour
        
        # Check if access is outside normal hours
        baseline_key = f"baseline:time:{user_id}"
        normal_hours = await self._get_normal_hours(baseline_key)
        
        if normal_hours:
            if hour not in normal_hours:
                return True
        
        # Update baseline
        await self._update_normal_hours(baseline_key, hour)
        
        return False
    
    async def _check_behavior_anomaly(self, user_id: str, action: str, timestamp: datetime) -> bool:
        """Check for behavioral anomalies"""
        key = f"anomaly:behavior:{user_id}"
        
        # Get action history
        recent_actions = await self._get_recent_actions(key, timestamp - timedelta(hours=1))
        
        # Check if action is unusual for this user
        if recent_actions:
            action_frequency = defaultdict(int)
            for act in recent_actions:
                action_frequency[act] += 1
            
            # If this action is rare for user, might be anomaly
            if action not in action_frequency or action_frequency[action] < 2:
                return True
        
        # Update action history
        await self._add_action(key, action, timestamp)
        
        return False
    
    async def _count_events_in_window(self, key: str, start: datetime, end: datetime) -> int:
        """Count events in time window"""
        # Implementation using Redis sorted sets
        count = await self.redis_client.zcount(key, start.timestamp(), end.timestamp())
        return count
    
    async def _get_baseline(self, key: str) -> Optional[tuple]:
        """Get baseline statistics"""
        data = await self.redis_client.hgetall(key)
        if data:
            mean = float(data.get(b"mean", 0))
            std = float(data.get(b"std", 0))
            return (mean, std)
        return None
    
    async def _update_baseline(self, key: str, value: float):
        """Update baseline statistics"""
        baseline = await self._get_baseline(key)
        if baseline:
            mean, std = baseline
            # Simple moving average
            new_mean = (mean * 0.9) + (value * 0.1)
            new_std = std * 0.9  # Simplified
            await self.redis_client.hset(key, mapping={"mean": new_mean, "std": new_std})
        else:
            await self.redis_client.hset(key, mapping={"mean": value, "std": 1.0})
    
    async def _get_recent_locations(self, key: str, since: datetime) -> List[str]:
        """Get recent locations"""
        locations = await self.redis_client.zrangebyscore(key, since.timestamp(), "+inf")
        return [loc.decode() for loc in locations]
    
    async def _add_location(self, key: str, location: str, timestamp: datetime):
        """Add location to history"""
        await self.redis_client.zadd(key, {location: timestamp.timestamp()})
        await self.redis_client.expire(key, 86400)  # 24 hours
    
    async def _get_normal_hours(self, key: str) -> Optional[set]:
        """Get normal access hours"""
        hours = await self.redis_client.smembers(key)
        return {int(h.decode()) for h in hours} if hours else None
    
    async def _update_normal_hours(self, key: str, hour: int):
        """Update normal access hours"""
        await self.redis_client.sadd(key, hour)
        await self.redis_client.expire(key, 86400 * 30)  # 30 days
    
    async def _get_recent_actions(self, key: str, since: datetime) -> List[str]:
        """Get recent actions"""
        actions = await self.redis_client.zrangebyscore(key, since.timestamp(), "+inf")
        return [act.decode() for act in actions]
    
    async def _add_action(self, key: str, action: str, timestamp: datetime):
        """Add action to history"""
        await self.redis_client.zadd(key, {action: timestamp.timestamp()})
        await self.redis_client.expire(key, 86400)  # 24 hours


class IntrusionDetectionSystem:
    """Intrusion Detection System"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.patterns = self._load_detection_patterns()
    
    def _load_detection_patterns(self) -> List[Dict[str, Any]]:
        """Load IDS detection patterns"""
        return [
            {
                "name": "sql_injection",
                "pattern": r"(union|select|insert|delete|drop|exec|script)",
                "severity": "high",
            },
            {
                "name": "xss_attempt",
                "pattern": r"(<script|javascript:|onerror=|onload=)",
                "severity": "medium",
            },
            {
                "name": "path_traversal",
                "pattern": r"(\.\./|\.\.\\|/etc/passwd|/etc/shadow)",
                "severity": "high",
            },
            {
                "name": "command_injection",
                "pattern": r"(\||;|\$\(|`|&&)",
                "severity": "high",
            },
        ]
    
    async def detect_intrusion(
        self,
        request_data: Dict[str, Any],
        ip_address: str,
    ) -> Optional[Dict[str, Any]]:
        """Detect potential intrusion"""
        # Check request data against patterns
        request_str = str(request_data).lower()
        
        for pattern_config in self.patterns:
            pattern = pattern_config["pattern"]
            if re.search(pattern, request_str, re.IGNORECASE):
                return {
                    "detected": True,
                    "pattern": pattern_config["name"],
                    "severity": pattern_config["severity"],
                    "ip_address": ip_address,
                }
        
        return None


class SIEMIntegration:
    """SIEM system integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.siem_type = config.get("type", "splunk")
    
    async def send_alert(self, alert: SecurityAlert):
        """Send alert to SIEM system"""
        if self.siem_type == "splunk":
            await self._send_to_splunk(alert)
        elif self.siem_type == "elastic":
            await self._send_to_elastic(alert)
        elif self.siem_type == "datadog":
            await self._send_to_datadog(alert)
        else:
            logger.warning(f"Unknown SIEM type: {self.siem_type}")
    
    async def _send_to_splunk(self, alert: SecurityAlert):
        """Send alert to Splunk"""
        try:
            import httpx
            
            splunk_url = self.config.get("splunk_url")
            splunk_token = self.config.get("splunk_token")
            
            event = {
                "time": alert.timestamp.isoformat(),
                "event": {
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "source_ip": alert.source_ip,
                    "user_id": alert.user_id,
                    "description": alert.description,
                    "metadata": alert.metadata,
                },
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{splunk_url}/services/collector/event",
                    headers={"Authorization": f"Splunk {splunk_token}"},
                    json=event,
                )
        except Exception as e:
            logger.error(f"Failed to send alert to Splunk: {e}")
    
    async def _send_to_elastic(self, alert: SecurityAlert):
        """Send alert to Elasticsearch"""
        try:
            import httpx
            
            elastic_url = self.config.get("elastic_url")
            elastic_index = self.config.get("elastic_index", "security-alerts")
            
            event = {
                "@timestamp": alert.timestamp.isoformat(),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "source_ip": alert.source_ip,
                "user_id": alert.user_id,
                "description": alert.description,
                "metadata": alert.metadata,
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{elastic_url}/{elastic_index}/_doc",
                    json=event,
                )
        except Exception as e:
            logger.error(f"Failed to send alert to Elasticsearch: {e}")
    
    async def _send_to_datadog(self, alert: SecurityAlert):
        """Send alert to Datadog"""
        try:
            import httpx
            
            datadog_url = self.config.get("datadog_url", "https://api.datadoghq.com/api/v1/events")
            datadog_api_key = self.config.get("datadog_api_key")
            
            event = {
                "title": f"Security Alert: {alert.alert_type}",
                "text": alert.description,
                "alert_type": alert.severity,
                "tags": [
                    f"alert_type:{alert.alert_type}",
                    f"severity:{alert.severity}",
                ],
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    datadog_url,
                    headers={"DD-API-KEY": datadog_api_key},
                    json=event,
                )
        except Exception as e:
            logger.error(f"Failed to send alert to Datadog: {e}")


class SecurityMonitoringSystem:
    """Unified security monitoring system"""
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        
        self.anomaly_detector = AnomalyDetector(redis_client)
        self.ids = IntrusionDetectionSystem(redis_client)
        
        if config.get("siem"):
            self.siem = SIEMIntegration(config["siem"])
        else:
            self.siem = None
        
        self.alert_handlers: List[Callable] = []
    
    async def monitor_request(
        self,
        user_id: Optional[str],
        action: str,
        request_data: Dict[str, Any],
        ip_address: str,
        timestamp: datetime,
    ) -> List[SecurityAlert]:
        """Monitor request and generate alerts"""
        alerts = []
        
        # Check for intrusions
        intrusion = await self.ids.detect_intrusion(request_data, ip_address)
        if intrusion:
            alert = SecurityAlert(
                alert_id=f"ids_{timestamp.timestamp()}",
                alert_type="intrusion_detection",
                severity=intrusion["severity"],
                timestamp=timestamp,
                source_ip=ip_address,
                user_id=user_id,
                description=f"Intrusion detected: {intrusion['pattern']}",
                metadata=intrusion,
            )
            alerts.append(alert)
        
        # Check for anomalies
        if user_id:
            is_anomaly = await self.anomaly_detector.detect_anomaly(
                user_id, action, ip_address, timestamp
            )
            if is_anomaly:
                alert = SecurityAlert(
                    alert_id=f"anomaly_{timestamp.timestamp()}",
                    alert_type="anomaly_detection",
                    severity="medium",
                    timestamp=timestamp,
                    source_ip=ip_address,
                    user_id=user_id,
                    description=f"Anomalous behavior detected for user {user_id}",
                    metadata={"action": action},
                )
                alerts.append(alert)
        
        # Send alerts
        for alert in alerts:
            await self._handle_alert(alert)
        
        return alerts
    
    async def _handle_alert(self, alert: SecurityAlert):
        """Handle security alert"""
        # Log alert
        logger.warning(f"Security alert: {alert.alert_type} - {alert.description}")
        
        # Send to SIEM
        if self.siem:
            await self.siem.send_alert(alert)
        
        # Call custom handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def register_alert_handler(self, handler: Callable):
        """Register custom alert handler"""
        self.alert_handlers.append(handler)
