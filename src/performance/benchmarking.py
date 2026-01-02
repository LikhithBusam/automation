"""
Performance Benchmarking Suite
"""

import asyncio
import logging
import time
import statistics
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Benchmark result"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    p95_time: float
    p99_time: float
    throughput: float  # Operations per second
    errors: int = 0
    error_rate: float = 0.0
    timings: List[float] = field(default_factory=list)


class PerformanceBenchmark:
    """
    Performance benchmarking suite.
    Measures execution time, throughput, and error rates.
    """
    
    def __init__(self):
        """Initialize benchmark suite"""
        self.logger = logging.getLogger("benchmark")
        self.results: Dict[str, BenchmarkResult] = {}
    
    async def benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup_iterations: int = 10,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark function execution.
        
        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            warmup_iterations: Warmup iterations (not counted)
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Benchmark result
        """
        self.logger.info(f"Starting benchmark: {name} ({iterations} iterations)")
        
        # Warmup
        for _ in range(warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except Exception:
                pass
        
        # Benchmark
        timings = []
        errors = 0
        start_time = time.time()
        
        for i in range(iterations):
            try:
                iteration_start = time.time()
                
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                
                iteration_time = time.time() - iteration_start
                timings.append(iteration_time)
            except Exception as e:
                errors += 1
                self.logger.warning(f"Benchmark iteration {i} failed: {e}")
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        if timings:
            avg_time = statistics.mean(timings)
            min_time = min(timings)
            max_time = max(timings)
            median_time = statistics.median(timings)
            p95_time = self._percentile(timings, 95)
            p99_time = self._percentile(timings, 99)
            throughput = len(timings) / total_time
        else:
            avg_time = min_time = max_time = median_time = p95_time = p99_time = 0.0
            throughput = 0.0
        
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput,
            errors=errors,
            error_rate=errors / iterations if iterations > 0 else 0.0,
            timings=timings
        )
        
        self.results[name] = result
        self.logger.info(
            f"Benchmark complete: {name} - "
            f"avg: {avg_time*1000:.2f}ms, "
            f"p95: {p95_time*1000:.2f}ms, "
            f"throughput: {throughput:.2f} ops/s"
        )
        
        return result
    
    async def compare_benchmarks(
        self,
        benchmarks: List[Callable],
        names: List[str],
        iterations: int = 100,
        *args,
        **kwargs
    ) -> Dict[str, BenchmarkResult]:
        """
        Compare multiple benchmarks.
        
        Args:
            benchmarks: List of functions to benchmark
            names: List of benchmark names
            iterations: Number of iterations
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Dictionary of benchmark results
        """
        results = {}
        
        for func, name in zip(benchmarks, names):
            result = await self.benchmark(name, func, iterations, *args, **kwargs)
            results[name] = result
        
        # Print comparison
        self._print_comparison(results)
        
        return results
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _print_comparison(self, results: Dict[str, BenchmarkResult]):
        """Print benchmark comparison"""
        self.logger.info("\n" + "="*80)
        self.logger.info("BENCHMARK COMPARISON")
        self.logger.info("="*80)
        
        for name, result in results.items():
            self.logger.info(f"\n{name}:")
            self.logger.info(f"  Average: {result.avg_time*1000:.2f}ms")
            self.logger.info(f"  Median:  {result.median_time*1000:.2f}ms")
            self.logger.info(f"  P95:     {result.p95_time*1000:.2f}ms")
            self.logger.info(f"  P99:     {result.p99_time*1000:.2f}ms")
            self.logger.info(f"  Throughput: {result.throughput:.2f} ops/s")
            self.logger.info(f"  Error rate: {result.error_rate*100:.2f}%")
        
        self.logger.info("\n" + "="*80)
    
    def get_results(self) -> Dict[str, BenchmarkResult]:
        """Get all benchmark results"""
        return self.results.copy()
    
    def export_results(self, format: str = "json") -> str:
        """
        Export benchmark results.
        
        Args:
            format: Export format (json, csv)
        
        Returns:
            Exported data
        """
        if format == "json":
            import json
            return json.dumps({
                name: {
                    "name": result.name,
                    "iterations": result.iterations,
                    "avg_time": result.avg_time,
                    "p95_time": result.p95_time,
                    "throughput": result.throughput,
                    "error_rate": result.error_rate
                }
                for name, result in self.results.items()
            }, indent=2)
        elif format == "csv":
            lines = ["name,iterations,avg_time,p95_time,throughput,error_rate"]
            for name, result in self.results.items():
                lines.append(
                    f"{name},{result.iterations},{result.avg_time},"
                    f"{result.p95_time},{result.throughput},{result.error_rate}"
                )
            return "\n".join(lines)
        
        return ""


# Global benchmark instance
_benchmark: Optional[PerformanceBenchmark] = None


def get_benchmark() -> PerformanceBenchmark:
    """Get global benchmark instance"""
    global _benchmark
    if _benchmark is None:
        _benchmark = PerformanceBenchmark()
    return _benchmark

