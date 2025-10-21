"""
Real-time monitoring dashboard for DocForge Brain MVP.

This module provides real-time monitoring capabilities including:
- System health monitoring
- Processing queue monitoring
- Performance metrics tracking
- Error rate monitoring
- Resource usage monitoring
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import asyncio

from .logging_system import get_logger, LogCategory


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    processing_queue_size: int
    error_rate: float
    avg_response_time: float


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    component: str
    status: str  # healthy, warning, critical, unknown
    last_activity: float
    error_count: int
    performance_score: float
    details: Dict[str, Any]


class MonitoringDashboard:
    """Real-time monitoring dashboard for DocForge system."""
    
    def __init__(self, log_dir: str = "logs", metrics_retention_hours: int = 24):
        """Initialize monitoring dashboard."""
        self.log_dir = Path(log_dir)
        self.metrics_retention_hours = metrics_retention_hours
        self.logger = get_logger()
        
        # Metrics storage
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 metrics
        self.component_health = {}
        self.alert_thresholds = self._get_default_thresholds()
        
        # Performance tracking
        self.response_times = deque(maxlen=100)
        self.error_counts = defaultdict(int)
        self.processing_queue = deque()
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Initialize component health
        self._initialize_component_health()
    
    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default alert thresholds."""
        return {
            'cpu': {'warning': 70.0, 'critical': 90.0},
            'memory': {'warning': 80.0, 'critical': 95.0},
            'disk': {'warning': 85.0, 'critical': 95.0},
            'error_rate': {'warning': 5.0, 'critical': 10.0},
            'response_time': {'warning': 2.0, 'critical': 5.0},
            'queue_size': {'warning': 50, 'critical': 100}
        }
    
    def _initialize_component_health(self):
        """Initialize health status for all components."""
        components = [
            'preprocessing', 'postprocessing', 'storage', 
            'rag', 'versioning', 'api', 'authentication'
        ]
        
        for component in components:
            self.component_health[component] = ComponentHealth(
                component=component,
                status='unknown',
                last_activity=time.time(),
                error_count=0,
                performance_score=100.0,
                details={}
            )
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Start real-time monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info(
            LogCategory.SYSTEM,
            "monitoring_dashboard",
            "Monitoring dashboard started",
            details={'interval_seconds': interval_seconds}
        )
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info(
            LogCategory.SYSTEM,
            "monitoring_dashboard",
            "Monitoring dashboard stopped"
        )
    
    def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Update component health
                self._update_component_health()
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(
                    LogCategory.SYSTEM,
                    "monitoring_dashboard",
                    f"Error in monitoring loop: {str(e)}",
                    details={'error': str(e)}
                )
                time.sleep(interval_seconds)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            import psutil
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network connections (approximate)
            connections = len(psutil.net_connections())
            
        except ImportError:
            # Fallback if psutil not available
            cpu_percent = 0.0
            memory_percent = 0.0
            memory_used_mb = 0.0
            disk_usage_percent = 0.0
            connections = 0
        else:
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            disk_usage_percent = disk.percent
        
        # Application metrics
        queue_size = len(self.processing_queue)
        error_rate = self._calculate_error_rate()
        avg_response_time = self._calculate_avg_response_time()
        
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_usage_percent=disk_usage_percent,
            active_connections=connections,
            processing_queue_size=queue_size,
            error_rate=error_rate,
            avg_response_time=avg_response_time
        )
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        if not self.response_times:
            return 0.0
        
        # Simple error rate calculation
        total_errors = sum(self.error_counts.values())
        total_requests = len(self.response_times)
        
        return (total_errors / max(total_requests, 1)) * 100
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        
        return sum(self.response_times) / len(self.response_times)
    
    def _update_component_health(self):
        """Update health status for all components."""
        current_time = time.time()
        
        for component_name, health in self.component_health.items():
            # Check last activity
            time_since_activity = current_time - health.last_activity
            
            # Determine status based on activity and errors
            if time_since_activity > 300:  # 5 minutes
                health.status = 'unknown'
            elif health.error_count > 10:
                health.status = 'critical'
            elif health.error_count > 5:
                health.status = 'warning'
            else:
                health.status = 'healthy'
            
            # Update performance score
            if health.error_count == 0:
                health.performance_score = min(100.0, health.performance_score + 1.0)
            else:
                health.performance_score = max(0.0, health.performance_score - health.error_count)
    
    def _check_alerts(self, metrics: SystemMetrics):
        """Check for alert conditions."""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_percent >= self.alert_thresholds['cpu']['critical']:
            alerts.append(('critical', 'cpu', f'CPU usage critical: {metrics.cpu_percent:.1f}%'))
        elif metrics.cpu_percent >= self.alert_thresholds['cpu']['warning']:
            alerts.append(('warning', 'cpu', f'CPU usage high: {metrics.cpu_percent:.1f}%'))
        
        # Memory alerts
        if metrics.memory_percent >= self.alert_thresholds['memory']['critical']:
            alerts.append(('critical', 'memory', f'Memory usage critical: {metrics.memory_percent:.1f}%'))
        elif metrics.memory_percent >= self.alert_thresholds['memory']['warning']:
            alerts.append(('warning', 'memory', f'Memory usage high: {metrics.memory_percent:.1f}%'))
        
        # Queue size alerts
        if metrics.processing_queue_size >= self.alert_thresholds['queue_size']['critical']:
            alerts.append(('critical', 'queue', f'Processing queue critical: {metrics.processing_queue_size}'))
        elif metrics.processing_queue_size >= self.alert_thresholds['queue_size']['warning']:
            alerts.append(('warning', 'queue', f'Processing queue high: {metrics.processing_queue_size}'))
        
        # Error rate alerts
        if metrics.error_rate >= self.alert_thresholds['error_rate']['critical']:
            alerts.append(('critical', 'errors', f'Error rate critical: {metrics.error_rate:.1f}%'))
        elif metrics.error_rate >= self.alert_thresholds['error_rate']['warning']:
            alerts.append(('warning', 'errors', f'Error rate high: {metrics.error_rate:.1f}%'))
        
        # Log alerts
        for severity, category, message in alerts:
            self.logger.warning(
                LogCategory.SYSTEM,
                "monitoring_alert",
                f"ALERT [{severity.upper()}]: {message}",
                details={
                    'alert_severity': severity,
                    'alert_category': category,
                    'metrics': asdict(metrics)
                }
            )
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff_time = time.time() - (self.metrics_retention_hours * 3600)
        
        # Clean metrics history
        while self.metrics_history and self.metrics_history[0].timestamp < cutoff_time:
            self.metrics_history.popleft()
        
        # Reset error counts periodically
        if int(time.time()) % 3600 == 0:  # Every hour
            self.error_counts.clear()
    
    # Public API methods
    def record_api_request(self, response_time: float, status_code: int):
        """Record API request metrics."""
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_counts['api_errors'] += 1
        
        # Update API component health
        if 'api' in self.component_health:
            self.component_health['api'].last_activity = time.time()
    
    def record_processing_task(self, task_id: str, operation: str):
        """Record processing task."""
        self.processing_queue.append({
            'task_id': task_id,
            'operation': operation,
            'timestamp': time.time()
        })
    
    def complete_processing_task(self, task_id: str, success: bool):
        """Mark processing task as complete."""
        # Remove from queue
        self.processing_queue = deque([
            task for task in self.processing_queue 
            if task.get('task_id') != task_id
        ])
        
        if not success:
            self.error_counts['processing_errors'] += 1
    
    def record_component_activity(self, component: str, success: bool = True):
        """Record component activity."""
        if component in self.component_health:
            self.component_health[component].last_activity = time.time()
            
            if not success:
                self.component_health[component].error_count += 1
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status."""
        current_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'timestamp': time.time(),
            'overall_status': self._get_overall_status(),
            'current_metrics': asdict(current_metrics) if current_metrics else None,
            'component_health': {
                name: asdict(health) 
                for name, health in self.component_health.items()
            },
            'active_alerts': self._get_active_alerts(),
            'queue_status': {
                'size': len(self.processing_queue),
                'oldest_task_age': self._get_oldest_task_age()
            }
        }
    
    def _get_overall_status(self) -> str:
        """Get overall system status."""
        if not self.component_health:
            return 'unknown'
        
        statuses = [health.status for health in self.component_health.values()]
        
        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        elif all(status == 'healthy' for status in statuses):
            return 'healthy'
        else:
            return 'degraded'
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        if not self.metrics_history:
            return []
        
        current_metrics = self.metrics_history[-1]
        alerts = []
        
        # Check current thresholds
        if current_metrics.cpu_percent >= self.alert_thresholds['cpu']['warning']:
            alerts.append({
                'type': 'cpu',
                'severity': 'critical' if current_metrics.cpu_percent >= self.alert_thresholds['cpu']['critical'] else 'warning',
                'message': f'CPU usage: {current_metrics.cpu_percent:.1f}%',
                'value': current_metrics.cpu_percent
            })
        
        if current_metrics.memory_percent >= self.alert_thresholds['memory']['warning']:
            alerts.append({
                'type': 'memory',
                'severity': 'critical' if current_metrics.memory_percent >= self.alert_thresholds['memory']['critical'] else 'warning',
                'message': f'Memory usage: {current_metrics.memory_percent:.1f}%',
                'value': current_metrics.memory_percent
            })
        
        return alerts
    
    def _get_oldest_task_age(self) -> float:
        """Get age of oldest task in queue."""
        if not self.processing_queue:
            return 0.0
        
        oldest_timestamp = min(task['timestamp'] for task in self.processing_queue)
        return time.time() - oldest_timestamp
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours."""
        cutoff_time = time.time() - (hours * 3600)
        
        return [
            asdict(metrics) for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics_history:
            return {}
        
        recent_metrics = [m for m in self.metrics_history if m.timestamp > time.time() - 3600]
        
        if not recent_metrics:
            return {}
        
        return {
            'avg_cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            'avg_memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            'avg_response_time': sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics),
            'avg_queue_size': sum(m.processing_queue_size for m in recent_metrics) / len(recent_metrics),
            'total_errors': sum(self.error_counts.values()),
            'uptime_hours': (time.time() - recent_metrics[0].timestamp) / 3600
        }
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        export_data = {
            'timestamp': time.time(),
            'metrics_history': [asdict(m) for m in self.metrics_history],
            'component_health': {
                name: asdict(health) 
                for name, health in self.component_health.items()
            },
            'performance_summary': self.get_performance_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)


