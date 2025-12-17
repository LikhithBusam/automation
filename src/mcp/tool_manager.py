"""
MCP Tool Manager
Central orchestrator for all MCP server integrations

Features:
1. Initialize all tool wrappers (GitHub, Filesystem, Memory, Slack)
2. Load configuration from config.yaml
3. Tool discovery and registration
4. Health check for all servers
5. Unified error handling and fallback mechanisms
6. Statistics aggregation across all tools
7. Tool access control based on agent permissions
8. Connection pooling for MCP servers
"""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import logging
import asyncio
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

from src.mcp.base_tool import BaseMCPTool, MCPToolError


# =============================================================================
# Connection Pool
# =============================================================================

@dataclass
class ConnectionPoolEntry:
    """Entry in the connection pool"""
    tool: BaseMCPTool
    created_at: float
    last_used: float
    in_use: bool = False
    use_count: int = 0


class MCPConnectionPool:
    """
    Connection pool for MCP servers.
    
    Maintains persistent connections to reduce overhead
    and improve performance.
    """
    
    def __init__(self, max_connections_per_server: int = 5):
        self.max_connections = max_connections_per_server
        self._pools: Dict[str, List[ConnectionPoolEntry]] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("mcp.pool")
    
    async def get_connection(self, tool_name: str, tool_factory) -> BaseMCPTool:
        """Get a connection from the pool or create a new one"""
        async with self._lock:
            if tool_name not in self._pools:
                self._pools[tool_name] = []
            
            pool = self._pools[tool_name]
            
            # Find available connection
            for entry in pool:
                if not entry.in_use:
                    entry.in_use = True
                    entry.last_used = datetime.now().timestamp()
                    entry.use_count += 1
                    return entry.tool
            
            # Create new connection if under limit
            if len(pool) < self.max_connections:
                tool = await tool_factory()
                entry = ConnectionPoolEntry(
                    tool=tool,
                    created_at=datetime.now().timestamp(),
                    last_used=datetime.now().timestamp(),
                    in_use=True,
                    use_count=1
                )
                pool.append(entry)
                self.logger.debug(f"Created new connection for {tool_name}, pool size: {len(pool)}")
                return tool
            
            # Wait for available connection
            self.logger.warning(f"Connection pool exhausted for {tool_name}, waiting...")
            
        # Wait and retry
        await asyncio.sleep(0.1)
        return await self.get_connection(tool_name, tool_factory)
    
    async def release_connection(self, tool_name: str, tool: BaseMCPTool):
        """Release a connection back to the pool"""
        async with self._lock:
            if tool_name in self._pools:
                for entry in self._pools[tool_name]:
                    if entry.tool is tool:
                        entry.in_use = False
                        entry.last_used = datetime.now().timestamp()
                        return
    
    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            for tool_name, pool in self._pools.items():
                for entry in pool:
                    try:
                        await entry.tool.disconnect()
                    except Exception as e:
                        self.logger.error(f"Error closing connection for {tool_name}: {e}")
            self._pools.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = {}
        for tool_name, pool in self._pools.items():
            in_use = sum(1 for e in pool if e.in_use)
            stats[tool_name] = {
                "total_connections": len(pool),
                "in_use": in_use,
                "available": len(pool) - in_use,
                "total_uses": sum(e.use_count for e in pool)
            }
        return stats


# =============================================================================
# Agent Permissions
# =============================================================================

@dataclass
class AgentPermissions:
    """Permissions for an agent"""
    allowed_tools: Set[str] = field(default_factory=set)
    allowed_operations: Dict[str, Set[str]] = field(default_factory=dict)
    rate_limit_override: Optional[int] = None
    
    def can_access_tool(self, tool_name: str) -> bool:
        """Check if agent can access a tool"""
        return "*" in self.allowed_tools or tool_name in self.allowed_tools
    
    def can_execute_operation(self, tool_name: str, operation: str) -> bool:
        """Check if agent can execute an operation on a tool"""
        if not self.can_access_tool(tool_name):
            return False
        
        if tool_name not in self.allowed_operations:
            return True  # No operation restrictions
        
        ops = self.allowed_operations[tool_name]
        return "*" in ops or operation in ops


