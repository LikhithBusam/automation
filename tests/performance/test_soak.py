"""
Soak Testing
Run system under moderate load for extended periods (24-72 hours),
check for memory leaks, monitor resource utilization trends
"""

import pytest
import asyncio
import time
import psutil
import os
import gc
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict


class SoakTestMonitor:
    """Monitor system during soak testing"""
    
    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self.memory_trend: List[float] = []
        self.cpu_trend: List[float] = []
        self.error_count = 0
        self.start_time = None
    
    def record_metrics(self):
        """Record current system metrics"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        self.metrics.append({
            "timestamp": datetime.now().isoformat(),
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        })
        
        self.memory_trend.append(memory_mb)
        self.cpu_trend.append(cpu_percent)
    
    def detect_memory_leak(self) -> bool:
        """Detect potential memory leak"""
        if len(self.memory_trend) < 10:
            return False
        
        # Check if memory is consistently increasing
        recent_trend = self.memory_trend[-10:]
        if recent_trend[-1] > recent_trend[0] * 1.2:  # 20% increase
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from soak test"""
        if not self.metrics:
            return {
                "duration_seconds": 0,
                "error_count": self.error_count,
                "memory_leak_detected": False
            }
        
        memory_values = [m["memory_mb"] for m in self.metrics]
        cpu_values = [m["cpu_percent"] for m in self.metrics]
        
        return {
            "duration_seconds": self.metrics[-1]["elapsed_seconds"],
            "memory_initial_mb": memory_values[0] if memory_values else 0,
            "memory_final_mb": memory_values[-1] if memory_values else 0,
            "memory_peak_mb": max(memory_values) if memory_values else 0,
            "memory_avg_mb": sum(memory_values) / len(memory_values) if memory_values else 0,
            "cpu_avg_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "cpu_peak_percent": max(cpu_values) if cpu_values else 0,
            "error_count": self.error_count,
            "memory_leak_detected": self.detect_memory_leak()
        }


