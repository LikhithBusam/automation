"""
AutoGen Agent Factory
Creates AutoGen agents from YAML configuration with Gemini and Groq LLM integration
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

# AutoGen imports
try:
    from autogen import AssistantAgent, GroupChatManager, UserProxyAgent

    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False
    AssistantAgent = None
    UserProxyAgent = None
    GroupChatManager = None
    print("Warning: pyautogen not installed. Run: pip install pyautogen")

# Try to import TeachableAgent separately (may not be available in newer versions)
try:
    from autogen.agentchat.contrib.teachable_agent import TeachableAgent

    HAS_TEACHABLE = True
except ImportError:
    try:
        # Try alternative import path for newer versions
        from autogen import TeachableAgent

        HAS_TEACHABLE = True
    except ImportError:
        HAS_TEACHABLE = False
        TeachableAgent = None


class AutoGenAgentFactory:
    """
    Factory for creating AutoGen agents from YAML configuration.

    Features:
    - Load agent configs from autogen_agents.yaml
    - Create AssistantAgent, UserProxyAgent, TeachableAgent instances
    - Configure Gemini and Groq LLM connections
    - Setup teachability for learning agents
    - Register functions with agents
    """

    def __init__(self, config_path: str = "config/autogen_agents.yaml"):
        """
        Initialize the agent factory.

        Args:
            config_path: Path to AutoGen agents configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path

        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config = self._load_config()
        self.llm_configs = self.config.get("llm_configs", {})
        self.agent_configs = self.config.get("agents", {})
        self.manager_configs = self.config.get("group_chat_managers", {})

        # Storage for created agents
        self.agents: Dict[str, Any] = {}
        self.managers: Dict[str, GroupChatManager] = {}

        self.logger.info(f"AgentFactory initialized with {len(self.agent_configs)} agent configs")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Replace environment variable placeholders
        config = self._replace_env_vars(config)

        return config

    def _replace_env_vars(self, obj: Any) -> Any:
        """Recursively replace ${VAR} with environment variables"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Replace ${VAR} patterns
            if obj.startswith("${") and obj.endswith("}"):
                var_name = obj[2:-1]
                return os.getenv(var_name, obj)
            return obj
        return obj

    def _create_llm_config(self, config_name: str) -> Dict[str, Any]:
        """
        Create LLM configuration for AutoGen from config name.
        Supports both Gemini and Groq (OpenAI-compatible) APIs.

        Args:
            config_name: Name of LLM config in llm_configs section

        Returns:
            AutoGen-compatible LLM config dict
        """
        if config_name not in self.llm_configs:
            raise ValueError(f"LLM config '{config_name}' not found in configuration")

        llm_cfg = self.llm_configs[config_name]
        api_type = llm_cfg.get("api_type", "openai")

        # DYNAMIC API TYPE HANDLING - AutoGen format (api_type MUST be inside config_entry)
        # Azure OpenAI specific configuration
        if api_type == "azure":
            config_entry = {
                "model": llm_cfg.get("model"),
                "api_type": "azure",
                "api_key": llm_cfg.get("api_key"),
                "azure_endpoint": llm_cfg.get("azure_endpoint"),
                "api_version": llm_cfg.get("api_version"),
            }
            self.logger.info(f"Using Azure OpenAI: {llm_cfg.get('azure_endpoint')}")

        # Gemini API with LiteLLM routing
        elif api_type == "google" or api_type == "gemini":
            model_name = llm_cfg.get("model")
            if not model_name.startswith("gemini/"):
                model_name = f"gemini/{model_name}"
            config_entry = {
                "model": model_name,
                "api_key": llm_cfg.get("api_key"),
            }

        # OpenAI-compatible APIs (OpenRouter, Groq, etc.)
        else:
            config_entry = {
                "model": llm_cfg.get("model"),
                "api_key": llm_cfg.get("api_key"),
            }
            # Add base_url if specified
            if "base_url" in llm_cfg and llm_cfg["base_url"]:
                config_entry["base_url"] = llm_cfg["base_url"]

        autogen_config = {
            "config_list": [config_entry],
            "temperature": llm_cfg.get("temperature", 0.7),
            "max_tokens": llm_cfg.get("max_tokens", 2048),
            "timeout": llm_cfg.get("timeout", 120),
        }

        # Add cache_seed if specified (for caching responses)
        if "cache_seed" in llm_cfg:
            autogen_config["cache_seed"] = llm_cfg["cache_seed"]

        # Log the config for debugging (hide API key)
        debug_config = {
            k: (
                v
                if k != "config_list"
                else [{**item, "api_key": "***" if "api_key" in item else None} for item in v]
            )
            for k, v in autogen_config.items()
        }
        self.logger.debug(f"Created LLM config for '{config_name}': {debug_config}")

        return autogen_config

    def create_agent(self, agent_name: str) -> Any:
        """
        Create an AutoGen agent from configuration.

        Args:
            agent_name: Name of agent in configuration

        Returns:
            AutoGen agent instance (AssistantAgent, UserProxyAgent, or TeachableAgent)
        """
        if not HAS_AUTOGEN:
            raise RuntimeError("pyautogen is not installed. Run: pip install pyautogen")

        if agent_name in self.agents:
            self.logger.debug(f"Returning cached agent: {agent_name}")
            return self.agents[agent_name]

        if agent_name not in self.agent_configs:
            raise ValueError(f"Agent '{agent_name}' not found in configuration")

        agent_cfg = self.agent_configs[agent_name]
        agent_type = agent_cfg.get("agent_type", "AssistantAgent")

        self.logger.info(f"Creating {agent_type}: {agent_name}")

        # Create appropriate agent type
        if agent_type == "AssistantAgent":
            agent = self._create_assistant_agent(agent_name, agent_cfg)
        elif agent_type == "UserProxyAgent":
            agent = self._create_user_proxy_agent(agent_name, agent_cfg)
        elif agent_type == "TeachableAgent":
            agent = self._create_teachable_agent(agent_name, agent_cfg)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Cache the agent
        self.agents[agent_name] = agent

        self.logger.info(f"Created agent: {agent_name}")
        return agent

    def _create_assistant_agent(self, agent_name: str, agent_cfg: Dict[str, Any]) -> AssistantAgent:
        """Create an AssistantAgent with function calling support"""
        # Get LLM config
        llm_config_name = agent_cfg.get("llm_config")
        llm_config = self._create_llm_config(llm_config_name) if llm_config_name else None

        # Create agent
        agent = AssistantAgent(
            name=agent_cfg.get("name", agent_name),
            system_message=agent_cfg.get("system_message", "You are a helpful AI assistant."),
            llm_config=llm_config,
            human_input_mode=agent_cfg.get("human_input_mode", "NEVER"),
            max_consecutive_auto_reply=agent_cfg.get("max_consecutive_auto_reply", 10),
            code_execution_config=agent_cfg.get("code_execution_config", False),
        )

        # Store agent name for later function schema registration
        agent._agent_config_name = agent_name

        return agent

    def _create_user_proxy_agent(
        self, agent_name: str, agent_cfg: Dict[str, Any]
    ) -> UserProxyAgent:
        """Create a UserProxyAgent"""
        # Get code execution config
        code_exec_cfg = agent_cfg.get("code_execution_config", False)

        # If code_execution_config is a dict, prepare it
        if isinstance(code_exec_cfg, dict):
            code_exec_cfg = {
                "work_dir": code_exec_cfg.get("work_dir", "./workspace/code_execution"),
                "use_docker": code_exec_cfg.get("use_docker", False),
                "timeout": code_exec_cfg.get("timeout", 60),
                "last_n_messages": code_exec_cfg.get("last_n_messages", 3),
            }

        # Create agent
        agent = UserProxyAgent(
            name=agent_cfg.get("name", agent_name),
            system_message=agent_cfg.get("system_message", ""),
            human_input_mode=agent_cfg.get("human_input_mode", "NEVER"),
            max_consecutive_auto_reply=agent_cfg.get("max_consecutive_auto_reply", 5),
            code_execution_config=code_exec_cfg,
        )

        return agent

    def _create_teachable_agent(self, agent_name: str, agent_cfg: Dict[str, Any]):
        """Create a TeachableAgent (for learning agents)"""
        if not HAS_TEACHABLE or not TeachableAgent:
            self.logger.warning(
                f"TeachableAgent not available, creating AssistantAgent instead for {agent_name}"
            )
            # Fallback to regular AssistantAgent if TeachableAgent is not available
            return self._create_assistant_agent(agent_name, agent_cfg)

        # Get LLM config
        llm_config_name = agent_cfg.get("llm_config")
        llm_config = self._create_llm_config(llm_config_name) if llm_config_name else None

        # Get teachability config
        teach_cfg = agent_cfg.get("teachability_config", {})

        # Create base agent first
        agent = TeachableAgent(
            name=agent_cfg.get("name", agent_name),
            system_message=agent_cfg.get("system_message", "You are a helpful AI assistant."),
            llm_config=llm_config,
            human_input_mode=agent_cfg.get("human_input_mode", "NEVER"),
            max_consecutive_auto_reply=agent_cfg.get("max_consecutive_auto_reply", 10),
        )

        # Configure teachability
        if teach_cfg:
            # TeachableAgent uses a database path for storage
            db_path = teach_cfg.get("db_path", "./data/teachable")

            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            # Note: TeachableAgent's learn method is called during conversations
            # The actual learning happens through the conversation flow

        return agent

    def create_all_agents(self, function_registry=None) -> Dict[str, Any]:
        """
        Create all agents from configuration.

        Args:
            function_registry: Optional FunctionRegistry for adding tools to llm_config

        Returns:
            Dictionary of agent_name -> agent instance
        """
        for agent_name in self.agent_configs.keys():
            try:
                agent = self.create_agent(agent_name)

                # Add function/tool schemas to AssistantAgent's llm_config
                if function_registry and hasattr(agent, "llm_config") and agent.llm_config:
                    tools = function_registry.get_tools_for_llm_config(agent_name)
                    if tools:
                        agent.llm_config["tools"] = tools
                        self.logger.info(f"Added {len(tools)} tools to llm_config for {agent_name}")
            except Exception as e:
                self.logger.error(f"Failed to create agent {agent_name}: {e}")

        self.logger.info(f"Created {len(self.agents)} agents")
        return self.agents

    def get_agent(self, agent_name: str) -> Optional[Any]:
        """
        Get a created agent by name.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_name)

    def list_agents(self) -> List[str]:
        """
        List all created agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())

    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dict or None
        """
        return self.agent_configs.get(agent_name)


# Convenience function
def create_agent_factory(config_path: str = "config/autogen_agents.yaml") -> AutoGenAgentFactory:
    """
    Create an AutoGenAgentFactory instance.

    Args:
        config_path: Path to configuration file

    Returns:
        AutoGenAgentFactory instance
    """
    return AutoGenAgentFactory(config_path)
