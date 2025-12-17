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
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from fastmcp import FastMCP
from typing import List, Optional, Dict, Any
import logging
import json
import asyncio
import ast
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

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
            logging.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
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

import numpy as np


# Initialize FastMCP server
mcp = FastMCP("CodeBaseBuddy - Semantic Code Search")
logger = logging.getLogger("mcp.codebasebuddy")

# Configuration
INDEX_DIR = Path("./data/codebase_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
MAPPINGS_PATH = INDEX_DIR / "file_mappings.json"
STATS_PATH = INDEX_DIR / "index_stats.json"

# Embedding dimensions for all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS = 384

# Code file extensions to index
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".yaml", ".yml", ".json", ".md", ".txt"
}

# Directories to exclude
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules", 
    ".pytest_cache", ".mypy_cache", "dist", "build", ".eggs",
    "*.egg-info", ".tox", ".coverage", "htmlcov"
}

# Files to exclude
EXCLUDE_FILES = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".o", ".a",
    ".class", ".jar"
}


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
    "index_size_bytes": 0
}


def init_embedding_model():
    """Initialize the sentence-transformer embedding model"""
    global embedding_model
    
    # Lazy load dependencies
    if not _lazy_load_embeddings():
        logger.error("sentence-transformers not available")
        return False
    
    try:
        # Use same model as memory_server for consistency
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded sentence-transformers embedding model: all-MiniLM-L6-v2")
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
        return embedding.astype('float32')  # FAISS requires float32
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        return None


def load_index():
    """Load existing FAISS index and mappings from disk"""
    global faiss_index, file_mappings, index_stats
    
    # Lazy load FAISS
    if not _lazy_load_faiss():
        logger.error("FAISS not available")
        return False
    
    try:
        # Load mappings
        if MAPPINGS_PATH.exists():
            with open(MAPPINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                file_mappings = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(file_mappings)} file mappings")
        
        # Load stats
        if STATS_PATH.exists():
            with open(STATS_PATH, 'r', encoding='utf-8') as f:
                index_stats.update(json.load(f))
        
        # Load FAISS index
        if FAISS_INDEX_PATH.exists() and len(file_mappings) > 0:
            faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
            logger.info(f"Loaded FAISS index with {index_stats.get('total_vectors', 0)} vectors")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        return False


def save_index():
    """Save FAISS index and mappings to disk"""
    global faiss_index, file_mappings, index_stats
    
    try:
        # Save mappings
        with open(MAPPINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in file_mappings.items()}, f, indent=2)
        
        # Update and save stats
        if FAISS_INDEX_PATH.exists():
            index_stats["index_size_bytes"] = FAISS_INDEX_PATH.stat().st_size
        
        with open(STATS_PATH, 'w', encoding='utf-8') as f:
            json.dump(index_stats, f, indent=2)
        
        logger.info("Saved index and mappings to disk")
        return True
    except Exception as e:
        logger.error(f"Error saving index: {e}")
        return False


def extract_python_chunks(file_path: str, content: str) -> List[CodeChunk]:
    """Extract functions and classes from Python code using AST"""
    chunks = []
    
    try:
        tree = ast.parse(content)
        lines = content.split('\n')
        
        current_id = len(file_mappings)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Extract function
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                func_content = '\n'.join(lines[start_line-1:end_line])
                
                # Get docstring if exists
                docstring = ast.get_docstring(node)
                
                chunks.append(CodeChunk(
                    id=current_id,
                    file_path=file_path,
                    chunk_type='function',
                    name=node.name,
                    content=func_content,
                    start_line=start_line,
                    end_line=end_line,
                    docstring=docstring
                ))
                current_id += 1
                
            elif isinstance(node, ast.ClassDef):
                # Extract class
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                class_content = '\n'.join(lines[start_line-1:end_line])
                
                # Get docstring if exists
                docstring = ast.get_docstring(node)
                
                chunks.append(CodeChunk(
                    id=current_id,
                    file_path=file_path,
                    chunk_type='class',
                    name=node.name,
                    content=class_content,
                    start_line=start_line,
                    end_line=end_line,
                    docstring=docstring
                ))
                current_id += 1
        
        # If no chunks extracted, add the whole file as a chunk
        if not chunks:
            chunks.append(CodeChunk(
                id=current_id,
                file_path=file_path,
                chunk_type='file',
                name=Path(file_path).name,
                content=content[:5000],  # Limit file-level content
                start_line=1,
                end_line=len(lines)
            ))
    
    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {file_path}: {e}")
        # Add as file chunk if parsing fails
        chunks.append(CodeChunk(
            id=len(file_mappings),
            file_path=file_path,
            chunk_type='file',
            name=Path(file_path).name,
            content=content[:5000],
            start_line=1,
            end_line=len(content.split('\n'))
        ))
    except Exception as e:
        logger.error(f"Error extracting chunks from {file_path}: {e}")
    
    return chunks


