"""
Comprehensive logging system for DocForge Brain MVP.

This module provides structured logging for all pipeline components including:
- Document processing activities
- Post-processing operations
- RAG preparation metrics
- Performance tracking
- Error logging and debugging
- Prompt history logging
"""

import logging
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import threading
from contextlib import contextmanager

# Configure structured logging
import structlog


class LogLevel(str, Enum):
    """Log levels for the system."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for different system components."""
    SYSTEM = "system"
    PREPROCESSING = "preprocessing"
    POSTPROCESSING = "postprocessing"
    STORAGE = "storage"
    RAG = "rag"
    VERSIONING = "versioning"
    API = "api"
    AUTHENTICATION = "auth"
    PERFORMANCE = "performance"
    ERROR = "error"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    category: str
    component: str
    message: str
    details: Dict[str, Any]
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    version_id: Optional[str] = None
    session_id: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None


class DocForgeLogger:
    """Comprehensive logging system for DocForge Brain MVP."""
    
    def __init__(self, log_dir: str = "logs", enable_console: bool = True):
        """Initialize the logging system."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enable_console = enable_console
        
        # Thread-local storage for context
        self._local = threading.local()
        
        # Initialize structured logging
        self._setup_structured_logging()
        
        # Create specialized loggers
        self._setup_component_loggers()
        
        # Initialize log files
        self._setup_log_files()
    
    def _setup_structured_logging(self):
        """Set up structured logging with structlog."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout if self.enable_console else None,
            level=logging.INFO,
        )
    
    def _setup_component_loggers(self):
        """Set up specialized loggers for different components."""
        self.loggers = {}
        
        for category in LogCategory:
            logger = structlog.get_logger(category.value)
            self.loggers[category.value] = logger
    
    def _setup_log_files(self):
        """Set up log files for different categories."""
        self.log_files = {}
        
        # Main application log
        self.log_files['main'] = self.log_dir / "docforge_main.log"
        
        # Component-specific logs
        for category in LogCategory:
            filename = f"docforge_{category.value}.log"
            self.log_files[category.value] = self.log_dir / filename
        
        # Special logs
        self.log_files['performance'] = self.log_dir / "docforge_performance.log"
        self.log_files['errors'] = self.log_dir / "docforge_errors.log"
        self.log_files['audit'] = self.log_dir / "docforge_audit.log"
        self.log_files['prompt_history'] = self.log_dir / "prompt_history.txt"
    
    def set_context(self, **kwargs):
        """Set logging context for current thread."""
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        
        self._local.context.update(kwargs)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current logging context."""
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        return self._local.context.copy()
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary logging context."""
        old_context = self.get_context()
        self.set_context(**kwargs)
        try:
            yield
        finally:
            self._local.context = old_context
    
    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        component: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log a structured message."""
        # Get current context
        context = self.get_context()
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=category.value,
            component=component,
            message=message,
            details=details or {},
            trace_id=context.get('trace_id'),
            user_id=context.get('user_id'),
            document_id=context.get('document_id'),
            version_id=context.get('version_id'),
            session_id=context.get('session_id'),
            performance_metrics=kwargs.get('performance_metrics'),
            error_info=kwargs.get('error_info')
        )
        
        # Log to structured logger
        logger = self.loggers.get(category.value, self.loggers['system'])
        log_method = getattr(logger, level.value.lower())
        
        log_method(
            message,
            **asdict(log_entry)
        )
        
        # Write to specific log files
        self._write_to_file(log_entry)
    
    def _write_to_file(self, log_entry: LogEntry):
        """Write log entry to appropriate files."""
        log_line = json.dumps(asdict(log_entry)) + "\n"
        
        # Write to main log
        with open(self.log_files['main'], 'a') as f:
            f.write(log_line)
        
        # Write to category-specific log
        category_file = self.log_files.get(log_entry.category)
        if category_file:
            with open(category_file, 'a') as f:
                f.write(log_line)
        
        # Write to special logs
        if log_entry.level in ['ERROR', 'CRITICAL']:
            with open(self.log_files['errors'], 'a') as f:
                f.write(log_line)
        
        if log_entry.performance_metrics:
            with open(self.log_files['performance'], 'a') as f:
                f.write(log_line)
        
        if log_entry.category == 'audit':
            with open(self.log_files['audit'], 'a') as f:
                f.write(log_line)
    
    # Convenience methods for different log levels
    def debug(self, category: LogCategory, component: str, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, category, component, message, **kwargs)
    
    def info(self, category: LogCategory, component: str, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, category, component, message, **kwargs)
    
    def warning(self, category: LogCategory, component: str, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, category, component, message, **kwargs)
    
    def error(self, category: LogCategory, component: str, message: str, **kwargs):
        """Log error message."""
        # Add exception info if available
        if 'exception' in kwargs:
            exc = kwargs.pop('exception')
            kwargs['error_info'] = {
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'traceback': traceback.format_exc()
            }
        
        self.log(LogLevel.ERROR, category, component, message, **kwargs)
    
    def critical(self, category: LogCategory, component: str, message: str, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, category, component, message, **kwargs)
    
    # Specialized logging methods
    def log_document_processing(
        self,
        document_id: str,
        stage: str,
        status: str,
        details: Dict[str, Any],
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log document processing activity."""
        with self.context(document_id=document_id):
            self.info(
                LogCategory.PREPROCESSING,
                f"processor_{stage}",
                f"Document processing {status}: {stage}",
                details=details,
                performance_metrics=performance_metrics
            )
    
    def log_postprocessing_activity(
        self,
        document_id: str,
        method: str,
        status: str,
        details: Dict[str, Any],
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log post-processing activity."""
        with self.context(document_id=document_id):
            self.info(
                LogCategory.POSTPROCESSING,
                f"postprocessor_{method}",
                f"Post-processing {status}: {method}",
                details=details,
                performance_metrics=performance_metrics
            )
    
    def log_rag_activity(
        self,
        document_id: str,
        operation: str,
        status: str,
        details: Dict[str, Any],
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log RAG preparation activity."""
        with self.context(document_id=document_id):
            self.info(
                LogCategory.RAG,
                f"rag_{operation}",
                f"RAG {status}: {operation}",
                details=details,
                performance_metrics=performance_metrics
            )
    
    def log_api_request(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str],
        status_code: int,
        response_time: float,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log API request."""
        with self.context(user_id=user_id):
            self.info(
                LogCategory.API,
                "api_request",
                f"{method} {endpoint} - {status_code}",
                details=details or {},
                performance_metrics={
                    'response_time_ms': response_time * 1000,
                    'status_code': status_code
                }
            )
    
    def log_authentication_event(
        self,
        event_type: str,
        user_id: Optional[str],
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication event."""
        with self.context(user_id=user_id):
            level = LogLevel.INFO if success else LogLevel.WARNING
            self.log(
                level,
                LogCategory.AUTHENTICATION,
                "auth_event",
                f"Authentication {event_type}: {'success' if success else 'failed'}",
                details=details or {}
            )
    
    def log_performance_metrics(
        self,
        component: str,
        operation: str,
        metrics: Dict[str, Any]
    ):
        """Log performance metrics."""
        self.info(
            LogCategory.PERFORMANCE,
            component,
            f"Performance metrics for {operation}",
            details={'operation': operation},
            performance_metrics=metrics
        )
    
    def log_error_with_context(
        self,
        category: LogCategory,
        component: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log error with full context and traceback."""
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        self.error(
            category,
            component,
            f"Error in {component}: {str(error)}",
            details=error_details
        )
    
    def log_prompt_history(self, prompt: str, response: str, metadata: Dict[str, Any]):
        """Log prompt history to text file."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        prompt_entry = f"""
=== PROMPT HISTORY ENTRY ===
Timestamp: {timestamp}
Metadata: {json.dumps(metadata, indent=2)}

PROMPT:
{prompt}

RESPONSE:
{response}

=== END ENTRY ===

"""
        
        with open(self.log_files['prompt_history'], 'a', encoding='utf-8') as f:
            f.write(prompt_entry)
    
    def get_log_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get log summary for the last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        summary = {
            'time_range': f'Last {hours} hours',
            'cutoff_time': cutoff_time.isoformat(),
            'categories': {},
            'error_count': 0,
            'warning_count': 0,
            'total_entries': 0
        }
        
        # Read and analyze main log file
        try:
            with open(self.log_files['main'], 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        
                        if entry_time >= cutoff_time:
                            summary['total_entries'] += 1
                            
                            category = entry.get('category', 'unknown')
                            if category not in summary['categories']:
                                summary['categories'][category] = 0
                            summary['categories'][category] += 1
                            
                            if entry.get('level') == 'ERROR':
                                summary['error_count'] += 1
                            elif entry.get('level') == 'WARNING':
                                summary['warning_count'] += 1
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except FileNotFoundError:
            pass
        
        return summary
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days."""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for log_file in self.log_files.values():
            if log_file.exists():
                # Create backup of old logs
                backup_file = log_file.with_suffix(f'.{cutoff_time.strftime("%Y%m%d")}.bak')
                
                # Read and filter log entries
                recent_entries = []
                
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                                
                                if entry_time >= cutoff_time:
                                    recent_entries.append(line)
                            
                            except (json.JSONDecodeError, KeyError, ValueError):
                                # Keep malformed entries
                                recent_entries.append(line)
                    
                    # Write recent entries back to log file
                    with open(log_file, 'w') as f:
                        f.writelines(recent_entries)
                
                except FileNotFoundError:
                    pass


# Global logger instance
_logger_instance = None


def get_logger() -> DocForgeLogger:
    """Get global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DocForgeLogger()
    return _logger_instance


def setup_logging(log_dir: str = "logs", enable_console: bool = True) -> DocForgeLogger:
    """Set up global logging system."""
    global _logger_instance
    _logger_instance = DocForgeLogger(log_dir, enable_console)
    return _logger_instance


# Convenience functions
def log_info(category: LogCategory, component: str, message: str, **kwargs):
    """Log info message using global logger."""
    get_logger().info(category, component, message, **kwargs)


def log_error(category: LogCategory, component: str, message: str, **kwargs):
    """Log error message using global logger."""
    get_logger().error(category, component, message, **kwargs)


def log_performance(component: str, operation: str, metrics: Dict[str, Any]):
    """Log performance metrics using global logger."""
    get_logger().log_performance_metrics(component, operation, metrics)


# Decorator for automatic performance logging
def log_performance_decorator(category: LogCategory, component: str):
    """Decorator to automatically log function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                get_logger().log_performance_metrics(
                    component,
                    func.__name__,
                    {
                        'duration_seconds': duration,
                        'success': True,
                        'function': func.__name__
                    }
                )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                
                get_logger().log_performance_metrics(
                    component,
                    func.__name__,
                    {
                        'duration_seconds': duration,
                        'success': False,
                        'error': str(e),
                        'function': func.__name__
                    }
                )
                
                get_logger().log_error_with_context(
                    category,
                    component,
                    e,
                    {'function': func.__name__, 'args': str(args)[:200]}
                )
                
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the logging system
    logger = setup_logging()
    
    # Test different log types
    logger.info(LogCategory.SYSTEM, "test", "System startup")
    logger.log_document_processing("doc123", "preprocessing", "started", {"file": "test.pdf"})
    logger.log_api_request("POST", "/api/v1/documents/upload", "user123", 200, 0.5)
    
    print("Logging system test completed. Check logs/ directory for output.")