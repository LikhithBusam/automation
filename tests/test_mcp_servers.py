"""MCP Server Health Check and Basic Operation Tests"""
import pytest
import requests
from unittest.mock import Mock, patch

pytestmark = pytest.mark.mcp


class TestMCPServerHealth:
    """Health check tests for all MCP servers"""

    def test_github_server_health(self, test_config):
        """Test GitHub MCP server is responsive"""
        port = test_config["mcp_servers"]["github"]["port"]
        try:
            response = requests.get(
                f"http://localhost:{port}/health",
                timeout=test_config["mcp_servers"]["github"]["timeout"]
            )
            assert response.status_code == 200
            assert response.elapsed.total_seconds() < 0.5
        except requests.ConnectionError:
            pytest.skip("GitHub MCP server not running")

    def test_filesystem_server_health(self, test_config):
        """Test Filesystem MCP server is responsive"""
        port = test_config["mcp_servers"]["filesystem"]["port"]
        try:
            response = requests.get(
                f"http://localhost:{port}/health",
                timeout=test_config["mcp_servers"]["filesystem"]["timeout"]
            )
            assert response.status_code == 200
        except requests.ConnectionError:
            pytest.skip("Filesystem MCP server not running")

    def test_memory_server_health(self, test_config):
        """Test Memory MCP server is responsive"""
        port = test_config["mcp_servers"]["memory"]["port"]
        try:
            response = requests.get(
                f"http://localhost:{port}/health",
                timeout=test_config["mcp_servers"]["memory"]["timeout"]
            )
            assert response.status_code == 200
        except requests.ConnectionError:
            pytest.skip("Memory MCP server not running")


class TestFilesystemMCPOperations:
    """Test basic filesystem operations"""

    @pytest.mark.integration
    def test_read_file(self, temp_workspace, sample_code_file):
        """Test reading a file through MCP"""
        from src.mcp.filesystem_tool import FilesystemMCPTool

        tool = FilesystemMCPTool(allowed_paths=[str(temp_workspace)])
        result = tool.read_file(str(sample_code_file))

        assert result is not None
        assert "hello_world" in result
        assert "Calculator" in result

    @pytest.mark.integration
    def test_write_file(self, temp_workspace):
        """Test writing a file through MCP"""
        from src.mcp.filesystem_tool import FilesystemMCPTool

        tool = FilesystemMCPTool(allowed_paths=[str(temp_workspace)])
        test_file = temp_workspace / "test_write.txt"
        content = "Test content"

        tool.write_file(str(test_file), content)

        assert test_file.exists()
        assert test_file.read_text() == content

    @pytest.mark.integration
    def test_list_directory(self, temp_workspace, sample_code_file):
        """Test listing directory contents"""
        from src.mcp.filesystem_tool import FilesystemMCPTool

        tool = FilesystemMCPTool(allowed_paths=[str(temp_workspace)])
        result = tool.list_directory(str(temp_workspace))

        assert "sample.py" in str(result)


class TestMemoryMCPOperations:
    """Test memory storage and retrieval"""

    @pytest.mark.integration
    def test_store_and_retrieve_memory(self):
        """Test storing and retrieving memory"""
        from src.mcp.memory_tool import MemoryMCPTool

        tool = MemoryMCPTool()
        memory_content = {"test": "data", "type": "pattern"}

        memory_id = tool.store_memory(
            content=memory_content,
            memory_type="short_term",
            tags=["test"]
        )

        assert memory_id is not None

        retrieved = tool.retrieve_memory(memory_id)
        assert retrieved["content"] == memory_content
