"""Integration layer for performance monitoring and optimization across the DocForge system."""

import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .performance_metrics import metrics_collector, monitor_performance
from .database_optimization import db_optimizer, create_optimized_engine
from .caching_strategies import cache_manager, setup_multilevel_cache
from .performance_benchmarks import create_benchmark_suite, benchmark
from .performance_dashboard import dashboard, get_performance_summary

logger = logging.getLogger(__name__)


class PerformanceIntegration:
    """Central integration point for all performance monitoring and optimization."""
    
    def __init__(self):
        """Initialize performance integration."""
        self.initialized = False
        self.config = {}
        self._lock = threading.RLock()
    
    def initialize(self, config: Dict[str, Any]):
        """Initialize performance system with configuration."""
        with self._lock:
            if self.initialized:
                logger.warning("Performance system already initialized")
                return
            
            self.config = config
            
            try:
                # Initialize database optimization
                self._setup_database_optimization()
                
                # Initialize caching
                self._setup_caching()
                
                # Initialize benchmarking
                self._setup_benchmarking()
                
                # Initialize monitoring and alerting
                self._setup_monitoring()
                
                self.initialized = True
                logger.info("Performance system initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize performance system: {e}")
                raise
    
    def _setup_database_optimization(self):
        """Setup database optimization."""
        db_config = self.config.get('database', {})
        
        # Configure slow query threshold
        threshold = db_config.get('slow_query_threshold', 1.0)
        db_optimizer.slow_query_threshold = threshold
        
        # Enable/disable query cache
        cache_enabled = db_config.get('query_cache_enabled', True)
        db_optimizer.query_cache_enabled = cache_enabled
        
        if cache_enabled:
            cache_size = db_config.get('query_cache_size', 1000)
            cache_ttl = db_config.get('query_cache_ttl', 300)
            db_optimizer.max_cache_size = cache_size
            db_optimizer.cache_ttl = cache_ttl
        
        logger.info(f"Database optimization configured: slow_query_threshold={threshold}s, cache_enabled={cache_enabled}")
    
    def _setup_caching(self):
        """Setup caching strategies."""
        cache_config = self.config.get('caching', {})
        
        # Setup Redis cache if configured
        redis_url = cache_config.get('redis_url')
        if redis_url:
            try:
                cache_manager.create_redis_cache('redis', redis_url)
                logger.info(f"Redis cache configured: {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to setup Redis cache: {e}")
        
        # Setup multi-level cache
        multilevel_config = cache_config.get('multilevel', {})
        if multilevel_config.get('enabled', True):
            l1_size = multilevel_config.get('l1_max_size', 1000)
            setup_multilevel_cache('multilevel', l1_size, redis_url)
            logger.info(f"Multi-level cache configured: L1_size={l1_size}")
        
        # Add caching strategies
        strategies = cache_config.get('strategies', {})
        for strategy_name, strategy_config in strategies.items():
            cache_manager.add_strategy(
                strategy_name,
                strategy_config.get('cache_name', 'default'),
                strategy_config.get('ttl', 3600)
            )
            logger.info(f"Cache strategy added: {strategy_name}")
    
    def _setup_benchmarking(self):
        """Setup performance benchmarking."""
        benchmark_config = self.config.get('benchmarking', {})
        
        if benchmark_config.get('enabled', True):
            # Create default benchmark suite
            suite = create_benchmark_suite('system')
            
            # Add system benchmarks
            self._add_system_benchmarks(suite)
            
            logger.info("Performance benchmarking configured")
    
    def _add_system_benchmarks(self, suite):
        """Add system-level benchmarks."""
        
        @suite.benchmark('memory_allocation')
        def benchmark_memory_allocation():
            """Benchmark memory allocation performance."""
            data = []
            for i in range(10000):
                data.append({'id': i, 'value': f'item_{i}'})
            return len(data)
        
        @suite.benchmark('cpu_computation')
        def benchmark_cpu_computation():
            """Benchmark CPU computation performance."""
            result = 0
            for i in range(100000):
                result += i * i
            return result
        
        @suite.benchmark('file_io')
        def benchmark_file_io():
            """Benchmark file I/O performance."""
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                for i in range(1000):
                    f.write(f"line {i}\n")
                temp_path = f.name
            
            try:
                with open(temp_path, 'r') as f:
                    lines = f.readlines()
                return len(lines)
            finally:
                os.unlink(temp_path)
    
    def _setup_monitoring(self):
        """Setup monitoring and alerting."""
        monitoring_config = self.config.get('monitoring', {})
        
        # Configure monitoring interval
        interval = monitoring_config.get('interval_seconds', 30)
        dashboard.monitoring_interval = interval
        
        # Configure email alerts
        email_config = monitoring_config.get('email_alerts', {})
        if email_config.get('enabled', False):
            dashboard.alert_manager.configure_email_notifications(
                smtp_host=email_config['smtp_host'],
                smtp_port=email_config['smtp_port'],
                from_email=email_config['from_email'],
                to_emails=email_config['to_emails'],
                username=email_config.get('username'),
                password=email_config.get('password'),
                use_tls=email_config.get('use_tls', True)
            )
            logger.info("Email alerts configured")
        
        # Configure webhook alerts
        webhook_config = monitoring_config.get('webhook_alerts', {})
        if webhook_config.get('enabled', False):
            dashboard.alert_manager.configure_webhook_notifications(
                webhook_config['webhook_url']
            )
            logger.info("Webhook alerts configured")
        
        # Configure custom alert rules
        custom_rules = monitoring_config.get('alert_rules', [])
        for rule_config in custom_rules:
            from .performance_dashboard import AlertRule
            
            rule = AlertRule(
                name=rule_config['name'],
                metric_name=rule_config['metric_name'],
                condition=rule_config['condition'],
                threshold=rule_config['threshold'],
                severity=rule_config['severity'],
                duration_seconds=rule_config.get('duration_seconds', 60),
                cooldown_seconds=rule_config.get('cooldown_seconds', 300)
            )
            dashboard.alert_manager.add_rule(rule)
            logger.info(f"Custom alert rule added: {rule.name}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system performance status."""
        if not self.initialized:
            return {'error': 'Performance system not initialized'}
        
        try:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'initialized': self.initialized,
                'performance_summary': get_performance_summary(),
                'metrics_summary': metrics_collector.get_metrics_summary(),
                'database_stats': db_optimizer.get_database_stats(),
                'cache_stats': cache_manager.get_all_stats(),
                'dashboard_data': dashboard.get_dashboard_data()
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {'error': str(e)}
    
    def optimize_system(self) -> Dict[str, Any]:
        """Run system optimization procedures."""
        if not self.initialized:
            return {'error': 'Performance system not initialized'}
        
        optimization_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'optimizations_applied': []
        }
        
        try:
            # Clean expired cache entries
            for cache_name, cache in cache_manager.caches.items():
                if hasattr(cache, 'cleanup_expired'):
                    expired_count = cache.cleanup_expired()
                    if expired_count > 0:
                        optimization_results['optimizations_applied'].append({
                            'type': 'cache_cleanup',
                            'cache_name': cache_name,
                            'expired_entries_removed': expired_count
                        })
            
            # Clear old query statistics
            if len(db_optimizer.query_stats) > 10000:
                # Keep only the most recent 5000 queries
                sorted_stats = sorted(
                    db_optimizer.query_stats.items(),
                    key=lambda x: x[1].last_execution or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True
                )
                
                db_optimizer.query_stats = dict(sorted_stats[:5000])
                optimization_results['optimizations_applied'].append({
                    'type': 'query_stats_cleanup',
                    'entries_removed': len(sorted_stats) - 5000
                })
            
            # Reset metrics if they're getting too large
            if len(metrics_collector.metrics) > 50:
                old_count = len(metrics_collector.metrics)
                # Keep only recent metrics for each metric name
                for metric_name, metric_deque in metrics_collector.metrics.items():
                    if len(metric_deque) > 1000:
                        # Keep only last 500 entries
                        new_deque = type(metric_deque)(list(metric_deque)[-500:], maxlen=metric_deque.maxlen)
                        metrics_collector.metrics[metric_name] = new_deque
                
                optimization_results['optimizations_applied'].append({
                    'type': 'metrics_cleanup',
                    'old_metric_count': old_count,
                    'new_metric_count': len(metrics_collector.metrics)
                })
            
            logger.info(f"System optimization completed: {len(optimization_results['optimizations_applied'])} optimizations applied")
            
        except Exception as e:
            logger.error(f"System optimization failed: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks and return results."""
        if not self.initialized:
            return {'error': 'Performance system not initialized'}
        
        try:
            from .performance_benchmarks import benchmark_suites
            
            results = {}
            
            for suite_name, suite in benchmark_suites.items():
                if suite.benchmarks:
                    logger.info(f"Running benchmark suite: {suite_name}")
                    suite_results = suite.run_all_benchmarks(iterations=50, warmup_iterations=5)
                    results[suite_name] = [result.to_dict() for result in suite_results]
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'benchmark_results': results
            }
            
        except Exception as e:
            logger.error(f"Performance tests failed: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Shutdown performance system."""
        with self._lock:
            if not self.initialized:
                return
            
            try:
                # Stop monitoring
                dashboard.stop_monitoring()
                
                # Stop metrics collection
                metrics_collector.stop_system_metrics_collection()
                
                self.initialized = False
                logger.info("Performance system shutdown completed")
                
            except Exception as e:
                logger.error(f"Error during performance system shutdown: {e}")


# Global performance integration instance
performance_integration = PerformanceIntegration()


# Convenience functions for integration with existing codebase
def initialize_performance_system(config: Dict[str, Any]):
    """Initialize the performance system."""
    performance_integration.initialize(config)


def get_performance_status() -> Dict[str, Any]:
    """Get performance system status."""
    return performance_integration.get_system_status()


def optimize_performance() -> Dict[str, Any]:
    """Run performance optimizations."""
    return performance_integration.optimize_system()


def run_performance_benchmarks() -> Dict[str, Any]:
    """Run performance benchmarks."""
    return performance_integration.run_performance_tests()


# Decorators for easy integration
def monitor_docforge_operation(operation_name: Optional[str] = None):
    """Decorator for monitoring DocForge operations."""
    return monitor_performance(operation_name, record_args=True, record_result=True)


def cached_docforge_operation(ttl: int = 3600, cache_name: str = "multilevel"):
    """Decorator for caching DocForge operations."""
    return cache_manager.cached(cache_name=cache_name, ttl=ttl)


# Integration with existing DocForge components
def setup_docforge_performance_monitoring():
    """Setup performance monitoring for DocForge components."""
    
    # Default configuration
    default_config = {
        'database': {
            'slow_query_threshold': 1.0,
            'query_cache_enabled': True,
            'query_cache_size': 1000,
            'query_cache_ttl': 300
        },
        'caching': {
            'multilevel': {
                'enabled': True,
                'l1_max_size': 1000
            },
            'strategies': {
                'document_processing': {
                    'cache_name': 'multilevel',
                    'ttl': 1800  # 30 minutes
                },
                'rag_queries': {
                    'cache_name': 'multilevel',
                    'ttl': 3600  # 1 hour
                },
                'metadata_queries': {
                    'cache_name': 'default',
                    'ttl': 600  # 10 minutes
                }
            }
        },
        'benchmarking': {
            'enabled': True
        },
        'monitoring': {
            'interval_seconds': 30,
            'alert_rules': [
                {
                    'name': 'document_processing_slow',
                    'metric_name': 'document_processing.avg_time',
                    'condition': 'gt',
                    'threshold': 30.0,  # 30 seconds
                    'severity': 'warning',
                    'duration_seconds': 120
                },
                {
                    'name': 'rag_query_slow',
                    'metric_name': 'rag_query.avg_time',
                    'condition': 'gt',
                    'threshold': 5.0,  # 5 seconds
                    'severity': 'warning',
                    'duration_seconds': 60
                }
            ]
        }
    }
    
    # Initialize with default config
    initialize_performance_system(default_config)
    
    logger.info("DocForge performance monitoring setup completed")