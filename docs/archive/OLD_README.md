# Intelligent Development Assistant

A comprehensive AI-powered development assistant built with **Microsoft AutoGen** framework, **Groq API**, and **MCP (Model Context Protocol)** servers using FastMCP.

## 🚀 Features

- **Multi-Agent System**: AutoGen-powered agents with conversational AI, human-in-the-loop, and autonomous task execution
- **MCP Integration**: FastMCP-based servers for GitHub, Filesystem, and Memory with rate limiting and caching
- **Workflow Orchestration**: YAML-based workflow definitions with GroupChat, two-agent, and nested execution patterns
- **Groq API**: Fast inference with Llama 3.3 70B, Mixtral 8x7B, and Llama 3.1 8B models
- **Code Analysis**: Automated code review, security auditing, and pattern learning
- **Documentation Generation**: Multi-format docs (Markdown, HTML, RST) with intelligent templates
- **Deployment Automation**: CI/CD pipeline management with rollback capabilities
- **Research Agent**: Technology trends, best practices, and competitive analysis
- **Conversation Management**: Persistent conversations, resumption support, and approval workflows
- **Function Registry**: Automatic tool registration with OpenAI-compatible function calling
- **Memory System**: Context storage with semantic search and pattern learning
- **Security**: Path validation, API token management, and comprehensive input validation

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CLI Interface (main.py)                                 │
│         Interactive Mode | Workflows | History | Command Parser              │
└────────────────────────────┬────────────────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
    ┌───────────────────┐                 ┌─────────────────────┐
    │Conversation Manager│◄───────────────►│ Function Registry   │
    │  (AutoGen Core)   │                 │ (MCP Tool Wrapper)  │
    │   • Workflow Exec │                 │   • GitHub Tools    │
    │   • Persistence   │                 │   • Filesystem      │
    │   • Resumption    │                 │   • Memory Tools    │
    │   • Approval Flow │                 │   • Auto-register   │
    └─────────┬─────────┘                 └─────────────────────┘
              │
    ┌─────────┴────────────────────────────────────────────┐
    │              AutoGen Agent Layer                      │
    │  ┌──────────┬───────────┬──────────┬──────────┐      │
    │  │   Code   │   Docs    │  Deploy  │ Research │      │
    │  │ Analyzer │   Agent   │   Agent  │  Agent   │      │
    │  │ • Review │ • Generate│ • CI/CD  │ • Trends │      │
    │  │ • Audit  │ • Convert │ • Deploy │ • Best   │      │
    │  │ • Pattern│ • Template│ • K8s    │  Practice│      │
    │  └────┬─────┴─────┬─────┴────┬─────┴────┬─────┘      │
    │       │           │          │          │            │
    │       └───────────┴────┬─────┴──────────┘            │
    │                        ▼                             │
    │              ┌──────────────────┐                    │
    │              │ Project Manager  │                    │
    │              │  (Coordinator)   │                    │
    │              │ • Task Routing   │                    │
    │              │ • GroupChat Mgmt │                    │
    │              └──────────────────┘                    │
    └──────────────────────┬───────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │   MCP Tool Manager  │   │     Groq API        │
    │   • Rate Limiting   │   │   • Llama 3.3 70B  │
    │   • Caching         │   │   • Mixtral 8x7B   │
    │   • Retry Logic     │   │   • Llama 3.1 8B   │
    │   • Fallbacks       │   │   • Fast Inference │
    └──────────┬──────────┘   └─────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐
