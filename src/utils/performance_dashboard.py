"""Performance dashboard and alerting system."""

import time
import threading
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    smtplib = None
    MimeText = None
    MimeMultipart = None
    EMAIL_AVAILABLE = False

from .performance_metrics import metrics_collector, get_system_metrics
from .database_optimization import db_optimizer
from .caching_strategies import cache_manager
from .performance_benchmarks import benchmark_suites

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Performance alert."""
    id: str
    type: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'severity': self.severity,
            'message': self.message,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    threshold: float
    severity: str
    duration_seconds: int = 60  # Alert only if condition persists
    cooldown_seconds: int = 300  # Minimum time between alerts
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if alert condition is met."""
        if not self.enabled:
            return False
        
        if self.condition == 'gt':
            return value > self.threshold
        elif self.condition == 'gte':
            return value >= self.threshold
        elif self.condition == 'lt':
            return value < self.threshold
        elif self.condition == 'lte':
            return value <= self.threshold
        elif self.condition == 'eq':
            return abs(value - self.threshold) < 0.001
        else:
            return False


class AlertManager:
    """Alert management system."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.condition_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = threading.RLock()
        
        # Notification settings
        self.email_enabled = False
        self.email_config = {}
        self.webhook_enabled = False
        self.webhook_url = ""
        
        # Setup default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="system.cpu.percent",
                condition="gt",
                threshold=80.0,
                severity="warning",
                duration_seconds=60
            ),
            AlertRule(
                name="critical_cpu_usage",
                metric_name="system.cpu.percent",
                condition="gt",
                threshold=95.0,
                severity="critical",
                duration_seconds=30
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="system.memory.percent",
                condition="gt",
                threshold=85.0,
                severity="warning",
                duration_seconds=60
            ),
            AlertRule(
                name="critical_memory_usage",
                metric_name="system.memory.percent",
                condition="gt",
                threshold=95.0,
                severity="critical",
                duration_seconds=30
            ),
            AlertRule(
                name="high_disk_usage",
                metric_name="system.disk.percent",
                condition="gt",
                threshold=90.0,
                severity="warning",
                duration_seconds=300
            ),
            AlertRule(
                name="critical_disk_usage",
                metric_name="system.disk.percent",
                condition="gt",
                threshold=98.0,
                severity="critical",
                duration_seconds=60
            ),
            AlertRule(
                name="slow_database_queries",
                metric_name="database.avg_query_time",
                condition="gt",
                threshold=2.0,
                severity="warning",
                duration_seconds=120
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="application.error_rate",
                condition="gt",
                threshold=0.05,  # 5%
                severity="warning",
                duration_seconds=60
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        with self._lock:
            self.rules[rule.name] = rule
            logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule."""
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
    
    def evaluate_rules(self, metrics: Dict[str, float]):
        """Evaluate all alert rules against current metrics."""
        with self._lock:
            current_time = time.time()
            
            for rule_name, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                metric_value = metrics.get(rule.metric_name)
                if metric_value is None:
                    continue
                
                condition_met = rule.evaluate(metric_value)
                
                # Track condition state
                if rule_name not in self.condition_states:
                    self.condition_states[rule_name] = {
                        'first_triggered': None,
                        'last_alerted': 0,
                        'condition_met': False
                    }
                
                state = self.condition_states[rule_name]
                
                if condition_met:
                    if not state['condition_met']:
                        # Condition just became true
                        state['first_triggered'] = current_time
                        state['condition_met'] = True
                    
                    # Check if condition has persisted long enough
                    if (current_time - state['first_triggered'] >= rule.duration_seconds and
                        current_time - state['last_alerted'] >= rule.cooldown_seconds):
                        
                        # Trigger alert
                        alert = self._create_alert(rule, metric_value)
                        self._trigger_alert(alert)
                        state['last_alerted'] = current_time
                
                else:
                    if state['condition_met']:
                        # Condition no longer met, resolve any active alerts
                        self._resolve_alerts_for_rule(rule_name)
                        state['condition_met'] = False
                        state['first_triggered'] = None
    
    def _create_alert(self, rule: AlertRule, current_value: float) -> Alert:
        """Create alert from rule and current value."""
        alert_id = f"{rule.name}_{int(time.time())}"
        
        return Alert(
            id=alert_id,
            type=rule.name,
            severity=rule.severity,
            message=f"{rule.name}: {rule.metric_name} is {current_value:.2f} (threshold: {rule.threshold:.2f})",
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold_value=rule.threshold
        )
    
    def _trigger_alert(self, alert: Alert):
        """Trigger an alert."""
        with self._lock:
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            logger.warning(f"ALERT TRIGGERED: {alert.message}")
            
            # Send notifications
            self._send_notifications(alert)
    
    def _resolve_alerts_for_rule(self, rule_name: str):
        """Resolve all active alerts for a rule."""
        with self._lock:
            alerts_to_resolve = [
                alert for alert in self.active_alerts.values()
                if alert.type == rule_name and not alert.resolved
            ]
            
            for alert in alerts_to_resolve:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                logger.info(f"ALERT RESOLVED: {alert.message}")
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications."""
        try:
            if self.email_enabled:
                self._send_email_notification(alert)
            
            if self.webhook_enabled:
                self._send_webhook_notification(alert)
        
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification."""
        if not self.email_config or not EMAIL_AVAILABLE:
            logger.warning("Email notifications not available")
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = ', '.join(self.email_config['to'])
            msg['Subject'] = f"[{alert.severity.upper()}] DocForge Alert: {alert.type}"
            
            body = f"""
            Alert Details:
            - Type: {alert.type}
            - Severity: {alert.severity}
            - Message: {alert.message}
            - Metric: {alert.metric_name}
            - Current Value: {alert.current_value:.2f}
            - Threshold: {alert.threshold_value:.2f}
            - Timestamp: {alert.timestamp.isoformat()}
            
            Please investigate this issue promptly.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port'])
            if self.email_config.get('use_tls'):
                server.starttls()
            if self.email_config.get('username'):
                server.login(self.email_config['username'], self.email_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.type}")
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification."""
        try:
            import requests
            
            payload = {
                'alert': alert.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook alert sent for {alert.type}")
            else:
                logger.error(f"Webhook alert failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        with self._lock:
            return [alert.to_dict() for alert in self.active_alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get alert history."""
        with self._lock:
            history = list(self.alert_history)
            if limit:
                history = history[-limit:]
            return [alert.to_dict() for alert in history]
    
    def configure_email_notifications(self, smtp_host: str, smtp_port: int,
                                    from_email: str, to_emails: List[str],
                                    username: Optional[str] = None,
                                    password: Optional[str] = None,
                                    use_tls: bool = True):
        """Configure email notifications."""
        self.email_config = {
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'from': from_email,
            'to': to_emails,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        self.email_enabled = True
        logger.info("Email notifications configured")
    
    def configure_webhook_notifications(self, webhook_url: str):
        """Configure webhook notifications."""
        self.webhook_url = webhook_url
        self.webhook_enabled = True
        logger.info(f"Webhook notifications configured: {webhook_url}")


class PerformanceDashboard:
    """Performance monitoring dashboard."""
    
    def __init__(self):
        """Initialize performance dashboard."""
        self.alert_manager = AlertManager()
        self.monitoring_enabled = True
        self.monitoring_interval = 30  # seconds
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start performance monitoring."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitoring_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self._stop_monitoring.wait(self.monitoring_interval):
            try:
                # Collect current metrics
                metrics = self._collect_current_metrics()
                
                # Evaluate alert rules
                self.alert_manager.evaluate_rules(metrics)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_current_metrics(self) -> Dict[str, float]:
        """Collect current performance metrics."""
        metrics = {}
        
        # System metrics
        system_metrics = get_system_metrics()
        if system_metrics:
            metrics.update({
                'system.cpu.percent': system_metrics.get('cpu', {}).get('percent', 0.0),
                'system.memory.percent': system_metrics.get('memory', {}).get('percent', 0.0),
                'system.disk.percent': system_metrics.get('disk', {}).get('percent', 0.0),
                'process.memory.rss_bytes': system_metrics.get('process', {}).get('memory_rss', 0.0),
                'process.cpu.percent': system_metrics.get('process', {}).get('cpu_percent', 0.0)
            })
        
        # Database metrics
        db_stats = db_optimizer.get_database_stats()
        if db_stats and 'query_stats' in db_stats:
            query_stats = db_stats['query_stats']
            if query_stats.get('top_queries'):
                avg_times = [q.get('avg_time', 0) for q in query_stats['top_queries']]
                if avg_times:
                    metrics['database.avg_query_time'] = sum(avg_times) / len(avg_times)
        
        # Cache metrics
        cache_stats = cache_manager.get_all_stats()
        if cache_stats and 'caches' in cache_stats:
            for cache_name, cache_stat in cache_stats['caches'].items():
                hit_rate = cache_stat.get('hit_rate', 0.0)
                metrics[f'cache.{cache_name}.hit_rate'] = hit_rate
        
        # Application metrics from metrics collector
        perf_stats = metrics_collector.get_performance_stats()
        if perf_stats:
            error_rates = []
            for op_name, op_stats in perf_stats.items():
                if isinstance(op_stats, dict) and op_stats.get('count', 0) > 0:
                    error_rate = op_stats.get('error_count', 0) / op_stats['count']
                    error_rates.append(error_rate)
            
            if error_rates:
                metrics['application.error_rate'] = sum(error_rates) / len(error_rates)
        
        return metrics
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_metrics': get_system_metrics(),
            'performance_stats': metrics_collector.get_performance_stats(),
            'database_stats': db_optimizer.get_database_stats(),
            'cache_stats': cache_manager.get_all_stats(),
            'active_alerts': self.alert_manager.get_active_alerts(),
            'alert_history': self.alert_manager.get_alert_history(limit=50),
            'benchmark_results': self._get_recent_benchmark_results(),
            'monitoring_status': {
                'enabled': self.monitoring_enabled,
                'interval_seconds': self.monitoring_interval,
                'uptime_seconds': time.time() - (metrics_collector.created_at if hasattr(metrics_collector, 'created_at') else time.time())
            }
        }
    
    def _get_recent_benchmark_results(self) -> Dict[str, Any]:
        """Get recent benchmark results."""
        results = {}
        
        for suite_name, suite in benchmark_suites.items():
            if suite.results:
                # Get latest results for each benchmark
                latest_results = {}
                for result in suite.results:
                    if result.name not in latest_results or result.timestamp > latest_results[result.name].timestamp:
                        latest_results[result.name] = result
                
                results[suite_name] = {
                    benchmark_name: result.to_dict()
                    for benchmark_name, result in latest_results.items()
                }
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for quick overview."""
        current_metrics = self._collect_current_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Categorize alerts by severity
        alert_counts = {'info': 0, 'warning': 0, 'critical': 0}
        for alert in active_alerts:
            severity = alert.get('severity', 'info')
            alert_counts[severity] = alert_counts.get(severity, 0) + 1
        
        # System health score (0-100)
        health_score = 100
        
        # Deduct points for high resource usage
        cpu_usage = current_metrics.get('system.cpu.percent', 0)
        memory_usage = current_metrics.get('system.memory.percent', 0)
        disk_usage = current_metrics.get('system.disk.percent', 0)
        
        if cpu_usage > 80:
            health_score -= min(20, (cpu_usage - 80) * 2)
        if memory_usage > 85:
            health_score -= min(15, (memory_usage - 85) * 2)
        if disk_usage > 90:
            health_score -= min(25, (disk_usage - 90) * 5)
        
        # Deduct points for alerts
        health_score -= alert_counts['warning'] * 5
        health_score -= alert_counts['critical'] * 15
        
        health_score = max(0, health_score)
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'health_score': health_score,
            'status': 'healthy' if health_score >= 80 else 'degraded' if health_score >= 60 else 'unhealthy',
            'system_metrics': {
                'cpu_percent': cpu_usage,
                'memory_percent': memory_usage,
                'disk_percent': disk_usage
            },
            'alert_counts': alert_counts,
            'total_active_alerts': len(active_alerts),
            'monitoring_enabled': self.monitoring_enabled
        }


# Global dashboard instance
dashboard = PerformanceDashboard()


# Convenience functions
def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data."""
    return dashboard.get_dashboard_data()


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary."""
    return dashboard.get_performance_summary()


def get_active_alerts() -> List[Dict[str, Any]]:
    """Get active alerts."""
    return dashboard.alert_manager.get_active_alerts()


def add_alert_rule(rule: AlertRule):
    """Add alert rule."""
    dashboard.alert_manager.add_rule(rule)


def configure_email_alerts(smtp_host: str, smtp_port: int, from_email: str, to_emails: List[str], **kwargs):
    """Configure email alerts."""
    dashboard.alert_manager.configure_email_notifications(smtp_host, smtp_port, from_email, to_emails, **kwargs)


def configure_webhook_alerts(webhook_url: str):
    """Configure webhook alerts."""
    dashboard.alert_manager.configure_webhook_notifications(webhook_url)