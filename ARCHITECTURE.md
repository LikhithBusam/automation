# System Architecture

> **Comprehensive technical architecture documentation for the AutoGen Development Assistant**

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Directory Structure](#directory-structure)
- [Agent System](#agent-system)
- [MCP Integration](#mcp-integration)
- [Security Architecture](#security-architecture)
- [Memory System](#memory-system)

---

## Overview

The AutoGen Development Assistant is a sophisticated multi-agent AI system built on Microsoft's AutoGen framework. It orchestrates specialized AI agents to perform code analysis, security auditing, documentation generation, and deployment automation.

### Key Architectural Principles

- **Modularity**: Clear separation between adapters, tools, security, and models
- **Extensibility**: YAML-based configuration for agents and workflows
- **Security-First**: Multiple security layers (validation, rate limiting, circuit breakers)
- **Scalability**: Connection pooling, caching, and async operations
- **Observability**: Comprehensive logging and monitoring

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     CLI      │  │   Scripts    │  │  Examples    │          │
│  │  (main.py)   │  │   (Daemon)   │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   Application Layer                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Conversation Manager (Workflow Orchestration)    │   │
│  │  • Two-Agent Conversations  • GroupChats  • NestedChats │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Agent Factory (Agent Creation)              │   │
│  │  • Dynamic Agent Instantiation  • YAML-based Config     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Function Registry (Tool Management)              │   │
│  │  • MCP Tool Registration  • Function Call Handling      │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      Agent Layer                                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │  Code  │ │Security│ │  Docs  │ │ Deploy │ │Research│       │
│  │Analyzer│ │Auditor │ │ Agent  │ │ Agent  │ │ Agent  │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
│  ┌────────┐ ┌────────┐ ┌────────┐                              │
│  │Project │ │Executor│ │  User  │                              │
│  │Manager │ │        │ │ Proxy  │                              │
│  └────────┘ └────────┘ └────────┘                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                       Tool Layer                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   MCP Tool Manager                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │  GitHub  │ │Filesystem│ │  Memory  │ │CodeBase  │   │   │
│  │  │   Tool   │ │   Tool   │ │   Tool   │ │  Buddy   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  │  ┌──────────┐                                           │   │
│  │  │  Slack   │                                           │   │
│  │  │   Tool   │                                           │   │
│  │  └──────────┘                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      MCP Server Layer                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   GitHub     │ │  Filesystem  │ │   Memory     │           │
│  │   Server     │ │   Server     │ │   Server     │           │
│  │  (Port 3000) │ │ (Port 3001)  │ │ (Port 3002)  │           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
│  ┌──────────────┐                                              │
│  │CodeBaseBuddy │                                              │
│  │   Server     │                                              │
│  │ (Port 3004)  │                                              │
│  └──────────────┘                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   LLM Providers  │  │  Security Layer  │                    │
│  │  • OpenRouter    │  │  • Validation    │                    │
│  │  • Groq          │  │  • Rate Limiting │                    │
│  │  • Google Gemini │  │  • Auth          │                    │
│  └──────────────────┘  └──────────────────┘                    │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Memory System   │  │  Data Storage    │                    │
│  │  • Short-term    │  │  • SQLite        │                    │
│  │  • Medium-term   │  │  • ChromaDB      │                    │
│  │  • Long-term     │  │  • Redis Cache   │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. AutoGen Adapters (`src/autogen_adapters/`)

**Purpose**: Integration layer between the application and AutoGen framework

**Components**:

- **Agent Factory** (`agent_factory.py`)
  - Creates agents dynamically from YAML configuration
  - Supports AssistantAgent, UserProxyAgent, TeachableAgent
  - Handles LLM configuration and tool registration

- **Conversation Manager** (`conversation_manager.py`)
  - Orchestrates workflow execution
  - Manages two-agent, group chat, and nested chat patterns
  - Handles conversation persistence and resumption

- **Function Registry** (`function_registry.py`)
  - Registers MCP tools as callable functions
  - Manages function schemas and parameter validation
  - Routes function calls to appropriate MCP servers

- **GroupChat Factory** (`groupchat_factory.py`)
  - Creates multi-agent group conversations
  - Configures speaker selection patterns
  - Manages agent turn-taking and termination

### 2. MCP Tools (`src/mcp/`)

**Purpose**: Wrapper layer for Model Context Protocol server tools

**Components**:

- **Base Tool** (`base_tool.py`)
  - Abstract base class for all MCP tools
  - Connection pooling and retry logic
  - Error handling and logging

- **GitHub Tool** (`github_tool.py`)
  - Repository operations (clone, commit, PR)
  - Issue and PR management
  - Code search and file operations

- **Filesystem Tool** (`filesystem_tool.py`)
  - Local file read/write operations
  - Directory traversal and search
  - Path validation and security checks

- **Memory Tool** (`memory_tool.py`)
  - Store and retrieve semantic memories
  - Vector similarity search
  - Conversation context management

- **CodeBaseBuddy Tool** (`codebasebuddy_tool.py`)
  - Semantic code search across repositories
  - Function/class definition lookup
  - Code dependency analysis

- **Slack Tool** (`slack_tool.py`)
  - Send notifications to Slack channels
  - Post code review results
  - Alert on security findings

- **Tool Manager** (`tool_manager.py`)
  - Central orchestrator for all tools
  - Health checking and monitoring
  - Automatic server reconnection

### 3. Security Layer (`src/security/`)

**Purpose**: Multi-layered security implementation

**Components**:

- **Input Validator** (`input_validator.py`)
  - Path traversal prevention
  - SQL injection detection
  - Command injection prevention
  - XSS and CSRF protection

- **Rate Limiter** (`rate_limiter.py`)
  - Per-user request throttling
  - Sliding window algorithm
  - 60 req/min, 1000 req/hour limits

- **Circuit Breaker** (`circuit_breaker.py`)
  - Failure detection and prevention
  - Automatic service degradation
  - Health check integration

- **Authentication** (`auth.py`)
  - API key validation
  - Token-based authentication
  - Session management

- **Log Sanitizer** (`log_sanitizer.py`)
  - Automatic credential redaction
  - PII removal from logs
  - Sensitive data masking

- **YAML Loader** (`yaml_loader.py`)
  - Safe YAML parsing
  - Prevents code injection
  - Schema validation

### 4. Model Layer (`src/models/`)

**Purpose**: LLM provider integrations

**Components**:

- **Model Factory** (`model_factory.py`)
  - Creates LLM clients from configuration
  - Supports multiple providers
  - Handles API key management

- **Groq LLM** (`groq_llm.py`)
  - Ultra-fast inference via Groq API
  - LLaMA 3.1 and Mixtral models
  - Function calling support

- **Gemini LLM** (`gemini_llm.py`)
  - Google Gemini integration
  - Gemini 2.5 Flash model
  - Advanced reasoning capabilities

### 5. Memory System (`src/memory/`)

**Purpose**: Three-tier memory management

**Components**:

- **Memory Manager** (`memory_manager.py`)
  - Short-term: In-memory cache (5 min)
  - Medium-term: SQLite teachable storage
  - Long-term: JSON file persistence
  - Automatic memory consolidation

---

## Data Flow

### Code Review Workflow

```
User Request
    │
    ▼
┌──────────────────┐
│  main.py (CLI)   │
└────────┬─────────┘
         │ Parse input
         ▼
┌──────────────────────────┐
│ Conversation Manager     │
│ • Load workflow config   │
│ • Validate parameters    │
└────────┬─────────────────┘
         │ Create agents
         ▼
┌──────────────────────────┐
│    Agent Factory         │
│ • CodeAnalyzer (LLM)     │
│ • Executor (UserProxy)   │
└────────┬─────────────────┘
         │ Initiate conversation
         ▼
┌──────────────────────────┐
│  Two-Agent Conversation  │
│ ┌────────────────────┐   │
│ │ UserProxy: Read    │   │
│ │ file via MCP       │───┼─┐
│ └────────────────────┘   │ │
│ ┌────────────────────┐   │ │
│ │ CodeAnalyzer:      │   │ │
│ │ Analyze code       │   │ │
│ └────────────────────┘   │ │
│ ┌────────────────────┐   │ │
│ │ UserProxy: Return  │   │ │
│ │ findings           │   │ │
│ └────────────────────┘   │ │
└─────────────────────┬────┘ │
                      │      │
                      │      │ MCP call
                      │      ▼
                      │ ┌──────────────────┐
                      │ │ Filesystem Tool  │
                      │ │ • Read file      │
                      │ └────────┬─────────┘
                      │          │
                      │          ▼
                      │ ┌──────────────────┐
                      │ │ Filesystem Server│
                      │ │ (Port 3001)      │
                      │ └────────┬─────────┘
                      │          │
                      │          │ File content
                      │          ▼
                      │      Returns
         Summary      │
         ▼            ▼
┌──────────────────────────┐
│   Return to User         │
│ • Code quality score     │
│ • Security issues        │
│ • Recommendations        │
└──────────────────────────┘
```

---

## Technology Stack

### AI/ML Frameworks

| Technology | Version | Purpose |
|-----------|---------|---------|
| Microsoft AutoGen | 0.2.0+ | Multi-agent orchestration |
| LangChain | 0.1.0+ | LLM utilities and chains |
| Sentence Transformers | 2.2.2+ | Text embeddings |
| ChromaDB | 0.4.18+ | Vector database |
| FAISS | 1.7.4+ | Vector similarity search |

### LLM Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| OpenRouter | 200+ models | Function calling, GPT-OSS-120B |
| Groq | LLaMA 3.1, Mixtral | Ultra-fast inference |
| Google Gemini | Gemini 2.5 Flash | Advanced reasoning |

### Infrastructure

| Technology | Version | Purpose |
|-----------|---------|---------|
| FastMCP | 0.1.0+ | Model Context Protocol servers |
| SQLAlchemy | 2.0.23+ | ORM and database management |
| Redis | 5.0.1+ | Caching and session storage |
| PyGithub | 2.1.1+ | GitHub API integration |
| httpx | 0.25.0+ | Async HTTP client |

### Development Tools

| Technology | Purpose |
|-----------|---------|
| pytest | Testing framework |
| black | Code formatting |
| flake8 | Linting |
| mypy | Type checking |
| bandit | Security scanning |

---

## Directory Structure

```
automaton/
├── config/                       # Configuration files
│   ├── autogen_agents.yaml       # Agent definitions (8 agents)
│   ├── autogen_workflows.yaml    # Workflow definitions (7 workflows)
│   ├── autogen_groupchats.yaml   # GroupChat configurations
│   ├── function_schemas.yaml     # MCP tool schemas
│   ├── config.yaml               # Application settings
│   └── config.production.yaml    # Production settings
│
├── src/                          # Source code
│   ├── autogen_adapters/         # AutoGen framework integration
│   │   ├── agent_factory.py
│   │   ├── conversation_manager.py
│   │   ├── function_registry.py
│   │   └── groupchat_factory.py
│   ├── mcp/                      # MCP tool wrappers
│   │   ├── base_tool.py
│   │   ├── github_tool.py
│   │   ├── filesystem_tool.py
│   │   ├── memory_tool.py
│   │   ├── codebasebuddy_tool.py
│   │   ├── slack_tool.py
│   │   └── tool_manager.py
│   ├── security/                 # Security utilities
│   │   ├── auth.py
│   │   ├── circuit_breaker.py
│   │   ├── input_validator.py
│   │   ├── log_sanitizer.py
│   │   ├── rate_limiter.py
│   │   └── yaml_loader.py
│   ├── memory/                   # Memory management
│   │   └── memory_manager.py
│   ├── models/                   # LLM integrations
│   │   ├── model_factory.py
│   │   ├── groq_llm.py
│   │   └── gemini_llm.py
│   └── api/                      # API endpoints
│       └── health.py
│
├── mcp_servers/                  # MCP server implementations
│   ├── github_server.py          # Port 3000
│   ├── filesystem_server.py      # Port 3001
│   ├── memory_server.py          # Port 3002
│   └── codebasebuddy_server.py   # Port 3004
│
├── tests/                        # Test suite
│   ├── test_autogen_agents.py
│   ├── test_integration.py
│   ├── test_mcp_servers.py
│   ├── diagnostics/              # Diagnostic tools (13 files)
│   └── root_tests/               # Moved from root directory
│
├── scripts/                      # Automation scripts
│   ├── mcp_server_daemon.py      # Auto-start servers
│   ├── mcp_server_watchdog.py    # Health monitoring
│   ├── windows/                  # Windows batch scripts
│   └── unix/                     # Unix shell scripts
│
├── docs/                         # Documentation
│   ├── API_REFERENCE.md
│   ├── QUICK_START.md
│   ├── SECURITY.md
│   ├── TROUBLESHOOTING.md
│   ├── CODEBASEBUDDY_INTEGRATION.md
│   ├── PROJECT_EXPLANATION.md
│   ├── guides/                   # Technical guides
│   │   ├── PERFORMANCE_GUIDE.md
│   │   ├── SERVER_MANAGEMENT.md
│   │   └── TEST_GUIDE.md
│   └── archive/                  # Historical documentation
│       └── migration/            # Migration documents
│
├── examples/                     # Usage examples
│   └── mcp_integration_example.py
│
├── data/                         # Data storage
│   ├── teachable/                # SQLite databases
│   └── memory_fallback.json      # Long-term memory
│
├── logs/                         # Application logs
│   ├── autogen_dev_assistant.log
│   └── mcp_servers/              # MCP server logs
│
├── state/                        # Application state
│   └── app_state.json            # Conversation persistence
│
├── reports/                      # Generated reports
│   └── coverage/                 # Test coverage reports
│
├── main.py                       # Main entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── README.md                     # Main documentation
└── ARCHITECTURE.md               # This file
```

---

## Agent System

### Agent Configuration

All agents are configured via `config/autogen_agents.yaml`:

```yaml
agents:
  code_analyzer:
    agent_type: "teachable_assistant"  # Learns from interactions
    llm_config: "openrouter_config"
    system_message: |
      You are an expert code reviewer...
    tools:
      - "filesystem_read_file"
      - "codebasebuddy_search"
      - "memory_store"
    human_input_mode: "NEVER"
    max_consecutive_auto_reply: 10
```

### Agent Types

| Type | Description | Use Case |
|------|-------------|----------|
| AssistantAgent | Standard LLM-powered agent | Code analysis, research |
| UserProxyAgent | Human-in-the-loop agent | File access, execution |
| TeachableAgent | Agent with learning capability | Code review (learns patterns) |

### Agent Communication Patterns

1. **Two-Agent Conversation**
   - Simple request-response pattern
   - Fast execution (3-5 seconds)
   - Example: Quick code review

2. **GroupChat**
   - Multiple agents collaborate
   - Sequential or dynamic speaker selection
   - Example: Comprehensive security audit

3. **Nested Chat**
   - Multi-level agent conversations
   - Sub-task delegation
   - Example: Feature review with deployment planning

---

## MCP Integration

### MCP Server Architecture

All MCP servers follow the FastMCP protocol:

```python
from fastmcp import FastMCP

mcp = FastMCP("ServerName")

@mcp.tool()
async def tool_function(param: str) -> str:
    """Tool description for LLM"""
    # Implementation
    return result

if __name__ == "__main__":
    mcp.run()
```

### Server Ports

| Server | Port | Purpose |
|--------|------|---------|
| GitHub | 3000 | GitHub API operations |
| Filesystem | 3001 | Local file access |
| Memory | 3002 | Semantic memory storage |
| CodeBaseBuddy | 3004 | Semantic code search |

### Tool Function Calling Flow

```
Agent → Function Registry → Tool Manager → MCP Server → Tool Implementation
  │                             │                             │
  │ Request                     │ Connection Pool            │ Execute
  │                             │ Retry Logic                │ Validate
  │                             │ Error Handling             │ Return
  │ ← Response ← Result ← Response ← Response ← Result
```

---

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────┐
│      Input Validation Layer         │
│  • Path traversal prevention        │
│  • SQL injection detection          │
│  • Command injection prevention     │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│      Authentication Layer           │
│  • API key validation               │
│  • Token verification               │
│  • Session management               │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│      Rate Limiting Layer            │
│  • 60 requests/minute               │
│  • 1000 requests/hour               │
│  • Sliding window algorithm         │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│      Circuit Breaker Layer          │
│  • Failure detection                │
│  • Automatic degradation            │
│  • Health check integration         │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│      Log Sanitization Layer         │
│  • Credential redaction             │
│  • PII removal                      │
│  • Sensitive data masking           │
└─────────────────────────────────────┘
```

### Security Configuration

```yaml
security:
  allowed_paths:
    - "./src"
    - "./tests"
    - "./docs"
  blocked_paths:
    - ".env"
    - "*.key"
    - "credentials.json"
  rate_limits:
    requests_per_minute: 60
    requests_per_hour: 1000
  circuit_breaker:
    failure_threshold: 5
    timeout: 60
```

---

## Memory System

### Three-Tier Architecture

```
┌─────────────────────────────────────┐
│        Short-Term Memory            │
│  • In-memory cache (5 min)          │
│  • Current conversation context     │
│  • Fast access (< 1ms)              │
└────────────┬────────────────────────┘
             │ Consolidation
┌────────────▼────────────────────────┐
│       Medium-Term Memory            │
│  • SQLite teachable storage         │
│  • Session-specific data            │
│  • Agent learning patterns          │
│  • Location: data/teachable/*.db    │
└────────────┬────────────────────────┘
             │ Persistence
┌────────────▼────────────────────────┐
│        Long-Term Memory             │
│  • JSON file persistence            │
│  • Permanent knowledge base         │
│  • Cross-session memory             │
│  • Location: data/memory_fallback.json│
└─────────────────────────────────────┘
```

### Memory Operations

```python
# Store memory
memory_manager.store(
    agent_id="code_analyzer",
    memory_type="pattern",
    content="Always check error handling in API routes",
    metadata={"category": "best_practice"}
)

# Retrieve memory
memories = memory_manager.retrieve(
    agent_id="code_analyzer",
    query="error handling patterns",
    top_k=5
)
```

---

## Performance Characteristics

### Workflow Execution Times

| Workflow | Agents | Avg Time | Max Time |
|----------|--------|----------|----------|
| quick_code_review | 2 | 3-5s | 10s |
| code_analysis | 3+ | 20-60s | 90s |
| security_audit | 3+ | 30-90s | 120s |
| documentation_generation | 2 | 10-30s | 45s |
| deployment | 2 | 15-45s | 60s |

### Resource Usage

- **Memory**: 500MB - 2GB (depending on model cache)
- **CPU**: Minimal (LLM inference is remote)
- **Disk**: 100MB logs, 500MB cache, 50MB data
- **Network**: 10KB - 500KB per request (depends on code size)

---

## Scalability Considerations

### Current Limitations

- Single-process execution
- Local file system only
- In-memory caching (no distributed cache)
- Sequential workflow execution

### Future Scalability Enhancements

- **Distributed Execution**: Celery task queue for parallel workflows
- **Database Clustering**: PostgreSQL with read replicas
- **Caching Layer**: Redis cluster for distributed caching
- **Load Balancing**: Multiple MCP server instances
- **Async Workflows**: Parallel agent conversations

---

## Extension Points

### Adding a New Agent

1. Define agent in `config/autogen_agents.yaml`
2. Register in workflow (`config/autogen_workflows.yaml`)
3. Optionally add custom system message
4. Test with diagnostic tools

### Adding a New MCP Server

1. Create server in `mcp_servers/`
2. Implement FastMCP protocol
3. Add to daemon configuration
4. Create tool wrapper in `src/mcp/`
5. Register in `config/function_schemas.yaml`

### Adding a New Workflow

1. Define workflow in `config/autogen_workflows.yaml`
2. Specify agents and conversation pattern
3. Set termination keywords
4. Test end-to-end

---

## Monitoring and Observability

### Logging

```
logs/
├── autogen_dev_assistant.log    # Main application log
└── mcp_servers/
    ├── github.log
    ├── filesystem.log
    ├── memory.log
    └── codebasebuddy.log
```

### Metrics

- Request count per workflow
- Average execution time
- Error rate by agent
- MCP server health status
- Memory usage trends

### Health Checks

```bash
# Check all MCP servers
python scripts/mcp_server_daemon.py status

# Check specific server
curl http://localhost:3000/health
```

---

## Conclusion

The AutoGen Development Assistant is a production-ready, extensible multi-agent AI system with clear architectural boundaries, comprehensive security, and robust error handling. The modular design allows for easy extension and customization while maintaining stability and performance.

For implementation details, see the source code in `src/` and configuration files in `config/`.
