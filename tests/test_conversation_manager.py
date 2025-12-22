"""
Tests for ConversationManager
Tests workflow execution, conversation handling, and result processing
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.autogen_adapters.agent_factory import AutoGenAgentFactory
from src.autogen_adapters.conversation_manager import ConversationManager, ConversationResult
from src.autogen_adapters.function_registry import FunctionRegistry
from src.autogen_adapters.groupchat_factory import GroupChatFactory


@pytest.fixture
def mock_agent_factory():
    """Create a mock agent factory"""
    factory = Mock(spec=AutoGenAgentFactory)
    factory.list_agents = Mock(return_value=["code_analyzer", "user_proxy"])
    factory.get_agent = Mock(return_value=Mock())
    factory.create_all_agents = Mock()
    return factory


@pytest.fixture
def mock_groupchat_factory():
    """Create a mock groupchat factory"""
    factory = Mock(spec=GroupChatFactory)
    return factory


@pytest.fixture
def mock_function_registry():
    """Create a mock function registry"""
    registry = Mock(spec=FunctionRegistry)
    registry.initialize_tools = AsyncMock()
    registry.register_functions_with_agent = Mock()
    return registry


@pytest.fixture
def mock_workflow_config(tmp_path):
    """Create a temporary workflow configuration file"""
    config_content = """
workflows:
  test_workflow:
    type: "two_agent"
    agents: ["code_analyzer", "user_proxy"]
    initiator: "user_proxy"
    max_turns: 3
    message_template: "Analyze {code_path}"

  test_groupchat:
    type: "group_chat"
    agents: ["code_analyzer", "security_auditor", "user_proxy"]
    max_round: 5
    message_template: "Review {target_path}"

conversation_patterns:
  sequential:
    type: "sequential"

conversation_persistence:
  enabled: true
  storage: "sqlite"
"""
    config_file = tmp_path / "test_workflows.yaml"
    config_file.write_text(config_content)
    return str(config_file)


class TestConversationManagerInit:
    """Test ConversationManager initialization"""

    def test_init_with_config_file(self, mock_workflow_config, mock_agent_factory):
        """Test initialization with valid config file"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        assert manager.config_path == mock_workflow_config
        assert "test_workflow" in manager.workflow_configs
        assert "test_groupchat" in manager.workflow_configs
        assert len(manager.history) == 0

    def test_init_with_missing_config(self):
        """Test initialization with missing config file"""
        with pytest.raises(FileNotFoundError):
            ConversationManager(config_path="nonexistent.yaml")

    def test_init_with_custom_factories(
        self,
        mock_workflow_config,
        mock_agent_factory,
        mock_groupchat_factory,
        mock_function_registry,
    ):
        """Test initialization with custom factory instances"""
        manager = ConversationManager(
            config_path=mock_workflow_config,
            agent_factory=mock_agent_factory,
            groupchat_factory=mock_groupchat_factory,
            function_registry=mock_function_registry,
        )

        assert manager.agent_factory == mock_agent_factory
        assert manager.groupchat_factory == mock_groupchat_factory
        assert manager.function_registry == mock_function_registry


class TestConversationManagerInitialization:
    """Test async initialization"""

    @pytest.mark.asyncio
    async def test_initialize(
        self, mock_workflow_config, mock_agent_factory, mock_function_registry
    ):
        """Test async initialization of components"""
        manager = ConversationManager(
            config_path=mock_workflow_config,
            agent_factory=mock_agent_factory,
            function_registry=mock_function_registry,
        )

        await manager.initialize()

        # Verify initialization calls
        mock_function_registry.initialize_tools.assert_called_once()
        mock_agent_factory.create_all_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_functions_with_agents(
        self, mock_workflow_config, mock_agent_factory, mock_function_registry
    ):
        """Test function registration with agents"""
        manager = ConversationManager(
            config_path=mock_workflow_config,
            agent_factory=mock_agent_factory,
            function_registry=mock_function_registry,
        )

        await manager._register_functions_with_agents()

        # Should register for each agent
        assert mock_function_registry.register_functions_with_agent.call_count == 2


class TestVariableReplacement:
    """Test variable replacement in templates"""

    def test_replace_variables_simple(self, mock_workflow_config, mock_agent_factory):
        """Test simple variable replacement"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        template = "Analyze {code_path} for {focus_areas}"
        variables = {"code_path": "./test.py", "focus_areas": "security"}

        result = manager._replace_variables(template, variables)
        assert result == "Analyze ./test.py for security"

    def test_replace_variables_multiple(self, mock_workflow_config, mock_agent_factory):
        """Test multiple variable replacements"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        template = "{name} {name} {value}"
        variables = {"name": "test", "value": "123"}

        result = manager._replace_variables(template, variables)
        assert result == "test test 123"

    def test_replace_variables_missing(self, mock_workflow_config, mock_agent_factory):
        """Test variable replacement with missing variables"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        template = "Analyze {code_path}"
        variables = {}

        result = manager._replace_variables(template, variables)
        # Should leave placeholder unchanged
        assert result == "Analyze {code_path}"


class TestWorkflowExecution:
    """Test workflow execution"""

    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_name(self, mock_workflow_config, mock_agent_factory):
        """Test executing non-existent workflow"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        with pytest.raises(ValueError, match="Workflow 'invalid' not found"):
            await manager.execute_workflow("invalid")

    @pytest.mark.asyncio
    async def test_execute_workflow_two_agent(self, mock_workflow_config, mock_agent_factory):
        """Test executing two-agent workflow"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        # Mock the two-agent execution
        mock_result = ConversationResult(
            workflow_name="test_workflow",
            status="success",
            messages=[{"role": "user", "content": "test"}],
            summary="Test completed",
            duration_seconds=0,
            tasks_completed=1,
            tasks_failed=0,
        )

        with patch.object(manager, "_execute_two_agent_workflow", return_value=mock_result):
            result = await manager.execute_workflow(
                "test_workflow", variables={"code_path": "./test.py"}
            )

        assert result.workflow_name == "test_workflow"
        assert result.status == "success"
        assert len(manager.history) == 1

    @pytest.mark.asyncio
    async def test_execute_workflow_error_handling(self, mock_workflow_config, mock_agent_factory):
        """Test workflow execution error handling"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        # Mock the execution to raise an error
        with patch.object(
            manager, "_execute_two_agent_workflow", side_effect=Exception("Test error")
        ):
            result = await manager.execute_workflow("test_workflow")

        assert result.status == "failed"
        assert result.error == "Test error"
        assert result.tasks_failed == 1
        assert len(manager.history) == 1


