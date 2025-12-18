# AutoGen Development Assistant

> **Multi-Agent AI System for Code Analysis, Security Auditing, and Development Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AutoGen](https://img.shields.io/badge/AutoGen-0.9.9+-green.svg)](https://microsoft.github.io/autogen/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🚀 Overview

**AutoGen Development Assistant** is a production-ready, multi-agent AI system built on Microsoft's AutoGen framework. It provides intelligent code analysis, security auditing, documentation generation, and deployment automation through collaborative AI agents powered by Groq and Google Gemini.

### Key Features

- ✅ **Multi-Agent Collaboration** - 8 specialized AI agents working together
- ✅ **Fast Code Reviews** - Complete code analysis in 3-5 seconds
- ✅ **Security Auditing** - Deep vulnerability assessment and OWASP compliance
- ✅ **MCP Integration** - FastMCP servers for GitHub, Filesystem, Memory, and Slack
- ✅ **Workflow Orchestration** - 8 pre-configured workflows for common tasks
- ✅ **Production Ready** - Docker support, monitoring, and comprehensive logging

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Workflows](#-workflows)
- [Configuration](#%EF%B8%8F-configuration)
- [Development](#-development)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10 or higher
- Virtual environment (venv)
- API Keys: Groq API, Google Gemini (optional)

### Installation (30 seconds)

```bash
# Clone the repository
git clone <repository-url>
cd automaton

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Start MCP Servers

Before running the system, start the MCP servers:

**Windows:**
```bash
scripts\windows\start_servers.bat
```

**Unix/macOS:**
```bash
python scripts/mcp_server_daemon.py start
```

This will start all 4 MCP servers in the background (GitHub, Filesystem, Memory, CodeBaseBuddy).

### Run the System

**Windows:**
```bash
scripts\windows\run.bat
```

**Unix/macOS:**
```bash
bash scripts/unix/run.sh
```

### Simple Code Review (Alternative)

```bash
python tests/diagnostics/simple_code_review.py ./main.py "error handling, security"
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (CLI)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Conversation Manager                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Workflows  │  │  GroupChats  │  │  Two-Agent   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Agent Factory                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │   Code     │ │  Security  │ │    Docs    │ │  Deploy │ │
│  │  Analyzer  │ │  Auditor   │ │   Writer   │ │  Agent  │ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │  Research  │ │  Project   │ │  Executor  │ │  User   │ │
│  │   Agent    │ │   Manager  │ │            │ │  Proxy  │ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  MCP Tool Manager                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  GitHub  │  │Filesystem│  │  Memory  │  │  Slack   │   │
│  │   MCP    │  │   MCP    │  │   MCP    │  │   MCP    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   LLM Providers                             │
│  ┌──────────────────┐           ┌──────────────────┐       │
│  │  Groq API        │           │  Google Gemini   │       │
│  │  llama-3.1-8b    │           │  gemini-2.5      │       │
│  └──────────────────┘           └──────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Purpose | Model |
|-------|---------|-------|
| **Code Analyzer** | Code review, quality analysis, best practices | llama-3.1-8b-instant |
| **Security Auditor** | Vulnerability scanning, OWASP compliance | llama-3.1-8b-instant |
| **Documentation Agent** | Generate/update documentation | llama-3.1-70b-versatile |
| **Deployment Agent** | Deployment automation, CI/CD | llama-3.1-8b-instant |
| **Research Agent** | Technology research, best practices | llama-3.1-70b-versatile |
| **Project Manager** | Orchestration, task planning | llama-3.1-8b-instant |
| **Executor** | Code execution, testing | N/A (UserProxyAgent) |
| **User Proxy** | User interaction, human-in-the-loop | N/A (UserProxyAgent) |

---

## 💻 Installation

### 1. System Requirements

- **OS**: Windows 10+, Ubuntu 20.04+, macOS 11+
- **Python**: 3.10, 3.11, 3.12, or 3.13
- **Memory**: 4GB+ RAM recommended
- **Disk**: 2GB free space (excluding model cache)

### 2. Clone Repository

```bash
git clone <repository-url>
cd automaton
```

### 3. Virtual Environment Setup

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Unix/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
python -c "import autogen; print('AutoGen:', autogen.__version__)"
```

### 5. Environment Configuration

Create `.env` file in the root directory:

```bash
# LLM API Keys
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here  # Optional

# MCP Server Configuration
MCP_GITHUB_TOKEN=your_github_token_here  # Optional
MCP_SLACK_TOKEN=your_slack_token_here    # Optional

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
```

**Get API Keys:**
- Groq: [https://console.groq.com/keys](https://console.groq.com/keys)
- Google Gemini: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

### 6. Verify Installation

```bash
# Run diagnostics
python tests/diagnostics/check_env.py

# Expected output:
# [OK] AutoGen imports work!
# [OK] Agent factory imports!
# HAS_AUTOGEN: True
# [OK] Agent created: UserProxyAgent
```

---

## 🎯 Usage

### Interactive Mode

Start the interactive CLI:

```bash
# Windows
scripts\windows\run.bat

# Unix/macOS
bash scripts/unix/run.sh
```

**Available Commands:**

```
>>> help              # Show help message
>>> list              # List available workflows
>>> history           # Show execution history
>>> run <workflow> [params...]  # Execute workflow
>>> exit              # Exit application
```

### Example: Code Review

```bash
>>> run quick_code_review code_path=./main.py focus_areas="error handling, security"
```

Output:
```
Executing workflow: quick_code_review
Parameters: {'code_path': './main.py', 'focus_areas': 'error handling, security'}

CodeAnalyzer (to Executor):
[Agent reads file and analyzes code...]

Summary:
Two-agent conversation completed with 5 messages
Duration: 3.47s
Tasks: 1 completed, 0 failed
```

### Standalone Code Review

For quick code reviews without the full system:

```bash
python tests/diagnostics/simple_code_review.py <file_path> "[focus_areas]"

# Example:
python tests/diagnostics/simple_code_review.py ./src/main.py "security, performance"
```

---

## 📊 Workflows

### Available Workflows

| Workflow | Type | Description | Duration |
|----------|------|-------------|----------|
| `quick_code_review` | Two-Agent | Fast code review for small changes | 3-5s |
| `code_analysis` | GroupChat | Comprehensive code review with security checks | 20-60s |
| `security_audit` | GroupChat | Deep security vulnerability assessment | 30-90s |
| `documentation_generation` | Two-Agent | Generate/update project documentation | 10-30s |
| `deployment` | Two-Agent | Execute deployment to target environment | 15-45s |
| `research` | Two-Agent | Research technologies and best practices | 20-60s |
| `quick_documentation` | Two-Agent | Quick documentation update | 5-15s |
| `comprehensive_feature_review` | GroupChat | Full feature review with multiple agents | 60-180s |

### Workflow Examples

#### 1. Quick Code Review
```bash
>>> run quick_code_review code_path=./src/api/routes.py focus_areas="error handling"
```

#### 2. Security Audit
```bash
>>> run security_audit target_path=./src focus_areas="SQL injection, XSS, CSRF"
```

#### 3. Documentation Generation
```bash
>>> run documentation_generation module_path=./src/models output_path=./docs/api
```

#### 4. Deployment
```bash
>>> run deployment environment=staging branch=develop
```

---

## ⚙️ Configuration

### Agent Configuration

Edit `config/autogen_agents.yaml`:

```yaml
llm_configs:
  code_analysis_config:
    model: "llama-3.1-8b-instant"
    api_type: "openai"
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"
    temperature: 0.3
    max_tokens: 4096
```

### Workflow Configuration

Edit `config/autogen_workflows.yaml`:

```yaml
quick_code_review:
  type: "two_agent"
  agents: ["code_analyzer", "user_proxy_executor"]
  initiator: "user_proxy_executor"
  max_turns: 3
  termination_keywords: ["TERMINATE", "REVIEW_COMPLETE"]
```

### MCP Server Configuration

Start MCP servers:

```bash
# Windows
scripts\windows\start_servers.bat

# Unix/macOS
bash scripts/unix/start_servers.sh
```

Check server status:

```bash
scripts\windows\check_servers.bat
```

---

## 🛠️ Development

### Project Structure

```
automaton/
├── config/                 # Configuration files (YAML)
├── src/                    # Source code
│   ├── autogen_adapters/   # AutoGen framework integration
│   ├── mcp/                # MCP tool implementations
│   ├── models/             # LLM provider integrations
│   ├── memory/             # Memory management
│   └── security/           # Security utilities
├── tests/                  # Test suite
│   └── diagnostics/        # Diagnostic tools
├── scripts/                # Management scripts
│   ├── windows/            # Windows batch scripts
│   └── unix/               # Unix shell scripts
├── docs/                   # Documentation
│   ├── guides/             # Technical guides
│   └── archive/            # Historical documentation
├── mcp_servers/            # MCP server implementations
├── examples/               # Usage examples
├── main.py                 # Main entry point
└── README.md               # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_autogen_agents.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run diagnostics
python tests/diagnostics/diagnose_agents.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Adding a New Agent

1. Define agent in `config/autogen_agents.yaml`:

```yaml
my_custom_agent:
  agent_type: "assistant"
  llm_config: "code_analysis_config"
  system_message: |
    You are a specialized agent for...
```

2. Register agent in workflow (`config/autogen_workflows.yaml`):

```yaml
my_workflow:
  type: "two_agent"
  agents: ["my_custom_agent", "user_proxy_executor"]
```

3. Test the agent:

```bash
>>> run my_workflow param1=value1
```

---

## 📚 Documentation

### Core Documentation

- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in 5 minutes
- **[Security Guide](docs/SECURITY.md)** - Security best practices
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Technical Guides

- **[Performance Guide](docs/guides/PERFORMANCE_GUIDE.md)** - Optimization tips
- **[Server Management](docs/guides/SERVER_MANAGEMENT.md)** - MCP server administration
- **[Test Guide](docs/guides/TEST_GUIDE.md)** - Testing strategies

### Examples

- **[MCP Integration Example](examples/mcp_integration_example.py)** - Using MCP tools

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "pyautogen is not installed"

**Solution:**
```bash
# Verify virtual environment is activated
where python  # Windows
which python  # Unix

# Reinstall autogen
pip install --force-reinstall pyautogen autogen-agentchat
```

#### 2. Groq API 401 Error

**Solution:**
- Verify `GROQ_API_KEY` in `.env`
- Check API key is valid at [console.groq.com](https://console.groq.com)
- Ensure `base_url` is set in agent configuration

#### 3. Model Decommissioned Error

**Solution:**
Update `config/autogen_agents.yaml` to use available models:
- ✅ `llama-3.1-8b-instant`
- ✅ `llama-3.1-70b-versatile`
- ❌ `mixtral-8x7b-32768` (decommissioned)

#### 4. MCP Servers Not Responding

**Current Status:**
- All 4 servers (GitHub, Filesystem, Memory, CodeBaseBuddy) are automatically started by the daemon

**Solution:**
```bash
# Check server status
scripts\windows\check_servers.bat

# Or use daemon
python scripts/mcp_server_daemon.py status

# Restart servers
scripts\windows\restart_servers.bat

# Or use daemon
python scripts/mcp_server_daemon.py restart

# Expected output (4 servers):
# GitHub Server         - PID: XXXX - Port: 3000 - Status: running
# Filesystem Server     - PID: XXXX - Port: 3001 - Status: running
# Memory Server         - PID: XXXX - Port: 3002 - Status: running
# CodeBaseBuddy Server  - PID: XXXX - Port: 3004 - Status: running
```

### Debug Mode

Enable debug logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG

# Run with verbose output
python main.py --verbose
```

### Getting Help

1. Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
2. Review logs in `logs/autogen_dev_assistant.log`
3. Run diagnostics: `python tests/diagnostics/diagnose_agents.py`
4. Open an issue on GitHub

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Run code quality checks before committing

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Microsoft AutoGen** - Multi-agent conversation framework
- **Groq** - Fast LLM inference
- **Google Gemini** - Advanced language models
- **FastMCP** - Model Context Protocol implementation

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

## 🚀 What's Next?

- [ ] Add support for more LLM providers (Anthropic, OpenAI)
- [ ] Implement web UI interface
- [ ] Add more specialized agents (DevOps, Database, Frontend)
- [ ] Expand MCP tool integrations (Jira, GitLab, Discord)
- [ ] Create agent marketplace for sharing custom agents

---

**Built with ❤️ using Microsoft AutoGen**

---

## 📝 Recent Updates

**December 18, 2025 (v2):**
- ✅ **Added CodeBaseBuddy to auto-start** - All 4 MCP servers now start automatically via daemon
- ✅ Updated daemon configuration to include CodeBaseBuddy server (Port 3004)
- ✅ Verified all 4 servers running: GitHub, Filesystem, Memory, CodeBaseBuddy
- ✅ Updated documentation throughout to reflect 4-server auto-start configuration

**December 18, 2025 (v1):**
- ✅ Clarified MCP server configuration: 3 core servers (GitHub, Filesystem, Memory) auto-start via daemon
- ✅ Updated documentation to reflect CodeBaseBuddy as optional manual-start server
- ✅ Added comprehensive server management instructions
- ✅ Corrected architecture diagram and server status indicators

*Last Updated: December 18, 2025*
