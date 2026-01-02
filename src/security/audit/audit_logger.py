"""
Comprehensive Audit Logging System
Immutable logs with cryptographic signatures
"""

import logging
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types"""
    USER_ACTION = "user_action"
    ADMIN_CHANGE = "admin_change"
    SECURITY_EVENT = "security_event"
    API_CALL = "api_call"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION_CHANGE = "configuration_change"


@dataclass
class AuditLogEntry:
    """Audit log entry"""
    timestamp: str
    event_type: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_data: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    status: str  # "success", "failure", "error"
    error_message: Optional[str]
    metadata: Dict[str, Any]
    signature: Optional[str] = None


class AuditLogger:
    """Comprehensive audit logger"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        signing_key: Optional[str] = None,
        log_retention_days: int = 2555,  # 7 years for compliance
    ):
        """
        Initialize audit logger.
        
        Args:
            redis_client: Redis client for log storage
            signing_key: Key for cryptographic signatures
            log_retention_days: Log retention period in days
        """
        self.redis_client = redis_client
        self.signing_key = signing_key or "default_signing_key"  # Use secure key in production
        self.log_retention_days = log_retention_days
        self.key_prefix = "audit:"
        self.index_prefix = "audit_index:"
    
    def _make_key(self, log_id: str) -> str:
        """Create Redis key for audit log"""
        return f"{self.key_prefix}{log_id}"
    
    def _generate_log_id(self) -> str:
        """Generate unique log ID"""
        timestamp = datetime.now(timezone.utc).timestamp()
        random_part = hashlib.md5(f"{timestamp}{id(self)}".encode()).hexdigest()[:8]
        return f"{int(timestamp)}_{random_part}"
    
    def _sign_log(self, log_data: Dict[str, Any]) -> str:
        """Create cryptographic signature for log entry"""
        # Create canonical JSON representation
        canonical_json = json.dumps(log_data, sort_keys=True, separators=(",", ":"))
        
        # Create HMAC signature
        signature = hmac.new(
            self.signing_key.encode(),
            canonical_json.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log audit event"""
        log_id = self._generate_log_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create log entry
        log_entry = AuditLogEntry(
            timestamp=timestamp,
            event_type=event_type.value,
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_data=response_data,
            status=status,
            error_message=error_message,
            metadata=metadata or {},
        )
        
        # Convert to dict
        log_dict = asdict(log_entry)
        
        # Add signature
        signature = self._sign_log(log_dict)
        log_dict["signature"] = signature
        
        # Store in Redis
        key = self._make_key(log_id)
        await self.redis_client.hset(key, mapping={
            k: json.dumps(v) if isinstance(v, dict) else str(v)
            for k, v in log_dict.items()
        })
        
        # Set expiration
        await self.redis_client.expire(key, self.log_retention_days * 86400)
        
        # Create indexes for fast queries
        await self._create_indexes(log_id, log_entry)
        
        return log_id
    
    async def _create_indexes(self, log_id: str, entry: AuditLogEntry):
        """Create indexes for fast querying"""
        timestamp = datetime.fromisoformat(entry.timestamp)
        date_key = timestamp.strftime("%Y-%m-%d")
        
        # Index by date
        date_index_key = f"{self.index_prefix}date:{date_key}"
        await self.redis_client.sadd(date_index_key, log_id)
        await self.redis_client.expire(date_index_key, self.log_retention_days * 86400)
        
        # Index by user
        if entry.user_id:
            user_index_key = f"{self.index_prefix}user:{entry.user_id}"
            await self.redis_client.sadd(user_index_key, log_id)
            await self.redis_client.expire(user_index_key, self.log_retention_days * 86400)
        
        # Index by event type
        event_index_key = f"{self.index_prefix}event:{entry.event_type}"
        await self.redis_client.sadd(event_index_key, log_id)
        await self.redis_client.expire(event_index_key, self.log_retention_days * 86400)
        
        # Index by resource
        if entry.resource_type and entry.resource_id:
            resource_index_key = f"{self.index_prefix}resource:{entry.resource_type}:{entry.resource_id}"
            await self.redis_client.sadd(resource_index_key, log_id)
            await self.redis_client.expire(resource_index_key, self.log_retention_days * 86400)
    
    async def get_log(self, log_id: str) -> Optional[AuditLogEntry]:
        """Get audit log entry by ID"""
        key = self._make_key(log_id)
        log_data = await self.redis_client.hgetall(key)
        
        if not log_data:
            return None
        
        # Deserialize
        entry_dict = {
            k.decode(): json.loads(v.decode()) if v.decode().startswith("{") else v.decode()
            for k, v in log_data.items()
        }
        
        # Verify signature
        signature = entry_dict.pop("signature")
        expected_signature = self._sign_log(entry_dict)
        
        if signature != expected_signature:
            logger.warning(f"Audit log signature mismatch for {log_id}")
            return None
        
        return AuditLogEntry(**entry_dict)
    
    async def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """Query audit logs"""
        # Build query using indexes
        log_ids = set()
        
        # Query by date range
        if start_date or end_date:
            current_date = start_date or datetime.utcnow() - timedelta(days=30)
            end_date = end_date or datetime.utcnow()
            
            while current_date <= end_date:
                date_key = current_date.strftime("%Y-%m-%d")
                date_index_key = f"{self.index_prefix}date:{date_key}"
                ids = await self.redis_client.smembers(date_index_key)
                log_ids.update(id.decode() for id in ids)
                current_date += timedelta(days=1)
        
        # Filter by user
        if user_id:
            user_index_key = f"{self.index_prefix}user:{user_id}"
            user_ids = await self.redis_client.smembers(user_index_key)
            user_log_ids = {id.decode() for id in user_ids}
            log_ids = log_ids.intersection(user_log_ids) if log_ids else user_log_ids
        
        # Filter by event type
        if event_type:
            event_index_key = f"{self.index_prefix}event:{event_type.value}"
            event_ids = await self.redis_client.smembers(event_index_key)
            event_log_ids = {id.decode() for id in event_ids}
            log_ids = log_ids.intersection(event_log_ids) if log_ids else event_log_ids
        
        # Filter by resource
        if resource_type and resource_id:
            resource_index_key = f"{self.index_prefix}resource:{resource_type}:{resource_id}"
            resource_ids = await self.redis_client.smembers(resource_index_key)
            resource_log_ids = {id.decode() for id in resource_ids}
            log_ids = log_ids.intersection(resource_log_ids) if log_ids else resource_log_ids
        
        # Get log entries
        logs = []
        for log_id in list(log_ids)[:limit]:
            entry = await self.get_log(log_id)
            if entry:
                logs.append(entry)
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return logs
    
    async def verify_log_integrity(self, log_id: str) -> bool:
        """Verify log entry integrity"""
        entry = await self.get_log(log_id)
        return entry is not None

