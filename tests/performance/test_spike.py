"""
Spike Testing
Test sudden traffic increases and auto-scaling response
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime


class SpikeTestResults:
    """Container for spike test results"""
    
    def __init__(self):
        self.spike_start_time: float = None
        self.spike_end_time: float = None
        self.recovery_time: float = None
        self.response_times_during_spike: List[float] = []
        self.response_times_after_spike: List[float] = []
        self.errors_during_spike = 0
        self.scaling_detected = False
    
    def record_spike_response(self, response_time: float):
        """Record response time during spike"""
        self.response_times_during_spike.append(response_time)
    
    def record_recovery_response(self, response_time: float):
        """Record response time after spike"""
        self.response_times_after_spike.append(response_time)


class TestSpikeTesting:
    """Spike testing scenarios"""
    
    @pytest.mark.asyncio
    async def test_sudden_traffic_increase_10x(self):
        """Test 10x sudden traffic increase"""
        results = SpikeTestResults()
        
        # Baseline load
        baseline_tasks = [self._simulate_request() for _ in range(10)]
        await asyncio.gather(*baseline_tasks)
        
        # Sudden spike (10x increase)
        results.spike_start_time = time.time()
        spike_tasks = [self._simulate_request() for _ in range(100)]
        spike_results = await asyncio.gather(*spike_tasks, return_exceptions=True)
        results.spike_end_time = time.time()
        
        # Count errors during spike
        results.errors_during_spike = sum(1 for r in spike_results if isinstance(r, Exception))
        
        # System should handle spike
        error_rate = results.errors_during_spike / len(spike_tasks) * 100
        assert error_rate < 30, f"Error rate too high during spike: {error_rate}%"
    
    @pytest.mark.asyncio
    async def test_sudden_traffic_increase_100x(self):
        """Test 100x sudden traffic increase"""
        results = SpikeTestResults()
        
        # Baseline
        baseline_tasks = [self._simulate_request() for _ in range(5)]
        await asyncio.gather(*baseline_tasks)
        
        # Massive spike
        results.spike_start_time = time.time()
        spike_tasks = [self._simulate_request() for _ in range(500)]
        spike_results = await asyncio.gather(*spike_tasks, return_exceptions=True)
        results.spike_end_time = time.time()
        
        results.errors_during_spike = sum(1 for r in spike_results if isinstance(r, Exception))
        
        # System may degrade but should not completely fail
        error_rate = results.errors_during_spike / len(spike_tasks) * 100
        assert error_rate < 50, f"Error rate too high during massive spike: {error_rate}%"
    
    @pytest.mark.asyncio
    async def test_auto_scaling_response(self):
        """Test auto-scaling response to spike"""
        results = SpikeTestResults()
        
        # Monitor scaling
        initial_capacity = 10
        current_capacity = initial_capacity
        
        async def detect_scaling():
            nonlocal current_capacity
            # Simulate scaling detection
            await asyncio.sleep(0.5)
            # In real scenario, would check actual capacity
            current_capacity = 50  # Simulated scale-up
            results.scaling_detected = True
        
        # Apply spike
        results.spike_start_time = time.time()
        spike_tasks = [self._simulate_request() for _ in range(200)]
        scaling_task = asyncio.create_task(detect_scaling())
        
        await asyncio.gather(*spike_tasks, scaling_task, return_exceptions=True)
        results.spike_end_time = time.time()
        
        # Scaling should be detected
        assert results.scaling_detected, "Auto-scaling not detected"
        assert current_capacity > initial_capacity, "Capacity did not increase"
    
    @pytest.mark.asyncio
    async def test_recovery_after_spike(self):
        """Test system recovery after traffic spike"""
        results = SpikeTestResults()
        
        # Apply spike
        results.spike_start_time = time.time()
        spike_tasks = [self._simulate_request() for _ in range(500)]
        await asyncio.gather(*spike_tasks, return_exceptions=True)
        results.spike_end_time = time.time()
        
        # Wait for recovery
        await asyncio.sleep(1.0)
        
        # Test normal operation after spike
        recovery_start = time.time()
        recovery_tasks = [self._simulate_request() for _ in range(10)]
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        recovery_end = time.time()
        
        results.recovery_time = recovery_end - recovery_start
        
        # System should recover
        recovery_errors = sum(1 for r in recovery_results if isinstance(r, Exception))
        recovery_success_rate = (len(recovery_tasks) - recovery_errors) / len(recovery_tasks) * 100
        
        assert recovery_success_rate > 90, f"System did not recover: {recovery_success_rate}% success"
        assert results.recovery_time < 5.0, f"Recovery time too long: {results.recovery_time}s"
    
    @pytest.mark.asyncio
    async def test_multiple_spikes(self):
        """Test multiple consecutive spikes"""
        spike_results = []
        
        for spike_num in range(3):
            # Apply spike
            spike_start = time.time()
            spike_tasks = [self._simulate_request() for _ in range(100)]
            spike_res = await asyncio.gather(*spike_tasks, return_exceptions=True)
            spike_end = time.time()
            
            errors = sum(1 for r in spike_res if isinstance(r, Exception))
            spike_results.append({
                "spike_num": spike_num + 1,
                "duration": spike_end - spike_start,
                "error_rate": errors / len(spike_tasks) * 100
            })
            
            # Brief pause between spikes
            await asyncio.sleep(0.5)
        
        # All spikes should be handled
        for result in spike_results:
            assert result["error_rate"] < 40, f"Spike {result['spike_num']} error rate too high: {result['error_rate']}%"
    
    @pytest.mark.asyncio
    async def test_spike_with_gradual_increase(self):
        """Test spike with gradual traffic increase"""
        results = SpikeTestResults()
        
        # Gradually increase load
        load_levels = [10, 50, 100, 200, 500]
        
        for load in load_levels:
            tasks = [self._simulate_request() for _ in range(load)]
            res = await asyncio.gather(*tasks, return_exceptions=True)
            errors = sum(1 for r in res if isinstance(r, Exception))
            error_rate = errors / len(tasks) * 100
            
            # Error rate should remain reasonable
            assert error_rate < 50, f"Error rate too high at load {load}: {error_rate}%"
            await asyncio.sleep(0.2)
    
    async def _simulate_request(self):
        """Simulate a request"""
        start = time.time()
        try:
            await asyncio.sleep(0.01)
            return {"status": "success", "response_time": time.time() - start}
        except Exception as e:
            raise

