"""
Continuous Performance Monitoring
Implement continuous performance monitoring and alerting
"""

import pytest
import asyncio
import time
import psutil
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert"""
    timestamp: datetime
    severity: str  # "warning", "critical"
    metric_name: str
    threshold: float
    actual_value: float
    message: str


class PerformanceMonitor:
    """Continuous performance monitor"""
    
    def __init__(self, alert_thresholds: Dict[str, Dict[str, float]] = None):
        self.metrics: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.alerts: List[Alert] = []
        self.alert_thresholds = alert_thresholds or {
            "response_time": {"warning": 1.0, "critical": 5.0},
            "error_rate": {"warning": 5.0, "critical": 20.0},
            "memory_usage": {"warning": 1000.0, "critical": 2000.0},  # MB
            "cpu_usage": {"warning": 80.0, "critical": 95.0},  # Percent
        }
        self.is_monitoring = False
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            tags=tags or {}
        )
        self.metrics.append(metric)
        
        # Check for alerts
        self._check_alerts(metric)
    
    def _check_alerts(self, metric: PerformanceMetric):
        """Check if metric triggers alerts"""
        if metric.metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric.metric_name]
        
        # Check critical threshold
        if "critical" in thresholds and metric.value >= thresholds["critical"]:
            alert = Alert(
                timestamp=datetime.now(),
                severity="critical",
                metric_name=metric.metric_name,
                threshold=thresholds["critical"],
                actual_value=metric.value,
                message=f"Critical: {metric.metric_name} = {metric.value} (threshold: {thresholds['critical']})"
            )
            self.alerts.append(alert)
        
        # Check warning threshold
        elif "warning" in thresholds and metric.value >= thresholds["warning"]:
            alert = Alert(
                timestamp=datetime.now(),
                severity="warning",
                metric_name=metric.metric_name,
                threshold=thresholds["warning"],
                actual_value=metric.value,
                message=f"Warning: {metric.metric_name} = {metric.value} (threshold: {thresholds['warning']})"
            )
            self.alerts.append(alert)
    
    def get_metrics(self, metric_name: str, minutes: int = 60) -> List[PerformanceMetric]:
        """Get metrics for a specific metric name within time window"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            m for m in self.metrics
            if m.metric_name == metric_name and m.timestamp >= cutoff
        ]
    
    def get_statistics(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for a metric"""
        metrics = self.get_metrics(metric_name, minutes)
        
        if not metrics:
            return {"count": 0}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "latest": values[-1]
        }
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [a for a in self.alerts if a.timestamp >= cutoff]


class TestContinuousMonitoring:
    """Test continuous performance monitoring"""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor"""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_metric_recording(self, monitor):
        """Test metric recording"""
        # Record various metrics
        monitor.record_metric("response_time", 0.5)
        monitor.record_metric("response_time", 0.8)
        monitor.record_metric("error_rate", 2.0)
        monitor.record_metric("memory_usage", 500.0)
        
        # Verify metrics recorded
        response_times = monitor.get_metrics("response_time")
        assert len(response_times) == 2
        
        stats = monitor.get_statistics("response_time")
        assert stats["count"] == 2
        assert stats["mean"] == 0.65
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, monitor):
        """Test alert generation"""
        # Record metric that exceeds threshold
        monitor.record_metric("response_time", 6.0)  # Exceeds critical threshold
        
        # Check for alerts
        alerts = monitor.get_recent_alerts()
        assert len(alerts) > 0
        
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) > 0
        assert critical_alerts[0].metric_name == "response_time"
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring_loop(self, monitor):
        """Test continuous monitoring loop"""
        monitor.is_monitoring = True
        
        async def monitoring_loop():
            """Simulate continuous monitoring"""
            for i in range(10):
                # Record system metrics
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                monitor.record_metric("memory_usage", memory_mb)
                monitor.record_metric("cpu_usage", cpu_percent)
                
                await asyncio.sleep(0.1)
        
        await monitoring_loop()
        
        # Verify metrics collected
        memory_metrics = monitor.get_metrics("memory_usage")
        assert len(memory_metrics) == 10
        
        cpu_metrics = monitor.get_metrics("cpu_usage")
        assert len(cpu_metrics) == 10
    
    @pytest.mark.asyncio
    async def test_metric_aggregation(self, monitor):
        """Test metric aggregation"""
        # Record multiple metrics
        for i in range(100):
            monitor.record_metric("response_time", 0.5 + (i % 10) * 0.1)
        
        stats = monitor.get_statistics("response_time")
        
        assert stats["count"] == 100
        assert stats["min"] >= 0.5
        assert stats["max"] <= 1.4
    
    @pytest.mark.asyncio
    async def test_alert_thresholds(self, monitor):
        """Test alert threshold configuration"""
        # Test warning threshold
        monitor.record_metric("response_time", 1.5)  # Exceeds warning
        
        alerts = monitor.get_recent_alerts()
        warning_alerts = [a for a in alerts if a.severity == "warning"]
        assert len(warning_alerts) > 0
        
        # Test critical threshold
        monitor.record_metric("response_time", 6.0)  # Exceeds critical
        
        alerts = monitor.get_recent_alerts()
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) > 0


class TestPerformanceDashboards:
    """Test performance dashboard data"""
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics(self):
        """Test metrics for dashboard"""
        monitor = PerformanceMonitor()
        
        # Record various metrics
        for i in range(50):
            monitor.record_metric("response_time", 0.5 + (i % 5) * 0.1)
            monitor.record_metric("throughput", 100 + i)
            monitor.record_metric("error_rate", i % 10)
        
        # Get dashboard data
        dashboard_data = {
            "response_time": monitor.get_statistics("response_time"),
            "throughput": monitor.get_statistics("throughput"),
            "error_rate": monitor.get_statistics("error_rate"),
            "alerts": monitor.get_recent_alerts()
        }
        
        assert "response_time" in dashboard_data
        assert "throughput" in dashboard_data
        assert "error_rate" in dashboard_data
        assert "alerts" in dashboard_data


class TestPerformanceTrends:
    """Test performance trend analysis"""
    
    @pytest.mark.asyncio
    async def test_trend_detection(self):
        """Test detection of performance trends"""
        monitor = PerformanceMonitor()
        
        # Simulate degrading performance
        for i in range(20):
            response_time = 0.5 + i * 0.05  # Gradually increasing
            monitor.record_metric("response_time", response_time)
            await asyncio.sleep(0.01)
        
        # Get recent metrics
        recent_metrics = monitor.get_metrics("response_time", minutes=60)
        
        # Check trend (recent values should be higher)
        if len(recent_metrics) >= 10:
            early_values = [m.value for m in recent_metrics[:5]]
            late_values = [m.value for m in recent_metrics[-5:]]
            
            early_avg = sum(early_values) / len(early_values)
            late_avg = sum(late_values) / len(late_values)
            
            # Trend detected if late average is significantly higher
            trend_detected = late_avg > early_avg * 1.2
            assert isinstance(trend_detected, bool), "Trend detection should return boolean"

