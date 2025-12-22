"""
Filesystem MCP Server using FastMCP
Provides safe file operations with security boundaries
"""

from fastmcp import FastMCP
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import os
import re
import yaml
from datetime import datetime


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml with environment variable substitution"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    default_config = {
        "port": 3001,
        "host": "0.0.0.0",
        "allowed_paths": ["./workspace", "./projects", "./src", "./config", "./examples"],
        "blocked_patterns": [r"\.\./", r"/etc/", r"/root/", r"\.ssh/", r"\.env$"],
        "max_file_size_mb": 10,
        "rate_limit_minute": 100,
        "rate_limit_hour": 2000
    }
    
    if not config_path.exists():
        logging.warning(f"Config file not found at {config_path}, using defaults")
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
        
        # Get filesystem server config
        server_config = full_config.get("mcp_servers", {}).get("filesystem", {})
        
        # Substitute environment variables (${VAR_NAME} pattern)
        def substitute_env_vars(value):
            if isinstance(value, str):
                pattern = r'\$\{([^}]+)\}'
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

# Initialize FastMCP server
mcp = FastMCP("Filesystem Operations")
logger = logging.getLogger("mcp.filesystem")

# Security configuration (from config)
ALLOWED_PATHS = [Path(p).resolve() for p in CONFIG.get("allowed_paths", ["./workspace", "./src"])]

BLOCKED_PATTERNS = CONFIG.get("blocked_patterns", [
    r"\.\./",  # Directory traversal
    r"/etc/",  # System files
    r"/root/",  # Root directory
    r"\.ssh/",  # SSH keys
    r"\.env$",  # Environment files
])

# Add default patterns that should always be blocked
DEFAULT_BLOCKED = [r"\.git/config", r"__pycache__", r"\.pyc$"]
BLOCKED_PATTERNS.extend([p for p in DEFAULT_BLOCKED if p not in BLOCKED_PATTERNS])

# File size limits (from config)
MAX_FILE_SIZE_MB = CONFIG.get("max_file_size_mb", 10)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# File type filters for code analysis
CODE_FILE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".yaml", ".yml", ".json", ".xml", ".toml", ".ini", ".cfg"
}


def is_path_allowed(path: str) -> bool:
    """Validate path is within allowed directories"""
    try:
        resolved = Path(path).resolve()

        # Check against blocked patterns
        path_str = str(resolved)
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, path_str):
                logger.warning(f"Blocked pattern matched: {pattern} in {path_str}")
                return False

        # Check if within allowed paths
        return any(
            str(resolved).startswith(str(allowed))
            for allowed in ALLOWED_PATHS
        )
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False


def is_code_file(path: Path) -> bool:
    """Check if file is a code file"""
    return path.suffix.lower() in CODE_FILE_EXTENSIONS


