"""Pytest fixtures for security testing"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any


@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager"""
    from unittest.mock import Mock
    
    manager = Mock()
    manager.create_user = Mock(return_value=Mock(
        user_id="user_123",
        username="test_user",
        email="test@example.com",
        role="developer",
        has_permission=Mock(return_value=False)
    ))
    manager.generate_token = Mock(return_value="mock_token_123")
    manager.create_session = Mock(return_value="session_123")
    return manager


@pytest.fixture
def mock_input_validator():
    """Mock input validator"""
    from unittest.mock import Mock
    from src.security.input_validator import ValidationError
    
    validator = Mock()
    validator.validate_parameter_value = Mock(side_effect=lambda k, v: None if len(v) < 1000 else ValidationError("Too long"))
    validator.validate_path = Mock(side_effect=lambda p: None if ".." not in p else ValidationError("Path traversal"))
    return validator


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter"""
    from unittest.mock import AsyncMock
    from src.security.rate_limiter import RateLimitExceeded
    
    limiter = AsyncMock()
    limiter.acquire = AsyncMock(side_effect=lambda wait=False: None)
    return limiter

