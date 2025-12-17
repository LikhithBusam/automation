# AutoGen Migration Guide

## Overview

This guide documents the migration of the Intelligent Development Assistant from CrewAI framework to Microsoft AutoGen framework. The migration maintains all core functionality while leveraging AutoGen's unique capabilities for multi-agent conversations, code execution, and human-in-the-loop interactions.

## What Has Been Created

### 1. Configuration Files

#### `config/autogen_agents.yaml`
Defines all AutoGen agents with OpenRouter LLM configurations:

**Agent Types:**
- **TeachableAgent**: `code_analyzer` - Learns coding patterns over time
- **AssistantAgent**: `security_auditor`, `documentation_agent`, `deployment_agent`, `research_agent`, `project_manager`
- **UserProxyAgent**: `user_proxy_executor` - Handles function execution and code running

**Key Features:**
- OpenRouter API integration for all models
- Configurable LLM settings per agent
- Custom system messages for each role
- Human input modes (NEVER, TERMINATE, ALWAYS)
- Code execution configuration
- Teachability settings for learning agents

#### `config/autogen_groupchats.yaml`
Defines multi-agent conversation patterns:

**Group Chats:**
- `code_review_chat`: Code Analyzer + Security Auditor + Project Manager
- `security_audit_chat`: Deep security analysis
- `documentation_chat`: Documentation generation
- `deployment_chat`: Safe deployment with validation
- `research_chat`: Technology research
- `full_team_chat`: All specialists collaborate

**Features:**
- Speaker selection methods (auto, manual, round_robin, random)
- Custom termination conditions
- Max rounds per conversation
- Admin/manager assignment

#### `config/autogen_workflows.yaml`
Defines conversation-based workflows:

**Workflow Types:**
1. **Group Chat Workflows**:
   - `code_analysis`: Comprehensive code review
   - `security_audit`: Security vulnerability assessment
   - `documentation_generation`: Create docs
   - `deployment`: Execute deployments
   - `research`: Technology research

2. **Two-Agent Workflows**:
   - `quick_code_review`: Fast review for small changes
   - `quick_documentation`: Quick doc updates

3. **Nested Conversations**:
   - `comprehensive_feature_review`: Multi-perspective analysis with sub-tasks

**Features:**
- Message templates with variables
- Termination keywords
- Human approval points
- Conversation persistence
- Summary methods

#### `config/function_schemas.yaml`
Maps MCP server operations to AutoGen function calling:

**Tool Categories:**
- **GitHub Operations**: PR creation, issue management, code search
- **Filesystem Operations**: Read, write, list, search files
- **Memory Operations**: Store, retrieve, search memories
- **Slack Operations**: Send messages and notifications

**Features:**
- Full function schemas for AutoGen
- Parameter validation
- Agent-function registration mapping
- Execution routing to UserProxyAgent
- Error handling and retry configuration

## Architecture Changes

### From CrewAI to AutoGen

| Aspect | CrewAI | AutoGen |
|--------|--------|---------|
| **Execution Model** | Task-based | Conversation-based |
| **Agent Coordination** | Crew class | GroupChat + GroupChatManager |
| **Tool Integration** | CrewAI Tools | Function Calling |
| **Agent Types** | Generic Agent | AssistantAgent, UserProxyAgent, TeachableAgent |
| **Workflow Definition** | Task DAGs | Conversation patterns |
| **Human Interaction** | Limited | Built-in modes (NEVER, TERMINATE, ALWAYS) |

### New Capabilities with AutoGen

1. **Code Execution**: Safe code execution via UserProxyAgent (Docker or local)
2. **Human-in-the-Loop**: Multiple interaction modes with approval gates
3. **Teachable Agents**: Agents learn from conversations and remember patterns
4. **Conversation Persistence**: Save, resume, and audit conversations
5. **Dynamic Speaker Selection**: AI-driven or custom speaker selection logic
6. **Nested Conversations**: Hierarchical task breakdown with sub-conversations

## OpenRouter Integration

All models use OpenRouter API for flexibility and cost-effectiveness:

### Model Assignments

