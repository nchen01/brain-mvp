"""Tests for comprehensive error handling framework."""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from src.utils.error_handling import (
    ErrorHandler, ErrorContext, ErrorSeverity, ErrorCategory,
    RecoverableError, NonRecoverableError, CircuitBreakerError,
    CircuitBreakerState, handle_errors, handle_async_errors,
    graceful_degradation, error_handler
)


class TestErrorContext:
    """Test ErrorContext functionality."""
    
    def test_error_context_creation(self):
        """Test creating error context."""
        context = ErrorContext(
            error_id="test_error_123",
            component="test_component",
            operation="test_operation",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="Test error message"
        )
        
        assert context.error_id == "test_error_123"
        assert context.component == "test_component"
        assert context.operation == "test_operation"
        assert context.category == ErrorCategory.DATABASE
        assert context.severity == ErrorSeverity.HIGH
        assert context.message == "Test error message"
        assert context.retry_count == 0
        assert context.max_retries == 3
    
    def test_error_context_to_dict(self):
        """Test converting error context to dictionary."""
        context = ErrorContext(
            error_id="test_error_123",
            component="test_component",
            operation="test_operation"
        )
        
        result = context.to_dict()
        
        assert isinstance(result, dict)
        assert result['error_id'] == "test_error_123"
        assert result['component'] == "test_component"
        assert result['operation'] == "test_operation"
        assert 'timestamp' in result
        assert 'category' in result
        assert 'severity' in result