│ GitHub ││Filesys ││ Memory ││Security│
│ :3000  ││ :3001  ││ :3002  ││  Layer │
└────────┘└────────┘└────────┘└────────┘
```

## 📦 Project Structure

```
automaton/
├── config/
│   ├── config.yaml                  # Main configuration (models, MCP, memory)
│   ├── autogen_agents.yaml          # Agent definitions and capabilities
│   ├── autogen_groupchats.yaml      # GroupChat configurations
│   ├── autogen_workflows.yaml       # Workflow orchestration patterns
│   ├── function_schemas.yaml        # OpenAI function schemas
│   ├── config.production.yaml       # Production settings
│   └── config.production.yaml.example
├── mcp_servers/                     # FastMCP server implementations
│   ├── github_server.py             # GitHub API operations (port 3000)
│   ├── filesystem_server.py         # File system operations (port 3001)
│   └── memory_server.py             # Memory/context storage (port 3002)
├── src/
│   ├── autogen_adapters/            # AutoGen integration layer
│   │   ├── agent_factory.py         # Agent creation from YAML configs
│   │   ├── conversation_manager.py  # Workflow execution & persistence
│   │   ├── groupchat_factory.py     # GroupChat creation & management
│   │   └── function_registry.py     # MCP tool registration
│   ├── autogen_agents/              # Agent-specific implementations
│   │   └── __init__.py
│   ├── autogen_conversations/       # Conversation state & history
│   │   └── __init__.py
│   ├── mcp/                         # MCP tool wrappers
│   │   ├── base_tool.py             # Base with retry/cache/rate-limit
│   │   ├── tool_manager.py          # Central tool orchestrator
│   │   ├── github_tool.py           # GitHub MCP wrapper
│   │   ├── filesystem_tool.py       # Filesystem MCP wrapper
│   │   └── memory_tool.py           # Memory MCP wrapper
│   ├── memory/
│   │   └── memory_manager.py        # Context storage with semantic search
│   ├── models/
│   │   ├── model_factory.py         # OpenRouter LLM integration
│   │   └── openrouter_llm.py        # OpenRouter API client
│   ├── security/
│   │   ├── auth.py                  # Token & API key management
│   │   └── validation.py            # Input validation & sanitization
│   ├── api/
│   │   └── health.py                # Health check endpoints
│   └── utils/
├── examples/
│   └── mcp_integration_example.py   # Usage examples
├── logs/
│   └── autogen_dev_assistant.log    # Application logs
├── state/
│   └── app_state.json               # Application state persistence
├── alembic/                         # Database migrations (if using DB)
│   ├── env.py
│   └── script.py.mako
├── main.py                          # Application entry point (AutoGen)
├── requirements.txt                 # Python dependencies
├── start_mcp_servers.py             # MCP server launcher
├── docker-compose.yml               # Production deployment
├── Dockerfile                       # Container image
└── README.md                        # This file
```
│   ├── models/
│   │   └── model_factory.py      # HF model loading & quantization
│   └── workflows/
│       └── crew_manager.py       # Workflow DAG orchestration
├── examples/
│   └── mcp_integration_example.py # Usage examples
├── test_reports/                 # Generated test reports (JSON/HTML)
├── main.py                       # Application entry point with full CLI
├── requirements.txt              # Python dependencies
├── start_mcp_servers.py          # MCP server launcher
├── test_mcp_servers.py           # Comprehensive MCP test suite
└── README.md                     # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- Git
- Groq API key (for LLM access) - [Get one here](https://console.groq.com/)
- GitHub Personal Access Token (optional, for GitHub operations)
- 4GB+ RAM recommended

### Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd automaton
```

2. **Create virtual environment**:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
# Create .env file
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Groq API (Required for LLM access)
GROQ_API_KEY=your_groq_api_key_here

# GitHub Integration (Optional for GitHub operations)
GITHUB_TOKEN=your_github_personal_access_token

# Workspace Configuration
WORKSPACE_DIR=./workspace
DATA_DIR=./data

# Optional: Slack Integration
SLACK_BOT_TOKEN=your_slack_bot_token
```

5. **Start MCP servers** (in separate terminals or use launcher):

**Option 1: Use the launcher** (Recommended)
```bash
python start_mcp_servers.py
```

**Option 2: Start individually**
```bash
# Terminal 1: GitHub Server
python mcp_servers/github_server.py    # Port 3000

# Terminal 2: Filesystem Server
python mcp_servers/filesystem_server.py # Port 3001

# Terminal 3: Memory Server
python mcp_servers/memory_server.py     # Port 3002
```

6. **Run the application**:
```bash
# Interactive mode
python main.py

# Or with optimized startup script (Windows)
start_optimized.bat

# Linux/Mac
./start_optimized.sh
```

## 🧪 Testing

### MCP Server Health Check

```bash
# Quick health check for all servers
python test_mcp_servers.py --suites health

# Test specific server
python test_mcp_servers.py --suites github
python test_mcp_servers.py --suites filesystem
python test_mcp_servers.py --suites memory
```

### Integration Testing

```bash
# Test AutoGen agent integration
python test_agents.py

