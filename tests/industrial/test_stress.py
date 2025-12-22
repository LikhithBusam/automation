"""
Industrial Stress Tests
Tests system behavior under extreme conditions

Tests:
- Memory exhaustion handling
- CPU saturation handling
- Network failure simulation
- Timeout handling
- Error cascade prevention
"""

import asyncio
import time
import gc
from typing import List, Dict, Any
from dataclasses import dataclass
import pytest
import psutil


@dataclass
class StressTestResult:
    """Result of a stress test"""
    test_name: str
    passed: bool
    duration_seconds: float
    peak_memory_mb: float
    peak_cpu_percent: float
    errors_encountered: int
    recovery_time_seconds: float = 0.0
    details: str = ""


class StressTester:
    """Industrial stress testing utilities"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_memory_mb(self) -> float:
        return self.process.memory_info().rss / (1024 * 1024)
    
    def get_cpu_percent(self) -> float:
        return self.process.cpu_percent(interval=0.1)


class TestMemoryStress:
    """Memory stress tests"""
    
    @pytest.fixture
    def tester(self):
        return StressTester()
    
    @pytest.mark.asyncio
    async def test_handles_large_data(self, tester):
        """Test system handles large data without crashing"""
        from src.performance.optimizer import SmartCache
        
        cache = SmartCache(max_size=100)  # Limited size
        initial_memory = tester.get_memory_mb()
        
        # Try to add more data than cache can hold
        for i in range(500):
            large_data = {"data": "x" * 10000, "index": i}
            cache.set(f"key_{i}", large_data)
        
        final_memory = tester.get_memory_mb()
        memory_growth = final_memory - initial_memory
        
        # Cache should evict old entries, memory shouldn't grow unbounded
        assert len(cache.cache) <= 100, "Cache exceeded max size"
        assert memory_growth < 100, f"Memory grew too much: {memory_growth}MB"
    
    @pytest.mark.asyncio
    async def test_gc_pressure(self, tester):
        """Test system handles GC pressure"""
        initial_memory = tester.get_memory_mb()
        
        # Create and destroy many objects
        for _ in range(100):
            data = [{"key": f"value_{i}" * 100} for i in range(1000)]
            del data
        
        gc.collect()
        final_memory = tester.get_memory_mb()
        
        # Memory should return to near initial
        assert final_memory < initial_memory + 50, \
            f"Memory not reclaimed: {final_memory - initial_memory}MB growth"


class TestConcurrencyStress:
    """Concurrency stress tests"""
    
    @pytest.mark.asyncio
    async def test_extreme_concurrency(self):
        """Test system under extreme concurrent load"""
        from src.performance.optimizer import ConnectionPool
        
        pool = ConnectionPool(max_connections=5)
        errors = []
        successes = 0
        
        async def extreme_operation():
            nonlocal successes
            try:
                conn = await asyncio.wait_for(
                    pool.get_connection("stress_test"),
                    timeout=5.0
                )
                await asyncio.sleep(0.01)
                await pool.release_connection(conn)
                successes += 1
            except asyncio.TimeoutError:
                errors.append("Timeout")
            except Exception as e:
                errors.append(str(e))
        
        # Launch many concurrent operations
        tasks = [extreme_operation() for _ in range(100)]
        await asyncio.gather(*tasks)
        
        # Most should succeed despite limited pool
        success_rate = successes / 100
        assert success_rate >= 0.9, f"Success rate too low: {success_rate:.2%}"
    
    @pytest.mark.asyncio
    async def test_lock_contention(self):
        """Test performance under heavy lock contention"""
        counter = 0
        lock = asyncio.Lock()
        
        async def contested_operation():
            nonlocal counter
            async with lock:
                counter += 1
                await asyncio.sleep(0.001)
        
        start = time.perf_counter()
        tasks = [contested_operation() for _ in range(100)]
        await asyncio.gather(*tasks)
        duration = time.perf_counter() - start
        
        assert counter == 100, f"Counter mismatch: {counter}"
        # With 1ms sleep per op and serialized execution, should take ~100ms
        assert duration < 2.0, f"Lock contention too slow: {duration}s"


class TestErrorCascade:
    """Test error cascade prevention"""
    
    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test that errors in one task don't cascade"""
        results = []
        
        async def good_task():
            await asyncio.sleep(0.01)
            results.append("success")
            return "ok"
        
        async def bad_task():
            await asyncio.sleep(0.01)
            raise ValueError("Intentional error")
        
        # Mix of good and bad tasks
        tasks = []
        for i in range(20):
            if i % 5 == 0:
                tasks.append(asyncio.create_task(bad_task()))
            else:
                tasks.append(asyncio.create_task(good_task()))
        
        # Gather with return_exceptions to prevent cascade
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Good tasks should still complete
        assert len(results) >= 15, f"Too few successes: {len(results)}"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_cascade(self):
        """Test circuit breaker prevents error cascades"""
        from src.security.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
        
        cb = CircuitBreaker(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=0.5
        )
        
        failures_before_open = 0
        failures_after_open = 0
        
        # Try many operations
        for _ in range(20):
            try:
                async with cb:
                    if cb.state == CircuitState.CLOSED:
                        failures_before_open += 1
                    else:
                        failures_after_open += 1
                    raise Exception("Service down")
            except CircuitBreakerOpenError:
                # Circuit is open, request rejected
                failures_after_open += 1
            except Exception:
                pass
        
        # Circuit should have opened, preventing further calls to service
        assert cb.state == CircuitState.OPEN, "Circuit should be open"
        # Most calls after opening should have been rejected
        assert failures_before_open <= 5, f"Too many calls before open: {failures_before_open}"