# Default agent-to-tool mappings with operations
AGENT_PERMISSIONS: Dict[str, AgentPermissions] = {
    "code_analyzer": AgentPermissions(
        allowed_tools={"github", "filesystem", "memory", "codebasebuddy"},
        allowed_operations={
            "github": {"get_pr", "review_pr", "search_code", "list_prs", "get_commit"},
            "filesystem": {"read_file", "list_directory", "search_content", "get_code_files", "analyze_structure"},
            "memory": {"store", "search", "retrieve"},
            "codebasebuddy": {"semantic_search", "find_similar_code", "get_code_context", "find_usages"}
        }
    ),
    "documentation": AgentPermissions(
        allowed_tools={"filesystem", "memory", "codebasebuddy"},
        allowed_operations={
            "filesystem": {"read_file", "write_file", "list_directory", "analyze_structure"},
            "memory": {"store", "search", "retrieve"},
            "codebasebuddy": {"semantic_search", "get_code_context"}
        }
    ),
    "deployment": AgentPermissions(
        allowed_tools={"github", "slack", "memory"},
        allowed_operations={
            "github": {"trigger_deployment", "rollback_deployment", "get_commit", "create_pr"},
            "slack": {"send_message", "send_notification"},
            "memory": {"store", "search", "retrieve"}
        }
    ),
    "research": AgentPermissions(
        allowed_tools={"memory", "codebasebuddy"},
        allowed_operations={
            "memory": {"*"},  # Full access to memory
            "codebasebuddy": {"semantic_search", "find_similar_code", "find_usages"}
        }
    ),
    "security_auditor": AgentPermissions(
        allowed_tools={"github", "filesystem", "memory", "codebasebuddy"},
        allowed_operations={
            "github": {"get_pr", "search_code", "get_commit"},
            "filesystem": {"read_file", "list_directory", "search_content"},
            "memory": {"store", "search", "retrieve"},
            "codebasebuddy": {"semantic_search", "find_similar_code", "find_usages", "get_code_context"}
        }
    ),
    "project_manager": AgentPermissions(
        allowed_tools={"*"},  # Full tool access
        allowed_operations={}  # No operation restrictions
    )
}


# =============================================================================
# Tool Registry
# =============================================================================

class ToolRegistry:
    """Registry for dynamic tool discovery and registration"""
    
    def __init__(self):
        self._tools: Dict[str, type] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("mcp.registry")
    
    def register(
        self,
        name: str,
        tool_class: type,
        metadata: Dict[str, Any] = None
    ):
        """Register a tool class"""
        self._tools[name] = tool_class
        self._tool_metadata[name] = metadata or {}
        self.logger.info(f"Registered tool: {name}")
    
    def unregister(self, name: str):
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            del self._tool_metadata[name]
            self.logger.info(f"Unregistered tool: {name}")
    
    def get_tool_class(self, name: str) -> Optional[type]:
        """Get a tool class by name"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, type]:
        """Get all registered tools"""
        return self._tools.copy()
    
    def get_tool_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for a tool"""
        return self._tool_metadata.get(name, {})
    
    def discover_tools(self):
        """Auto-discover tool classes"""
        # Import tool classes
        from src.mcp.github_tool import GitHubMCPTool
        from src.mcp.filesystem_tool import FilesystemMCPTool
        from src.mcp.memory_tool import MemoryMCPTool
        from src.mcp.slack_tool import SlackMCPTool
        from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool
        
        # Register discovered tools
        self.register("github", GitHubMCPTool, {
            "description": "GitHub API operations",
            "server_port": 3000,
            "operations": ["create_pr", "get_pr", "review_pr", "create_issue", "search_code"]
        })
        self.register("filesystem", FilesystemMCPTool, {
            "description": "Filesystem operations",
            "server_port": 3001,
            "operations": ["read_file", "write_file", "list_directory", "search_content"]
        })
        self.register("memory", MemoryMCPTool, {
            "description": "Persistent memory operations",
            "server_port": 3002,
            "operations": ["store", "retrieve", "search", "update", "delete"]
        })
        self.register("slack", SlackMCPTool, {
            "description": "Slack notifications",
            "server_port": 3003,
            "operations": ["send_message", "send_notification"]
        })
        self.register("codebasebuddy", CodeBaseBuddyMCPTool, {
            "description": "Semantic code search and understanding",
            "server_port": 3004,
            "operations": ["semantic_search", "find_similar_code", "get_code_context", "build_index", "find_usages"]
        })


