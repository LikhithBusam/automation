"""
Chaos Engineering Tests
Tests for random failures, latency injection, and resource exhaustion
"""

import pytest
import asyncio
from src.resilience.chaos import ChaosEngine, ChaosConfig, ChaosScenario


class TestChaosEngineering:
    """Test chaos engineering scenarios"""
    
    @pytest.fixture
    def chaos_engine(self):
        """Create chaos engine for testing"""
        config = ChaosConfig(
            enabled=True,
            failure_rate=0.5,  # 50% for testing
            latency_probability=1.0,  # Always inject for testing
            min_latency_ms=10.0,
            max_latency_ms=50.0
        )
        return ChaosEngine(config)
    
    @pytest.mark.asyncio
    async def test_random_failure_injection(self, chaos_engine):
        """Test random failure injection"""
        failures = 0
        total = 100
        
        for _ in range(total):
            if chaos_engine.inject_failure("test-service"):
                failures += 1
        
        # Should have some failures (not all, not none)
        assert 0 < failures < total, f"Expected some failures, got {failures}/{total}"
    
    @pytest.mark.asyncio
    async def test_latency_injection(self, chaos_engine):
        """Test latency injection"""
        start_time = asyncio.get_event_loop().time()
        
        await chaos_engine.inject_latency("test-service")
        
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000  # Convert to ms
        
        # Should have injected some latency
        assert elapsed >= 10.0, f"Expected at least 10ms latency, got {elapsed}ms"
        assert elapsed <= 100.0, f"Expected at most 100ms latency, got {elapsed}ms"
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion(self, chaos_engine):
        """Test resource exhaustion injection"""
        config = ChaosConfig(
            enabled=True,
            resource_exhaustion_probability=1.0  # Always inject for testing
        )
        chaos_engine.config = config
        
        exhausted = chaos_engine.inject_resource_exhaustion("test-service")
        assert exhausted, "Should inject resource exhaustion"
    
    @pytest.mark.asyncio
    async def test_execute_with_chaos_failure(self, chaos_engine):
        """Test executing function with chaos failure"""
        async def test_func():
            return "success"
        
        # With high failure rate, should eventually fail
        failures = 0
        for _ in range(10):
            try:
                await chaos_engine.execute_with_chaos("test-service", test_func)
            except Exception:
                failures += 1
        
        # Should have some failures
        assert failures > 0, "Should have some failures with chaos enabled"
    
    @pytest.mark.asyncio
    async def test_execute_with_chaos_latency(self, chaos_engine):
        """Test executing function with chaos latency"""
        async def test_func():
            return "success"
        
        start_time = asyncio.get_event_loop().time()
        
        await chaos_engine.execute_with_chaos("test-service", test_func)
        
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Should have some latency
        assert elapsed >= 10.0, f"Expected latency injection, got {elapsed}ms"
    
    def test_chaos_stats(self, chaos_engine):
        """Test chaos statistics"""
        chaos_engine.inject_failure("test")
        chaos_engine.inject_resource_exhaustion("test")
        
        stats = chaos_engine.get_stats()
        
        assert stats["failure_count"] > 0
        assert stats["resource_exhaustions"] > 0
        assert stats["enabled"] is True
    
    def test_disable_chaos(self, chaos_engine):
        """Test disabling chaos"""
        chaos_engine.disable()
        
        assert not chaos_engine.inject_failure("test")
        assert not chaos_engine.inject_resource_exhaustion("test")
        
        stats = chaos_engine.get_stats()
        assert stats["enabled"] is False

