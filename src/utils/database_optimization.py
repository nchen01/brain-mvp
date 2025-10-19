"""Database optimization utilities including connection pooling and query optimization."""

import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
import hashlib
import json

try:
    import sqlalchemy
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    sqlalchemy = None
    Engine = None
    QueuePool = None
    StaticPool = None
    SQLALCHEMY_AVAILABLE = False

from .performance_metrics import metrics_collector, monitor_performance

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for database queries."""
    query_hash: str
    query_template: str
    execution_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_execution: Optional[datetime] = None
    error_count: int = 0
    
    def update(self, execution_time: float, error: bool = False):
        """Update query statistics."""
        self.execution_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.execution_count
        self.last_execution = datetime.now(timezone.utc)
        
        if error:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_hash': self.query_hash,
            'query_template': self.query_template,
            'execution_count': self.execution_count,
            'total_time': self.total_time,
            'min_time': self.min_time if self.min_time != float('inf') else 0.0,
            'max_time': self.max_time,
            'avg_time': self.avg_time,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'error_count': self.error_count,
            'error_rate': self.error_count / self.execution_count if self.execution_count > 0 else 0.0
        }


class DatabaseOptimizer:
    """Database optimization and monitoring system."""
    
    def __init__(self):
        """Initialize database optimizer."""
        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_query_threshold = 1.0  # seconds
        self.connection_pools: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Query cache
        self.query_cache_enabled = True
        self.query_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 1000
    
    def create_optimized_engine(self, 
                              database_url: str,
                              pool_size: int = 10,
                              max_overflow: int = 20,
                              pool_timeout: int = 30,
                              pool_recycle: int = 3600,
                              echo: bool = False) -> Optional[Engine]:
        """Create optimized SQLAlchemy engine with connection pooling."""
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available, cannot create optimized engine")
            return None
        
        try:
            # Configure connection pool based on database type
            if database_url.startswith('sqlite'):
                # SQLite specific optimizations
                engine = create_engine(
                    database_url,
                    poolclass=StaticPool,
                    connect_args={
                        'check_same_thread': False,
                        'timeout': 20,
                        'isolation_level': None  # Autocommit mode
                    },
                    echo=echo
                )
                
                # SQLite optimizations
                @event.listens_for(engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    # Performance optimizations
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA cache_size=10000")
                    cursor.execute("PRAGMA temp_store=MEMORY")
                    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
                    cursor.close()
            
            else:
                # PostgreSQL/MySQL optimizations
                engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                    pool_recycle=pool_recycle,
                    pool_pre_ping=True,  # Validate connections
                    echo=echo
                )
            
            # Add query monitoring
            self._setup_query_monitoring(engine)
            
            # Store engine for monitoring
            engine_id = hashlib.md5(database_url.encode()).hexdigest()[:8]
            self.connection_pools[engine_id] = {
                'engine': engine,
                'url': database_url,
                'created_at': datetime.now(timezone.utc)
            }
            
            logger.info(f"Created optimized database engine: {engine_id}")
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create optimized engine: {e}")
            return None
    
    def _setup_query_monitoring(self, engine: Engine):
        """Setup query monitoring for an engine."""
        if not SQLALCHEMY_AVAILABLE:
            return
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            execution_time = time.time() - context._query_start_time
            
            # Record query statistics
            self._record_query_stats(statement, execution_time, False)
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected ({execution_time:.3f}s): {statement[:200]}...")
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            if hasattr(exception_context, '_query_statement'):
                self._record_query_stats(exception_context._query_statement, 0.0, True)
    
    def _record_query_stats(self, statement: str, execution_time: float, error: bool):
        """Record query statistics."""
        with self._lock:
            # Create query template (remove parameters for grouping)
            query_template = self._normalize_query(statement)
            query_hash = hashlib.md5(query_template.encode()).hexdigest()
            
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = QueryStats(
                    query_hash=query_hash,
                    query_template=query_template
                )
            
            self.query_stats[query_hash].update(execution_time, error)
            
            # Record metrics
            metrics_collector.record_execution_time(f"db_query.{query_hash[:8]}", execution_time, error)
            metrics_collector.record_metric("database.query_count", 1.0, {
                'query_type': self._get_query_type(statement),
                'error': str(error)
            })
    
    def _normalize_query(self, statement: str) -> str:
        """Normalize query for grouping (remove parameters)."""
        # Simple normalization - replace numbers and strings with placeholders
        import re
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', statement.strip())
        
        # Replace string literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)
        
        # Replace numbers
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Replace UUIDs
        normalized = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '?', normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _get_query_type(self, statement: str) -> str:
        """Get query type from statement."""
        statement_upper = statement.strip().upper()
        
        if statement_upper.startswith('SELECT'):
            return 'SELECT'
        elif statement_upper.startswith('INSERT'):
            return 'INSERT'
        elif statement_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif statement_upper.startswith('DELETE'):
            return 'DELETE'
        elif statement_upper.startswith('CREATE'):
            return 'CREATE'
        elif statement_upper.startswith('DROP'):
            return 'DROP'
        elif statement_upper.startswith('ALTER'):
            return 'ALTER'
        else:
            return 'OTHER'
    
    @contextmanager
    def monitored_query(self, query_name: str):
        """Context manager for monitoring specific queries."""
        start_time = time.time()
        error = False
        
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            execution_time = time.time() - start_time
            metrics_collector.record_execution_time(f"db_query.{query_name}", execution_time, error)
    
    def get_query_stats(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get query statistics."""
        with self._lock:
            stats = [stat.to_dict() for stat in self.query_stats.values()]
            
            # Sort by total time
            stats.sort(key=lambda x: x['total_time'], reverse=True)
            
            if limit:
                stats = stats[:limit]
            
            return stats
    
    def get_slow_queries(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get slow queries above threshold."""
        threshold = threshold or self.slow_query_threshold
        
        with self._lock:
            slow_queries = []
            
            for stat in self.query_stats.values():
                if stat.avg_time > threshold:
                    slow_queries.append(stat.to_dict())
            
            # Sort by average time
            slow_queries.sort(key=lambda x: x['avg_time'], reverse=True)
            
            return slow_queries
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        pool_stats = {}
        
        for pool_id, pool_info in self.connection_pools.items():
            engine = pool_info['engine']
            
            if SQLALCHEMY_AVAILABLE and hasattr(engine, 'pool'):
                pool = engine.pool
                
                pool_stats[pool_id] = {
                    'url': pool_info['url'],
                    'created_at': pool_info['created_at'].isoformat(),
                    'size': getattr(pool, 'size', lambda: 0)(),
                    'checked_in': getattr(pool, 'checkedin', lambda: 0)(),
                    'checked_out': getattr(pool, 'checkedout', lambda: 0)(),
                    'overflow': getattr(pool, 'overflow', lambda: 0)(),
                    'invalid': getattr(pool, 'invalid', lambda: 0)()
                }
        
        return pool_stats
    
    def optimize_query_cache(self, query: str, result: Any, ttl: Optional[int] = None) -> str:
        """Cache query result."""
        if not self.query_cache_enabled:
            return ""
        
        cache_key = hashlib.md5(query.encode()).hexdigest()
        ttl = ttl or self.cache_ttl
        
        # Clean cache if too large
        if len(self.query_cache) >= self.max_cache_size:
            self._clean_cache()
        
        self.query_cache[cache_key] = {
            'result': result,
            'cached_at': time.time(),
            'ttl': ttl
        }
        
        return cache_key
    
    def get_cached_query_result(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        if not self.query_cache_enabled:
            return None
        
        cache_key = hashlib.md5(query.encode()).hexdigest()
        
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            
            # Check if cache is still valid
            if time.time() - cached_item['cached_at'] < cached_item['ttl']:
                metrics_collector.increment_counter("database.cache_hit")
                return cached_item['result']
            else:
                # Remove expired item
                del self.query_cache[cache_key]
        
        metrics_collector.increment_counter("database.cache_miss")
        return None
    
    def _clean_cache(self):
        """Clean expired cache entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, item in self.query_cache.items():
            if current_time - item['cached_at'] >= item['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.query_cache[key]
        
        # If still too large, remove oldest entries
        if len(self.query_cache) >= self.max_cache_size:
            sorted_items = sorted(
                self.query_cache.items(),
                key=lambda x: x[1]['cached_at']
            )
            
            # Remove oldest 20%
            remove_count = len(sorted_items) // 5
            for i in range(remove_count):
                del self.query_cache[sorted_items[i][0]]
    
    def clear_cache(self):
        """Clear query cache."""
        self.query_cache.clear()
        logger.info("Query cache cleared")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query_stats': {
                'total_queries': len(self.query_stats),
                'slow_queries_count': len(self.get_slow_queries()),
                'top_queries': self.get_query_stats(limit=10)
            },
            'connection_pools': self.get_connection_pool_stats(),
            'cache_stats': {
                'enabled': self.query_cache_enabled,
                'size': len(self.query_cache),
                'max_size': self.max_cache_size,
                'ttl': self.cache_ttl
            },
            'configuration': {
                'slow_query_threshold': self.slow_query_threshold
            }
        }
    
    def reset_stats(self):
        """Reset all statistics."""
        with self._lock:
            self.query_stats.clear()
            self.clear_cache()


