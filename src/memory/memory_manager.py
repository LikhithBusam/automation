"""
Memory Manager - Handles persistent agent memory and context management
Implements three-tier memory architecture with automatic tier promotion,
LRU eviction, memory consolidation, and context retrieval for agents.

Tiers:
- SHORT_TERM: Session memory (1 hour TTL, LRU eviction)
- MEDIUM_TERM: Project memory (30 days TTL)
- LONG_TERM: Knowledge base (permanent, no TTL)
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import asyncio
from datetime import datetime, timedelta
from collections import OrderedDict
import json
import hashlib
from enum import Enum
import logging
import threading
from dataclasses import dataclass, field

from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

# Optional: Import Memory MCP tool for persistence
try:
    from src.mcp.memory_tool import MemoryMCPTool
    HAS_MCP_MEMORY = True
except ImportError:
    HAS_MCP_MEMORY = False


Base = declarative_base()


# =============================================================================
# MEMORY TIER DEFINITIONS
# =============================================================================

class MemoryTier(str, Enum):
    """
    Three-tier memory system
    - SHORT_TERM: Session-scoped, fast access, LRU eviction
    - MEDIUM_TERM: Project-scoped, 30-day retention
    - LONG_TERM: Permanent knowledge base
    """
    SHORT_TERM = "short_term"    # Session memory (TTL: 1 hour)
    MEDIUM_TERM = "medium_term"  # Project memory (TTL: 30 days)
    LONG_TERM = "long_term"      # Knowledge base (permanent)


# Alias for backward compatibility
MemoryLayer = MemoryTier


class MemoryType(str, Enum):
    """Types of memory entries"""
    DECISION = "decision"
    PATTERN = "pattern"
    PREFERENCE = "preference"
    CONTEXT = "context"
    TASK_RESULT = "task_result"
    LEARNING = "learning"
    CODE_SNIPPET = "code_snippet"
    DOCUMENTATION = "documentation"
    ERROR_RESOLUTION = "error_resolution"
    AGENT_INTERACTION = "agent_interaction"


# =============================================================================
# TIER CONFIGURATION
# =============================================================================

@dataclass
class TierConfig:
    """Configuration for each memory tier"""
    ttl_seconds: Optional[int]  # None = permanent
    max_entries: Optional[int]  # None = unlimited
    promotion_threshold: int    # Access count to promote
    consolidation_similarity: float  # Similarity threshold for merging


TIER_CONFIGS: Dict[MemoryTier, TierConfig] = {
    MemoryTier.SHORT_TERM: TierConfig(
        ttl_seconds=3600,           # 1 hour
        max_entries=1000,           # LRU eviction after 1000 entries
        promotion_threshold=5,      # Promote after 5 accesses
        consolidation_similarity=0.95
    ),
    MemoryTier.MEDIUM_TERM: TierConfig(
        ttl_seconds=30 * 24 * 3600, # 30 days
        max_entries=10000,
        promotion_threshold=20,     # Promote after 20 accesses
        consolidation_similarity=0.90
    ),
    MemoryTier.LONG_TERM: TierConfig(
        ttl_seconds=None,           # Permanent
        max_entries=None,           # Unlimited
        promotion_threshold=0,      # Already at top tier
        consolidation_similarity=0.85
    ),
}


# =============================================================================
# MEMORY STATISTICS TRACKING
# =============================================================================

@dataclass
class MemoryStats:
    """Track memory usage statistics"""
    total_stores: int = 0
    total_retrievals: int = 0
    total_promotions: int = 0
    total_consolidations: int = 0
    total_evictions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tier_counts: Dict[str, int] = field(default_factory=dict)
    type_counts: Dict[str, int] = field(default_factory=dict)
    agent_counts: Dict[str, int] = field(default_factory=dict)
    avg_retrieval_latency_ms: float = 0.0
    _latency_samples: List[float] = field(default_factory=list)
    
    def record_latency(self, latency_ms: float):
        """Record retrieval latency and update average"""
        self._latency_samples.append(latency_ms)
        # Keep only last 1000 samples
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]
        self.avg_retrieval_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_stores": self.total_stores,
            "total_retrievals": self.total_retrievals,
            "total_promotions": self.total_promotions,
            "total_consolidations": self.total_consolidations,
            "total_evictions": self.total_evictions,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "tier_counts": self.tier_counts,
            "type_counts": self.type_counts,
            "agent_counts": self.agent_counts,
            "avg_retrieval_latency_ms": round(self.avg_retrieval_latency_ms, 2),
        }


# =============================================================================
# LRU CACHE FOR SHORT-TERM MEMORY
# =============================================================================

class LRUMemoryCache:
    """
    LRU cache for short-term memory with automatic eviction.
    Thread-safe implementation using OrderedDict.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._access_counts: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item and move to end (most recently used)"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                # Increment access count
                self._access_counts[key] = self._access_counts.get(key, 0) + 1
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Dict[str, Any]) -> Optional[str]:
        """
        Add item to cache. Returns evicted key if capacity exceeded.
        """
        with self._lock:
            evicted_key = None
            
            if key in self._cache:
                # Update existing
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                # Add new
                if len(self._cache) >= self.max_size:
                    # Evict least recently used
                    evicted_key, _ = self._cache.popitem(last=False)
                    self._access_counts.pop(evicted_key, None)
                
                self._cache[key] = value
                self._access_counts[key] = 1
            
            return evicted_key
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_counts.pop(key, None)
                return True
            return False
    
    def get_access_count(self, key: str) -> int:
        """Get access count for a key"""
        return self._access_counts.get(key, 0)
    
    def get_promotion_candidates(self, threshold: int) -> List[str]:
        """Get keys that have been accessed more than threshold times"""
        with self._lock:
            return [
                key for key, count in self._access_counts.items()
                if count >= threshold
            ]
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_counts.clear()
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def items(self):
        """Iterate over cache items"""
        with self._lock:
            return list(self._cache.items())