@mcp.tool()
async def read_file(path: str, max_size_mb: Optional[float] = None) -> Dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        path: Path to the file to read
        max_size_mb: Maximum file size in MB (default: 10MB)

    Returns:
        Dictionary with file content and metadata

    Example:
        result = await read_file("./src/main.py")
        content = result["content"]
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Not a file: {path}")

    # Check file size
    stat = file_path.stat()
    size_limit = (max_size_mb or MAX_FILE_SIZE_MB) * 1024 * 1024
    if stat.st_size > size_limit:
        raise ValueError(f"File too large: {stat.st_size / 1024 / 1024:.2f}MB exceeds limit of {max_size_mb or MAX_FILE_SIZE_MB}MB")

    try:
        content = file_path.read_text(encoding='utf-8')

        return {
            "content": content,
            "path": str(file_path),
            "size": stat.st_size,
            "lines": len(content.split('\n')),
            "encoding": "utf-8",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except UnicodeDecodeError:
        # Try binary read for non-text files
        content = file_path.read_bytes()
        return {
            "content": content.hex(),
            "path": str(file_path),
            "size": len(content),
            "encoding": "binary",
            "note": "Binary file - content returned as hex string"
        }


@mcp.tool()
async def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """
    Write content to a file.

    Args:
        path: Path to the file to write
        content: Content to write to the file
        create_dirs: Create parent directories if they don't exist

    Returns:
        Success status and metadata

    Example:
        result = await write_file("./output/result.txt", "Hello World")
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    file_path = Path(path)

    # Create parent directories if needed
    if create_dirs and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    file_path.write_text(content, encoding='utf-8')
    stat = file_path.stat()

    return {
        "status": "success",
        "path": str(file_path),
        "bytes_written": stat.st_size,
        "lines_written": len(content.split('\n'))
    }


@mcp.tool()
async def list_directory(
    path: str,
    recursive: bool = False,
    filter_code_files: bool = False
) -> Dict[str, Any]:
    """
    List contents of a directory.

    Args:
        path: Directory path to list
        recursive: Include subdirectories recursively
        filter_code_files: Only show code files

    Returns:
        List of files and directories with metadata

    Example:
        result = await list_directory("./src", recursive=True, filter_code_files=True)
        files = result["files"]
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    items = []

    if recursive:
        iterator = dir_path.rglob("*")
    else:
        iterator = dir_path.iterdir()

    for item in iterator:
        # Skip if not allowed
        if not is_path_allowed(str(item)):
            continue

        # Filter code files if requested
        if filter_code_files and item.is_file() and not is_code_file(item):
            continue

        try:
            stat = item.stat()
            items.append({
                "name": item.name,
                "path": str(item.relative_to(dir_path)),
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix if item.is_file() else None,
            })
        except Exception as e:
            logger.warning(f"Error accessing {item}: {e}")
            continue

    return {
        "path": str(dir_path),
        "items": items,
        "count": len(items),
        "recursive": recursive,
        "filtered": filter_code_files
    }


@mcp.tool()
async def search_files(
    path: str,
    query: str,
    case_sensitive: bool = False,
    max_results: int = 100,
    file_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for text within files in a directory.

    Args:
        path: Root directory to search
        query: Text to search for
        case_sensitive: Whether search is case-sensitive
        max_results: Maximum number of matching files to return
        file_pattern: Optional glob pattern to filter files (e.g., "*.py")

    Returns:
        Matching files with line numbers and context

    Example:
        result = await search_files("./src", "async def", file_pattern="*.py")
        matches = result["results"]
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    search_path = Path(path)
    if not search_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    results = []
    pattern = file_pattern or "**/*"

    # Prepare query
    search_query = query if case_sensitive else query.lower()

    for file_path in search_path.glob(pattern):
        if len(results) >= max_results:
            break

        # Skip non-files and non-allowed paths
        if not file_path.is_file() or not is_path_allowed(str(file_path)):
            continue

        # Skip non-code files
        if not is_code_file(file_path):
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            matches = []
            for i, line in enumerate(lines, 1):
                check_line = line if case_sensitive else line.lower()
                if search_query in check_line:
                    matches.append({
                        "line_number": i,
                        "content": line.strip(),
                        "context_before": lines[max(0, i-2):i-1] if i > 1 else [],
                        "context_after": lines[i:min(len(lines), i+2)] if i < len(lines) else []
                    })

            if matches:
                results.append({
                    "file": str(file_path.relative_to(search_path)),
                    "absolute_path": str(file_path),
                    "matches": matches,
                    "match_count": len(matches)
                })

        except UnicodeDecodeError:
            # Skip binary files
            continue
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            continue

    return {
        "query": query,
        "path": str(search_path),
        "results": results,
        "total_files": len(results),
        "total_matches": sum(r["match_count"] for r in results),
        "case_sensitive": case_sensitive
    }


@mcp.tool()
async def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get detailed metadata about a file.

    Args:
        path: File path to get information about

    Returns:
        File metadata including size, dates, permissions

    Example:
        info = await get_file_info("./src/main.py")
        print(f"File size: {info['size']} bytes")
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    stat = file_path.stat()

    return {
        "path": str(file_path),
        "name": file_path.name,
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "is_file": file_path.is_file(),
        "is_directory": file_path.is_dir(),
        "is_symlink": file_path.is_symlink(),
        "extension": file_path.suffix,
        "is_code_file": is_code_file(file_path) if file_path.is_file() else False,
    }


@mcp.tool()
async def analyze_code_structure(path: str) -> Dict[str, Any]:
    """
    Analyze code structure in a directory.

    Args:
        path: Directory path to analyze

    Returns:
        Code structure analysis with file counts by type

    Example:
        analysis = await analyze_code_structure("./src")
        print(f"Python files: {analysis['by_extension']['.py']}")
    """
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    stats = {
        "total_files": 0,
        "total_lines": 0,
        "total_size": 0,
        "by_extension": {},
        "largest_files": []
    }

    files_with_sizes = []

    for file_path in dir_path.rglob("*"):
        if not file_path.is_file() or not is_path_allowed(str(file_path)):
            continue

        if not is_code_file(file_path):
            continue

        try:
            stat = file_path.stat()
            content = file_path.read_text(encoding='utf-8')
            lines = len(content.split('\n'))

            stats["total_files"] += 1
            stats["total_lines"] += lines
            stats["total_size"] += stat.st_size

            ext = file_path.suffix or "no_extension"
            if ext not in stats["by_extension"]:
                stats["by_extension"][ext] = {"count": 0, "lines": 0, "size": 0}

            stats["by_extension"][ext]["count"] += 1
            stats["by_extension"][ext]["lines"] += lines
            stats["by_extension"][ext]["size"] += stat.st_size

            files_with_sizes.append({
                "file": str(file_path.relative_to(dir_path)),
                "size": stat.st_size,
                "lines": lines
            })

        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")
            continue

    # Get top 10 largest files
    files_with_sizes.sort(key=lambda x: x["size"], reverse=True)
    stats["largest_files"] = files_with_sizes[:10]

    return stats


@mcp.tool()
async def delete_file(path: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Delete a file from the filesystem.

    Args:
        path: Path to the file to delete
        confirm: Must be True to actually delete (safety check)

    Returns:
        Success status and deleted file info

    Example:
        result = await delete_file("./workspace/temp.txt", confirm=True)
    """
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Set confirm=True to actually delete the file",
            "path": path
        }
    
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Not a file (use rmdir for directories): {path}")

    # Get file info before deletion
    stat = file_path.stat()
    file_info = {
        "name": file_path.name,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }

    # Delete the file
    file_path.unlink()
    logger.info(f"Deleted file: {path}")

    return {
        "status": "success",
        "deleted_file": file_info,
        "path": str(file_path)
    }


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check Filesystem MCP server health.

    Returns:
        Health status including allowed paths and accessibility

    Example:
        health = await health_check()
        print(f"Status: {health['status']}")
    """
    health = {
        "server": "filesystem_mcp",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "allowed_paths": [],
        "blocked_patterns": BLOCKED_PATTERNS,
        "max_file_size_mb": MAX_FILE_SIZE_MB
    }
    
    # Check each allowed path
    for allowed_path in ALLOWED_PATHS:
        path_status = {
            "path": str(allowed_path),
            "exists": allowed_path.exists(),
            "readable": allowed_path.exists() and os.access(allowed_path, os.R_OK),
            "writable": allowed_path.exists() and os.access(allowed_path, os.W_OK)
        }
        health["allowed_paths"].append(path_status)
    
    # Check if any paths are inaccessible
    if not any(p["readable"] for p in health["allowed_paths"]):
        health["status"] = "degraded"
        health["warning"] = "No allowed paths are accessible"
    
    return health


if __name__ == "__main__":
    port = CONFIG["port"]
    host = CONFIG["host"]
    
    print(f"Starting Filesystem MCP Server on http://{host}:{port}...")
    print(f"Allowed paths: {[str(p) for p in ALLOWED_PATHS]}")
    print(f"Max file size: {MAX_FILE_SIZE_MB}MB")
    print(f"Config source: config/config.yaml + environment variables")

    # Run server directly
    mcp.run(transport="sse", port=port, host=host)
