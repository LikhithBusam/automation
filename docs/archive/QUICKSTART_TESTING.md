# Quick Start - Testing Framework

## 🚀 Get Started in 3 Minutes

### 1. Install Dependencies (1 min)

```bash
# Install all test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-html pytest-json-report pytest-xdist httpx pyyaml psutil
```

### 2. Start MCP Servers (Optional - 30 sec)

```bash
# Start MCP servers for integration tests
python start_mcp_servers.py
```

**Note**: If MCP servers aren't running, tests will skip gracefully with informative messages.

### 3. Run Tests (1 min)

```bash
# Quick run - unit tests only
python run_tests.py -c unit

# Full run - all tests
python run_tests.py

# With coverage report
python run_tests.py -c unit --coverage
```

---

## 📊 What You'll See

```
================================================================================
AutoGen Testing Framework - Test Execution
================================================================================
Start time: 2024-01-01 12:00:00

Command: pytest tests/ -m unit -q ...

tests/test_autogen_agents.py ........                                    [ 40%]
tests/test_mcp_servers.py ............                                   [ 80%]
tests/test_workflows.py ....                                             [100%]

================================================================================
Test Summary
================================================================================
Total:   24
Passed:  20
Failed:  0
Skipped: 4
Duration: 2.35s

Reports generated:
  HTML:  tests/reports/report.html
  JSON:  tests/reports/report.json
  JUnit: tests/reports/junit.xml

================================================================================
End time: 2024-01-01 12:00:02
================================================================================
```

---

## 🎯 Common Commands

### By Category

```bash
# Unit tests (fast, no dependencies)
python run_tests.py -c unit

# Component tests (single modules)
python run_tests.py -c component

# Integration tests (multiple components)
python run_tests.py -c integration

# End-to-end tests (full workflows)
python run_tests.py -c e2e

# Performance tests
python run_tests.py -c performance

# Security tests
python run_tests.py -c security
```

### By Speed

```bash
# Fast tests only (unit + component)
python run_tests.py -c unit -c component

# Skip slow tests
pytest -m "not slow"

# Parallel execution (faster)
python run_tests.py --parallel
```

### With Reports

```bash
# Generate HTML report
python run_tests.py -c unit

# Generate coverage report
python run_tests.py -c unit --coverage

# Verbose output
python run_tests.py -c unit -v
```

---

## 📁 View Reports

### HTML Report (Visual)
1. Run tests: `python run_tests.py -c unit`
2. Open: `tests/reports/report.html`
3. View: Test results, execution times, errors

### Coverage Report (Code Coverage)
1. Run with coverage: `python run_tests.py --coverage`
2. Open: `htmlcov/index.html`
3. View: Line-by-line coverage, missing lines

### JSON Report (Programmatic)
- Location: `tests/reports/report.json`
- Use for: Parsing results, CI/CD integration

---

## 🔍 Specific Tests

```bash
# Run specific file
pytest tests/test_autogen_agents.py -v

# Run specific class
pytest tests/test_autogen_agents.py::TestAgentInitialization -v

# Run specific test
pytest tests/test_autogen_agents.py::TestAgentInitialization::test_create_assistant_agent -v
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install pytest pytest-asyncio
```

### "MCP server not available" (tests skipped)
```bash
# Option 1: Start MCP servers
python start_mcp_servers.py

# Option 2: Skip MCP tests
pytest -m "not requires_mcp"
```

### "ImportError: No module named 'autogen'"
```bash
pip install pyautogen
```

### Tests run but no reports generated
```bash
# Create reports directory
mkdir -p tests/reports

# Run again
python run_tests.py -c unit
```

---

## 📚 Next Steps

### Learn More
- Read: `tests/README.md` - Comprehensive testing guide
- Read: `TESTING_SUMMARY.md` - Complete implementation details

### Run Full Suite
```bash
# Run everything with coverage
python run_tests.py --parallel --coverage
```

### Contribute Tests
1. Choose test category (unit, component, integration, e2e, performance, security)
2. Create test in appropriate file
3. Use AAA pattern (Arrange-Act-Assert)
4. Add appropriate markers
5. Run locally to verify
6. Commit and push

---

## ✅ Quick Checklist

- [ ] Install dependencies: `pip install pytest pytest-asyncio ...`
- [ ] Run unit tests: `python run_tests.py -c unit`
- [ ] View HTML report: Open `tests/reports/report.html`
- [ ] (Optional) Start MCP servers: `python start_mcp_servers.py`
- [ ] (Optional) Run integration tests: `python run_tests.py -c integration`
- [ ] (Optional) Generate coverage: `python run_tests.py --coverage`

---

## 🎉 You're Ready!

The testing framework is set up and ready to use. Start with unit tests and gradually explore integration, E2E, performance, and security tests.

**Questions?** Check `tests/README.md` or `TESTING_SUMMARY.md`

**Happy Testing! 🚀**
