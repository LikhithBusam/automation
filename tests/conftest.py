"""
Pytest Configuration and Fixtures
"""

import pytest
import asyncio
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, Mock

# Test fixtures and factories


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return {
        "content": "Mock LLM response",
        "tokens_used": 100,
        "model": "gpt-4"
    }


@pytest.fixture
def mock_llm():
    """Mock LLM client"""
    mock = AsyncMock()
    mock.generate.return_value = {
        "content": "Mock LLM response",
        "tokens_used": 100,
        "model": "gpt-4"
    }
    mock.chat.return_value = {
        "content": "Mock chat response",
        "tokens_used": 50
    }
    return mock


@pytest.fixture
def mock_tool():
    """Mock tool"""
    mock = AsyncMock()
    mock.execute.return_value = {"success": True, "result": "tool_result"}
    return mock


@pytest.fixture
def mock_storage_backend():
    """Mock storage backend"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def sample_workflow_definition():
    """Sample workflow definition"""
    return {
        "name": "Test Workflow",
        "steps": [
            {
                "id": "step1",
                "type": "agent",
                "agent": "test_agent",
                "task": "test_task"
            }
        ]
    }


@pytest.fixture
def sample_user_data():
    """Sample user data"""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data"""
    return {
        "tenant_id": "test_tenant_123",
        "name": "Test Tenant",
        "plan": "professional"
    }
