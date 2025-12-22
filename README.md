# AutoGen Development Assistant

> **Production-ready multi-agent AI system for intelligent code analysis, security auditing, and development automation**

[![CI/CD Pipeline](https://github.com/LikhithBusam/automation/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/LikhithBusam/automation/actions/workflows/ci-cd.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AutoGen](https://img.shields.io/badge/AutoGen-0.2.0+-green.svg)](https://microsoft.github.io/autogen/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

**AutoGen Development Assistant** is an enterprise-grade, multi-agent AI system built on Microsoft's AutoGen framework. It orchestrates 8 specialized AI agents powered by OpenRouter (GPT-OSS-120B), Groq (LLaMA 3.1), and Google Gemini to deliver lightning-fast code reviews, comprehensive security audits, automated documentation, and intelligent deployment planning.

### Key Features

- **Multi-Agent Orchestration** - 8 specialized AI agents collaborating via AutoGen framework
- **Lightning-Fast Analysis** - Complete code reviews in 3-5 seconds using Groq inference
- **Semantic Code Search** - CodeBaseBuddy integration for intelligent codebase exploration
- **Security-First Design** - OWASP-compliant vulnerability scanning with multiple security layers
- **MCP Protocol Integration** - 4 FastMCP servers (GitHub, Filesystem, Memory, CodeBaseBuddy)
- **Production-Ready** - Comprehensive logging, monitoring, rate limiting, and circuit breakers
- **Learning Agents** - TeachableAgent remembers patterns and improves over time
- **Flexible LLM Support** - OpenRouter (200+ models), Groq, and Gemini providers

---

## Quick Start

### Prerequisites

- **Python**: 3.10+ (tested on 3.10, 3.11, 3.12, 3.13)
- **OS**: Windows 10+, Ubuntu 20.04+, macOS 11+
- **Memory**: 4GB+ RAM
- **API Keys**:
  - [Groq API Key](https://console.groq.com/keys) (required for fast inference)
  - [OpenRouter API Key](https://openrouter.ai/keys) (recommended for 200+ models)
  - [Google Gemini API Key](https://makersuite.google.com/app/apikey) (optional)

> **Note**: Python 3.9 is not supported due to `fastmcp` and other dependencies requiring Python 3.10+

### Installation (2 minutes)

```bash
# Clone the repository
git clone <repository-url>
cd automaton

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# Unix/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys:
#   GROQ_API_KEY=your_groq_api_key
#   OPENROUTER_API_KEY=your_openrouter_api_key  # Recommended
#   GOOGLE_API_KEY=your_gemini_api_key          # Optional
```

### Start the System

**Step 1: Start MCP Servers**

```bash
# Windows:
scripts\windows\start_servers.bat

# Unix/macOS:
python scripts/mcp_server_daemon.py start
```

This auto-starts all 4 MCP servers:
- GitHub Server (Port 3000) - GitHub API operations
- Filesystem Server (Port 3001) - Local file access
- Memory Server (Port 3002) - Semantic memory storage
- CodeBaseBuddy Server (Port 3004) - Intelligent code search

**Step 2: Use CodeBaseBuddy Interactive Chat**

```bash
# Start interactive Q&A about your codebase
python scripts/codebasebuddy_interactive.py

# Example queries:
CodeBaseBuddy> What agents are available?
CodeBaseBuddy> How does the security module work?
CodeBaseBuddy> search authentication
CodeBaseBuddy> find_usages AgentFactory
```

**Step 3: Launch the Assistant**

```bash
# Windows:
scripts\windows\run.bat

# Unix/macOS:
bash scripts/unix/run.sh
```

### First Code Review

```bash
# Interactive mode
>>> run quick_code_review code_path=./main.py focus_areas="error handling, security"

# Standalone mode (no server required)
python tests/diagnostics/simple_code_review.py ./main.py "security, performance"
```

**Output:**
```
Executing workflow: quick_code_review
Duration: 3.47s

Summary:
- Code Quality: 8/10
- Security Issues: 2 found (SQL injection risk in line 45)
- Recommendations: Add input validation, implement error logging
```

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                  User Interface                     │
│       CLI (main.py) + Diagnostic Scripts            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            Conversation Manager                     │
│  Workflows • GroupChats • Two-Agent Conversations   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 Agent Factory                       │
│  8 Specialized Agents (Code, Security, Docs, etc.) │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              MCP Tool Manager                       │
│  GitHub • Filesystem • Memory • CodeBaseBuddy       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            MCP Servers (FastMCP)                    │
│  4 Servers on Ports 3000-3004                       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          Infrastructure Layer                       │
│  OpenRouter • Groq • Gemini • Security • Memory     │
└─────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Role | Model | Key Capabilities |
|-------|------|-------|------------------|
| **Code Analyzer** | Code review & quality analysis | openai/gpt-oss-120b | Best practices, refactoring, code smells |
| **Security Auditor** | Vulnerability assessment | openai/gpt-oss-120b | OWASP Top 10, CVE detection, semantic search |
| **Documentation Agent** | Doc generation/updates | openai/gpt-oss-120b | README, API docs, inline comments |
| **Deployment Agent** | CI/CD automation | openai/gpt-oss-120b | Docker, K8s, deployment planning |
| **Research Agent** | Technology research | openai/gpt-oss-120b | Best practices, framework recommendations |
| **Project Manager** | Orchestration & planning | openai/gpt-oss-120b | Task breakdown, dependency management |
| **Executor** | Code execution & testing | UserProxyAgent | File operations, tool invocation |
| **User Proxy** | Human-in-the-loop | UserProxyAgent | Interactive review, approval workflows |

**Note**: All agents use OpenRouter's `openai/gpt-oss-120b` model via function calling. Groq and Gemini are available as alternative providers.

---

## Workflows

### Available Workflows

| Workflow | Type | Agents | Duration | Description |
|----------|------|--------|----------|-------------|
| `quick_code_review` | Two-Agent | 2 | 3-5s | Fast code review for small changes |
| `code_analysis` | GroupChat | 3+ | 20-60s | Comprehensive analysis with security |
| `security_audit` | GroupChat | 3+ | 30-90s | Deep vulnerability assessment (OWASP) |
| `documentation_generation` | GroupChat | 2+ | 10-30s | Generate/update project documentation |
| `deployment` | GroupChat | 2+ | 15-45s | Deployment planning and automation |
| `research` | GroupChat | 2+ | 20-60s | Technology research and recommendations |
| `quick_documentation` | Two-Agent | 2 | 5-15s | Quick doc updates |
| `comprehensive_feature_review` | NestedChat | 4+ | 60-180s | Full feature review with sub-tasks |

### Workflow Examples

#### 1. Quick Code Review
```bash
>>> run quick_code_review code_path=./src/api/routes.py focus_areas="error handling, security"
```

#### 2. Security Audit
```bash
>>> run security_audit target_path=./src focus_areas="SQL injection, XSS, authentication"
```

#### 3. Documentation Generation
```bash
>>> run documentation_generation module_path=./src/models output_format="markdown"
```

#### 4. Deployment Planning
```bash
>>> run deployment environment=production branch=main
```

---

## Configuration

### Agent Configuration

Agents are defined in `config/autogen_agents.yaml`:

```yaml
agents:
  code_analyzer:
    agent_type: "teachable_assistant"
    llm_config: "openrouter_config"
    system_message: |
      You are an expert code reviewer specializing in Python,
      JavaScript, and system architecture...
    tools:
      - "filesystem_read_file"
      - "codebasebuddy_search_code"
      - "memory_store_conversation"
    max_consecutive_auto_reply: 10
    timeout: 120
```

### LLM Configuration

Configure LLM providers in `config/autogen_agents.yaml`:

```yaml
llm_configs:
  openrouter_config:
    model: "openai/gpt-oss-120b"
    api_type: "openai"
    base_url: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"
    temperature: 0.3
    max_tokens: 4096
    functions: "auto"  # Enable function calling
```

### Workflow Configuration

Define workflows in `config/autogen_workflows.yaml`:

```yaml
workflows:
  quick_code_review:
    type: "two_agent"
    agents: ["code_analyzer", "user_proxy_executor"]
    initiator: "user_proxy_executor"
    max_turns: 3
    termination_keywords: ["TERMINATE", "REVIEW_COMPLETE"]
```

---

## Project Structure

```
automaton/
├── config/                       # YAML configuration files
│   ├── autogen_agents.yaml       # 8 agent definitions
│   ├── autogen_workflows.yaml    # 7 workflow definitions
│   ├── autogen_groupchats.yaml   # GroupChat patterns
│   ├── function_schemas.yaml     # MCP tool schemas
│   ├── config.yaml               # Application settings
│   └── config.production.yaml    # Production settings
│
├── src/                          # Source code (32 modules)
│   ├── autogen_adapters/         # AutoGen framework integration (4 modules)
│   ├── mcp/                      # MCP tool wrappers (7 modules)
│   ├── security/                 # Security layer (6 modules)
│   ├── memory/                   # Memory management (1 module)
│   ├── models/                   # LLM integrations (3 modules)
│   └── api/                      # Health check endpoints (1 module)
│
├── mcp_servers/                  # MCP server implementations
│   ├── github_server.py          # GitHub integration (Port 3000)
│   ├── filesystem_server.py      # File system access (Port 3001)
│   ├── memory_server.py          # Semantic memory (Port 3002)
│   └── codebasebuddy_server.py   # Code search (Port 3004)
│
├── tests/                        # Test suite
│   ├── test_autogen_agents.py    # Agent creation tests
│   ├── test_integration.py       # End-to-end tests
│   ├── test_mcp_servers.py       # MCP server tests
│   ├── diagnostics/              # Diagnostic tools (13 files)
│   └── root_tests/               # Additional test utilities
│
├── scripts/                      # Management scripts
│   ├── mcp_server_daemon.py      # Auto-start/stop servers
│   ├── mcp_server_watchdog.py    # Health monitoring
│   ├── windows/                  # Windows batch scripts
│   └── unix/                     # Unix shell scripts
│
├── docs/                         # Documentation
│   ├── API_REFERENCE.md          # Complete API reference
│   ├── QUICK_START.md            # 5-minute quick start
│   ├── SECURITY.md               # Security best practices
│   ├── TROUBLESHOOTING.md        # Common issues & solutions
│   ├── CODEBASEBUDDY_INTEGRATION.md  # Semantic search guide
│   ├── PROJECT_EXPLANATION.md    # Project overview
│   ├── guides/                   # Technical guides
│   └── archive/                  # Historical documentation
│
├── examples/                     # Usage examples
│   └── mcp_integration_example.py
│
├── data/                         # Data storage
│   └── teachable/                # Agent learning databases
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
├── main.py                       # Main entry point (CLI)
├── requirements.txt              # Python dependencies (65 packages)
├── .env.example                  # Environment variable template
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
└── ARCHITECTURE.md               # Technical architecture documentation
```

---

## MCP Servers

### Overview

The system uses 4 FastMCP servers for tool integration:

| Server | Port | Purpose | Key Functions |
|--------|------|---------|---------------|
| **GitHub** | 3000 | GitHub API operations | clone, commit, create_pr, search_code |
| **Filesystem** | 3001 | Local file access | read_file, write_file, list_directory |
| **Memory** | 3002 | Semantic memory | store_memory, search_memory, get_context |
| **CodeBaseBuddy** | 3004 | Code search | semantic_search, find_definition, find_usages |

### CodeBaseBuddy Interactive Chat

CodeBaseBuddy provides an interactive chat interface for exploring your codebase:

```bash
python scripts/codebasebuddy_interactive.py
```

**Available Commands:**
| Command | Description | Example |
|---------|-------------|---------|
| `search <query>` | Search code semantically | `search authentication logic` |
| `find <symbol>` | Find symbol definition | `find AgentFactory` |
| `find_usages <symbol>` | Find all usages of a symbol | `find_usages validate_parameters` |
| `analyze <path>` | Analyze file dependencies | `analyze src/mcp/` |
| `help` | Show all commands | `help` |
| `exit` | Exit the chat | `exit` |

**Natural Language Queries:**
```
CodeBaseBuddy> What agents are available in this project?
CodeBaseBuddy> How does the security module work?
CodeBaseBuddy> Where is the rate limiter configured?
CodeBaseBuddy> Show me the MCP server implementations
```

### Server Management

```bash
# Start all servers
python scripts/mcp_server_daemon.py start

# Check status
python scripts/mcp_server_daemon.py status

# Restart servers
python scripts/mcp_server_daemon.py restart

# Stop servers
python scripts/mcp_server_daemon.py stop

# Windows shortcuts
scripts\windows\start_servers.bat
scripts\windows\check_servers.bat
scripts\windows\restart_servers.bat
```

### Expected Status Output

```
MCP Server Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Server Name          PID      Port    Status
────────────────────────────────────────────────────
GitHub Server        12345    3000    running
Filesystem Server    12346    3001    running
Memory Server        12347    3002    running
CodeBaseBuddy Server 12348    3004    running
```

---

## Security Features

### Multi-Layer Security

```
┌─────────────────────────────────┐
│   Input Validation              │
│   • Path traversal prevention   │
│   • SQL injection detection     │
│   • Command injection blocking  │
└─────────────┬───────────────────┘
              │
┌─────────────▼───────────────────┐
│   Rate Limiting                 │
│   • 60 requests/minute          │
│   • 1000 requests/hour          │
└─────────────┬───────────────────┘
              │
┌─────────────▼───────────────────┐
│   Circuit Breaker               │
│   • Automatic failure detection │
│   • Service degradation         │
└─────────────┬───────────────────┘
              │
┌─────────────▼───────────────────┐
│   Log Sanitization              │
│   • Credential redaction        │
│   • PII removal                 │
└─────────────────────────────────┘
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
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_autogen_agents.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run diagnostics
python tests/diagnostics/diagnose_agents.py

# Environment check
python tests/diagnostics/check_env.py
```

### Code Quality

```bash
# Format code (line length 100)
black --line-length 100 src/ tests/ scripts/ mcp_servers/

# Sort imports
isort --line-length 100 --profile black src/ tests/

# Lint code
flake8 src/ tests/ --max-line-length=100

# Lint with Ruff (fast)
ruff check src/ tests/

# Type checking
mypy src/ --ignore-missing-imports

# Security scan
bandit -r src/
```

### Adding a New Agent

1. **Define agent** in `config/autogen_agents.yaml`:

```yaml
my_custom_agent:
  agent_type: "assistant"
  llm_config: "openrouter_config"
  system_message: |
    You are a specialized agent for...
  tools:
    - "filesystem_read_file"
    - "github_search_code"
```

2. **Register in workflow** (`config/autogen_workflows.yaml`):

```yaml
my_workflow:
  type: "two_agent"
  agents: ["my_custom_agent", "user_proxy_executor"]
  max_turns: 5
```

3. **Test the agent**:

```bash
>>> run my_workflow param1=value1
```

---

## Troubleshooting

### Common Issues

#### 1. "pyautogen is not installed"

**Solution:**
```bash
# Verify virtual environment is activated
which python  # Should show venv path

# Reinstall AutoGen
pip install --force-reinstall pyautogen autogen-agentchat
```

#### 2. OpenRouter API 401 Error

**Solution:**
- Verify `OPENROUTER_API_KEY` in `.env`
- Check API key at [openrouter.ai/keys](https://openrouter.ai/keys)
- Ensure `base_url` is `https://openrouter.ai/api/v1` in config

#### 3. Groq API Rate Limit

**Solution:**
- Groq free tier: 30 requests/minute
- Upgrade to paid tier or use OpenRouter fallback
- Configure rate limits in `config.yaml`

#### 4. MCP Servers Not Responding

**Solution:**
```bash
# Check server status
python scripts/mcp_server_daemon.py status

# Restart servers
python scripts/mcp_server_daemon.py restart

# Check logs
tail -f logs/mcp_servers/github.log
```

#### 5. CodeBaseBuddy Initialization Takes Long

**Solution:**
- First run indexes the codebase (30-60 seconds for large repos)
- Subsequent runs use cached embeddings (< 1 second)
- Check progress in `logs/mcp_servers/codebasebuddy.log`

### Debug Mode

Enable detailed logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG

# Run with verbose output
python main.py --verbose
```

### Getting Help

1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review logs: `logs/autogen_dev_assistant.log`
3. Run diagnostics: `python tests/diagnostics/diagnose_agents.py`
4. Open GitHub issue with logs and error details

---

## Performance

### Workflow Execution Times

| Workflow | Agents | Model | Avg Time | Throughput |
|----------|--------|-------|----------|------------|
| quick_code_review | 2 | openai/gpt-oss-120b | 3-5s | 12-20 reviews/min |
| code_analysis | 3+ | openai/gpt-oss-120b | 20-60s | 1-3 reviews/min |
| security_audit | 3+ | openai/gpt-oss-120b | 30-90s | 0.7-2 audits/min |

### Resource Usage

- **Memory**: 500MB - 2GB (model cache + embeddings)
- **CPU**: < 10% (inference is remote)
- **Disk**: 100MB logs + 500MB cache + 50MB data
- **Network**: 10KB - 500KB per request

---

## Documentation

### Core Documentation

- **[README.md](README.md)** - This file (overview and quick start)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design
- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Complete API documentation
- **[QUICK_START.md](docs/QUICK_START.md)** - 5-minute quick start guide
- **[SECURITY.md](docs/SECURITY.md)** - Security best practices
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Technical Guides

- **[PERFORMANCE_GUIDE.md](docs/guides/PERFORMANCE_GUIDE.md)** - Optimization tips
- **[SERVER_MANAGEMENT.md](docs/guides/SERVER_MANAGEMENT.md)** - MCP server admin
- **[TEST_GUIDE.md](docs/guides/TEST_GUIDE.md)** - Testing strategies
- **[CODEBASEBUDDY_INTEGRATION.md](docs/CODEBASEBUDDY_INTEGRATION.md)** - Semantic search setup

### Examples

- **[mcp_integration_example.py](examples/mcp_integration_example.py)** - Using MCP tools

---

## Contributing

Contributions are welcome! Please follow these guidelines:

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run code quality checks: `black`, `flake8`, `mypy`, `pytest`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Standards

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public APIs
- Maintain test coverage above 80%
- Update documentation for new features

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **[Microsoft AutoGen](https://microsoft.github.io/autogen/)** - Multi-agent conversation framework
- **[OpenRouter](https://openrouter.ai/)** - Unified LLM API (200+ models)
- **[Groq](https://groq.com/)** - Ultra-fast LLM inference
- **[Google Gemini](https://ai.google.dev/)** - Advanced language models
- **[FastMCP](https://github.com/jlowin/fastmcp)** - Model Context Protocol implementation
- **[CodeBaseBuddy](https://github.com/RyanLisse/codebase-buddy)** - Semantic code search

---

## Support

- **Documentation**: [docs/](docs/)
- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas

---

## Roadmap

### Planned Features

- [ ] Web UI interface (React + FastAPI)
- [ ] VS Code extension
- [ ] Additional LLM providers (Anthropic Claude, Cohere)
- [ ] More specialized agents (DevOps, Database, Frontend)
- [ ] Expanded MCP integrations (Jira, GitLab, Discord, Slack)
- [ ] Distributed execution (Celery task queue)
- [ ] Agent marketplace for sharing custom agents
- [ ] Real-time collaboration features
- [ ] Advanced analytics dashboard

### Version History

**v2.1.0** (December 22, 2024)
- Added CodeBaseBuddy interactive chat (`scripts/codebasebuddy_interactive.py`)
- Enhanced fallback search with YAML config file support
- Improved smart keyword extraction for natural language queries
- CI/CD pipeline with Black, isort, flake8, Ruff, and mypy
- Updated to Python 3.10+ (dropped 3.9 support due to fastmcp)
- Added `pyproject.toml` for unified tool configuration
- Consolidated GitHub Actions workflows into single `ci-cd.yml`

**v2.0.0** (December 18, 2024)
- Migrated from CrewAI to AutoGen framework
- Added CodeBaseBuddy semantic search integration
- Implemented 4 MCP servers with auto-start daemon
- Enhanced security layer (validation, rate limiting, circuit breakers)
- Added OpenRouter support (200+ models with function calling)
- Comprehensive test suite and diagnostics
- Production-ready configuration

**v1.0.0** (Initial Release)
- CrewAI-based multi-agent system
- Basic code review and security auditing
- Groq and Gemini LLM integration

---

**Built with ❤️ using Microsoft AutoGen**

*Last Updated: December 22, 2024*
