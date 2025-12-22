# Dynamic Configuration Implementation

## Overview

All MCP servers have been updated to load configuration dynamically from `config/config.yaml` instead of using hardcoded values. This enables:

- **Centralized Configuration**: All settings in one place
- **Environment Variable Support**: Use `${VAR_NAME}` syntax for secrets
- **Easy Customization**: Change ports, paths, limits without code changes
- **Production Ready**: Different configs for dev/staging/prod

## Servers Updated

### 1. Filesystem Server (`mcp_servers/filesystem_server.py`)

**Dynamic Settings:**
- `port` - Server port (default: 3001)
- `host` - Server host (default: 0.0.0.0)
- `allowed_paths` - List of paths users can access
- `blocked_patterns` - Regex patterns to block
- `max_file_size_mb` - Maximum file size limit

**Config Section:**
```yaml
mcp_servers:
  filesystem:
    port: 3001
    host: "0.0.0.0"
    allowed_paths:
      - "./workspace"
      - "./src"
    blocked_patterns:
      - "\\.\\.\/"  # Directory traversal
    max_file_size_mb: 10
```

### 2. GitHub Server (`mcp_servers/github_server.py`)

**Dynamic Settings:**
- `port` - Server port (default: 3000)
- `host` - Server host (default: 0.0.0.0)
- `api_base` - GitHub API base URL
- `auth_token` - GitHub token (supports `${GITHUB_TOKEN}`)
- `rate_limit_minute` - Requests per minute
- `rate_limit_hour` - Requests per hour

**Config Section:**
```yaml
mcp_servers:
  github:
    port: 3000
    host: "0.0.0.0"
    api_base: "https://api.github.com"
    auth_token: "${GITHUB_TOKEN}"
    rate_limit_minute: 60
    rate_limit_hour: 1000
```

### 3. Memory Server (`mcp_servers/memory_server.py`)

**Dynamic Settings:**
- `port` - Server port (default: 3002)
- `host` - Server host (default: 0.0.0.0)
- `sqlite_path` - Database file path
- `embedding_model` - Sentence-transformers model name
- `valid_memory_types` - List of allowed memory types

**Config Section:**
```yaml
mcp_servers:
  memory:
    port: 3002
    host: "0.0.0.0"
    sqlite_path: "./data/memory.db"
    embedding_model: "all-MiniLM-L6-v2"
    valid_memory_types:
      - "pattern"
      - "preference"
      - "solution"
      - "context"
      - "error"
```

### 4. CodeBaseBuddy Server (`mcp_servers/codebasebuddy_server.py`)

**Dynamic Settings:**
- `port` - Server port (default: 3004)
- `host` - Server host (default: 0.0.0.0)
- `index_path` - FAISS index directory
- `embedding_dimensions` - Vector dimensions (384 for all-MiniLM-L6-v2)
- `embedding_model` - Model name
- `file_extensions` - List of file types to index
- `exclude_patterns` - Directories to skip
- `exclude_files` - File extensions to skip
- `scan_paths` - Default paths to scan

**Config Section:**
```yaml
mcp_servers:
  codebasebuddy:
    port: 3004
    host: "0.0.0.0"
    index_path: "./data/codebase_index"
    embedding_dimensions: 384
    embedding_model: "all-MiniLM-L6-v2"
    file_extensions:
      - ".py"
      - ".js"
      - ".ts"
    exclude_patterns:
      - "__pycache__"
      - ".git"
      - "node_modules"
```

## Environment Variable Substitution

Any configuration value can reference environment variables using the `${VAR_NAME}` syntax:

```yaml
auth_token: "${GITHUB_TOKEN}"
api_key: "${OPENROUTER_API_KEY}"
```

The servers will automatically substitute these with the corresponding environment variable values at startup.

## How Configuration Loading Works

Each server has a `load_config()` function that:

1. Reads `config/config.yaml` from the project root
2. Extracts the server-specific section (e.g., `mcp_servers.github`)
3. Substitutes `${VAR_NAME}` patterns with environment variables
4. Merges with default values for any missing settings
5. Returns the final configuration dictionary

```python
def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml with environment variable substitution"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    # ... load and process config ...
    return server_config

CONFIG = load_config()
```

## Fallback Behavior

If `config/config.yaml` is not found or cannot be parsed:
- A warning is logged
- Default hardcoded values are used
- The server continues to function normally

This ensures the servers remain operational even if configuration is missing.

## Testing Configuration

Verify configuration loading:

```python
# Test filesystem server config
from mcp_servers.filesystem_server import CONFIG
print(f"Port: {CONFIG.get('port')}")  # Should print: 3001

# Test github server config
from mcp_servers.github_server import CONFIG
print(f"API Base: {CONFIG.get('api_base')}")  # Should print: https://api.github.com
```

## Migration Notes

If you had custom configurations in the old hardcoded values:

1. Add your settings to `config/config.yaml` under the appropriate server section
2. Use environment variables for sensitive data (tokens, keys)
3. Restart the affected servers for changes to take effect

## Files Modified

- `mcp_servers/filesystem_server.py` - Added `load_config()`, dynamic paths/limits
- `mcp_servers/github_server.py` - Added `load_config()`, dynamic API/rate limits
- `mcp_servers/memory_server.py` - Added `load_config()`, dynamic DB path/types
- `mcp_servers/codebasebuddy_server.py` - Added `load_config()`, dynamic index/extensions
- `config/config.yaml` - Added port/host and enhanced server configurations