class TestWorkflowTypes:
    """Test different workflow types"""

    @pytest.mark.asyncio
    async def test_workflow_type_detection(self, mock_workflow_config, mock_agent_factory):
        """Test workflow type detection and routing"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        # Test two_agent type
        with patch.object(manager, "_execute_two_agent_workflow") as mock_two_agent:
            mock_two_agent.return_value = ConversationResult(
                workflow_name="test",
                status="success",
                messages=[],
                summary="",
                duration_seconds=0,
                tasks_completed=0,
                tasks_failed=0,
            )
            await manager.execute_workflow("test_workflow")
            mock_two_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_workflow_type(self, mock_workflow_config, mock_agent_factory):
        """Test handling of invalid workflow type"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        # Add workflow with invalid type
        manager.workflow_configs["invalid_type"] = {"type": "unknown_type", "agents": ["test"]}

        result = await manager.execute_workflow("invalid_type")
        assert result.status == "failed"
        assert "Unknown workflow type" in result.error


class TestConversationHistory:
    """Test conversation history tracking"""

    @pytest.mark.asyncio
    async def test_history_tracking(self, mock_workflow_config, mock_agent_factory):
        """Test that execution history is tracked"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        mock_result = ConversationResult(
            workflow_name="test",
            status="success",
            messages=[],
            summary="Test",
            duration_seconds=0,
            tasks_completed=1,
            tasks_failed=0,
        )

        with patch.object(manager, "_execute_two_agent_workflow", return_value=mock_result):
            await manager.execute_workflow("test_workflow")
            await manager.execute_workflow("test_workflow")

        assert len(manager.history) == 2
        assert all(r.workflow_name == "test" for r in manager.history)

    def test_get_history(self, mock_workflow_config, mock_agent_factory):
        """Test retrieving execution history"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        # Add some results to history
        manager.history.append(
            ConversationResult(
                workflow_name="test1",
                status="success",
                messages=[],
                summary="",
                duration_seconds=1.0,
                tasks_completed=1,
                tasks_failed=0,
            )
        )

        assert len(manager.history) == 1
        assert manager.history[0].workflow_name == "test1"


class TestWorkflowListing:
    """Test workflow listing functionality"""

    def test_list_workflows(self, mock_workflow_config, mock_agent_factory):
        """Test listing available workflows"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        workflows = manager.list_workflows()

        assert "test_workflow" in workflows
        assert "test_groupchat" in workflows
        assert len(workflows) == 2

    def test_get_workflow_config(self, mock_workflow_config, mock_agent_factory):
        """Test retrieving workflow configuration"""
        manager = ConversationManager(
            config_path=mock_workflow_config, agent_factory=mock_agent_factory
        )

        config = manager.workflow_configs.get("test_workflow")

        assert config is not None
        assert config["type"] == "two_agent"
        assert "code_analyzer" in config["agents"]


class TestConversationResult:
    """Test ConversationResult dataclass"""

    def test_conversation_result_creation(self):
        """Test creating ConversationResult"""
        result = ConversationResult(
            workflow_name="test",
            status="success",
            messages=[{"role": "user", "content": "test"}],
            summary="Test completed",
            duration_seconds=1.5,
            tasks_completed=1,
            tasks_failed=0,
        )

        assert result.workflow_name == "test"
        assert result.status == "success"
        assert len(result.messages) == 1
        assert result.duration_seconds == 1.5
        assert result.error is None

    def test_conversation_result_with_error(self):
        """Test ConversationResult with error"""
        result = ConversationResult(
            workflow_name="test",
            status="failed",
            messages=[],
            summary="Failed",
            duration_seconds=0.5,
            tasks_completed=0,
            tasks_failed=1,
            error="Test error message",
        )

        assert result.status == "failed"
        assert result.error == "Test error message"
        assert result.tasks_failed == 1


@pytest.mark.integration
class TestConversationManagerIntegration:
    """Integration tests for ConversationManager"""

    def test_full_initialization_flow(self, mock_workflow_config):
        """Test complete initialization flow"""
        # This test verifies the manager can be created with real factories
        # (though agents won't be functional without API keys)
        manager = ConversationManager(config_path=mock_workflow_config)

        assert manager.agent_factory is not None
        assert manager.groupchat_factory is not None
        assert manager.function_registry is not None
        assert len(manager.workflow_configs) == 2
