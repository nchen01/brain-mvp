# Performance Monitoring and Optimization System

This document describes the comprehensive performance monitoring and optimization system implemented for DocForge.

## Overview

The performance system provides:

- **Real-time Metrics Collection**: System and application performance metrics
- **Database Query Optimization**: Connection pooling, query caching, and slow query detection
- **Multi-level Caching**: Memory and Redis-based caching with intelligent strategies
- **Performance Benchmarking**: Automated benchmarking and regression testing
- **Alerting and Monitoring**: Real-time alerts with email and webhook notifications
- **Performance Dashboard**: Comprehensive performance visualization and health monitoring

## Architecture

### Core Components

1. **MetricsCollector**: Centralized metrics collection and storage
2. **DatabaseOptimizer**: Database performance optimization and monitoring
3. **CacheManager**: Multi-level caching with various backends
4. **BenchmarkSuite**: Performance benchmarking and regression testing
5. **PerformanceDashboard**: Monitoring dashboard with alerting
6. **PerformanceIntegration**: Central integration layer

## Usage

### Basic Setup

```python
from src.utils.performance_integration import setup_docforge_performance_monitoring

# Initialize with default configuration
setup_docforge_performance_monitoring()
```

### Custom Configuration

```python
from src.utils.performance_integration import initialize_performance_system

config = {
    'database': {
        'slow_query_threshold': 2.0,
        'query_cache_enabled': True,
        'query_cache_size': 2000,
        'query_cache_ttl': 600
    },
    'caching': {
        'redis_url': 'redis://localhost:6379/0',
        'multilevel': {
            'enabled': True,
            'l1_max_size': 2000
        }
    },
    'monitoring': {
        'interval_seconds': 15,
        'email_alerts': {
            'enabled': True,
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'from_email': 'alerts@docforge.com',
            'to_emails': ['admin@docforge.com']
        }
    }
}

initialize_performance_system(config)
```

## Metrics Collection

### Recording Metrics

```python
from src.utils.performance_metrics import record_metric, increment_counter, record_gauge

# Record a metric value
record_metric('document.processing_time', 2.5, {'document_type': 'pdf'})

# Increment a counter
increment_counter('documents.processed', {'status': 'success'})

# Record a gauge value
record_gauge('queue.size', 42)
```

### Performance Monitoring Decorator

```python
from src.utils.performance_metrics import monitor_performance

@monitor_performance('document_processing')
def process_document(document):
    # Processing logic here
    return processed_document

# Async functions are also supported
@monitor_performance('async_operation')
async def async_process(data):
    # Async processing logic
    return result
```

### Context Manager for Timing

```python
from src.utils.performance_metrics import measure_time

with measure_time('database_query', {'query_type': 'select'}):
    results = execute_query(sql)
```

## Database Optimization

### Optimized Engine Creation

```python
from src.utils.database_optimization import create_optimized_engine

# Create optimized SQLAlchemy engine
engine = create_optimized_engine(
    database_url="postgresql://user:pass@localhost/db",
    pool_size=20,
    max_overflow=40,
    pool_timeout=60
)
```

### Query Monitoring

```python
from src.utils.database_optimization import monitor_db_operation

@monitor_db_operation('user_lookup')
def get_user_by_id(user_id):
    return session.query(User).filter(User.id == user_id).first()
```

### Query Caching

```python
from src.utils.database_optimization import cache_query_result, get_cached_result

# Cache query result
query = "SELECT * FROM users WHERE active = true"
result = execute_query(query)
cache_query_result(query, result, ttl=300)

# Retrieve from cache
cached_result = get_cached_result(query)
if cached_result is not None:
    return cached_result
```

## Caching Strategies

### Memory Cache

```python
from src.utils.caching_strategies import MemoryCache

cache = MemoryCache(max_size=1000, default_ttl=3600)

# Set and get values
cache.set('key', 'value', ttl=1800)
value = cache.get('key')
```

### Redis Cache

