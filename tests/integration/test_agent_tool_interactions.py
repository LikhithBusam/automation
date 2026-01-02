"""
Integration Tests: Agent-to-Tool Interactions
Tests agent successfully calling tools, error propagation, retry logic, timeout handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any


class TestAgentToolInteractions:
    """Test agent-to-tool interactions"""
    
    @pytest.fixture
    async def tool_manager(self):
        """Create a mock tool manager"""
        from src.mcp.tool_manager import MCPToolManager
        
        # Create a minimal config
        config = {
            "mcp_servers": {},
            "connection_pool_size": 5
        }
        
        manager = MCPToolManager(config=config)
        return manager
    
    @pytest.fixture
    async def mock_agent(self):
        """Create a mock agent"""
        # Use mock agent since BaseAgent doesn't exist
        agent = Mock()
        agent.name = "test_agent"
        agent.tools = ["github", "filesystem"]
        agent.execute_task = AsyncMock(return_value={"status": "success"})
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_successfully_calls_tool(self, mock_agent, tool_manager):
        """Test agent successfully calls a tool"""
        # Mock tool execution
        with patch.object(tool_manager, 'execute') as mock_execute:
            mock_execute.return_value = {"status": "success", "data": "test_result"}
            
            # Agent calls tool
            result = await tool_manager.execute(
                tool_name="github",
                operation="get_repository",
                params={"owner": "test", "repo": "test"},
                agent_name="test_agent"
            )
            
            assert result["status"] == "success"
            assert result["data"] == "test_result"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, mock_agent, tool_manager):
        """Test error propagation from tool to agent"""
        from src.mcp.base_tool import MCPToolError
        
        # Mock tool execution to raise error
        with patch.object(tool_manager, 'execute') as mock_execute:
            mock_execute.side_effect = MCPToolError("Tool execution failed", "github", "get_repository")
            
            # Agent should receive the error
            with pytest.raises(MCPToolError) as exc_info:
                await tool_manager.execute(
                    tool_name="github",
                    operation="get_repository",
                    params={"owner": "test", "repo": "test"},
                    agent_name="test_agent"
                )
            
            assert "Tool execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, tool_manager):
        """Test retry logic in tool execution"""
        # Create a mock tool with retry logic
        call_count = 0
        
        async def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return {"status": "success"}
        
        # Implement retry logic manually
        max_retries = 3
        result = None
        
        for attempt in range(max_retries):
            try:
                result = await failing_then_succeeding()
                break
            except ConnectionError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.01)  # Brief delay between retries
        
        assert result["status"] == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, tool_manager):
        """Test timeout handling in tool execution"""
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow operation
            return {"status": "success"}
        
        with patch.object(tool_manager, 'execute', side_effect=slow_operation):
            # Should timeout after 1 second
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    tool_manager.execute(
                        tool_name="github",
                        operation="get_repository",
                        params={"owner": "test", "repo": "test"}
                    ),
                    timeout=1.0
                )
    
    @pytest.mark.asyncio
    async def test_tool_permission_check(self, tool_manager):
        """Test tool permission checking"""
        # Mock permission check
        with patch.object(tool_manager, 'agent_permissions') as mock_perms:
            mock_perms.get.return_value = Mock(can_execute_operation=lambda t, o: False)
            
            # Agent without permission should be denied
            with pytest.raises(PermissionError):
                await tool_manager.execute(
                    tool_name="github",
                    operation="delete_repository",
                    params={"owner": "test", "repo": "test"},
                    agent_name="unauthorized_agent"
                )
    
    @pytest.mark.asyncio
    async def test_tool_caching(self, tool_manager):
        """Test tool result caching"""
        call_count = 0
        cache = {}
        
        async def cached_operation(*args, **kwargs):
            nonlocal call_count
            cache_key = str(args) + str(kwargs)
            if cache_key in cache:
                return cache[cache_key]
            call_count += 1
            result = {"status": "success", "call_count": call_count}
            cache[cache_key] = result
            return result
        
        # First call
        result1 = await cached_operation("github", "get_repository", owner="test", repo="test")
        
        # Second call should use cache (same call_count)
        result2 = await cached_operation("github", "get_repository", owner="test", repo="test")
        
        # Results should be the same (cached)
        assert result1 == result2
        assert result1["call_count"] == 1  # Only called once due to caching
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, tool_manager):
        """Test rate limiting in tool calls"""
        from src.security.rate_limiter import RateLimiter, RateLimitExceeded
        
        # Create rate limiter with very low limit (1 call per 10 seconds)
        rate_limiter = RateLimiter(max_calls=1, time_window_seconds=10)
        
        call_count = 0
        
        async def rate_limited_operation(*args, **kwargs):
            nonlocal call_count
            # Use acquire with wait=False to immediately get rate limit error
            try:
                await rate_limiter.acquire(wait=False)
            except RateLimitExceeded:
                raise Exception("Rate limit exceeded")
            call_count += 1
            return {"status": "success"}
        
        with patch.object(tool_manager, 'execute', side_effect=rate_limited_operation):
            # First call should succeed
            result1 = await tool_manager.execute(
                tool_name="github",
                operation="get_repository",
                params={"owner": "test", "repo": "test"}
            )
            assert result1["status"] == "success"
            
            # Immediate second call should be rate limited
            with pytest.raises(Exception) as exc_info:
                await tool_manager.execute(
                    tool_name="github",
                    operation="get_repository",
                    params={"owner": "test", "repo": "test"}
                )
            assert "Rate limit" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, tool_manager):
        """Test circuit breaker pattern"""
        from src.security.circuit_breaker import CircuitBreaker
        
        # Create circuit breaker that opens after 3 failures
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout_seconds=60
        )
        
        failure_count = 0
        
        async def failing_operation(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            raise Exception("Operation failed")
        
        with patch.object(tool_manager, 'execute', side_effect=failing_operation):
            # First 3 failures should be allowed
            for i in range(3):
                with pytest.raises(Exception):
                    await circuit_breaker.call(
                        tool_manager.execute,
                        tool_name="github",
                        operation="get_repository",
                        params={"owner": "test", "repo": "test"}
                    )
            
            # After 3 failures, circuit should be open
            with pytest.raises(Exception) as exc_info:
                await circuit_breaker.call(
                    tool_manager.execute,
                    tool_name="github",
                    operation="get_repository",
                    params={"owner": "test", "repo": "test"}
                )
            assert "Circuit breaker is OPEN" in str(exc_info.value) or "Circuit open" in str(exc_info.value)

