"""
Memory MCP Server using FastMCP
Provides persistent memory storage with semantic search using embeddings
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml
from fastmcp import FastMCP

# Conditional import for sentence-transformers
# Python 3.13+ has compatibility issues with sentence-transformers
EMBEDDINGS_AVAILABLE = False
embedding_model = None

if sys.version_info < (3, 13):
    try:
        from sentence_transformers import SentenceTransformer
        EMBEDDINGS_AVAILABLE = True
    except ImportError:
        logging.warning(
            "sentence-transformers not installed. Semantic search will use keyword matching."
        )
else:
    logging.warning(
        f"Python {sys.version_info.major}.{sys.version_info.minor} detected. "
        "sentence-transformers has known compatibility issues with Python 3.13+. "
        "Using keyword-based search fallback."
    )


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml with environment variable substitution"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    default_config = {
        "port": 3002,
        "host": "0.0.0.0",
        "sqlite_path": "./data/memory.db",
        "valid_memory_types": ["pattern", "preference", "solution", "context", "error"],
        "embedding_model": "all-MiniLM-L6-v2",
        "rate_limit_minute": 200,
        "rate_limit_hour": 5000,
        "cache_ttl": 300,
    }

    if not config_path.exists():
        logging.warning(f"Config file not found at {config_path}, using defaults")
        return default_config

    try:
        with open(config_path, "r") as f:
            full_config = yaml.safe_load(f)

        # Get memory server config
        server_config = full_config.get("mcp_servers", {}).get("memory", {})

        # Substitute environment variables (${VAR_NAME} pattern)
        def substitute_env_vars(value):
            if isinstance(value, str):
                pattern = r"\$\{([^}]+)\}"
                matches = re.findall(pattern, value)
                for var_name in matches:
                    env_value = os.getenv(var_name, "")
                    value = value.replace(f"${{{var_name}}}", env_value)
                return value
            elif isinstance(value, dict):
                return {k: substitute_env_vars(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_env_vars(item) for item in value]
            return value

        server_config = substitute_env_vars(server_config)

        # Merge with defaults
        for key, value in default_config.items():
            if key not in server_config:
                server_config[key] = value

        return server_config

    except Exception as e:
        logging.error(f"Error loading config: {e}, using defaults")
        return default_config


# Load configuration
CONFIG = load_config()

# Initialize LiteMCP server
mcp = FastMCP("Memory & Context Storage")
logger = logging.getLogger("mcp.memory")

# Database configuration (from config)
MEMORY_DB_PATH = Path(CONFIG.get("sqlite_path", "./data/memory.db"))
MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Valid memory types (from config)
VALID_MEMORY_TYPES = CONFIG.get(
    "valid_memory_types", ["pattern", "preference", "solution", "context", "error"]
)

# Embedding model name (from config)
EMBEDDING_MODEL_NAME = CONFIG.get("embedding_model", "all-MiniLM-L6-v2")

# Initialize embedding model (only if Python < 3.13)
if EMBEDDINGS_AVAILABLE and sys.version_info < (3, 13):
    try:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Loaded sentence-transformers embedding model: {EMBEDDING_MODEL_NAME}")
    except Exception as e:
        logger.warning(f"Failed to load embedding model: {e}")
        EMBEDDINGS_AVAILABLE = False
        embedding_model = None


def init_database():
    """Initialize SQLite database with memories table"""
    conn = sqlite3.connect(str(MEMORY_DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            type TEXT NOT NULL,
            tags TEXT,
            embedding BLOB,
            created_at REAL NOT NULL,
            ttl REAL,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL,
            metadata TEXT
        )
    """
    )

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ttl ON memories(ttl)")

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {MEMORY_DB_PATH}")


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(MEMORY_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_embedding(text: str) -> Optional[bytes]:
    """Create embedding vector for text"""
    if not EMBEDDINGS_AVAILABLE or embedding_model is None:
        return None
    try:
        embedding = embedding_model.encode(text)
        return embedding.tobytes()
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    if vec1 is None or vec2 is None:
        return 0.0
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def bytes_to_vector(embedding_bytes: bytes) -> Optional[np.ndarray]:
    """Convert bytes back to numpy array"""
    if embedding_bytes is None:
        return None
    try:
        return np.frombuffer(embedding_bytes, dtype=np.float32)
    except Exception:
        return None


def calculate_keyword_relevance(query: str, content: str, tags: List[str]) -> float:
    """Calculate keyword-based relevance score (fallback when embeddings unavailable)"""
    query_lower = query.lower()
    content_lower = content.lower()

    score = 0.0

    # Exact match bonus
    if query_lower == content_lower:
        score += 10.0

    # Substring match
    if query_lower in content_lower:
        position = content_lower.find(query_lower)
        position_score = max(0, 5 - (position / len(content_lower)) * 5)
        score += position_score

    # Word match
    query_words = set(query_lower.split())
    content_words = set(content_lower.split())
    common_words = query_words & content_words
    if common_words:
        score += len(common_words) / len(query_words) * 3

    # Tag match bonus
    query_words_in_tags = sum(1 for tag in tags if any(word in tag.lower() for word in query_words))
    if query_words_in_tags > 0:
        score += query_words_in_tags * 2

    return min(score / 10.0, 1.0)  # Normalize to 0-1


@mcp.tool()
async def store_memory(
    content: str,
    memory_type: str,
    tags: Optional[List[str]] = None,
    ttl_days: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store information in memory with optional TTL.

    Args:
        content: Information to remember
        memory_type: Type of memory (pattern, preference, solution, context, error)
        tags: Optional tags for categorization
        ttl_days: Time-to-live in days (None = permanent)
        metadata: Additional metadata

    Returns:
        Memory ID and status

    Example:
        result = await store_memory(
            content="Use FastAPI for REST APIs - it's faster than Flask",
            memory_type="pattern",
            tags=["python", "api", "framework"],
            ttl_days=30
        )
        memory_id = result["id"]
    """
    # Validate memory type
    if memory_type not in VALID_MEMORY_TYPES:
        raise ValueError(f"Invalid memory type. Must be one of: {VALID_MEMORY_TYPES}")

    # Generate unique ID
    memory_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:16]

    # Create embedding for semantic search
    embedding = create_embedding(content)

    # Calculate TTL timestamp
    ttl_timestamp = None
    if ttl_days is not None:
        ttl_timestamp = time.time() + (ttl_days * 24 * 3600)

    # Store in SQLite
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memories (id, content, type, tags, embedding, created_at, ttl, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                content,
                memory_type,
                json.dumps(tags or []),
                embedding,
                time.time(),
                ttl_timestamp,
                json.dumps(metadata or {}),
            ),
        )
        conn.commit()

    logger.info(f"Stored memory {memory_id} of type '{memory_type}'")

    return {
        "status": "success",
        "id": memory_id,
        "type": memory_type,
        "tags": tags or [],
        "has_embedding": embedding is not None,
        "ttl_days": ttl_days,
    }


# Alias for backwards compatibility
@mcp.tool()
async def remember(
    content: str,
    memory_type: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Alias for store_memory (backwards compatibility)"""
    return await store_memory(content, memory_type, tags, None, metadata)


@mcp.tool()
async def search_memory(
    query: str, memory_type: Optional[str] = None, limit: int = 5, min_score: float = 0.3
) -> Dict[str, Any]:
    """
    Search memory using semantic similarity (embeddings) or keyword matching.

    Args:
        query: Search query
        memory_type: Optional filter by memory type
        limit: Maximum number of results to return
        min_score: Minimum relevance score threshold (0-1)

    Returns:
        Matching memories ranked by relevance

    Example:
        results = await search_memory("API best practices", limit=3)
        for memory in results["results"]:
            print(memory["content"])
    """
    results = []

    # Create query embedding for semantic search
    query_embedding = None
    if EMBEDDINGS_AVAILABLE and embedding_model:
        try:
            query_embedding = embedding_model.encode(query)
        except Exception as e:
            logger.warning(f"Failed to create query embedding: {e}")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build query
        sql = "SELECT * FROM memories WHERE (ttl IS NULL OR ttl > ?)"
        params = [time.time()]

        if memory_type:
            sql += " AND type = ?"
            params.append(memory_type)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        for row in rows:
            tags = json.loads(row["tags"]) if row["tags"] else []

            # Calculate relevance score
            if query_embedding is not None and row["embedding"]:
                # Semantic similarity using cosine
                memory_embedding = bytes_to_vector(row["embedding"])
                score = cosine_similarity(query_embedding, memory_embedding)
            else:
                # Fallback to keyword matching
                score = calculate_keyword_relevance(query, row["content"], tags)

            if score >= min_score:
                results.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "type": row["type"],
                        "tags": tags,
                        "score": float(score),
                        "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
                        "access_count": row["access_count"] or 0,
                    }
                )

        # Update access counts for returned results
        result_ids = [r["id"] for r in results]
        if result_ids:
            placeholders = ",".join(["?"] * len(result_ids))
            cursor.execute(
                f"""
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id IN ({placeholders})
            """,
                [time.time()] + result_ids,
            )
            conn.commit()

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"Found {len(results)} memories for query '{query}'")

    return {
        "query": query,
        "results": results[:limit],
        "total_found": len(results),
        "limit": limit,
        "semantic_search": EMBEDDINGS_AVAILABLE and query_embedding is not None,
    }