```python
from src.utils.caching_strategies import RedisCache

cache = RedisCache(redis_url='redis://localhost:6379/0')

cache.set('key', {'data': 'complex_object'})
value = cache.get('key')
```

### Multi-level Cache

```python
from src.utils.caching_strategies import setup_multilevel_cache

# Setup L1 (memory) + L2 (Redis) cache
setup_multilevel_cache('multilevel', l1_max_size=1000, redis_url='redis://localhost:6379/0')
```

### Caching Decorator

```python
from src.utils.caching_strategies import cached

@cached(ttl=3600, cache_name='multilevel')
def expensive_computation(param1, param2):
    # Expensive computation here
    return result

# First call executes function
result1 = expensive_computation('a', 'b')

# Second call returns cached result
result2 = expensive_computation('a', 'b')  # From cache
```

## Performance Benchmarking

### Creating Benchmarks

```python
from src.utils.performance_benchmarks import create_benchmark_suite

suite = create_benchmark_suite('document_processing')

@suite.benchmark('pdf_processing')
def benchmark_pdf_processing():
    # Simulate PDF processing
    process_pdf_document(sample_pdf)

@suite.benchmark('text_extraction')
def benchmark_text_extraction():
    # Simulate text extraction
    extract_text_from_document(sample_doc)
```

### Running Benchmarks

```python
# Run single benchmark
result = suite.run_benchmark('pdf_processing', iterations=100)
print(f"Mean time: {result.mean_time:.3f}s")
print(f"Throughput: {result.throughput:.2f} ops/sec")

# Run all benchmarks
results = suite.run_all_benchmarks(iterations=50)
```

### Load Testing

```python
from src.utils.performance_benchmarks import LoadTester

load_tester = LoadTester(max_workers=10)

def api_endpoint():
    # Simulate API call
    return make_api_request()

results = load_tester.run_load_test(
    api_endpoint,
    concurrent_users=20,
    duration_seconds=60,
    ramp_up_seconds=10
)

print(f"Throughput: {results['throughput']:.2f} req/s")
print(f"Error rate: {results['error_rate']:.2%}")
```

### Regression Testing

```python
# Set baseline
suite.set_baseline('pdf_processing')

# Run new benchmark
new_result = suite.run_benchmark('pdf_processing', iterations=100)

# Compare with baseline
comparison = suite.compare_with_baseline('pdf_processing', new_result)

if comparison.is_regression:
    print(f"Performance regression detected!")
    print(f"Mean time increased by {comparison.mean_time_change:.1%}")
```

## Monitoring and Alerting

### Dashboard Data

```python
from src.utils.performance_dashboard import get_dashboard_data, get_performance_summary

# Get comprehensive dashboard data
dashboard_data = get_dashboard_data()

# Get quick performance summary
summary = get_performance_summary()
print(f"Health score: {summary['health_score']}")
print(f"Status: {summary['status']}")
```

### Custom Alert Rules

```python
from src.utils.performance_dashboard import AlertRule, add_alert_rule

# Create custom alert rule
rule = AlertRule(
    name='high_document_processing_time',
    metric_name='document.processing_time',
    condition='gt',
    threshold=30.0,  # 30 seconds
    severity='warning',
    duration_seconds=120  # Alert if condition persists for 2 minutes
)

add_alert_rule(rule)
```

### Email Notifications

```python
from src.utils.performance_dashboard import configure_email_alerts

configure_email_alerts(
    smtp_host='smtp.gmail.com',
    smtp_port=587,
    from_email='alerts@docforge.com',
    to_emails=['admin@docforge.com', 'ops@docforge.com'],
    username='alerts@docforge.com',
    password='app_password',
    use_tls=True
)
```

### Webhook Notifications

```python
from src.utils.performance_dashboard import configure_webhook_alerts

configure_webhook_alerts('https://hooks.slack.com/services/YOUR/WEBHOOK/URL')
```

## Integration with DocForge Components

