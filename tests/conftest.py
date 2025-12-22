import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "test_mode": True,
        "mcp_servers": {
            "github": {"port": 3000, "timeout": 5},
            "filesystem": {"port": 3001, "timeout": 5},
            "memory": {"port": 3002, "timeout": 5},
            "communication": {"port": 3003, "timeout": 5},
        },
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    return monkeypatch


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_code_file(temp_workspace):
    """Create sample code file for testing"""
    code_file = temp_workspace / "sample.py"
    code_file.write_text(
        '''
def hello_world():
    """Say hello"""
    return "Hello, World!"

class Calculator:
    def add(self, a, b):
        return a + b
'''
    )
    return code_file


from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
async def mock_mcp_manager():
    """Mock MCP Manager for integration tests"""
    manager = Mock()
    manager.start_all = AsyncMock()
    manager.stop_all = AsyncMock()
    manager.health_check_all = AsyncMock(
        return_value={
            "github": {"status": "healthy"},
            "filesystem": {"status": "healthy"},
            "memory": {"status": "healthy"},
            "codebasebuddy": {"status": "healthy"},
        }
    )
    manager.get_server = Mock(return_value=Mock())

    await manager.start_all()
    yield manager
    await manager.stop_all()
