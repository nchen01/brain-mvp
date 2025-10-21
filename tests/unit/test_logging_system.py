"""
Unit tests for the comprehensive logging system.

Tests logging functionality including:
- Structured logging
- Component-specific loggers
- Performance logging
- Error logging with context
- Log file management
- Prompt history logging
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from utils.logging_system import (
    DocForgeLogger, LogLevel, LogCategory, LogEntry,
    get_logger, setup_logging, log_info, log_error, log_performance
)
from utils.logging_integration import (
    ComponentLogger, log_function_call,
    document_processing_context, postprocessing_context, rag_operation_context
)


class TestDocForgeLogger:
    """Test the main DocForge logger class."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create logger instance with temporary directory."""
        return DocForgeLogger(log_dir=temp_log_dir, enable_console=False)
    
    def test_logger_initialization(self, logger, temp_log_dir):
        """Test logger initialization."""
        assert logger.log_dir == Path(temp_log_dir)
        assert not logger.enable_console
        
        # Check log files are created
        assert logger.log_files['main'].parent.exists()
        
        # Check component loggers are created
        assert 'system' in logger.loggers
        assert 'preprocessing' in logger.loggers
        assert 'api' in logger.loggers
    
    def test_basic_logging(self, logger, temp_log_dir):
        """Test basic logging functionality."""
        # Log a message
        logger.info(
            LogCategory.SYSTEM,
            "test_component",
            "Test message",
            details={"test": "data"}
        )
        
        # Check log file was created and contains entry
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            log_content = f.read()
            assert "Test message" in log_content
            assert "test_component" in log_content
    
    def test_structured_logging(self, logger, temp_log_dir):
        """Test structured logging with JSON format."""
        # Log structured message
        logger.log(
            LogLevel.INFO,
            LogCategory.PREPROCESSING,
            "test_processor",
            "Processing document",
            details={"document_id": "doc123", "file_type": "pdf"},
            performance_metrics={"duration": 1.5, "success": True}
        )
        
        # Read and parse log entry
        main_log = Path(temp_log_dir) / "docforge_main.log"
        with open(main_log, 'r') as f:
            log_line = f.read().strip()
            log_entry = json.loads(log_line)
        
        assert log_entry['level'] == 'INFO'
        assert log_entry['category'] == 'preprocessing'
        assert log_entry['component'] == 'test_processor'
        assert log_entry['message'] == 'Processing document'
        assert log_entry['details']['document_id'] == 'doc123'
        assert log_entry['performance_metrics']['duration'] == 1.5
    
    def test_context_management(self, logger):
        """Test logging context management."""
        # Set context
        logger.set_context(document_id="doc123", user_id="user456")
        context = logger.get_context()
        
        assert context['document_id'] == 'doc123'
        assert context['user_id'] == 'user456'
        
        # Test context manager
        with logger.context(trace_id="trace789"):
            inner_context = logger.get_context()
            assert inner_context['trace_id'] == 'trace789'
            assert inner_context['document_id'] == 'doc123'  # Preserved
        
        # Context should be restored
        final_context = logger.get_context()
        assert 'trace_id' not in final_context
        assert final_context['document_id'] == 'doc123'
    
    def test_error_logging(self, logger, temp_log_dir):
        """Test error logging with exception info."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error(
                LogCategory.SYSTEM,
                "test_component",
                "Test error occurred",
                exception=e,
                details={"context": "test"}
            )
        
        # Check error log file
        error_log = Path(temp_log_dir) / "docforge_errors.log"
        assert error_log.exists()
        
        with open(error_log, 'r') as f:
            log_content = f.read()
            assert "Test error occurred" in log_content
            assert "ValueError" in log_content
    
    def test_performance_logging(self, logger, temp_log_dir):
        """Test performance metrics logging."""
        metrics = {
            "duration_seconds": 2.5,
            "memory_used_mb": 150.0,
            "cpu_percent": 25.0
        }
        
        logger.log_performance_metrics("test_component", "test_operation", metrics)
        
        # Check performance log file
        perf_log = Path(temp_log_dir) / "docforge_performance.log"
        assert perf_log.exists()
        
        with open(perf_log, 'r') as f:
            log_content = f.read()
            assert "test_operation" in log_content
            assert "2.5" in log_content
    
    def test_prompt_history_logging(self, logger, temp_log_dir):
        """Test prompt history logging."""
        prompt = "Test prompt for API"
        response = "Test response from system"
        metadata = {"user": "test_user", "timestamp": time.time()}
        
        logger.log_prompt_history(prompt, response, metadata)
        
        # Check prompt history file
        prompt_log = Path(temp_log_dir) / "prompt_history.txt"
        assert prompt_log.exists()
        
        with open(prompt_log, 'r') as f:
            content = f.read()
            assert "Test prompt for API" in content
            assert "Test response from system" in content
            assert "test_user" in content
    
    def test_log_summary(self, logger):
        """Test log summary generation."""
        # Generate some log entries
        for i in range(5):
            logger.info(LogCategory.SYSTEM, "test", f"Message {i}")
        
        for i in range(2):
            logger.error(LogCategory.SYSTEM, "test", f"Error {i}")
        
        # Get summary
        summary = logger.get_log_summary(hours=1)
        
        assert 'total_entries' in summary
        assert 'error_count' in summary
        assert summary['error_count'] >= 2


class TestComponentLogger:
    """Test component-specific logger wrapper."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def component_logger(self, temp_log_dir):
        """Create component logger."""
        setup_logging(temp_log_dir, enable_console=False)
        return ComponentLogger(LogCategory.PREPROCESSING, "test_processor")
    
    def test_component_logging(self, component_logger, temp_log_dir):
        """Test component-specific logging."""
        component_logger.info("Processing started", details={"file": "test.pdf"})
        component_logger.error("Processing failed", details={"error": "timeout"})
        
        # Check logs were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            content = f.read()
            assert "Processing started" in content
            assert "Processing failed" in content
    
    def test_performance_logging(self, component_logger):
        """Test performance metrics logging."""
        metrics = {"duration": 1.5, "success": True}
        component_logger.log_performance("test_operation", metrics)
        
        # Should not raise any exceptions
        assert True
    
    def test_context_management(self, component_logger):
        """Test context management in component logger."""
        with component_logger.context(document_id="doc123"):
            component_logger.info("Processing with context")
        
        # Should not raise any exceptions
        assert True


