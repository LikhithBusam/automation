"""
AutoGen Function Registry
Registers MCP tool operations as AutoGen functions for function calling
"""

import os
import yaml
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dotenv import load_dotenv

# Import MCP tools
from src.mcp.tool_manager import MCPToolManager
from src.mcp.github_tool import GitHubMCPTool
from src.mcp.filesystem_tool import FilesystemMCPTool
from src.mcp.memory_tool import MemoryMCPTool
from src.mcp.slack_tool import SlackMCPTool


class FunctionRegistry:
    """
    Registry for MCP tool operations as AutoGen functions.

    Features:
    - Load function schemas from function_schemas.yaml
    - Create async wrapper functions for MCP calls
    - Register functions with specified agents
    - Setup execution routing to UserProxyAgent
    - Configure error handling and retries
    """

    def __init__(
        self,
        config_path: str = "config/function_schemas.yaml",
        tool_manager: Optional[MCPToolManager] = None
    ):
        """
        Initialize the function registry.

        Args:
            config_path: Path to function schemas configuration
            tool_manager: MCPToolManager instance (creates new if None)
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path

        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config = self._load_config()
        self.tool_configs = self.config.get("tools", {})
        self.registration_config = self.config.get("function_registration", {})

        # Initialize tool manager
        self.tool_manager = tool_manager or MCPToolManager(
            config=self._load_tool_manager_config()
        )

        # Storage for registered functions
        self.functions: Dict[str, Callable] = {}
        self.function_schemas: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"FunctionRegistry initialized with {len(self.tool_configs)} tool categories")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _load_tool_manager_config(self) -> Dict[str, Any]:
        """Load main configuration for tool manager"""
        main_config_path = Path("config/config.yaml")

        if main_config_path.exists():
            with open(main_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        return {}

    async def initialize_tools(self):
        """Initialize MCP tool manager and connections"""
        await self.tool_manager.initialize()
        self.logger.info("MCP tools initialized")
        
        # Register all MCP tool functions
        self.register_all_functions()
        self.logger.info(f"Registered {len(self.functions)} MCP tool functions")

    def create_function_wrapper(
        self,
        tool_name: str,
        function_config: Dict[str, Any]
    ) -> Callable:
        """
        Create an async wrapper function for an MCP tool operation.

        Args:
            tool_name: Name of the tool (github, filesystem, etc.)
            function_config: Function configuration from YAML

        Returns:
            Async function that calls the MCP tool
        """
        func_name = function_config.get("name")
        wrapper_name = function_config.get("wrapper_function")

        async def wrapper(**kwargs):
            """Wrapper function that calls MCP tool"""
            try:
                self.logger.debug(f"Calling {tool_name}.{func_name} with {kwargs}")

                # Get the appropriate tool
                tool = self.tool_manager.get_tool(tool_name)

                if not tool:
                    raise ValueError(f"Tool '{tool_name}' not found")

                # Call the tool method
                # Map function names to tool methods
                method_mapping = {
                    # GitHub operations
                    "create_pull_request": "create_pull_request",
                    "get_pull_request": "get_pull_request",
                    "create_issue": "create_issue",
                    "search_code": "search_code",
                    "get_file_contents": "get_file_contents",

                    # Filesystem operations
                    "read_file": "read_file",
                    "write_file": "write_file",
                    "list_directory": "list_directory",
                    "search_files": "search_files",

                    # Memory operations
                    "store_memory": "store_memory",
                    "retrieve_memory": "retrieve_memory",
                    "search_memory": "search_memory",

                    # Slack operations
                    "send_slack_message": "send_message",
                    "send_slack_notification": "send_notification",
                }

                method_name = method_mapping.get(func_name)

                if not method_name or not hasattr(tool, method_name):
                    raise AttributeError(f"Method '{func_name}' not found on tool '{tool_name}'")

                method = getattr(tool, method_name)

                # Call the method - handle both sync and async
                if asyncio.iscoroutinefunction(method):
                    result = await method(**kwargs)
                else:
                    # For sync methods, run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: method(**kwargs))

                self.logger.debug(f"Successfully called {tool_name}.{func_name}")
                return result

            except Exception as e:
                self.logger.error(f"Error calling {tool_name}.{func_name}: {e}")
                return {"error": str(e), "function": func_name}

        # Set function metadata
        wrapper.__name__ = func_name
        wrapper.__doc__ = function_config.get("description", f"Call {tool_name}.{func_name}")

        return wrapper

    def register_tool_functions(self, tool_name: str) -> Dict[str, Callable]:
        """
        Register all functions for a specific tool.

        Args:
            tool_name: Name of the tool category (github_operations, etc.)

        Returns:
            Dictionary of function_name -> wrapper function
        """
        if tool_name not in self.tool_configs:
            raise ValueError(f"Tool '{tool_name}' not found in configuration")

        tool_config = self.tool_configs[tool_name]
        functions_config = tool_config.get("functions", {})

        registered = {}

        for func_name, func_config in functions_config.items():
            # Create wrapper function
            base_tool_name = tool_name.replace("_operations", "")
            wrapper = self.create_function_wrapper(base_tool_name, func_config)

            # Store function and schema
            self.functions[func_name] = wrapper
            self.function_schemas[func_name] = func_config.get("schema", {})

            registered[func_name] = wrapper

            self.logger.info(f"Registered function: {func_name}")

        return registered

    def register_all_functions(self) -> Dict[str, Callable]:
        """
        Register all configured tool functions.

        Returns:
            Dictionary of all registered functions
        """
        for tool_name in self.tool_configs.keys():
            try:
                self.register_tool_functions(tool_name)
            except Exception as e:
                self.logger.error(f"Failed to register functions for {tool_name}: {e}")

        self.logger.info(f"Registered {len(self.functions)} functions total")
        return self.functions

    def get_function(self, function_name: str) -> Optional[Callable]:
        """
        Get a registered function by name.

        Args:
            function_name: Name of the function

        Returns:
            Function or None if not found
        """
        return self.functions.get(function_name)

    def get_function_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a function.

        Args:
            function_name: Name of the function

        Returns:
            Function schema dict or None
        """
        return self.function_schemas.get(function_name)

    def get_functions_for_agent(self, agent_name: str) -> Dict[str, Callable]:
        """
        Get all functions that should be registered with a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary of function_name -> function
        """
        agent_functions = {}

        for tool_name, tool_config in self.tool_configs.items():
            functions_config = tool_config.get("functions", {})

            for func_name, func_config in functions_config.items():
                # Check if this function should be registered with this agent
                register_with = func_config.get("register_with", [])

                if agent_name in register_with:
                    if func_name in self.functions:
                        agent_functions[func_name] = self.functions[func_name]

        return agent_functions

    def get_function_schemas_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get all function schemas for a specific agent (for LLM function calling).
        Returns schemas in OpenAI tools format compatible with AutoGen 0.10+

        Args:
            agent_name: Name of the agent

        Returns:
            List of function schema dicts in OpenAI tools format
        """
        schemas = []

        for tool_name, tool_config in self.tool_configs.items():
            functions_config = tool_config.get("functions", {})

            for func_name, func_config in functions_config.items():
                register_with = func_config.get("register_with", [])

                if agent_name in register_with:
                    schema = func_config.get("schema", {})
                    if schema:
                        # Schema is already in correct format from YAML
                        # {"type": "function", "function": {"name": ..., "parameters": ...}}
                        schemas.append(schema)

        self.logger.debug(f"Got {len(schemas)} function schemas for agent: {agent_name}")
        return schemas
    
    def get_tools_for_llm_config(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get function schemas in the format required for llm_config['tools'].
        This is for AutoGen 0.10+ which uses OpenAI tools format.

        Args:
            agent_name: Name of the agent

        Returns:
            List of tool definitions for llm_config
        """
        return self.get_function_schemas_for_agent(agent_name)

    def register_functions_with_agent(self, agent: Any, agent_name: str):
        """
        Register functions with an AutoGen agent.

        Args:
            agent: AutoGen agent instance
            agent_name: Name of the agent
        """
        try:
            from autogen import UserProxyAgent, AssistantAgent
        except ImportError:
            # Fallback if import fails
            UserProxyAgent = type(None)
            AssistantAgent = type(None)
        
        # Get functions for this agent
        agent_functions = self.get_functions_for_agent(agent_name)

        # For UserProxyAgent, register ALL functions for execution
        if isinstance(agent, UserProxyAgent) or agent.__class__.__name__ == 'UserProxyAgent':
            # UserProxyAgent needs all functions to execute them
            all_functions = self.functions.copy()
            if all_functions:
                agent.register_function(function_map=all_functions)
                self.logger.info(f"Registered {len(all_functions)} functions for execution with UserProxyAgent: {agent_name}")
            return

        # For AssistantAgent or other types
        if not agent_functions:
            self.logger.debug(f"No functions to register for agent: {agent_name}")
            return

        # Register each function
        for func_name, func in agent_functions.items():
            try:
                # AutoGen uses register_function method
                if hasattr(agent, 'register_function'):
                    agent.register_function(
                        function_map={func_name: func}
                    )
                    self.logger.info(f"Registered {func_name} for calling with agent: {agent_name}")
            except Exception as e:
                self.logger.error(f"Failed to register {func_name} with {agent_name}: {e}")

    def register_function(self, function_name: str, function: Callable):
        """
        Register a single function.

        Args:
            function_name: Name for the function
            function: The callable function to register
        """
        self.functions[function_name] = function
        self.logger.info(f"Registered function: {function_name}")

    def execute_function(self, function_name: str, kwargs: Dict[str, Any]) -> Any:
        """
        Execute a registered function with the given parameters.

        Args:
            function_name: Name of the function to execute
            kwargs: Keyword arguments to pass to the function

        Returns:
            Result from the function execution

        Raises:
            ValueError: If function not found
        """
        if function_name not in self.functions:
            raise ValueError(f"Function '{function_name}' not found in registry")

        func = self.functions[function_name]

        # Handle async functions
        if asyncio.iscoroutinefunction(func):
            # If there's an event loop running, schedule the coroutine
            try:
                loop = asyncio.get_running_loop()
                # Create a task and run it
                future = asyncio.ensure_future(func(**kwargs))
                return asyncio.get_event_loop().run_until_complete(future)
            except RuntimeError:
                # No event loop running, create one
                return asyncio.run(func(**kwargs))
        else:
            # Synchronous function
            return func(**kwargs)

    def list_functions(self) -> List[str]:
        """
        List all registered function names.

        Returns:
            List of function names
        """
        return list(self.functions.keys())


# Convenience function
def create_function_registry(
    config_path: str = "config/function_schemas.yaml",
    tool_manager: Optional[MCPToolManager] = None
) -> FunctionRegistry:
    """
    Create a FunctionRegistry instance.

    Args:
        config_path: Path to function schemas configuration
        tool_manager: Optional MCPToolManager instance

    Returns:
        FunctionRegistry instance
    """
    return FunctionRegistry(config_path, tool_manager)