# =============================================================================
# DATABASE MODEL
# =============================================================================

class MemoryEntry(Base):
    """SQLAlchemy model for memory entries"""
    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True)
    tier = Column(String, nullable=False, index=True)  # Renamed from layer
    type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Summarized version for long content
    embedding = Column(Text)  # Stored as JSON string
    meta_data = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy reserved word
    agent = Column(String, index=True)
    project = Column(String, index=True)
    tags = Column(JSON)
    relevance_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)  # For tier promotion
    relationships = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    ttl = Column(DateTime, nullable=True, index=True)
    
    # Backward compatibility alias
    @property
    def layer(self) -> str:
        return self.tier


# =============================================================================
# MEMORY MANAGER - MAIN CLASS
# =============================================================================

class MemoryManager:
    """
    Three-tier memory management system with:
    - Automatic tier promotion based on access patterns
    - LRU eviction for short-term memory
    - Memory consolidation (merge similar memories)
    - Context retrieval for agents
    - Memory MCP tool integration for persistence
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("memory.manager")

        # Initialize embedding model for semantic search
        self.embedding_model = SentenceTransformer(
            config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        )

        # Initialize database
        database_url = config.get("database_url", "sqlite:///./memory.db")
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()

        # Initialize Redis for caching (optional)
        self.redis_client = None
        if config.get("redis_url"):
            asyncio.create_task(self._init_redis(config["redis_url"]))

        # Initialize LRU cache for short-term memory
        short_term_max = TIER_CONFIGS[MemoryTier.SHORT_TERM].max_entries or 1000
        self.short_term_cache = LRUMemoryCache(max_size=short_term_max)
        
        # Initialize Memory MCP tool for persistence (if available)
        self.mcp_memory: Optional[MemoryMCPTool] = None
        if HAS_MCP_MEMORY and config.get("use_mcp_memory", True):
            self._init_mcp_memory(config)
        
        # Statistics tracking
        self.stats = MemoryStats()
        
        # Tier TTL settings (use config or defaults)
        self.tier_ttl = {
            MemoryTier.SHORT_TERM: timedelta(
                seconds=config.get("short_term_ttl", TIER_CONFIGS[MemoryTier.SHORT_TERM].ttl_seconds)
            ),
            MemoryTier.MEDIUM_TERM: timedelta(
                seconds=config.get("medium_term_ttl", TIER_CONFIGS[MemoryTier.MEDIUM_TERM].ttl_seconds)
            ),
            MemoryTier.LONG_TERM: None  # Permanent
        }
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._promotion_task: Optional[asyncio.Task] = None
        
        self.logger.info("MemoryManager initialized with three-tier architecture")

    def _init_mcp_memory(self, config: Dict[str, Any]):
        """Initialize Memory MCP tool for persistence"""
        try:
            mcp_config = config.get("mcp_memory", {})
            self.mcp_memory = MemoryMCPTool(
                server_url=mcp_config.get("server_url", "http://localhost:8002"),
                config=mcp_config
            )
            self.logger.info("Memory MCP tool initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Memory MCP tool: {e}")
            self.mcp_memory = None

    async def _init_redis(self, redis_url: str):
        """Initialize Redis connection"""
        try:
            self.redis_client = await redis.from_url(redis_url)
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.warning(f"Redis initialization failed: {str(e)}")
            self.redis_client = None

    # =========================================================================
    # CORE OPERATIONS: store, retrieve, promote, consolidate, get_context
    # =========================================================================

    async def store(
        self,
        content: str,
        tier: MemoryTier = MemoryTier.SHORT_TERM,
        type: MemoryType = MemoryType.CONTEXT,
        tags: Optional[List[str]] = None,
        agent: Optional[str] = None,
        project: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relationships: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Store a new memory entry with appropriate TTL based on tier.
        
        Args:
            content: Memory content to store
            tier: Memory tier (SHORT_TERM, MEDIUM_TERM, LONG_TERM)
            type: Type of memory (DECISION, PATTERN, CONTEXT, etc.)
            tags: List of tags for categorization
            agent: Associated agent name
            project: Associated project name
            metadata: Additional metadata
            relationships: Related memory IDs
            
        Returns:
            Memory entry ID
        """
        start_time = datetime.utcnow()
        
        try:
            # Support legacy entry_data dict format
            if isinstance(content, dict):
                entry_data = content
                content = entry_data.get("content", "")
                tier = MemoryTier(entry_data.get("tier", entry_data.get("layer", "short_term")))
                type = MemoryType(entry_data.get("type", "context"))
                tags = entry_data.get("tags", [])
                agent = entry_data.get("agent")
                project = entry_data.get("project")
                metadata = entry_data.get("metadata", {})
                relationships = entry_data.get("relationships", [])
            
            # Generate unique ID
            entry_id = self._generate_id(content)

            # Generate embedding for semantic search
            embedding = self._create_embedding(content)
            
            # Generate summary for long content
            summary = self._summarize_content(content) if len(content) > 500 else None

            # Determine TTL based on tier
            ttl = None
            if self.tier_ttl[tier]:
                ttl = datetime.utcnow() + self.tier_ttl[tier]

            # Create memory entry
            entry = MemoryEntry(
                id=entry_id,
                tier=tier.value,
                type=type.value if isinstance(type, MemoryType) else type,
                content=content,
                summary=summary,
                embedding=json.dumps(embedding.tolist()),
                meta_data=metadata or {},
                agent=agent,
                project=project,
                tags=tags or [],
                relevance_score=1.0,
                access_count=0,
                relationships=relationships or [],
                created_at=datetime.utcnow(),
                last_accessed_at=datetime.utcnow(),
                ttl=ttl
            )

            # Store in database
            self.db_session.add(entry)
            self.db_session.commit()
            
            # Also store in LRU cache if short-term
            if tier == MemoryTier.SHORT_TERM:
                evicted = self.short_term_cache.put(entry_id, {
                    "id": entry_id,
                    "content": content,
                    "type": type.value if isinstance(type, MemoryType) else type,
                    "tier": tier.value,
                    "tags": tags or [],
                    "agent": agent,
                    "metadata": metadata or {},
                })
                if evicted:
                    self.stats.total_evictions += 1
                    self.logger.debug(f"LRU evicted entry: {evicted}")
            
            # Persist to MCP Memory tool if available
            if self.mcp_memory:
                await self._persist_to_mcp(entry_id, content, tier, tags or [])

            # Update statistics
            self.stats.total_stores += 1
            self.stats.tier_counts[tier.value] = self.stats.tier_counts.get(tier.value, 0) + 1
            self.stats.type_counts[type.value if isinstance(type, MemoryType) else type] = \
                self.stats.type_counts.get(type.value if isinstance(type, MemoryType) else type, 0) + 1
            if agent:
                self.stats.agent_counts[agent] = self.stats.agent_counts.get(agent, 0) + 1

            self.logger.info(f"Stored memory entry: {entry_id} (tier: {tier.value})")
            return entry_id

        except Exception as e:
            self.logger.error(f"Failed to store memory: {str(e)}")
            self.db_session.rollback()
            raise

    async def retrieve(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        agent: Optional[str] = None,
        type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_relevance: float = 0.5,
        include_summary: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories matching query with semantic search.
        Updates access counts for tier promotion.
        
        Args:
            query: Search query
            tier: Filter by specific tier (None = all tiers)
            limit: Maximum number of results
            agent: Filter by agent name
            type: Filter by memory type
            tags: Filter by tags (any match)
            min_relevance: Minimum similarity score
            include_summary: Include summary in results
            
        Returns:
            List of matching memory entries
        """
        start_time = datetime.utcnow()
        
        try:
            # Check short-term cache first for quick hits
            if tier == MemoryTier.SHORT_TERM or tier is None:
                cache_results = self._search_lru_cache(query, limit)
                if cache_results and tier == MemoryTier.SHORT_TERM:
                    self.stats.cache_hits += 1
                    self.stats.total_retrievals += 1
                    return cache_results
            
            self.stats.cache_misses += 1

            # Create query embedding
            query_embedding = self._create_embedding(query)

            # Query database
            now = datetime.utcnow()
            entries = self.db_session.query(MemoryEntry).filter(
                (MemoryEntry.ttl.is_(None)) | (MemoryEntry.ttl > now)
            )

            # Apply filters
            if tier:
                entries = entries.filter(MemoryEntry.tier == tier.value)
            if agent:
                entries = entries.filter(MemoryEntry.agent == agent)
            if type:
                entries = entries.filter(MemoryEntry.type == type.value)

            # Calculate similarity scores and filter
            results = []
            for entry in entries:
                # Tag filter (any match)
                if tags and entry.tags:
                    if not any(tag in entry.tags for tag in tags):
                        continue
                
                entry_embedding = np.array(json.loads(entry.embedding))
                similarity = self._cosine_similarity(query_embedding, entry_embedding)

                if similarity >= min_relevance:
                    # Update access count
                    entry.access_count += 1
                    entry.last_accessed_at = datetime.utcnow()
                    
                    result = {
                        "id": entry.id,
                        "content": entry.content,
                        "type": entry.type,
                        "tier": entry.tier,
                        "agent": entry.agent,
                        "project": entry.project,
                        "metadata": entry.meta_data,
                        "tags": entry.tags,
                        "relevance_score": float(similarity),
                        "access_count": entry.access_count,
                        "created_at": entry.created_at.isoformat(),
                        "last_accessed_at": entry.last_accessed_at.isoformat(),
                    }
                    
                    if include_summary and entry.summary:
                        result["summary"] = entry.summary
                    
                    results.append(result)

            # Commit access count updates
            self.db_session.commit()

            # Sort by relevance and limit
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = results[:limit]

            # Update statistics
            self.stats.total_retrievals += 1
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats.record_latency(latency_ms)

            self.logger.info(f"Retrieved {len(results)} memories for query")
            return results

        except Exception as e:
            self.logger.error(f"Memory retrieval failed: {str(e)}")
            return []

    async def promote(self, entry_id: str, new_tier: MemoryTier) -> bool:
        """
        Promote a memory entry to a higher tier.
        
        Args:
            entry_id: Memory entry ID
            new_tier: Target tier to promote to
            
        Returns:
            True if promotion successful
        """
        try:
            entry = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.id == entry_id
            ).first()

            if not entry:
                self.logger.warning(f"Entry not found for promotion: {entry_id}")
                return False
            
            current_tier = MemoryTier(entry.tier)
            
            # Validate promotion (can only promote up)
            tier_order = [MemoryTier.SHORT_TERM, MemoryTier.MEDIUM_TERM, MemoryTier.LONG_TERM]
            current_idx = tier_order.index(current_tier)
            new_idx = tier_order.index(new_tier)
            
            if new_idx <= current_idx:
                self.logger.warning(f"Cannot demote or same-tier promote: {current_tier} -> {new_tier}")
                return False
            
            # Update tier and TTL
            entry.tier = new_tier.value
            if self.tier_ttl[new_tier]:
                entry.ttl = datetime.utcnow() + self.tier_ttl[new_tier]
            else:
                entry.ttl = None  # Permanent for LONG_TERM
            
            self.db_session.commit()
            
            # Remove from short-term cache if promoted from there
            if current_tier == MemoryTier.SHORT_TERM:
                self.short_term_cache.remove(entry_id)
            
            # Update statistics
            self.stats.total_promotions += 1
            self.stats.tier_counts[current_tier.value] = max(0, 
                self.stats.tier_counts.get(current_tier.value, 1) - 1)
            self.stats.tier_counts[new_tier.value] = \
                self.stats.tier_counts.get(new_tier.value, 0) + 1
            
            self.logger.info(f"Promoted {entry_id}: {current_tier.value} -> {new_tier.value}")
            return True

        except Exception as e:
            self.logger.error(f"Promotion failed for {entry_id}: {str(e)}")
            self.db_session.rollback()
            return False

    async def consolidate(
        self,
        tier: Optional[MemoryTier] = None,
        similarity_threshold: Optional[float] = None
    ) -> int:
        """
        Merge similar memories to reduce redundancy.
        Uses embedding similarity to find duplicates/near-duplicates.
        
        Args:
            tier: Specific tier to consolidate (None = all)
            similarity_threshold: Override default threshold
            
        Returns:
            Number of memories consolidated
        """
        consolidated_count = 0
        
        try:
            # Get entries to consolidate
            query = self.db_session.query(MemoryEntry)
            if tier:
                query = query.filter(MemoryEntry.tier == tier.value)
                threshold = similarity_threshold or TIER_CONFIGS[tier].consolidation_similarity
            else:
                threshold = similarity_threshold or 0.90
            
            entries = query.order_by(MemoryEntry.created_at).all()
            
            # Track which entries to keep vs merge
            keep_ids: Set[str] = set()
            merge_map: Dict[str, str] = {}  # merged_id -> keep_id
            
            for i, entry in enumerate(entries):
                if entry.id in merge_map:
                    continue  # Already marked for merge
                
                keep_ids.add(entry.id)
                entry_embedding = np.array(json.loads(entry.embedding))
                
                # Check remaining entries for similarity
                for j in range(i + 1, len(entries)):
                    other = entries[j]
                    if other.id in merge_map or other.id in keep_ids:
                        continue
                    
                    other_embedding = np.array(json.loads(other.embedding))
                    similarity = self._cosine_similarity(entry_embedding, other_embedding)
                    
                    if similarity >= threshold:
                        # Mark for merge
                        merge_map[other.id] = entry.id
                        
                        # Update kept entry's metadata
                        if other.tags:
                            entry.tags = list(set(entry.tags or []) | set(other.tags))
                        if other.relationships:
                            entry.relationships = list(
                                set(entry.relationships or []) | set(other.relationships)
                            )
                        # Boost relevance for consolidated entries
                        entry.relevance_score = min(1.0, entry.relevance_score + 0.1)
            
            # Delete merged entries
            for merged_id in merge_map:
                self.db_session.query(MemoryEntry).filter(
                    MemoryEntry.id == merged_id
                ).delete()
                consolidated_count += 1
            
            self.db_session.commit()
            
            # Update statistics
            self.stats.total_consolidations += consolidated_count
            
            self.logger.info(f"Consolidated {consolidated_count} memories")
            return consolidated_count

        except Exception as e:
            self.logger.error(f"Consolidation failed: {str(e)}")
            self.db_session.rollback()
            return 0

    async def get_context(
        self,
        agent_id: str,
        task_type: Optional[str] = None,
        project: Optional[str] = None,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for an agent based on its role and current task.
        Assembles memories from all tiers with smart prioritization.
        
        Args:
            agent_id: Agent identifier
            task_type: Current task type (for relevance)
            project: Current project name
            max_tokens: Approximate max tokens in context
            
        Returns:
            Structured context with memories from each tier
        """
        context = {
            "agent_id": agent_id,
            "task_type": task_type,
            "project": project,
            "short_term": [],
            "medium_term": [],
            "long_term": [],
            "recent_decisions": [],
            "patterns": [],
            "total_memories": 0,
        }
        
        try:
            # Build query for agent's relevant memories
            query = f"{agent_id} {task_type or ''} {project or ''}"
            
            # Get short-term memories (most recent, session context)
            short_term = await self.retrieve(
                query=query,
                tier=MemoryTier.SHORT_TERM,
                agent=agent_id,
                limit=5
            )
            context["short_term"] = short_term
            
            # Get medium-term memories (project knowledge)
            medium_term = await self.retrieve(
                query=query,
                tier=MemoryTier.MEDIUM_TERM,
                agent=agent_id,
                limit=10
            )
            context["medium_term"] = medium_term
            
            # Get long-term memories (permanent knowledge)
            long_term = await self.retrieve(
                query=query,
                tier=MemoryTier.LONG_TERM,
                limit=10
            )
            context["long_term"] = long_term
            
            # Get recent decisions
            decisions = await self.retrieve(
                query=query,
                type=MemoryType.DECISION,
                agent=agent_id,
                limit=5
            )
            context["recent_decisions"] = decisions
            
            # Get patterns
            patterns = await self.retrieve(
                query=query,
                type=MemoryType.PATTERN,
                limit=5
            )
            context["patterns"] = patterns
            
            # Calculate totals
            context["total_memories"] = (
                len(short_term) + len(medium_term) + len(long_term) +
                len(decisions) + len(patterns)
            )
            
            # Summarize if context is too long
            context = self._trim_context_to_tokens(context, max_tokens)
            
            self.logger.info(
                f"Retrieved context for {agent_id}: {context['total_memories']} memories"
            )
            return context

        except Exception as e:
            self.logger.error(f"Failed to get context for {agent_id}: {str(e)}")
            return context

    # =========================================================================
    # AUTOMATIC TIER PROMOTION
    # =========================================================================

    async def check_and_promote(self) -> int:
        """
        Check all entries for promotion eligibility based on access patterns.
        Called periodically by background task.
        
        Returns:
            Number of entries promoted
        """
        promoted_count = 0
        
        try:
            # Check short-term entries for promotion to medium-term
            short_threshold = TIER_CONFIGS[MemoryTier.SHORT_TERM].promotion_threshold
            short_candidates = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.tier == MemoryTier.SHORT_TERM.value,
                MemoryEntry.access_count >= short_threshold
            ).all()
            
            for entry in short_candidates:
                if await self.promote(entry.id, MemoryTier.MEDIUM_TERM):
                    promoted_count += 1
            
            # Check medium-term entries for promotion to long-term
            medium_threshold = TIER_CONFIGS[MemoryTier.MEDIUM_TERM].promotion_threshold
            medium_candidates = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.tier == MemoryTier.MEDIUM_TERM.value,
                MemoryEntry.access_count >= medium_threshold
            ).all()
            
            for entry in medium_candidates:
                if await self.promote(entry.id, MemoryTier.LONG_TERM):
                    promoted_count += 1
            
            if promoted_count > 0:
                self.logger.info(f"Auto-promoted {promoted_count} entries")
            
            return promoted_count

        except Exception as e:
            self.logger.error(f"Auto-promotion check failed: {str(e)}")
            return 0

    # =========================================================================
    # LRU EVICTION FOR SHORT-TERM MEMORY
    # =========================================================================

    async def evict_lru(self, count: int = 10) -> int:
        """
        Manually evict least recently used entries from short-term memory.
        
        Args:
            count: Number of entries to evict
            
        Returns:
            Number of entries evicted
        """
        evicted = 0
        
        try:
            # Get oldest short-term entries
            entries = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.tier == MemoryTier.SHORT_TERM.value
            ).order_by(
                MemoryEntry.last_accessed_at.asc()
            ).limit(count).all()
            
            for entry in entries:
                self.db_session.delete(entry)
                self.short_term_cache.remove(entry.id)
                evicted += 1
            
            self.db_session.commit()
            self.stats.total_evictions += evicted
            
            self.logger.info(f"Evicted {evicted} LRU entries from short-term memory")
            return evicted

        except Exception as e:
            self.logger.error(f"LRU eviction failed: {str(e)}")
            self.db_session.rollback()
            return 0

    # =========================================================================
    # MEMORY SUMMARIZATION
    # =========================================================================

    def _summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        Summarize long content for efficient context retrieval.
        Uses extractive summarization (first + key sentences).
        
        Args:
            content: Content to summarize
            max_length: Maximum summary length
            
        Returns:
            Summarized content
        """
        if len(content) <= max_length:
            return content
        
        # Simple extractive summarization
        sentences = content.split('. ')
        
        if len(sentences) <= 2:
            return content[:max_length] + "..."
        
        # Take first sentence and last sentence
        summary_parts = [sentences[0]]
        
        # Add middle important sentence (longest, likely most informative)
        middle_sentences = sentences[1:-1]
        if middle_sentences:
            longest = max(middle_sentences, key=len)
            summary_parts.append(longest)
        
        summary_parts.append(sentences[-1])
        
        summary = '. '.join(summary_parts)
        
        if len(summary) > max_length:
            return summary[:max_length] + "..."
        
        return summary

    def _trim_context_to_tokens(
        self,
        context: Dict[str, Any],
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Trim context to fit within token budget.
        Prioritizes: short_term > decisions > medium_term > patterns > long_term
        
        Args:
            context: Context dictionary
            max_tokens: Maximum tokens
            
        Returns:
            Trimmed context
        """
        # Rough estimate: 4 chars per token
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        def estimate_size(obj: Any) -> int:
            return len(json.dumps(obj, default=str))
        
        current_size = estimate_size(context)
        
        if current_size <= max_chars:
            return context
        
        # Trim in priority order (lowest priority first)
        trim_order = ["long_term", "patterns", "medium_term", "recent_decisions", "short_term"]
        
        for key in trim_order:
            if key in context and context[key]:
                while context[key] and estimate_size(context) > max_chars:
                    context[key].pop()
        
        # Use summaries instead of full content if still too large
        for key in ["short_term", "medium_term", "long_term"]:
            if key in context:
                for mem in context[key]:
                    if "summary" in mem and mem.get("summary"):
                        mem["content"] = mem["summary"]
        
        return context

    # =========================================================================
    # STATISTICS AND MONITORING
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory usage statistics"""
        try:
            # Get database counts
            total = self.db_session.query(MemoryEntry).count()
            
            tier_counts = {}
            for tier in MemoryTier:
                count = self.db_session.query(MemoryEntry).filter(
                    MemoryEntry.tier == tier.value
                ).count()
                tier_counts[tier.value] = count
            
            type_counts = {}
            for mem_type in MemoryType:
                count = self.db_session.query(MemoryEntry).filter(
                    MemoryEntry.type == mem_type.value
                ).count()
                type_counts[mem_type.value] = count
            
            # Update stats object
            self.stats.tier_counts = tier_counts
            self.stats.type_counts = type_counts
            
            return {
                "database": {
                    "total_entries": total,
                    "by_tier": tier_counts,
                    "by_type": type_counts,
                },
                "cache": {
                    "short_term_cache_size": len(self.short_term_cache),
                    "short_term_cache_max": self.short_term_cache.max_size,
                },
                "operations": self.stats.to_dict(),
                "mcp_memory_enabled": self.mcp_memory is not None,
                "redis_enabled": self.redis_client is not None,
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {"error": str(e)}

    # =========================================================================
    # BACKGROUND TASKS
    # =========================================================================

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._promotion_task = asyncio.create_task(self._promotion_loop())
        self.logger.info("Background tasks started")

    async def stop_background_tasks(self):
        """Stop background maintenance tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._promotion_task:
            self._promotion_task.cancel()
        self.logger.info("Background tasks stopped")

    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")

    async def _promotion_loop(self):
        """Periodic check for tier promotion"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self.check_and_promote()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Promotion loop error: {e}")

    async def cleanup_expired(self) -> int:
        """Remove expired memory entries"""
        try:
            now = datetime.utcnow()
            deleted = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.ttl.isnot(None),
                MemoryEntry.ttl < now
            ).delete()

            self.db_session.commit()
            self.logger.info(f"Cleaned up {deleted} expired memory entries")
            return deleted

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            self.db_session.rollback()
            return 0

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _search_lru_cache(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search LRU cache with simple string matching"""
        results = []
        query_lower = query.lower()
        
        for entry_id, entry in self.short_term_cache.items():
            content = entry.get("content", "").lower()
            if query_lower in content:
                results.append({
                    **entry,
                    "relevance_score": 0.8,  # Approximate score for cache hits
                })
                if len(results) >= limit:
                    break
        
        return results

    async def _persist_to_mcp(
        self,
        entry_id: str,
        content: str,
        tier: MemoryTier,
        tags: List[str]
    ):
        """Persist memory to MCP Memory server"""
        if not self.mcp_memory:
            return
        
        try:
            await self.mcp_memory.execute({
                "operation": "store",
                "key": entry_id,
                "content": content,
                "tier": tier.value,
                "tags": tags,
            })
        except Exception as e:
            self.logger.warning(f"MCP persistence failed: {e}")

    def _create_embedding(self, text: str) -> np.ndarray:
        """Create embedding vector for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry"""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{content}_{timestamp}".encode()
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_parts = [str(arg) for arg in args if arg is not None]
        return "memory:" + ":".join(key_parts)

    async def _cache_entry(self, entry_id: str, data: Dict[str, Any]):
        """Cache memory entry in Redis"""
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"memory:entry:{entry_id}",
                    3600,  # 1 hour
                    json.dumps(data, default=str)
                )
            except Exception as e:
                self.logger.warning(f"Cache write failed: {str(e)}")

    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================

    async def search(
        self,
        query: str,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
        layer: Optional[MemoryTier] = None,
        limit: int = 5,
        min_relevance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Legacy search method - wraps retrieve()"""
        return await self.retrieve(
            query=query,
            tier=layer,
            agent=agent,
            limit=limit,
            min_relevance=min_relevance
        )

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing memory entry"""
        try:
            entry = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.id == entry_id
            ).first()

            if not entry:
                return False

            for key, value in updates.items():
                if key == "content":
                    entry.content = value
                    entry.embedding = json.dumps(
                        self._create_embedding(value).tolist()
                    )
                    if len(value) > 500:
                        entry.summary = self._summarize_content(value)
                elif hasattr(entry, key):
                    setattr(entry, key, value)

            self.db_session.commit()
            self.logger.info(f"Updated memory entry: {entry_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update memory {entry_id}: {str(e)}")
            self.db_session.rollback()
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        try:
            entry = self.db_session.query(MemoryEntry).filter(
                MemoryEntry.id == entry_id
            ).first()

            if entry:
                self.db_session.delete(entry)
                self.db_session.commit()
                self.short_term_cache.remove(entry_id)
                self.logger.info(f"Deleted memory entry: {entry_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to delete memory {entry_id}: {str(e)}")
            self.db_session.rollback()
            return False

    async def close(self):
        """Close database and Redis connections"""
        await self.stop_background_tasks()
        self.db_session.close()
        if self.redis_client:
            await self.redis_client.close()
        self.logger.info("MemoryManager closed")
