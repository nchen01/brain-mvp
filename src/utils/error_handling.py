"""Comprehensive error handling and recovery framework."""

import logging
import time
import functools
import asyncio
import inspect
from typing import Dict, Any, Optional, Callable, Union, Type, List
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager
import traceback
import sys


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    DATABASE = "database"
    FILE_IO = "file_io"
    NETWORK = "network"
    PROCESSING = "processing"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM_RESOURCE = "system_resource"


@dataclass
class ErrorContext:
    """Context information for error tracking and debugging."""
    error_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    component: str = ""
    operation: str = ""
    category: ErrorCategory = ErrorCategory.PROCESSING
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary for logging."""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'operation': self.operation,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'stack_trace': self.stack_trace,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }


class RecoverableError(Exception):
    """Base class for recoverable errors that can be retried."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context or ErrorContext(
            error_id=f"recoverable_{int(time.time())}",
            message=message
        )


class NonRecoverableError(Exception):
    """Base class for non-recoverable errors that should not be retried."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context or ErrorContext(
            error_id=f"non_recoverable_{int(time.time())}",
            message=message,
            severity=ErrorSeverity.HIGH
        )


class CircuitBreakerError(Exception):
    """Error raised when circuit breaker is open."""
    pass


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker pattern."""
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    
    def should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.state != "open":
            return False
        
        if self.last_failure_time is None:
            return True
            
        return time.time() - self.last_failure_time > self.recovery_timeout
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ErrorHandler:
    """Centralized error handling and recovery manager."""
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.error_stats: Dict[str, int] = {}
        self.error_history: List[ErrorContext] = []
        
    def create_error_context(
        self,
        component: str,
        operation: str,
        category: ErrorCategory = ErrorCategory.PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs
    ) -> ErrorContext:
        """Create error context with automatic ID generation."""
        error_id = f"{component}_{operation}_{int(time.time())}"
        
        return ErrorContext(
            error_id=error_id,
            component=component,
            operation=operation,
            category=category,
            severity=severity,
            **kwargs
        )
    
    def log_error(self, error: Exception, context: Optional[ErrorContext] = None):
        """Log error with comprehensive context information."""
        if context is None:
            context = self.create_error_context(
                component="unknown",
                operation="unknown",
                message=str(error)
            )
        
        # Add stack trace if not present
        if context.stack_trace is None:
            context.stack_trace = traceback.format_exc()
        
        # Update error statistics
        error_key = f"{context.category.value}_{context.component}"
        self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1
        
        # Log based on severity
        log_data = context.to_dict()
        # Remove 'message' from extra data to avoid conflict with logging
        extra_data = {k: v for k, v in log_data.items() if k != 'message'}
        
        log_message = f"{context.severity.value.upper()} error in {context.component}.{context.operation}: {context.message}"
        
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra=extra_data)
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra=extra_data)
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra=extra_data)
        else:
            self.logger.info(log_message, extra=extra_data)
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreakerState()
        return self.circuit_breakers[service_name]
    
    @contextmanager
    def circuit_breaker(self, service_name: str):
        """Circuit breaker context manager."""
        breaker = self.get_circuit_breaker(service_name)
        
        # Check if circuit is open
        if breaker.state == "open":
            if not breaker.should_attempt_reset():
                raise CircuitBreakerError(f"Circuit breaker open for {service_name}")
            else:
                breaker.state = "half_open"
        
        try:
            yield breaker
            breaker.record_success()
        except Exception as e:
            breaker.record_failure()
            raise
    
    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        context: Optional[ErrorContext] = None
    ):
        """Retry function with exponential backoff."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if context:
                    context.retry_count = attempt
                
                return func()
                
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    if context:
                        context.retry_count = attempt
                        context.message = f"Max retries ({max_retries}) exceeded: {str(e)}"
                        self.log_error(e, context)
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                if context:
                    self.logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {context.operation} "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
                
                time.sleep(delay)
        
        raise last_exception
    
    async def async_retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        context: Optional[ErrorContext] = None
    ):
        """Async version of retry with exponential backoff."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if context:
                    context.retry_count = attempt
                
                if inspect.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
                    
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    if context:
                        context.retry_count = attempt
                        context.message = f"Max retries ({max_retries}) exceeded: {str(e)}"
                        self.log_error(e, context)
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                if context:
                    self.logger.warning(
                        f"Async retry attempt {attempt + 1}/{max_retries} for {context.operation} "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> str:
        """Handle error and return error ID.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            severity: Error severity level
            
        Returns:
            str: Unique error ID for tracking
        """
        # Create error context
        error_context = self.create_error_context(
            component=context.get('component', 'unknown') if context else 'unknown',
            operation=context.get('operation', 'unknown') if context else 'unknown',
            severity=severity,
            message=str(error)
        )
        
        # Add additional context details
        if context:
            error_context.details.update(context)
        
        # Add stack trace
        error_context.stack_trace = traceback.format_exc()
        
        # Store in history
        self.error_history.append(error_context)
        
        # Log the error
        self.log_error(error, error_context)
        
        return error_context.error_id
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for monitoring.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of error dictionaries
        """
        recent_errors = self.error_history[-limit:] if self.error_history else []
        return [error.to_dict() for error in recent_errors]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        # Count errors by type
        error_types = {}
        for error in self.error_history:
            error_type = error.category.value
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'error_counts': self.error_stats.copy(),
            'error_types': error_types,
            'circuit_breakers': {
                name: {
                    'state': breaker.state,
                    'failure_count': breaker.failure_count,
                    'last_failure_time': breaker.last_failure_time
                }
                for name, breaker in self.circuit_breakers.items()
            },
            'recent_error_count': len(self.error_history),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    component: str,
    operation: str,
    category: ErrorCategory = ErrorCategory.PROCESSING,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    max_retries: int = 0,
    exceptions: tuple = (Exception,)
):
    """Decorator for automatic error handling and retry."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = error_handler.create_error_context(
                component=component,
                operation=operation,
                category=category,
                severity=severity,
                max_retries=max_retries
            )
            
            if max_retries > 0:
                return error_handler.retry_with_backoff(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    exceptions=exceptions,
                    context=context
                )
            else:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context.message = str(e)
                    error_handler.log_error(e, context)
                    raise
        
        return wrapper
    return decorator


def handle_async_errors(
    component: str,
    operation: str,
    category: ErrorCategory = ErrorCategory.PROCESSING,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    max_retries: int = 0,
    exceptions: tuple = (Exception,)
):
    """Decorator for automatic async error handling and retry."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            context = error_handler.create_error_context(
                component=component,
                operation=operation,
                category=category,
                severity=severity,
                max_retries=max_retries
            )
            
            if max_retries > 0:
                return await error_handler.async_retry_with_backoff(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    exceptions=exceptions,
                    context=context
                )
            else:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    context.message = str(e)
                    error_handler.log_error(e, context)
                    raise
        
        return wrapper
    return decorator


@contextmanager
def graceful_degradation(
    fallback_value: Any = None,
    component: str = "unknown",
    operation: str = "unknown",
    log_errors: bool = True
):
    """Context manager for graceful degradation of non-critical operations."""
    try:
        yield
    except Exception as e:
        if log_errors:
            context = error_handler.create_error_context(
                component=component,
                operation=operation,
                severity=ErrorSeverity.LOW,
                message=f"Graceful degradation: {str(e)}"
            )
            error_handler.log_error(e, context)
        
        return fallback_value