### Document Processing Monitoring

```python
from src.utils.performance_integration import monitor_docforge_operation

@monitor_docforge_operation('pdf_processing')
def process_pdf_document(document_path):
    # PDF processing logic
    return processed_document

@monitor_docforge_operation('text_extraction')
def extract_text(document):
    # Text extraction logic
    return extracted_text
```

### Caching Document Operations

```python
from src.utils.performance_integration import cached_docforge_operation

@cached_docforge_operation(ttl=1800, cache_name='multilevel')
def get_document_metadata(document_id):
    # Expensive metadata retrieval
    return metadata

@cached_docforge_operation(ttl=3600)
def search_documents(query, filters):
    # Expensive search operation
    return search_results
```

### RAG System Optimization

```python
# Cache embedding computations
@cached_docforge_operation(ttl=7200, cache_name='multilevel')
def compute_embeddings(text_chunks):
    return embedding_model.encode(text_chunks)

# Monitor RAG query performance
@monitor_docforge_operation('rag_query')
def execute_rag_query(query, context):
    return rag_system.query(query, context)
```

## Performance Metrics

### System Metrics

The system automatically collects:

- **CPU Usage**: System and process CPU utilization
- **Memory Usage**: System and process memory consumption
- **Disk Usage**: Disk space utilization
- **Network I/O**: Network traffic metrics
- **Process Metrics**: Thread count, file descriptors

### Application Metrics

- **Execution Times**: Function and operation execution times
- **Throughput**: Operations per second
- **Error Rates**: Success/failure ratios
- **Queue Sizes**: Processing queue lengths
- **Cache Hit Rates**: Cache effectiveness metrics

### Database Metrics

- **Query Performance**: Execution times, slow queries
- **Connection Pool**: Pool utilization, connection counts
- **Cache Statistics**: Query cache hit rates
- **Transaction Metrics**: Transaction success/failure rates

## Performance Optimization Strategies

### 1. Database Optimization

```python
# Use connection pooling
engine = create_optimized_engine(
    database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)

# Enable query caching for read-heavy operations
@cached_docforge_operation(ttl=600)
def get_user_preferences(user_id):
    return db.query(UserPreferences).filter_by(user_id=user_id).first()
```

### 2. Caching Strategy

```python
# Use multi-level caching for frequently accessed data
@cached_docforge_operation(ttl=3600, cache_name='multilevel')
def get_document_content(document_id):
    return expensive_document_retrieval(document_id)

# Cache computation results
@cached_docforge_operation(ttl=7200)
def compute_document_similarity(doc1_id, doc2_id):
    return similarity_algorithm(doc1_id, doc2_id)
```

### 3. Asynchronous Processing

```python
import asyncio
from src.utils.performance_metrics import monitor_performance

@monitor_performance('async_document_processing')
async def process_documents_async(document_ids):
    tasks = [process_single_document(doc_id) for doc_id in document_ids]
    return await asyncio.gather(*tasks)
```

### 4. Batch Processing

```python
@monitor_docforge_operation('batch_embedding')
def compute_embeddings_batch(text_list, batch_size=32):
    results = []
    for i in range(0, len(text_list), batch_size):
        batch = text_list[i:i + batch_size]
        batch_embeddings = embedding_model.encode(batch)
        results.extend(batch_embeddings)
    return results
```

## Monitoring Best Practices

### 1. Set Appropriate Thresholds

```python
# Configure alert thresholds based on your SLA
alert_rules = [
    {
        'name': 'document_processing_sla',
        'metric_name': 'document.processing_time',
        'condition': 'gt',
        'threshold': 60.0,  # 1 minute SLA
        'severity': 'warning'
    },
    {
        'name': 'system_overload',
        'metric_name': 'system.cpu.percent',
        'condition': 'gt',
        'threshold': 85.0,
        'severity': 'critical'
    }
]
```

### 2. Monitor Key Business Metrics

