"""
Pytest fixtures for integration tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    return {
        "models": {
            "default": {
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "test_key"
            }
        },
        "mcp_servers": {
            "github": {
                "port": 3000,
                "enabled": True
            },
            "filesystem": {
                "port": 3001,
                "enabled": True
            }
        },
        "agents": {
            "code_analyzer": {
                "enabled": True,
                "tools": ["github", "filesystem"]
            }
        }
    }


@pytest.fixture
def mock_tool_manager():
    """Create mock tool manager"""
    manager = Mock()
    manager.execute = AsyncMock()
    manager.get_tool = Mock()
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    return manager


@pytest.fixture
def mock_memory_manager():
    """Create mock memory manager"""
    manager = Mock()
    manager.store = AsyncMock()
    manager.retrieve = AsyncMock()
    manager.search = AsyncMock(return_value=[])
    return manager

