"""Integration layer error handling with component-specific recovery strategies."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone

from .error_handling import (
    ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    RecoverableError, NonRecoverableError, error_handler
)

logger = logging.getLogger(__name__)


class IntegrationErrorHandler:
    """Specialized error handler for integration layer operations."""
    
    def __init__(self):
        """Initialize integration error handler."""
        self.base_handler = error_handler
        self.component_strategies: Dict[str, Dict[str, Any]] = {}
        self.setup_default_strategies()
    
    def setup_default_strategies(self):
        """Setup default error handling strategies for different components."""
        
        # Database operations
        self.component_strategies["database"] = {
            "max_retries": 3,
            "base_delay": 1.0,
            "backoff_factor": 2.0,
            "exceptions": (ConnectionError, TimeoutError, RecoverableError),
            "circuit_breaker_threshold": 5,
            "recovery_timeout": 30.0
        }
        
        # File I/O operations
        self.component_strategies["file_io"] = {
            "max_retries": 2,
            "base_delay": 0.5,
            "backoff_factor": 1.5,
            "exceptions": (IOError, OSError, PermissionError),
            "circuit_breaker_threshold": 3,
            "recovery_timeout": 15.0
        }
        
        # External service calls (LightRAG, etc.)
        self.component_strategies["external_service"] = {
            "max_retries": 3,
            "base_delay": 2.0,
            "backoff_factor": 2.0,
            "exceptions": (ConnectionError, TimeoutError, RecoverableError),
            "circuit_breaker_threshold": 5,
            "recovery_timeout": 60.0
        }
        
        # Processing operations
        self.component_strategies["processing"] = {
            "max_retries": 1,
            "base_delay": 1.0,
            "backoff_factor": 1.0,
            "exceptions": (RecoverableError,),
            "circuit_breaker_threshold": 10,
            "recovery_timeout": 120.0
        }
    
    def get_strategy(self, category: ErrorCategory) -> Dict[str, Any]:
        """Get error handling strategy for a specific category."""
        category_map = {
            ErrorCategory.DATABASE: "database",
            ErrorCategory.FILE_IO: "file_io",
            ErrorCategory.EXTERNAL_SERVICE: "external_service",
            ErrorCategory.NETWORK: "external_service",
            ErrorCategory.PROCESSING: "processing"
        }
        
        strategy_key = category_map.get(category, "processing")
        return self.component_strategies.get(strategy_key, self.component_strategies["processing"])
    
    async def execute_with_recovery(
        self,
        operation: Callable,
        component: str,
        operation_name: str,
        category: ErrorCategory = ErrorCategory.PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context_data: Optional[Dict[str, Any]] = None,
        custom_strategy: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute operation with comprehensive error handling and recovery."""
        
        # Get strategy
        strategy = custom_strategy or self.get_strategy(category)
        
        # Create error context
        context = self.base_handler.create_error_context(
            component=component,
            operation=operation_name,
            category=category,
            severity=severity,
            max_retries=strategy["max_retries"]
        )
        
        if context_data:
            context.details.update(context_data)
        
        # Use circuit breaker for external services
        if category in [ErrorCategory.EXTERNAL_SERVICE, ErrorCategory.NETWORK]:
            service_name = f"{component}_{operation_name}"
            
            try:
                with self.base_handler.circuit_breaker(service_name):
                    return await self._execute_with_retry(
                        operation, strategy, context
                    )
            except Exception as e:
                context.message = f"Circuit breaker or operation failed: {str(e)}"
                self.base_handler.log_error(e, context)
                raise
        else:
            return await self._execute_with_retry(operation, strategy, context)
    
    async def _execute_with_retry(
        self,
        operation: Callable,
        strategy: Dict[str, Any],
        context: ErrorContext
    ) -> Any:
        """Execute operation with retry logic."""
        return await self.base_handler.async_retry_with_backoff(
            operation,
            max_retries=strategy["max_retries"],
            base_delay=strategy["base_delay"],
            backoff_factor=strategy["backoff_factor"],
            exceptions=strategy["exceptions"],
            context=context
        )
    
    def handle_component_failure(
        self,
        component: str,
        error: Exception,
        fallback_action: Optional[Callable] = None,
        critical: bool = False
    ) -> Any:
        """Handle component failure with graceful degradation."""
        
        context = self.base_handler.create_error_context(
            component=component,
            operation="component_failure",
            severity=ErrorSeverity.CRITICAL if critical else ErrorSeverity.HIGH,
            message=f"Component {component} failed: {str(error)}"
        )
        
        self.base_handler.log_error(error, context)
        
        if critical:
            # For critical components, re-raise the error
            raise NonRecoverableError(
                f"Critical component {component} failed: {str(error)}",
                context
            )
        
        # For non-critical components, try fallback
        if fallback_action:
            try:
                logger.info(f"Attempting fallback action for component {component}")
                return fallback_action()
            except Exception as fallback_error:
                logger.error(f"Fallback action failed for component {component}: {fallback_error}")
        
        # Return None or appropriate default value
        return None
    
    def create_component_health_check(
        self,
        component: str,
        health_check_func: Callable,
        check_interval: float = 60.0
    ) -> Callable:
        """Create a health check function for a component."""
        
        async def health_check():
            """Perform health check for component."""
            try:
                result = await health_check_func()
                
                # Reset circuit breaker on successful health check
                if component in self.base_handler.circuit_breakers:
                    breaker = self.base_handler.circuit_breakers[component]
                    if breaker.state == "open" and breaker.should_attempt_reset():
                        breaker.record_success()
                        logger.info(f"Circuit breaker reset for component {component}")
                
                return {
                    'component': component,
                    'status': 'healthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'details': result
                }
                
            except Exception as e:
                context = self.base_handler.create_error_context(
                    component=component,
                    operation="health_check",
                    category=ErrorCategory.SYSTEM_RESOURCE,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Health check failed: {str(e)}"
                )
                
                self.base_handler.log_error(e, context)
                
                return {
                    'component': component,
                    'status': 'unhealthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': str(e)
                }
        
        return health_check
    
    def get_integration_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for integration layer."""
        
        base_stats = self.base_handler.get_error_statistics()
        
        # Add integration-specific metrics
        integration_stats = {
            'component_strategies': list(self.component_strategies.keys()),
            'active_circuit_breakers': len([
                name for name, breaker in base_stats['circuit_breakers'].items()
                if breaker['state'] != 'closed'
            ]),
            'error_rate_by_category': {},
            'recommendations': []
        }
        
        # Calculate error rates by category
        total_errors = base_stats['total_errors']
        if total_errors > 0:
            for error_key, count in base_stats['error_counts'].items():
                category = error_key.split('_')[0]
                if category not in integration_stats['error_rate_by_category']:
                    integration_stats['error_rate_by_category'][category] = 0
                integration_stats['error_rate_by_category'][category] += count
        
        # Generate recommendations
        if integration_stats['active_circuit_breakers'] > 0:
            integration_stats['recommendations'].append(
                "Some circuit breakers are open - check external service connectivity"
            )
        
        if total_errors > 100:
            integration_stats['recommendations'].append(
                "High error count detected - consider reviewing error patterns"
            )
        
        return {
            **base_stats,
            'integration_metrics': integration_stats
        }


# Global integration error handler instance
integration_error_handler = IntegrationErrorHandler()


# Convenience functions for common integration patterns
async def execute_database_operation(
    operation: Callable,
    component: str,
    operation_name: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Any:
    """Execute database operation with appropriate error handling."""
    return await integration_error_handler.execute_with_recovery(
        operation=operation,
        component=component,
        operation_name=operation_name,
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        context_data=context_data
    )


async def execute_external_service_call(
    operation: Callable,
    component: str,
    operation_name: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Any:
    """Execute external service call with circuit breaker and retry logic."""
    return await integration_error_handler.execute_with_recovery(
        operation=operation,
        component=component,
        operation_name=operation_name,
        category=ErrorCategory.EXTERNAL_SERVICE,
        severity=ErrorSeverity.HIGH,
        context_data=context_data
    )


async def execute_file_operation(
    operation: Callable,
    component: str,
    operation_name: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Any:
    """Execute file I/O operation with appropriate error handling."""
    return await integration_error_handler.execute_with_recovery(
        operation=operation,
        component=component,
        operation_name=operation_name,
        category=ErrorCategory.FILE_IO,
        severity=ErrorSeverity.MEDIUM,
        context_data=context_data
    )