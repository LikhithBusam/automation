"""
CodeBaseBuddy MCP Server using FastMCP
Provides semantic code search and understanding capabilities

Features:
- Vector-based semantic search using sentence-transformers
- Function-level code indexing with AST parsing
- FAISS index for fast similarity search
- File mappings for tracking code locations
- Cross-file dependency tracking
"""

# Suppress TensorFlow and other verbose logging before any imports
import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import ast
import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastmcp import FastMCP

# Lazy loading for heavy libraries
EMBEDDINGS_AVAILABLE = False
FAISS_AVAILABLE = False
SentenceTransformer = None
faiss = None


def _lazy_load_embeddings():
    """Lazy load sentence_transformers to avoid slow startup"""
    global EMBEDDINGS_AVAILABLE, SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as ST

            SentenceTransformer = ST
            EMBEDDINGS_AVAILABLE = True
        except ImportError:
            EMBEDDINGS_AVAILABLE = False
            logging.warning(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )
    return EMBEDDINGS_AVAILABLE


def _lazy_load_faiss():
    """Lazy load faiss to avoid slow startup"""
    global FAISS_AVAILABLE, faiss
    if faiss is None:
        try:
            import faiss as faiss_module

            faiss = faiss_module
            FAISS_AVAILABLE = True
        except ImportError:
            FAISS_AVAILABLE = False
            logging.warning("faiss not installed. Install with: pip install faiss-cpu")
    return FAISS_AVAILABLE


import asyncio
import shutil
from contextlib import asynccontextmanager
from threading import RLock

import numpy as np

# =========================================================================
# Concurrency Safety - Read/Write Lock Manager
# =========================================================================


class IndexManager:
    """Thread-safe index manager with read/write locks"""

    def __init__(self):
        self._lock = RLock()
        self._updating = False
        self._search_count = 0

    @asynccontextmanager
    async def read_lock(self):
        """Allow multiple concurrent readers"""
        # Wait if index is being updated
        while self._updating:
            await asyncio.sleep(0.1)

        with self._lock:
            self._search_count += 1

        try:
            yield
        finally:
            with self._lock:
                self._search_count -= 1

    @asynccontextmanager
    async def write_lock(self):
        """Exclusive write access for index updates"""
        with self._lock:
            self._updating = True

        # Wait for active searches to complete
        while self._search_count > 0:
            await asyncio.sleep(0.1)

        try:
            yield
        finally:
            with self._lock:
                self._updating = False


# Global index manager
index_manager = IndexManager()


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml with environment variable substitution"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    default_config = {
        "port": 3004,
        "host": "0.0.0.0",
        "index_path": "./data/codebase_index",
        "embedding_dimensions": 384,
        "embedding_model": "all-MiniLM-L6-v2",
        "file_extensions": [
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
            ".md",
            ".txt",
        ],
        "exclude_patterns": [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".eggs",
            "*.egg-info",
            ".tox",
            ".coverage",
            "htmlcov",
        ],
        "exclude_files": [".pyc", ".pyo", ".so", ".dll", ".exe", ".o", ".a", ".class", ".jar"],
        "scan_paths": ["./src", "./mcp_servers", "./config"],
        "rate_limit_minute": 100,
        "rate_limit_hour": 2000,
        "cache_ttl": 300,
    }

    if not config_path.exists():
        logging.warning(f"Config file not found at {config_path}, using defaults")
        return default_config

    try:
        with open(config_path, "r") as f:
            full_config = yaml.safe_load(f)

        # Get codebasebuddy server config
        server_config = full_config.get("mcp_servers", {}).get("codebasebuddy", {})

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

# Initialize FastMCP server
mcp = FastMCP("CodeBaseBuddy - Semantic Code Search")
logger = logging.getLogger("mcp.codebasebuddy")

# Configuration (from config.yaml)
INDEX_DIR = Path(CONFIG.get("index_path", "./data/codebase_index"))
INDEX_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
MAPPINGS_PATH = INDEX_DIR / "file_mappings.json"
STATS_PATH = INDEX_DIR / "index_stats.json"

# Embedding dimensions (from config)
EMBEDDING_DIMENSIONS = CONFIG.get("embedding_dimensions", 384)

