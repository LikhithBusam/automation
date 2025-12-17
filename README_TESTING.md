# Testing Guide

## Quick Start

### Install Test Dependencies

```bash
pip install pytest pytest-cov pytest-html pytest-asyncio requests
```

### Run All Tests

```bash
python run_tests.py
```

### Run Specific Test Types

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# MCP server tests
python run_tests.py mcp

# Agent tests
python run_tests.py agent

# Quick tests (skip slow ones)
python run_tests.py quick
```

### Run with Pytest Directly

```bash
# All tests
pytest

# Specific file
pytest tests/test_mcp_servers.py

# Specific test
pytest tests/test_mcp_servers.py::TestMCPServerHealth::test_github_server_health

# With coverage
pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── test_mcp_servers.py         # MCP server health and operations
├── test_autogen_agents.py      # AutoGen agent tests
└── test_integration.py         # Integration tests
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.mcp` - MCP server tests
- `@pytest.mark.agent` - AutoGen agent tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_api` - Tests requiring API keys

## Coverage Reports

After running tests with coverage:

```bash
# View HTML report
start reports/coverage/index.html  # Windows
open reports/coverage/index.html   # Mac
xdg-open reports/coverage/index.html  # Linux
```

## CI/CD Integration

The test suite generates JUnit XML reports for CI/CD integration:

```bash
pytest --junit-xml=reports/junit.xml
```

## Writing New Tests

### Test File Naming

- `test_*.py` for test files
- `Test*` for test classes
- `test_*` for test functions

### Example Test

```python
import pytest

class TestMyFeature:
    """Test my feature"""

    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic functionality"""
        result = my_function()
        assert result == expected_value

    @pytest.mark.integration
    def test_with_dependencies(self, sample_code_file):
        """Test with dependencies"""
        # Use fixtures
        assert sample_code_file.exists()
```

## Fixtures Available

- `test_config` - Test configuration dictionary
- `mock_env` - Mock environment variables
- `temp_workspace` - Temporary workspace directory
- `sample_code_file` - Sample Python file for testing

## Troubleshooting

### Tests Skipped

Some tests may be skipped if:
- MCP servers are not running
- Required API keys are missing
- Optional dependencies not installed

This is normal - tests will skip gracefully with a message.

### Failed Tests

Check:
1. All dependencies installed: `pip install -r requirements.txt`
2. Environment variables set in `.env`
3. MCP servers running if testing integration

## Production Testing

For production environments:

```bash
# Run only critical tests
pytest -m "not slow and not requires_api"

# Generate comprehensive report
pytest --html=reports/test_report.html --self-contained-html
```