# =============================================================================
# MCP Tool Manager
# =============================================================================

class MCPToolManager:
    """
    Central orchestrator for MCP server tools.
    
    Features:
    - Initialize and manage all MCP tools
    - Load configuration from config.yaml
    - Tool discovery and registration
    - Health checks for all servers
    - Unified error handling and fallback mechanisms
    - Statistics aggregation across all tools
    - Tool access control based on agent permissions
    - Connection pooling for MCP servers
    """

    def __init__(self, config: Dict[str, Any] = None, config_path: str = None):
        self.logger = logging.getLogger("mcp.manager")
        
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = self._load_config("config/config.yaml")
        
        # Tool registry for discovery
        self.registry = ToolRegistry()
        self.registry.discover_tools()
        
        # Active tool instances
        self.tools: Dict[str, BaseMCPTool] = {}
        
        # Connection pool
        pool_size = self.config.get("connection_pool_size", 5)
        self.connection_pool = MCPConnectionPool(max_connections_per_server=pool_size)
        
        # Agent permissions
        self.agent_permissions = AGENT_PERMISSIONS.copy()
        self._load_custom_permissions()
        
        # Manager state
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        
        # Error handling
        self._error_handlers: Dict[str, callable] = {}
        self._fallback_order: List[str] = []

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                self.logger.warning(f"Config file not found: {config_path}, using defaults")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def _load_custom_permissions(self):
        """Load custom agent permissions from config"""
        custom_perms = self.config.get("agent_permissions", {})
        for agent_name, perms in custom_perms.items():
            self.agent_permissions[agent_name] = AgentPermissions(
                allowed_tools=set(perms.get("tools", [])),
                allowed_operations={
                    tool: set(ops) for tool, ops in perms.get("operations", {}).items()
                },
                rate_limit_override=perms.get("rate_limit")
            )

    async def initialize(self):
        """Initialize all MCP tools based on configuration"""
        async with self._initialization_lock:
            if self._initialized:
                return
            
            mcp_config = self.config.get("mcp_servers", {})
            
            # Initialize each configured tool
            for tool_name, tool_config in mcp_config.items():
                if not tool_config.get("enabled", False):
                    continue
                
                tool_class = self.registry.get_tool_class(tool_name)
                if not tool_class:
                    self.logger.warning(f"No tool class found for: {tool_name}")
                    continue
                
                try:
                    tool = tool_class(
                        server_url=tool_config.get("server_url", f"http://localhost:{3000 + len(self.tools)}"),
                        config=tool_config
                    )
                    await tool.connect()
                    self.tools[tool_name] = tool
                    self.logger.info(f"[OK] {tool_name.capitalize()} MCP tool initialized")
                except Exception as e:
                    self.logger.error(f"[ERROR] Failed to initialize {tool_name} MCP: {e}")
            
            self._initialized = True
            self.logger.info(f"Initialized {len(self.tools)} MCP tools")

    def _initialize_tools(self):
        """Synchronous initialization (for backward compatibility)"""
        mcp_config = self.config.get("mcp_servers", {})
        
        # GitHub MCP
        if mcp_config.get("github", {}).get("enabled", False):
            try:
                from src.mcp.github_tool import GitHubMCPTool
                self.tools["github"] = GitHubMCPTool(
                    server_url=mcp_config["github"]["server_url"],
                    config=mcp_config["github"]
                )
                self.logger.info("✓ GitHub MCP tool initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize GitHub MCP: {e}")
        
        # Filesystem MCP
        if mcp_config.get("filesystem", {}).get("enabled", False):
            try:
                from src.mcp.filesystem_tool import FilesystemMCPTool
                self.tools["filesystem"] = FilesystemMCPTool(
                    server_url=mcp_config["filesystem"]["server_url"],
                    config=mcp_config["filesystem"]
                )
                self.logger.info("✓ Filesystem MCP tool initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Filesystem MCP: {e}")
        
        # Memory MCP
        if mcp_config.get("memory", {}).get("enabled", False):
            try:
                from src.mcp.memory_tool import MemoryMCPTool
                self.tools["memory"] = MemoryMCPTool(
                    server_url=mcp_config["memory"]["server_url"],
                    config=mcp_config["memory"]
                )
                self.logger.info("✓ Memory MCP tool initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Memory MCP: {e}")
        
        # Slack MCP
        if mcp_config.get("slack", {}).get("enabled", False):
            try:
                from src.mcp.slack_tool import SlackMCPTool
                self.tools["slack"] = SlackMCPTool(
                    server_url=mcp_config["slack"]["server_url"],
                    config=mcp_config["slack"]
                )
                self.logger.info("✓ Slack MCP tool initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Slack MCP: {e}")
        
        self.logger.info(f"Initialized {len(self.tools)} MCP tools")

    # =========================================================================
    # Tool Execution
    # =========================================================================

    async def execute(
        self,
        tool_name: str,
        operation: str,
        params: Dict[str, Any],
        use_cache: bool = True,
        agent_name: str = None
    ) -> Any:
        """
        Execute an operation on a specific MCP tool.
        
        Args:
            tool_name: Name of the tool (github, filesystem, memory, slack)
            operation: Operation to execute
            params: Operation parameters
            use_cache: Whether to use caching
            agent_name: Name of the calling agent (for permission checks)
            
        Returns:
            Operation result
            
        Raises:
            ValueError: If tool not found
            PermissionError: If agent lacks permission
        """
        # Check permissions if agent specified
        if agent_name:
            perms = self.agent_permissions.get(agent_name)
            if perms and not perms.can_execute_operation(tool_name, operation):
                raise PermissionError(
                    f"Agent '{agent_name}' not authorized for {tool_name}.{operation}"
                )
        
        # Check tool availability
        if tool_name not in self.tools:
            available = list(self.tools.keys())
            raise ValueError(
                f"Tool '{tool_name}' not found. Available tools: {available}"
            )
        
        tool = self.tools[tool_name]
        
        try:
            return await tool.execute(operation, params, use_cache)
        except MCPToolError as e:
            # Try unified error handling
            handled = await self._handle_error(tool_name, operation, params, e)
            if handled is not None:
                return handled
            raise

    async def _handle_error(
        self,
        tool_name: str,
        operation: str,
        params: Dict[str, Any],
        error: Exception
    ) -> Optional[Any]:
        """Unified error handling with fallback mechanisms"""
        # Check for custom error handler
        handler_key = f"{tool_name}.{operation}"
        if handler_key in self._error_handlers:
            try:
                return await self._error_handlers[handler_key](params, error)
            except Exception:
                pass
        
        # Try fallback tools in order
        for fallback_tool in self._fallback_order:
            if fallback_tool in self.tools and fallback_tool != tool_name:
                try:
                    self.logger.info(f"Trying fallback tool: {fallback_tool}")
                    return await self.tools[fallback_tool].execute(operation, params)
                except Exception:
                    continue
        
        return None

    def register_error_handler(
        self,
        tool_name: str,
        operation: str,
        handler: callable
    ):
        """Register custom error handler for tool.operation"""
        self._error_handlers[f"{tool_name}.{operation}"] = handler

    def set_fallback_order(self, tool_names: List[str]):
        """Set the order of fallback tools"""
        self._fallback_order = tool_names

    # =========================================================================
    # CrewAI Integration
    # =========================================================================

    def get_tools_for_agent(self, agent_name: str, tool_names: List[str] = None) -> List[Any]:
        """
        Get CrewAI-compatible tools for an agent.
        
        Args:
            agent_name: Name of the agent
            tool_names: Optional list of specific tools (defaults to agent's allowed tools)
            
        Returns:
            List of CrewAI tool objects
        """
        from src.mcp.crewai_wrapper import MCPToolFactory
        
        # Get agent permissions
        perms = self.agent_permissions.get(agent_name, AgentPermissions(allowed_tools={"*"}))
        
        # Determine which tools to provide
        if tool_names:
            requested_tools = set(tool_names)
        else:
            requested_tools = perms.allowed_tools if "*" not in perms.allowed_tools else set(self.tools.keys())
        
        crewai_tools = []
        factory = MCPToolFactory(self)
        
        for tool_name in requested_tools:
            if tool_name not in self.tools:
                self.logger.warning(f"Tool '{tool_name}' not available for agent '{agent_name}'")
                continue
            
            if not perms.can_access_tool(tool_name):
                self.logger.warning(f"Agent '{agent_name}' not authorized for tool '{tool_name}'")
                continue
            
            # Get operations for this tool
            operations = self._get_tool_operations(tool_name)
            
            # Create CrewAI tools for allowed operations
            for op_name, op_info in operations.items():
                if perms.can_execute_operation(tool_name, op_name):
                    tool = factory.create_tool(
                        tool_name=tool_name,
                        operation=op_name,
                        description=op_info.get("description", ""),
                        params_schema=op_info.get("params", [])
                    )
                    crewai_tools.append(tool)
        
        return crewai_tools

    def _get_tool_operations(self, tool_name: str) -> Dict[str, Dict[str, Any]]:
        """Get available operations for a tool"""
        
        operations = {
            "github": {
                "create_pr": {
                    "description": "Create a pull request on GitHub",
                    "params": ["repo", "title", "head", "base", "body"]
                },
                "get_pr": {
                    "description": "Get pull request details",
                    "params": ["repo", "pr_number"]
                },
                "review_pr": {
                    "description": "Submit a review on a pull request",
                    "params": ["repo", "pr_number", "body", "event"]
                },
                "create_issue": {
                    "description": "Create an issue on GitHub",
                    "params": ["repo", "title", "body", "labels"]
                },
                "search_code": {
                    "description": "Search code across repositories",
                    "params": ["query", "per_page"]
                },
                "list_prs": {
                    "description": "List pull requests in a repository",
                    "params": ["repo", "state", "per_page"]
                },
                "get_commit": {
                    "description": "Get commit details",
                    "params": ["repo", "sha"]
                },
                "trigger_deployment": {
                    "description": "Trigger a deployment workflow",
                    "params": ["repo", "environment", "version", "strategy"]
                },
                "rollback_deployment": {
                    "description": "Rollback a deployment",
                    "params": ["repo", "environment"]
                }
            },
            
            "filesystem": {
                "read_file": {
                    "description": "Read the contents of a file",
                    "params": ["path"]
                },
                "write_file": {
                    "description": "Write content to a file",
                    "params": ["path", "content"]
                },
                "list_directory": {
                    "description": "List directory contents",
                    "params": ["path", "recursive"]
                },
                "search_content": {
                    "description": "Search for text patterns in files",
                    "params": ["path", "pattern", "file_types"]
                },
                "get_code_files": {
                    "description": "Get all code files in a directory",
                    "params": ["path"]
                },
                "analyze_structure": {
                    "description": "Analyze project structure",
                    "params": ["path", "max_depth"]
                }
            },
            
            "memory": {
                "store": {
                    "description": "Store information in persistent memory",
                    "params": ["content", "type", "tags", "metadata"]
                },
                "search": {
                    "description": "Search memories with semantic similarity",
                    "params": ["query", "type", "tags", "limit", "min_relevance"]
                },
                "retrieve": {
                    "description": "Retrieve memories by query",
                    "params": ["query", "limit"]
                },
                "update": {
                    "description": "Update an existing memory",
                    "params": ["id", "content", "tags"]
                },
                "delete": {
                    "description": "Delete a memory",
                    "params": ["id"]
                },
                "prune": {
                    "description": "Prune old or low-value memories",
                    "params": ["max_age_days", "max_count"]
                },
                "get_stats": {
                    "description": "Get memory statistics",
                    "params": []
                }
            },
            
            "slack": {
                "send_message": {
                    "description": "Send a message to Slack",
                    "params": ["channel", "text", "thread_ts"]
                },
                "send_notification": {
                    "description": "Send a formatted notification",
                    "params": ["type", "title", "message", "details", "channel"]
                }
            }
        }
        
        return operations.get(tool_name, {})

    # =========================================================================
    # Health Checks
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all MCP tools.
        
        Returns:
            Health status for each tool
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "tools": {},
            "overall": "healthy"
        }
        
        unhealthy_count = 0
        
        for tool_name, tool in self.tools.items():
            try:
                status = await tool.health_check()
                health_status["tools"][tool_name] = status
                if status.get("status") != "healthy":
                    unhealthy_count += 1
            except Exception as e:
                health_status["tools"][tool_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                unhealthy_count += 1
        
        if unhealthy_count > 0:
            health_status["overall"] = "degraded" if unhealthy_count < len(self.tools) else "unhealthy"
        
        return health_status

    async def health_check_single(self, tool_name: str) -> Dict[str, Any]:
        """Check health of a single tool"""
        if tool_name not in self.tools:
            return {"status": "not_found", "tool": tool_name}
        return await self.tools[tool_name].health_check()

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics for all tools"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "tools": {},
            "aggregated": {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
        }
        
        for tool_name, tool in self.tools.items():
            tool_stats = tool.get_stats()
            stats["tools"][tool_name] = tool_stats
            
            # Aggregate
            stats["aggregated"]["total_calls"] += tool_stats.get("total_calls", 0)
            stats["aggregated"]["successful_calls"] += tool_stats.get("successful_calls", 0)
            stats["aggregated"]["failed_calls"] += tool_stats.get("failed_calls", 0)
            stats["aggregated"]["cache_hits"] += tool_stats.get("cache_hits", 0)
            stats["aggregated"]["cache_misses"] += tool_stats.get("cache_misses", 0)
        
        # Calculate rates
        total = stats["aggregated"]["total_calls"]
        if total > 0:
            stats["aggregated"]["success_rate"] = f"{(stats['aggregated']['successful_calls'] / total * 100):.1f}%"
        
        cache_total = stats["aggregated"]["cache_hits"] + stats["aggregated"]["cache_misses"]
        if cache_total > 0:
            stats["aggregated"]["cache_hit_rate"] = f"{(stats['aggregated']['cache_hits'] / cache_total * 100):.1f}%"
        
        # Add connection pool stats
        stats["connection_pool"] = self.connection_pool.get_stats()
        
        return stats

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for all tools"""
        cache_stats = {}
        
        for tool_name, tool in self.tools.items():
            cache_stats[tool_name] = tool.cache.stats
        
        return cache_stats

    def clear_all_caches(self):
        """Clear caches for all tools"""
        for tool in self.tools.values():
            tool.clear_cache()
        
        self.logger.info("Cleared caches for all tools")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available"""
        return tool_name in self.tools

    def get_tool(self, tool_name: str) -> Optional[BaseMCPTool]:
        """Get a tool instance by name"""
        return self.tools.get(tool_name)

    async def shutdown(self):
        """Shutdown all tools and connections"""
        self.logger.info("Shutting down MCP Tool Manager...")
        
        # Close all tool connections
        for tool_name, tool in self.tools.items():
            try:
                await tool.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting {tool_name}: {e}")
        
        # Close connection pool
        await self.connection_pool.close_all()
        
        self._initialized = False
        self.logger.info("MCP Tool Manager shutdown complete")

    @asynccontextmanager
    async def tool_context(self, tool_name: str):
        """Context manager for tool usage with automatic connection handling"""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            yield tool
        finally:
            pass  # Connection pooling handles cleanup


# Backward compatibility: Agent-to-Tool mapping
AGENT_TOOL_MAPPING = {
    "code_analyzer": ["github", "filesystem", "memory"],
    "documentation": ["filesystem", "memory"],
    "deployment": ["github", "slack", "memory"],
    "research": ["memory"],
    "project_manager": ["github", "filesystem", "memory", "slack"],
}
