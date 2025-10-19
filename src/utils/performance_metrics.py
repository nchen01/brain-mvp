"""Performance metrics collection and monitoring system."""

import time
import threading
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import contextmanager
import functools
import asyncio
import inspect

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'labels': self.labels
        }


@dataclass
class PerformanceStats:
    """Performance statistics for an operation."""
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    error_count: int = 0
    last_execution: Optional[datetime] = None
    
    def update(self, execution_time: float, error: bool = False):
        """Update statistics with new execution."""
        self.count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.count
        self.last_execution = datetime.now(timezone.utc)
        
        if error:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'count': self.count,
            'total_time': self.total_time,
            'min_time': self.min_time if self.min_time != float('inf') else 0.0,
            'max_time': self.max_time,
            'avg_time': self.avg_time,
            'p95_time': self.p95_time,
            'p99_time': self.p99_time,
            'error_count': self.error_count,
            'error_rate': self.error_count / self.count if self.count > 0 else 0.0,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None
        }


class MetricsCollector:
    """Centralized metrics collection system."""
    
    def __init__(self, max_history: int = 10000):
        """Initialize metrics collector."""
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.performance_stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self.execution_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.RLock()
        
        # System metrics
        self.system_metrics_enabled = True
        self.system_metrics_interval = 60  # seconds
        self._system_metrics_thread = None
        self._stop_system_metrics = threading.Event()
        
        # Start system metrics collection
        self.start_system_metrics_collection()
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        with self._lock:
            metric_point = MetricPoint(
                timestamp=datetime.now(timezone.utc),
                value=value,
                labels=labels or {}
            )
            self.metrics[name].append(metric_point)
    
    def record_execution_time(self, operation: str, execution_time: float, error: bool = False):
        """Record execution time for an operation."""
        with self._lock:
            # Update performance statistics
            self.performance_stats[operation].update(execution_time, error)
            
            # Store execution time for percentile calculations
            self.execution_times[operation].append(execution_time)
            
            # Update percentiles if we have enough data
            if len(self.execution_times[operation]) >= 20:
                times = sorted(self.execution_times[operation])
                p95_idx = int(len(times) * 0.95)
                p99_idx = int(len(times) * 0.99)
                self.performance_stats[operation].p95_time = times[p95_idx]
                self.performance_stats[operation].p99_time = times[p99_idx]
            
            # Record as metric
            self.record_metric(f"execution_time.{operation}", execution_time, {
                'operation': operation,
                'error': str(error)
            })
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self.record_metric(name, 1.0, labels)
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric (current value)."""
        self.record_metric(name, value, labels)
    
    def get_metric_history(self, name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metric history."""
        with self._lock:
            history = list(self.metrics[name])
            if limit:
                history = history[-limit:]
            return [point.to_dict() for point in history]
    
    def get_performance_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            if operation:
                return self.performance_stats[operation].to_dict()
            else:
                return {op: stats.to_dict() for op, stats in self.performance_stats.items()}
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'num_fds': process.num_fds() if hasattr(process, 'num_fds') else None
                }
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def start_system_metrics_collection(self):
        """Start background system metrics collection."""
        if not self.system_metrics_enabled or self._system_metrics_thread:
            return
        
        def collect_system_metrics():
            """Background thread for system metrics collection."""
            while not self._stop_system_metrics.wait(self.system_metrics_interval):
                try:
                    metrics = self.get_system_metrics()
                    timestamp = datetime.now(timezone.utc)
                    
                    # Record CPU metrics
                    if 'cpu' in metrics:
                        self.record_gauge('system.cpu.percent', metrics['cpu']['percent'])
                        if metrics['cpu']['load_avg']:
                            self.record_gauge('system.cpu.load_avg_1m', metrics['cpu']['load_avg'][0])
                    
                    # Record memory metrics
                    if 'memory' in metrics:
                        self.record_gauge('system.memory.percent', metrics['memory']['percent'])
                        self.record_gauge('system.memory.used_bytes', metrics['memory']['used'])
                        self.record_gauge('system.memory.available_bytes', metrics['memory']['available'])
                    
                    # Record disk metrics
                    if 'disk' in metrics:
                        self.record_gauge('system.disk.percent', metrics['disk']['percent'])
                        self.record_gauge('system.disk.used_bytes', metrics['disk']['used'])
                        self.record_gauge('system.disk.free_bytes', metrics['disk']['free'])
                    
                    # Record process metrics
                    if 'process' in metrics:
                        self.record_gauge('process.memory.rss_bytes', metrics['process']['memory_rss'])
                        self.record_gauge('process.cpu.percent', metrics['process']['cpu_percent'])
                        self.record_gauge('process.threads.count', metrics['process']['num_threads'])
                        if metrics['process']['num_fds']:
                            self.record_gauge('process.fds.count', metrics['process']['num_fds'])
                
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")
        
        self._system_metrics_thread = threading.Thread(
            target=collect_system_metrics,
            daemon=True,
            name="SystemMetricsCollector"
        )
        self._system_metrics_thread.start()
        logger.info("Started system metrics collection")
    
    def stop_system_metrics_collection(self):
        """Stop background system metrics collection."""
        if self._system_metrics_thread:
            self._stop_system_metrics.set()
            self._system_metrics_thread.join(timeout=5)
            self._system_metrics_thread = None
            logger.info("Stopped system metrics collection")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self._lock:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_metrics': len(self.metrics),
                'total_operations': len(self.performance_stats),
                'system_metrics': self.get_system_metrics(),
                'performance_stats': self.get_performance_stats(),
                'top_operations': self._get_top_operations(),
                'alerts': self._check_performance_alerts()
            }
    
    def _get_top_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top operations by various metrics."""
        operations = []
        
        for op_name, stats in self.performance_stats.items():
            operations.append({
                'operation': op_name,
                'total_time': stats.total_time,
                'avg_time': stats.avg_time,
                'count': stats.count,
                'error_rate': stats.error_count / stats.count if stats.count > 0 else 0.0
            })
        
        # Sort by total time
        top_by_time = sorted(operations, key=lambda x: x['total_time'], reverse=True)[:limit]
        
        # Sort by average time
        top_by_avg = sorted(operations, key=lambda x: x['avg_time'], reverse=True)[:limit]
        
        # Sort by error rate
        top_by_errors = sorted(operations, key=lambda x: x['error_rate'], reverse=True)[:limit]
        
        return {
            'by_total_time': top_by_time,
            'by_avg_time': top_by_avg,
            'by_error_rate': top_by_errors
        }
    
    def _check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts."""
        alerts = []
        
        # Check system metrics
        system_metrics = self.get_system_metrics()
        
        if system_metrics.get('cpu', {}).get('percent', 0) > 80:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f"High CPU usage: {system_metrics['cpu']['percent']:.1f}%",
                'value': system_metrics['cpu']['percent']
            })
        
        if system_metrics.get('memory', {}).get('percent', 0) > 85:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f"High memory usage: {system_metrics['memory']['percent']:.1f}%",
                'value': system_metrics['memory']['percent']
            })
        
        if system_metrics.get('disk', {}).get('percent', 0) > 90:
            alerts.append({
                'type': 'high_disk',
                'severity': 'critical',
                'message': f"High disk usage: {system_metrics['disk']['percent']:.1f}%",
                'value': system_metrics['disk']['percent']
            })
        
        # Check operation performance
        for op_name, stats in self.performance_stats.items():
            if stats.count > 10:  # Only check operations with sufficient data
                error_rate = stats.error_count / stats.count
                if error_rate > 0.1:  # 10% error rate
                    alerts.append({
                        'type': 'high_error_rate',
                        'severity': 'warning',
                        'message': f"High error rate for {op_name}: {error_rate:.1%}",
                        'operation': op_name,
                        'value': error_rate
                    })
                
                if stats.avg_time > 5.0:  # 5 second average
                    alerts.append({
                        'type': 'slow_operation',
                        'severity': 'warning',
                        'message': f"Slow operation {op_name}: {stats.avg_time:.2f}s average",
                        'operation': op_name,
                        'value': stats.avg_time
                    })
        
        return alerts
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.performance_stats.clear()
            self.execution_times.clear()
    
    def shutdown(self):
        """Shutdown metrics collector."""
        self.stop_system_metrics_collection()


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Decorator for automatic performance monitoring
def monitor_performance(operation_name: Optional[str] = None, 
                       record_args: bool = False,
                       record_result: bool = False):
    """Decorator to monitor function performance."""
    def decorator(func):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                error = False
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    error = True
                    raise
                finally:
                    execution_time = time.time() - start_time
                    metrics_collector.record_execution_time(op_name, execution_time, error)
                    
                    # Record additional metrics if requested
                    if record_args:
                        metrics_collector.record_gauge(f"{op_name}.args_count", len(args) + len(kwargs))
                    
                    if record_result and not error:
                        try:
                            if hasattr(result, '__len__'):
                                metrics_collector.record_gauge(f"{op_name}.result_size", len(result))
                        except:
                            pass
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                error = False
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error = True
                    raise
                finally:
                    execution_time = time.time() - start_time
                    metrics_collector.record_execution_time(op_name, execution_time, error)
                    
                    # Record additional metrics if requested
                    if record_args:
                        metrics_collector.record_gauge(f"{op_name}.args_count", len(args) + len(kwargs))
                    
                    if record_result and not error:
                        try:
                            if hasattr(result, '__len__'):
                                metrics_collector.record_gauge(f"{op_name}.result_size", len(result))
                        except:
                            pass
            
            return sync_wrapper
    
    return decorator


@contextmanager
def measure_time(operation_name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager to measure execution time."""
    start_time = time.time()
    error = False
    
    try:
        yield
    except Exception:
        error = True
        raise
    finally:
        execution_time = time.time() - start_time
        metrics_collector.record_execution_time(operation_name, execution_time, error)
        
        if labels:
            metrics_collector.record_metric(f"execution_time.{operation_name}", execution_time, labels)


# Convenience functions
def record_metric(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Record a metric value."""
    metrics_collector.record_metric(name, value, labels)


def increment_counter(name: str, labels: Optional[Dict[str, str]] = None):
    """Increment a counter metric."""
    metrics_collector.increment_counter(name, labels)


def record_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Record a gauge metric."""
    metrics_collector.record_gauge(name, value, labels)


def get_metrics_summary() -> Dict[str, Any]:
    """Get comprehensive metrics summary."""
    return metrics_collector.get_metrics_summary()


def get_performance_stats(operation: Optional[str] = None) -> Dict[str, Any]:
    """Get performance statistics."""
    return metrics_collector.get_performance_stats(operation)


def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    return metrics_collector.get_system_metrics()