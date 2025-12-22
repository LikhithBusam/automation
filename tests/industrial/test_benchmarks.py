"""
Industrial Benchmark Suite
Measures and validates system performance against industrial standards

Benchmarks:
- Response time (P50, P95, P99)
- Throughput (requests per second)
- Memory efficiency
- CPU utilization
- Latency under load
"""

import asyncio
import time
import gc
import statistics
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import psutil
import pytest


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs"""

    warmup_iterations: int = 10
    benchmark_iterations: int = 100
    concurrent_operations: int = 1
    memory_tracking: bool = True
    gc_before_run: bool = True


@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""

    name: str
    timestamp: str
    iterations: int

    # Timing metrics (milliseconds)
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float

    # Throughput
    operations_per_second: float

    # Memory metrics (MB)
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0

    # Status
    passed_sla: bool = True
    sla_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SLARequirements:
    """Service Level Agreement requirements"""

    max_p50_ms: float = 50.0
    max_p95_ms: float = 200.0
    max_p99_ms: float = 500.0
    min_ops_per_second: float = 100.0
    max_memory_growth_mb: float = 100.0


class Benchmarker:
    """Industrial benchmarking utilities"""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.process = psutil.Process()
        self.results: List[BenchmarkResult] = []

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)

    def calculate_percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def benchmark_async(
        self, func: Callable, name: str, sla: Optional[SLARequirements] = None, **kwargs
    ) -> BenchmarkResult:
        """
        Run async benchmark with SLA validation
        """
        sla = sla or SLARequirements()

        # Garbage collect before benchmark
        if self.config.gc_before_run:
            gc.collect()

        memory_before = self.get_memory_mb()
        memory_peak = memory_before
        timings: List[float] = []

        # Warmup phase
        for _ in range(self.config.warmup_iterations):
            await func(**kwargs)

        # Benchmark phase
        start_total = time.perf_counter()

        for _ in range(self.config.benchmark_iterations):
            start = time.perf_counter()
            await func(**kwargs)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            timings.append(elapsed)

            # Track peak memory
            current_mem = self.get_memory_mb()
            if current_mem > memory_peak:
                memory_peak = current_mem

        total_time = (time.perf_counter() - start_total) * 1000
        memory_after = self.get_memory_mb()

        # Calculate statistics
        result = BenchmarkResult(
            name=name,
            timestamp=datetime.utcnow().isoformat(),
            iterations=self.config.benchmark_iterations,
            total_time_ms=total_time,
            avg_time_ms=statistics.mean(timings),
            min_time_ms=min(timings),
            max_time_ms=max(timings),
            p50_ms=self.calculate_percentile(timings, 50),
            p95_ms=self.calculate_percentile(timings, 95),
            p99_ms=self.calculate_percentile(timings, 99),
            stddev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
            operations_per_second=self.config.benchmark_iterations / (total_time / 1000),
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_peak_mb=memory_peak,
            memory_delta_mb=memory_after - memory_before,
        )

        # Validate SLA
        violations = []
        if result.p50_ms > sla.max_p50_ms:
            violations.append(f"P50 {result.p50_ms:.2f}ms > {sla.max_p50_ms}ms")
        if result.p95_ms > sla.max_p95_ms:
            violations.append(f"P95 {result.p95_ms:.2f}ms > {sla.max_p95_ms}ms")
        if result.p99_ms > sla.max_p99_ms:
            violations.append(f"P99 {result.p99_ms:.2f}ms > {sla.max_p99_ms}ms")
        if result.operations_per_second < sla.min_ops_per_second:
            violations.append(f"OPS {result.operations_per_second:.2f} < {sla.min_ops_per_second}")
        if result.memory_delta_mb > sla.max_memory_growth_mb:
            violations.append(
                f"Memory growth {result.memory_delta_mb:.2f}MB > {sla.max_memory_growth_mb}MB"
            )

        result.passed_sla = len(violations) == 0
        result.sla_violations = violations

        self.results.append(result)
        return result

    def benchmark_sync(
        self, func: Callable, name: str, sla: Optional[SLARequirements] = None, **kwargs
    ) -> BenchmarkResult:
        """Run sync benchmark with SLA validation"""
        sla = sla or SLARequirements()

        if self.config.gc_before_run:
            gc.collect()

        memory_before = self.get_memory_mb()
        memory_peak = memory_before
        timings: List[float] = []

        # Warmup
        for _ in range(self.config.warmup_iterations):
            func(**kwargs)

        # Benchmark
        start_total = time.perf_counter()

        for _ in range(self.config.benchmark_iterations):
            start = time.perf_counter()
            func(**kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)

            current_mem = self.get_memory_mb()
            if current_mem > memory_peak:
                memory_peak = current_mem

        total_time = (time.perf_counter() - start_total) * 1000
        memory_after = self.get_memory_mb()

        result = BenchmarkResult(
            name=name,
            timestamp=datetime.utcnow().isoformat(),
            iterations=self.config.benchmark_iterations,
            total_time_ms=total_time,
            avg_time_ms=statistics.mean(timings),
            min_time_ms=min(timings),
            max_time_ms=max(timings),
            p50_ms=self.calculate_percentile(timings, 50),
            p95_ms=self.calculate_percentile(timings, 95),
            p99_ms=self.calculate_percentile(timings, 99),
            stddev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
            operations_per_second=self.config.benchmark_iterations / (total_time / 1000),
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_peak_mb=memory_peak,
            memory_delta_mb=memory_after - memory_before,
        )

        # Validate SLA
        violations = []
        if result.p50_ms > sla.max_p50_ms:
            violations.append(f"P50 {result.p50_ms:.2f}ms > {sla.max_p50_ms}ms")
        if result.p95_ms > sla.max_p95_ms:
            violations.append(f"P95 {result.p95_ms:.2f}ms > {sla.max_p95_ms}ms")
        if result.p99_ms > sla.max_p99_ms:
            violations.append(f"P99 {result.p99_ms:.2f}ms > {sla.max_p99_ms}ms")
        if result.operations_per_second < sla.min_ops_per_second:
            violations.append(f"OPS {result.operations_per_second:.2f} < {sla.min_ops_per_second}")
        if result.memory_delta_mb > sla.max_memory_growth_mb:
            violations.append(
                f"Memory growth {result.memory_delta_mb:.2f}MB > {sla.max_memory_growth_mb}MB"
            )

        result.passed_sla = len(violations) == 0
        result.sla_violations = violations

        self.results.append(result)
        return result

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate benchmark report"""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_benchmarks": len(self.results),
            "passed_sla": sum(1 for r in self.results if r.passed_sla),
            "failed_sla": sum(1 for r in self.results if not r.passed_sla),
            "results": [r.to_dict() for r in self.results],
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)

        return report


