"""Advanced caching strategies for performance optimization."""

import time
import threading
import hashlib
import pickle
import json
import logging
from typing import Any, Dict, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import OrderedDict
from abc import ABC, abstractmethod
import functools
import weakref

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from .performance_metrics import metrics_collector, monitor_performance

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Access cache entry and update metadata."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'created_at': self.created_at,
            'ttl': self.ttl,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed,
            'size_bytes': self.size_bytes,
            'is_expired': self.is_expired()
        }


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: float) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """Initialize memory cache."""
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.created_at = time.time()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if entry.is_expired():
                    del self._cache[key]
                    self.misses += 1
                    metrics_collector.increment_counter("cache.memory.miss", {"reason": "expired"})
                    return None
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self.hits += 1
                metrics_collector.increment_counter("cache.memory.hit")
                return entry.access()
            
            self.misses += 1
            metrics_collector.increment_counter("cache.memory.miss", {"reason": "not_found"})
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        with self._lock:
            try:
                # Calculate size
                size_bytes = len(pickle.dumps(value))
                
                # Create cache entry
                entry = CacheEntry(
                    value=value,
                    created_at=time.time(),
                    ttl=ttl,
                    size_bytes=size_bytes
                )
                
                # Remove existing entry if present
                if key in self._cache:
                    del self._cache[key]
                
                # Add new entry
                self._cache[key] = entry
                
                # Evict if necessary
                while len(self._cache) > self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    self.evictions += 1
                    metrics_collector.increment_counter("cache.memory.eviction")
                
                metrics_collector.increment_counter("cache.memory.set")
                metrics_collector.record_gauge("cache.memory.size", len(self._cache))
                return True
                
            except Exception as e:
                logger.error(f"Failed to set cache entry: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                metrics_collector.increment_counter("cache.memory.delete")
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            metrics_collector.increment_counter("cache.memory.clear")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                'backend': 'memory',
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions,
                'total_size_bytes': total_size,
                'uptime_seconds': time.time() - self.created_at
            }
    
    def cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)


class RedisCache(CacheBackend):
    """Redis-based cache backend."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", 
                 key_prefix: str = "docforge:", default_ttl: float = 3600):
        """Initialize Redis cache."""
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        
        try:
            self.client = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.created_at = time.time()
    
    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            redis_key = self._make_key(key)
            data = self.client.get(redis_key)
            
            if data is not None:
                self.hits += 1
                metrics_collector.increment_counter("cache.redis.hit")
                return pickle.loads(data)
            
            self.misses += 1
            metrics_collector.increment_counter("cache.redis.miss")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.misses += 1
            metrics_collector.increment_counter("cache.redis.error")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)
            
            result = self.client.setex(redis_key, int(ttl), data)
            
            if result:
                metrics_collector.increment_counter("cache.redis.set")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            metrics_collector.increment_counter("cache.redis.error")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            redis_key = self._make_key(key)
            result = self.client.delete(redis_key)
            
            if result:
                metrics_collector.increment_counter("cache.redis.delete")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            metrics_collector.increment_counter("cache.redis.error")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries with prefix."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.client.keys(pattern)
            
            if keys:
                self.client.delete(*keys)
            
            metrics_collector.increment_counter("cache.redis.clear")
            return True
            
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            metrics_collector.increment_counter("cache.redis.error")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = self.client.info()
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'backend': 'redis',
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'redis_info': {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                },
                'uptime_seconds': time.time() - self.created_at
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {
                'backend': 'redis',
                'error': str(e),
                'hits': self.hits,
                'misses': self.misses
            }


class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis) backends."""
    
    def __init__(self, 
                 l1_cache: CacheBackend,
                 l2_cache: Optional[CacheBackend] = None,
                 l1_ttl_ratio: float = 0.1):
        """Initialize multi-level cache."""
        self.l1_cache = l1_cache
        self.l2_cache = l2_cache
        self.l1_ttl_ratio = l1_ttl_ratio  # L1 TTL as ratio of L2 TTL
        
        # Statistics
        self.l1_hits = 0
        self.l2_hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)."""
        # Try L1 cache first
        value = self.l1_cache.get(key)
        if value is not None:
            self.l1_hits += 1
            metrics_collector.increment_counter("cache.multilevel.l1_hit")
            return value
        
        # Try L2 cache if available
        if self.l2_cache:
            value = self.l2_cache.get(key)
            if value is not None:
                self.l2_hits += 1
                metrics_collector.increment_counter("cache.multilevel.l2_hit")
                
                # Promote to L1 cache
                l1_ttl = 300  # 5 minutes default for L1
                self.l1_cache.set(key, value, l1_ttl)
                
                return value
        
        self.misses += 1
        metrics_collector.increment_counter("cache.multilevel.miss")
        return None
    
    def set(self, key: str, value: Any, ttl: float = 3600) -> bool:
        """Set value in both cache levels."""
        success = True
        
        # Set in L1 with shorter TTL
        l1_ttl = ttl * self.l1_ttl_ratio
        if not self.l1_cache.set(key, value, l1_ttl):
            success = False
        
        # Set in L2 with full TTL
        if self.l2_cache:
            if not self.l2_cache.set(key, value, ttl):
                success = False
        
        if success:
            metrics_collector.increment_counter("cache.multilevel.set")
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete from both cache levels."""
        l1_result = self.l1_cache.delete(key)
        l2_result = self.l2_cache.delete(key) if self.l2_cache else True
        
        return l1_result or l2_result
    
    def clear(self) -> bool:
        """Clear both cache levels."""
        l1_result = self.l1_cache.clear()
        l2_result = self.l2_cache.clear() if self.l2_cache else True
        
        return l1_result and l2_result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.l1_hits + self.l2_hits + self.misses
        
        stats = {
            'backend': 'multilevel',
            'l1_hits': self.l1_hits,
            'l2_hits': self.l2_hits,
            'misses': self.misses,
            'total_requests': total_requests,
            'l1_hit_rate': self.l1_hits / total_requests if total_requests > 0 else 0.0,
            'l2_hit_rate': self.l2_hits / total_requests if total_requests > 0 else 0.0,
            'overall_hit_rate': (self.l1_hits + self.l2_hits) / total_requests if total_requests > 0 else 0.0,
            'l1_stats': self.l1_cache.get_stats()
        }
        
        if self.l2_cache:
            stats['l2_stats'] = self.l2_cache.get_stats()
        
        return stats


