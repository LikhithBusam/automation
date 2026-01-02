"""
API Key Management System
Key rotation, expiration, scope-based permissions
"""

import logging
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API Key definition"""
    key_id: str
    key_hash: str  # Hashed key (never store plain key)
    user_id: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    metadata: Dict[str, Any]


class APIKeyManager:
    """API Key management system"""
    
    def __init__(self):
        # In production, use database
        self.keys: Dict[str, APIKey] = {}
        self.key_secrets: Dict[str, str] = {}  # Temporary storage for new keys
    
    def generate_key(
        self,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate new API key.
        
        Args:
            user_id: User ID
            name: Key name/description
            scopes: List of permission scopes
            expires_in_days: Expiration in days (None = no expiration)
            metadata: Additional metadata
        
        Returns:
            Dict with key_id and plain key (only shown once)
        """
        # Generate key ID and secret
        key_id = self._generate_key_id()
        plain_key = self._generate_key_secret()
        key_hash = self._hash_key(plain_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key record
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_used_at=None,
            is_active=True,
            metadata=metadata or {},
        )
        
        # Store key (in production, save to database)
        self.keys[key_id] = api_key
        self.key_secrets[key_id] = plain_key  # Temporary, should be shown to user once
        
        return {
            "key_id": key_id,
            "api_key": plain_key,  # Show only once!
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
    
    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key"""
        # Try to find matching key
        for key_id, key_record in self.keys.items():
            if not key_record.is_active:
                continue
            
            # Check expiration
            if key_record.expires_at and datetime.utcnow() > key_record.expires_at:
                continue
            
            # Verify key hash
            if self._verify_key(api_key, key_record.key_hash):
                # Update last used
                key_record.last_used_at = datetime.utcnow()
                return key_record
        
        return None
    
    def rotate_key(self, key_id: str, user_id: str) -> Dict[str, Any]:
        """Rotate API key (generate new, invalidate old)"""
        if key_id not in self.keys:
            raise ValueError(f"API key not found: {key_id}")
        
        old_key = self.keys[key_id]
        
        if old_key.user_id != user_id:
            raise ValueError("Unauthorized: Key belongs to different user")
        
        # Generate new key with same scopes
        new_key_data = self.generate_key(
            user_id=old_key.user_id,
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=self._days_until_expiration(old_key.expires_at),
            metadata=old_key.metadata,
        )
        
        # Deactivate old key
        old_key.is_active = False
        
        return new_key_data
    
    def revoke_key(self, key_id: str, user_id: str):
        """Revoke API key"""
        if key_id not in self.keys:
            raise ValueError(f"API key not found: {key_id}")
        
        key = self.keys[key_id]
        
        if key.user_id != user_id:
            raise ValueError("Unauthorized: Key belongs to different user")
        
        key.is_active = False
    
    def list_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List all API keys for user"""
        user_keys = [
            {
                "key_id": key.key_id,
                "name": key.name,
                "scopes": key.scopes,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "is_active": key.is_active,
            }
            for key in self.keys.values()
            if key.user_id == user_id
        ]
        
        return user_keys
    
    def update_key_scopes(self, key_id: str, user_id: str, scopes: List[str]):
        """Update API key scopes"""
        if key_id not in self.keys:
            raise ValueError(f"API key not found: {key_id}")
        
        key = self.keys[key_id]
        
        if key.user_id != user_id:
            raise ValueError("Unauthorized: Key belongs to different user")
        
        key.scopes = scopes
    
    def check_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if API key has required scope"""
        return required_scope in api_key.scopes or "*" in api_key.scopes
    
    def _generate_key_id(self) -> str:
        """Generate unique key ID"""
        return f"ak_{secrets.token_urlsafe(16)}"
    
    def _generate_key_secret(self) -> str:
        """Generate API key secret"""
        # Format: prefix_secret (e.g., ag_abc123...)
        prefix = "ag_"
        secret = secrets.token_urlsafe(32)
        return f"{prefix}{secret}"
    
    def _hash_key(self, plain_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(plain_key.encode()).hexdigest()
    
    def _verify_key(self, plain_key: str, key_hash: str) -> bool:
        """Verify API key against hash"""
        return self._hash_key(plain_key) == key_hash
    
    def _days_until_expiration(self, expires_at: Optional[datetime]) -> Optional[int]:
        """Calculate days until expiration"""
        if not expires_at:
            return None
        delta = expires_at - datetime.utcnow()
        return max(0, delta.days)


# Global API key manager instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager

