"""
Session Management with Secure Token Handling
Secure session storage and token management
"""

import logging
import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Session definition"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Dict[str, Any]


class SessionManager:
    """Secure session management"""
    
    def __init__(self, redis_client: redis.Redis, session_ttl: int = 3600):
        """
        Initialize session manager.
        
        Args:
            redis_client: Redis client for session storage
            session_ttl: Session TTL in seconds (default: 1 hour)
        """
        self.redis_client = redis_client
        self.session_ttl = session_ttl
        self.key_prefix = "session:"
    
    def _make_key(self, session_id: str) -> str:
        """Create Redis key for session"""
        return f"{self.key_prefix}{session_id}"
    
    def generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(32)
    
    async def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Session:
        """Create new session"""
        session_id = self.generate_session_id()
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl or self.session_ttl)
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        
        # Store in Redis
        key = self._make_key(session_id)
        session_data = {
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "metadata": str(session.metadata),  # JSON serialize in production
        }
        
        await self.redis_client.hset(key, mapping=session_data)
        await self.redis_client.expire(key, ttl or self.session_ttl)
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        key = self._make_key(session_id)
        session_data = await self.redis_client.hgetall(key)
        
        if not session_data:
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(session_data[b"expires_at"].decode())
        if datetime.utcnow() > expires_at:
            await self.delete_session(session_id)
            return None
        
        return Session(
            session_id=session_id,
            user_id=session_data[b"user_id"].decode(),
            created_at=datetime.fromisoformat(session_data[b"created_at"].decode()),
            expires_at=expires_at,
            last_activity=datetime.fromisoformat(session_data[b"last_activity"].decode()),
            ip_address=session_data.get(b"ip_address", b"").decode() or None,
            user_agent=session_data.get(b"user_agent", b"").decode() or None,
            metadata={},  # Deserialize from JSON in production
        )
    
    async def update_session_activity(self, session_id: str):
        """Update session last activity"""
        key = self._make_key(session_id)
        now = datetime.utcnow().isoformat()
        
        await self.redis_client.hset(key, "last_activity", now)
        
        # Extend TTL
        ttl = await self.redis_client.ttl(key)
        if ttl > 0:
            await self.redis_client.expire(key, self.session_ttl)
    
    async def delete_session(self, session_id: str):
        """Delete session"""
        key = self._make_key(session_id)
        await self.redis_client.delete(key)
    
    async def delete_user_sessions(self, user_id: str):
        """Delete all sessions for user"""
        # In production, maintain index of user -> sessions
        pattern = f"{self.key_prefix}*"
        keys = await self.redis_client.keys(pattern)
        
        for key in keys:
            session_data = await self.redis_client.hgetall(key)
            if session_data.get(b"user_id", b"").decode() == user_id:
                await self.redis_client.delete(key)
    
    async def extend_session(self, session_id: str, additional_seconds: int):
        """Extend session expiration"""
        key = self._make_key(session_id)
        current_ttl = await self.redis_client.ttl(key)
        
        if current_ttl > 0:
            new_ttl = current_ttl + additional_seconds
            await self.redis_client.expire(key, new_ttl)
            
            # Update expires_at in session data
            session = await self.get_session(session_id)
            if session:
                new_expires_at = datetime.utcnow() + timedelta(seconds=new_ttl)
                await self.redis_client.hset(key, "expires_at", new_expires_at.isoformat())
    
    async def cleanup_expired_sessions(self):
        """Cleanup expired sessions (should run periodically)"""
        pattern = f"{self.key_prefix}*"
        keys = await self.redis_client.keys(pattern)
        
        expired_count = 0
        for key in keys:
            session_data = await self.redis_client.hgetall(key)
            if session_data:
                expires_at = datetime.fromisoformat(session_data[b"expires_at"].decode())
                if datetime.utcnow() > expires_at:
                    await self.redis_client.delete(key)
                    expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        return expired_count


class TokenManager:
    """Secure token management for refresh tokens, etc."""
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize token manager.
        
        Args:
            redis_client: Redis client
        """
        self.redis_client = redis_client
        self.key_prefix = "token:"
    
    def _make_key(self, token_hash: str) -> str:
        """Create Redis key for token"""
        return f"{self.key_prefix}{token_hash}"
    
    def generate_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_token(self, token: str) -> str:
        """Hash token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def store_token(
        self,
        token: str,
        user_id: str,
        token_type: str = "refresh",
        ttl: int = 86400 * 7,  # 7 days default
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store token in Redis"""
        token_hash = self.hash_token(token)
        key = self._make_key(token_hash)
        
        token_data = {
            "user_id": user_id,
            "token_type": token_type,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": str(metadata or {}),  # JSON serialize in production
        }
        
        await self.redis_client.hset(key, mapping=token_data)
        await self.redis_client.expire(key, ttl)
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token"""
        token_hash = self.hash_token(token)
        key = self._make_key(token_hash)
        
        token_data = await self.redis_client.hgetall(key)
        
        if not token_data:
            return None
        
        return {
            "user_id": token_data[b"user_id"].decode(),
            "token_type": token_data[b"token_type"].decode(),
            "created_at": datetime.fromisoformat(token_data[b"created_at"].decode()),
        }
    
    async def revoke_token(self, token: str):
        """Revoke token"""
        token_hash = self.hash_token(token)
        key = self._make_key(token_hash)
        await self.redis_client.delete(key)
    
    async def revoke_user_tokens(self, user_id: str, token_type: Optional[str] = None):
        """Revoke all tokens for user"""
        pattern = f"{self.key_prefix}*"
        keys = await self.redis_client.keys(pattern)
        
        for key in keys:
            token_data = await self.redis_client.hgetall(key)
            if token_data:
                token_user_id = token_data[b"user_id"].decode()
                token_token_type = token_data[b"token_type"].decode()
                
                if token_user_id == user_id:
                    if token_type is None or token_token_type == token_type:
                        await self.redis_client.delete(key)