# Test MCP integration
python test_mcp_integration.py

# Test configuration
python test_config.py
```

### Comprehensive Test Suite

```bash
# Run all tests with report generation
python test_mcp_servers.py

# Run specific test suites
python test_mcp_servers.py --suites health github filesystem memory

# Load testing with custom concurrency
python test_mcp_servers.py --suites load --concurrent 20

# JSON output only (for CI/CD)
python test_mcp_servers.py --json-only

# Custom report directory
python test_mcp_servers.py --report-dir ./my_reports
```

### Test Suites Available

| Suite | Description |
|-------|-------------|
| `health` | Server connectivity and response times |
| `github` | GitHub API operations (repos, PRs, issues, code search) |
| `filesystem` | File operations with security checks (path traversal, .env blocking) |
| `memory` | Memory CRUD operations (store, retrieve, search, delete) |
| `load` | Concurrent request handling and rate limit testing |
| `integration` | Cross-server workflow tests |

### Test Reports

Reports are generated in JSON and HTML formats:
- `test_reports/test_report_YYYYMMDD_HHMMSS.json` - Machine-readable results
- `test_reports/test_report_YYYYMMDD_HHMMSS.html` - Visual report with styling

## ⚙️ Configuration

### config/config.yaml - Main Configuration

```yaml
# MCP Server Configuration
mcp_servers:
  github:
    enabled: true
    server_url: "http://localhost:3000"
    auth_token: "${GITHUB_TOKEN}"
    rate_limit_minute: 60
    rate_limit_hour: 1000
    cache_enabled: true
    cache_ttl: 300

  filesystem:
    enabled: true
    server_url: "http://localhost:3001"
    allowed_paths:
      - "./workspace"
      - "./projects"
      - "./src"
      - "./config"
      - "./examples"
    blocked_patterns:
      - "\\.\\.\/"  # Directory traversal
      - "\/etc\/"   # System files
      - "\\.env$"   # Environment files
      - "\\.ssh\/"  # SSH keys

  memory:
    enabled: true
    server_url: "http://localhost:3002"
    cache_ttl: 300
    max_context_size: 10000

# MCP Server Configuration
mcp_servers:
  github:
    enabled: true
    server_url: "http://localhost:3000"
    auth_token: "${GITHUB_TOKEN}"
    rate_limit_minute: 60
    rate_limit_hour: 1000
    cache_enabled: true
    cache_ttl: 300

  filesystem:
    enabled: true
    server_url: "http://localhost:3001"
    allowed_paths:
      - "./workspace"
      - "./projects"
      - "./src"
      - "./config"
      - "./examples"
    blocked_patterns:
      - "\\.\\.\/"  # Directory traversal
      - "\/etc\/"   # System files
      - "\\.env$"   # Environment files
      - "\\.ssh\/"  # SSH keys

  memory:
    enabled: true
    server_url: "http://localhost:3002"
    cache_ttl: 300
    max_context_size: 10000

# Memory Configuration
memory:
  backend: "sqlite"  # or "redis", "postgresql"
  path: "./data/memory.db"
  semantic_search: true
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

# Logging Configuration
logging:
  level: "INFO"
  file: "./logs/autogen_dev_assistant.log"
  format: "json"
  max_bytes: 10485760  # 10MB
  backup_count: 5
```

### config/autogen_agents.yaml - Agent Definitions

```yaml
# LLM Configuration Templates (using Groq)
llm_configs:
  code_analysis_config:
    model: "llama-3.3-70b-versatile"
    api_type: "openai"
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"
    temperature: 0.3
    max_tokens: 4096

agents:
  code_analyzer:
    agent_type: "TeachableAgent"
    name: "CodeAnalyzer"
    system_message: "You are a Senior Code Analyst..."
    llm_config: "code_analysis_config"
    human_input_mode: "NEVER"
    max_consecutive_auto_reply: 10
    teachability_config:
      verbosity: 0
      reset_db: false
      db_path: "${DATA_DIR}/teachable/code_analyzer.db"
    tools: ["github", "filesystem"]

  documentation_agent:
    agent_type: "AssistantAgent"
    name: "DocumentationAgent"
    system_message: "You are an expert Technical Writer..."
    llm_config: "documentation_config"
    human_input_mode: "NEVER"
    tools: ["github", "filesystem"]