# Global monitoring dashboard instance
_dashboard_instance = None


def get_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard()
    return _dashboard_instance


def start_monitoring(interval_seconds: int = 30):
    """Start system monitoring."""
    dashboard = get_dashboard()
    dashboard.start_monitoring(interval_seconds)


def stop_monitoring():
    """Stop system monitoring."""
    dashboard = get_dashboard()
    dashboard.stop_monitoring()


# Convenience functions
def record_api_request(response_time: float, status_code: int):
    """Record API request metrics."""
    get_dashboard().record_api_request(response_time, status_code)


def record_processing_task(task_id: str, operation: str):
    """Record processing task."""
    get_dashboard().record_processing_task(task_id, operation)


def complete_processing_task(task_id: str, success: bool):
    """Complete processing task."""
    get_dashboard().complete_processing_task(task_id, success)


def record_component_activity(component: str, success: bool = True):
    """Record component activity."""
    get_dashboard().record_component_activity(component, success)


if __name__ == "__main__":
    # Test monitoring dashboard
    dashboard = MonitoringDashboard()
    dashboard.start_monitoring(5)  # 5 second intervals for testing
    
    try:
        # Simulate some activity
        time.sleep(10)
        dashboard.record_api_request(0.5, 200)
        dashboard.record_processing_task("test_task", "preprocessing")
        time.sleep(5)
        dashboard.complete_processing_task("test_task", True)
        
        # Print status
        status = dashboard.get_current_status()
        print(json.dumps(status, indent=2))
        
    finally:
        dashboard.stop_monitoring()