def extract_generic_chunks(file_path: str, content: str) -> List[CodeChunk]:
    """Extract chunks from non-Python files using simple text chunking"""
    chunks = []
    lines = content.split('\n')
    
    # For non-Python files, chunk by logical sections or size
    chunk_size = 50  # lines per chunk
    
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i:i+chunk_size]
        chunk_content = '\n'.join(chunk_lines)
        
        if chunk_content.strip():  # Skip empty chunks
            chunks.append(CodeChunk(
                id=len(file_mappings) + len(chunks),
                file_path=file_path,
                chunk_type='file',
                name=f"{Path(file_path).name}:{i+1}-{min(i+chunk_size, len(lines))}",
                content=chunk_content,
                start_line=i+1,
                end_line=min(i+chunk_size, len(lines))
            ))
    
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
    rebuild: bool = False
) -> Dict[str, Any]:
    """
    Build or rebuild the semantic code index.
    
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
    
    # Lazy load dependencies
    if not _lazy_load_embeddings() or not _lazy_load_faiss():
        return {
            "success": False,
            "error": "Required libraries not installed. Run: pip install sentence-transformers faiss-cpu"
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
        
        logger.info(f"Found {len(code_files)} code files to index")
        
        # Extract chunks and create embeddings
        all_chunks: List[CodeChunk] = []
        
        for file_path in code_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if file_path.suffix == '.py':
                    chunks = extract_python_chunks(str(file_path), content)
                else:
                    chunks = extract_generic_chunks(str(file_path), content)
                
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
        
        logger.info(f"Extracted {len(all_chunks)} code chunks")
        
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
                
                # Store mapping
                file_mappings[chunk.id] = {
                    "file_path": chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "docstring": chunk.docstring,
                    "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                }
                
                if chunk.chunk_type == 'function':
                    functions_count += 1
                elif chunk.chunk_type == 'class':
                    classes_count += 1
        
        # Create FAISS index from all embeddings
        if embeddings_list:
            embeddings_array = np.vstack(embeddings_list).astype('float32')
            faiss_index = faiss.IndexFlatIP(EMBEDDING_DIMENSIONS)  # Inner product (cosine similarity with normalized vectors)
            faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
            faiss_index.add(embeddings_array)
            
            # Save the index
            faiss.write_index(faiss_index, str(FAISS_INDEX_PATH))
        
        # Update stats
        index_stats.update({
            "total_vectors": len(file_mappings),
            "files_indexed": len(code_files),
            "functions_indexed": functions_count,
            "classes_indexed": classes_count,
            "last_indexed": datetime.now().isoformat(),
            "index_size_bytes": FAISS_INDEX_PATH.stat().st_size if FAISS_INDEX_PATH.exists() else 0,
            "root_path": str(root)
        })
        
        # Save everything
        save_index()
        
        return {
            "success": True,
            "message": "Index built successfully",
            "stats": index_stats
        }
        
    except Exception as e:
        logger.error(f"Error building index: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def semantic_search(
    query: str,
    top_k: int = 5,
    file_filter: Optional[str] = None,
    chunk_type_filter: Optional[str] = None
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
    
    if faiss_index is None:
        # Try to load existing index
        if not load_index():
            return {
                "success": False,
                "error": "Index not built. Run build_index first.",
                "results": []
            }
    
    if not file_mappings:
        return {
            "success": False,
            "error": "No indexed content. Run build_index first.",
            "results": []
        }
    
    try:
        # Create query embedding
        query_embedding = create_embedding(query)
        if query_embedding is None:
            return {"success": False, "error": "Failed to create query embedding", "results": []}
        
        # Normalize for cosine similarity
        query_vec = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_vec)
        
        # Search FAISS index
        distances, indices = faiss_index.search(query_vec, top_k * 2)  # Get more to allow filtering
        
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
            
            results.append({
                "file_path": mapping["file_path"],
                "chunk_type": mapping["chunk_type"],
                "name": mapping["name"],
                "start_line": mapping["start_line"],
                "end_line": mapping["end_line"],
                "content_preview": mapping["content_preview"],
                "docstring": mapping.get("docstring"),
                "similarity_score": round(similarity, 4)
            })
            
            if len(results) >= top_k:
                break
        
        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {"success": False, "error": str(e), "results": []}


@mcp.tool()
async def find_similar_code(
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
        query_vec = embedding.reshape(1, -1).astype('float32')
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
            
            results.append({
                "file_path": mapping["file_path"],
                "chunk_type": mapping["chunk_type"],
                "name": mapping["name"],
                "start_line": mapping["start_line"],
                "end_line": mapping["end_line"],
                "content_preview": mapping["content_preview"],
                "similarity_score": round(similarity, 4)
            })
            
            if len(results) >= top_k:
                break
        
        return {
            "success": True,
            "similar_to": code_snippet[:100] + "..." if len(code_snippet) > 100 else code_snippet,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error finding similar code: {e}")
        return {"success": False, "error": str(e), "results": []}


@mcp.tool()
async def get_code_context(
    file_path: str,
    line_number: int,
    context_lines: int = 10
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
        
        content = path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        total_lines = len(lines)
        start_line = max(1, line_number - context_lines)
        end_line = min(total_lines, line_number + context_lines)
        
        context = '\n'.join(lines[start_line-1:end_line])
        
        return {
            "success": True,
            "file_path": str(path.resolve()),
            "target_line": line_number,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "context": context
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
            with open(STATS_PATH, 'r') as f:
                index_stats.update(json.load(f))
        except Exception:
            pass
    
    return {
        "success": True,
        "stats": {
            **index_stats,
            "index_loaded": faiss_index is not None,
            "mappings_in_memory": len(file_mappings)
        }
    }


@mcp.tool()
async def find_usages(
    symbol_name: str,
    top_k: int = 10
) -> Dict[str, Any]:
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
        query=f"uses {symbol_name} function call import",
        top_k=top_k * 2
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
        "results": filtered_results
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
        "timestamp": datetime.now().isoformat()
    }


# Initialize on module load
def initialize():
    """Initialize the server - lazy loading for embedding model"""
    global faiss_index
    
    logger.info("Initializing CodeBaseBuddy server...")
    
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


if __name__ == "__main__":
    logger.info("Starting CodeBaseBuddy MCP server on port 3004...")
    mcp.run(transport="sse", port=3004, host="0.0.0.0")