```

### config/autogen_workflows.yaml - Workflow Definitions

```yaml
workflows:
  code_analysis:
    type: "group_chat"
    group_chat_config: "code_review_chat"
    description: "Comprehensive code quality and security analysis"
    initial_message_template: |
      Please analyze the code at: {code_path}
      
      Analysis requirements:
      - Code quality and maintainability
      - Security vulnerabilities
      - Performance considerations
    message_variables:
      code_path: "${CODE_PATH}"
    max_turns: 20
    termination_keywords: ["TERMINATE", "CODE_REVIEW_COMPLETE"]

  quick_code_review:
    type: "two_agent"
    agents: ["code_analyzer", "user_proxy_executor"]
    description: "Quick code review with two agents"
    max_turns: 10
```

## 🤖 AutoGen Agents

### Agent Architecture

The system uses **Microsoft AutoGen** for multi-agent conversations with:
- **Conversational AI**: Natural language task execution
- **Human-in-the-loop**: Approval workflows and feedback
- **Tool Integration**: MCP servers via function calling
- **State Management**: Conversation persistence and resumption

### Available Agents

| Agent | Role | Capabilities | Tools | Model |
|-------|------|--------------|-------|-------|
| **Code Analyzer** | Senior Code Analyst | Code review, security audits, pattern learning | GitHub, Filesystem | Llama 3.3 70B (Groq) |
| **Security Auditor** | Security Expert | Vulnerability scanning, OWASP compliance | GitHub, Filesystem | Llama 3.3 70B (Groq) |
| **Documentation Agent** | Technical Writer | Generate docs (MD/HTML/RST), API documentation | GitHub, Filesystem | Llama 3.3 70B (Groq) |
| **Deployment Agent** | DevOps Specialist | CI/CD, Kubernetes, Docker, deployments | GitHub, Filesystem, Slack | Mixtral 8x7B (Groq) |
| **Research Agent** | Technology Researcher | Trends, best practices, tech evaluation | Filesystem, Memory | Llama 3.3 70B (Groq) |
| **Project Manager** | Coordinator | Task routing, multi-agent orchestration | All Tools | Mixtral 8x7B (Groq) |
| **Executor** | UserProxyAgent | Function execution, code running | N/A | N/A |

### Agent Features

**AutoGen Capabilities**:
- **GroupChat**: Multi-agent collaboration with speaker selection
- **Sequential Execution**: Step-by-step task processing
- **Parallel Tasks**: Concurrent execution for independent tasks
- **Conversation Resumption**: Continue from saved state
- **Human Approval**: Request user confirmation at key steps
- **Function Calling**: OpenAI-compatible tool integration

**MCP Integration**:
- **Automatic Registration**: Tools from MCP servers auto-register
- **Rate Limiting**: Prevents API throttling
- **Caching**: Reduces redundant MCP calls
- **Retry Logic**: Exponential backoff on failures
- **Security**: Path validation and token management

## 🔧 MCP Servers

MCP (Model Context Protocol) servers provide standardized tool interfaces for AI agents.

### GitHub Server (Port 3000)

**Available Operations**:
```python
# Repository Operations
await github_tool.list_repositories(owner="username")
await github_tool.get_repository(owner="org", repo="project")

# Code Search
await github_tool.search_code(query="async def", owner="org", repo="project")
await github_tool.get_file_contents(owner="org", repo="project", path="src/main.py")

# Pull Requests
await github_tool.create_pull_request(
    owner="org", repo="project",
    title="Feature X", body="Description",
    head="feature-branch", base="main"
)
await github_tool.get_pull_request(owner="org", repo="project", pr_number=42)

# Issues
await github_tool.create_issue(
    owner="org", repo="project",
    title="Bug report", body="Details",
    labels=["bug", "priority-high"]
)

# Commits
await github_tool.get_commits(owner="org", repo="project", branch="main")
```

**Features**:
- Rate limiting (60/min, 1000/hr configurable)
- Response caching (5-minute TTL)
- Retry logic with exponential backoff
- GitHub API v3 compatibility

### Filesystem Server (Port 3001)

**Available Operations**:
```python
# File Operations
await fs_tool.read_file(path="./src/main.py", max_size_mb=10)
await fs_tool.write_file(path="./output/result.txt", content="data")
await fs_tool.delete_file(path="./temp/file.txt", confirm=True)
await fs_tool.get_file_info(path="./README.md")

