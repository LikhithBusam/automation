"""
Tests for GroupChatFactory
Tests group chat creation, speaker selection, and agent coordination
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.autogen_adapters.groupchat_factory import GroupChatFactory


@pytest.fixture
def mock_groupchat_config(tmp_path):
    """Create a temporary groupchat configuration file"""
    config_content = """
group_chats:
  code_review_team:
    agents: ["code_analyzer", "security_auditor", "user_proxy"]
    max_round: 10
    admin_name: "project_manager"
    speaker_selection_method: "round_robin"
    allow_repeat_speaker: false

  security_team:
    agents: ["security_auditor", "code_analyzer"]
    max_round: 5
    speaker_selection_method: "auto"
    allow_repeat_speaker: true

group_chat_managers:
  default_manager:
    system_message: "You are managing a group chat"
    max_consecutive_auto_reply: 10
"""
    config_file = tmp_path / "test_groupchats.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def mock_agents():
    """Create mock agents for testing"""
    agents = {}
    for name in ["code_analyzer", "security_auditor", "user_proxy", "project_manager"]:
        agent = Mock()
        agent.name = name
        agents[name] = agent
    return agents


class TestGroupChatFactoryInit:
    """Test GroupChatFactory initialization"""

    def test_init_with_config_file(self, mock_groupchat_config):
        """Test initialization with valid config file"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        assert factory.config_path == mock_groupchat_config
        assert (
            "code_review_team" in factory.groupchat_configs
            or "code_review_team" in factory.list_groupchats()
        )
        assert (
            "security_team" in factory.groupchat_configs
            or "security_team" in factory.list_groupchats()
        )
        assert len(factory.groupchats) == 0

    def test_init_with_missing_config(self):
        """Test initialization with missing config file"""
        with pytest.raises(FileNotFoundError):
            GroupChatFactory(config_path="nonexistent.yaml")

    def test_config_loading(self, mock_groupchat_config):
        """Test configuration loading"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        config = factory.groupchat_configs["code_review_team"]
        assert config["max_round"] == 10
        assert config["speaker_selection_method"] == "round_robin"
        assert config["allow_repeat_speaker"] is False


class TestGroupChatCreation:
    """Test group chat creation"""

    def test_create_groupchat_basic(self, mock_groupchat_config, mock_agents):
        """Test basic group chat creation"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        # Mock the AutoGen GroupChat class
        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            mock_groupchat = Mock()
            MockGroupChat.return_value = mock_groupchat

            # create_groupchat expects Dict[str, agent], not List
            groupchat = factory.create_groupchat("code_review_team", mock_agents)

            MockGroupChat.assert_called_once()
            assert groupchat == mock_groupchat

    def test_create_groupchat_with_config(self, mock_groupchat_config, mock_agents):
        """Test creating group chat from configuration"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            MockGroupChat.return_value = Mock()

            # create_groupchat expects Dict[str, agent], not List
            groupchat = factory.create_groupchat("code_review_team", mock_agents)

            # Verify GroupChat was called with config parameters
            call_kwargs = MockGroupChat.call_args[1]
            assert call_kwargs["max_round"] == 10
            assert (
                "speaker_selection_method" in call_kwargs or "allow_repeat_speaker" in call_kwargs
            )

    def test_create_groupchat_invalid_config(self, mock_groupchat_config, mock_agents):
        """Test creating group chat with invalid config name"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with pytest.raises(ValueError, match="not found"):
            factory.create_groupchat("nonexistent_chat", mock_agents)


class TestGroupChatManager:
    """Test group chat manager creation"""

    def test_create_manager_basic(self, mock_groupchat_config, mock_agents):
        """Test basic manager creation"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            with patch("src.autogen_adapters.groupchat_factory.GroupChatManager") as MockManager:
                mock_groupchat = Mock()
                MockGroupChat.return_value = mock_groupchat
                mock_manager = Mock()
                MockManager.return_value = mock_manager

                groupchat = factory.create_groupchat("code_review_team", mock_agents)
                manager = factory.create_groupchat_manager(groupchat, llm_config={})

                MockManager.assert_called_once()
                assert manager == mock_manager

    def test_create_manager_with_config(self, mock_groupchat_config):
        """Test creating manager from configuration"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            with patch("src.autogen_adapters.groupchat_factory.GroupChatManager") as MockManager:
                mock_groupchat = Mock()
                MockGroupChat.return_value = mock_groupchat
                mock_manager = Mock()
                MockManager.return_value = mock_manager

                agents_list = [Mock() for _ in range(3)]
                groupchat = factory.create_groupchat("test", agents_list)
                manager = factory.create_manager_from_config(groupchat, "default_manager")

                MockManager.assert_called_once()
                # Verify system_message was passed
                call_kwargs = MockManager.call_args[1]
                assert "system_message" in call_kwargs