```python
# Track business-relevant metrics
record_metric('documents.processed_per_hour', hourly_count)
record_metric('user.query_response_time', response_time)
record_metric('system.availability_percent', uptime_percentage)
```

### 3. Use Performance Budgets

```python
# Set performance budgets for critical operations
@monitor_performance('critical_operation')
def critical_business_operation():
    start_time = time.time()
    
    try:
        result = perform_operation()
        
        # Check performance budget
        execution_time = time.time() - start_time
        if execution_time > 5.0:  # 5-second budget
            logger.warning(f"Performance budget exceeded: {execution_time:.2f}s")
        
        return result
    except Exception as e:
        logger.error(f"Critical operation failed: {e}")
        raise
```

## Troubleshooting

### High CPU Usage

1. Check system metrics in dashboard
2. Identify CPU-intensive operations
3. Optimize algorithms or add caching
4. Consider horizontal scaling

### Memory Leaks

1. Monitor process memory usage
2. Check cache sizes and TTL settings
3. Review object lifecycle management
4. Use memory profiling tools

### Slow Database Queries

1. Review slow query logs
2. Add database indexes
3. Optimize query patterns
4. Enable query caching

### Cache Inefficiency

1. Check cache hit rates
2. Adjust TTL values
3. Review cache key strategies
4. Consider cache warming

## API Reference

### Performance Integration

```python
from src.utils.performance_integration import (
    initialize_performance_system,
    get_performance_status,
    optimize_performance,
    run_performance_benchmarks
)

# Initialize system
initialize_performance_system(config)

# Get system status
status = get_performance_status()

# Run optimizations
optimization_results = optimize_performance()

# Run benchmarks
benchmark_results = run_performance_benchmarks()
```

### Metrics Collection

```python
from src.utils.performance_metrics import (
    record_metric,
    increment_counter,
    record_gauge,
    monitor_performance,
    measure_time
)
```

### Caching

```python
from src.utils.caching_strategies import (
    cached,
    setup_multilevel_cache,
    get_cache_stats,
    clear_all_caches
)
```

### Database Optimization

```python
from src.utils.database_optimization import (
    create_optimized_engine,
    monitor_db_operation,
    get_database_stats,
    get_slow_queries
)
```

### Benchmarking

```python
from src.utils.performance_benchmarks import (
    create_benchmark_suite,
    benchmark,
    run_benchmarks
)
```

### Dashboard and Alerting

```python
from src.utils.performance_dashboard import (
    get_dashboard_data,
    get_performance_summary,
    get_active_alerts,
    add_alert_rule,
    configure_email_alerts,
    configure_webhook_alerts
)
```

## Configuration Examples

### Production Configuration

```yaml
# config/production.yaml
performance:
  database:
    slow_query_threshold: 1.0
    query_cache_enabled: true
    query_cache_size: 5000
    query_cache_ttl: 600
  
  caching:
    redis_url: "redis://redis-cluster:6379/0"
    multilevel:
      enabled: true
      l1_max_size: 2000
    strategies:
      document_processing:
        cache_name: "multilevel"
        ttl: 1800
      rag_queries:
        cache_name: "multilevel"
        ttl: 3600
  
  monitoring:
    interval_seconds: 15
    email_alerts:
      enabled: true
      smtp_host: "smtp.company.com"
      smtp_port: 587
      from_email: "docforge-alerts@company.com"
      to_emails: ["ops-team@company.com"]
    
    alert_rules:
      - name: "document_processing_slow"
        metric_name: "document.processing_time"
        condition: "gt"
        threshold: 30.0
        severity: "warning"
        duration_seconds: 120
      
      - name: "high_error_rate"
        metric_name: "application.error_rate"
        condition: "gt"
        threshold: 0.05
        severity: "critical"
        duration_seconds: 60
```

This comprehensive performance monitoring and optimization system provides the foundation for maintaining high-performance DocForge operations with proactive monitoring, intelligent caching, and automated optimization.