# Directory Operations
await fs_tool.list_directory(
    path="./src",
    recursive=True,
    filter_code_files=True
)

# Code Search
await fs_tool.search_files(
    path="./src",
    query="async def",
    case_sensitive=False,
    file_pattern="*.py"
)

# Analysis
await fs_tool.analyze_code_structure(path="./src")
```

**Security Features**:
- ✅ Path whitelisting (only allowed directories)
- ✅ Directory traversal prevention (`../` blocked)
- ✅ Sensitive file blocking (`.env`, `.ssh/`, `/etc/`)
- ✅ File size limits (10MB default)
- ✅ Extension filtering for code files
- ✅ Blocked pattern regex matching

**Allowed Paths** (configurable):
- `./workspace`
- `./projects`
- `./src`
- `./config`
- `./examples`

### Memory Server (Port 3002)

**Available Operations**:
```python
# Store Context
await memory_tool.store_context(
    content="FastAPI is great for REST APIs",
    type="pattern",
    metadata={"tags": ["python", "api"], "priority": "high"}
)

# Retrieve by ID
await memory_tool.retrieve_context(memory_id="abc123")

# Semantic Search
await memory_tool.search_context(
    query="best practices for APIs",
    limit=10,
    min_similarity=0.7
)

# Update Memory
await memory_tool.update_context(
    memory_id="abc123",
    content="Updated content",
    tags=["python", "api", "updated"]
)

# Delete
await memory_tool.delete_context(memory_id="abc123")

# List by Type
await memory_tool.list_memories(type="pattern", limit=50)
```

**Memory Types**:
- `pattern`: Code patterns and best practices
- `preference`: User preferences and settings
- `solution`: Problem solutions and fixes
- `context`: General context and knowledge
- `error`: Error patterns and resolutions

**Features**:
- Semantic search with embeddings
- Tag-based filtering
- Metadata support
- TTL-based expiration
- Similarity scoring

## 🧠 Workflow System

### Workflow Patterns

The system supports three execution patterns defined in `config/autogen_workflows.yaml`:

**1. GroupChat Workflows**
```yaml
type: "group_chat"
group_chat_config: "code_review_chat"
agents:
  - code_analyzer
  - security_auditor
  - project_manager
max_turns: 20
```
Agents collaborate dynamically with intelligent speaker selection and auto/manual/round-robin patterns.

**2. Two-Agent Workflows**
```yaml
type: "two_agent"
agents:
  - code_analyzer
  - user_proxy_executor
max_turns: 10
```
Direct conversation between two agents for quick tasks.

**3. Nested Chat Workflows**
```yaml
type: "nested_chat"
child_conversations:
  - type: "two_agent"
    agents: ["code_analyzer", "executor"]
  - type: "two_agent"
    agents: ["security_auditor", "executor"]
```
Sequential execution of multiple two-agent conversations.

### Available Workflows

| Workflow | Pattern | Agents | Description |
|----------|---------|--------|-------------|
| `code_analysis` | GroupChat | Code Analyzer, Security Auditor, PM | Comprehensive code review |
| `security_audit` | GroupChat | Security Auditor, Code Analyzer, PM | Deep security assessment |
| `documentation_generation` | GroupChat | Documentation Agent, Code Analyzer, PM | Generate project docs |
| `deployment` | GroupChat | Deployment Agent, PM, Executor | Deploy to environment |
| `research` | GroupChat | Research Agent, Code Analyzer, PM | Technology research |
| `quick_code_review` | Two-Agent | Code Analyzer, Executor | Fast review for PRs |
| `quick_documentation` | Two-Agent | Documentation Agent, Executor | Quick doc updates |

### Conversation Features

**Persistence**:
- Save conversation state to disk
- Resume from last checkpoint
- Export conversation history

**Human-in-the-Loop**:
- Approve critical operations
- Provide feedback mid-conversation
- Override agent decisions

**Approval Workflows**:
```yaml
approval_points:
  - step: "before_deployment"
    prompt: "Deploy to production?"
  - step: "after_security_scan"
    prompt: "Security issues found. Continue?"