# Global database optimizer instance
db_optimizer = DatabaseOptimizer()


# Decorator for database operations
def monitor_db_operation(operation_name: Optional[str] = None):
    """Decorator to monitor database operations."""
    return monitor_performance(
        operation_name=operation_name or "db_operation",
        record_args=True
    )


# Context manager for database transactions
@contextmanager
def monitored_transaction(connection, operation_name: str = "transaction"):
    """Context manager for monitoring database transactions."""
    start_time = time.time()
    error = False
    
    transaction = connection.begin()
    
    try:
        yield connection
        transaction.commit()
    except Exception:
        error = True
        transaction.rollback()
        raise
    finally:
        execution_time = time.time() - start_time
        metrics_collector.record_execution_time(f"db_transaction.{operation_name}", execution_time, error)


# Convenience functions
def create_optimized_engine(database_url: str, **kwargs) -> Optional[Engine]:
    """Create optimized database engine."""
    return db_optimizer.create_optimized_engine(database_url, **kwargs)


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    return db_optimizer.get_database_stats()


def get_slow_queries(threshold: Optional[float] = None) -> List[Dict[str, Any]]:
    """Get slow queries."""
    return db_optimizer.get_slow_queries(threshold)


def cache_query_result(query: str, result: Any, ttl: Optional[int] = None) -> str:
    """Cache query result."""
    return db_optimizer.optimize_query_cache(query, result, ttl)


def get_cached_result(query: str) -> Optional[Any]:
    """Get cached query result."""
    return db_optimizer.get_cached_query_result(query)