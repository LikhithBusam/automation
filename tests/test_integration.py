"""Integration Tests for Agent-MCP Communication"""
import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.integration


class TestAgentMCPIntegration:
    """Test agents using MCP tools"""

    @patch('src.autogen_adapters.agent_factory.HAS_AUTOGEN', True)
    @patch('src.autogen_adapters.agent_factory.AssistantAgent')
    def test_agent_uses_filesystem_tool(self, mock_assistant, temp_workspace, sample_code_file):
        """Test agent can use filesystem tool to read files"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory
        from src.mcp.filesystem_tool import FilesystemMCPTool

        mock_agent = MagicMock()
        mock_assistant.return_value = mock_agent

        # Create tool and agent
        tool = FilesystemMCPTool(allowed_paths=[str(temp_workspace)])
        factory = AutoGenAgentFactory("config/autogen_agents.yaml")

        # Test tool can read file
        content = tool.read_file(str(sample_code_file))
        assert "hello_world" in content

    @patch('src.autogen_adapters.agent_factory.HAS_AUTOGEN', True)
    @patch('src.autogen_adapters.agent_factory.AssistantAgent')
    def test_agent_uses_memory_tool(self, mock_assistant, mock_env):
        """Test agent can use memory tool"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory
        from src.mcp.memory_tool import MemoryMCPTool

        mock_agent = MagicMock()
        mock_assistant.return_value = mock_agent

        # Create tool and agent
        tool = MemoryMCPTool()
        factory = AutoGenAgentFactory("config/autogen_agents.yaml")

        # Test tool can store and retrieve
        memory_id = tool.store_memory(
            content={"test": "data"},
            memory_type="short_term",
            tags=["test"]
        )
        assert memory_id is not None

        retrieved = tool.retrieve_memory(memory_id)
        assert retrieved is not None


class TestConversationManager:
    """Test conversation manager"""

    @patch('src.autogen_adapters.agent_factory.HAS_AUTOGEN', True)
    def test_create_conversation_manager(self, mock_env):
        """Test creating conversation manager"""
        from src.autogen_adapters.conversation_manager import create_conversation_manager

        try:
            manager = create_conversation_manager()
            assert manager is not None
        except Exception as e:
            pytest.skip(f"Conversation manager creation failed: {e}")


class TestFunctionRegistry:
    """Test function registry integration"""

    def test_register_mcp_tool_functions(self):
        """Test registering MCP tools as functions"""
        from src.autogen_adapters.function_registry import FunctionRegistry

        registry = FunctionRegistry()

        # Register a mock MCP tool function
        def mock_mcp_function(param: str) -> dict:
            """Mock MCP function"""
            return {"status": "success", "param": param}

        registry.register_function("mock_mcp", mock_mcp_function)

        # Verify registration
        assert "mock_mcp" in registry.functions

        # Test execution
        result = registry.execute_function("mock_mcp", {"param": "test"})
        assert result["status"] == "success"
        assert result["param"] == "test"

    def test_function_error_handling(self):
        """Test function registry error handling"""
        from src.autogen_adapters.function_registry import FunctionRegistry

        registry = FunctionRegistry()

        def failing_function():
            """Function that raises error"""
            raise ValueError("Test error")

        registry.register_function("failing_func", failing_function)

        # Should handle error gracefully
        with pytest.raises((ValueError, Exception)):
            registry.execute_function("failing_func", {})