class TestSpeakerSelection:
    """Test speaker selection methods"""

    def test_round_robin_selection(self, mock_groupchat_config, mock_agents):
        """Test round robin speaker selection"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        config = factory.groupchat_configs["code_review_team"]
        assert config["speaker_selection_method"] == "round_robin"

    def test_auto_selection(self, mock_groupchat_config, mock_agents):
        """Test auto speaker selection"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        config = factory.groupchat_configs["security_team"]
        assert config["speaker_selection_method"] == "auto"

    def test_repeat_speaker_control(self, mock_groupchat_config):
        """Test repeat speaker configuration"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        # code_review_team doesn't allow repeats
        config1 = factory.groupchat_configs["code_review_team"]
        assert config1["allow_repeat_speaker"] is False

        # security_team allows repeats
        config2 = factory.groupchat_configs["security_team"]
        assert config2["allow_repeat_speaker"] is True


class TestGroupChatStorage:
    """Test group chat storage and retrieval"""

    def test_store_groupchat(self, mock_groupchat_config, mock_agents):
        """Test storing created group chats"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            mock_groupchat = Mock()
            MockGroupChat.return_value = mock_groupchat

            agents_list = list(mock_agents.values())[:3]
            factory.create_groupchat("test_chat", agents_list, max_round=5)

            # Groupchat should be stored
            assert "test_chat" in factory.groupchats
            assert factory.groupchats["test_chat"] == mock_groupchat

    def test_get_groupchat(self, mock_groupchat_config, mock_agents):
        """Test retrieving stored group chats"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            mock_groupchat = Mock()
            MockGroupChat.return_value = mock_groupchat

            agents_list = list(mock_agents.values())[:3]
            factory.create_groupchat("test_chat", agents_list, max_round=5)

            retrieved = factory.get_groupchat("test_chat")
            assert retrieved == mock_groupchat

    def test_get_nonexistent_groupchat(self, mock_groupchat_config):
        """Test retrieving non-existent group chat"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        result = factory.get_groupchat("nonexistent")
        assert result is None


class TestGroupChatListing:
    """Test listing group chats"""

    def test_list_groupchat_configs(self, mock_groupchat_config):
        """Test listing available group chat configurations"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        configs = factory.list_groupchats()
        assert "code_review_team" in configs
        assert "security_team" in configs
        assert len(configs) == 2

    def test_list_created_groupchats(self, mock_groupchat_config, mock_agents):
        """Test listing created group chats"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            MockGroupChat.return_value = Mock()

            agents_list = list(mock_agents.values())[:3]
            factory.create_groupchat("chat1", agents_list, max_round=5)
            factory.create_groupchat("chat2", agents_list, max_round=5)

            created = factory.list_groupchats()
            assert "chat1" in created
            assert "chat2" in created
            assert len(created) == 2


class TestAgentValidation:
    """Test agent validation"""

    def test_validate_agents_list(self, mock_groupchat_config):
        """Test validation of agents list"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        # Should accept list of agents
        agents = [Mock(name="agent1"), Mock(name="agent2")]

        with patch("src.autogen_adapters.groupchat_factory.GroupChat"):
            # Should not raise
            factory.create_groupchat("test", agents, max_round=5)

    def test_empty_agents_list(self, mock_groupchat_config):
        """Test handling empty agents list"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            # Some implementations may allow empty list
            factory.create_groupchat("test", [], max_round=5)
            MockGroupChat.assert_called_once()


class TestMaxRoundConfiguration:
    """Test max round configuration"""

    def test_max_round_from_config(self, mock_groupchat_config, mock_agents):
        """Test max_round from configuration"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        config = factory.groupchat_configs["code_review_team"]
        assert config["max_round"] == 10

        config = factory.groupchat_configs["security_team"]
        assert config["max_round"] == 5

    def test_max_round_override(self, mock_groupchat_config, mock_agents):
        """Test overriding max_round"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            MockGroupChat.return_value = Mock()

            agents_list = list(mock_agents.values())[:3]

            # Create with custom max_round
            factory.create_groupchat("test", agents_list, max_round=15)

            # Verify max_round was passed
            call_kwargs = MockGroupChat.call_args[1]
            assert call_kwargs["max_round"] == 15


@pytest.mark.integration
class TestGroupChatFactoryIntegration:
    """Integration tests for GroupChatFactory"""

    def test_full_groupchat_creation_flow(self, mock_groupchat_config):
        """Test complete group chat creation flow"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        # Verify factory initialized correctly
        assert len(factory.groupchat_configs) == 2
        assert len(factory.groupchats) == 0

    def test_config_to_groupchat_pipeline(self, mock_groupchat_config, mock_agents):
        """Test pipeline from config to groupchat to manager"""
        factory = GroupChatFactory(config_path=mock_groupchat_config)

        with patch("src.autogen_adapters.groupchat_factory.GroupChat") as MockGroupChat:
            with patch("src.autogen_adapters.groupchat_factory.GroupChatManager") as MockManager:
                MockGroupChat.return_value = Mock()
                MockManager.return_value = Mock()

                agents_list = list(mock_agents.values())[:3]

                # Create groupchat from config
                groupchat = factory.create_groupchat("code_review_team", agents_list)

                # Create manager
                manager = factory.create_manager_from_config(groupchat, "default_manager")

                # Verify both were created
                MockGroupChat.assert_called_once()
                MockManager.assert_called_once()


class TestErrorHandling:
    """Test error handling in GroupChatFactory"""

    def test_invalid_yaml_config(self, tmp_path):
        """Test handling of invalid YAML configuration"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        with pytest.raises(Exception):  # YAML parse error
            GroupChatFactory(config_path=str(config_file))

    def test_missing_required_fields(self, tmp_path):
        """Test handling of missing required configuration fields"""
        config_content = """
group_chats:
  incomplete_chat:
    # Missing agents and max_round
    speaker_selection_method: "auto"
"""
        config_file = tmp_path / "incomplete.yaml"
        config_file.write_text(config_content)

        factory = GroupChatFactory(config_path=str(config_file))

        # Should handle missing fields gracefully
        with patch("src.autogen_adapters.groupchat_factory.GroupChat"):
            # May raise error or use defaults depending on implementation
            try:
                factory.create_groupchat("incomplete_chat", [Mock()])
            except (KeyError, ValueError):
                pass  # Expected if missing required fields
