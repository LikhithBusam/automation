"""
Pytest fixtures for performance tests
"""

import pytest
import asyncio
from typing import Dict, Any


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async performance tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def performance_config():
    """Performance test configuration"""
    return {
        "load_test": {
            "num_users": 100,
            "requests_per_user": 10,
            "ramp_up_time": 10
        },
        "stress_test": {
            "max_load": 1000,
            "increment": 100
        },
        "soak_test": {
            "duration_hours": 1,  # Compressed for testing
            "load_level": 50
        },
        "spike_test": {
            "baseline_load": 10,
            "spike_multiplier": 10
        }
    }

