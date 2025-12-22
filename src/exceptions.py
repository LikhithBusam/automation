"""
Standardized Exception Hierarchy for AutoGen Development Assistant

This module provides a unified exception hierarchy for consistent error handling
across the entire application.
"""

from typing import Any, Dict, Optional

# =============================================================================
# Base Exception
# =============================================================================


class AutoGenAssistantError(Exception):
    """
    Base exception for all AutoGen Development Assistant errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "AGENT_001")
            details: Additional error details as a dictionary
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(AutoGenAssistantError):
    """Base class for configuration-related errors"""

    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration is invalid or malformed"""

    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing"""

    pass


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails"""

    pass


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(AutoGenAssistantError):
    """Base class for agent-related errors"""

    pass


class AgentNotFoundError(AgentError):
    """Raised when a requested agent is not found"""

    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails"""

    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails"""

    pass


# =============================================================================
# Workflow Errors
# =============================================================================


class WorkflowError(AutoGenAssistantError):
    """Base class for workflow-related errors"""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a requested workflow is not found"""

    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails"""

    pass


class WorkflowTimeoutError(WorkflowError):
    """Raised when workflow exceeds timeout"""

    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow configuration is invalid"""

    pass


# =============================================================================
# MCP Tool Errors
# =============================================================================


class MCPToolError(AutoGenAssistantError):
    """Base class for MCP tool-related errors"""

    pass


class MCPConnectionError(MCPToolError):
    """Raised when MCP server connection fails"""

    pass


class MCPTimeoutError(MCPToolError):
    """Raised when MCP operation times out"""

    pass


class MCPServerNotFoundError(MCPToolError):
    """Raised when MCP server is not found or not running"""

    pass


class MCPOperationError(MCPToolError):
    """Raised when MCP operation fails"""

    pass


class MCPAuthenticationError(MCPToolError):
    """Raised when MCP authentication fails"""

    pass


# =============================================================================
# Security Errors
# =============================================================================


class SecurityError(AutoGenAssistantError):
    """Base class for security-related errors"""

    pass


class ValidationError(SecurityError):
    """Raised when input validation fails"""

    pass


class AuthenticationError(SecurityError):
    """Raised when authentication fails"""

    pass


class AuthorizationError(SecurityError):
    """Raised when authorization/permission check fails"""

    pass


class RateLimitError(SecurityError):
    """Raised when rate limit is exceeded"""

    pass


class PathTraversalError(ValidationError):
    """Raised when path traversal attack is detected"""

    pass


class InjectionError(ValidationError):
    """Raised when injection attack (SQL, command, etc.) is detected"""

    pass


# =============================================================================
# Model Errors
# =============================================================================


class ModelError(AutoGenAssistantError):
    """Base class for LLM model-related errors"""

    pass


class ModelNotFoundError(ModelError):
    """Raised when requested model is not found"""

    pass


class ModelInitializationError(ModelError):
    """Raised when model initialization fails"""

    pass


class ModelInferenceError(ModelError):
    """Raised when model inference/generation fails"""

    pass


class ModelAPIError(ModelError):
    """Raised when model API call fails"""

    pass


# =============================================================================
# Memory Errors
# =============================================================================


class MemoryError(AutoGenAssistantError):
    """Base class for memory-related errors"""

    pass


class MemoryStorageError(MemoryError):
    """Raised when memory storage operation fails"""

    pass


class MemoryRetrievalError(MemoryError):
    """Raised when memory retrieval operation fails"""

    pass


class MemoryCorruptionError(MemoryError):
    """Raised when memory data is corrupted"""

    pass


# =============================================================================
# Function Registry Errors
# =============================================================================


class FunctionRegistryError(AutoGenAssistantError):
    """Base class for function registry errors"""

    pass


class FunctionNotFoundError(FunctionRegistryError):
    """Raised when a requested function is not found"""

    pass


class FunctionRegistrationError(FunctionRegistryError):
    """Raised when function registration fails"""

    pass


class FunctionExecutionError(FunctionRegistryError):
    """Raised when function execution fails"""

    pass


# =============================================================================
# Conversation Errors
# =============================================================================


class ConversationError(AutoGenAssistantError):
    """Base class for conversation-related errors"""

    pass


class ConversationTimeoutError(ConversationError):
    """Raised when conversation times out"""

    pass


class ConversationTerminatedError(ConversationError):
    """Raised when conversation is terminated unexpectedly"""

    pass


class GroupChatError(ConversationError):
    """Raised when group chat operation fails"""

    pass


# =============================================================================
# Resource Errors
# =============================================================================


class ResourceError(AutoGenAssistantError):
    """Base class for resource-related errors"""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a required resource is not found"""

    pass


class ResourceExhaustedError(ResourceError):
    """Raised when resource is exhausted (e.g., memory, connections)"""

    pass


class ResourceLockError(ResourceError):
    """Raised when resource lock cannot be acquired"""

    pass


# =============================================================================
# Retry and Circuit Breaker Errors
# =============================================================================


class RetryError(AutoGenAssistantError):
    """Raised when operation fails after all retry attempts"""

    pass


class CircuitBreakerError(AutoGenAssistantError):
    """Raised when circuit breaker is open"""

    pass


# =============================================================================
# Error Code Registry
# =============================================================================

ERROR_CODES = {
    # Configuration (CFG-xxx)
    "CFG_001": "Invalid configuration format",
    "CFG_002": "Missing required configuration",
    "CFG_003": "Configuration validation failed",
    # Agent (AGT-xxx)
    "AGT_001": "Agent not found",
    "AGT_002": "Agent initialization failed",
    "AGT_003": "Agent execution failed",
    # Workflow (WFL-xxx)
    "WFL_001": "Workflow not found",
    "WFL_002": "Workflow execution failed",
    "WFL_003": "Workflow timeout",
    "WFL_004": "Workflow validation failed",
    # MCP Tool (MCP-xxx)
    "MCP_001": "MCP connection failed",
    "MCP_002": "MCP operation timeout",
    "MCP_003": "MCP server not found",
    "MCP_004": "MCP operation failed",
    "MCP_005": "MCP authentication failed",
    # Security (SEC-xxx)
    "SEC_001": "Input validation failed",
    "SEC_002": "Authentication failed",
    "SEC_003": "Authorization failed",
    "SEC_004": "Rate limit exceeded",
    "SEC_005": "Path traversal detected",
    "SEC_006": "Injection attack detected",
    # Model (MDL-xxx)
    "MDL_001": "Model not found",
    "MDL_002": "Model initialization failed",
    "MDL_003": "Model inference failed",
    "MDL_004": "Model API error",
    # Memory (MEM-xxx)
    "MEM_001": "Memory storage failed",
    "MEM_002": "Memory retrieval failed",
    "MEM_003": "Memory corruption detected",
    # Function (FNC-xxx)
    "FNC_001": "Function not found",
    "FNC_002": "Function registration failed",
    "FNC_003": "Function execution failed",
    # Conversation (CNV-xxx)
    "CNV_001": "Conversation timeout",
    "CNV_002": "Conversation terminated",
    "CNV_003": "Group chat error",
    # Resource (RSC-xxx)
    "RSC_001": "Resource not found",
    "RSC_002": "Resource exhausted",
    "RSC_003": "Resource lock failed",
}


def get_error_message(error_code: str) -> str:
    """Get error message for error code"""
    return ERROR_CODES.get(error_code, "Unknown error")