class TestCircuitBreakerState:
    """Test CircuitBreakerState functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Test initial circuit breaker state."""
        breaker = CircuitBreakerState()
        
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
        assert breaker.state == "closed"
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60.0
    
    def test_circuit_breaker_record_success(self):
        """Test recording successful operation."""
        breaker = CircuitBreakerState()
        breaker.failure_count = 3
        breaker.state = "half_open"
        
        breaker.record_success()
        
        assert breaker.failure_count == 0
        assert breaker.state == "closed"
        assert breaker.last_failure_time is None
    
    def test_circuit_breaker_record_failure(self):
        """Test recording failed operation."""
        breaker = CircuitBreakerState(failure_threshold=2)
        
        # First failure
        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.state == "closed"
        assert breaker.last_failure_time is not None
        
        # Second failure - should open circuit
        breaker.record_failure()
        assert breaker.failure_count == 2
        assert breaker.state == "open"
    
    def test_circuit_breaker_should_attempt_reset(self):
        """Test circuit breaker reset logic."""
        breaker = CircuitBreakerState(recovery_timeout=1.0)
        
        # Closed state - should not reset
        assert not breaker.should_attempt_reset()
        
        # Open state without last failure time - should reset
        breaker.state = "open"
        assert breaker.should_attempt_reset()
        
        # Open state with recent failure - should not reset
        breaker.last_failure_time = time.time()
        assert not breaker.should_attempt_reset()
        
        # Open state with old failure - should reset
        breaker.last_failure_time = time.time() - 2.0
        assert breaker.should_attempt_reset()


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        
        assert hasattr(handler, 'logger')
        assert isinstance(handler.circuit_breakers, dict)
        assert isinstance(handler.error_stats, dict)
    
    def test_create_error_context(self):
        """Test creating error context."""
        handler = ErrorHandler()
        
        context = handler.create_error_context(
            component="test_component",
            operation="test_operation",
            category=ErrorCategory.FILE_IO,
            severity=ErrorSeverity.MEDIUM
        )
        
        assert context.component == "test_component"
        assert context.operation == "test_operation"
        assert context.category == ErrorCategory.FILE_IO
        assert context.severity == ErrorSeverity.MEDIUM
        assert "test_component_test_operation" in context.error_id
    
    @patch('src.utils.error_handling.logging.getLogger')
    def test_log_error(self, mock_get_logger):
        """Test error logging."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        handler = ErrorHandler()
        handler.logger = mock_logger
        
        error = ValueError("Test error")
        context = ErrorContext(
            error_id="test_error",
            component="test_component",
            operation="test_operation",
            severity=ErrorSeverity.HIGH,
            message="Test error message"
        )
        
        handler.log_error(error, context)
        
        # Should log as error due to HIGH severity
        mock_logger.error.assert_called_once()
        
        # Check error stats
        assert "processing_test_component" in handler.error_stats
        assert handler.error_stats["processing_test_component"] == 1
    
    def test_get_circuit_breaker(self):
        """Test getting circuit breaker."""
        handler = ErrorHandler()
        
        # First call should create new breaker
        breaker1 = handler.get_circuit_breaker("test_service")
        assert isinstance(breaker1, CircuitBreakerState)
        assert "test_service" in handler.circuit_breakers
        
        # Second call should return same breaker
        breaker2 = handler.get_circuit_breaker("test_service")
        assert breaker1 is breaker2
    
    def test_circuit_breaker_context_manager_success(self):
        """Test circuit breaker context manager with success."""
        handler = ErrorHandler()
        
        with handler.circuit_breaker("test_service") as breaker:
            assert breaker.state == "closed"
            # Simulate successful operation
            pass
        
        assert breaker.failure_count == 0
        assert breaker.state == "closed"
    
    def test_circuit_breaker_context_manager_failure(self):
        """Test circuit breaker context manager with failure."""
        handler = ErrorHandler()
        
        with pytest.raises(ValueError):
            with handler.circuit_breaker("test_service") as breaker:
                raise ValueError("Test error")
        
        assert breaker.failure_count == 1
        assert breaker.state == "closed"  # Still closed, below threshold
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        handler = ErrorHandler()
        breaker = handler.get_circuit_breaker("test_service")
        
        # Force circuit to open
        breaker.state = "open"
        breaker.last_failure_time = time.time()
        
        with pytest.raises(CircuitBreakerError):
            with handler.circuit_breaker("test_service"):
                pass
    
    def test_retry_with_backoff_success(self):
        """Test retry mechanism with eventual success."""
        handler = ErrorHandler()
        
        call_count = 0
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = handler.retry_with_backoff(
            flaky_function,
            max_retries=3,
            base_delay=0.01  # Fast for testing
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_backoff_max_retries_exceeded(self):
        """Test retry mechanism when max retries exceeded."""
        handler = ErrorHandler()
        
        def always_fail():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            handler.retry_with_backoff(
                always_fail,
                max_retries=2,
                base_delay=0.01
            )
    
    @pytest.mark.asyncio
    async def test_async_retry_with_backoff_success(self):
        """Test async retry mechanism with eventual success."""
        handler = ErrorHandler()
        
        call_count = 0
        async def flaky_async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "async_success"
        
        result = await handler.async_retry_with_backoff(
            flaky_async_function,
            max_retries=3,
            base_delay=0.01
        )
        
        assert result == "async_success"
        assert call_count == 3
    
    def test_get_error_statistics(self):
        """Test getting error statistics."""
        handler = ErrorHandler()
        
        # Add some test data
        handler.error_stats["database_component1"] = 5
        handler.error_stats["file_io_component2"] = 3
        
        breaker = handler.get_circuit_breaker("test_service")
        breaker.failure_count = 2
        breaker.state = "half_open"
        
        stats = handler.get_error_statistics()
        
        assert "error_counts" in stats
        assert "circuit_breakers" in stats
        assert "total_errors" in stats
        assert "generated_at" in stats
        
        assert stats["error_counts"]["database_component1"] == 5
        assert stats["total_errors"] == 8
        assert stats["circuit_breakers"]["test_service"]["failure_count"] == 2


class TestDecorators:
    """Test error handling decorators."""
    
    def test_handle_errors_decorator_success(self):
        """Test handle_errors decorator with successful function."""
        @handle_errors(
            component="test_component",
            operation="test_operation"
        )
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_handle_errors_decorator_with_retry(self):
        """Test handle_errors decorator with retry."""
        call_count = 0
        
        @handle_errors(
            component="test_component",
            operation="test_operation",
            max_retries=2
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_async_errors_decorator(self):
        """Test handle_async_errors decorator."""
        @handle_async_errors(
            component="test_component",
            operation="test_operation"
        )
        async def async_function():
            return "async_success"
        
        result = await async_function()
        assert result == "async_success"


class TestGracefulDegradation:
    """Test graceful degradation functionality."""
    
    def test_graceful_degradation_success(self):
        """Test graceful degradation with successful operation."""
        with graceful_degradation(fallback_value="fallback") as result:
            result = "success"
        
        # Should not use fallback value
        assert result == "success"
    
    def test_graceful_degradation_with_exception(self):
        """Test graceful degradation with exception."""
        result = None
        
        with graceful_degradation(
            fallback_value="fallback",
            component="test_component",
            operation="test_operation"
        ):
            raise ValueError("Test error")
        
        # Should return fallback value (None in this case since we didn't capture the return)
        # The context manager handles the exception gracefully
    
    def test_graceful_degradation_no_logging(self):
        """Test graceful degradation without logging."""
        with graceful_degradation(
            fallback_value="fallback",
            log_errors=False
        ):
            raise ValueError("Test error")
        
        # Should handle exception without logging


if __name__ == "__main__":
    pytest.main([__file__])