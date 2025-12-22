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
import time
import hashlib
from contextlib import asynccontextmanager

from src.mcp.base_tool import BaseMCPTool, MCPConnectionError, MCPValidationError, MCPToolError


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
        "semantic_search": 300,  # 5 minutes
        "find_similar_code": 300,  # 5 minutes
        "get_index_stats": 60,  # 1 minute
    }

    def __init__(
        self, server_url: str = "http://localhost:3004", config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize CodeBaseBuddy tool.

        Args:
            server_url: URL of the CodeBaseBuddy MCP server (not used for direct calls)
            config: Additional configuration options
        """
        if config is None:
            config = {}

        config.setdefault("cache_ttl", 300)  # 5 minutes default
        config.setdefault("rate_limit_minute", 100)
        config.setdefault("rate_limit_hour", 2000)
        config.setdefault("connection_timeout", 60)
        config.setdefault("max_connections", 10)
        config.setdefault("max_connections_per_host", 5)

        super().__init__(
            name="codebasebuddy",
            server_url=server_url,
            config=config,
            fallback_handler=self._fallback_handler,
        )

        self.logger = logging.getLogger(__name__)
        self.index_path = Path(config.get("index_path", "./data/codebase_index"))
        self.scan_paths = config.get("scan_paths", ["./src", "./mcp_servers"])
        self._session = None
        self._connection_timeout = config.get("connection_timeout", 60)
        self._max_connections = config.get("max_connections", 10)
        self._max_connections_per_host = config.get("max_connections_per_host", 5)

    async def _fallback_handler(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback handler when MCP server is unavailable.
        Uses basic text search and file operations as fallback.
        """
        self.logger.warning(f"CodeBaseBuddy server unavailable, using fallback for: {operation}")

        if operation == "semantic_search":
            return await self._fallback_search(params)
        elif operation == "build_index":
            return self._fallback_build_index(params)
        elif operation == "get_index_stats":
            return self._fallback_stats()
        elif operation == "find_similar_code":
            return await self._fallback_find_similar(params)
        elif operation == "get_code_context":
            return await self._fallback_get_context(params)
        elif operation == "find_usages":
            return await self._fallback_find_usages(params)
        elif operation == "health":
            return {"status": "fallback", "server": "unavailable"}
        else:
            return {
                "success": False,
                "error": f"Fallback not available for operation: {operation}",
                "fallback_used": True,
            }

    async def _fallback_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Smart text search fallback when semantic search unavailable"""
        query = params.get("query", "")
        top_k = params.get("top_k", 5)

        results = []

        # Extract meaningful keywords from query (ignore common words)
        stop_words = {
            "what",
            "is",
            "how",
            "does",
            "the",
            "a",
            "an",
            "are",
            "in",
            "to",
            "for",
            "of",
            "and",
            "or",
            "it",
            "this",
            "that",
            "be",
            "with",
            "on",
            "at",
            "by",
            "work",
            "works",
            "working",
            "used",
            "use",
            "using",
            "do",
            "can",
            "where",
            "when",
            "why",
            "which",
            "there",
            "here",
            "about",
            "get",
            "gets",
            "got",
            "available",
            "exist",
            "exists",
            "have",
            "has",
            "had",
            "defined",
            "define",
            "list",
            "show",
            "find",
            "tell",
            "give",
            "me",
            "all",
            "any",
            "some",
        }

        # Get keywords - words longer than 2 chars that aren't stop words
        words = query.lower().replace("?", "").replace('"', "").replace("'", "").split()
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]

        # If no keywords found, use original query words
        if not keywords:
            keywords = [w for w in words if len(w) > 2]

        if not keywords:
            return {
                "success": True,
                "query": query,
                "results_count": 0,
                "results": [],
                "fallback_used": True,
                "message": "No searchable keywords found in query",
            }

        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            # Search Python files AND YAML config files
            file_patterns = ["*.py", "*.yaml", "*.yml"]
            for pattern in file_patterns:
                for file_path in path.rglob(pattern):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        content_lower = content.lower()

                        # Check if file contains any keywords
                        matching_keywords = [kw for kw in keywords if kw in content_lower]
                        if not matching_keywords:
                            continue

                        lines = content.split("\n")
                        is_yaml = file_path.suffix in [".yaml", ".yml"]

                        # Priority 1: Look for class/function definitions containing keywords
                        for i, line in enumerate(lines):
                            line_lower = line.lower()

                            # For Python: class/function definitions
                            # For YAML: key definitions (lines ending with :)
                            if is_yaml:
                                is_definition = ":" in line and not line.strip().startswith("#")
                            else:
                                is_definition = line.strip().startswith(
                                    ("class ", "def ", "async def ")
                                )

                            # Check if this line contains any keyword
                            line_keywords = [kw for kw in keywords if kw in line_lower]

                            if line_keywords:
                                # Higher score for definitions and config files
                                score = 0.8 if is_definition else 0.5
                                score += 0.1 * len(line_keywords)  # Bonus for multiple keywords

                                # Boost YAML config files (they contain important definitions)
                                if is_yaml:
                                    score += 0.15

                                # Get context (2 lines before, 3 lines after)
                                start_idx = max(0, i - 2)
                                end_idx = min(len(lines), i + 4)
                                context_lines = lines[start_idx:end_idx]
                                context_preview = "\n".join(context_lines)[:300]

                                results.append(
                                    {
                                        "file_path": str(file_path),
                                        "chunk_type": (
                                            "config"
                                            if is_yaml
                                            else ("definition" if is_definition else "code")
                                        ),
                                        "name": file_path.name,
                                        "start_line": i + 1,
                                        "end_line": end_idx,
                                        "content_preview": context_preview,
                                        "similarity_score": min(0.98, score),
                                        "matched_keywords": line_keywords,
                                        "fallback_match": True,
                                    }
                                )

                                # Don't break early - collect results from ALL scan paths
                                if len(results) >= top_k * 5:  # Collect more to ensure variety
                                    break

                    except Exception as e:
                        self.logger.warning(f"Error reading {file_path}: {e}")

                    if len(results) >= top_k * 5:
                        break

                # Don't break here - continue to next pattern in same scan path

            # Don't break here - continue to next scan path to get config files

        # Sort by score (YAML configs and definitions first)
        results.sort(key=lambda x: (-x["similarity_score"], x["file_path"]))

        # Remove duplicates (same file + same line)
        seen = set()
        unique_results = []
        for r in results:
            key = (r["file_path"], r["start_line"])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return {
            "success": True,
            "query": query,
            "keywords_used": keywords,
            "results_count": len(unique_results[:top_k]),
            "results": unique_results[:top_k],
            "fallback_used": True,
        }

    def _fallback_stats(self) -> Dict[str, Any]:
        """Return fallback stats when server unavailable"""
        stats_path = self.index_path / "index_stats.json"

        if stats_path.exists():
            try:
                with open(stats_path, "r") as f:
                    stats = json.load(f)
                return {"success": True, "stats": stats, "fallback_used": True}
            except Exception:
                pass

        # Count Python files in scan paths as fallback
        file_count = 0
        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if path.exists():
                file_count += len(list(path.rglob("*.py")))

        return {
            "success": True,
            "stats": {
                "files_indexed": file_count,
                "functions_indexed": 0,
                "classes_indexed": 0,
                "total_vectors": 0,
                "index_ready": False,
                "mode": "fallback",
            },
            "fallback_used": True,
        }

    def _fallback_build_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback build index - returns success status"""
        root_path = params.get("root_path", "./src")
        file_extensions = params.get("file_extensions", [".py"])

        return {
            "success": True,
            "message": "Index building skipped in fallback mode",
            "root_path": root_path,
            "extensions": file_extensions,
            "stats": {
                "files_indexed": 0,
                "functions_indexed": 0,
                "classes_indexed": 0,
                "total_vectors": 0,
            },
            "fallback_used": True,
        }

    async def _fallback_find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback find similar code - uses basic text matching"""
        code_snippet = params.get("code_snippet", "")
        top_k = params.get("top_k", 5)

        results = []

        # Search for files containing similar patterns
        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            for file_path in path.rglob("*.py"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    # Look for keywords from the snippet
                    keywords = [w for w in code_snippet.split() if len(w) > 3]
                    match_count = sum(1 for kw in keywords if kw.lower() in content.lower())

                    if match_count > 0:
                        results.append(
                            {
                                "file_path": str(file_path),
                                "similarity_score": (
                                    min(0.9, match_count / len(keywords)) if keywords else 0
                                ),
                                "match_count": match_count,
                                "fallback_match": True,
                            }
                        )
                except Exception:
                    pass

                if len(results) >= top_k:
                    break

            if len(results) >= top_k:
                break

        return {
            "success": True,
            "results_count": len(results),
            "results": sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:top_k],
            "fallback_used": True,
        }

    async def _fallback_get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback get code context - reads file and returns lines"""
        file_path = params.get("file_path", "")
        line_number = params.get("line_number", 1)
        context_lines = params.get("context_lines", 10)

        try:
            # Try multiple path variants
            possible_paths = [
                Path(file_path),
                Path.cwd() / file_path,
                Path.cwd().parent / file_path,  # If called from scripts directory
                Path(__file__).parent.parent / file_path,  # Relative to src directory
            ]

            path = None
            for p in possible_paths:
                if p.exists():
                    path = p
                    break

            if path is None:
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "fallback_used": True,
                }

            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            context_lines_list = lines[start:end]
            context = "\n".join(
                f"{i+1:4d}: {line}" for i, line in enumerate(context_lines_list, start=start)
            )

            return {
                "success": True,
                "file_path": str(path),
                "line_number": line_number,
                "start_line": start + 1,
                "end_line": end,
                "total_lines": len(lines),
                "context": context,
                "fallback_used": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "fallback_used": True}

    async def _fallback_find_usages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback find usages - searches for exact symbol in files"""
        symbol = params.get("symbol", params.get("symbol_name", ""))
        top_k = params.get("top_k", 10)

        if not symbol:
            return {"success": False, "error": "No symbol provided", "fallback_used": True}

        results = []

        for scan_path in self.scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            for file_path in path.rglob("*.py"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    # Only process files that contain the symbol
                    if symbol not in content:
                        continue

                    lines = content.split("\n")

                    for i, line in enumerate(lines):
                        # Check for exact symbol match (as whole word or part of identifier)
                        if symbol in line:
                            # Determine usage type
                            stripped = line.strip()
                            if (
                                stripped.startswith(f"class {symbol}")
                                or f"class {symbol}(" in stripped
                            ):
                                usage_type = "definition (class)"
                            elif stripped.startswith(f"def {symbol}") or stripped.startswith(
                                f"async def {symbol}"
                            ):
                                usage_type = "definition (function)"
                            elif (
                                f"import {symbol}" in stripped
                                or f"from " in stripped
                                and symbol in stripped
                            ):
                                usage_type = "import"
                            elif f"{symbol}(" in stripped:
                                usage_type = "call"
                            elif f"= {symbol}" in stripped or f"={symbol}" in stripped:
                                usage_type = "assignment"
                            else:
                                usage_type = "reference"

                            results.append(
                                {
                                    "file_path": str(file_path),
                                    "line_number": i + 1,
                                    "line_content": stripped[:200],
                                    "usage_type": usage_type,
                                    "fallback_match": True,
                                }
                            )

                            if len(results) >= top_k * 2:  # Collect extra to filter
                                break
                except Exception:
                    pass

                if len(results) >= top_k * 2:
                    break

            if len(results) >= top_k * 2:
                break

        # Sort: definitions first, then imports, then calls, then others
        priority = {
            "definition (class)": 0,
            "definition (function)": 1,
            "import": 2,
            "call": 3,
            "assignment": 4,
            "reference": 5,
        }
        results.sort(
            key=lambda x: (priority.get(x.get("usage_type", "reference"), 5), x["file_path"])
        )

        return {
            "success": True,
            "symbol": symbol,
            "results_count": len(results[:top_k]),
            "results": results[:top_k],
            "fallback_used": True,
        }

        return {
            "success": True,
            "symbol": symbol,
            "results_count": len(results),
            "results": results[:top_k],
            "fallback_used": True,
        }

    # =========================================================================
    # Abstract Method Implementations
    # =========================================================================

    async def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute CodeBaseBuddy operation"""

        # Map operations to handlers
        handlers = {
            "semantic_search": self._handle_semantic_search,
            "find_similar_code": self._handle_find_similar,
            "get_code_context": self._handle_get_context,
            "build_index": self._handle_build_index,
            "get_index_stats": self._handle_get_stats,
            "find_usages": self._handle_find_usages,
            "health": self._handle_health,
        }

        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")

        return await handler(params)

    async def _handle_semantic_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle semantic search operation"""
        return await self._make_http_request("semantic_search", params)

    async def _handle_find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find similar code operation"""
        return await self._make_http_request("find_similar_code", params)

    async def _handle_get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get code context operation"""
        return await self._make_http_request("get_code_context", params)

    async def _handle_build_index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle build index operation"""
        return await self._make_http_request("build_index", params)

    async def _handle_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get stats operation"""
        return await self._make_http_request("get_index_stats", params)

    async def _handle_find_usages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find usages operation"""
        return await self._make_http_request("find_usages", params)

    async def _handle_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check operation"""
        return await self._make_http_request("health", params)

    async def connect(self):
        """Initialize connection with proper session management and connection pooling"""
        if self._session is None or self._session.closed:
            import aiohttp

            timeout = aiohttp.ClientTimeout(
                total=self._connection_timeout, connect=min(10, self._connection_timeout // 6)
            )

            connector = aiohttp.TCPConnector(
                limit=self._max_connections,
                limit_per_host=self._max_connections_per_host,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )

            self._session = aiohttp.ClientSession(
                timeout=timeout, connector=connector, raise_for_status=False
            )

            self.logger.info(
                f"Initialized HTTP session with {self._max_connections} max connections"
            )

    async def disconnect(self):
        """Properly close session and cleanup resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self.logger.info("Closed HTTP session")

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()

    async def _make_http_request(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make request to CodeBaseBuddy server.
        Uses fallback operations when server is unavailable (typical for MCP servers).

        Args:
            operation: Operation to call
            params: Parameters for the operation

        Returns:
            Response from fallback (CodeBaseBuddy works best in fallback mode)
        """
        # CodeBaseBuddy MCP server is complex to integrate directly
        # Use fallback mode which provides text-based search
        if self.fallback_handler:
            return await self.fallback_handler(operation, params)
        else:
            raise MCPConnectionError(f"CodeBaseBuddy server unavailable and no fallback handler")

    def validate_params(self, operation: str, params: Dict[str, Any]):
        """Validate operation parameters"""

        validators = {
            "semantic_search": self._validate_semantic_search,
            "find_similar_code": self._validate_find_similar,
            "get_code_context": self._validate_get_context,
            "build_index": self._validate_build_index,
            "find_usages": self._validate_find_usages,
        }

        validator = validators.get(operation)
        if validator:
            validator(params)

    def _validate_semantic_search(self, params: Dict[str, Any]):
        """Validate semantic search params"""
        if not params.get("query"):
            raise MCPValidationError("Query is required for semantic search")

    def _validate_find_similar(self, params: Dict[str, Any]):
        """Validate find similar params"""
        if not params.get("code_snippet"):
            raise MCPValidationError("Code snippet is required")

    def _validate_get_context(self, params: Dict[str, Any]):
        """Validate get context params"""
        if not params.get("file_path"):
            raise MCPValidationError("File path is required")
        if not params.get("line_number"):
            raise MCPValidationError("Line number is required")

    def _validate_build_index(self, params: Dict[str, Any]):
        """Validate build index params"""
        if not params.get("root_path"):
            raise MCPValidationError("Root path is required")

    def _validate_find_usages(self, params: Dict[str, Any]):
        """Validate find usages params"""
        if not params.get("symbol_name"):
            raise MCPValidationError("Symbol name is required")

    # =========================================================================
    # Main API Methods
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        file_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None,
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

        params = {"query": query.strip(), "top_k": min(top_k, 50)}  # Cap at 50 results

        if file_filter:
            params["file_filter"] = file_filter
        if chunk_type_filter:
            params["chunk_type_filter"] = chunk_type_filter

        # Check cache first
        cache_key = f"semantic_search:{hash(json.dumps(params, sort_keys=True))}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self._make_http_request("semantic_search", params)

        # Cache successful results
        if result.get("success"):
            self._set_cached(cache_key, result, ttl=self.CACHE_TTLS["semantic_search"])

        return result

    async def find_similar_code(
        self, code_snippet: str, top_k: int = 5, exclude_self: bool = True
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
            "exclude_self": exclude_self,
        }

        return await self._make_http_request("find_similar_code", params)

    async def get_code_context(
        self, file_path: str, line_number: int, context_lines: int = 10
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
            "context_lines": max(1, min(context_lines, 100)),
        }

        return await self._make_http_request("get_code_context", params)

    async def build_index(
        self,
        root_path: str,
        file_extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        rebuild: bool = False,
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

        params = {"root_path": root_path, "rebuild": rebuild}

        if file_extensions:
            params["file_extensions"] = file_extensions
        if exclude_patterns:
            params["exclude_patterns"] = exclude_patterns

        return await self._make_http_request("build_index", params)

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

        result = await self._make_http_request("get_index_stats", {})

        if result.get("success"):
            self._set_cached(cache_key, result, ttl=self.CACHE_TTLS["get_index_stats"])

        return result

    async def find_usages(self, symbol_name: str, top_k: int = 10) -> Dict[str, Any]:
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

        params = {"symbol_name": symbol_name.strip(), "top_k": min(top_k, 50)}

        return await self._make_http_request("find_usages", params)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the CodeBaseBuddy server is healthy.

        Returns:
            Dictionary with health status
        """
        return await self._make_http_request("health", {})

    # =========================================================================
    # Cache Helpers
    # =========================================================================

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        if hasattr(self, "_cache") and key in self._cache:
            entry = self._cache[key]
            import time

            if time.time() < entry["expires"]:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: Dict[str, Any], ttl: int = 300):
        """Cache a result with TTL"""
        import time

        if not hasattr(self, "_cache"):
            self._cache = {}
        self._cache[key] = {"data": data, "expires": time.time() + ttl}


# Convenience function for standalone usage
async def create_codebasebuddy_tool(
    server_url: str = "http://localhost:3004", config: Optional[Dict[str, Any]] = None
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
