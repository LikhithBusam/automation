"""
Industrial Load Testing Suite
Tests system performance under high load conditions

Tests:
- Concurrent request handling
- Memory stability under load
- Response time under pressure
- Connection pool efficiency
- Rate limiter effectiveness
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import pytest
import psutil


@dataclass
class LoadTestResult:
    """Result of a load test"""

    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    errors: List[str] = field(default_factory=list)


@dataclass
class ConcurrencyTestResult:
    """Result of concurrency test"""

    test_name: str
    concurrent_users: int
    total_operations: int
    successful: int
    failed: int
    avg_response_time_ms: float
    errors: List[str] = field(default_factory=list)


class LoadTester:
    """Industrial-grade load testing utilities"""

    def __init__(self):
        self.process = psutil.Process()

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)

    def calculate_percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def run_load_test(
        self, test_func, num_requests: int, concurrent_limit: int = 10, test_name: str = "load_test"
    ) -> LoadTestResult:
        """
        Run load test with specified concurrency

        Args:
            test_func: Async function to test
            num_requests: Total number of requests to make
            concurrent_limit: Maximum concurrent requests
            test_name: Name of the test
        """
        memory_before = self.get_memory_mb()
        response_times: List[float] = []
        errors: List[str] = []
        successful = 0
        failed = 0

        semaphore = asyncio.Semaphore(concurrent_limit)

        async def limited_request():
            nonlocal successful, failed
            async with semaphore:
                start = time.perf_counter()
                try:
                    await test_func()
                    end = time.perf_counter()
                    response_times.append((end - start) * 1000)
                    successful += 1
                except Exception as e:
                    end = time.perf_counter()
                    response_times.append((end - start) * 1000)
                    failed += 1
                    errors.append(str(e)[:100])

        start_time = time.perf_counter()
        tasks = [limited_request() for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        memory_after = self.get_memory_mb()

        return LoadTestResult(
            test_name=test_name,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_time_seconds=total_time,
            requests_per_second=num_requests / total_time if total_time > 0 else 0,
            avg_response_time_ms=statistics.mean(response_times) if response_times else 0,
            p50_response_time_ms=self.calculate_percentile(response_times, 50),
            p95_response_time_ms=self.calculate_percentile(response_times, 95),
            p99_response_time_ms=self.calculate_percentile(response_times, 99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_delta_mb=memory_after - memory_before,
            errors=errors[:10],  # Limit errors stored
        )

    async def run_concurrency_test(
        self,
        test_func,
        concurrent_users: List[int],
        operations_per_user: int = 10,
        test_name: str = "concurrency_test",
    ) -> List[ConcurrencyTestResult]:
        """
        Test system behavior at different concurrency levels
        """
        results = []

        for num_users in concurrent_users:
            response_times: List[float] = []
            errors: List[str] = []
            successful = 0
            failed = 0

            async def user_operation():
                nonlocal successful, failed
                start = time.perf_counter()
                try:
                    await test_func()
                    response_times.append((time.perf_counter() - start) * 1000)
                    successful += 1
                except Exception as e:
                    response_times.append((time.perf_counter() - start) * 1000)
                    failed += 1
                    errors.append(str(e)[:100])

            # Simulate concurrent users
            tasks = []
            for _ in range(num_users):
                for _ in range(operations_per_user):
                    tasks.append(user_operation())

            await asyncio.gather(*tasks)

            results.append(
                ConcurrencyTestResult(
                    test_name=f"{test_name}_{num_users}_users",
                    concurrent_users=num_users,
                    total_operations=num_users * operations_per_user,
                    successful=successful,
                    failed=failed,
                    avg_response_time_ms=statistics.mean(response_times) if response_times else 0,
                    errors=errors[:5],
                )
            )

        return results


class TestLoadPerformance:
    """Load performance tests"""

    @pytest.fixture
    def load_tester(self):
        return LoadTester()

    @pytest.mark.asyncio
    async def test_high_throughput(self, load_tester):
        """Test handling of high request volume"""

        async def dummy_operation():
            await asyncio.sleep(0.001)  # 1ms simulated work
            return {"status": "ok"}

        result = await load_tester.run_load_test(
            test_func=dummy_operation,
            num_requests=1000,
            concurrent_limit=100,
            test_name="high_throughput",
        )

        # Assertions for industrial standards
        assert (
            result.successful_requests >= result.total_requests * 0.99
        ), f"Success rate below 99%: {result.successful_requests}/{result.total_requests}"
        assert (
            result.avg_response_time_ms < 100
        ), f"Average response time too high: {result.avg_response_time_ms}ms"
        assert (
            result.p99_response_time_ms < 500
        ), f"P99 response time too high: {result.p99_response_time_ms}ms"
        assert (
            result.requests_per_second > 100
        ), f"Throughput too low: {result.requests_per_second} RPS"

    @pytest.mark.asyncio
    async def test_memory_stability(self, load_tester):
        """Test memory doesn't leak under load"""

        async def memory_intensive_operation():
            data = [i for i in range(1000)]  # Allocate some memory
            await asyncio.sleep(0.001)
            return len(data)

        result = await load_tester.run_load_test(
            test_func=memory_intensive_operation,
            num_requests=500,
            concurrent_limit=50,
            test_name="memory_stability",
        )

        # Memory shouldn't grow more than 50MB during test
        assert result.memory_delta_mb < 50, f"Memory grew too much: {result.memory_delta_mb}MB"

    @pytest.mark.asyncio
    async def test_concurrent_scaling(self, load_tester):
        """Test performance at different concurrency levels"""

        async def scalable_operation():
            await asyncio.sleep(0.005)
            return True

        results = await load_tester.run_concurrency_test(
            test_func=scalable_operation,
            concurrent_users=[1, 5, 10, 25, 50],
            operations_per_user=20,
            test_name="scaling",
        )

        for result in results:
            # Success rate should stay high at all concurrency levels
            success_rate = result.successful / result.total_operations
            assert (
                success_rate >= 0.95
            ), f"Success rate dropped at {result.concurrent_users} users: {success_rate:.2%}"

    @pytest.mark.asyncio
    async def test_error_resilience(self, load_tester):
        """Test system handles errors gracefully"""

        error_count = 0

        async def flaky_operation():
            nonlocal error_count
            error_count += 1
            if error_count % 10 == 0:  # 10% failure rate
                raise Exception("Simulated failure")
            await asyncio.sleep(0.001)
            return True

        result = await load_tester.run_load_test(
            test_func=flaky_operation,
            num_requests=100,
            concurrent_limit=20,
            test_name="error_resilience",
        )

        # System should continue despite failures
        assert result.successful_requests > 0, "No successful requests"
        # Success rate should be approximately 90%
        success_rate = result.successful_requests / result.total_requests
        assert 0.85 <= success_rate <= 0.95, f"Unexpected success rate: {success_rate:.2%}"