# Embedding model name (from config)
EMBEDDING_MODEL_NAME = CONFIG.get("embedding_model", "all-MiniLM-L6-v2")

# Code file extensions to index (from config)
file_extensions_list = CONFIG.get(
    "file_extensions", [".py", ".js", ".ts", ".yaml", ".yml", ".json", ".md"]
)
CODE_EXTENSIONS = set(file_extensions_list)

# Directories to exclude (from config)
exclude_patterns_list = CONFIG.get(
    "exclude_patterns", ["__pycache__", ".git", "venv", "node_modules"]
)
EXCLUDE_DIRS = set(exclude_patterns_list)

# Files to exclude (from config)
exclude_files_list = CONFIG.get("exclude_files", [".pyc", ".pyo", ".so", ".dll", ".exe"])
EXCLUDE_FILES = set(exclude_files_list)


@dataclass
class CodeChunk:
    """Represents a chunk of code for indexing"""

    id: int
    file_path: str
    chunk_type: str  # 'function', 'class', 'file', 'docstring'
    name: str
    content: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    parent: Optional[str] = None  # Parent class/function name


# Global state
embedding_model = None
faiss_index = None
file_mappings: Dict[int, Dict] = {}
index_stats = {
    "total_vectors": 0,
    "files_indexed": 0,
    "functions_indexed": 0,
    "classes_indexed": 0,
    "last_indexed": None,
    "index_size_bytes": 0,
}


