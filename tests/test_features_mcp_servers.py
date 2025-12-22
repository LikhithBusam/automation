"""
Feature Testing for All MCP Servers
Tests each MCP server's specific features and operations
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

from src.mcp.github_tool import GitHubMCPTool
from src.mcp.filesystem_tool import FilesystemMCPTool
from src.mcp.memory_tool import MemoryMCPTool
from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool
from src.exceptions import *


# =============================================================================
# GitHub MCP Server Feature Tests
# =============================================================================

class TestGitHubMCPFeatures:
    """Test all GitHub MCP server features"""

    @pytest.fixture
    def github_tool(self):
        """Create GitHub MCP tool instance"""
        config = {
            "server_url": "http://localhost:3000",
            "auth_token": "test_token_12345",
            "timeout": 30,
            "rate_limit_minute": 60,
            "rate_limit_hour": 1000
        }
        return GitHubMCPTool(server_url=config["server_url"], config=config)

    @pytest.mark.asyncio
    async def test_github_create_pull_request(self, github_tool):
        """Test creating a pull request"""
        params = {
            "owner": "testorg",
            "repo": "testrepo",
            "title": "Test PR",
            "body": "This is a test PR",
            "head": "feature-branch",
            "base": "main"
        }

        # Mock the HTTP request
        with patch.object(github_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "number": 123,
                "state": "open",
                "title": "Test PR"
            }

            result = await github_tool.execute("create_pr", params)

            # Verify request was made
            mock_request.assert_called_once()
            assert result is not None

    @pytest.mark.asyncio
    async def test_github_get_pull_request(self, github_tool):
        """Test getting pull request details"""
        params = {
            "owner": "testorg",
            "repo": "testrepo",
            "pr_number": 123
        }

        with patch.object(github_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "number": 123,
                "state": "open",
                "title": "Test PR",
                "user": {"login": "testuser"}
            }

            result = await github_tool.execute("get_pr", params)

            assert result is not None
            assert result["number"] == 123

    @pytest.mark.asyncio
    async def test_github_create_issue(self, github_tool):
        """Test creating a GitHub issue"""
        params = {
            "owner": "testorg",
            "repo": "testrepo",
            "title": "Bug report",
            "body": "Found a bug",
            "labels": ["bug", "high-priority"]
        }

        with patch.object(github_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "number": 456,
                "state": "open",
                "title": "Bug report"
            }

            result = await github_tool.execute("create_issue", params)

            assert result is not None
            assert result["number"] == 456

    @pytest.mark.asyncio
    async def test_github_search_code(self, github_tool):
        """Test searching code in GitHub"""
        params = {
            "query": "function authenticate",
            "owner": "testorg",
            "repo": "testrepo"
        }

        with patch.object(github_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "total_count": 3,
                "items": [
                    {"name": "auth.py", "path": "src/auth.py"},
                    {"name": "utils.py", "path": "src/utils.py"}
                ]
            }

            result = await github_tool.execute("search_code", params)

            assert result is not None
            assert result["total_count"] == 3

    @pytest.mark.asyncio
    async def test_github_get_file_contents(self, github_tool):
        """Test getting file contents from GitHub"""
        params = {
            "owner": "testorg",
            "repo": "testrepo",
            "path": "README.md",
            "ref": "main"
        }

        with patch.object(github_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "name": "README.md",
                "path": "README.md",
                "content": "IyBUZXN0IFByb2plY3Q=",  # Base64 encoded "# Test Project"
                "encoding": "base64"
            }

            result = await github_tool.execute("get_file_contents", params)

            assert result is not None
            assert result["name"] == "README.md"

    def test_github_rate_limiting(self, github_tool):
        """Test GitHub rate limiting is configured"""
        assert github_tool.config.get("rate_limit_minute") == 60
        assert github_tool.config.get("rate_limit_hour") == 1000

    def test_github_authentication(self, github_tool):
        """Test GitHub authentication token is set"""
        assert github_tool.config.get("auth_token") is not None


# =============================================================================
# Filesystem MCP Server Feature Tests
# =============================================================================

class TestFilesystemMCPFeatures:
    """Test all Filesystem MCP server features"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def filesystem_tool(self, temp_workspace):
        """Create Filesystem MCP tool instance"""
        config = {
            "server_url": "http://localhost:3001",
            "timeout": 10,
            "allowed_paths": [temp_workspace],
            "blocked_patterns": [r"\.\.\/", r"\/etc\/", r"\.ssh\/"],
            "max_file_size_mb": 10
        }
        return FilesystemMCPTool(server_url=config["server_url"], config=config)

    @pytest.mark.asyncio
    async def test_filesystem_read_file(self, filesystem_tool, temp_workspace):
        """Test reading a file"""
        # Create test file
        test_file = Path(temp_workspace) / "test.txt"
        test_file.write_text("Hello, World!")

        params = {"file_path": str(test_file)}

        with patch.object(filesystem_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "content": "Hello, World!",
                "path": str(test_file),
                "size": 13
            }

            result = await filesystem_tool.execute("read_file", params)

            assert result is not None
            assert result["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_filesystem_write_file(self, filesystem_tool, temp_workspace):
        """Test writing a file"""
        test_file = Path(temp_workspace) / "output.txt"

        params = {
            "path": str(test_file),
            "content": "Test content"
        }

        with patch.object(filesystem_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "success": True,
                "path": str(test_file),
                "bytes_written": 12
            }

            result = await filesystem_tool.execute("write_file", params)

            assert result is not None
            assert result["success"] == True

    @pytest.mark.asyncio
    async def test_filesystem_list_directory(self, filesystem_tool, temp_workspace):
        """Test listing directory contents"""
        # Create test files
        (Path(temp_workspace) / "file1.txt").write_text("Content 1")
        (Path(temp_workspace) / "file2.py").write_text("# Python file")

        params = {
            "path": temp_workspace,
            "recursive": False
        }

        with patch.object(filesystem_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "path": temp_workspace,
                "files": [
                    {"name": "file1.txt", "type": "file"},
                    {"name": "file2.py", "type": "file"}
                ]
            }

            result = await filesystem_tool.execute("list_directory", params)

            assert result is not None
            assert len(result["files"]) == 2

    @pytest.mark.asyncio
    async def test_filesystem_search_files(self, filesystem_tool, temp_workspace):
        """Test searching for files"""
        params = {
            "path": temp_workspace,
            "pattern": "*.py"
        }

        with patch.object(filesystem_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "matches": [
                    {"path": "src/main.py", "name": "main.py"},
                    {"path": "tests/test_main.py", "name": "test_main.py"}
                ],
                "total": 2
            }

            result = await filesystem_tool.execute("search_files", params)

            assert result is not None
            assert result["total"] == 2

    def test_filesystem_path_security(self, filesystem_tool, temp_workspace):
        """Test path security restrictions"""
        # Verify allowed paths are configured
        assert temp_workspace in filesystem_tool.config["allowed_paths"]

        # Verify blocked patterns are configured
        blocked = filesystem_tool.config["blocked_patterns"]
        assert r"\.\./" in blocked  # Path traversal
        assert r"\/etc\/" in blocked  # System files

    def test_filesystem_file_size_limit(self, filesystem_tool):
        """Test file size limit is configured"""
        assert filesystem_tool.config.get("max_file_size_mb") == 10


# =============================================================================
# Memory MCP Server Feature Tests
# =============================================================================

class TestMemoryMCPFeatures:
    """Test all Memory MCP server features"""

    @pytest.fixture
    def memory_tool(self):
        """Create Memory MCP tool instance"""
        config = {
            "server_url": "http://localhost:3002",
            "storage_backend": "sqlite",
            "sqlite_path": ":memory:",  # In-memory database for testing
            "embedding_model": "all-MiniLM-L6-v2",
            "timeout": 5
        }
        return MemoryMCPTool(server_url=config["server_url"], config=config)

    @pytest.mark.asyncio
    async def test_memory_store(self, memory_tool):
        """Test storing information in memory"""
        params = {
            "content": "User prefers verbose logging",
            "memory_type": "preference",
            "tags": ["logging", "configuration"],
            "metadata": {"priority": "high"}
        }

        with patch.object(memory_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "success": True,
                "memory_id": "mem_12345",
                "type": "preference"
            }

            result = await memory_tool.execute("store", params)

            assert result is not None
            assert result["success"] == True
            assert "memory_id" in result

    @pytest.mark.asyncio
    async def test_memory_retrieve(self, memory_tool):
        """Test retrieving memory by ID"""
        params = {"memory_id": "mem_12345"}

        with patch.object(memory_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "memory_id": "mem_12345",
                "content": "User prefers verbose logging",
                "type": "preference",
                "tags": ["logging", "configuration"]
            }

            result = await memory_tool.execute("retrieve", params)

            assert result is not None
            assert result["memory_id"] == "mem_12345"

    @pytest.mark.asyncio
    async def test_memory_search(self, memory_tool):
        """Test semantic search in memory"""
        params = {
            "query": "logging preferences",
            "limit": 10,
            "memory_type": "preference",
            "min_relevance": 0.7
        }

        with patch.object(memory_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "results": [
                    {
                        "memory_id": "mem_12345",
                        "content": "User prefers verbose logging",
                        "relevance_score": 0.95
                    },
                    {
                        "memory_id": "mem_67890",
                        "content": "Logging level set to DEBUG",
                        "relevance_score": 0.82
                    }
                ],
                "total": 2
            }

            result = await memory_tool.execute("search", params)

            assert result is not None
            assert len(result["results"]) == 2
            assert result["results"][0]["relevance_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_memory_update(self, memory_tool):
        """Test updating existing memory"""
        params = {
            "memory_id": "mem_12345",
            "content": "User prefers DEBUG logging",
            "tags": ["logging", "configuration", "debug"]
        }

        with patch.object(memory_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "success": True,
                "memory_id": "mem_12345",
                "updated": True
            }

            result = await memory_tool.execute("update", params)

            assert result is not None
            assert result["success"] == True

    @pytest.mark.asyncio
    async def test_memory_delete(self, memory_tool):
        """Test deleting memory"""
        params = {"memory_id": "mem_12345"}

        with patch.object(memory_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "success": True,
                "memory_id": "mem_12345",
                "deleted": True
            }

            result = await memory_tool.execute("delete", params)

            assert result is not None
            assert result["success"] == True

    def test_memory_type_validation(self, memory_tool):
        """Test valid memory types"""
        valid_types = ["pattern", "preference", "solution", "context", "error"]
        # Memory types should be configurable
        assert memory_tool.config is not None


# =============================================================================
# CodeBaseBuddy MCP Server Feature Tests
# =============================================================================

class TestCodeBaseBuddyMCPFeatures:
    """Test all CodeBaseBuddy MCP server features"""

    @pytest.fixture
    def codebasebuddy_tool(self):
        """Create CodeBaseBuddy MCP tool instance"""
        config = {
            "server_url": "http://localhost:3004",
            "index_path": "./data/test_codebase_index",
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimensions": 384,
            "timeout": 60
        }
        return CodeBaseBuddyMCPTool(server_url=config["server_url"], config=config)

    @pytest.mark.asyncio
    async def test_codebasebuddy_semantic_search(self, codebasebuddy_tool):
        """Test semantic code search"""
        params = {
            "query": "How does authentication work?",
            "top_k": 5,
            "file_filter": "*.py"
        }

        with patch.object(codebasebuddy_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "results": [
                    {
                        "file": "src/auth.py",
                        "function": "authenticate_user",
                        "score": 0.95,
                        "content": "def authenticate_user(username, password):"
                    },
                    {
                        "file": "src/middleware.py",
                        "function": "check_auth",
                        "score": 0.88,
                        "content": "def check_auth(request):"
                    }
                ],
                "total": 5
            }

            result = await codebasebuddy_tool.execute("semantic_search", params)

            assert result is not None
            assert len(result["results"]) >= 2
            assert result["results"][0]["score"] > 0.8

    @pytest.mark.asyncio
    async def test_codebasebuddy_find_similar_code(self, codebasebuddy_tool):
        """Test finding similar code patterns"""
        params = {
            "code_snippet": "def calculate_total(items):\n    return sum(items)",
            "top_k": 5,
            "exclude_self": True
        }

        with patch.object(codebasebuddy_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "similar": [
                    {
                        "file": "src/utils.py",
                        "function": "sum_values",
                        "similarity": 0.92
                    },
                    {
                        "file": "src/calculator.py",
                        "function": "total_amount",
                        "similarity": 0.85
                    }
                ]
            }

            result = await codebasebuddy_tool.execute("find_similar_code", params)

            assert result is not None
            assert len(result["similar"]) >= 2

    @pytest.mark.asyncio
    async def test_codebasebuddy_get_code_context(self, codebasebuddy_tool):
        """Test getting code context around a line"""
        params = {
            "file_path": "src/main.py",
            "line_number": 42,
            "context_lines": 10
        }

        with patch.object(codebasebuddy_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "file": "src/main.py",
                "target_line": 42,
                "context": {
                    "before": ["line 32", "line 33", "..."],
                    "target": "def main():",
                    "after": ["    app.run()", "    logger.info('Started')"]
                }
            }

            result = await codebasebuddy_tool.execute("get_code_context", params)

            assert result is not None
            assert result["target_line"] == 42

    @pytest.mark.asyncio
    async def test_codebasebuddy_build_index(self, codebasebuddy_tool):
        """Test building code index"""
        params = {
            "root_path": "./src",
            "file_extensions": [".py", ".js"],
            "rebuild": False
        }

        with patch.object(codebasebuddy_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "success": True,
                "files_indexed": 42,
                "functions_indexed": 156,
                "classes_indexed": 28
            }

            result = await codebasebuddy_tool.execute("build_index", params)

            assert result is not None
            assert result["success"] == True
            assert result["files_indexed"] > 0

    @pytest.mark.asyncio
    async def test_codebasebuddy_find_usages(self, codebasebuddy_tool):
        """Test finding symbol usages"""
        params = {
            "symbol_name": "authenticate_user",
            "top_k": 10
        }

        with patch.object(codebasebuddy_tool, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "symbol": "authenticate_user",
                "usages": [
                    {
                        "file": "src/views.py",
                        "line": 25,
                        "context": "user = authenticate_user(username, pwd)"
                    },
                    {
                        "file": "src/api.py",
                        "line": 102,
                        "context": "result = authenticate_user(req.user, req.pass)"
                    }
                ],
                "total": 2
            }

            result = await codebasebuddy_tool.execute("find_usages", params)

            assert result is not None
            assert result["symbol"] == "authenticate_user"
            assert len(result["usages"]) > 0

    def test_codebasebuddy_configuration(self, codebasebuddy_tool):
        """Test CodeBaseBuddy configuration"""
        assert codebasebuddy_tool.config.get("embedding_model") == "all-MiniLM-L6-v2"
        assert codebasebuddy_tool.config.get("embedding_dimensions") == 384


# =============================================================================
# RUN ALL TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
