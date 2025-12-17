"""
MCP Integration Layer
Connects agents with MCP servers

This module provides:
- BaseMCPTool: Abstract base class with retry, caching, rate limiting
- MCPToolManager: Central orchestrator for all MCP tools
- Tool wrappers: GitHub, Filesystem, Memory tools
"""

from src.mcp.base_tool import BaseMCPTool, TokenBucket
from src.mcp.tool_manager import MCPToolManager, MCPConnectionPool
from src.mcp.github_tool import GitHubMCPTool
from src.mcp.filesystem_tool import FilesystemMCPTool
from src.mcp.memory_tool import MemoryMCPTool

__all__ = [
    # Base classes
    "BaseMCPTool",
    "TokenBucket",
    # Manager and pooling
    "MCPToolManager",
    "MCPConnectionPool",
    # Tool implementations
    "GitHubMCPTool",
    "FilesystemMCPTool",
    "MemoryMCPTool",
]
