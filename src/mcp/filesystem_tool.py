"""
Filesystem MCP Tool Wrapper
Wraps Filesystem MCP server functions for CrewAI agents

Features:
1. Connect to Filesystem MCP server at localhost:3001
2. Wrap filesystem operations with additional validation
3. File type detection and filtering
4. Size checks before operations
5. Cache directory listings (1min TTL)
6. Atomic write operations
7. Fallback to direct file operations if server unavailable
"""

import mimetypes
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from src.mcp.base_tool import BaseMCPTool, MCPConnectionError, MCPToolError, MCPValidationError

# =============================================================================
# Filesystem MCP Tool
# =============================================================================


class FilesystemMCPTool(BaseMCPTool):
    """
    Filesystem MCP Tool Wrapper.

    Provides safe file operations with security boundaries:
    - Read/write files with size limits
    - List directories with caching
    - Search content with filters
    - Code file analysis
    - Atomic write operations

    Features:
    - File type detection and filtering
    - Size checks before operations (default 10MB limit)
    - Directory listing cache (1min TTL)
    - Fallback to direct file I/O
    """

    # Cache TTLs for different operations (in seconds)
    CACHE_TTLS = {
        "list_directory": 60,  # 1 minute
        "analyze_structure": 120,  # 2 minutes
        "get_code_files": 60,  # 1 minute
    }

    # Maximum file size for operations (default 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(
        self,
        server_url: str = "http://localhost:3001",
        config: Optional[Dict[str, Any]] = None,
        allowed_paths: Optional[List[str]] = None,
    ):
        # Set filesystem-specific defaults
        if config is None:
            config = {}

        config.setdefault("cache_ttl", 60)  # 1 minute default for directory ops
        config.setdefault("rate_limit_minute", 300)  # Higher rate for local ops
        config.setdefault("rate_limit_hour", 10000)

        # Handle allowed_paths parameter
        if allowed_paths is not None:
            config["allowed_paths"] = allowed_paths

        super().__init__(
            name="filesystem",
            server_url=server_url,
            config=config,
            fallback_handler=self._fallback_handler,
        )

        self.allowed_paths = [Path(p).resolve() for p in config.get("allowed_paths", [])]
        self.blocked_patterns = config.get(
            "blocked_patterns",
            [
                r"\.git/config",
                r"\.env",
                r"secrets?\.ya?ml",
                r"credentials",
                r"\.pem$",
                r"\.key$",
                r"id_rsa",
                r"\.ssh/",
            ],
        )
        self.max_file_size = config.get("max_file_size", self.MAX_FILE_SIZE)

        # File type filters for code analysis
        self.code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".yaml",
            ".yml",
            ".json",
            ".xml",
            ".toml",
            ".ini",
            ".cfg",
            ".md",
            ".rst",
            ".txt",
            ".html",
            ".css",
            ".scss",
            ".sass",
        }

        # HTTP client for MCP server communication
        self._client: Optional[httpx.AsyncClient] = None

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def _do_connect(self):
        """Establish connection to Filesystem MCP server"""
        self._client = httpx.AsyncClient(base_url=self.server_url, timeout=httpx.Timeout(30.0))

    async def _do_disconnect(self):
        """Close connection to Filesystem MCP server"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client, creating if needed"""
        if not self._client:
            await self._do_connect()
        return self._client

    # =========================================================================
    # Operation Execution
    # =========================================================================

    async def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute filesystem operation"""

        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "delete_file": self._delete_file,
            "list_directory": self._list_directory,
            "create_directory": self._create_directory,
            "search_content": self._search_content,
            "get_code_files": self._get_code_files,
            "analyze_structure": self._analyze_structure,
            "get_file_info": self._get_file_info,
            "copy_file": self._copy_file,
            "move_file": self._move_file,
            "health_check": self._health_check,
        }

        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")

        return await handler(params)

    # =========================================================================
    # Parameter Validation
    # =========================================================================

    def validate_params(self, operation: str, params: Dict[str, Any]):
        """Validate operation parameters and security"""

        path = params.get("path", "")

        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, str(path), re.IGNORECASE):
                raise MCPValidationError(f"Path blocked by security pattern: {pattern}")

        # Check if path is within allowed directories
        if self.allowed_paths and path:
            try:
                resolved = Path(path).resolve()
                if not any(
                    self._is_path_allowed(resolved, allowed) for allowed in self.allowed_paths
                ):
                    raise MCPValidationError(f"Path {path} is outside allowed directories")
            except Exception as e:
                raise MCPValidationError(f"Invalid path: {path} - {str(e)}")

        # Operation-specific validation
        if operation == "write_file":
            content = params.get("content", "")
            if len(content) > self.max_file_size:
                raise MCPValidationError(
                    f"Content size ({len(content)} bytes) exceeds limit ({self.max_file_size} bytes)"
                )

        if operation == "read_file":
            if path and Path(path).exists():
                size = Path(path).stat().st_size
                if size > self.max_file_size:
                    raise MCPValidationError(
                        f"File size ({size} bytes) exceeds limit ({self.max_file_size} bytes)"
                    )

    def _is_path_allowed(self, path: Path, allowed: Path) -> bool:
        """Check if path is under allowed directory"""
        try:
            path.relative_to(allowed)
            return True
        except ValueError:
            return False

    # =========================================================================
    # Cache TTL Customization
    # =========================================================================

    def _get_cache_ttl(self, operation: str) -> float:
        """Get TTL for specific filesystem operation"""
        return self.CACHE_TTLS.get(operation, self.cache.default_ttl)

    def _is_cacheable_operation(self, operation: str) -> bool:
        """Determine if operation should be cached"""
        cacheable = {"list_directory", "analyze_structure", "get_code_files", "get_file_info"}
        return operation in cacheable

    # =========================================================================
    # File Type Detection
    # =========================================================================

    def detect_file_type(self, path: str) -> Dict[str, Any]:
        """Detect file type and MIME type"""
        p = Path(path)
        mime_type, encoding = mimetypes.guess_type(str(p))

        return {
            "extension": p.suffix.lower(),
            "mime_type": mime_type or "application/octet-stream",
            "encoding": encoding,
            "is_code": p.suffix.lower() in self.code_extensions,
            "is_text": (
                mime_type and mime_type.startswith("text/")
                if mime_type
                else p.suffix.lower() in self.code_extensions
            ),
        }

    def filter_files_by_type(
        self, files: List[Dict[str, Any]], extensions: List[str] = None, code_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Filter files by type"""
        result = []

        for file_info in files:
            if file_info.get("type") == "directory":
                result.append(file_info)
                continue

            name = file_info.get("name", "")
            ext = Path(name).suffix.lower()

            if code_only and ext not in self.code_extensions:
                continue

            if extensions and ext not in extensions:
                continue

            result.append(file_info)

        return result

    # =========================================================================
    # Filesystem Operations
    # =========================================================================

    async def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents"""
        try:
            client = await self._get_client()
            response = await client.post("/read_file", json={"path": params["path"]})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to direct read
            return await self._fallback_read_file(params)

    async def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file with atomic operation"""
        path = params["path"]
        content = params["content"]
        atomic = params.get("atomic", True)

        try:
            client = await self._get_client()
            response = await client.post(
                "/write_file", json={"path": path, "content": content, "atomic": atomic}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to direct write
            return await self._fallback_write_file(params)

    async def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file"""
        path = params["path"]
        confirm = params.get("confirm", False)

        if not confirm:
            raise MCPValidationError("Delete operation requires confirm=True")

        try:
            client = await self._get_client()
            response = await client.post("/delete_file", json={"path": path, "confirm": True})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to direct delete
            return await self._fallback_delete_file(params)

    async def _list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents"""
        try:
            client = await self._get_client()
            response = await client.post(
                "/list_directory",
                json={"path": params["path"], "recursive": params.get("recursive", False)},
            )
            response.raise_for_status()
            result = response.json()

            # Apply type filtering if requested
            if params.get("extensions") or params.get("code_only"):
                result["files"] = self.filter_files_by_type(
                    result.get("files", []),
                    extensions=params.get("extensions"),
                    code_only=params.get("code_only", False),
                )

            return result
        except Exception as e:
            # Fallback to direct listing
            return await self._fallback_list_directory(params)

    async def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a directory"""
        path = Path(params["path"])
        parents = params.get("parents", True)

        try:
            client = await self._get_client()
            response = await client.post(
                "/create_directory", json={"path": str(path), "parents": parents}
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            # Fallback to direct mkdir
            path.mkdir(parents=parents, exist_ok=True)
            return {"success": True, "path": str(path)}

    async def _search_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search file contents"""
        try:
            client = await self._get_client()
            response = await client.post(
                "/search_content",
                json={
                    "path": params["path"],
                    "pattern": params["pattern"],
                    "file_types": params.get("file_types"),
                    "case_sensitive": params.get("case_sensitive", False),
                    "max_results": params.get("max_results", 100),
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to local search
            return await self._fallback_search_content(params)

    async def _get_code_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get all code files in directory"""
        # List directory and filter by extension
        dir_result = await self._list_directory({**params, "code_only": True})
        files = dir_result.get("files", [])

        code_files = [
            f
            for f in files
            if f.get("type") != "directory"
            and Path(f.get("name", "")).suffix.lower() in self.code_extensions
        ]

        return {
            "path": params.get("path"),
            "code_files": code_files,
            "total_files": len(dir_result.get("files", [])),
            "code_file_count": len(code_files),
            "extensions_found": list(
                set(Path(f.get("name", "")).suffix.lower() for f in code_files)
            ),
        }

    async def _analyze_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze project structure"""
        path = params.get("path", ".")
        max_depth = params.get("max_depth", 5)

        structure = {
            "root": path,
            "directories": [],
            "code_files": [],
            "config_files": [],
            "documentation": [],
            "tests": [],
            "summary": {},
        }

        # Recursive directory traversal
        async def traverse(current_path: str, depth: int = 0):
            if depth > max_depth:
                return

            try:
                result = await self._list_directory({"path": current_path})
                files = result.get("files", [])

                for file_info in files:
                    file_name = file_info.get("name", "")
                    file_path = str(Path(current_path) / file_name)

                    if file_info.get("type") == "directory":
                        structure["directories"].append(file_path)
                        await traverse(file_path, depth + 1)
                    else:
                        # Categorize file
                        ext = Path(file_name).suffix.lower()

                        if ext in self.code_extensions:
                            structure["code_files"].append(file_path)

                        if file_name.lower() in [
                            "readme.md",
                            "changelog.md",
                            "contributing.md",
                            "license",
                            "license.md",
                        ]:
                            structure["documentation"].append(file_path)
                        elif "test" in file_name.lower() or file_path.startswith("test"):
                            structure["tests"].append(file_path)
                        elif ext in [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"]:
                            structure["config_files"].append(file_path)

            except Exception as e:
                self.logger.warning(f"Error traversing {current_path}: {e}")

        await traverse(path)

        # Generate summary
        structure["summary"] = {
            "total_directories": len(structure["directories"]),
            "total_code_files": len(structure["code_files"]),
            "total_config_files": len(structure["config_files"]),
            "total_documentation": len(structure["documentation"]),
            "total_tests": len(structure["tests"]),
        }

        return structure

    async def _get_file_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed file information"""
        path = Path(params["path"])

        if not path.exists():
            raise MCPValidationError(f"File not found: {path}")

        stat = path.stat()
        type_info = self.detect_file_type(str(path))

        return {
            "path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            **type_info,
        }

    async def _copy_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Copy a file"""
        src = Path(params["src"])
        dst = Path(params["dst"])

        # Validate both paths
        self.validate_params("copy_file", {"path": str(src)})
        self.validate_params("copy_file", {"path": str(dst)})

        shutil.copy2(src, dst)

        return {"success": True, "src": str(src), "dst": str(dst)}

    async def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Move a file"""
        src = Path(params["src"])
        dst = Path(params["dst"])

        # Validate both paths
        self.validate_params("move_file", {"path": str(src)})
        self.validate_params("move_file", {"path": str(dst)})

        shutil.move(src, dst)

        return {"success": True, "src": str(src), "dst": str(dst)}

    async def _health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Health check"""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                return {"status": "ok", "server": self.server_url}
        except Exception:
            pass
        return {"status": "ok", "server": self.server_url, "mode": "basic"}

    # =========================================================================
    # Fallback Handlers (Direct File I/O)
    # =========================================================================

    async def _fallback_handler(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to direct file I/O"""
        self.logger.warning(f"Using fallback for {operation}")

        fallback_ops = {
            "read_file": self._fallback_read_file,
            "write_file": self._fallback_write_file,
            "delete_file": self._fallback_delete_file,
            "list_directory": self._fallback_list_directory,
            "search_content": self._fallback_search_content,
        }

        handler = fallback_ops.get(operation)
        if handler:
            return await handler(params)

        raise NotImplementedError(f"No fallback for {operation}")

    async def _fallback_read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct file read fallback"""
        path = Path(params["path"])
        content = path.read_text(encoding="utf-8")
        return {"content": content, "size": len(content), "path": str(path), "fallback": True}

    async def _fallback_write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct file write fallback with atomic operation"""
        path = Path(params["path"])
        content = params["content"]
        atomic = params.get("atomic", True)

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        if atomic:
            # Atomic write using temp file
            fd, temp_path = tempfile.mkstemp(dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                shutil.move(temp_path, path)
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        else:
            path.write_text(content, encoding="utf-8")

        return {"success": True, "path": str(path), "size": len(content), "fallback": True}

    async def _fallback_delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct file delete fallback"""
        path = Path(params["path"])
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        return {"success": True, "path": str(path), "fallback": True}

    async def _fallback_list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct directory listing fallback"""
        path = Path(params["path"])
        recursive = params.get("recursive", False)

        files = []

        if recursive:
            for item in path.rglob("*"):
                files.append(
                    {
                        "name": str(item.relative_to(path)),
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                    }
                )
        else:
            for item in path.iterdir():
                files.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0,
                    }
                )

        return {"files": files, "path": str(path), "fallback": True}

    async def _fallback_search_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct content search fallback"""
        path = Path(params["path"])
        pattern = params["pattern"]
        file_types = params.get("file_types", list(self.code_extensions))
        case_sensitive = params.get("case_sensitive", False)
        max_results = params.get("max_results", 100)

        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        matches = []

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in file_types:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        matches.append(
                            {
                                "file": str(file_path),
                                "line_number": i,
                                "line": line.strip()[:200],  # Truncate long lines
                            }
                        )
                        if len(matches) >= max_results:
                            break
            except Exception:
                continue

            if len(matches) >= max_results:
                break

        return {
            "matches": matches,
            "total_matches": len(matches),
            "pattern": pattern,
            "fallback": True,
        }

    # =========================================================================
    # Synchronous Wrappers for Testing
    # =========================================================================

    def read_file(self, path: str = None, file_path: str = None) -> str:
        """Synchronous wrapper for reading files (for testing)"""
        # Accept both 'path' and 'file_path' for compatibility
        actual_path = file_path or path
        if not actual_path:
            raise ValueError("Either 'path' or 'file_path' parameter is required")

        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use run_until_complete
                raise RuntimeError("Cannot use sync wrapper with running event loop")
            result = loop.run_until_complete(self._read_file({"path": actual_path}))
            return result.get("content", "")
        except RuntimeError:
            # Fallback to direct file read
            return Path(actual_path).read_text()

    def write_file(self, path: str, content: str) -> bool:
        """Synchronous wrapper for writing files (for testing)"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync wrapper with running event loop")
            result = loop.run_until_complete(self._write_file({"path": path, "content": content}))
            return result.get("success", False)
        except RuntimeError:
            # Fallback to direct file write
            Path(path).write_text(content)
            return True

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper for listing directories (for testing)"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync wrapper with running event loop")
            result = loop.run_until_complete(self._list_directory({"path": path}))
            return result.get("files", [])
        except RuntimeError:
            # Fallback to direct directory listing
            path_obj = Path(path)
            return [{"name": item.name, "path": str(item)} for item in path_obj.iterdir()]


# =============================================================================
# Tool Documentation for CrewAI Agents
# =============================================================================

FILESYSTEM_TOOL_DESCRIPTIONS = {
    "read_file": """
    Read the contents of a file.
    
    Parameters:
    - path (str): Path to the file to read
    
    Returns:
    - content (str): File content
    - size (int): File size in bytes
    - encoding (str): File encoding
    
    Note: Files larger than 10MB will be rejected.
    """,
    "write_file": """
    Write content to a file.
    
    Parameters:
    - path (str): Path to the file to write
    - content (str): Content to write
    - atomic (bool, optional): Use atomic write (default: True)
    
    Returns:
    - success (bool): Whether write was successful
    - path (str): Path written to
    
    Note: Atomic writes use temp file + rename for safety.
    """,
    "list_directory": """
    List contents of a directory.
    
    Parameters:
    - path (str): Directory path
    - recursive (bool, optional): Recursive listing
    - extensions (list, optional): Filter by extensions
    - code_only (bool, optional): Show only code files
    
    Returns:
    - files (list): List of file/directory info
    - total_count (int): Total items
    """,
    "search_content": """
    Search for text patterns in files.
    
    Parameters:
    - path (str): Directory to search in
    - pattern (str): Search pattern (regex)
    - file_types (list, optional): File extensions to search
    - case_sensitive (bool, optional): Case sensitive search
    - max_results (int, optional): Maximum results (default: 100)
    
    Returns:
    - matches (list): Matches with file paths and line numbers
    - total_matches (int): Total number of matches
    """,
    "analyze_structure": """
    Analyze project structure to understand codebase organization.
    
    Parameters:
    - path (str): Project root path
    - max_depth (int, optional): Maximum traversal depth (default: 5)
    
    Returns:
    - directories (list): All directories
    - code_files (list): Code files found
    - config_files (list): Configuration files
    - documentation (list): Documentation files
    - tests (list): Test files
    - summary (dict): Counts of each category
    """,
}