```

## 📈 Performance & Optimization

### Groq API Benefits

| Feature | Benefit |
|---------|---------|
| **Fast Inference** | Up to 750 tokens/second with Llama 3.3 70B |
| **Free Tier** | Generous free tier for development |
| **High Quality** | State-of-the-art open-source models |
| **No GPU Required** | Cloud-based inference on LPU hardware |
| **Low Latency** | Optimized for real-time applications |

### Model Selection Guide

| Task Type | Recommended Model | Use Case |
|-----------|------------------|----------|
| Code Analysis | Llama 3.3 70B Versatile | Deep code review, security audits |
| Code Generation | Llama 3.3 70B Versatile | Generate code, refactoring |
| Documentation | Llama 3.3 70B Versatile | Technical writing, API docs |
| Quick Tasks | Llama 3.1 8B Instant | Fast routing, simple decisions |
| Coordination | Mixtral 8x7B | Project management, orchestration |

### MCP Tool Optimization

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Retry Logic** | Exponential backoff (3 attempts) | Resilience to transient failures |
| **Rate Limiting** | Token bucket algorithm | Prevents API throttling |
| **Caching** | TTL-based response cache (5min) | Reduces redundant requests |
| **Fallbacks** | Alternative operations | Graceful degradation |
| **Connection Pooling** | HTTP session reuse | Lower latency |

### Performance Tips

1. **Use appropriate models**: Don't use GPT-4 for simple tasks
2. **Enable caching**: Set `cache_enabled: true` in config
3. **Adjust rate limits**: Match your API tier
4. **Batch operations**: Group related tasks
5. **Monitor costs**: Check OpenRouter dashboard

## 💻 Usage

### Interactive Mode

```bash
python main.py
```

**Available Commands**:
- `run <workflow> [params...]` - Execute a workflow
- `list` - Show available workflows
- `history` - View execution history
- `help` - Show command help
- `exit` - Exit application

**Example Session**:
```
>>> list
Available Workflows:
  • code_analysis
  • documentation_generation
  • deployment
  • research

>>> run code_analysis code_path=./src
Executing workflow: code_analysis

✓ Workflow completed successfully
Summary: Analyzed 45 files, found 3 issues
Duration: 23.5s
Tasks: 3 completed, 0 failed

>>> history
┌─────────────────┬─────────┬──────────┐
│ Workflow        │ Status  │ Duration │
├─────────────────┼─────────┼──────────┤
│ code_analysis   │ ✓ success │ 23.50s  │
└─────────────────┴─────────┴──────────┘
```

### Programmatic API

```python
from src.autogen_adapters.conversation_manager import create_conversation_manager
import asyncio

async def main():
    # Initialize conversation manager
    manager = await create_conversation_manager()
    
    # Execute workflow
    result = await manager.execute_workflow(
        "code_analysis",
        variables={"code_path": "./src"}
    )
    
    print(f"Status: {result.status}")
    print(f"Summary: {result.summary}")
    print(f"Duration: {result.duration_seconds}s")

asyncio.run(main())
```

### Custom Workflows

Create custom workflows in `config/autogen_workflows.yaml`:

```yaml
workflows:
  my_custom_workflow:
    name: "Custom Analysis"
    description: "My custom workflow"
    pattern: "sequential"
    agents:
      - code_analyzer
      - documentation_agent
    max_rounds: 5
    variables:
      - name: "target_path"
        type: "string"
        required: true
      - name: "output_format"
        type: "string"
        default: "markdown"
    approval_points:
      - step: "before_documentation"
        prompt: "Generate documentation?"
```

Execute:
```bash
>>> run my_custom_workflow target_path=./src output_format=html
```

## 🐛 Troubleshooting

### Common Issues

#### 1. MCP Servers Not Running

**Check server status**:
```bash
python test_mcp_servers.py --suites health
```

**Start servers manually**:
```bash
# Each in a separate terminal
python mcp_servers/github_server.py
python mcp_servers/filesystem_server.py
python mcp_servers/memory_server.py
```

**Check logs**:
- Server logs appear in terminal where server runs
- Application logs: `logs/autogen_dev_assistant.log`

#### 2. Groq API Errors

**Invalid API Key**:
```bash
# Verify key in .env
echo $GROQ_API_KEY

