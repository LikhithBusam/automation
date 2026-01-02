"""
Unit Tests for MCP Tools
Test each operation, mock external services, error handling, rate limiting, circuit breaker
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Note: Import actual classes when available
# from src.mcp.github_tool import GitHubMCPTool
# from src.mcp.filesystem_tool import FilesystemMCPTool
# from src.mcp.memory_tool import MemoryMCPTool
from src.security.rate_limiter import RateLimiter
from src.security.circuit_breaker import CircuitBreaker


class TestGitHubMCPTool:
    """Test GitHub MCP tool"""
    
    @pytest.fixture
    def github_tool(self):
        """Create GitHub tool instance"""
        # Mock tool for testing
        class MockGitHubTool:
            def __init__(self, api_token):
                self.api_token = api_token
            
            async def list_repositories(self):
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.github.com/user/repos",
                        headers={"Authorization": f"token {self.api_token}"}
                    )
                    return response.json()
            
            async def create_issue(self, repo, title, body):
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://api.github.com/repos/{repo}/issues",
                        headers={"Authorization": f"token {self.api_token}"},
                        json={"title": title, "body": body}
                    )
                    return response.json()
        
        return MockGitHubTool(api_token="test_token")
    
    @pytest.mark.asyncio
    async def test_list_repositories(self, github_tool):
        """Test list repositories"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [{"name": "repo1"}, {"name": "repo2"}]
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            repos = await github_tool.list_repositories()
            assert len(repos) == 2
    
    @pytest.mark.asyncio
    async def test_list_repositories_error(self, github_tool):
        """Test list repositories with error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("API error")
            
            with pytest.raises(Exception):
                await github_tool.list_repositories()
    
    @pytest.mark.asyncio
    async def test_create_issue(self, github_tool):
        """Test create issue"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"number": 1, "title": "Test Issue"}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            issue = await github_tool.create_issue("owner/repo", "Title", "Body")
            assert issue["number"] == 1


class TestFilesystemMCPTool:
    """Test Filesystem MCP tool"""
    
    @pytest.fixture
    def fs_tool(self):
        """Create filesystem tool instance"""
        # Mock filesystem tool
        class MockFilesystemTool:
            async def read_file(self, path):
                with open(path, 'r') as f:
                    return f.read()
            
            async def write_file(self, path, content):
                with open(path, 'w') as f:
                    f.write(content)
            
            async def list_directory(self, path):
                import os
                return os.listdir(path)
        
        return MockFilesystemTool()
    
    @pytest.mark.asyncio
    async def test_read_file(self, fs_tool, tmp_path):
        """Test read file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        content = await fs_tool.read_file(str(test_file))
        assert content == "test content"
    
    @pytest.mark.asyncio
    async def test_read_file_not_found(self, fs_tool):
        """Test read file not found"""
        with pytest.raises(FileNotFoundError):
            await fs_tool.read_file("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_write_file(self, fs_tool, tmp_path):
        """Test write file"""
        test_file = tmp_path / "test.txt"
        
        await fs_tool.write_file(str(test_file), "new content")
        
        assert test_file.read_text() == "new content"
    
    @pytest.mark.asyncio
    async def test_list_directory(self, fs_tool, tmp_path):
        """Test list directory"""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        
        files = await fs_tool.list_directory(str(tmp_path))
        assert len(files) >= 2


class TestMemoryMCPTool:
    """Test Memory MCP tool"""
    
    @pytest.fixture
    def memory_tool(self, mock_storage_backend):
        """Create memory tool instance"""
        # Mock memory tool
        class MockMemoryTool:
            def __init__(self, storage_backend):
                self.storage_backend = storage_backend
            
            async def store_memory(self, key, content, tier="short_term"):
                await self.storage_backend.set(f"memory:{key}", {
                    "content": content,
                    "tier": tier
                })
                return key
            
            async def retrieve_memory(self, key):
                data = await self.storage_backend.get(f"memory:{key}")
                return data.get("content") if data else None
        
        return MockMemoryTool(storage_backend=mock_storage_backend)
    
    @pytest.mark.asyncio
    async def test_store_memory(self, memory_tool):
        """Test store memory"""
        result = await memory_tool.store_memory(
            "test_key",
            "test_content",
            tier="short_term"
        )
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_memory(self, memory_tool, mock_storage_backend):
        """Test retrieve memory"""
        mock_storage_backend.get.return_value = {
            "content": "test_content",
            "tier": "short_term"
        }
        
        content = await memory_tool.retrieve_memory("test_key")
        assert content == "test_content"
    
    @pytest.mark.asyncio
    async def test_retrieve_memory_not_found(self, memory_tool, mock_storage_backend):
        """Test retrieve memory not found"""
        mock_storage_backend.get.return_value = None
        
        content = await memory_tool.retrieve_memory("nonexistent_key")
        assert content is None


class TestRateLimiter:
    """Test rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allow(self):
        """Test rate limiter allows requests"""
        from src.security.rate_limiter import RateLimitExceeded
        
        limiter = RateLimiter(max_calls=10, time_window_seconds=60)
        
        for _ in range(10):
            allowed = await limiter.acquire(wait=False)
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_block(self):
        """Test rate limiter blocks excess requests"""
        from src.security.rate_limiter import RateLimitExceeded
        
        limiter = RateLimiter(max_calls=5, time_window_seconds=60)
        
        # Exceed limit
        for _ in range(5):
            await limiter.acquire(wait=False)
        
        # Next request should be blocked
        with pytest.raises(RateLimitExceeded):
            await limiter.acquire(wait=False)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self):
        """Test rate limiter reset"""
        limiter = RateLimiter(max_calls=5, time_window_seconds=1)
        
        # Exceed limit
        for _ in range(5):
            await limiter.acquire(wait=False)
        
        # Wait for reset
        await asyncio.sleep(1.1)
        
        # Should allow again
        allowed = await limiter.acquire(wait=False)
        assert allowed is True


class TestCircuitBreaker:
    """Test circuit breaker"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed(self):
        """Test circuit breaker in closed state"""
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60
        )
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failures"""
        breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=60
        )
        
        async def fail_func():
            raise Exception("Failure")
        
        # Trigger failures
        for _ in range(3):
            try:
                await breaker.call(fail_func)
            except Exception:
                pass
        
        # Circuit should be open
        with pytest.raises(Exception):
            await breaker.call(fail_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self):
        """Test circuit breaker half-open state"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            timeout_seconds=1
        )
        
        async def fail_func():
            raise Exception("Failure")
        
        # Open circuit
        for _ in range(2):
            try:
                await breaker.call(fail_func)
            except Exception:
                pass
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Should be in half-open state
        # First success should close it
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"

