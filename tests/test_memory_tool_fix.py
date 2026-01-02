"""
Test suite for Memory Tool Bug Fix
Tests the fix for KeyError: 'type' when storing memory without explicit type
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.mcp.memory_tool import MemoryMCPTool, MCPValidationError


class TestMemoryToolTypeParameter:
    """Test memory tool handles missing type parameter correctly"""

    @pytest.fixture
    def memory_tool(self):
        """Create MemoryMCPTool instance"""
        return MemoryMCPTool()

    @pytest.mark.asyncio
    async def test_store_memory_without_type(self, memory_tool):
        """Test storing memory without explicit type parameter (should default to 'context')"""
        params = {
            "content": "Test memory content",
            # No 'type' parameter - should default to 'context'
        }

        # Mock the client and response
        with patch.object(memory_tool, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"id": "test-id", "status": "stored"}
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await memory_tool._store_memory(params)

            # Verify type defaults to 'context'
            call_args = mock_client.post.call_args
            assert call_args is not None
            memory_data = call_args[1]['json']
            assert memory_data['type'] == 'context'
            assert memory_data['content'] == 'Test memory content'

    @pytest.mark.asyncio
    async def test_store_memory_with_explicit_type(self, memory_tool):
        """Test storing memory with explicit type parameter"""
        params = {
            "content": "Test memory content",
            "type": "pattern"  # Explicit type
        }

        with patch.object(memory_tool, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"id": "test-id", "status": "stored"}
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await memory_tool._store_memory(params)

            # Verify explicit type is used
            call_args = mock_client.post.call_args
            memory_data = call_args[1]['json']
            assert memory_data['type'] == 'pattern'

    @pytest.mark.asyncio
    async def test_store_memory_missing_content(self, memory_tool):
        """Test that missing content parameter raises ValidationError"""
        params = {
            # Missing 'content' parameter - should raise error
            "type": "context"
        }

        with pytest.raises(MCPValidationError, match="Missing required parameter: content"):
            await memory_tool._store_memory(params)

    @pytest.mark.asyncio
    async def test_store_memory_tier_determination(self, memory_tool):
        """Test tier determination based on type"""
        test_cases = [
            ({"content": "test", "type": "pattern"}, "long"),
            ({"content": "test", "type": "decision"}, "long"),
            ({"content": "test", "type": "error"}, "medium"),
            ({"content": "test", "type": "solution"}, "medium"),
            ({"content": "test", "type": "context"}, "short"),
            ({"content": "test"}, "short"),  # Default type 'context' -> short tier
        ]

        for params, expected_tier in test_cases:
            with patch.object(memory_tool, '_get_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.json.return_value = {"id": "test-id"}
                mock_response.raise_for_status = Mock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await memory_tool._store_memory(params)
                
                # Verify tier is correctly determined
                call_args = mock_client.post.call_args
                memory_data = call_args[1]['json']
                assert memory_data['tier'] == expected_tier, \
                    f"Expected tier {expected_tier} for params {params}, got {memory_data['tier']}"

    @pytest.mark.asyncio
    async def test_store_memory_fallback_handling(self, memory_tool):
        """Test fallback to local storage when server fails"""
        params = {
            "content": "Test memory content",
        }

        with patch.object(memory_tool, '_get_client') as mock_get_client:
            # Simulate server failure
            mock_get_client.side_effect = Exception("Connection failed")
            
            # Mock fallback store
            with patch.object(memory_tool, '_fallback_store') as mock_fallback:
                mock_fallback.return_value = {"id": "fallback-id", "fallback": True}
                
                result = await memory_tool._store_memory(params)
                
                # Verify fallback was called
                assert mock_fallback.called
                assert result["fallback"] is True