class TestLoggingDecorators:
    """Test logging decorators and context managers."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(temp_dir, enable_console=False)
            yield temp_dir
    
    def test_function_logging_decorator(self, temp_log_dir):
        """Test function logging decorator."""
        @log_function_call(LogCategory.PREPROCESSING, "test_processor")
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
        
        # Check logs were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
    
    def test_function_logging_with_error(self, temp_log_dir):
        """Test function logging decorator with error."""
        @log_function_call(LogCategory.PREPROCESSING, "test_processor")
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Check error was logged
        error_log = Path(temp_log_dir) / "docforge_errors.log"
        assert error_log.exists()
    
    def test_document_processing_context(self, temp_log_dir):
        """Test document processing context manager."""
        with document_processing_context("doc123", "preprocessing"):
            time.sleep(0.1)  # Simulate processing
        
        # Check logs were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            content = f.read()
            assert "doc123" in content
            assert "preprocessing" in content
            assert "started" in content
            assert "completed" in content
    
    def test_postprocessing_context(self, temp_log_dir):
        """Test post-processing context manager."""
        with postprocessing_context("doc123", "chunking"):
            time.sleep(0.1)
        
        # Check logs were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
    
    def test_rag_operation_context(self, temp_log_dir):
        """Test RAG operation context manager."""
        with rag_operation_context("doc123", "indexing"):
            time.sleep(0.1)
        
        # Check logs were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
    
    def test_context_with_error(self, temp_log_dir):
        """Test context manager with error."""
        with pytest.raises(ValueError):
            with document_processing_context("doc123", "preprocessing"):
                raise ValueError("Processing failed")
        
        # Check error was logged
        main_log = Path(temp_log_dir) / "docforge_main.log"
        with open(main_log, 'r') as f:
            content = f.read()
            assert "failed" in content


class TestGlobalLoggingFunctions:
    """Test global logging convenience functions."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(temp_dir, enable_console=False)
            yield temp_dir
    
    def test_global_log_info(self, temp_log_dir):
        """Test global log_info function."""
        log_info(LogCategory.SYSTEM, "test", "Global info message")
        
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
    
    def test_global_log_error(self, temp_log_dir):
        """Test global log_error function."""
        log_error(LogCategory.SYSTEM, "test", "Global error message")
        
        error_log = Path(temp_log_dir) / "docforge_errors.log"
        assert error_log.exists()
    
    def test_global_log_performance(self, temp_log_dir):
        """Test global log_performance function."""
        metrics = {"duration": 1.0, "success": True}
        log_performance("test_component", "test_operation", metrics)
        
        perf_log = Path(temp_log_dir) / "docforge_performance.log"
        assert perf_log.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])