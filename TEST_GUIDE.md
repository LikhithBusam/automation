# Complete Testing Guide for Automaton

## System Status from Error Log

❌ **Current Issues:**
- Agents failing to register: `unhashable type: 'list'` error
- Config has agents that don't have factories (`dev_workflow`, `communication`, `code_generation`, `memory`)
- 0 agents loaded successfully

✅ **What's Working:**
- MCP Tool Manager configured
- Memory Manager initialized
- Model Factory ready
- 4 MCP servers configured (github, filesystem, memory, slack)

---

## Testing Roadmap

### Phase 1: Test MCP Servers (Basic Infrastructure)

#### Step 1.1: Start All MCP Servers

Open **4 separate terminal windows** and run:

**Terminal 1 - GitHub Server (Port 3000):**
```bash
cd c:\Users\Likith\OneDrive\Desktop\automaton
python mcp_servers\github_server.py
```

**Terminal 2 - Filesystem Server (Port 3001):**
```bash
cd c:\Users\Likith\OneDrive\Desktop\automaton
python mcp_servers\filesystem_server.py
```

**Terminal 3 - Memory Server (Port 3002):**
```bash
cd c:\Users\Likith\OneDrive\Desktop\automaton
python mcp_servers\memory_server.py
```

**Terminal 4 - Slack Server (Port 3003) - Optional:**
```bash
cd c:\Users\Likith\OneDrive\Desktop\automaton
python mcp_servers\slack_server.py
```

**Expected Output (each server):**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:3000 (Press CTRL+C to quit)
```

#### Step 1.2: Run Comprehensive MCP Server Tests

In a **5th terminal:**

```bash
cd c:\Users\Likith\OneDrive\Desktop\automaton
python test_mcp_servers.py
```

**What This Tests:**
- ✅ Health checks for all servers
- ✅ GitHub operations (list repos, get PRs, search code)
- ✅ Filesystem operations with security (read/write/list/search)
- ✅ Memory operations (store/retrieve/search/delete)
- ✅ Load testing (concurrent requests)
- ✅ Integration tests (cross-server workflows)

**Expected Output:**
```
🧪 MCP Server Comprehensive Test Suite
📡 Phase 1: Server Health Checks
  ✅ PASS health_check_github (23.5ms)
  ✅ PASS health_check_filesystem (12.1ms)
  ✅ PASS health_check_memory (15.3ms)
...
📊 Test Summary
PASSED
Total: 45 | Passed: 43 | Failed: 2 | Errors: 0
Pass Rate: 95.6% | Duration: 3245ms
```

**Reports Generated:**
- JSON: `test_reports/test_report_YYYYMMDD_HHMMSS.json`
- HTML: `test_reports/test_report_YYYYMMDD_HHMMSS.html`

---

### Phase 2: Fix Agent Registration Issues

The main error `unhashable type: 'list'` occurs because:
1. `AgentConfig.tools` is a `List[str]`
2. Somewhere in the code path, this list is being used as a dict key or in a set

#### Option A: Quick Fix - Disable Problematic Agents

Edit [config/config.yaml](config/config.yaml):

```yaml
agents:
  code_analyzer:
    enabled: true  # Keep this
    # ...

  documentation:
    enabled: true  # Keep this
    # ...

  dev_workflow:
    enabled: false  # Disable - no factory exists
    # ...

  communication:
    enabled: false  # Disable - no factory exists
    # ...

  code_generation:
    enabled: false  # Disable - no factory exists
    # ...

  memory:
    enabled: false  # Disable - no factory exists
    # ...
```

Then restart: `python main.py`

#### Option B: Proper Fix - Debug Hash Issue

The issue is likely in CrewAI's Agent creation or how tools are passed. Check:

1. **CrewAI Version**: Update to latest
   ```bash
   pip install --upgrade crewai
   ```

2. **Debug Tools**: Add debug logging in `base_agent.py` line 292:
   ```python
   tools = self.tool_manager.get_tools_for_agent(self.config.tools)
   print(f"DEBUG: tools type = {type(tools)}, tools = {tools}")
   ```

---

### Phase 3: Test Individual Components

#### Test 1: MCP Tool Manager

Create `test_tool_manager.py`:
```python
import asyncio
from src.mcp.tool_manager import MCPToolManager
from pathlib import Path
import yaml

async def test():
    # Load config
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialize
    tool_manager = MCPToolManager(config)

    # Health check
    health = await tool_manager.health_check()
    print("MCP Server Health:", health)

    # Get tools for agent
    tools = tool_manager.get_tools_for_agent(["github", "filesystem"])
    print(f"Tools retrieved: {len(tools)} tools")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

asyncio.run(test())
```

Run: `python test_tool_manager.py`

#### Test 2: Memory Manager

Create `test_memory.py`:
```python
import asyncio
from src.memory.memory_manager import MemoryManager, MemoryTier, MemoryType
import yaml

async def test():
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    memory_manager = MemoryManager(config["memory"])

    # Store memory
    mem_id = await memory_manager.store(
        key="test_key",
        value="Test content",
        tier=MemoryTier.SHORT_TERM,
        memory_type=MemoryType.PATTERN,
        tags=["test"]
    )
    print(f"Stored memory: {mem_id}")

    # Retrieve
    result = await memory_manager.retrieve("test_key")
    print(f"Retrieved: {result}")

    # Stats
    stats = await memory_manager.get_statistics()
    print(f"Memory stats: {stats}")

