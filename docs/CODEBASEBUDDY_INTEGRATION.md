# CodeBaseBuddy Integration

## Overview

CodeBaseBuddy is a semantic code search MCP server that provides intelligent code understanding capabilities using FAISS vector search and sentence-transformers embeddings.

## Features

- **Semantic Code Search**: Query your codebase using natural language
- **Function-Level Indexing**: AST-based parsing for Python functions and classes
- **Similar Code Finding**: Find similar code snippets across the codebase
- **Code Context Retrieval**: Get full context for any file with line ranges
- **Fast Vector Search**: FAISS-powered similarity search (384-dimension embeddings)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoGen Agents                           │
│   (code_analyzer, security_auditor, documentation_agent)    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CodeBaseBuddyMCPTool (Client)                  │
│              src/mcp/codebasebuddy_tool.py                  │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP/SSE
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           CodeBaseBuddy MCP Server (Port 3004)              │
│           mcp_servers/codebasebuddy_server.py               │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐   │
│  │ FAISS Index   │  │ Embeddings    │  │ AST Parser     │   │
│  │ (384-dim)     │  │ (MiniLM-L6-v2)│  │ (Python)       │   │
│  └───────────────┘  └───────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Files Created/Modified

### New Files
- `mcp_servers/codebasebuddy_server.py` - MCP server with semantic search capabilities
- `src/mcp/codebasebuddy_tool.py` - MCP client wrapper for agent integration
- `test_codebasebuddy.py` - Integration test script

### Modified Files
- `config/config.yaml` - Added codebasebuddy server configuration
- `config/function_schemas.yaml` - Added function definitions for CodeBaseBuddy
- `config/autogen_agents.yaml` - Added codebasebuddy tools to relevant agents
- `src/mcp/tool_manager.py` - Registered CodeBaseBuddy tool
- `src/autogen_adapters/function_registry.py` - Added method mappings
- `scripts/start_mcp_servers.py` - Added CodeBaseBuddy to server list

## Usage

### Starting the Server

```bash
python mcp_servers/codebasebuddy_server.py
```

The server runs on port 3004 with SSE transport.

### Building the Index

Before searching, build the index for your codebase:

```python
from mcp_servers.codebasebuddy_server import build_index
import asyncio

result = asyncio.run(build_index("./src", rebuild=True))
print(f"Indexed {result['stats']['files_indexed']} files")
```

### Semantic Search

```python
from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool

tool = CodeBaseBuddyMCPTool()
results = await tool.semantic_search("authentication middleware")
```

### Agent Integration

Agents with CodeBaseBuddy access:
- `code_analyzer` - Uses semantic search for code understanding
- `security_auditor` - Finds security-related code patterns
- `documentation_agent` - Searches for documentation patterns
- `research_agent` - Researches code structure and patterns

## Configuration

```yaml
# config/config.yaml
mcp_servers:
  codebasebuddy:
    server_url: "http://localhost:3004"
    enabled: true
    scan_paths:
      - "./src"
      - "./mcp_servers"
      - "./config"
    embedding_model: "all-MiniLM-L6-v2"
    embedding_dimensions: 384
    chunk_strategy: "function"
```

## Functions Available

| Function | Description |
|----------|-------------|
| `semantic_code_search` | Search code using natural language queries |
| `find_similar_code` | Find similar code snippets to a given sample |
| `get_code_context` | Get file context with line ranges |
| `rebuild_index` | Rebuild the code index |
| `get_index_stats` | Get indexing statistics |

## Dependencies

- `faiss-cpu` - Vector similarity search
- `sentence-transformers` - Text embeddings
- `fastmcp` - MCP server framework

## Testing

Run the integration test:

```bash
python test_codebasebuddy.py
```

All tests should pass with:
- ✅ Module imports
- ✅ Embedding model loading
- ✅ Index building
- ✅ Semantic search
- ✅ Code context retrieval
- ✅ FAISS index operations

## Index Storage

Index files are stored in `data/codebase_index/`:
- `faiss.index` - FAISS vector index
- `file_mappings.json` - Chunk metadata
- `index_stats.json` - Indexing statistics