# Alias for backwards compatibility
@mcp.tool()
async def recall(
    query: str, limit: int = 5, memory_type: Optional[str] = None, min_score: float = 0.1
) -> Dict[str, Any]:
    """Alias for search_memory (backwards compatibility)"""
    return await search_memory(query, memory_type, limit, min_score)


@mcp.tool()
async def retrieve_memory(memory_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific memory by ID.

    Args:
        memory_id: The ID of the memory to retrieve

    Returns:
        Memory details

    Example:
        memory = await retrieve_memory("abc123")
        print(memory["content"])
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Memory not found: {memory_id}")

        # Update access count
        cursor.execute(
            """
            UPDATE memories SET access_count = access_count + 1, last_accessed = ?
            WHERE id = ?
        """,
            (time.time(), memory_id),
        )
        conn.commit()

        tags = json.loads(row["tags"]) if row["tags"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return {
            "id": row["id"],
            "content": row["content"],
            "type": row["type"],
            "tags": tags,
            "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
            "access_count": (row["access_count"] or 0) + 1,
            "metadata": metadata,
        }


@mcp.tool()
async def recall_recent(
    memory_type: str, limit: int = 10, hours: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get recent memories of a specific type.

    Args:
        memory_type: Type of memory to retrieve
        limit: Maximum number of results
        hours: Optional filter for memories from last N hours

    Returns:
        Recent memories of the specified type

    Example:
        recent_errors = await recall_recent("error", limit=5, hours=24)
        for error in recent_errors["results"]:
            print(error["content"])
    """
    results = []
    cutoff_time = time.time() - (hours * 3600) if hours else 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        sql = """
            SELECT * FROM memories 
            WHERE type = ? AND created_at > ? AND (ttl IS NULL OR ttl > ?)
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor.execute(sql, (memory_type, cutoff_time, time.time(), limit))
        rows = cursor.fetchall()

        for row in rows:
            tags = json.loads(row["tags"]) if row["tags"] else []
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            results.append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "tags": tags,
                    "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
                    "access_count": row["access_count"] or 0,
                    "metadata": metadata,
                }
            )

    logger.info(f"Retrieved {len(results)} recent {memory_type} memories")

    return {
        "type": memory_type,
        "results": results,
        "total": len(results),
        "time_window_hours": hours,
    }


@mcp.tool()
async def update_memory(
    memory_id: str, content: Optional[str] = None, tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update an existing memory.

    Args:
        memory_id: ID of memory to update
        content: New content (optional)
        tags: New tags (optional)

    Returns:
        Updated memory details

    Example:
        result = await update_memory(
            memory_id="abc123",
            tags=["python", "api", "production"]
        )
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if memory exists
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Memory not found: {memory_id}")

        # Build update query
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
            # Re-create embedding for new content
            embedding = create_embedding(content)
            if embedding:
                updates.append("embedding = ?")
                params.append(embedding)

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if updates:
            params.append(memory_id)
            sql = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

        # Fetch updated memory
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        updated = cursor.fetchone()

        logger.info(f"Updated memory {memory_id}")

        return {
            "status": "success",
            "id": memory_id,
            "content": updated["content"],
            "tags": json.loads(updated["tags"]) if updated["tags"] else [],
        }


@mcp.tool()
async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """
    Delete a memory by ID.

    Args:
        memory_id: Memory ID to delete

    Returns:
        Success status

    Example:
        result = await delete_memory("abc123")
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get memory info before deletion
        cursor.execute("SELECT type FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if row:
            memory_type = row["type"]
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()

            logger.info(f"Deleted memory {memory_id}")

            return {
                "status": "success",
                "id": memory_id,
                "message": f"Memory of type '{memory_type}' deleted",
            }
        else:
            return {"status": "not_found", "id": memory_id, "message": "Memory not found"}


# Alias for backwards compatibility
@mcp.tool()
async def forget(memory_id: str) -> Dict[str, Any]:
    """Alias for delete_memory (backwards compatibility)"""
    return await delete_memory(memory_id)


@mcp.tool()
async def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about stored memories.

    Returns:
        Memory statistics by type, access patterns, etc.

    Example:
        stats = await get_memory_stats()
        print(f"Total memories: {stats['total_count']}")
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Total count
        cursor.execute(
            "SELECT COUNT(*) as count FROM memories WHERE (ttl IS NULL OR ttl > ?)", (time.time(),)
        )
        total_count = cursor.fetchone()["count"]

        # Count by type
        cursor.execute(
            """
            SELECT type, COUNT(*) as count FROM memories 
            WHERE (ttl IS NULL OR ttl > ?)
            GROUP BY type
        """,
            (time.time(),),
        )
        by_type = {row["type"]: row["count"] for row in cursor.fetchall()}

        # Most accessed
        cursor.execute(
            """
            SELECT id, content, access_count FROM memories 
            WHERE (ttl IS NULL OR ttl > ?)
            ORDER BY access_count DESC LIMIT 5
        """,
            (time.time(),),
        )
        most_accessed = [
            {
                "id": row["id"],
                "content": (
                    row["content"][:50] + "..." if len(row["content"]) > 50 else row["content"]
                ),
                "access_count": row["access_count"] or 0,
            }
            for row in cursor.fetchall()
        ]

        # Recent memories
        cursor.execute(
            """
            SELECT id, type, content, created_at FROM memories 
            WHERE (ttl IS NULL OR ttl > ?)
            ORDER BY created_at DESC LIMIT 5
        """,
            (time.time(),),
        )
        recent = [
            {
                "id": row["id"],
                "type": row["type"],
                "content": (
                    row["content"][:50] + "..." if len(row["content"]) > 50 else row["content"]
                ),
                "created_at": datetime.fromtimestamp(row["created_at"]).isoformat(),
            }
            for row in cursor.fetchall()
        ]

        # Get all unique tags
        cursor.execute(
            "SELECT DISTINCT tags FROM memories WHERE (ttl IS NULL OR ttl > ?)", (time.time(),)
        )
        all_tags = set()
        for row in cursor.fetchall():
            if row["tags"]:
                tags = json.loads(row["tags"])
                all_tags.update(tags)

        return {
            "total_count": total_count,
            "by_type": by_type,
            "most_accessed": most_accessed,
            "recent_memories": recent,
            "total_tags": list(all_tags),
            "embeddings_enabled": EMBEDDINGS_AVAILABLE,
        }


@mcp.tool()
async def prune_old_memories(
    days: int = 30, exclude_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Delete memories older than specified days based on TTL.

    Args:
        days: Delete memories older than this many days
        exclude_types: Memory types to exclude from pruning

    Returns:
        Pruning statistics

    Example:
        result = await prune_old_memories(days=7, exclude_types=["pattern", "preference"])
        print(f"Deleted {result['deleted_count']} old memories")
    """
    cutoff_time = time.time() - (days * 24 * 3600)
    exclude_types = exclude_types or []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build exclusion clause
        exclude_clause = ""
        params = [cutoff_time]

        if exclude_types:
            placeholders = ",".join(["?" for _ in exclude_types])
            exclude_clause = f" AND type NOT IN ({placeholders})"
            params.extend(exclude_types)

        # Count before deletion
        cursor.execute(
            f"""
            SELECT COUNT(*) as count FROM memories 
            WHERE created_at < ? {exclude_clause}
        """,
            params,
        )
        delete_count = cursor.fetchone()["count"]

        # Delete old memories
        cursor.execute(
            f"""
            DELETE FROM memories 
            WHERE created_at < ? {exclude_clause}
        """,
            params,
        )
        conn.commit()

    logger.info(f"Pruned {delete_count} memories older than {days} days")

    return {
        "status": "success",
        "deleted_count": delete_count,
        "days_threshold": days,
        "excluded_types": exclude_types,
    }


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check Memory MCP server health.

    Returns:
        Health status including database connectivity and embedding model status

    Example:
        health = await health_check()
        print(f"Status: {health['status']}")
    """
    health = {
        "server": "memory_mcp",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_path": str(MEMORY_DB_PATH),
        "embeddings_available": EMBEDDINGS_AVAILABLE,
        "valid_memory_types": VALID_MEMORY_TYPES,
    }

    # Check database connectivity
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM memories")
            count = cursor.fetchone()["count"]
            health["database"] = {"connected": True, "total_memories": count}
    except Exception as e:
        health["database"] = {"connected": False, "error": str(e)}
        health["status"] = "degraded"

    # Check embedding model
    if EMBEDDINGS_AVAILABLE:
        health["embedding_model"] = {
            "loaded": embedding_model is not None,
            "model_name": "all-MiniLM-L6-v2",
        }
    else:
        health["embedding_model"] = {"loaded": False, "fallback": "keyword_matching"}

    return health


# Initialize database on server start
init_database()


if __name__ == "__main__":
    port = CONFIG.get("port", 3002)
    host = CONFIG.get("host", "0.0.0.0")
    print(f"Starting Memory MCP Server on http://{host}:{port}...")
    print(f"Database: {MEMORY_DB_PATH}")
    print(f"Embeddings enabled: {EMBEDDINGS_AVAILABLE}")
    if EMBEDDINGS_AVAILABLE:
        print(f"Embedding model: {EMBEDDING_MODEL_NAME}")

    # Run server with dynamic config
    mcp.run(transport="sse", port=port, host=host)