| Agent | Model | Purpose |
|-------|-------|---------|
| Code Analyzer | `qwen/qwen-2.5-coder-32b-instruct` | Code analysis, pattern detection |
| Security Auditor | `qwen/qwen-2.5-coder-32b-instruct` | Security vulnerability assessment |
| Documentation Agent | `meta-llama/llama-3.1-70b-instruct` | Technical writing |
| Deployment Agent | `anthropic/claude-3.5-sonnet` | Critical deployment operations |
| Research Agent | `google/gemini-pro-1.5` | Technology research |
| Project Manager | `anthropic/claude-3.5-sonnet` | Coordination and decision-making |
| Routing/Manager | `openai/gpt-4o-mini` | Fast routing decisions |

### Benefits
- No local model downloads (immediate startup)
- Access to best-in-class models for each task
- Cost-effective with free tier models available
- Fallback model configurations
- Easy model swapping via configuration

## Migration Steps (To Complete)

### Phase 1: Core Implementation ✅ (Configuration Done)
- [x] Create AutoGen agent configurations
- [x] Define GroupChat patterns
- [x] Design workflow templates
- [x] Map MCP tools to functions

### Phase 2: Code Implementation (In Progress)
- [ ] Implement `src/autogen_adapters/agent_factory.py`
- [ ] Implement `src/autogen_adapters/groupchat_factory.py`
- [ ] Implement `src/autogen_adapters/function_registry.py`
- [ ] Implement `src/autogen_adapters/conversation_manager.py`

### Phase 3: MCP Tool Wrappers
- [ ] Create AutoGen function wrappers for GitHub MCP
- [ ] Create AutoGen function wrappers for Filesystem MCP
- [ ] Create AutoGen function wrappers for Memory MCP
- [ ] Create AutoGen function wrappers for Slack MCP

### Phase 4: Integration
- [ ] Update `main.py` for AutoGen workflows
- [ ] Integrate TeachableAgent with existing memory system
- [ ] Implement conversation persistence
- [ ] Add human approval workflows

### Phase 5: Testing
- [ ] Test individual agent functionality
- [ ] Test GroupChat conversations
- [ ] Test function calling integration
- [ ] Test workflow execution
- [ ] Load testing and optimization

## Key Files to Implement

### 1. `src/autogen_adapters/agent_factory.py`

```python
class AutoGenAgentFactory:
    """
    Creates AutoGen agents from YAML configuration.

    Features:
    - Load agent configs from autogen_agents.yaml
    - Create AssistantAgent, UserProxyAgent, TeachableAgent instances
    - Configure LLM connections to OpenRouter
    - Register functions with agents
    - Setup teachability for learning agents
    """
```

### 2. `src/autogen_adapters/groupchat_factory.py`

```python
class GroupChatFactory:
    """
    Creates GroupChat instances from configuration.

    Features:
    - Load groupchat configs from autogen_groupchats.yaml
    - Create GroupChat with specified agents
    - Configure speaker selection methods
    - Setup termination conditions
    - Create GroupChatManager instances
    """
```

### 3. `src/autogen_adapters/function_registry.py`

```python
class FunctionRegistry:
    """
    Registers MCP tool operations as AutoGen functions.

    Features:
    - Load function schemas from function_schemas.yaml
    - Create async wrapper functions for MCP calls
    - Register functions with specified agents
    - Setup execution routing to UserProxyAgent
    - Configure error handling and retries
    """
```

### 4. `src/autogen_adapters/conversation_manager.py`

```python
class ConversationManager:
    """
    Manages conversation lifecycle and execution.

    Features:
    - Execute workflows from autogen_workflows.yaml
    - Handle conversation persistence
    - Manage conversation resumption
    - Process human approval points
    - Generate conversation summaries
    """
```

## Environment Variables

Add these to your `.env` file:

```env
# OpenRouter API (already configured)
OPENROUTER_API_KEY=sk-or-v1-...

# AutoGen Specific
AUTOGEN_USE_DOCKER=false
AUTOGEN_DOCKER_IMAGE=python:3.11-slim
AUTOGEN_WORK_DIR=./workspace/code_execution
AUTOGEN_MAX_CONSECUTIVE_AUTO_REPLY=10
AUTOGEN_HUMAN_INPUT_TIMEOUT=300

# Teachability
TEACHABLE_DB_PATH=./data/teachable
TEACHABLE_RECALL_THRESHOLD=1.5
TEACHABLE_MAX_RETRIEVALS=10

# Conversation Management
CONVERSATION_STORAGE_PATH=./data/conversations
CONVERSATION_CHECKPOINT_PATH=./data/checkpoints
CONVERSATION_AUTO_SAVE=true
CONVERSATION_RETENTION_DAYS=90

# Data Directories
DATA_DIR=./data
WORKSPACE_DIR=./workspace
```