# Test key (Windows PowerShell)
$headers = @{"Authorization" = "Bearer $env:GROQ_API_KEY"}
Invoke-RestMethod -Uri "https://api.groq.com/openai/v1/models" -Headers $headers
```

**Rate Limiting**:
- Check your Groq console dashboard
- Free tier: 30 requests/minute, 14,400/day
- Paid tier: Higher limits available
- Enable caching to reduce requests

**Model Not Found**:
```yaml
# Use valid Groq models in config/autogen_agents.yaml
llm_configs:
  code_analysis_config:
    model: "llama-3.3-70b-versatile"  # Valid Groq model
    base_url: "https://api.groq.com/openai/v1"
```

#### 3. Permission Errors (Filesystem)

**Path not allowed**:
```yaml
# Add path to config.yaml
mcp_servers:
  filesystem:
    allowed_paths:
      - "./workspace"
      - "./your/custom/path"  # Add this
```

**Blocked pattern**:
```bash
# Avoid these patterns:
../             # Directory traversal
.env            # Environment files
.ssh/           # SSH keys
/etc/           # System files
```

#### 4. Import Errors

**Missing dependencies**:
```bash
pip install -r requirements.txt --upgrade
```

**Module not found**:
```bash
# Verify virtual environment is activated
which python  # Should show venv path

# Reinstall
pip uninstall pyautogen
pip install pyautogen>=0.2.0
```

#### 5. GitHub API Issues

**Invalid Token**:
```bash
# Test GitHub token
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/user
```

**Rate Limit Exceeded**:
- GitHub allows 5000 requests/hour with auth
- Check: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`
- Wait or adjust `rate_limit_minute` in config

### Debug Mode

Enable verbose logging:

```yaml
# config.yaml
logging:
  level: "DEBUG"
  file: "./logs/autogen_dev_assistant.log"
```

Or via environment:
```bash
# Windows
$env:AUTOMATON_LOG_LEVEL="DEBUG"
python main.py

# Linux/Mac
export AUTOMATON_LOG_LEVEL=DEBUG
python main.py
```

### Health Checks

```bash
# Quick system health check
python -c "
import asyncio
from src.autogen_adapters.conversation_manager import create_conversation_manager

async def check():
    manager = await create_conversation_manager()
    print('✓ System healthy')

asyncio.run(check())
"
```

### Getting Help

1. **Check logs**: `logs/autogen_dev_assistant.log`
2. **Run tests**: `python test_mcp_servers.py`
3. **Check config**: Verify all environment variables
4. **GitHub Issues**: Report bugs with logs
5. **Documentation**: See `IMPLEMENTATION_COMPLETE.md` for architecture details

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Implementation Complete](IMPLEMENTATION_COMPLETE.md) | AutoGen migration details and architecture |
| [AutoGen Setup Summary](AUTOGEN_SETUP_SUMMARY.md) | Setup guide and configuration |
| [Migration Guide](AUTOGEN_MIGRATION_GUIDE.md) | Transition from CrewAI to AutoGen |
| [Performance Guide](PERFORMANCE_GUIDE.md) | Optimization and best practices |
| [Security Guide](SECURITY.md) | Security features and hardening |
| [Test Guide](TEST_GUIDE.md) | Testing procedures and examples |
| [Cleanup Summary](CLEANUP_SUMMARY.md) | System cleanup and maintenance |

## 🐳 Docker Deployment

### Quick Start with Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f automaton

# Stop
docker-compose down
```

### Production Deployment

```yaml
# docker-compose.yml includes:
services:
  automaton:      # Main application
  postgres:       # Database (optional)
  redis:          # Cache (optional)
  prometheus:     # Monitoring
  grafana:        # Dashboards
```

**Environment Variables**:
```bash
# .env for Docker
OPENROUTER_API_KEY=your_key
GITHUB_TOKEN=your_token
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_password
```

### Custom Docker Build

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t automaton:latest .
docker run -d \
  -e OPENROUTER_API_KEY=your_key \
  -e GITHUB_TOKEN=your_token \
  -p 8000:8000 \
  automaton:latest
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/automaton.git
cd automaton

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install dev dependencies
pip install pytest pytest-asyncio black flake8 mypy

# 5. Setup pre-commit hooks
pip install pre-commit
pre-commit install
```

