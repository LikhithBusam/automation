"""
CodeBaseBuddy MCP Tool Wrapper
Wraps CodeBaseBuddy MCP server functions for AutoGen agents

Features:
1. Connect to CodeBaseBuddy MCP server at localhost:3004
2. Semantic code search with natural language queries
3. Find similar code patterns across codebase
4. Build and manage vector index
5. Fallback to direct operations if server unavailable
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import asyncio
import json

from src.mcp.base_tool import (
    BaseMCPTool,
    MCPConnectionError,
    MCPValidationError,
    MCPToolError
)


class CodeBaseBuddyMCPTool(BaseMCPTool):
    """
    CodeBaseBuddy MCP Tool Wrapper.
    
    Provides semantic code search and understanding:
    - Natural language code search
    - Find similar code patterns
    - Get code context
    - Build/manage vector index
    
    Features:
    - Sentence-transformer embeddings
    - Annoy vector index for fast search
    - Function-level Python indexing
    - Fallback to basic text search
    """

    # Cache TTLs for different operations (in seconds)
    CACHE_TTLS = {
        "semantic_search": 300,      # 5 minutes
        "find_similar_code": 300,    # 5 minutes
        "get_index_stats": 60,       # 1 minute
    }

    def __init__(
        self,
        server_url: str = "http://localhost:3004",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize CodeBaseBuddy tool.
        
        Args:
            server_url: URL of the CodeBaseBuddy MCP server
            config: Additional configuration options
        """
        if config is None:
            config = {}

        config.setdefault("cache_ttl", 300)  # 5 minutes default
        config.setdefault("rate_limit_minute", 100)
        config.setdefault("rate_limit_hour", 2000)

        super().__init__(
            name="codebasebuddy",
            server_url=server_url,
            config=config,
            fallback_handler=self._fallback_handler
        )

        self.logger = logging.getLogger(__name__)
        self.index_path = Path(config.get("index_path", "./data/codebase_index"))
        self.scan_paths = config.get("scan_paths", ["./src", "./mcp_servers"])

    async def _fallback_handler(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback handler when MCP server is unavailable.
        Uses basic text search as fallback.
        """
        self.logger.warning(f"CodeBaseBuddy server unavailable, using fallback for: {operation}")

        if operation == "semantic_search":
            return await self._fallback_search(params)
        elif operation == "get_index_stats":
            return self._fallback_stats()
        elif operation == "health":
            return {"status": "fallback", "server": "unavailable"}
        else:
            return {
                "success": False,
                "error": f"Fallback not available for operation: {operation}",
                "fallback_used": True
            }

    async def _fallback_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Basic text search fallback when semantic search unavailable"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)

        results = []

        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            for file_path in path.rglob("*.py"):
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if query.lower() in content.lower():
                        # Find matching lines
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                results.append({
                                    "file_path": str(file_path),
                                    "chunk_type": "line_match",
                                    "name": file_path.name,
                                    "start_line": i + 1,
                                    "end_line": i + 1,
                                    "content_preview": line.strip()[:200],
                                    "similarity_score": 0.5,  # Fallback has no real score
                                    "fallback_match": True
                                })
                                if len(results) >= top_k:
                                    break
                except Exception as e:
                    self.logger.warning(f"Error reading {file_path}: {e}")

                if len(results) >= top_k:
                    break

            if len(results) >= top_k:
                break

        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": results[:top_k],
            "fallback_used": True
        }

    def _fallback_stats(self) -> Dict[str, Any]:
        """Return fallback stats when server unavailable"""
        stats_path = self.index_path / "index_stats.json"

        if stats_path.exists():
            try:
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                return {
                    "success": True,
                    "stats": stats,
                    "fallback_used": True
                }
            except Exception:
                pass

        return {
            "success": False,
            "error": "No stats available",
            "fallback_used": True
        }

    # =========================================================================
    # Main API Methods
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        file_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search the codebase using natural language queries.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            file_filter: Filter by file path pattern
            chunk_type_filter: Filter by chunk type ('function', 'class', 'file')
        
        Returns:
            Dictionary with search results
        
        Example:
            results = await tool.semantic_search("How does authentication work?")
        """
        if not query or not query.strip():
            raise MCPValidationError("Query cannot be empty")

        params = {
            "query": query.strip(),
            "top_k": min(top_k, 50)  # Cap at 50 results
        }

        if file_filter:
            params["file_filter"] = file_filter
        if chunk_type_filter:
            params["chunk_type_filter"] = chunk_type_filter

        # Check cache first
        cache_key = f"semantic_search:{hash(json.dumps(params, sort_keys=True))}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self.call_mcp_server("semantic_search", params)

        # Cache successful results
        if result.get("success"):
            self._set_cached(cache_key, result, ttl=self.CACHE_TTLS["semantic_search"])

        return result

    async def find_similar_code(
        self,
        code_snippet: str,
        top_k: int = 5,
        exclude_self: bool = True
    ) -> Dict[str, Any]:
        """
        Find code similar to a given snippet.
        
        Args:
            code_snippet: Code snippet to find similar patterns for
            top_k: Number of similar results to return
            exclude_self: If True, exclude exact matches
        
        Returns:
            Dictionary with similar code locations
        
        Example:
            results = await tool.find_similar_code("def process_data(df):")
        """
        if not code_snippet or not code_snippet.strip():
            raise MCPValidationError("Code snippet cannot be empty")

        params = {
            "code_snippet": code_snippet,
            "top_k": min(top_k, 50),
            "exclude_self": exclude_self
        }

        return await self.call_mcp_server("find_similar_code", params)

    async def get_code_context(
        self,
        file_path: str,
        line_number: int,
        context_lines: int = 10
    ) -> Dict[str, Any]:
        """
        Get code context around a specific line in a file.
        
        Args:
            file_path: Path to the code file
            line_number: Target line number
            context_lines: Number of lines before and after
        
        Returns:
            Dictionary with code context
        
        Example:
            context = await tool.get_code_context("./src/main.py", 42)
        """
        if not file_path:
            raise MCPValidationError("File path cannot be empty")
        if line_number < 1:
            raise MCPValidationError("Line number must be positive")

        params = {
            "file_path": file_path,
            "line_number": line_number,
            "context_lines": max(1, min(context_lines, 100))
        }

        return await self.call_mcp_server("get_code_context", params)

    async def build_index(
        self,
        root_path: str,
        file_extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Build or rebuild the semantic code index.
        
        Args:
            root_path: Root directory to scan
            file_extensions: File extensions to include
            exclude_patterns: Patterns to exclude
            rebuild: If True, completely rebuild index
        
        Returns:
            Dictionary with build status
        
        Example:
            result = await tool.build_index("./src", file_extensions=[".py"])
        """
        if not root_path:
            raise MCPValidationError("Root path cannot be empty")

        params = {
            "root_path": root_path,
            "rebuild": rebuild
        }

        if file_extensions:
            params["file_extensions"] = file_extensions
        if exclude_patterns:
            params["exclude_patterns"] = exclude_patterns

        return await self.call_mcp_server("build_index", params)

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current index.
        
        Returns:
            Dictionary with index statistics
        """
        cache_key = "index_stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self.call_mcp_server("get_index_stats", {})

        if result.get("success"):
            self._set_cached(cache_key, result, ttl=self.CACHE_TTLS["get_index_stats"])

        return result

    async def find_usages(
        self,
        symbol_name: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Find all usages of a symbol across the codebase.
        
        Args:
            symbol_name: Name of the symbol to find
            top_k: Maximum number of results
        
        Returns:
            Dictionary with usage locations
        
        Example:
            results = await tool.find_usages("MCPToolManager")
        """
        if not symbol_name or not symbol_name.strip():
            raise MCPValidationError("Symbol name cannot be empty")

        params = {
            "symbol_name": symbol_name.strip(),
            "top_k": min(top_k, 50)
        }

        return await self.call_mcp_server("find_usages", params)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the CodeBaseBuddy server is healthy.
        
        Returns:
            Dictionary with health status
        """
        return await self.call_mcp_server("health", {})

    # =========================================================================
    # Cache Helpers
    # =========================================================================

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        if hasattr(self, '_cache') and key in self._cache:
            entry = self._cache[key]
            import time
            if time.time() < entry['expires']:
                return entry['data']
        return None

    def _set_cached(self, key: str, data: Dict[str, Any], ttl: int = 300):
        """Cache a result with TTL"""
        import time
        if not hasattr(self, '_cache'):
            self._cache = {}
        self._cache[key] = {
            'data': data,
            'expires': time.time() + ttl
        }


# Convenience function for standalone usage
async def create_codebasebuddy_tool(
    server_url: str = "http://localhost:3004",
    config: Optional[Dict[str, Any]] = None
) -> CodeBaseBuddyMCPTool:
    """
    Create and initialize a CodeBaseBuddy tool instance.
    
    Args:
        server_url: URL of the CodeBaseBuddy MCP server
        config: Additional configuration
    
    Returns:
        Initialized CodeBaseBuddyMCPTool instance
    """
    tool = CodeBaseBuddyMCPTool(server_url=server_url, config=config)
    await tool.connect()
    return tool
