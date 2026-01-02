"""
AutoGen GroupChat Factory
Creates GroupChat instances from YAML configuration
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

# AutoGen imports
try:
    from autogen import GroupChat, GroupChatManager

    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False
    GroupChat = None
    GroupChatManager = None
    print("Warning: pyautogen not installed. Run: pip install pyautogen")


class GroupChatFactory:
    """
    Factory for creating AutoGen GroupChat instances from configuration.

    Features:
    - Load groupchat configs from autogen_groupchats.yaml
    - Create GroupChat with specified agents
    - Configure speaker selection methods
    - Setup termination conditions
    - Create GroupChatManager instances
    """

    def __init__(self, config_path: str = "config/autogen_groupchats.yaml"):
        """
        Initialize the GroupChat factory.

        Args:
            config_path: Path to GroupChat configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path

        # Load configuration
        self.config = self._load_config()
        self.groupchat_configs = self.config.get("group_chats", {})
        self.termination_configs = self.config.get("termination_conditions", {})
        self.speaker_selection_configs = self.config.get("speaker_selection_functions", {})

        # Storage for created group chats
        self.groupchats: Dict[str, GroupChat] = {}
        self.managers: Dict[str, GroupChatManager] = {}

        self.logger.info(
            f"GroupChatFactory initialized with {len(self.groupchat_configs)} chat configs"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config

    def _create_termination_function(self, condition_name: str) -> Optional[Callable]:
        """
        Create a termination function from configuration.

        Args:
            condition_name: Name of termination condition

        Returns:
            Callable termination function or None
        """
        if condition_name not in self.termination_configs:
            return None

        condition_cfg = self.termination_configs[condition_name]
        keywords = condition_cfg.get("keywords", [])

        def is_termination_msg(msg: Dict[str, Any]) -> bool:
            """
            Dynamically check if message indicates termination.
            Uses smart matching to avoid false positives from casual mentions.
            """
            content = msg.get("content", "")

            # Handle empty or None content
            if not content:
                return False

            # Convert to string and strip whitespace
            content = str(content).strip()

            # DYNAMIC TERMINATION LOGIC:
            # Only trigger if keyword appears in specific contexts:
            # 1. As the ONLY content (exact match)
            # 2. At the END of a message (final statement)
            # 3. On its own line
            # 4. NOT in explanatory text (e.g., "I will respond with TERMINATE")

            content_upper = content.upper()
            lines = content.split('\n')

            for keyword in keywords:
                keyword_upper = keyword.upper()

                # Check 1: Exact match (entire message is just the keyword)
                if content_upper == keyword_upper:
                    self.logger.info(f"Termination: Exact match for '{keyword}'")
                    return True

                # Check 2: Keyword at the very end of message (last 50 chars)
                if content_upper.endswith(keyword_upper):
                    # Make sure it's not part of a larger word
                    if len(content) == len(keyword) or content[-len(keyword)-1] in [' ', '\n', '.', '!']:
                        self.logger.info(f"Termination: '{keyword}' at message end")
                        return True

                # Check 3: Keyword on its own line at the end
                if lines and lines[-1].strip().upper() == keyword_upper:
                    self.logger.info(f"Termination: '{keyword}' on final line")
                    return True

                # Check 4: Multiple occurrences (forced termination from AutoGen)
                if content_upper.count(keyword_upper) >= 2:
                    # Check if it's bold/emphasized: **KEYWORD**
                    bold_pattern = f"**{keyword_upper}**"
                    if bold_pattern in content_upper:
                        self.logger.info(f"Termination: Multiple '{keyword}' detected (forced)")
                        return True

            # Avoid false positives from explanatory text
            # Examples that should NOT trigger:
            # - "When complete, respond with TERMINATE"
            # - "I will say TERMINATE when done"
            # - "Use TERMINATE to end the workflow"
            explanation_phrases = [
                "RESPOND WITH",
                "WILL SAY",
                "WILL RESPOND",
                "USE ",
                "SAY ",
                "END WITH",
                "REPLY WITH",
                "WHEN DONE",
                "WHEN COMPLETE",
                "TO END",
                "IF NO",
            ]

            for phrase in explanation_phrases:
                if phrase in content_upper:
                    # Check if any keyword appears near this phrase
                    for keyword in keywords:
                        phrase_pos = content_upper.find(phrase)
                        keyword_pos = content_upper.find(keyword.upper())
                        if keyword_pos >= 0 and abs(keyword_pos - phrase_pos) < 50:
                            # Keyword is being explained, not executed
                            return False

            return False

        return is_termination_msg

    def create_groupchat(
        self, chat_name: str, agents: Dict[str, Any], llm_config: Optional[Dict[str, Any]] = None
    ) -> GroupChat:
        """
        Create a GroupChat instance from configuration.

        Args:
            chat_name: Name of the group chat
            agents: Dictionary of agent_name -> agent instance
            llm_config: Optional LLM config for the manager

        Returns:
            GroupChat instance
        """
        if not HAS_AUTOGEN:
            raise RuntimeError("pyautogen is not installed. Run: pip install pyautogen")

        if chat_name in self.groupchats:
            self.logger.debug(f"Returning cached groupchat: {chat_name}")
            return self.groupchats[chat_name]

        if chat_name not in self.groupchat_configs:
            raise ValueError(f"GroupChat '{chat_name}' not found in configuration")

        chat_cfg = self.groupchat_configs[chat_name]

        # Get agent instances
        agent_names = chat_cfg.get("agents", [])
        chat_agents = []

        for agent_name in agent_names:
            if agent_name in agents:
                chat_agents.append(agents[agent_name])
            else:
                self.logger.warning(f"Agent '{agent_name}' not found for chat '{chat_name}'")

        if not chat_agents:
            raise ValueError(f"No valid agents found for chat '{chat_name}'")

        # Get configuration parameters
        max_round = chat_cfg.get("max_round", 20)
        allow_repeat_speaker = chat_cfg.get("allow_repeat_speaker", False)
        speaker_selection_method = chat_cfg.get("speaker_selection_method", "auto")

        # Create GroupChat with backward compatibility
        # Feature detection: Check if GroupChat accepts allow_repeat_speaker
        import inspect

        groupchat_params = inspect.signature(GroupChat.__init__).parameters

        # Build kwargs dynamically based on what's supported
        groupchat_kwargs = {
            "agents": chat_agents,
            "messages": [],
            "max_round": max_round,
        }

        # Add optional parameters only if supported
        if "allow_repeat_speaker" in groupchat_params:
            groupchat_kwargs["allow_repeat_speaker"] = allow_repeat_speaker
            self.logger.debug(f"Using allow_repeat_speaker={allow_repeat_speaker}")
        else:
            self.logger.debug("allow_repeat_speaker not supported in this AutoGen version")

        if "speaker_selection_method" in groupchat_params:
            groupchat_kwargs["speaker_selection_method"] = speaker_selection_method
            self.logger.debug(f"Using speaker_selection_method={speaker_selection_method}")
        else:
            self.logger.debug("speaker_selection_method not supported in this AutoGen version")

        # Create GroupChat with compatible parameters
        groupchat = GroupChat(**groupchat_kwargs)

        # Cache the groupchat
        self.groupchats[chat_name] = groupchat

        self.logger.info(f"Created GroupChat: {chat_name} with {len(chat_agents)} agents")
        return groupchat

    def create_groupchat_manager(
        self, chat_name: str, agents: Dict[str, Any], llm_config: Dict[str, Any]
    ) -> GroupChatManager:
        """
        Create a GroupChatManager for a group chat.

        Args:
            chat_name: Name of the group chat
            agents: Dictionary of agent_name -> agent instance
            llm_config: LLM configuration for the manager

        Returns:
            GroupChatManager instance
        """
        if not HAS_AUTOGEN:
            raise RuntimeError("pyautogen is not installed. Run: pip install pyautogen")

        if chat_name in self.managers:
            self.logger.debug(f"Returning cached manager: {chat_name}")
            return self.managers[chat_name]

        # Create the group chat first
        groupchat = self.create_groupchat(chat_name, agents, llm_config)

        # Get manager configuration
        chat_cfg = self.groupchat_configs[chat_name]
        manager_name = chat_cfg.get("manager", f"{chat_name}_manager")

        # Get termination condition
        termination_condition_name = chat_cfg.get("termination_condition")
        termination_func = None

        if termination_condition_name:
            termination_func = self._create_termination_function(termination_condition_name)
            self.logger.debug(f"Using termination condition: {termination_condition_name}")

        # Create manager with termination function
        manager_kwargs = {"groupchat": groupchat, "llm_config": llm_config, "name": manager_name}

        # Add is_termination_msg if we have a termination function
        if termination_func:
            manager_kwargs["is_termination_msg"] = termination_func
            self.logger.debug(f"Manager configured with termination function")

        manager = GroupChatManager(**manager_kwargs)

        # Cache the manager
        self.managers[chat_name] = manager

        self.logger.info(f"Created GroupChatManager: {manager_name} for chat {chat_name}")
        return manager

    def get_groupchat(self, chat_name: str) -> Optional[GroupChat]:
        """
        Get a created GroupChat by name.

        Args:
            chat_name: Name of the group chat

        Returns:
            GroupChat instance or None if not found
        """
        return self.groupchats.get(chat_name)

    def get_manager(self, chat_name: str) -> Optional[GroupChatManager]:
        """
        Get a GroupChatManager by chat name.

        Args:
            chat_name: Name of the group chat

        Returns:
            GroupChatManager instance or None if not found
        """
        return self.managers.get(chat_name)

    def list_groupchats(self) -> List[str]:
        """
        List all configured group chat names.

        Returns:
            List of group chat names
        """
        return list(self.groupchat_configs.keys())

    def get_groupchat_info(self, chat_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a group chat configuration.

        Args:
            chat_name: Name of the group chat

        Returns:
            Group chat configuration dict or None
        """
        return self.groupchat_configs.get(chat_name)


# Convenience function
def create_groupchat_factory(
    config_path: str = "config/autogen_groupchats.yaml",
) -> GroupChatFactory:
    """
    Create a GroupChatFactory instance.

    Args:
        config_path: Path to configuration file

    Returns:
        GroupChatFactory instance
    """
    return GroupChatFactory(config_path)