### Code Standards

**Formatting**:
```bash
# Format code with Black
black src/ mcp_servers/ main.py

# Sort imports
isort src/ mcp_servers/
```

**Linting**:
```bash
# Lint with flake8
flake8 src/ mcp_servers/ --max-line-length=100

# Type checking
mypy src/ --ignore-missing-imports
```

**Testing**:
```bash
# Run all tests
python test_mcp_servers.py
python test_agents.py

# Run with pytest
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Contribution Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**:
   - Write tests for new features
   - Update documentation
   - Follow code standards

3. **Test thoroughly**:
   ```bash
   python test_mcp_servers.py
   black src/
   flake8 src/
   ```

4. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add amazing feature"
   git commit -m "fix: resolve issue with XYZ"
   git commit -m "docs: update README"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/amazing-feature
   ```
   Then open a Pull Request on GitHub

### Areas for Contribution

- 🤖 **New Agents**: Add specialized agents for specific tasks
- 🔧 **MCP Servers**: Implement new tool servers (Slack, Jira, etc.)
- 📝 **Workflows**: Create reusable workflow templates
- 🧪 **Tests**: Improve test coverage
- 📚 **Documentation**: Enhance guides and examples
- 🐛 **Bug Fixes**: Report and fix issues
- ⚡ **Performance**: Optimize agent execution

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build/config changes

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Microsoft AutoGen](https://github.com/microsoft/autogen) - Multi-agent conversation framework
- [FastMCP](https://github.com/jlowin/fastmcp) - Fast MCP server implementation
- [Groq](https://groq.com/) - Ultra-fast LLM inference platform
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP standard
- [Rich](https://github.com/Textualize/rich) - Terminal formatting and UI
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-provider LLM gateway
- [Meta](https://ai.meta.com/) - Llama models
- [Mistral AI](https://mistral.ai/) - Mixtral models

## 🔗 Related Projects

- [AutoGen Studio](https://github.com/microsoft/autogen-studio) - Visual agent builder
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [LlamaIndex](https://github.com/jerryjliu/llama_index) - Data indexing for LLMs
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel) - Microsoft's AI orchestration

## 📊 Project Stats

- **Framework**: Microsoft AutoGen 0.10.0+
- **MCP Version**: FastMCP (latest)
- **Python**: 3.9+
- **Agents**: 7 specialized agents (6 assistants + 1 executor)
- **MCP Servers**: 3 tool servers (GitHub, Filesystem, Memory)
- **Workflows**: 7+ predefined workflows
- **LLM Provider**: Groq (Llama 3.3 70B, Mixtral 8x7B, Llama 3.1 8B)
- **Test Coverage**: Comprehensive health, integration, and load tests

## 🚀 Roadmap

### Current Version: 2.0.0 (AutoGen Edition)

**✅ Completed**:
- AutoGen multi-agent framework integration
- Groq API integration (Llama 3.3, Mixtral, Llama 3.1)
- FastMCP server implementation (GitHub, Filesystem, Memory)
- Workflow orchestration system (GroupChat, Two-Agent, Nested)
- Function registry with auto-registration
- LiteLLM integration for provider routing
- Security hardening and validation
- Backward compatibility for AutoGen versions

**🔄 In Progress**:
- Web UI for workflow management
- Additional MCP servers (Slack, Jira, Database)
- Advanced analytics and monitoring
- Multi-language support (Python, JavaScript, Go)

**📅 Planned**:
- VS Code extension
- GitHub Actions integration
- Kubernetes deployment templates
- Agent marketplace
- Custom model training pipelines
- Real-time collaboration features

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/automaton/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/automaton/discussions)
- **Email**: support@yourproject.com
- **Documentation**: See `docs/` directory

---

**Version**: 2.0.0 (AutoGen Edition)  
**Last Updated**: December 16, 2025  
**Framework**: Microsoft AutoGen 0.10.0  
**LLM Provider**: Groq (Llama 3.3, Mixtral, Llama 3.1)  
**Python**: 3.9+  
**License**: MIT

**Made with ❤️ using AutoGen, Groq, and FastMCP**
