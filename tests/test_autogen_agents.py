"""AutoGen Agent Tests"""

from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.agent


class TestAgentFactory:
    """Test AutoGen agent factory"""

    @patch("src.autogen_adapters.agent_factory.HAS_AUTOGEN", True)
    @patch("src.autogen_adapters.agent_factory.AssistantAgent")
    def test_create_assistant_agent(self, mock_assistant, mock_env):
        """Test creating an AssistantAgent from config"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        mock_assistant.return_value = MagicMock()

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")
        agent = factory.create_agent("code_analyzer")

        assert agent is not None
        assert "code_analyzer" in factory.agents

    @patch("src.autogen_adapters.agent_factory.HAS_AUTOGEN", False)
    def test_create_agent_without_autogen(self, mock_env):
        """Test that creating agent without autogen raises error"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")

        with pytest.raises(RuntimeError, match="pyautogen is not installed"):
            factory.create_agent("code_analyzer")

    @patch("src.autogen_adapters.agent_factory.HAS_AUTOGEN", True)
    @patch("src.autogen_adapters.agent_factory.UserProxyAgent")
    def test_create_user_proxy_agent(self, mock_proxy, mock_env):
        """Test creating a UserProxyAgent"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        mock_proxy.return_value = MagicMock()

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")
        agent = factory.create_agent("executor")

        assert agent is not None


class TestAgentConfiguration:
    """Test agent configuration loading"""

    def test_load_agent_config(self, mock_env):
        """Test loading agent configuration from YAML"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")

        assert factory.config is not None
        assert "agents" in factory.config
        assert "llm_configs" in factory.config

    def test_env_var_replacement(self, mock_env):
        """Test environment variable replacement in config"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")
        test_obj = {"key": "${GEMINI_API_KEY}"}

        result = factory._replace_env_vars(test_obj)

        assert result["key"] == "test-key"


class TestAgentFunctionCalling:
    """Test function calling capabilities"""

    @pytest.mark.integration
    @patch("src.autogen_adapters.agent_factory.HAS_AUTOGEN", True)
    @patch("src.autogen_adapters.agent_factory.AssistantAgent")
    def test_register_function_with_agent(self, mock_assistant, mock_env):
        """Test registering a function with an agent"""
        from src.autogen_adapters.agent_factory import AutoGenAgentFactory
        from src.autogen_adapters.function_registry import FunctionRegistry

        mock_agent = MagicMock()
        mock_assistant.return_value = mock_agent

        factory = AutoGenAgentFactory("config/autogen_agents.yaml")
        registry = FunctionRegistry()

        # Create a simple test function
        def test_function(param: str) -> str:
            """Test function"""
            return f"Result: {param}"

        registry.register_function("test_func", test_function)

        # Verify function is registered
        assert "test_func" in registry.functions

    @pytest.mark.integration
    def test_function_execution(self):
        """Test executing a registered function"""
        from src.autogen_adapters.function_registry import FunctionRegistry

        registry = FunctionRegistry()

        def add_numbers(a: int, b: int) -> int:
            """Add two numbers"""
            return a + b

        registry.register_function("add", add_numbers)
        result = registry.execute_function("add", {"a": 5, "b": 3})

        assert result == 8