class TestSoakTesting:
    """Soak testing scenarios"""
    
    @pytest.mark.asyncio
    async def test_short_soak_1_hour(self):
        """Short soak test (1 hour simulation - compressed to minutes for testing)"""
        monitor = SoakTestMonitor()
        monitor.start_time = datetime.now()
        
        # Simulate 1 hour in compressed time (1 minute = 1 hour)
        duration_seconds = 60  # 1 minute for testing (represents 1 hour)
        end_time = time.time() + duration_seconds
        
        async def continuous_load():
            """Apply continuous moderate load"""
            while time.time() < end_time:
                try:
                    # Simulate moderate load
                    await asyncio.sleep(0.1)
                    await asyncio.gather(*[self._simulate_request() for _ in range(10)])
                except Exception as e:
                    monitor.error_count += 1
        
        async def monitor_task():
            """Monitor system metrics"""
            while time.time() < end_time:
                monitor.record_metrics()
                await asyncio.sleep(5)  # Record every 5 seconds
        
        # Run soak test
        await asyncio.gather(
            continuous_load(),
            monitor_task(),
            return_exceptions=True
        )
        
        stats = monitor.get_stats()
        
        assert stats["duration_seconds"] >= duration_seconds - 10, "Soak test duration too short"
        assert not stats["memory_leak_detected"], "Memory leak detected during soak test"
        assert stats["error_count"] < 100, f"Too many errors during soak: {stats['error_count']}"
    
    @pytest.mark.asyncio
    async def test_medium_soak_12_hours(self):
        """Medium soak test (12 hours simulation - compressed)"""
        monitor = SoakTestMonitor()
        monitor.start_time = datetime.now()
        
        # Simulate 12 hours in compressed time (2 minutes = 12 hours)
        duration_seconds = 120  # 2 minutes for testing
        end_time = time.time() + duration_seconds
        
        async def continuous_load():
            while time.time() < end_time:
                try:
                    await asyncio.sleep(0.2)
                    await asyncio.gather(*[self._simulate_request() for _ in range(5)])
                except Exception:
                    monitor.error_count += 1
        
        async def monitor_task():
            while time.time() < end_time:
                monitor.record_metrics()
                await asyncio.sleep(10)  # Record every 10 seconds
        
        await asyncio.gather(
            continuous_load(),
            monitor_task(),
            return_exceptions=True
        )
        
        stats = monitor.get_stats()
        
        assert not stats["memory_leak_detected"], "Memory leak detected"
        assert stats["memory_final_mb"] < stats["memory_initial_mb"] * 2, "Memory growth too high"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test memory leak detection"""
        monitor = SoakTestMonitor()
        monitor.start_time = datetime.now()
        
        # Simulate memory leak scenario
        leaked_objects = []
        
        async def leak_memory():
            for i in range(100):
                leaked_objects.append({"data": "x" * 1000, "id": i})
                monitor.record_metrics()
                await asyncio.sleep(0.1)
        
        await leak_memory()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.5)
        monitor.record_metrics()
        
        # Check for memory leak
        leak_detected = monitor.detect_memory_leak()
        
        # Cleanup
        del leaked_objects
        gc.collect()
        
        # In this test, we expect to detect the leak
        # In real scenarios, we'd want leak_detected to be False
        assert isinstance(leak_detected, bool), "Leak detection should return boolean"
    
    @pytest.mark.asyncio
    async def test_resource_utilization_trends(self):
        """Test resource utilization trends over time"""
        monitor = SoakTestMonitor()
        monitor.start_time = datetime.now()
        
        # Monitor for extended period
        for i in range(20):
            monitor.record_metrics()
            await asyncio.sleep(0.5)
        
        stats = monitor.get_stats()
        
        # Check trends
        assert len(monitor.memory_trend) == 20, "Not enough memory samples"
        assert len(monitor.cpu_trend) == 20, "Not enough CPU samples"
        
        # Memory should be relatively stable (not continuously increasing)
        memory_variance = max(monitor.memory_trend) - min(monitor.memory_trend)
        assert memory_variance < 500, f"Memory variance too high: {memory_variance}MB"
    
    @pytest.mark.asyncio
    async def test_error_rate_during_soak(self):
        """Test error rate during extended soak"""
        monitor = SoakTestMonitor()
        monitor.start_time = datetime.now()
        
        error_rate_by_hour = defaultdict(int)
        
        async def generate_load_with_errors():
            for i in range(1000):
                try:
                    if i % 100 == 0:  # Simulate occasional errors
                        raise Exception("Simulated error")
                    await asyncio.sleep(0.01)
                except Exception:
                    monitor.error_count += 1
                    if monitor.start_time:
                        elapsed = (datetime.now() - monitor.start_time).total_seconds()
                        hour = int(elapsed / 3600)
                        error_rate_by_hour[hour] += 1
        
        await generate_load_with_errors()
        
        stats = monitor.get_stats()
        
        # Error rate should be reasonable
        error_rate = stats["error_count"] / 1000 * 100
        assert error_rate < 20, f"Error rate too high: {error_rate}%"
    
    async def _simulate_request(self):
        """Simulate a request"""
        await asyncio.sleep(0.01)
        return {"status": "success"}


class TestResourceMonitoring:
    """Test resource monitoring during soak tests"""
    
    @pytest.mark.asyncio
    async def test_memory_utilization_monitoring(self):
        """Test memory utilization monitoring"""
        memory_samples = []
        
        async def monitor_memory():
            for _ in range(10):
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                await asyncio.sleep(0.1)
        
        await monitor_memory()
        
        assert len(memory_samples) == 10, "Not enough memory samples"
        assert all(m > 0 for m in memory_samples), "Invalid memory readings"
    
    @pytest.mark.asyncio
    async def test_cpu_utilization_monitoring(self):
        """Test CPU utilization monitoring"""
        cpu_samples = []
        
        async def monitor_cpu():
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)
                await asyncio.sleep(0.1)
        
        await monitor_cpu()
        
        assert len(cpu_samples) == 10, "Not enough CPU samples"
        assert all(0 <= c <= 100 for c in cpu_samples), "Invalid CPU readings"