class TestCoreBenchmarks:
    """Core system benchmarks"""

    @pytest.fixture
    def benchmarker(self):
        return Benchmarker(BenchmarkConfig(warmup_iterations=5, benchmark_iterations=50))

    @pytest.mark.asyncio
    async def test_cache_performance(self, benchmarker):
        """Benchmark cache operations"""
        from src.performance.optimizer import SmartCache

        cache = SmartCache(max_size=1000)

        # Pre-populate cache
        for i in range(100):
            cache.set(f"key_{i}", {"data": f"value_{i}" * 10})

        async def cache_get():
            import random

            key = f"key_{random.randint(0, 99)}"
            return cache.get(key)

        result = await benchmarker.benchmark_async(
            func=cache_get,
            name="cache_get_operation",
            sla=SLARequirements(
                max_p50_ms=0.5, max_p95_ms=2.0, max_p99_ms=5.0, min_ops_per_second=10000
            ),
        )

        assert result.passed_sla, f"Cache SLA violations: {result.sla_violations}"

    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, benchmarker):
        """Benchmark connection pool operations"""
        from src.performance.optimizer import ConnectionPool

        pool = ConnectionPool(max_connections=10)

        async def pool_operation():
            conn = await pool.get_connection("benchmark_server")
            await pool.release_connection(conn)
            return conn

        result = await benchmarker.benchmark_async(
            func=pool_operation,
            name="connection_pool_cycle",
            sla=SLARequirements(
                max_p50_ms=1.0, max_p95_ms=5.0, max_p99_ms=10.0, min_ops_per_second=1000
            ),
        )

        assert result.passed_sla, f"Connection pool SLA violations: {result.sla_violations}"

    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self, benchmarker):
        """Benchmark rate limiter operations"""
        from src.security.rate_limiter import RateLimiter

        limiter = RateLimiter(max_calls=10000, time_window_seconds=1.0)

        async def rate_limit_check():
            return await limiter.acquire()

        result = await benchmarker.benchmark_async(
            func=rate_limit_check,
            name="rate_limiter_acquire",
            sla=SLARequirements(
                max_p50_ms=0.1, max_p95_ms=0.5, max_p99_ms=1.0, min_ops_per_second=5000
            ),
        )

        assert result.passed_sla, f"Rate limiter SLA violations: {result.sla_violations}"

    def test_input_validation_performance(self, benchmarker):
        """Benchmark input validation"""
        from src.security.input_validator import InputValidator

        validator = InputValidator()

        test_input = {
            "code_path": "/path/to/file.py",
            "query": "test query",
            "topic": "python programming",
        }

        def validate_input():
            return validator.validate_parameters(test_input)

        result = benchmarker.benchmark_sync(
            func=validate_input,
            name="input_validation",
            sla=SLARequirements(
                max_p50_ms=0.5, max_p95_ms=2.0, max_p99_ms=5.0, min_ops_per_second=5000
            ),
        )

        assert result.passed_sla, f"Validation SLA violations: {result.sla_violations}"