class TestCircuitBreakerLoad:
    """Test circuit breaker under load"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers(self):
        """Test circuit breaker opens under repeated failures"""
        from src.security.circuit_breaker import (
            CircuitBreaker,
            CircuitState,
            CircuitBreakerOpenError,
        )

        cb = CircuitBreaker(failure_threshold=5, success_threshold=2, timeout_seconds=1)

        # Cause failures to trip the breaker
        for _ in range(5):
            try:
                async with cb:
                    raise Exception("Failure")
            except CircuitBreakerOpenError:
                break  # Circuit opened
            except Exception:
                pass

        # Circuit should be open now
        assert cb.state == CircuitState.OPEN, "Circuit breaker should be open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovers after timeout"""
        from src.security.circuit_breaker import (
            CircuitBreaker,
            CircuitState,
            CircuitBreakerOpenError,
        )

        cb = CircuitBreaker(failure_threshold=3, success_threshold=2, timeout_seconds=0.5)

        # Trip the breaker
        for _ in range(3):
            try:
                async with cb:
                    raise Exception("Failure")
            except CircuitBreakerOpenError:
                break
            except Exception:
                pass

        assert cb.state == CircuitState.OPEN, "Circuit should be open after failures"

        # Wait for timeout
        await asyncio.sleep(0.6)

        # Should be half-open now, allow success
        async with cb:
            pass  # Success
        async with cb:
            pass  # Another success

        # Should be closed after successful recoveries
        assert cb.state == CircuitState.CLOSED, "Circuit breaker should be closed after recovery"


class TestRateLimiterLoad:
    """Test rate limiter under load"""

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles(self):
        """Test rate limiter correctly throttles requests"""
        from src.security.rate_limiter import RateLimiter

        limiter = RateLimiter(max_calls=10, time_window_seconds=1.0)

        # Try to make 20 requests
        allowed = 0
        denied = 0

        for _ in range(20):
            try:
                if await limiter.acquire(wait=False):
                    allowed += 1
            except Exception:
                denied += 1

        # Should allow ~10 and deny ~10
        assert allowed <= 12, f"Too many allowed: {allowed}"
        assert denied >= 8, f"Too few denied: {denied}"

    @pytest.mark.asyncio
    async def test_rate_limiter_refills(self):
        """Test rate limiter refills after window"""
        from src.security.rate_limiter import RateLimiter

        limiter = RateLimiter(max_calls=5, time_window_seconds=0.5)

        # Use all tokens
        for _ in range(5):
            await limiter.acquire()

        # Should be throttled
        from src.security.rate_limiter import RateLimitExceeded

        with pytest.raises(RateLimitExceeded):
            await limiter.acquire(wait=False)

        # Wait for refill
        await asyncio.sleep(0.6)

        # Should allow again
        assert await limiter.acquire(wait=False), "Should allow after refill"


class TestConnectionPoolLoad:
    """Test connection pool under load"""

    @pytest.mark.asyncio
    async def test_pool_reuses_connections(self):
        """Test connection pool reuses connections efficiently"""
        from src.performance.optimizer import ConnectionPool

        pool = ConnectionPool(max_connections=5)

        # Get and release connections
        connections_used = set()

        for _ in range(20):
            conn = await pool.get_connection("test_server")
            connections_used.add(conn.id)
            await pool.release_connection(conn)

        # Should have reused connections (not created 20 unique ones)
        assert len(connections_used) <= 5, f"Created too many connections: {len(connections_used)}"

    @pytest.mark.asyncio
    async def test_pool_handles_concurrent_requests(self):
        """Test pool handles concurrent connection requests"""
        from src.performance.optimizer import ConnectionPool

        pool = ConnectionPool(max_connections=3)

        async def get_and_use():
            conn = await pool.get_connection("concurrent_test")
            await asyncio.sleep(0.01)
            await pool.release_connection(conn)
            return conn.id

        # Make concurrent requests exceeding pool size
        tasks = [get_and_use() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should complete without error
        assert len(results) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
