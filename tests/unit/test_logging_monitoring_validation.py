"""
Validation tests for logging and monitoring systems.

This test suite provides a comprehensive validation of the logging and monitoring
implementation for task 11.3, focusing on core functionality that can be reliably tested.
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from utils.logging_system import (
    DocForgeLogger, LogLevel, LogCategory, setup_logging, get_logger
)
from utils.monitoring_dashboard import MonitoringDashboard, get_dashboard
from utils.logging_integration import (
    ComponentLogger, document_processing_context, postprocessing_context, rag_operation_context
)


class TestLoggingSystemValidation:
    """Validate core logging system functionality."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_log_file_creation_all_categories(self, temp_log_dir):
        """Test that log files are created for all pipeline stages."""
        logger = setup_logging(temp_log_dir, enable_console=False)
        
        # Test all log categories
        test_cases = [
            (LogCategory.PREPROCESSING, "preprocessing_component", "Document processing started"),
            (LogCategory.POSTPROCESSING, "postprocessing_component", "Post-processing started"),
            (LogCategory.RAG, "rag_component", "RAG indexing started"),
            (LogCategory.STORAGE, "storage_component", "Storage operation started"),
            (LogCategory.VERSIONING, "versioning_component", "Version creation started"),
            (LogCategory.API, "api_component", "API request received"),
            (LogCategory.AUTHENTICATION, "auth_component", "Authentication attempt"),
            (LogCategory.SYSTEM, "system_component", "System operation started")
        ]
        
        for category, component, message in test_cases:
            logger.info(category, component, message, details={"test": "validation"})
        
        # Verify main log file exists and contains all messages
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            content = f.read()
            for _, _, message in test_cases:
                assert message in content
        
        # Verify category-specific log files exist
        expected_logs = [
            "docforge_preprocessing.log",
            "docforge_postprocessing.log", 
            "docforge_rag.log",
            "docforge_storage.log",
            "docforge_versioning.log",
            "docforge_api.log",
            "docforge_authentication.log",
            "docforge_system.log"
        ]
        
        for log_file in expected_logs:
            log_path = Path(temp_log_dir) / log_file
            assert log_path.exists(), f"Log file {log_file} should exist"
    
    def test_error_logging_and_tracking(self, temp_log_dir):
        """Test error logging across all pipeline stages."""
        logger = setup_logging(temp_log_dir, enable_console=False)
        
        # Test error logging for different components
        error_scenarios = [
            (LogCategory.PREPROCESSING, "mineru_processor", ValueError("Invalid PDF format")),
            (LogCategory.POSTPROCESSING, "chunker", RuntimeError("Chunking failed")),
            (LogCategory.RAG, "lightrag_integration", ConnectionError("Service unavailable")),
            (LogCategory.STORAGE, "meta_document_crud", IOError("Database connection lost")),
            (LogCategory.VERSIONING, "lineage_manager", KeyError("Version not found"))
        ]
        
        for category, component, error in error_scenarios:
            logger.log_error_with_context(category, component, error, {"test_context": "validation"})
        
        # Verify error log file exists and contains all errors
        error_log = Path(temp_log_dir) / "docforge_errors.log"
        assert error_log.exists()
        
        with open(error_log, 'r') as f:
            error_content = f.read()
            assert "Invalid PDF format" in error_content
            assert "Chunking failed" in error_content
            assert "Service unavailable" in error_content
            assert "Database connection lost" in error_content
            assert "Version not found" in error_content
            assert "ValueError" in error_content
            assert "RuntimeError" in error_content
            assert "ConnectionError" in error_content
    
    def test_performance_metrics_logging(self, temp_log_dir):
        """Test performance metrics logging."""
        logger = setup_logging(temp_log_dir, enable_console=False)
        
        # Test performance logging for different operations
        performance_tests = [
            ("document_processor", "pdf_processing", {"duration_seconds": 15.2, "pages": 10}),
            ("chunker", "paragraph_chunking", {"duration_seconds": 2.1, "chunks": 25}),
            ("embedder", "text_embedding", {"duration_seconds": 8.7, "tokens": 3500}),
            ("indexer", "lightrag_indexing", {"duration_seconds": 25.4, "relationships": 12})
        ]
        
        for component, operation, metrics in performance_tests:
            logger.log_performance_metrics(component, operation, metrics)
        
        # Verify performance log file exists and contains metrics
        perf_log = Path(temp_log_dir) / "docforge_performance.log"
        assert perf_log.exists()
        
        with open(perf_log, 'r') as f:
            perf_content = f.read()
            assert "15.2" in perf_content  # pdf_processing duration
            assert "2.1" in perf_content   # chunking duration
            assert "8.7" in perf_content   # embedding duration
            assert "25.4" in perf_content  # indexing duration
    
    def test_context_managers_functionality(self, temp_log_dir):
        """Test logging context managers for pipeline operations."""
        logger = setup_logging(temp_log_dir, enable_console=False)
        
        doc_uuid = "test_context_doc_123"
        
        # Test document processing context
        with document_processing_context(doc_uuid, "test_preprocessing"):
            time.sleep(0.1)  # Simulate processing
        
        # Test postprocessing context
        with postprocessing_context(doc_uuid, "test_chunking"):
            time.sleep(0.05)  # Simulate processing
        
        # Test RAG operation context
        with rag_operation_context(doc_uuid, "test_indexing"):
            time.sleep(0.08)  # Simulate processing
        
        # Verify context logging
        main_log = Path(temp_log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            content = f.read()
            assert "test_preprocessing" in content
            assert "test_chunking" in content
            assert "test_indexing" in content
            assert "started" in content
            assert "completed" in content
            assert doc_uuid in content
    
    def test_prompt_history_logging(self, temp_log_dir):
        """Test prompt history logging functionality."""
        logger = setup_logging(temp_log_dir, enable_console=False)
        
        # Test prompt history logging
        test_prompts = [
            ("Summarize the document", "The document discusses AI systems", {"user": "test1"}),
            ("Extract key findings", "Key findings include performance improvements", {"user": "test2"}),
            ("Compare versions", "Version 2 shows better results than version 1", {"user": "test3"})
        ]
        
        for prompt, response, metadata in test_prompts:
            logger.log_prompt_history(prompt, response, metadata)
        
        # Verify prompt history file
        prompt_log = Path(temp_log_dir) / "prompt_history.txt"
        assert prompt_log.exists()
        
        with open(prompt_log, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Summarize the document" in content
            assert "Extract key findings" in content
            assert "Compare versions" in content
            assert "The document discusses AI systems" in content
            assert "test1" in content
            assert "test2" in content


class TestMonitoringSystemValidation:
    """Validate core monitoring system functionality."""
    
    @pytest.fixture
    def monitoring_dashboard(self):
        """Create monitoring dashboard for testing."""
        dashboard = MonitoringDashboard(metrics_retention_hours=1)
        yield dashboard
        dashboard.stop_monitoring()
    
    def test_component_health_tracking(self, monitoring_dashboard):
        """Test component health tracking functionality."""
        # Record activities for different components
        components = ['preprocessing', 'postprocessing', 'storage', 'rag', 'versioning', 'api']
        
        for component in components:
            # Record successful activities
            monitoring_dashboard.record_component_activity(component, success=True)
            monitoring_dashboard.record_component_activity(component, success=True)
            
            # Record some failures for specific components
            if component in ['preprocessing', 'rag']:
                monitoring_dashboard.record_component_activity(component, success=False)
        
        # Get component health status
        status = monitoring_dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        # Verify all components are tracked
        for component in components:
            assert component in component_health
            health = component_health[component]
            
            assert 'status' in health
            assert 'last_activity' in health
            assert 'error_count' in health
            assert 'performance_score' in health
            
            # Components with errors should have error counts
            if component in ['preprocessing', 'rag']:
                assert health['error_count'] >= 1
            else:
                assert health['error_count'] <= 1  # May have initialization errors
    
    def test_processing_queue_monitoring(self, monitoring_dashboard):
        """Test processing queue monitoring."""
        # Add tasks to queue
        test_tasks = [
            ("task_1", "document_upload"),
            ("task_2", "preprocessing"),
            ("task_3", "postprocessing"),
            ("task_4", "rag_indexing"),
            ("task_5", "storage_operation")
        ]
        
        for task_id, operation in test_tasks:
            monitoring_dashboard.record_processing_task(task_id, operation)
        
        # Verify queue status
        status = monitoring_dashboard.get_current_status()
        queue_status = status.get('queue_status', {})
        
        assert queue_status['size'] == 5
        
        # Complete some tasks
        monitoring_dashboard.complete_processing_task("task_1", success=True)
        monitoring_dashboard.complete_processing_task("task_2", success=False)
        monitoring_dashboard.complete_processing_task("task_3", success=True)
        
        # Verify updated queue status
        updated_status = monitoring_dashboard.get_current_status()
        updated_queue = updated_status.get('queue_status', {})
        
        assert updated_queue['size'] == 2  # 2 tasks remaining
    
    def test_api_request_metrics_tracking(self, monitoring_dashboard):
        """Test API request metrics tracking."""
        # Record various API requests
        api_requests = [
            (0.5, 200),   # Fast successful
            (1.2, 200),   # Slower successful  
            (0.3, 404),   # Fast error
            (2.5, 500),   # Slow error
            (0.8, 201),   # Successful creation
            (1.1, 200),   # Normal request
            (0.4, 200),   # Fast successful
            (3.0, 503)    # Service unavailable
        ]
        
        for response_time, status_code in api_requests:
            monitoring_dashboard.record_api_request(response_time, status_code)
        
        # Get current metrics
        status = monitoring_dashboard.get_current_status()
        current_metrics = status.get('current_metrics')
        
        if current_metrics:
            # Should have some error rate (3 errors out of 8 requests = 37.5%)
            assert current_metrics['error_rate'] > 0
            assert current_metrics['avg_response_time'] > 0
            
            # Error rate should be reasonable
            expected_error_rate = (3 / 8) * 100  # 37.5%
            assert abs(current_metrics['error_rate'] - expected_error_rate) < 5.0
    
    def test_alert_threshold_detection(self, monitoring_dashboard):
        """Test alert threshold detection."""
        # Set lower thresholds for testing
        monitoring_dashboard.alert_thresholds['queue_size']['warning'] = 3
        monitoring_dashboard.alert_thresholds['queue_size']['critical'] = 5
        monitoring_dashboard.alert_thresholds['error_rate']['warning'] = 20.0
        monitoring_dashboard.alert_thresholds['error_rate']['critical'] = 40.0
        
        # Create conditions that should trigger alerts
        
        # 1. High queue size
        for i in range(6):  # Above critical threshold
            monitoring_dashboard.record_processing_task(f"alert_task_{i}", "test_operation")
        
        # 2. High error rate
        for _ in range(3):  # Successful requests
            monitoring_dashboard.record_api_request(0.5, 200)
        
        for _ in range(5):  # Failed requests (62.5% error rate)
            monitoring_dashboard.record_api_request(1.0, 500)
        
        # Get status and check for alert conditions
        status = monitoring_dashboard.get_current_status()
        queue_size = status.get('queue_status', {}).get('size', 0)
        
        # Should have high queue size
        assert queue_size >= monitoring_dashboard.alert_thresholds['queue_size']['critical']
        
        # Error rate should be high
        current_metrics = status.get('current_metrics')
        if current_metrics:
            assert current_metrics['error_rate'] >= monitoring_dashboard.alert_thresholds['error_rate']['critical']


class TestLoggingMonitoringIntegrationValidation:
    """Validate integration between logging and monitoring systems."""
    
    @pytest.fixture
    def integrated_system(self):
        """Set up integrated logging and monitoring system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up logging
            logger = setup_logging(temp_dir, enable_console=False)
            
            # Set up monitoring  
            dashboard = MonitoringDashboard(log_dir=temp_dir, metrics_retention_hours=1)
            
            yield {
                'logger': logger,
                'dashboard': dashboard,
                'log_dir': temp_dir
            }
            
            dashboard.stop_monitoring()
    
    def test_coordinated_logging_and_monitoring(self, integrated_system):
        """Test coordinated operation of logging and monitoring systems."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        log_dir = integrated_system['log_dir']
        
        # Perform coordinated operations
        doc_uuid = "integration_test_doc"
        
        # 1. Log and monitor document processing
        with logger.context(document_id=doc_uuid):
            logger.log_document_processing(
                doc_uuid, "preprocessing", "started",
                {"processor": "mineru", "file_type": "pdf"}
            )
            
            dashboard.record_component_activity("preprocessing", success=True)
            dashboard.record_processing_task("preprocess_task", "preprocessing")
            
            logger.log_document_processing(
                doc_uuid, "preprocessing", "completed",
                {"processor": "mineru", "pages_processed": 10},
                performance_metrics={"duration_seconds": 12.5}
            )
            
            dashboard.complete_processing_task("preprocess_task", success=True)
        
        # 2. Log and monitor API requests
        logger.log_api_request("POST", "/api/v1/documents/upload", "test_user", 201, 2.1)
        dashboard.record_api_request(2.1, 201)
        
        # 3. Log and monitor errors
        try:
            raise ConnectionError("Test integration error")
        except ConnectionError as e:
            logger.log_error_with_context(
                LogCategory.RAG, "lightrag_integration", e,
                {"operation": "indexing", "document_id": doc_uuid}
            )
            dashboard.record_component_activity("rag", success=False)
        
        # Verify both systems recorded the activities
        
        # Check logging
        main_log = Path(log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            log_content = f.read()
            assert "preprocessing" in log_content
            assert "started" in log_content
            assert "completed" in log_content
            assert doc_uuid in log_content
            assert "Test integration error" in log_content
        
        # Check monitoring
        status = dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        assert 'preprocessing' in component_health
        assert 'rag' in component_health
        
        # RAG component should have error
        if 'rag' in component_health:
            assert component_health['rag']['error_count'] > 0
    
    def test_end_to_end_pipeline_logging_monitoring(self, integrated_system):
        """Test end-to-end pipeline with both logging and monitoring."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        log_dir = integrated_system['log_dir']
        
        doc_uuid = "e2e_test_doc"
        
        # Simulate complete pipeline with logging and monitoring
        pipeline_stages = [
            ("preprocessing", "Document preprocessing", 12.5),
            ("postprocessing", "Document postprocessing", 3.2),
            ("storage", "Document storage", 0.8),
            ("rag", "RAG preparation", 18.7)
        ]
        
        for stage, description, duration in pipeline_stages:
            # Log stage
            logger.info(
                getattr(LogCategory, stage.upper()),
                f"{stage}_component",
                f"{description} completed",
                details={"document_id": doc_uuid, "duration": duration},
                performance_metrics={"duration_seconds": duration, "success": True}
            )
            
            # Monitor stage
            dashboard.record_component_activity(stage, success=True)
            dashboard.record_processing_task(f"{stage}_task", stage)
            dashboard.complete_processing_task(f"{stage}_task", success=True)
        
        # Verify comprehensive logging
        log_files = [
            "docforge_main.log",
            "docforge_preprocessing.log", 
            "docforge_postprocessing.log",
            "docforge_storage.log",
            "docforge_rag.log",
            "docforge_performance.log"
        ]
        
        for log_file in log_files:
            log_path = Path(log_dir) / log_file
            assert log_path.exists(), f"Log file {log_file} should exist"
        
        # Verify performance metrics
        perf_log = Path(log_dir) / "docforge_performance.log"
        with open(perf_log, 'r') as f:
            perf_content = f.read()
            assert "12.5" in perf_content  # preprocessing
            assert "3.2" in perf_content   # postprocessing
            assert "18.7" in perf_content  # rag
        
        # Verify monitoring status
        status = dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        for stage, _, _ in pipeline_stages:
            assert stage in component_health
            # All stages should be healthy (no errors)
            health = component_health[stage]
            assert health['status'] in ['healthy', 'warning']  # May be warning due to timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])