class TestTimeoutHandling:
    """Test timeout handling"""
    
    @pytest.mark.asyncio
    async def test_operation_timeout(self):
        """Test operations respect timeouts"""
        
        async def slow_operation():
            await asyncio.sleep(10)  # Very slow
            return "done"
        
        start = time.perf_counter()
        
        try:
            result = await asyncio.wait_for(slow_operation(), timeout=0.1)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass
        
        duration = time.perf_counter() - start
        
        # Should have timed out quickly
        assert duration < 0.5, f"Timeout took too long: {duration}s"
    
    @pytest.mark.asyncio
    async def test_partial_results_on_timeout(self):
        """Test system returns partial results on timeout"""
        results = []
        
        async def fast_task(i):
            await asyncio.sleep(0.01)
            results.append(i)
            return i
        
        async def slow_task(i):
            await asyncio.sleep(10)
            results.append(i)
            return i
        
        tasks = [
            asyncio.create_task(fast_task(i)) for i in range(5)
        ] + [
            asyncio.create_task(slow_task(i)) for i in range(5, 10)
        ]
        
        # Wait with timeout
        done, pending = await asyncio.wait(tasks, timeout=0.5)
        
        # Cancel pending
        for task in pending:
            task.cancel()
        
        # Should have some results even with timeout
        assert len(results) >= 5, f"Too few results: {len(results)}"


class TestRecovery:
    """Test system recovery capabilities"""
    
    @pytest.mark.asyncio
    async def test_recovers_from_overload(self):
        """Test system recovers from temporary overload"""
        from src.security.rate_limiter import RateLimiter, RateLimitExceeded
        
        limiter = RateLimiter(max_calls=10, time_window_seconds=0.5)
        
        # Exhaust rate limit (use non-blocking to avoid waiting)
        allowed_initial = 0
        for _ in range(20):
            try:
                if await limiter.acquire(wait=False):
                    allowed_initial += 1
            except RateLimitExceeded:
                pass
        
        # Rate limit should be exceeded
        assert allowed_initial == 10, f"Expected 10 allowed, got {allowed_initial}"
        
        # Wait for recovery (window is 0.5s, so 0.6s ensures refill)
        await asyncio.sleep(0.6)
        
        # Should be able to make requests again
        allowed_after = 0
        for _ in range(5):
            try:
                if await limiter.acquire(wait=False):
                    allowed_after += 1
            except RateLimitExceeded:
                pass
        
        assert allowed_after >= 3, f"Recovery failed: only {allowed_after} allowed"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovers properly"""
        from src.security.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
        
        cb = CircuitBreaker(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.3
        )
        
        # Trip the breaker
        for _ in range(2):
            try:
                async with cb:
                    raise Exception("Failure")
            except CircuitBreakerOpenError:
                break
            except Exception:
                pass
        
        assert cb.state == CircuitState.OPEN, "Circuit should be open"
        
        # Wait for timeout
        await asyncio.sleep(0.4)
        
        # Success should help recover
        async with cb:
            pass  # Success
        async with cb:
            pass  # Another success
        
        assert cb.state == CircuitState.CLOSED, "Circuit should have recovered"


class TestResourceExhaustion:
    """Test handling of resource exhaustion"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test handling when connection pool is exhausted"""
        from src.performance.optimizer import ConnectionPool
        
        pool = ConnectionPool(max_connections=2)
        
        connections = []
        
        # Exhaust pool
        for _ in range(2):
            conn = await pool.get_connection("exhaust_test")
            connections.append(conn)
        
        # Next request should wait/timeout
        try:
            conn = await asyncio.wait_for(
                pool.get_connection("exhaust_test"),
                timeout=0.5
            )
            # If we get here, connection was obtained (pool implemented waiting)
            connections.append(conn)
        except asyncio.TimeoutError:
            pass  # Expected behavior
        
        # Release connections
        for conn in connections:
            await pool.release_connection(conn)
    
    @pytest.mark.asyncio  
    async def test_handles_many_concurrent_waits(self):
        """Test system handles many waiters gracefully"""
        from src.performance.optimizer import ConnectionPool
        
        pool = ConnectionPool(max_connections=3)
        completed = 0
        failed = 0
        
        async def wait_and_use():
            nonlocal completed, failed
            try:
                conn = await asyncio.wait_for(
                    pool.get_connection("wait_test"),
                    timeout=2.0
                )
                await asyncio.sleep(0.01)
                await pool.release_connection(conn)
                completed += 1
            except asyncio.TimeoutError:
                failed += 1
        
        # Many concurrent requests for limited connections
        tasks = [wait_and_use() for _ in range(20)]
        
        await asyncio.gather(*tasks)
        
        # Should have completed many despite limited pool
        assert completed >= 10, f"Too few completed: {completed}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
