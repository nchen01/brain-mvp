"""
Logging integration for existing DocForge components.

This module provides logging integration for all existing components
without requiring major refactoring of existing code.
"""

import functools
import time
from typing import Any, Dict, Optional
from contextlib import contextmanager

from .logging_system import get_logger, LogCategory, LogLevel


class ComponentLogger:
    """Component-specific logger wrapper."""
    
    def __init__(self, category: LogCategory, component: str):
        self.category = category
        self.component = component
        self.logger = get_logger()
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self.category, self.component, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self.category, self.component, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self.category, self.component, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self.category, self.component, message, **kwargs)
    
    @contextmanager
    def context(self, **kwargs):
        """Set logging context."""
        with self.logger.context(**kwargs):
            yield
    
    def log_performance(self, operation: str, metrics: Dict[str, Any]):
        """Log performance metrics."""
        self.logger.log_performance_metrics(self.component, operation, metrics)


# Component loggers for existing modules
preprocessing_logger = ComponentLogger(LogCategory.PREPROCESSING, "preprocessing")
postprocessing_logger = ComponentLogger(LogCategory.POSTPROCESSING, "postprocessing")
storage_logger = ComponentLogger(LogCategory.STORAGE, "storage")
rag_logger = ComponentLogger(LogCategory.RAG, "rag")
versioning_logger = ComponentLogger(LogCategory.VERSIONING, "versioning")
api_logger = ComponentLogger(LogCategory.API, "api")
auth_logger = ComponentLogger(LogCategory.AUTHENTICATION, "auth")
system_logger = ComponentLogger(LogCategory.SYSTEM, "system")


