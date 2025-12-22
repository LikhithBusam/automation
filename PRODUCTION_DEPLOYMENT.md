# Production Deployment Guide

## AutoGen Development Assistant - Industrial Grade Deployment

**Version:** 2.0.0
**Last Updated:** December 21, 2025
**Status:** Production Ready ✅

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Security Hardening](#security-hardening)
4. [MCP Server Setup](#mcp-server-setup)
5. [Model Configuration](#model-configuration)
6. [Deployment Checklist](#deployment-checklist)
7. [Monitoring & Logging](#monitoring--logging)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python:** 3.10, 3.11, or 3.12
- **RAM:** Minimum 8GB, Recommended 16GB
- **Disk:** 2GB for application + dependencies
- **OS:** Linux (Ubuntu 20.04+), Windows 10+, macOS 11+

### Required API Keys

```bash
# Required
OPENROUTER_API_KEY=your_openrouter_key_here

# Optional (but recommended)
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_api_key_here
GITHUB_TOKEN=your_github_token_here
SLACK_BOT_TOKEN=your_slack_token_here
HF_API_TOKEN=your_huggingface_token_here
```

### Dependencies Installation

```bash
# Clone repository
git clone https://github.com/your-org/automaton.git
cd automaton

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

---

## Configuration

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env
```

### 2. Configuration Files

#### Primary Configuration (`config/config.yaml`)

The system uses **OpenRouter API** by default with the following model:
- **Primary Model:** `mistralai/devstral-2512:free` (123B parameters)
- **Fallback Models:** `kwaipilot/kat-coder-pro:free`, `nex-agi/deepseek-v3.1-nex-n1:free`

**Key Configuration Sections:**

```yaml
models:
  openrouter:
    enabled: true
    api_key: "${OPENROUTER_API_KEY}"
    default_model: "mistralai/devstral-2512:free"
    max_retries: 3
    timeout: 120

mcp_servers:
  github:
    enabled: true
    port: 3000
  filesystem:
    enabled: true
    port: 3001
  memory:
    enabled: true
    port: 3002
  slack:
    enabled: false  # Enable if using Slack integration
    port: 3003
  codebasebuddy:
    enabled: true
    port: 3004
```

#### Agent Configuration (`config/autogen_agents.yaml`)

Defines 8 specialized agents:
1. **CodeAnalyzer** (TeachableAgent) - Code review and quality analysis
2. **SecurityAuditor** - Vulnerability scanning and OWASP compliance
3. **DocumentationAgent** - Technical writing and API docs
4. **DeploymentAgent** - CI/CD and infrastructure automation
5. **ResearchAgent** - Technology research and recommendations
6. **ProjectManager** - Orchestration and task coordination
7. **Executor** (UserProxyAgent) - Function execution
8. **UserProxyExecutor** - Human-in-the-loop interactions

---

## Security Hardening

### Input Validation

The system includes comprehensive input validation:

```python
from src.security.input_validator import validator

# Validate workflow parameters
validated_params = validator.validate_parameters(params)

# Validate MCP tool parameters
validated_tool_params = validator.validate_mcp_tool_params(
    tool_name="github",
    operation="create_pr",
    params={"owner": "org", "repo": "repo", "title": "Fix bug"}
)

# Validate paths (prevents path traversal)
safe_path = validator.validate_path(user_provided_path)
```

### Rate Limiting

Configured per MCP server:

```yaml
mcp_servers:
  github:
    rate_limit_minute: 60
    rate_limit_hour: 1000
    burst_size: 10

  filesystem:
    rate_limit_minute: 100
    rate_limit_hour: 2000
    burst_size: 20
```

### Authentication

For production deployments:

1. **API Key Rotation:** Rotate OpenRouter/Groq API keys every 90 days
2. **GitHub Token:** Use fine-grained personal access tokens with minimal scopes
3. **Environment Variables:** Never commit `.env` files to version control
4. **Secrets Management:** Use AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault

### Filesystem Security

The filesystem MCP server restricts access to allowed paths:

```yaml
filesystem:
  allowed_paths:
    - "./workspace"
    - "./projects"
    - "./src"
  blocked_patterns:
    - "\\.\\.\/"  # Directory traversal
    - "\/etc\/"   # System files
    - "\\.ssh\/"  # SSH keys
    - "\\.env$"   # Environment files
```

---

## MCP Server Setup

### Automatic Startup (Recommended)

```bash
# Start all MCP servers as daemon
python scripts/mcp_server_daemon.py start

# Check server status
python scripts/mcp_server_daemon.py status

# Stop all servers
python scripts/mcp_server_daemon.py stop

# Restart servers
python scripts/mcp_server_daemon.py restart
```

### Manual Startup

```bash
# GitHub MCP Server (Port 3000)
python mcp_servers/github_server.py &

# Filesystem MCP Server (Port 3001)
python mcp_servers/filesystem_server.py &

# Memory MCP Server (Port 3002)
python mcp_servers/memory_server.py &

# CodeBaseBuddy MCP Server (Port 3004)
python mcp_servers/codebasebuddy_server.py &
```

### Health Checks

```bash
# Check GitHub MCP
curl http://localhost:3000/health

# Check Filesystem MCP
curl http://localhost:3001/health

# Check Memory MCP
curl http://localhost:3002/health

# Check CodeBaseBuddy MCP
curl http://localhost:3004/health
```

Expected response:
```json
{"status": "healthy", "server": "github_mcp", "version": "2.0.0"}
```

---

## Model Configuration

### OpenRouter (Production - Default)

**Advantages:**
- 200+ models available
- No local GPU required
- Automatic failover between models
- Free tier available

**Configuration:**
```yaml
models:
  openrouter:
    enabled: true
    api_key: "${OPENROUTER_API_KEY}"
    default_model: "mistralai/devstral-2512:free"
```

**Get API Key:** https://openrouter.ai/keys

### Groq (High-Speed Inference)

**Advantages:**
- Ultra-fast inference (300+ tokens/sec)
- Free tier with generous limits
- LLaMA 3.1 and Mixtral models

**Configuration:**
```yaml
# Enable in agent_factory.py fallback logic
```

**Get API Key:** https://console.groq.com/keys

### Local Models (Development/Offline)

For offline development or sensitive data:

```yaml
models:
  local:
    enabled: true
    code_analyzer:
      primary: "codellama/CodeLlama-13b-Instruct-hf"
      quantization: "4bit"
      deployment: "local"
```

**Requirements:**
- 16GB+ RAM
- NVIDIA GPU with 8GB+ VRAM (recommended)
- Install: `torch`, `transformers`, `bitsandbytes`, `accelerate`

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Security scan clean (`bandit -r src/`)
- [ ] Code linting passed (`ruff check src/`)
- [ ] Type checking passed (`mypy src/`)
- [ ] Configuration validated
- [ ] API keys configured in `.env`
- [ ] MCP servers starting successfully
- [ ] Health checks passing

### Production Environment

- [ ] Use production configuration (`config.production.yaml`)
- [ ] Enable HTTPS for all MCP servers
- [ ] Set `code_execution_config.use_docker: true`
- [ ] Configure log rotation
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerting (Slack/PagerDuty)
- [ ] Backup strategy for memory database
- [ ] Disaster recovery plan documented

### Post-Deployment

- [ ] Verify all workflows execute successfully
- [ ] Monitor error rates
- [ ] Check API rate limits
- [ ] Review security logs
- [ ] Test agent responsiveness
- [ ] Validate memory persistence
- [ ] Confirm backup jobs running

---

## Monitoring & Logging

### Application Logs

Logs are written to `logs/dev_assistant.log` with JSON format:

```json
{
  "timestamp": "2025-12-21T10:30:45Z",
  "level": "INFO",
  "component": "conversation_manager",
  "message": "Workflow 'code_analysis' completed",
  "duration_seconds": 12.5,
  "status": "success"
}
```

### Log Levels

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  components:
    agents: "INFO"
    mcp: "DEBUG"
    models: "INFO"
    workflows: "INFO"
    memory: "DEBUG"
```

### Metrics to Monitor

1. **API Metrics:**
   - Request rate (req/min)
   - Error rate (%)
   - Latency (p50, p95, p99)

2. **Agent Metrics:**
   - Workflow success rate
   - Average workflow duration
   - Agent initialization time

3. **MCP Server Metrics:**
   - Connection pool utilization
   - Cache hit rate
   - Operation timeouts

4. **System Metrics:**
   - CPU usage
   - Memory usage
   - Disk I/O

### Prometheus Integration (Optional)

```python
# Add to main.py
from prometheus_client import start_http_server, Counter, Histogram

workflow_counter = Counter('workflow_executions_total', 'Total workflows')
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow duration')

start_http_server(8000)  # Metrics endpoint
```

---

## Troubleshooting

### Common Issues

#### 1. MCP Server Connection Failed

**Symptom:** `MCPConnectionError: Failed to connect to http://localhost:3000`

**Solutions:**
```bash
# Check if server is running
python scripts/mcp_server_daemon.py status

# Restart servers
python scripts/mcp_server_daemon.py restart

# Check port availability
netstat -an | grep 3000  # Linux/Mac
netstat -an | findstr 3000  # Windows
```

#### 2. OpenRouter API Rate Limit

**Symptom:** `RateLimitError: Rate limit exceeded`

**Solutions:**
- Wait for rate limit reset (usually 1 minute)
- Upgrade OpenRouter plan
- Enable Groq as fallback
- Implement request queuing

#### 3. Memory Database Corruption

**Symptom:** `MemoryCorruptionError: Failed to load memory database`

**Solutions:**
```bash
# Restore from backup
cp data/backups/memory_backup_latest.db data/memory.db

# Rebuild memory index
python scripts/rebuild_memory.py

# Clear and reinitialize
rm data/memory.db
python scripts/initialize_memory.py
```

#### 4. Agent Initialization Timeout

**Symptom:** `AgentInitializationError: Agent 'code_analyzer' failed to initialize`

**Solutions:**
- Check OpenRouter API key validity
- Verify network connectivity
- Increase timeout in `config.yaml`
- Check model availability

#### 5. Workflow Execution Fails

**Symptom:** `WorkflowExecutionError: Workflow 'code_analysis' failed`

**Solutions:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run diagnostic script
python tests/diagnostics/diagnose_workflows.py

# Check workflow configuration
python scripts/validate_config.py
```

### Performance Optimization

#### High Latency

1. **Enable Caching:**
```yaml
performance:
  caching:
    enabled: true
    cache_backend: "redis"
    prompt_cache_ttl: 3600
```

2. **Use Groq for Fast Inference:**
```python
# Switch to Groq in agent config
llm_config:
  model: "groq/llama-3.1-70b-versatile"
```

3. **Optimize Batch Size:**
```yaml
performance:
  batch_size: 4
  max_concurrent_inferences: 3
```

#### High Memory Usage

1. **Limit Memory Storage:**
```yaml
memory:
  long_term:
    max_entries: 50000  # Reduce from 100000
```

2. **Enable Memory Pruning:**
```python
# Automatic pruning every 24 hours
from src.memory.memory_manager import memory_manager
await memory_manager.prune(max_age_days=30, max_count=10000)
```

3. **Reduce Context Window:**
```yaml
memory:
  context_window_size: 2048  # Reduce from 4096
  max_context_entries: 3  # Reduce from 5
```

---

## Support & Documentation

- **GitHub Issues:** https://github.com/your-org/automaton/issues
- **Documentation:** `/docs` directory
- **API Reference:** `docs/API_REFERENCE.md`
- **Architecture:** `docs/ARCHITECTURE.md`

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Deployment Date:** ___________
**Deployed By:** ___________
**Environment:** [ ] Development [ ] Staging [ ] Production
**Sign-off:** ___________