class CacheManager:
    """Centralized cache management system."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.caches: Dict[str, CacheBackend] = {}
        self.default_cache_name = "default"
        
        # Create default memory cache
        self.caches[self.default_cache_name] = MemoryCache()
        
        # Cache strategies
        self.strategies: Dict[str, Dict[str, Any]] = {}
    
    def add_cache(self, name: str, cache: CacheBackend):
        """Add a named cache backend."""
        self.caches[name] = cache
        logger.info(f"Added cache backend: {name}")
    
    def get_cache(self, name: str = None) -> CacheBackend:
        """Get cache backend by name."""
        name = name or self.default_cache_name
        return self.caches.get(name, self.caches[self.default_cache_name])
    
    def create_redis_cache(self, name: str, redis_url: str, **kwargs) -> bool:
        """Create and add Redis cache."""
        try:
            cache = RedisCache(redis_url, **kwargs)
            self.add_cache(name, cache)
            return True
        except Exception as e:
            logger.error(f"Failed to create Redis cache {name}: {e}")
            return False
    
    def create_multilevel_cache(self, name: str, 
                              l1_max_size: int = 1000,
                              redis_url: Optional[str] = None) -> bool:
        """Create and add multi-level cache."""
        try:
            l1_cache = MemoryCache(max_size=l1_max_size)
            l2_cache = None
            
            if redis_url and REDIS_AVAILABLE:
                l2_cache = RedisCache(redis_url)
            
            cache = MultiLevelCache(l1_cache, l2_cache)
            self.add_cache(name, cache)
            return True
        except Exception as e:
            logger.error(f"Failed to create multi-level cache {name}: {e}")
            return False
    
    def add_strategy(self, name: str, cache_name: str, ttl: float, 
                    key_generator: Optional[Callable] = None):
        """Add caching strategy."""
        self.strategies[name] = {
            'cache_name': cache_name,
            'ttl': ttl,
            'key_generator': key_generator or self._default_key_generator
        }
    
    def _default_key_generator(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Default cache key generator."""
        key_parts = [func_name]
        
        # Add args
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add kwargs
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
            else:
                key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")
        
        return ":".join(key_parts)
    
    def cached(self, strategy: str = "default", ttl: Optional[float] = None, 
              cache_name: Optional[str] = None):
        """Decorator for caching function results."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Determine cache settings
                if strategy in self.strategies:
                    strategy_config = self.strategies[strategy]
                    cache = self.get_cache(strategy_config['cache_name'])
                    cache_ttl = ttl or strategy_config['ttl']
                    key_gen = strategy_config['key_generator']
                else:
                    cache = self.get_cache(cache_name)
                    cache_ttl = ttl or 3600
                    key_gen = self._default_key_generator
                
                # Generate cache key
                cache_key = key_gen(func.__name__, args, kwargs)
                
                # Try to get from cache
                result = cache.get(cache_key)
                if result is not None:
                    return result
                
                # Execute function and cache result
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    cache.set(cache_key, result, cache_ttl)
                    
                    execution_time = time.time() - start_time
                    metrics_collector.record_execution_time(f"cached_function.{func.__name__}", execution_time)
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    metrics_collector.record_execution_time(f"cached_function.{func.__name__}", execution_time, True)
                    raise
            
            return wrapper
        return decorator
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        stats = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'caches': {},
            'strategies': list(self.strategies.keys())
        }
        
        for name, cache in self.caches.items():
            stats['caches'][name] = cache.get_stats()
        
        return stats
    
    def clear_all_caches(self):
        """Clear all caches."""
        for name, cache in self.caches.items():
            cache.clear()
            logger.info(f"Cleared cache: {name}")


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
def cached(strategy: str = "default", ttl: Optional[float] = None, 
          cache_name: Optional[str] = None):
    """Decorator for caching function results."""
    return cache_manager.cached(strategy, ttl, cache_name)


def get_cache_stats() -> Dict[str, Any]:
    """Get all cache statistics."""
    return cache_manager.get_all_stats()


def clear_all_caches():
    """Clear all caches."""
    cache_manager.clear_all_caches()


def setup_redis_cache(name: str, redis_url: str) -> bool:
    """Setup Redis cache."""
    return cache_manager.create_redis_cache(name, redis_url)


def setup_multilevel_cache(name: str, l1_max_size: int = 1000, 
                          redis_url: Optional[str] = None) -> bool:
    """Setup multi-level cache."""
    return cache_manager.create_multilevel_cache(name, l1_max_size, redis_url)