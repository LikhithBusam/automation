"""
Memory Management Module

Three-tier memory architecture:
- SHORT_TERM: Session memory (1 hour TTL, LRU eviction)
- MEDIUM_TERM: Project memory (30 days TTL)
- LONG_TERM: Knowledge base (permanent)

Features:
- Automatic tier promotion based on access patterns
- LRU eviction for short-term memory
- Memory consolidation (merge similar memories)
- Context retrieval for agents
- Statistics tracking
"""

from src.memory.memory_manager import MemoryLayer  # Backward compatibility alias
from src.memory.memory_manager import (
    TIER_CONFIGS,
    LRUMemoryCache,
    MemoryManager,
    MemoryStats,
    MemoryTier,
    MemoryType,
    TierConfig,
)

__all__ = [
    # Main manager
    "MemoryManager",
    # Tier system
    "MemoryTier",
    "MemoryLayer",  # Alias for backward compatibility
    "MemoryType",
    "TierConfig",
    "TIER_CONFIGS",
    # Supporting classes
    "MemoryStats",
    "LRUMemoryCache",
]
