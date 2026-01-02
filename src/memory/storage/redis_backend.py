"""
Redis Backend for Memory Storage
Handles caching and short-term memory
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisBackend:
    """Redis backend for caching and short-term memory"""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        """
        Initialize Redis backend.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[redis.Redis] = None
        logger.info("Redis backend initialized")
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def store(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Store value in Redis"""
        if not self.client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            await self.client.setex(f"memory:{key}", ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Failed to store in Redis: {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve value from Redis"""
        if not self.client:
            return None
        
        try:
            serialized = await self.client.get(f"memory:{key}")
            if serialized:
                return json.loads(serialized)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve from Redis: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(f"memory:{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False
        
        try:
            return await self.client.exists(f"memory:{key}") > 0
        except Exception as e:
            logger.error(f"Failed to check existence in Redis: {e}")
            return False
    
    async def get_all_keys(self, pattern: str = "memory:*") -> List[str]:
        """Get all keys matching pattern"""
        if not self.client:
            return []
        
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key.replace("memory:", ""))
            return keys
        except Exception as e:
            logger.error(f"Failed to get keys from Redis: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.client:
            return {"connected": False}
        
        try:
            info = await self.client.info("memory")
            keys = await self.get_all_keys()
            return {
                "connected": True,
                "total_keys": len(keys),
                "memory_used": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {"connected": False, "error": str(e)}