def log_function_call(category: LogCategory, component: str = None):
    """Decorator to log function calls with performance metrics."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            comp_name = component or func.__module__.split('.')[-1]
            logger = ComponentLogger(category, comp_name)
            
            start_time = time.time()
            
            # Log function start
            logger.debug(f"Starting {func.__name__}", details={
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys())
            })
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log successful completion
                logger.info(f"Completed {func.__name__}", details={
                    'function': func.__name__,
                    'success': True,
                    'duration_seconds': duration
                })
                
                # Log performance metrics
                logger.log_performance(func.__name__, {
                    'duration_seconds': duration,
                    'success': True,
                    'function': func.__name__
                })
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                logger.error(f"Failed {func.__name__}: {str(e)}", details={
                    'function': func.__name__,
                    'success': False,
                    'duration_seconds': duration,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })
                
                # Log performance metrics for failed operation
                logger.log_performance(func.__name__, {
                    'duration_seconds': duration,
                    'success': False,
                    'error': str(e),
                    'function': func.__name__
                })
                
                raise
        
        return wrapper
    return decorator


def log_document_processing(func):
    """Decorator specifically for document processing functions."""
    return log_function_call(LogCategory.PREPROCESSING, "document_processor")(func)


def log_postprocessing(func):
    """Decorator specifically for post-processing functions."""
    return log_function_call(LogCategory.POSTPROCESSING, "postprocessor")(func)


def log_storage_operation(func):
    """Decorator specifically for storage operations."""
    return log_function_call(LogCategory.STORAGE, "storage")(func)


def log_rag_operation(func):
    """Decorator specifically for RAG operations."""
    return log_function_call(LogCategory.RAG, "rag")(func)


def log_versioning_operation(func):
    """Decorator specifically for versioning operations."""
    return log_function_call(LogCategory.VERSIONING, "versioning")(func)


def log_api_endpoint(func):
    """Decorator specifically for API endpoints."""
    return log_function_call(LogCategory.API, "api_endpoint")(func)


# Context managers for operation tracking
@contextmanager
def document_processing_context(document_id: str, operation: str):
    """Context manager for document processing operations."""
    logger = get_logger()
    
    with logger.context(document_id=document_id):
        start_time = time.time()
        
        logger.log_document_processing(
            document_id, operation, "started", 
            {"operation": operation}
        )
        
        try:
            yield
            duration = time.time() - start_time
            
            logger.log_document_processing(
                document_id, operation, "completed",
                {"operation": operation, "duration_seconds": duration},
                performance_metrics={"duration_seconds": duration, "success": True}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.log_document_processing(
                document_id, operation, "failed",
                {
                    "operation": operation, 
                    "duration_seconds": duration,
                    "error": str(e)
                },
                performance_metrics={
                    "duration_seconds": duration, 
                    "success": False,
                    "error": str(e)
                }
            )
            raise


@contextmanager
def postprocessing_context(document_id: str, method: str):
    """Context manager for post-processing operations."""
    logger = get_logger()
    
    with logger.context(document_id=document_id):
        start_time = time.time()
        
        logger.log_postprocessing_activity(
            document_id, method, "started",
            {"method": method}
        )
        
        try:
            yield
            duration = time.time() - start_time
            
            logger.log_postprocessing_activity(
                document_id, method, "completed",
                {"method": method, "duration_seconds": duration},
                performance_metrics={"duration_seconds": duration, "success": True}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.log_postprocessing_activity(
                document_id, method, "failed",
                {
                    "method": method,
                    "duration_seconds": duration,
                    "error": str(e)
                },
                performance_metrics={
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(e)
                }
            )
            raise


@contextmanager
def rag_operation_context(document_id: str, operation: str):
    """Context manager for RAG operations."""
    logger = get_logger()
    
    with logger.context(document_id=document_id):
        start_time = time.time()
        
        logger.log_rag_activity(
            document_id, operation, "started",
            {"operation": operation}
        )
        
        try:
            yield
            duration = time.time() - start_time
            
            logger.log_rag_activity(
                document_id, operation, "completed",
                {"operation": operation, "duration_seconds": duration},
                performance_metrics={"duration_seconds": duration, "success": True}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.log_rag_activity(
                document_id, operation, "failed",
                {
                    "operation": operation,
                    "duration_seconds": duration,
                    "error": str(e)
                },
                performance_metrics={
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(e)
                }
            )
            raise


# API request logging middleware
class APILoggingMiddleware:
    """Middleware for logging API requests."""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Extract request info
            method = scope["method"]
            path = scope["path"]
            
            # Get user info from headers if available
            user_id = None
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization")
            if auth_header:
                # Extract user from JWT token (simplified)
                user_id = "authenticated_user"  # Would extract from actual token
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    response_time = time.time() - start_time
                    
                    # Log API request
                    self.logger.log_api_request(
                        method, path, user_id, status_code, response_time,
                        details={
                            "path": path,
                            "method": method,
                            "user_agent": headers.get(b"user-agent", b"").decode(),
                            "content_length": headers.get(b"content-length", b"0").decode()
                        }
                    )
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Utility functions for manual logging
def log_system_startup():
    """Log system startup."""
    system_logger.info("DocForge Brain MVP system starting up", details={
        "timestamp": time.time(),
        "version": "1.0.0"
    })


def log_system_shutdown():
    """Log system shutdown."""
    system_logger.info("DocForge Brain MVP system shutting down", details={
        "timestamp": time.time()
    })


def log_configuration_loaded(config_data: Dict[str, Any]):
    """Log configuration loading."""
    system_logger.info("Configuration loaded", details={
        "config_keys": list(config_data.keys()),
        "config_count": len(config_data)
    })


def log_database_connection(database_type: str, status: str):
    """Log database connection events."""
    storage_logger.info(f"Database connection {status}: {database_type}", details={
        "database_type": database_type,
        "status": status
    })


def log_user_action(user_id: str, action: str, details: Dict[str, Any]):
    """Log user actions for audit trail."""
    logger = get_logger()
    
    with logger.context(user_id=user_id):
        logger.log(
            LogLevel.INFO,
            LogCategory.AUDIT,
            "user_action",
            f"User action: {action}",
            details=details
        )


def log_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Log security events."""
    level = LogLevel.WARNING if severity == "medium" else LogLevel.CRITICAL
    
    system_logger.logger.log(
        level,
        LogCategory.AUDIT,
        "security_event",
        f"Security event: {event_type}",
        details={**details, "severity": severity}
    )


# Performance monitoring helpers
def track_memory_usage(operation: str):
    """Track memory usage for an operation."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        system_logger.log_performance("memory_monitor", {
            "operation": operation,
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "memory_percent": process.memory_percent()
        })
    except ImportError:
        # psutil not available
        pass


def track_cpu_usage(operation: str):
    """Track CPU usage for an operation."""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        
        system_logger.log_performance("cpu_monitor", {
            "operation": operation,
            "cpu_percent": cpu_percent
        })
    except ImportError:
        # psutil not available
        pass