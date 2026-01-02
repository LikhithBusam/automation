"""
Edge Caching Strategy
Cache at edge locations for reduced latency
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EdgeCacheConfig:
    """Edge cache configuration"""
    provider: str  # "cloudflare", "fastly", "cloudfront"
    cache_ttl: int = 3600  # 1 hour
    stale_while_revalidate: int = 86400  # 24 hours
    cache_control: str = "public, max-age=3600"


class EdgeCache:
    """
    Edge caching strategy for reduced latency.
    Caches responses at edge locations closer to users.
    """
    
    def __init__(self, config: EdgeCacheConfig):
        """Initialize edge cache"""
        self.config = config
        self.logger = logging.getLogger("edge.cache")
    
    def get_cache_headers(
        self,
        ttl: Optional[int] = None,
        stale_while_revalidate: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Get cache control headers.
        
        Args:
            ttl: Optional TTL override
            stale_while_revalidate: Optional stale-while-revalidate override
        
        Returns:
            Cache headers
        """
        ttl = ttl or self.config.cache_ttl
        swr = stale_while_revalidate or self.config.stale_while_revalidate
        
        headers = {
            "Cache-Control": f"public, max-age={ttl}, stale-while-revalidate={swr}",
            "CDN-Cache-Control": f"public, max-age={ttl}",
        }
        
        # Provider-specific headers
        if self.config.provider == "cloudflare":
            headers["CF-Cache-Status"] = "HIT"  # Would be set by Cloudflare
        elif self.config.provider == "fastly":
            headers["Surrogate-Control"] = f"max-age={ttl}"
        
        return headers
    
    def should_cache(
        self,
        path: str,
        method: str,
        status_code: int
    ) -> bool:
        """
        Determine if response should be cached.
        
        Args:
            path: Request path
            method: HTTP method
            status_code: Response status code
        
        Returns:
            True if should cache
        """
        # Only cache GET requests
        if method != "GET":
            return False
        
        # Only cache successful responses
        if status_code not in [200, 301, 302]:
            return False
        
        # Don't cache authenticated endpoints
        if "/api/v1/auth/" in path:
            return False
        
        # Don't cache user-specific data
        if "/api/v1/users/" in path and "/profile" in path:
            return False
        
        return True
    
    def get_cache_key(
        self,
        path: str,
        query_params: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate cache key.
        
        Args:
            path: Request path
            query_params: Query parameters
            user_id: Optional user ID for user-specific caching
        
        Returns:
            Cache key
        """
        import hashlib
        import json
        
        key_parts = [path]
        
        if query_params:
            key_parts.append(json.dumps(query_params, sort_keys=True))
        
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def purge_cache(
        self,
        paths: List[str],
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Purge edge cache.
        
        Args:
            paths: Paths to purge
            tags: Optional cache tags to purge
        
        Returns:
            True if successful
        """
        try:
            if self.config.provider == "cloudflare":
                return await self._purge_cloudflare(paths, tags)
            elif self.config.provider == "fastly":
                return await self._purge_fastly(paths, tags)
            elif self.config.provider == "cloudfront":
                return await self._purge_cloudfront(paths, tags)
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to purge cache: {e}")
            return False
    
    async def _purge_cloudflare(self, paths: List[str], tags: Optional[List[str]]) -> bool:
        """Purge Cloudflare cache"""
        self.logger.info(f"Purging Cloudflare cache for {len(paths)} paths")
        return True
    
    async def _purge_fastly(self, paths: List[str], tags: Optional[List[str]]) -> bool:
        """Purge Fastly cache"""
        self.logger.info(f"Purging Fastly cache for {len(paths)} paths")
        return True
    
    async def _purge_cloudfront(self, paths: List[str], tags: Optional[List[str]]) -> bool:
        """Purge CloudFront cache"""
        self.logger.info(f"Purging CloudFront cache for {len(paths)} paths")
        return True


# Global edge cache instance
_edge_cache: Optional[EdgeCache] = None


def get_edge_cache() -> Optional[EdgeCache]:
    """Get global edge cache"""
    return _edge_cache


def initialize_edge_cache(config: EdgeCacheConfig) -> EdgeCache:
    """Initialize global edge cache"""
    global _edge_cache
    _edge_cache = EdgeCache(config)
    return _edge_cache

