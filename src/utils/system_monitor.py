"""System monitoring utilities using psutil."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System monitoring and resource tracking."""
    
    def __init__(self):
        """Initialize system monitor."""
        self.psutil_available = PSUTIL_AVAILABLE
        if not self.psutil_available:
            logger.warning("psutil not available - system monitoring features will be limited")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        stats = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'psutil_available': self.psutil_available
        }
        
        if not self.psutil_available:
            stats['error'] = 'psutil not available'
            return stats
        
        try:
            # CPU information
            stats['cpu'] = {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'count_logical': psutil.cpu_count(logical=True)
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            stats['memory'] = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # Disk information
            disk = psutil.disk_usage('/')
            stats['disk'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
            
            # Process information
            process = psutil.Process()
            stats['process'] = {
                'pid': process.pid,
                'memory_info': process.memory_info()._asdict(),
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            }
            
        except Exception as e:
            logger.error(f"Error collecting system stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            
            return {
                'system_memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_percent': memory.percent
                },
                'process_memory': {
                    'rss_mb': round(process.memory_info().rss / (1024**2), 2),
                    'vms_mb': round(process.memory_info().vms / (1024**2), 2),
                    'percent': process.memory_percent()
                }
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {'error': str(e)}
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage information."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return {'error': str(e)}
    
    def check_resource_limits(
        self, 
        max_memory_percent: float = 80.0,
        max_cpu_percent: float = 80.0
    ) -> Dict[str, Any]:
        """Check if system resources are within acceptable limits."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            warnings = []
            if memory.percent > max_memory_percent:
                warnings.append(f"Memory usage ({memory.percent:.1f}%) exceeds limit ({max_memory_percent}%)")
            
            if cpu_percent > max_cpu_percent:
                warnings.append(f"CPU usage ({cpu_percent:.1f}%) exceeds limit ({max_cpu_percent}%)")
            
            return {
                'within_limits': len(warnings) == 0,
                'warnings': warnings,
                'current_memory_percent': memory.percent,
                'current_cpu_percent': cpu_percent,
                'limits': {
                    'max_memory_percent': max_memory_percent,
                    'max_cpu_percent': max_cpu_percent
                }
            }
        except Exception as e:
            logger.error(f"Error checking resource limits: {e}")
            return {'error': str(e)}


# Global system monitor instance
system_monitor = SystemMonitor()


def get_system_stats() -> Dict[str, Any]:
    """Get current system statistics."""
    return system_monitor.get_system_stats()


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage information."""
    return system_monitor.get_memory_usage()


def get_cpu_usage() -> Dict[str, Any]:
    """Get CPU usage information."""
    return system_monitor.get_cpu_usage()


def check_resource_limits(max_memory_percent: float = 80.0, max_cpu_percent: float = 80.0) -> Dict[str, Any]:
    """Check if system resources are within acceptable limits."""
    return system_monitor.check_resource_limits(max_memory_percent, max_cpu_percent)