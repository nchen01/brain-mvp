"""Tests for integration layer error handling."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.utils.integration_error_handler import (
    IntegrationErrorHandler, integration_error_handler,
    execute_database_operation, execute_external_service_call, execute_file_operation
)
from src.utils.error_handling import (
    ErrorCategory, ErrorSeverity, RecoverableError, NonRecoverableError
)


class TestIntegrationErrorHandler:
    """Test IntegrationErrorHandler functionality."""
    
    def test_initialization(self):
        """Test IntegrationErrorHandler initialization."""
        handler = IntegrationErrorHandler()
        
        assert hasattr(handler, 'base_handler')
        assert hasattr(handler, 'component_strategies')
        assert len(handler.component_strategies) > 0
        
        # Check default strategies are set up
        assert 'database' in handler.component_strategies
        assert 'file_io' in handler.component_strategies
        assert 'external_service' in handler.component_strategies
        assert 'processing' in handler.component_strategies
    
    def test_get_strategy(self):
        """Test getting strategy for different error categories."""
        handler = IntegrationErrorHandler()
        
        # Test database strategy
        db_strategy = handler.get_strategy(ErrorCategory.DATABASE)
        assert db_strategy['max_retries'] == 3
        assert 'exceptions' in db_strategy
        
        # Test file I/O strategy
        file_strategy = handler.get_strategy(ErrorCategory.FILE_IO)
        assert file_strategy['max_retries'] == 2
        
        # Test external service strategy
        service_strategy = handler.get_strategy(ErrorCategory.EXTERNAL_SERVICE)
        assert service_strategy['max_retries'] == 3
        assert service_strategy['recovery_timeout'] == 60.0
        
        # Test unknown category defaults to processing
        unknown_strategy = handler.get_strategy(ErrorCategory.VALIDATION)
        processing_strategy = handler.get_strategy(ErrorCategory.PROCESSING)
        assert unknown_strategy == processing_strategy
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self):
        """Test successful execution with recovery."""
        handler = IntegrationErrorHandler()
        
        async def successful_operation():
            return "success"
        
        result = await handler.execute_with_recovery(
            operation=successful_operation,
            component="test_component",
            operation_name="test_operation",
            category=ErrorCategory.PROCESSING
        )
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_with_retry(self):
        """Test execution with retry on recoverable error."""
        handler = IntegrationErrorHandler()
        
        call_count = 0
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RecoverableError("Temporary failure")
            return "success_after_retry"
        
        result = await handler.execute_with_recovery(
            operation=flaky_operation,
            component="test_component",
            operation_name="test_operation",
            category=ErrorCategory.PROCESSING
        )
        
        assert result == "success_after_retry"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_circuit_breaker(self):
        """Test execution with circuit breaker for external services."""
        handler = IntegrationErrorHandler()
        
        async def external_service_call():
            return "external_success"
        
        result = await handler.execute_with_recovery(
            operation=external_service_call,
            component="external_api",
            operation_name="api_call",
            category=ErrorCategory.EXTERNAL_SERVICE
        )
        
        assert result == "external_success"
        
        # Check that circuit breaker was created
        service_name = "external_api_api_call"
        assert service_name in handler.base_handler.circuit_breakers
    
    def test_handle_component_failure_non_critical(self):
        """Test handling non-critical component failure."""
        handler = IntegrationErrorHandler()
        
        def fallback_action():
            return "fallback_result"
        
        error = ValueError("Component failed")
        result = handler.handle_component_failure(
            component="non_critical_component",
            error=error,
            fallback_action=fallback_action,
            critical=False
        )
        
        assert result == "fallback_result"
    
    def test_handle_component_failure_critical(self):
        """Test handling critical component failure."""
        handler = IntegrationErrorHandler()
        
        error = ValueError("Critical component failed")
        
        with pytest.raises(NonRecoverableError):
            handler.handle_component_failure(
                component="critical_component",
                error=error,
                critical=True
            )
    
    def test_handle_component_failure_fallback_fails(self):
        """Test handling component failure when fallback also fails."""
        handler = IntegrationErrorHandler()
        
        def failing_fallback():
            raise RuntimeError("Fallback also failed")
        
        error = ValueError("Component failed")
        result = handler.handle_component_failure(
            component="test_component",
            error=error,
            fallback_action=failing_fallback,
            critical=False
        )
        
        # Should return None when fallback fails
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_component_health_check_healthy(self):
        """Test creating health check for healthy component."""
        handler = IntegrationErrorHandler()
        
        async def healthy_check():
            return {"status": "ok", "response_time": 0.1}
        
        health_check = handler.create_component_health_check(
            component="test_service",
            health_check_func=healthy_check
        )
        
        result = await health_check()
        
        assert result['component'] == "test_service"
        assert result['status'] == 'healthy'
        assert 'timestamp' in result
        assert 'details' in result
    
    @pytest.mark.asyncio
    async def test_create_component_health_check_unhealthy(self):
        """Test creating health check for unhealthy component."""
        handler = IntegrationErrorHandler()
        
        async def unhealthy_check():
            raise ConnectionError("Service unavailable")
        
        health_check = handler.create_component_health_check(
            component="failing_service",
            health_check_func=unhealthy_check
        )
        
        result = await health_check()
        
        assert result['component'] == "failing_service"
        assert result['status'] == 'unhealthy'
        assert 'error' in result
        assert 'Service unavailable' in result['error']
    
    def test_get_integration_health_report(self):
        """Test getting integration health report."""
        handler = IntegrationErrorHandler()
        
        # Add some test data
        handler.base_handler.error_stats["database_component1"] = 5
        handler.base_handler.error_stats["file_io_component2"] = 3
        
        report = handler.get_integration_health_report()
        
        assert 'error_counts' in report
        assert 'circuit_breakers' in report
        assert 'integration_metrics' in report
        
        integration_metrics = report['integration_metrics']
        assert 'component_strategies' in integration_metrics
        assert 'active_circuit_breakers' in integration_metrics
        assert 'error_rate_by_category' in integration_metrics
        assert 'recommendations' in integration_metrics
        
        # Check error rate calculation
        assert integration_metrics['error_rate_by_category']['database'] == 5
        assert integration_metrics['error_rate_by_category']['file'] == 3


class TestConvenienceFunctions:
    """Test convenience functions for common integration patterns."""
    
    @pytest.mark.asyncio
    async def test_execute_database_operation(self):
        """Test database operation convenience function."""
        async def db_operation():
            return "db_result"
        
        result = await execute_database_operation(
            operation=db_operation,
            component="test_db",
            operation_name="select_data"
        )
        
        assert result == "db_result"
    
    @pytest.mark.asyncio
    async def test_execute_external_service_call(self):
        """Test external service call convenience function."""
        async def service_call():
            return "service_result"
        
        result = await execute_external_service_call(
            operation=service_call,
            component="external_api",
            operation_name="fetch_data"
        )
        
        assert result == "service_result"
    
    @pytest.mark.asyncio
    async def test_execute_file_operation(self):
        """Test file operation convenience function."""
        async def file_operation():
            return "file_result"
        
        result = await execute_file_operation(
            operation=file_operation,
            component="file_manager",
            operation_name="read_file"
        )
        
        assert result == "file_result"
    
    @pytest.mark.asyncio
    async def test_convenience_functions_with_context_data(self):
        """Test convenience functions with context data."""
        async def operation_with_context():
            return "context_result"
        
        context_data = {"file_path": "/test/path", "user_id": "test_user"}
        
        result = await execute_file_operation(
            operation=operation_with_context,
            component="file_manager",
            operation_name="write_file",
            context_data=context_data
        )
        
        assert result == "context_result"
    
    @pytest.mark.asyncio
    async def test_convenience_functions_error_handling(self):
        """Test that convenience functions properly handle errors."""
        async def failing_operation():
            raise RecoverableError("Operation failed")
        
        # Should retry and eventually fail
        with pytest.raises(RecoverableError):
            await execute_database_operation(
                operation=failing_operation,
                component="test_db",
                operation_name="failing_operation"
            )


if __name__ == "__main__":
    pytest.main([__file__])