asyncio.run(test())
```

Run: `python test_memory.py`

#### Test 3: Model Factory

Create `test_models.py`:
```python
from src.models.model_factory import ModelFactory
import yaml

# Load config
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

factory = ModelFactory(config)

# Check model configuration
print("Configured models:")
for agent_name in ["code_analyzer", "documentation"]:
    model_config = factory.config.get("models", {}).get(agent_name, {})
    print(f"  {agent_name}:")
    print(f"    - Primary: {model_config.get('primary')}")
    print(f"    - Deployment: {model_config.get('deployment')}")
    print(f"    - Quantization: {model_config.get('quantization')}")

# Try loading a model (if deployment is local)
# WARNING: This will download models!
try:
    model = factory.get_model("documentation")
    print(f"Model loaded successfully: {type(model)}")
except Exception as e:
    print(f"Model loading failed (expected if no GPU): {e}")
```

Run: `python test_models.py`

---

### Phase 4: Test Working Agents

Once you fix the agent registration, test each agent:

#### Test Code Analyzer Agent

```bash
python main.py
>>> analyze ./src --security
```

Expected:
- Agent loads successfully
- Analyzes files in ./src
- Returns security audit report

#### Test Documentation Agent

```bash
python main.py
>>> docs ./src --type=readme
```

Expected:
- Generates README documentation
- Uses filesystem tool to read files
- Returns markdown output

#### Test Full Workflow

```bash
python main.py
>>> workflow code_analysis ./src
```

Expected:
- Runs complete code analysis workflow
- Multiple agents collaborate
- Returns comprehensive report

---

## Manual Testing Checklist

### MCP Servers
- [ ] GitHub server responds to health check
- [ ] Filesystem server can read/write files
- [ ] Memory server can store/retrieve memories
- [ ] Rate limiting works (concurrent requests)
- [ ] Security: Directory traversal blocked
- [ ] Security: .env files blocked

### Agents
- [ ] Code analyzer agent registers successfully
- [ ] Documentation agent registers successfully
- [ ] Deployment agent registers successfully
- [ ] Research agent registers successfully
- [ ] Project manager agent registers successfully

### Tools Integration
- [ ] Agents can access GitHub tool
- [ ] Agents can access Filesystem tool
- [ ] Agents can access Memory tool
- [ ] Tool calls are rate-limited properly
- [ ] Tool caching works

### Memory System
- [ ] Short-term memory stores/retrieves
- [ ] Medium-term memory persists
- [ ] Long-term memory persists
- [ ] Semantic search works
- [ ] Memory cleanup runs

### Models
- [ ] Models load successfully (or via API)
- [ ] Quantization works (4-bit/8-bit)
- [ ] Model inference completes
- [ ] Token usage tracked

---

## Troubleshooting

### Issue: "unhashable type: 'list'"

**Cause:** `AgentConfig.tools` (a list) is being used as dict key somewhere

**Solutions:**
1. Update CrewAI: `pip install --upgrade crewai`
2. Check Pydantic version: `pip install pydantic==2.10.4`
3. Disable agents without factories in config.yaml
4. Add debug logging to identify exact location

### Issue: "No factory for agent type"

**Cause:** Config has agents without factory functions

**Solution:** Disable in config.yaml:
```yaml
dev_workflow:
  enabled: false
```

### Issue: MCP Servers not running

**Check:**
```bash
curl http://localhost:3000/health  # GitHub
curl http://localhost:3001/health  # Filesystem
curl http://localhost:3002/health  # Memory
```

**Fix:** Start servers in separate terminals

### Issue: Model loading fails

**Check GPU:**
```python
import torch
print(torch.cuda.is_available())
```

**Fix:** Use API deployment instead:
```yaml
models:
  code_analyzer:
    deployment: "hf_api"  # Change from "local"
```

---

## Success Criteria

✅ **MCP Servers:**
- All 3 servers start without errors
- Health checks pass (95%+ pass rate)
- Security tests pass (directory traversal blocked)

✅ **Agents:**
- At least 2 agents register successfully
- No "unhashable type" errors
- Agents respond to commands

✅ **Integration:**
- Workflow completes end-to-end
- Reports generated successfully
- Memory persists between sessions

---

## Next Steps After Testing

1. **Performance Testing:**
   - Load test with 50+ concurrent requests
   - Measure model inference time
   - Check memory usage patterns

2. **Real Workload Testing:**
   - Analyze actual codebase
   - Generate real documentation
   - Test deployment workflows

3. **Error Recovery:**
   - Kill servers mid-workflow (test retry logic)
   - Cause tool failures (test fallbacks)
   - Exceed rate limits (test backoff)

---

## Test Reports Location

After running tests, check:
- `./test_reports/` - Test reports (JSON + HTML)
- `./logs/dev_assistant.log` - Application logs
- `./state/app_state.json` - Application state

---

**Last Updated:** 2025-12-07
**Version:** 1.0
