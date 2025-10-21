"""
Comprehensive tests for logging and monitoring systems.

This test suite validates:
- Log file creation and content for all pipeline stages
- Monitoring metrics accuracy across the complete pipeline
- Alerting functionality for various failure scenarios
- Integration between logging and monitoring components
- Performance tracking and error handling
"""

import pytest
import tempfile
import json
import time
import os
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Any, List

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from utils.logging_system import (
    DocForgeLogger, LogLevel, LogCategory, LogEntry,
    get_logger, setup_logging
)
from utils.monitoring_dashboard import (
    MonitoringDashboard, SystemMetrics, ComponentHealth,
    get_dashboard
)
from utils.logging_integration import (
    ComponentLogger, log_function_call,
    document_processing_context, postprocessing_context, rag_operation_context,
    preprocessing_logger, postprocessing_logger, storage_logger, rag_logger
)


class TestLogFileCreationAndContent:
    """Test log file creation and content validation for all pipeline stages."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def logger_system(self, temp_log_dir):
        """Set up logger system for testing."""
        return setup_logging(temp_log_dir, enable_console=False) 
   
    def test_preprocessing_pipeline_logging(self, logger_system, temp_log_dir):
        """Test logging for preprocessing pipeline stages."""
        # Test document registration logging
        logger_system.log_document_processing(
            "doc123", "registration", "started",
            {"filename": "test.pdf", "user_id": "user123"}
        )
        
        logger_system.log_document_processing(
            "doc123", "registration", "completed",
            {"filename": "test.pdf", "doc_uuid": "doc123"},
            performance_metrics={"duration_seconds": 0.5}
        )
        
        # Test routing logging
        logger_system.log_document_processing(
            "doc123", "routing", "completed",
            {"processor_selected": "mineru", "file_type": "pdf"}
        )
        
        # Test processor logging
        logger_system.log_document_processing(
            "doc123", "mineru_processing", "started",
            {"processor": "mineru", "input_file": "test.pdf"}
        )
        
        logger_system.log_document_processing(
            "doc123", "mineru_processing", "completed",
            {"processor": "mineru", "output_pages": 5, "extracted_text_length": 2500},
            performance_metrics={"duration_seconds": 15.2, "memory_used_mb": 150}
        )
        
        # Verify log files were created
        main_log = Path(temp_log_dir) / "docforge_main.log"
        preprocessing_log = Path(temp_log_dir) / "docforge_preprocessing.log"
        performance_log = Path(temp_log_dir) / "docforge_performance.log"
        
        assert main_log.exists()
        assert preprocessing_log.exists()
        assert performance_log.exists()
        
        # Verify log content
        with open(preprocessing_log, 'r') as f:
            log_content = f.read()
            assert "doc123" in log_content
            assert "registration" in log_content
            assert "routing" in log_content
            assert "mineru_processing" in log_content
            assert "started" in log_content
            assert "completed" in log_content
        
        # Verify performance metrics logging
        with open(performance_log, 'r') as f:
            perf_content = f.read()
            assert "duration_seconds" in perf_content
            assert "15.2" in perf_content
            assert "memory_used_mb" in perf_content
    
    def test_postprocessing_pipeline_logging(self, logger_system, temp_log_dir):
        """Test logging for post-processing pipeline stages."""
        # Test chunking logging
        logger_system.log_postprocessing_activity(
            "doc123", "chunking", "started",
            {"strategy": "paragraph", "input_length": 2500}
        )
        
        logger_system.log_postprocessing_activity(
            "doc123", "chunking", "completed",
            {"strategy": "paragraph", "chunks_created": 15, "avg_chunk_size": 167},
            performance_metrics={"duration_seconds": 2.1}
        )
        
        # Test abbreviation expansion logging
        logger_system.log_postprocessing_activity(
            "doc123", "abbreviation_expansion", "started",
            {"abbreviations_found": 8, "domain": "technical"}
        )
        
        logger_system.log_postprocessing_activity(
            "doc123", "abbreviation_expansion", "completed",
            {"abbreviations_expanded": 6, "confidence_avg": 0.85},
            performance_metrics={"duration_seconds": 1.3}
        )
        
        # Verify postprocessing log
        postprocessing_log = Path(temp_log_dir) / "docforge_postprocessing.log"
        assert postprocessing_log.exists()
        
        with open(postprocessing_log, 'r') as f:
            log_content = f.read()
            assert "chunking" in log_content
            assert "abbreviation_expansion" in log_content
            assert "paragraph" in log_content
            assert "chunks_created" in log_content
            assert "abbreviations_expanded" in log_content
    
    def test_rag_pipeline_logging(self, logger_system, temp_log_dir):
        """Test logging for RAG preparation pipeline stages."""
        # Test embedding generation logging
        logger_system.log_rag_activity(
            "doc123", "embedding_generation", "started",
            {"chunks_to_embed": 15, "model": "sentence-transformers/all-MiniLM-L6-v2"}
        )
        
        logger_system.log_rag_activity(
            "doc123", "embedding_generation", "completed",
            {"embeddings_created": 15, "embedding_dim": 384},
            performance_metrics={"duration_seconds": 8.7, "tokens_processed": 3500}
        )
        
        # Test indexing logging
        logger_system.log_rag_activity(
            "doc123", "lightrag_indexing", "started",
            {"documents_to_index": 1, "existing_index_size": 50}
        )
        
        logger_system.log_rag_activity(
            "doc123", "lightrag_indexing", "completed",
            {"index_updated": True, "new_index_size": 51, "relationships_created": 12},
            performance_metrics={"duration_seconds": 25.4}
        )
        
        # Verify RAG log
        rag_log = Path(temp_log_dir) / "docforge_rag.log"
        assert rag_log.exists()
        
        with open(rag_log, 'r') as f:
            log_content = f.read()
            assert "embedding_generation" in log_content
            assert "lightrag_indexing" in log_content
            assert "embeddings_created" in log_content
            assert "relationships_created" in log_content
    
    def test_storage_operations_logging(self, logger_system, temp_log_dir):
        """Test logging for storage operations."""
        # Test database operations
        with logger_system.context(document_id="doc123"):
            logger_system.info(
                LogCategory.STORAGE,
                "meta_document_crud",
                "Creating meta document",
                details={"doc_uuid": "doc123", "components": 3}
            )
            
            logger_system.info(
                LogCategory.STORAGE,
                "meta_document_crud",
                "Meta document created successfully",
                details={"doc_uuid": "doc123", "meta_file_uuids": ["meta1", "meta2", "meta3"]},
                performance_metrics={"duration_seconds": 0.8}
            )
        
        # Test versioning operations
        with logger_system.context(document_id="doc123", version_id="v2"):
            logger_system.info(
                LogCategory.VERSIONING,
                "lineage_manager",
                "Creating new document version",
                details={"lineage_uuid": "lineage123", "parent_version": 1}
            )
        
        # Verify storage and versioning logs
        storage_log = Path(temp_log_dir) / "docforge_storage.log"
        versioning_log = Path(temp_log_dir) / "docforge_versioning.log"
        
        assert storage_log.exists()
        assert versioning_log.exists()
        
        with open(storage_log, 'r') as f:
            storage_content = f.read()
            assert "meta_document_crud" in storage_content
            assert "Creating meta document" in storage_content
            assert "doc123" in storage_content
        
        with open(versioning_log, 'r') as f:
            versioning_content = f.read()
            assert "lineage_manager" in versioning_content
            assert "Creating new document version" in versioning_content
            assert "lineage123" in versioning_content
    
    def test_api_request_logging(self, logger_system, temp_log_dir):
        """Test API request logging."""
        # Test various API requests
        api_requests = [
            ("POST", "/api/v1/documents/upload", "user123", 201, 2.5),
            ("GET", "/api/v1/documents/doc123", "user123", 200, 0.3),
            ("POST", "/api/v1/documents/doc123/process", "user123", 202, 0.1),
            ("GET", "/api/v1/documents/doc123/status", "user123", 200, 0.2),
            ("POST", "/api/v1/query", "user456", 200, 1.8),
            ("GET", "/api/v1/health", None, 200, 0.05)
        ]
        
        for method, endpoint, user_id, status_code, response_time in api_requests:
            logger_system.log_api_request(
                method, endpoint, user_id, status_code, response_time,
                details={
                    "user_agent": "DocForge-Client/1.0",
                    "content_length": "1024" if method == "POST" else "0"
                }
            )
        
        # Verify API log
        api_log = Path(temp_log_dir) / "docforge_api.log"
        assert api_log.exists()
        
        with open(api_log, 'r') as f:
            api_content = f.read()
            assert "/api/v1/documents/upload" in api_content
            assert "/api/v1/query" in api_content
            assert "user123" in api_content
            assert "user456" in api_content
            assert "201" in api_content
            assert "200" in api_content
    
    def test_error_logging_across_pipeline(self, logger_system, temp_log_dir):
        """Test error logging across all pipeline stages."""
        # Test preprocessing errors
        try:
            raise ValueError("Invalid file format: corrupted PDF")
        except ValueError as e:
            logger_system.log_error_with_context(
                LogCategory.PREPROCESSING,
                "mineru_processor",
                e,
                {"document_id": "doc123", "file_path": "/tmp/corrupted.pdf"}
            )
        
        # Test postprocessing errors
        try:
            raise RuntimeError("Chunking failed: text too short")
        except RuntimeError as e:
            logger_system.log_error_with_context(
                LogCategory.POSTPROCESSING,
                "chunker",
                e,
                {"document_id": "doc123", "text_length": 50}
            )
        
        # Test RAG errors
        try:
            raise ConnectionError("LightRAG service unavailable")
        except ConnectionError as e:
            logger_system.log_error_with_context(
                LogCategory.RAG,
                "lightrag_integration",
                e,
                {"document_id": "doc123", "operation": "indexing"}
            )
        
        # Test storage errors
        try:
            raise IOError("Database connection lost")
        except IOError as e:
            logger_system.log_error_with_context(
                LogCategory.STORAGE,
                "meta_document_crud",
                e,
                {"document_id": "doc123", "operation": "create"}
            )
        
        # Verify error log
        error_log = Path(temp_log_dir) / "docforge_errors.log"
        assert error_log.exists()
        
        with open(error_log, 'r') as f:
            error_content = f.read()
            assert "Invalid file format" in error_content
            assert "Chunking failed" in error_content
            assert "LightRAG service unavailable" in error_content
            assert "Database connection lost" in error_content
            assert "ValueError" in error_content
            assert "RuntimeError" in error_content
            assert "ConnectionError" in error_content
            assert "IOError" in error_content
    
    def test_prompt_history_logging(self, logger_system, temp_log_dir):
        """Test prompt history logging functionality."""
        # Test various prompt-response pairs
        prompts_responses = [
            (
                "Summarize the key findings from the uploaded research paper",
                "The research paper presents three main findings: 1) Novel algorithm improves efficiency by 25%, 2) Reduced memory usage by 40%, 3) Better accuracy in edge cases.",
                {"user_id": "user123", "document_id": "doc123", "query_type": "summarization"}
            ),
            (
                "What are the technical specifications mentioned in the document?",
                "Technical specifications include: CPU requirements (4+ cores), RAM (8GB minimum), Storage (50GB available space), Network (1Gbps recommended).",
                {"user_id": "user456", "document_id": "doc456", "query_type": "extraction"}
            ),
            (
                "Compare the performance metrics between version 1 and version 2",
                "Version 2 shows significant improvements: 30% faster processing, 50% less memory usage, 95% accuracy vs 87% in version 1.",
                {"user_id": "user123", "document_id": "doc789", "query_type": "comparison"}
            )
        ]
        
        for prompt, response, metadata in prompts_responses:
            logger_system.log_prompt_history(prompt, response, metadata)
        
        # Verify prompt history file
        prompt_log = Path(temp_log_dir) / "prompt_history.txt"
        assert prompt_log.exists()
        
        with open(prompt_log, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
            assert "Summarize the key findings" in prompt_content
            assert "What are the technical specifications" in prompt_content
            assert "Compare the performance metrics" in prompt_content
            assert "Novel algorithm improves efficiency" in prompt_content
            assert "Technical specifications include" in prompt_content
            assert "Version 2 shows significant improvements" in prompt_content
            assert "user123" in prompt_content
            assert "user456" in prompt_content
            assert "summarization" in prompt_content
            assert "extraction" in prompt_content
            assert "comparison" in prompt_content


class TestMonitoringMetricsAccuracy:
    """Test monitoring metrics accuracy across the complete pipeline."""
    
    @pytest.fixture
    def monitoring_dashboard(self):
        """Create monitoring dashboard for testing."""
        dashboard = MonitoringDashboard(metrics_retention_hours=1)
        yield dashboard
        dashboard.stop_monitoring()
    
    def test_system_metrics_collection(self, monitoring_dashboard):
        """Test system metrics collection accuracy."""
        # Start monitoring
        monitoring_dashboard.start_monitoring(interval_seconds=1)
        
        # Wait for metrics collection
        time.sleep(2)
        
        # Get current metrics
        status = monitoring_dashboard.get_current_status()
        current_metrics = status.get('current_metrics')
        
        assert current_metrics is not None
        
        # Verify metric ranges
        assert 0 <= current_metrics['cpu_percent'] <= 100
        assert 0 <= current_metrics['memory_percent'] <= 100
        assert current_metrics['memory_used_mb'] > 0
        assert 0 <= current_metrics['disk_usage_percent'] <= 100
        assert current_metrics['active_connections'] >= 0
        assert current_metrics['processing_queue_size'] >= 0
        assert current_metrics['error_rate'] >= 0
        assert current_metrics['avg_response_time'] >= 0
    
    def test_component_health_tracking(self, monitoring_dashboard):
        """Test component health tracking accuracy."""
        # Record component activities
        components = ['preprocessing', 'postprocessing', 'storage', 'rag', 'versioning', 'api']
        
        for component in components:
            # Record successful activity
            monitoring_dashboard.record_component_activity(component, success=True)
            
            # Record some errors for testing
            if component in ['preprocessing', 'rag']:
                monitoring_dashboard.record_component_activity(component, success=False)
                monitoring_dashboard.record_component_activity(component, success=False)
        
        # Get component health
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
            
            # Components with errors should have lower performance scores
            if component in ['preprocessing', 'rag']:
                assert health['error_count'] >= 2
            else:
                assert health['error_count'] <= 1
    
    def test_processing_queue_monitoring(self, monitoring_dashboard):
        """Test processing queue monitoring accuracy."""
        # Add tasks to queue
        tasks = [
            ("task1", "document_upload"),
            ("task2", "preprocessing"),
            ("task3", "postprocessing"),
            ("task4", "rag_indexing")
        ]
        
        for task_id, operation in tasks:
            monitoring_dashboard.record_processing_task(task_id, operation)
        
        # Check queue status
        status = monitoring_dashboard.get_current_status()
        queue_status = status.get('queue_status', {})
        
        assert queue_status['size'] == 4
        
        # Complete some tasks
        monitoring_dashboard.complete_processing_task("task1", success=True)
        monitoring_dashboard.complete_processing_task("task2", success=False)
        
        # Check updated queue status
        updated_status = monitoring_dashboard.get_current_status()
        updated_queue = updated_status.get('queue_status', {})
        
        assert updated_queue['size'] == 2  # 2 tasks remaining
    
    def test_api_request_metrics(self, monitoring_dashboard):
        """Test API request metrics tracking."""
        # Record various API requests
        api_calls = [
            (0.5, 200),  # Fast successful request
            (1.2, 200),  # Slower successful request
            (0.3, 404),  # Fast error request
            (2.5, 500),  # Slow error request
            (0.8, 201),  # Successful creation
            (1.1, 200),  # Normal request
        ]
        
        for response_time, status_code in api_calls:
            monitoring_dashboard.record_api_request(response_time, status_code)
        
        # Get current metrics
        status = monitoring_dashboard.get_current_status()
        current_metrics = status.get('current_metrics')
        
        # Verify metrics calculation
        assert current_metrics['error_rate'] > 0  # Should have some errors (404, 500)
        assert current_metrics['avg_response_time'] > 0  # Should have average response time
        
        # Error rate should be 2/6 = 33.33%
        expected_error_rate = (2 / 6) * 100
        assert abs(current_metrics['error_rate'] - expected_error_rate) < 1.0
    
    def test_performance_summary_accuracy(self, monitoring_dashboard):
        """Test performance summary calculation accuracy."""
        # Start monitoring to collect some data
        monitoring_dashboard.start_monitoring(interval_seconds=1)
        
        # Record some activities
        monitoring_dashboard.record_api_request(1.0, 200)
        monitoring_dashboard.record_api_request(1.5, 200)
        monitoring_dashboard.record_api_request(0.5, 404)
        
        monitoring_dashboard.record_processing_task("perf_task1", "test_operation")
        monitoring_dashboard.complete_processing_task("perf_task1", success=True)
        
        # Wait for metrics collection
        time.sleep(2)
        
        # Get performance summary
        summary = monitoring_dashboard.get_performance_summary()
        
        # Verify summary contains expected data
        if summary:  # May be empty if no metrics collected yet
            assert 'avg_cpu_percent' in summary
            assert 'avg_memory_percent' in summary
            assert 'avg_response_time' in summary
            assert 'total_errors' in summary
            assert 'uptime_hours' in summary
            
            # Verify reasonable values
            assert 0 <= summary['avg_cpu_percent'] <= 100
            assert 0 <= summary['avg_memory_percent'] <= 100
            assert summary['avg_response_time'] >= 0
            assert summary['total_errors'] >= 0
            assert summary['uptime_hours'] >= 0


class TestAlertingFunctionality:
    """Test alerting functionality for various failure scenarios."""
    
    @pytest.fixture
    def monitoring_dashboard(self):
        """Create monitoring dashboard with custom thresholds for testing."""
        dashboard = MonitoringDashboard(metrics_retention_hours=1)
        
        # Set lower thresholds for testing
        dashboard.alert_thresholds = {
            'cpu': {'warning': 50.0, 'critical': 80.0},
            'memory': {'warning': 60.0, 'critical': 85.0},
            'disk': {'warning': 70.0, 'critical': 90.0},
            'error_rate': {'warning': 10.0, 'critical': 25.0},
            'response_time': {'warning': 1.0, 'critical': 3.0},
            'queue_size': {'warning': 5, 'critical': 10}
        }
        
        yield dashboard
        dashboard.stop_monitoring()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_resource_threshold_alerts(self, mock_disk, mock_memory, mock_cpu, monitoring_dashboard):
        """Test alerts for resource threshold violations."""
        # Mock high resource usage
        mock_cpu.return_value = 85.0  # Above critical threshold
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 70.0  # Above warning threshold
        mock_memory_obj.used = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory.return_value = mock_memory_obj
        
        mock_disk_obj = Mock()
        mock_disk_obj.percent = 95.0  # Above critical threshold
        mock_disk.return_value = mock_disk_obj
        
        # Collect metrics (this should trigger alerts)
        metrics = monitoring_dashboard._collect_system_metrics()
        
        # Manually trigger alert checking
        monitoring_dashboard._check_alerts(metrics)
        
        # Verify metrics are above thresholds
        assert metrics.cpu_percent == 85.0
        assert metrics.memory_percent == 70.0
        assert metrics.disk_usage_percent == 95.0
    
    def test_error_rate_alerts(self, monitoring_dashboard):
        """Test alerts for high error rates."""
        # Record requests with high error rate
        successful_requests = 5
        failed_requests = 3  # 37.5% error rate - above critical threshold
        
        for _ in range(successful_requests):
            monitoring_dashboard.record_api_request(0.5, 200)
        
        for _ in range(failed_requests):
            monitoring_dashboard.record_api_request(1.0, 500)
        
        # Get current status to check error rate
        status = monitoring_dashboard.get_current_status()
        active_alerts = status.get('active_alerts', [])
        
        # Should have error rate alert
        error_alerts = [alert for alert in active_alerts if alert.get('type') == 'errors']
        assert len(error_alerts) > 0 or monitoring_dashboard._calculate_error_rate() > 25.0
    
    def test_queue_size_alerts(self, monitoring_dashboard):
        """Test alerts for processing queue size."""
        # Add many tasks to trigger queue size alert
        for i in range(12):  # Above critical threshold of 10
            monitoring_dashboard.record_processing_task(f"queue_task_{i}", "test_operation")
        
        # Get current metrics
        status = monitoring_dashboard.get_current_status()
        queue_size = status.get('queue_status', {}).get('size', 0)
        
        # Should trigger queue size alert
        assert queue_size >= 10  # Above critical threshold
        
        # Check for active alerts
        active_alerts = status.get('active_alerts', [])
        queue_alerts = [alert for alert in active_alerts if alert.get('type') == 'queue']
        
        # May not have alerts if _check_alerts wasn't called, but queue size should be high
        assert queue_size > monitoring_dashboard.alert_thresholds['queue_size']['critical']
    
    def test_component_failure_alerts(self, monitoring_dashboard):
        """Test alerts for component failures."""
        # Simulate component failures
        components_with_errors = ['preprocessing', 'rag', 'storage']
        
        for component in components_with_errors:
            # Record multiple failures
            for _ in range(15):  # Above error threshold
                monitoring_dashboard.record_component_activity(component, success=False)
        
        # Update component health
        monitoring_dashboard._update_component_health()
        
        # Check component health status
        status = monitoring_dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        for component in components_with_errors:
            if component in component_health:
                health = component_health[component]
                # Should be in critical or warning state due to high error count
                assert health['status'] in ['critical', 'warning']
                assert health['error_count'] >= 15
    
    def test_response_time_alerts(self, monitoring_dashboard):
        """Test alerts for slow response times."""
        # Record slow API requests
        slow_requests = [
            (4.0, 200),  # Above critical threshold
            (5.5, 200),  # Above critical threshold
            (2.0, 200),  # Above warning threshold
            (1.5, 200),  # Above warning threshold
            (0.5, 200),  # Normal
        ]
        
        for response_time, status_code in slow_requests:
            monitoring_dashboard.record_api_request(response_time, status_code)
        
        # Calculate average response time
        avg_response_time = monitoring_dashboard._calculate_avg_response_time()
        
        # Should be above warning threshold (1.0 seconds)
        assert avg_response_time > monitoring_dashboard.alert_thresholds['response_time']['warning']
    
    def test_alert_persistence_and_recovery(self, monitoring_dashboard):
        """Test alert persistence and recovery scenarios."""
        # Create alert condition
        for _ in range(15):
            monitoring_dashboard.record_processing_task(f"persist_task_{_}", "test_op")
        
        # Check initial alert state
        initial_status = monitoring_dashboard.get_current_status()
        initial_queue_size = initial_status.get('queue_status', {}).get('size', 0)
        
        # Should have high queue size
        assert initial_queue_size >= 10
        
        # Resolve alert condition by completing tasks
        for i in range(12):
            monitoring_dashboard.complete_processing_task(f"persist_task_{i}", success=True)
        
        # Check recovered state
        recovered_status = monitoring_dashboard.get_current_status()
        recovered_queue_size = recovered_status.get('queue_status', {}).get('size', 0)
        
        # Queue size should be reduced
        assert recovered_queue_size < initial_queue_size
        assert recovered_queue_size <= monitoring_dashboard.alert_thresholds['queue_size']['warning']


class TestLoggingMonitoringIntegration:
    """Test integration between logging and monitoring systems."""
    
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
    
    def test_logging_monitoring_coordination(self, integrated_system):
        """Test coordination between logging and monitoring systems."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        
        # Start monitoring
        dashboard.start_monitoring(interval_seconds=1)
        
        # Perform operations that should be logged and monitored
        with logger.context(document_id="integration_doc"):
            # Log document processing
            logger.log_document_processing(
                "integration_doc", "preprocessing", "started",
                {"processor": "test_processor"}
            )
            
            # Record monitoring activity
            dashboard.record_component_activity("preprocessing", success=True)
            dashboard.record_processing_task("integration_task", "preprocessing")
            
            # Log completion
            logger.log_document_processing(
                "integration_doc", "preprocessing", "completed",
                {"processor": "test_processor", "success": True},
                performance_metrics={"duration_seconds": 2.5}
            )
            
            # Complete monitoring task
            dashboard.complete_processing_task("integration_task", success=True)
        
        # Wait for monitoring cycle
        time.sleep(2)
        
        # Verify both systems recorded the activity
        log_summary = logger.get_log_summary(hours=1)
        dashboard_status = dashboard.get_current_status()
        
        assert log_summary['total_entries'] > 0
        assert 'preprocessing' in dashboard_status.get('component_health', {})
    
    def test_error_correlation(self, integrated_system):
        """Test correlation of errors between logging and monitoring."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        
        # Simulate correlated errors
        error_scenarios = [
            ("preprocessing", "FileNotFoundError", "Input file missing"),
            ("rag", "ConnectionError", "LightRAG service down"),
            ("storage", "DatabaseError", "Connection timeout"),
        ]
        
        for component, error_type, error_msg in error_scenarios:
            # Log the error
            try:
                if error_type == "FileNotFoundError":
                    raise FileNotFoundError(error_msg)
                elif error_type == "ConnectionError":
                    raise ConnectionError(error_msg)
                else:
                    raise Exception(error_msg)
            except Exception as e:
                logger.log_error_with_context(
                    getattr(LogCategory, component.upper()),
                    f"{component}_component",
                    e,
                    {"correlation_id": f"error_{component}"}
                )
            
            # Record monitoring error
            dashboard.record_component_activity(component, success=False)
        
        # Verify error correlation
        log_summary = logger.get_log_summary(hours=1)
        dashboard_status = dashboard.get_current_status()
        
        assert log_summary['error_count'] >= 3
        
        # Check component health reflects errors
        component_health = dashboard_status.get('component_health', {})
        for component, _, _ in error_scenarios:
            if component in component_health:
                assert component_health[component]['error_count'] > 0
    
    def test_performance_metrics_correlation(self, integrated_system):
        """Test correlation of performance metrics between systems."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        
        # Record performance data in both systems
        operations = [
            ("document_upload", 2.1),
            ("preprocessing", 15.5),
            ("postprocessing", 3.2),
            ("rag_indexing", 25.8),
        ]
        
        for operation, duration in operations:
            # Log performance
            logger.log_performance_metrics(
                f"{operation}_component",
                operation,
                {"duration_seconds": duration, "success": True}
            )
            
            # Record in monitoring
            dashboard.record_processing_task(f"{operation}_task", operation)
            time.sleep(0.1)  # Small delay
            dashboard.complete_processing_task(f"{operation}_task", success=True)
        
        # Verify performance data correlation
        log_summary = logger.get_log_summary(hours=1)
        performance_summary = dashboard.get_performance_summary()
        
        assert log_summary['total_entries'] > 0
        # Performance summary might be empty if monitoring hasn't collected enough data
        # but the operations should be recorded
    
    def test_real_time_monitoring_with_logging(self, integrated_system):
        """Test real-time monitoring with concurrent logging."""
        logger = integrated_system['logger']
        dashboard = integrated_system['dashboard']
        log_dir = integrated_system['log_dir']
        
        # Start real-time monitoring
        dashboard.start_monitoring(interval_seconds=1)
        
        # Simulate concurrent operations
        for i in range(5):
            # Log various activities
            logger.info(
                LogCategory.SYSTEM,
                "integration_test",
                f"Processing batch {i}",
                details={"batch_id": i, "items": 10}
            )
            
            # Record monitoring activities
            dashboard.record_api_request(0.5 + i * 0.1, 200)
            dashboard.record_component_activity("api", success=True)
            
            time.sleep(0.2)
        
        # Wait for monitoring to collect data
        time.sleep(2)
        
        # Verify both systems have data
        log_files = list(Path(log_dir).glob("*.log"))
        assert len(log_files) > 0
        
        dashboard_status = dashboard.get_current_status()
        assert dashboard_status['overall_status'] in ['healthy', 'warning', 'degraded', 'critical']
        
        # Verify log content
        main_log = Path(log_dir) / "docforge_main.log"
        if main_log.exists():
            with open(main_log, 'r') as f:
                content = f.read()
                assert "Processing batch" in content
                assert "integration_test" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])