def init_embedding_model():
    """Initialize the sentence-transformer embedding model"""
    global embedding_model

    # Lazy load dependencies
    if not _lazy_load_embeddings():
        logger.error("sentence-transformers not available")
        return False

    try:
        # Use model from config for consistency
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Loaded sentence-transformers embedding model: {EMBEDDING_MODEL_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return False


def create_embedding(text: str) -> Optional[np.ndarray]:
    """Create embedding vector for text"""
    global embedding_model

    # Ensure FAISS is loaded
    _lazy_load_faiss()

    if embedding_model is None:
        if not init_embedding_model():
            return None

    try:
        embedding = embedding_model.encode(text, convert_to_numpy=True)
        return embedding.astype("float32")  # FAISS requires float32
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        return None


def validate_index() -> bool:
    """Validate index integrity and compatibility"""
    global index_stats

    try:
        # Check if stats exist
        if not STATS_PATH.exists():
            logger.warning("Index stats not found")
            return False

        # Load and validate stats
        with open(STATS_PATH, "r") as f:
            stats = json.load(f)
            index_stats.update(stats)

        # Validate index version
        index_version = index_stats.get("index_version", "1.0.0")
        current_version = "2.0.0"

        if index_version != current_version:
            logger.warning(
                f"Index version mismatch: {index_version} vs {current_version}. "
                "Rebuilding recommended."
            )
            return False

        # Validate embedding dimensions match
        expected_dims = CONFIG.get("embedding_dimensions", 384)

        if FAISS_INDEX_PATH.exists():
            # Lazy load FAISS
            if not _lazy_load_faiss():
                logger.error("FAISS not available")
                return False

            temp_index = faiss.read_index(str(FAISS_INDEX_PATH))
            actual_dims = temp_index.d

            if actual_dims != expected_dims:
                logger.error(
                    f"Dimension mismatch: index has {actual_dims}, "
                    f"config expects {expected_dims}"
                )
                return False

        # Validate mappings checksum
        if MAPPINGS_PATH.exists():
            mappings_checksum = hashlib.md5(MAPPINGS_PATH.read_bytes()).hexdigest()
            expected_checksum = index_stats.get("mappings_checksum")

            if expected_checksum and mappings_checksum != expected_checksum:
                logger.error("Index corruption detected: checksum mismatch")
                return False

        logger.info("Index validation passed")
        return True

    except Exception as e:
        logger.error(f"Error validating index: {e}")
        return False


def load_index():
    """Load existing FAISS index and mappings from disk with validation"""
    global faiss_index, file_mappings, index_stats

    # Lazy load FAISS
    if not _lazy_load_faiss():
        logger.error("FAISS not available")
        return False

    try:
        # Validate before loading
        if not validate_index():
            logger.warning("Index validation failed, attempting recovery")
            return load_index_with_recovery()

        # Load mappings
        if MAPPINGS_PATH.exists():
            with open(MAPPINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_mappings = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(file_mappings)} file mappings")

        # Load stats (already loaded in validation)
        if not index_stats.get("total_vectors"):
            if STATS_PATH.exists():
                with open(STATS_PATH, "r", encoding="utf-8") as f:
                    index_stats.update(json.load(f))

        # Load FAISS index
        if FAISS_INDEX_PATH.exists() and len(file_mappings) > 0:
            faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
            logger.info(f"Loaded FAISS index with {index_stats.get('total_vectors', 0)} vectors")
            return True

        return False
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        return load_index_with_recovery()


def load_index_with_recovery():
    """Load index with automatic recovery strategies"""
    global faiss_index, file_mappings, index_stats

    logger.info("Attempting index recovery...")

    # Strategy 1: Try to load just mappings (without FAISS index)
    if MAPPINGS_PATH.exists() and MAPPINGS_PATH.stat().st_size > 0:
        try:
            with open(MAPPINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_mappings = {int(k): v for k, v in data.items()}
            logger.info(f"Recovered {len(file_mappings)} file mappings, FAISS index needs rebuild")
            # Return partial success - mappings loaded but index needs rebuild
            return False
        except Exception as e:
            logger.warning(f"Could not recover mappings: {e}")

    # Strategy 2: Try backup
    backup_path = INDEX_DIR / "backups" / "latest"
    if backup_path.exists():
        try:
            # Copy backup to main location
            for backup_file in backup_path.iterdir():
                dest = INDEX_DIR / backup_file.name
                shutil.copy2(backup_file, dest)

            logger.info("Restored from backup, retrying load")
            return load_index()
        except Exception as e:
            logger.warning(f"Backup recovery failed: {e}")

    # Strategy 3: Full rebuild required
    logger.warning("Index unrecoverable, full rebuild required")
    faiss_index = None
    file_mappings = {}
    index_stats = {
        "total_vectors": 0,
        "files_indexed": 0,
        "functions_indexed": 0,
        "classes_indexed": 0,
        "last_indexed": None,
        "index_size_bytes": 0,
    }
    return False


def save_index():
    """Save FAISS index and mappings to disk with backup and checksums"""
    global faiss_index, file_mappings, index_stats

    try:
        # Create backup before saving
        backup_dir = INDEX_DIR / "backups" / "latest"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup existing files if they exist
        if MAPPINGS_PATH.exists():
            shutil.copy2(MAPPINGS_PATH, backup_dir / "file_mappings.json")
        if STATS_PATH.exists():
            shutil.copy2(STATS_PATH, backup_dir / "index_stats.json")
        if FAISS_INDEX_PATH.exists():
            shutil.copy2(FAISS_INDEX_PATH, backup_dir / "faiss.index")

        # Save mappings
        with open(MAPPINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in file_mappings.items()}, f, indent=2)

        # Calculate mappings checksum
        mappings_checksum = hashlib.md5(MAPPINGS_PATH.read_bytes()).hexdigest()

        # Update and save stats with version and checksum
        if FAISS_INDEX_PATH.exists():
            index_stats["index_size_bytes"] = FAISS_INDEX_PATH.stat().st_size

        index_stats["index_version"] = "2.0.0"
        index_stats["mappings_checksum"] = mappings_checksum
        index_stats["last_saved"] = datetime.now().isoformat()

        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(index_stats, f, indent=2)

        logger.info("Saved index, mappings, and backup to disk")
        return True
    except Exception as e:
        logger.error(f"Error saving index: {e}")
        return False


def extract_python_chunks(file_path: str, content: str) -> List[CodeChunk]:
    """Extract functions and classes from Python code using AST"""
    chunks = []

    try:
        tree = ast.parse(content)
        lines = content.split("\n")

        current_id = len(file_mappings)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Extract function
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                func_content = "\n".join(lines[start_line - 1 : end_line])

                # Get docstring if exists
                docstring = ast.get_docstring(node)

                chunks.append(
                    CodeChunk(
                        id=current_id,
                        file_path=file_path,
                        chunk_type="function",
                        name=node.name,
                        content=func_content,
                        start_line=start_line,
                        end_line=end_line,
                        docstring=docstring,
                    )
                )
                current_id += 1

            elif isinstance(node, ast.ClassDef):
                # Extract class
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                class_content = "\n".join(lines[start_line - 1 : end_line])

                # Get docstring if exists
                docstring = ast.get_docstring(node)

                chunks.append(
                    CodeChunk(
                        id=current_id,
                        file_path=file_path,
                        chunk_type="class",
                        name=node.name,
                        content=class_content,
                        start_line=start_line,
                        end_line=end_line,
                        docstring=docstring,
                    )
                )
                current_id += 1

        # If no chunks extracted, add the whole file as a chunk
        if not chunks:
            chunks.append(
                CodeChunk(
                    id=current_id,
                    file_path=file_path,
                    chunk_type="file",
                    name=Path(file_path).name,
                    content=content[:5000],  # Limit file-level content
                    start_line=1,
                    end_line=len(lines),
                )
            )

    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {file_path}: {e}")
        # Add as file chunk if parsing fails
        chunks.append(
            CodeChunk(
                id=len(file_mappings),
                file_path=file_path,
                chunk_type="file",
                name=Path(file_path).name,
                content=content[:5000],
                start_line=1,
                end_line=len(content.split("\n")),
            )
        )
    except Exception as e:
        logger.error(f"Error extracting chunks from {file_path}: {e}")

    return chunks


def extract_generic_chunks(file_path: str, content: str) -> List[CodeChunk]:
    """Extract chunks from non-Python files using simple text chunking"""
    chunks = []
    lines = content.split("\n")

    # For non-Python files, chunk by logical sections or size
    chunk_size = 50  # lines per chunk

    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i : i + chunk_size]
        chunk_content = "\n".join(chunk_lines)

        if chunk_content.strip():  # Skip empty chunks
            chunks.append(
                CodeChunk(
                    id=len(file_mappings) + len(chunks),
                    file_path=file_path,
                    chunk_type="file",
                    name=f"{Path(file_path).name}:{i+1}-{min(i+chunk_size, len(lines))}",
                    content=chunk_content,
                    start_line=i + 1,
                    end_line=min(i + chunk_size, len(lines)),
                )
            )

    return chunks


