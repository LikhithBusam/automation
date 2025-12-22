"""
AutoGen Conversation Manager
Manages conversation lifecycle and workflow execution
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.autogen_adapters.agent_factory import AutoGenAgentFactory
from src.autogen_adapters.function_registry import FunctionRegistry
from src.autogen_adapters.groupchat_factory import GroupChatFactory


@dataclass
class ConversationResult:
    """Result of a conversation/workflow execution"""

    workflow_name: str
    status: str  # success, partial, failed
    messages: List[Dict[str, Any]]
    summary: str
    duration_seconds: float
    tasks_completed: int
    tasks_failed: int
    error: Optional[str] = None


class ConversationManager:
    """
    Manages conversation lifecycle and workflow execution.

    Features:
    - Execute workflows from autogen_workflows.yaml
    - Handle conversation persistence
    - Manage conversation resumption
    - Process human approval points
    - Generate conversation summaries
    """

    def __init__(
        self,
        config_path: str = "config/autogen_workflows.yaml",
        agent_factory: Optional[AutoGenAgentFactory] = None,
        groupchat_factory: Optional[GroupChatFactory] = None,
        function_registry: Optional[FunctionRegistry] = None,
    ):
        """
        Initialize the conversation manager.

        Args:
            config_path: Path to workflows configuration file
            agent_factory: Optional AutoGenAgentFactory instance
            groupchat_factory: Optional GroupChatFactory instance
            function_registry: Optional FunctionRegistry instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path

        # Load configuration
        self.config = self._load_config()
        self.workflow_configs = self.config.get("workflows", {})
        self.conversation_patterns = self.config.get("conversation_patterns", {})
        self.persistence_config = self.config.get("conversation_persistence", {})

        # Initialize factories
        self.agent_factory = agent_factory or AutoGenAgentFactory()
        self.groupchat_factory = groupchat_factory or GroupChatFactory()
        self.function_registry = function_registry or FunctionRegistry()

        # Execution history
        self.history: List[ConversationResult] = []

        self.logger.info(
            f"ConversationManager initialized with {len(self.workflow_configs)} workflows"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config

    async def initialize(self):
        """Initialize all components"""
        self.logger.info("Initializing ConversationManager components...")

        # Initialize function registry and MCP tools
        await self.function_registry.initialize_tools()

        # Create all agents with function schemas in llm_config
        self.agent_factory.create_all_agents(function_registry=self.function_registry)

        # Register functions with agents
        await self._register_functions_with_agents()

        self.logger.info("ConversationManager initialization complete")

    async def _register_functions_with_agents(self):
        """Register MCP tool functions with appropriate agents"""
        for agent_name in self.agent_factory.list_agents():
            agent = self.agent_factory.get_agent(agent_name)

            if agent:
                # Register functions for this agent
                self.function_registry.register_functions_with_agent(agent, agent_name)
                self.logger.info(f"Registered functions with agent: {agent_name}")

    def _replace_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Replace {variable} placeholders in template.

        Args:
            template: Template string
            variables: Dictionary of variable_name -> value

        Returns:
            String with variables replaced
        """
        result = template

        for key, value in variables.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))

        return result

    async def execute_workflow(
        self, workflow_name: str, variables: Optional[Dict[str, Any]] = None
    ) -> ConversationResult:
        """
        Execute a workflow from configuration.

        Args:
            workflow_name: Name of workflow to execute
            variables: Variables to substitute in templates

        Returns:
            ConversationResult with execution details
        """
        if workflow_name not in self.workflow_configs:
            raise ValueError(f"Workflow '{workflow_name}' not found in configuration")

        workflow_cfg = self.workflow_configs[workflow_name]
        variables = variables or {}

        start_time = datetime.now()

        try:
            # Get workflow type
            workflow_type = workflow_cfg.get("type", "group_chat")

            if workflow_type == "group_chat":
                result = await self._execute_groupchat_workflow(
                    workflow_name, workflow_cfg, variables
                )
            elif workflow_type == "two_agent":
                result = await self._execute_two_agent_workflow(
                    workflow_name, workflow_cfg, variables
                )
            elif workflow_type == "nested_chat":
                result = await self._execute_nested_workflow(workflow_name, workflow_cfg, variables)
            else:
                raise ValueError(f"Unknown workflow type: {workflow_type}")

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            result.duration_seconds = duration

            # Add to history
            self.history.append(result)

            self.logger.info(f"Workflow '{workflow_name}' completed in {duration:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Workflow '{workflow_name}' failed: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            result = ConversationResult(
                workflow_name=workflow_name,
                status="failed",
                messages=[],
                summary=f"Workflow failed: {str(e)}",
                duration_seconds=duration,
                tasks_completed=0,
                tasks_failed=1,
                error=str(e),
            )

            self.history.append(result)
            return result

    async def _execute_groupchat_workflow(
        self, workflow_name: str, workflow_cfg: Dict[str, Any], variables: Dict[str, Any]
    ) -> ConversationResult:
        """Execute a group chat workflow"""
        # Get groupchat configuration
        groupchat_name = workflow_cfg.get("group_chat_config")

        if not groupchat_name:
            raise ValueError(f"No group_chat_config specified for workflow '{workflow_name}'")

        # Get initial message template
        message_template = workflow_cfg.get("initial_message_template", "")
        initial_message = self._replace_variables(message_template, variables)

        # Get agents
        agents = self.agent_factory.agents

        # Get LLM config for manager (use a routing config)
        llm_config = self.agent_factory._create_llm_config("routing_config")

        # Create groupchat and manager
        manager = self.groupchat_factory.create_groupchat_manager(
            groupchat_name, agents, llm_config
        )

        # Get termination keywords
        termination_keywords = workflow_cfg.get("termination_keywords", ["TERMINATE"])

        # Execute conversation
        messages = []

        try:
            # Get the first agent to initiate
            groupchat = self.groupchat_factory.get_groupchat(groupchat_name)
            if groupchat and groupchat.agents:
                initiator = groupchat.agents[0]

                # Start the actual conversation
                max_turns = workflow_cfg.get("max_turns", 10)

                # Initiate the group chat
                chat_result = initiator.initiate_chat(
                    manager, message=initial_message, max_turns=max_turns
                )

                # Extract messages from chat history
                messages = []
                if hasattr(chat_result, "chat_history"):
                    messages = chat_result.chat_history
                elif hasattr(manager, "chat_messages") and manager.chat_messages:
                    # Get messages from the manager
                    for agent_name, agent_messages in manager.chat_messages.items():
                        messages.extend(agent_messages)

                # Get summary
                summary_method = workflow_cfg.get("summary_method", "last")
                if summary_method == "reflection_with_llm" and messages:
                    # Use the last message as summary
                    summary = messages[-1].get(
                        "content", f"GroupChat workflow '{workflow_name}' executed"
                    )
                else:
                    summary = f"GroupChat workflow '{workflow_name}' completed with {len(messages)} messages"

                status = "success"
                tasks_completed = 1

        except Exception as e:
            self.logger.error(f"GroupChat execution error: {e}")
            summary = f"Error: {str(e)}"
            status = "failed"
            tasks_completed = 0

        return ConversationResult(
            workflow_name=workflow_name,
            status=status,
            messages=messages,
            summary=summary,
            duration_seconds=0,  # Will be set by caller
            tasks_completed=tasks_completed,
            tasks_failed=0 if status == "success" else 1,
        )

    async def _execute_two_agent_workflow(
        self, workflow_name: str, workflow_cfg: Dict[str, Any], variables: Dict[str, Any]
    ) -> ConversationResult:
        """Execute a two-agent conversation workflow"""
        agent_names = workflow_cfg.get("agents", [])

        if len(agent_names) != 2:
            raise ValueError(
                f"Two-agent workflow requires exactly 2 agents, got {len(agent_names)}"
            )

        # Get agents
        agent1 = self.agent_factory.get_agent(agent_names[0])
        agent2 = self.agent_factory.get_agent(agent_names[1])

        if not agent1 or not agent2:
            raise ValueError(f"Failed to get agents: {agent_names}")

        # Get initial message
        message_template = workflow_cfg.get("initial_message_template", "")
        initial_message = self._replace_variables(message_template, variables)

        # Get max turns
        max_turns = workflow_cfg.get("max_turns", 5)

        # Execute actual two-agent conversation
        messages = []
        try:
            chat_result = agent1.initiate_chat(agent2, message=initial_message, max_turns=max_turns)

            # Extract messages from chat history
            if hasattr(chat_result, "chat_history"):
                messages = chat_result.chat_history
            elif hasattr(agent1, "chat_messages") and agent1.chat_messages:
                # Get messages from agent1
                for agent_name, agent_messages in agent1.chat_messages.items():
                    messages.extend(agent_messages)

            summary = f"Two-agent conversation between {agent_names[0]} and {agent_names[1]} completed with {len(messages)} messages"
            status = "success"
        except Exception as e:
            self.logger.error(f"Two-agent conversation error: {e}")
            summary = f"Error: {str(e)}"
            status = "failed"

        return ConversationResult(
            workflow_name=workflow_name,
            status=status,
            messages=messages,
            summary=summary,
            duration_seconds=0,
            tasks_completed=1 if status == "success" else 0,
            tasks_failed=0 if status == "success" else 1,
        )

    async def _execute_nested_workflow(
        self, workflow_name: str, workflow_cfg: Dict[str, Any], variables: Dict[str, Any]
    ) -> ConversationResult:
        """Execute a nested conversation workflow"""
        child_conversations = workflow_cfg.get("child_conversations", [])

        all_messages = []
        tasks_completed = 0
        tasks_failed = 0

        # Execute each child conversation
        for child_cfg in child_conversations:
            child_type = child_cfg.get("type", "two_agent")
            child_name = child_cfg.get("name", f"child_{tasks_completed}")

            try:
                if child_type == "two_agent":
                    result = await self._execute_two_agent_workflow(
                        child_name, child_cfg, variables
                    )
                    all_messages.extend(result.messages)
                    tasks_completed += 1
            except Exception as e:
                self.logger.error(f"Child conversation '{child_name}' failed: {e}")
                tasks_failed += 1

        summary = f"Nested workflow with {tasks_completed} completed, {tasks_failed} failed"

        return ConversationResult(
            workflow_name=workflow_name,
            status="success" if tasks_failed == 0 else "partial",
            messages=all_messages,
            summary=summary,
            duration_seconds=0,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
        )

    def get_workflow_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent workflow execution history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of workflow result dictionaries
        """
        recent = self.history[-limit:] if limit > 0 else self.history

        return [
            {
                "workflow_name": r.workflow_name,
                "status": r.status,
                "summary": r.summary,
                "duration_seconds": r.duration_seconds,
                "tasks_completed": r.tasks_completed,
                "tasks_failed": r.tasks_failed,
                "error": r.error,
            }
            for r in recent
        ]

    def list_workflows(self) -> List[str]:
        """
        List all available workflow names.

        Returns:
            List of workflow names
        """
        return list(self.workflow_configs.keys())

    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Workflow configuration dict or None
        """
        return self.workflow_configs.get(workflow_name)


# Convenience function
async def create_conversation_manager(
    config_path: str = "config/autogen_workflows.yaml",
) -> ConversationManager:
    """
    Create and initialize a ConversationManager instance.

    Args:
        config_path: Path to workflows configuration file

    Returns:
        Initialized ConversationManager instance
    """
    manager = ConversationManager(config_path)
    await manager.initialize()
    return manager
