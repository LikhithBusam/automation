"""
Pytest fixtures for E2E tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async E2E tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_environment():
    """Create test environment configuration"""
    return {
        "environment": "test",
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/0",
        "api_base_url": "http://localhost:8000"
    }


@pytest.fixture
async def authenticated_user():
    """Create authenticated test user"""
    from src.security.auth import AuthManager
    
    auth_manager = AuthManager()
    user = auth_manager.create_user(
        username="e2e_test_user",
        email="e2e@test.com",
        role="developer"
    )
    
    token = auth_manager.generate_token(user.user_id)
    
    return {
        "user": user,
        "token": token,
        "auth_manager": auth_manager
    }


@pytest.fixture
async def workflow_manager():
    """Create workflow manager for E2E tests"""
    from src.autogen_adapters.conversation_manager import ConversationManager
    
    config = {
        "workflows": {
            "test_workflow": {
                "type": "group_chat",
                "agents": ["code_analyzer"],
                "task": "Test workflow"
            }
        }
    }
    
    return ConversationManager(config)