## Usage Examples

### Example 1: Code Review Workflow

```python
from src.autogen_adapters.conversation_manager import ConversationManager

# Initialize
manager = ConversationManager(config_path="config/autogen_workflows.yaml")

# Execute code review
result = await manager.execute_workflow(
    workflow_name="code_analysis",
    variables={
        "code_path": "./src/models",
        "additional_requirements": "Focus on security and performance"
    }
)

print(result.summary)
```

### Example 2: Deployment with Human Approval

```python
# Execute deployment workflow
result = await manager.execute_workflow(
    workflow_name="deployment",
    variables={
        "environment": "production",
        "version": "v2.0.0",
        "strategy": "blue-green",
        "run_tests": "true",
        "notify": "true"
    }
)

# Human will be prompted for approval at critical points
```

### Example 3: Research with Nested Conversations

```python
# Comprehensive feature review with sub-tasks
result = await manager.execute_workflow(
    workflow_name="comprehensive_feature_review",
    variables={
        "feature_path": "./src/new_feature"
    }
)

# This spawns 3 sub-conversations:
# 1. Code quality check
# 2. Security audit
# 3. Documentation review
# Then aggregates results
```

## MCP Servers (No Changes Required)

The existing MCP servers remain unchanged:
- `mcp_servers/github_server.py` (Port 3000)
- `mcp_servers/filesystem_server.py` (Port 3001)
- `mcp_servers/memory_server.py` (Port 3002)
- `mcp_servers/slack_server.py` (Port 3003)

Only the **client-side wrappers** need to be created as AutoGen functions.

## Benefits of This Migration

### 1. **Better Conversation Flow**
- Natural multi-agent discussions
- Dynamic speaker selection based on context
- Automatic conversation termination

### 2. **Enhanced Capabilities**
- Code execution for automated testing
- Human approval for critical operations
- Agent learning and adaptation over time

### 3. **Improved Flexibility**
- Easy model swapping via configuration
- Access to best-in-class models via OpenRouter
- No local model management overhead

### 4. **Production Ready**
- Conversation auditing and persistence
- Graceful error handling
- Resume interrupted workflows
- Scalable architecture

## Next Steps

1. **Install AutoGen**:
   ```bash
   pip install pyautogen
   pip install pyautogen[teachable]
   ```

2. **Implement Core Adapters**:
   - Start with `agent_factory.py`
   - Then `function_registry.py`
   - Then `groupchat_factory.py`
   - Finally `conversation_manager.py`

3. **Test Individual Components**:
   - Test agent creation
   - Test function registration
   - Test GroupChat creation
   - Test workflow execution

4. **Integration Testing**:
   - End-to-end workflow tests
   - MCP tool integration tests
   - Conversation persistence tests

5. **Documentation**:
   - Update main README.md
   - Create usage examples
   - Document best practices

## Troubleshooting

### Common Issues

1. **OpenRouter API Errors**:
   - Verify `OPENROUTER_API_KEY` is set correctly
   - Check model availability on OpenRouter
   - Review rate limits and quotas

2. **Function Calling Issues**:
   - Ensure function schemas are valid
   - Verify MCP servers are running
   - Check function registration

3. **Conversation Not Terminating**:
   - Review termination conditions
   - Check max_round settings
   - Verify termination keywords

4. **TeachableAgent Issues**:
   - Check database path permissions
   - Verify teachability config
   - Review recall threshold settings

## Resources

- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [OpenRouter API](https://openrouter.ai/docs)
- [TeachableAgent Guide](https://microsoft.github.io/autogen/docs/tutorial/teachable-agent)
- [Function Calling in AutoGen](https://microsoft.github.io/autogen/docs/tutorial/tool-use)

## Status

✅ Configuration files created
✅ Architecture designed
✅ OpenRouter integration configured
⏳ Core implementation in progress
⏳ Testing pending

---

**Last Updated**: December 2025
**Version**: 1.0.0
**Status**: Migration In Progress
