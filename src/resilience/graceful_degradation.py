"""
Graceful Degradation Strategies
- Feature flags for non-critical features
- Fallback responses
- Cached responses when services are down
"""

import asyncio
import logging
import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict, List
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeatureState(Enum):
    """Feature flag states"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"  # Feature available but with reduced functionality


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    state: FeatureState = FeatureState.ENABLED
    description: str = ""
    fallback_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


class FeatureFlags:
    """Manages feature flags"""
    
    def __init__(self):
        """Initialize feature flags"""
        self._flags: Dict[str, FeatureFlag] = {}
        self._lock = asyncio.Lock()
    
    def register(self, flag: FeatureFlag):
        """Register a feature flag"""
        self._flags[flag.name] = flag
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature flag is enabled"""
        flag = self._flags.get(flag_name)
        if not flag:
            return True  # Default to enabled if not registered
        
        return flag.state == FeatureState.ENABLED
    
    def is_degraded(self, flag_name: str) -> bool:
        """Check if feature flag is in degraded state"""
        flag = self._flags.get(flag_name)
        if not flag:
            return False
        
        return flag.state == FeatureState.DEGRADED
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get feature flag"""
        return self._flags.get(flag_name)
    
    def set_state(self, flag_name: str, state: FeatureState):
        """Set feature flag state"""
        if flag_name in self._flags:
            self._flags[flag_name].state = state
            logger.info(f"Feature flag {flag_name} set to {state.value}")


class CacheStore:
    """Simple in-memory cache for fallback responses"""
    
    def __init__(self, default_ttl_seconds: int = 300):
        """Initialize cache store"""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_seconds
    
    def _generate_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key"""
        key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check TTL
        if time.time() - entry["timestamp"] > entry["ttl"]:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for key: {key[:16]}...")
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set cached value"""
        ttl = ttl_seconds or self._default_ttl
        self._cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl
        }
        logger.debug(f"Cached value for key: {key[:16]}...")
    
    def clear(self):
        """Clear all cached values"""
        self._cache.clear()
    
    def cleanup(self):
        """Cleanup expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry["timestamp"] > entry["ttl"]
        ]
        for key in expired_keys:
            del self._cache[key]


class FallbackManager:
    """Manages fallback strategies"""
    
    def __init__(self):
        """Initialize fallback manager"""
        self._fallbacks: Dict[str, Callable] = {}
        self._cache = CacheStore()
    
    def register_fallback(self, service_name: str, fallback_func: Callable):
        """Register fallback function for service"""
        self._fallbacks[service_name] = fallback_func
        logger.info(f"Registered fallback for service: {service_name}")
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        use_cache: bool = True,
        cache_ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with fallback support.
        
        Args:
            service_name: Service name
            primary_func: Primary function to execute
            *args: Positional arguments
            use_cache: Whether to use cached responses
            cache_ttl_seconds: Cache TTL override
            **kwargs: Keyword arguments
        
        Returns:
            Function result or fallback result
        """
        # Check cache first
        if use_cache:
            cache_key = self._cache._generate_key(primary_func, args, kwargs)
            cached_result = self._cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Using cached response for {service_name}")
                return cached_result
        
        # Try primary function
        try:
            result = await primary_func(*args, **kwargs)
            
            # Cache successful result
            if use_cache:
                cache_key = self._cache._generate_key(primary_func, args, kwargs)
                self._cache.set(cache_key, result, cache_ttl_seconds)
            
            return result
        
        except Exception as e:
            logger.warning(f"Primary function failed for {service_name}: {e}")
            
            # Try fallback
            fallback_func = self._fallbacks.get(service_name)
            if fallback_func:
                logger.info(f"Using fallback for {service_name}")
                try:
                    result = await fallback_func(*args, **kwargs)
                    
                    # Cache fallback result
                    if use_cache:
                        cache_key = self._cache._generate_key(primary_func, args, kwargs)
                        self._cache.set(cache_key, result, cache_ttl_seconds)
                    
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {service_name}: {fallback_error}")
                    raise
            
            # Try cache as last resort
            if use_cache:
                cache_key = self._cache._generate_key(primary_func, args, kwargs)
                cached_result = self._cache.get(cache_key)
                if cached_result is not None:
                    logger.warning(f"Using stale cached response for {service_name}")
                    return cached_result
            
            # All options exhausted
            raise


@dataclass
class DegradationStrategy:
    """Degradation strategy configuration"""
    feature_name: str
    primary_func: Callable
    fallback_func: Optional[Callable] = None
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    feature_flag: Optional[str] = None


class GracefulDegradation:
    """Manages graceful degradation"""
    
    def __init__(self):
        """Initialize graceful degradation"""
        self.feature_flags = FeatureFlags()
        self.fallback_manager = FallbackManager()
        self._strategies: Dict[str, DegradationStrategy] = {}
    
    def register_strategy(self, strategy: DegradationStrategy):
        """Register degradation strategy"""
        self._strategies[strategy.feature_name] = strategy
        
        # Register feature flag if specified
        if strategy.feature_flag:
            self.feature_flags.register(
                FeatureFlag(
                    name=strategy.feature_flag,
                    fallback_enabled=strategy.fallback_func is not None,
                    cache_enabled=strategy.cache_enabled
                )
            )
        
        # Register fallback if provided
        if strategy.fallback_func:
            self.fallback_manager.register_fallback(
                strategy.feature_name,
                strategy.fallback_func
            )
    
    async def execute(
        self,
        feature_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute feature with graceful degradation.
        
        Args:
            feature_name: Feature name
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Feature result
        """
        strategy = self._strategies.get(feature_name)
        if not strategy:
            # No strategy registered, cannot execute
            raise ValueError(f"No degradation strategy registered for feature: {feature_name}")
        
        # Check feature flag
        if strategy.feature_flag:
            if not self.feature_flags.is_enabled(strategy.feature_flag):
                logger.info(f"Feature {feature_name} is disabled via feature flag")
                if strategy.fallback_func:
                    return await strategy.fallback_func(*args, **kwargs)
                raise Exception(f"Feature {feature_name} is disabled and no fallback available")
            
            if self.feature_flags.is_degraded(strategy.feature_flag):
                logger.info(f"Feature {feature_name} is in degraded mode")
                # Use fallback in degraded mode
                if strategy.fallback_func:
                    return await self.fallback_manager.execute_with_fallback(
                        feature_name,
                        strategy.primary_func,
                        *args,
                        use_cache=strategy.cache_enabled,
                        cache_ttl_seconds=strategy.cache_ttl_seconds,
                        **kwargs
                    )
        
        # Execute with fallback support
        return await self.fallback_manager.execute_with_fallback(
            feature_name,
            strategy.primary_func,
            *args,
            use_cache=strategy.cache_enabled,
            cache_ttl_seconds=strategy.cache_ttl_seconds,
            **kwargs
        )


# Global graceful degradation manager
_graceful_degradation = GracefulDegradation()


def get_graceful_degradation() -> GracefulDegradation:
    """Get global graceful degradation manager"""
    return _graceful_degradation