class TestScalabilityBenchmarks:
    """Scalability benchmarks"""

    @pytest.fixture
    def benchmarker(self):
        return Benchmarker(BenchmarkConfig(warmup_iterations=3, benchmark_iterations=20))

    @pytest.mark.asyncio
    async def test_parallel_execution_scaling(self, benchmarker):
        """Test parallel execution scales properly"""
        from src.performance.optimizer import ParallelExecutor

        executor = ParallelExecutor(max_workers=8)

        async def parallel_workload():
            async def task():
                await asyncio.sleep(0.001)
                return 1

            results = await executor.execute_parallel([task for _ in range(10)])
            return sum(results)

        result = await benchmarker.benchmark_async(
            func=parallel_workload,
            name="parallel_execution_10_tasks",
            sla=SLARequirements(
                max_p50_ms=50.0, max_p95_ms=100.0, max_p99_ms=200.0, min_ops_per_second=10
            ),
        )

        executor.shutdown()
        assert result.passed_sla, f"Parallel execution SLA violations: {result.sla_violations}"

    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, benchmarker):
        """Test batch processing is efficient"""
        from src.performance.optimizer import RequestBatcher

        batcher = RequestBatcher(batch_size=10, batch_timeout=0.01)

        async def batch_operation():
            result = await batcher.add_request("test_op", {"param": "value"})
            return result

        result = await benchmarker.benchmark_async(
            func=batch_operation,
            name="batch_request_add",
            sla=SLARequirements(
                max_p50_ms=20.0, max_p95_ms=50.0, max_p99_ms=100.0, min_ops_per_second=50
            ),
        )

        assert result.passed_sla, f"Batch processing SLA violations: {result.sla_violations}"


def run_all_benchmarks():
    """Run all benchmarks and generate report"""
    benchmarker = Benchmarker(BenchmarkConfig(warmup_iterations=10, benchmark_iterations=100))

    # Run benchmarks
    # This would be called from command line

    report = benchmarker.generate_report("benchmark_report.json")
    print(f"\nBenchmark Report Generated:")
    print(f"  Total: {report['total_benchmarks']}")
    print(f"  Passed SLA: {report['passed_sla']}")
    print(f"  Failed SLA: {report['failed_sla']}")

    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