def should_exclude_path(path: Path) -> bool:
    """Check if a path should be excluded from indexing"""
    path_str = str(path)

    # Check directory exclusions
    for exclude in EXCLUDE_DIRS:
        if exclude in path_str:
            return True

    # Check file exclusions
    if path.suffix in EXCLUDE_FILES:
        return True

    return False


@mcp.tool()
async def build_index(
    root_path: str,
    file_extensions: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Build or rebuild the semantic code index with true incremental support.

    Args:
        root_path: Root directory to scan for code files
        file_extensions: List of file extensions to include (e.g., [".py", ".js"])
        exclude_patterns: Additional patterns to exclude
        rebuild: If True, completely rebuild index; if False, update incrementally

    Returns:
        Dictionary with build status and statistics

    Example:
        result = await build_index("./src", file_extensions=[".py"])
    """
    global faiss_index, file_mappings, index_stats

    # Acquire write lock for index updates
    async with index_manager.write_lock():
        # Lazy load dependencies
        if not _lazy_load_embeddings() or not _lazy_load_faiss():
            return {
                "success": False,
                "error": "Required libraries not installed. Run: pip install sentence-transformers faiss-cpu",
            }

        try:
            root = Path(root_path).resolve()
            if not root.exists():
                return {"success": False, "error": f"Path not found: {root_path}"}

            # Initialize embedding model
            if embedding_model is None:
                if not init_embedding_model():
                    return {"success": False, "error": "Failed to initialize embedding model"}

            # Reset if rebuilding
            if rebuild:
                file_mappings = {}
                faiss_index = None
                logger.info("Full rebuild requested, clearing existing index")
            else:
                # Incremental mode - load existing index if available
                if not faiss_index and FAISS_INDEX_PATH.exists():
                    load_index()
                logger.info("Incremental update mode")

            # Determine extensions to scan
            extensions = set(file_extensions) if file_extensions else CODE_EXTENSIONS
            exclude_pats = set(exclude_patterns) if exclude_patterns else set()

            # Scan for code files
            code_files = []
            for ext in extensions:
                for file_path in root.rglob(f"*{ext}"):
                    if not should_exclude_path(file_path):
                        # Check additional exclude patterns
                        if not any(re.search(pat, str(file_path)) for pat in exclude_pats):
                            code_files.append(file_path)

            logger.info(f"Found {len(code_files)} code files to scan")

            # Incremental indexing: Track existing file hashes
            indexed_files = {}
            if not rebuild:
                for chunk_id, mapping in file_mappings.items():
                    file_path = mapping.get("file_path")
                    file_hash = mapping.get("file_hash")
                    if file_path and file_hash:
                        indexed_files[file_path] = {
                            "hash": file_hash,
                            "chunk_ids": indexed_files.get(file_path, {}).get("chunk_ids", [])
                            + [chunk_id],
                        }

            # Extract chunks - only from new/changed files
            all_chunks: List[CodeChunk] = []
            files_to_remove = set(indexed_files.keys())
            changed_files = 0
            new_files = 0

            for file_path in code_files:
                try:
                    file_path_str = str(file_path)

                    # Calculate file hash for change detection
                    file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()

                    # Check if file is in index
                    if file_path_str in indexed_files:
                        files_to_remove.discard(file_path_str)

                        # Check if file changed
                        if indexed_files[file_path_str]["hash"] == file_hash:
                            # File unchanged - skip
                            continue
                        else:
                            # File changed - will re-index
                            changed_files += 1
                            # Remove old chunks from mappings
                            for old_chunk_id in indexed_files[file_path_str]["chunk_ids"]:
                                if old_chunk_id in file_mappings:
                                    del file_mappings[old_chunk_id]
                    else:
                        # New file
                        new_files += 1

                    # Read and extract chunks
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    if file_path.suffix == ".py":
                        chunks = extract_python_chunks(file_path_str, content)
                    else:
                        chunks = extract_generic_chunks(file_path_str, content)

                    # Add file hash to each chunk mapping
                    for chunk in chunks:
                        all_chunks.append(chunk)

                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")

            # Remove chunks for deleted files
            if not rebuild and files_to_remove:
                for removed_file in files_to_remove:
                    if removed_file in indexed_files:
                        for chunk_id in indexed_files[removed_file]["chunk_ids"]:
                            if chunk_id in file_mappings:
                                del file_mappings[chunk_id]
                logger.info(f"Removed {len(files_to_remove)} deleted files from index")

            logger.info(
                f"Extracted {len(all_chunks)} code chunks from {new_files} new and {changed_files} changed files"
            )

            # Generate embeddings and collect them
            embeddings_list = []
            functions_count = 0
            classes_count = 0
            valid_chunks = []

            for chunk in all_chunks:
                # Create embedding text: combine name, content, and docstring
                embed_text = f"{chunk.name}\n{chunk.content}"
                if chunk.docstring:
                    embed_text = f"{chunk.docstring}\n{embed_text}"

                embedding = create_embedding(embed_text)

                if embedding is not None:
                    embeddings_list.append(embedding)
                    valid_chunks.append(chunk)

                    # Calculate file hash for the chunk's file
                    try:
                        chunk_file_path = Path(chunk.file_path)
                        if chunk_file_path.exists():
                            file_hash = hashlib.md5(chunk_file_path.read_bytes()).hexdigest()
                        else:
                            file_hash = None
                    except Exception:
                        file_hash = None

                    # Store mapping with file hash
                    file_mappings[chunk.id] = {
                        "file_path": chunk.file_path,
                        "chunk_type": chunk.chunk_type,
                        "name": chunk.name,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "docstring": chunk.docstring,
                        "content_preview": (
                            chunk.content[:200] + "..."
                            if len(chunk.content) > 200
                            else chunk.content
                        ),
                        "file_hash": file_hash,
                    }

                    if chunk.chunk_type == "function":
                        functions_count += 1
                    elif chunk.chunk_type == "class":
                        classes_count += 1

            # For incremental mode, rebuild entire FAISS index with all vectors
            if not rebuild and faiss_index is not None and embeddings_list:
                logger.info("Rebuilding FAISS index with updated vectors")
                # Collect all existing embeddings (this is a limitation of FAISS - no remove operation)
                # In production, consider using a more sophisticated approach
                all_embeddings = []
                for chunk_id in sorted(file_mappings.keys()):
                    if chunk_id < len(embeddings_list):
                        all_embeddings.append(embeddings_list[chunk_id])

                if all_embeddings:
                    embeddings_array = np.vstack(all_embeddings).astype("float32")
                    faiss_index = faiss.IndexFlatIP(EMBEDDING_DIMENSIONS)
                    faiss.normalize_L2(embeddings_array)
                    faiss_index.add(embeddings_array)
                    faiss.write_index(faiss_index, str(FAISS_INDEX_PATH))
            elif embeddings_list:
                # Full rebuild or first build
                embeddings_array = np.vstack(embeddings_list).astype("float32")
                faiss_index = faiss.IndexFlatIP(EMBEDDING_DIMENSIONS)
                faiss.normalize_L2(embeddings_array)
                faiss_index.add(embeddings_array)
                faiss.write_index(faiss_index, str(FAISS_INDEX_PATH))

            # Update stats
            index_stats.update(
                {
                    "total_vectors": len(file_mappings),
                    "files_indexed": len(code_files),
                    "functions_indexed": functions_count,
                    "classes_indexed": classes_count,
                    "last_indexed": datetime.now().isoformat(),
                    "index_size_bytes": (
                        FAISS_INDEX_PATH.stat().st_size if FAISS_INDEX_PATH.exists() else 0
                    ),
                    "root_path": str(root),
                    "incremental_stats": {
                        "new_files": new_files,
                        "changed_files": changed_files,
                        "removed_files": len(files_to_remove) if not rebuild else 0,
                    },
                }
            )

            # Save everything
            save_index()

            return {
                "success": True,
                "message": f"Index {'rebuilt' if rebuild else 'updated'} successfully",
                "stats": index_stats,
            }

        except Exception as e:
            logger.error(f"Error building index: {e}")
            return {"success": False, "error": str(e)}


@mcp.tool()
async def semantic_search(
    query: str,
    top_k: int = 5,
    file_filter: Optional[str] = None,
    chunk_type_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search the codebase using natural language queries.

    Args:
        query: Natural language search query (e.g., "How does authentication work?")
        top_k: Number of results to return (default: 5)
        file_filter: Filter by file path pattern (e.g., "*.py" or "src/")
        chunk_type_filter: Filter by chunk type ('function', 'class', 'file')

    Returns:
        Dictionary with search results including file paths, code snippets, and scores

    Example:
        result = await semantic_search("error handling with try-except", top_k=10)
    """
    global faiss_index, file_mappings

    # Acquire read lock for concurrent searches
    async with index_manager.read_lock():
        if faiss_index is None:
            # Try to load existing index
            if not load_index():
                return {
                    "success": False,
                    "error": "Index not built. Run build_index first.",
                    "results": [],
                }

        if not file_mappings:
            return {
                "success": False,
                "error": "No indexed content. Run build_index first.",
                "results": [],
            }

        try:
            # Create query embedding
            query_embedding = create_embedding(query)
            if query_embedding is None:
                return {
                    "success": False,
                    "error": "Failed to create query embedding",
                    "results": [],
                }

            # Normalize for cosine similarity
            query_vec = query_embedding.reshape(1, -1).astype("float32")
            faiss.normalize_L2(query_vec)

            # Search FAISS index
            distances, indices = faiss_index.search(
                query_vec, top_k * 2
            )  # Get more to allow filtering

            # Build results
            results = []
            for idx, score in zip(indices[0], distances[0]):
                if idx < 0 or idx not in file_mappings:
                    continue

                mapping = file_mappings[idx]

                # Apply filters
                if file_filter:
                    if not re.search(file_filter, mapping["file_path"]):
                        continue

                if chunk_type_filter:
                    if mapping["chunk_type"] != chunk_type_filter:
                        continue

                # Score is already cosine similarity (inner product of normalized vectors)
                similarity = float(score)

                results.append(
                    {
                        "file_path": mapping["file_path"],
                        "chunk_type": mapping["chunk_type"],
                        "name": mapping["name"],
                        "start_line": mapping["start_line"],
                        "end_line": mapping["end_line"],
                        "content_preview": mapping["content_preview"],
                        "docstring": mapping.get("docstring"),
                        "similarity_score": round(similarity, 4),
                    }
                )

                if len(results) >= top_k:
                    break

            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return {"success": False, "error": str(e), "results": []}


@mcp.tool()
async def find_similar_code(
    code_snippet: str, top_k: int = 5, exclude_self: bool = True
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
        result = await find_similar_code("async def initialize_tools(self):")
    """
    global faiss_index, file_mappings

    if faiss_index is None:
        if not load_index():
            return {"success": False, "error": "Index not built", "results": []}

    try:
        # Create embedding for the code snippet
        embedding = create_embedding(code_snippet)
        if embedding is None:
            return {"success": False, "error": "Failed to create embedding", "results": []}

        # Normalize for cosine similarity
        query_vec = embedding.reshape(1, -1).astype("float32")
        faiss.normalize_L2(query_vec)

        # Search FAISS index
        distances, indices = faiss_index.search(query_vec, top_k + (5 if exclude_self else 0))

        results = []
        snippet_hash = hashlib.md5(code_snippet.encode()).hexdigest()

        for idx, score in zip(indices[0], distances[0]):
            if idx < 0 or idx not in file_mappings:
                continue

            mapping = file_mappings[idx]

            # Skip if this is the same code (for exclude_self)
            if exclude_self:
                content_hash = hashlib.md5(mapping["content_preview"].encode()).hexdigest()
                if content_hash == snippet_hash:
                    continue

            similarity = float(score)

            results.append(
                {
                    "file_path": mapping["file_path"],
                    "chunk_type": mapping["chunk_type"],
                    "name": mapping["name"],
                    "start_line": mapping["start_line"],
                    "end_line": mapping["end_line"],
                    "content_preview": mapping["content_preview"],
                    "similarity_score": round(similarity, 4),
                }
            )

            if len(results) >= top_k:
                break

        return {
            "success": True,
            "similar_to": code_snippet[:100] + "..." if len(code_snippet) > 100 else code_snippet,
            "results_count": len(results),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error finding similar code: {e}")
        return {"success": False, "error": str(e), "results": []}


@mcp.tool()
async def get_code_context(
    file_path: str, line_number: int, context_lines: int = 10
) -> Dict[str, Any]:
    """
    Get code context around a specific line in a file.

    Args:
        file_path: Path to the code file
        line_number: Target line number
        context_lines: Number of lines before and after to include

    Returns:
        Dictionary with code context and metadata

    Example:
        result = await get_code_context("./src/main.py", 42, context_lines=15)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        total_lines = len(lines)
        start_line = max(1, line_number - context_lines)
        end_line = min(total_lines, line_number + context_lines)

        context = "\n".join(lines[start_line - 1 : end_line])

        return {
            "success": True,
            "file_path": str(path.resolve()),
            "target_line": line_number,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "context": context,
        }

    except Exception as e:
        logger.error(f"Error getting code context: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_index_stats() -> Dict[str, Any]:
    """
    Get statistics about the current index.

    Returns:
        Dictionary with index statistics including vector count, files indexed, etc.

    Example:
        stats = await get_index_stats()
    """
    global index_stats, file_mappings

    # Load stats if not in memory
    if STATS_PATH.exists():
        try:
            with open(STATS_PATH, "r") as f:
                index_stats.update(json.load(f))
        except Exception:
            pass

    return {
        "success": True,
        "stats": {
            **index_stats,
            "index_loaded": faiss_index is not None,
            "mappings_in_memory": len(file_mappings),
        },
    }


@mcp.tool()
async def find_usages(symbol_name: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Find all usages of a symbol (function, class, variable) across the codebase.

    Args:
        symbol_name: Name of the symbol to find (e.g., "initialize_tools")
        top_k: Maximum number of results

    Returns:
        Dictionary with usage locations

    Example:
        result = await find_usages("MCPToolManager")
    """
    # This uses semantic search + text matching for better results
    search_result = await semantic_search(
        query=f"uses {symbol_name} function call import", top_k=top_k * 2
    )

    if not search_result.get("success"):
        return search_result

    # Filter results to those containing the symbol name
    filtered_results = []
    for result in search_result.get("results", []):
        if symbol_name.lower() in result.get("content_preview", "").lower():
            filtered_results.append(result)
            if len(filtered_results) >= top_k:
                break

    return {
        "success": True,
        "symbol": symbol_name,
        "results_count": len(filtered_results),
        "results": filtered_results,
    }


@mcp.tool()
async def health() -> Dict[str, Any]:
    """
    Health check endpoint for the CodeBaseBuddy server.

    Returns:
        Dictionary with server health status
    """
    # Check availability (but don't force load if not already loaded)
    embeddings_ok = EMBEDDINGS_AVAILABLE or (SentenceTransformer is not None)
    faiss_ok = FAISS_AVAILABLE or (faiss is not None)

    return {
        "status": "healthy",
        "server": "CodeBaseBuddy",
        "embeddings_available": embeddings_ok,
        "faiss_available": faiss_ok,
        "index_loaded": faiss_index is not None,
        "vectors_in_memory": len(file_mappings),
        "timestamp": datetime.now().isoformat(),
    }


def validate_config():
    """Validate configuration at startup"""
    errors = []
    warnings = []

    # Validate embedding dimensions
    if not isinstance(EMBEDDING_DIMENSIONS, int) or EMBEDDING_DIMENSIONS <= 0:
        errors.append(f"Invalid embedding dimensions: {EMBEDDING_DIMENSIONS}")

    # Validate embedding model name
    if not isinstance(EMBEDDING_MODEL_NAME, str) or not EMBEDDING_MODEL_NAME.strip():
        errors.append(f"Invalid embedding model name: {EMBEDDING_MODEL_NAME}")

    # Check if embedding model can be loaded
    try:
        if _lazy_load_embeddings():
            test_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            actual_dims = test_model.get_sentence_embedding_dimension()
            if actual_dims != EMBEDDING_DIMENSIONS:
                errors.append(
                    f"Embedding dimension mismatch: config has {EMBEDDING_DIMENSIONS}, "
                    f"model {EMBEDDING_MODEL_NAME} has {actual_dims}"
                )
            del test_model
        else:
            warnings.append(
                "sentence-transformers not installed, semantic search will be unavailable"
            )
    except Exception as e:
        warnings.append(f"Could not validate embedding model: {e}")

    # Check if FAISS is available
    if not _lazy_load_faiss():
        warnings.append("FAISS not installed, vector search will be unavailable")

    # Validate index path is writable
    try:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        test_file = INDEX_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        errors.append(f"Index directory not writable: {INDEX_DIR} - {e}")

    # Validate file extensions
    if not isinstance(CODE_EXTENSIONS, set) or len(CODE_EXTENSIONS) == 0:
        warnings.append("No file extensions configured for indexing")

    # Validate port number
    port = CONFIG.get("port", 3004)
    if not isinstance(port, int) or port < 1024 or port > 65535:
        errors.append(f"Invalid port number: {port}")

    # Log results
    if errors:
        error_msg = "\n".join(errors)
        logger.error(f"Configuration validation failed:\n{error_msg}")
        raise ValueError(f"Configuration errors:\n{error_msg}")

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    logger.info("Configuration validated successfully")
    return True


# Initialize on module load
def initialize():
    """Initialize the server with configuration validation"""
    global faiss_index

    logger.info("Initializing CodeBaseBuddy server...")

    # Validate configuration first
    try:
        validate_config()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.warning("Server starting with degraded functionality")

    # Try to load existing index (doesn't require embedding model)
    if load_index():
        logger.info("Loaded existing index from disk")
    else:
        logger.info("No existing index found. Run build_index to create one.")

    # Don't pre-load embedding model - it will be loaded on first use
    # This makes server startup much faster
    logger.info("CodeBaseBuddy server initialized (embedding model will load on first use)")


# Initialize when module loads
initialize()


# Initialize when module loads
initialize()


if __name__ == "__main__":
    port = CONFIG.get("port", 3004)
    host = CONFIG.get("host", "0.0.0.0")
    logger.info(f"Starting CodeBaseBuddy MCP server on http://{host}:{port}...")
    print(f"Index directory: {INDEX_DIR}")
    print(f"Embedding dimensions: {EMBEDDING_DIMENSIONS}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME}")
    print(f"Code extensions: {len(CODE_EXTENSIONS)} types")
    mcp.run(transport="sse", port=port, host=host)
