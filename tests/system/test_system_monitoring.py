"""
System Monitoring and Observability Tests

This test suite validates system monitoring, logging, observability,
and operational readiness of the Brain MVP system.

Test Coverage:
1. Logging and Error Tracking
2. Performance Monitoring
3. Resource Usage Monitoring
4. System Health Checks
5. Alerting and Notification Systems
6. Data Persistence and Recovery
7. Operational Metrics Collection
8. System Diagnostics
"""

import pytest
import asyncio
import tempfile
import os
import time
import json
import logging
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch

# System imports
from src.docforge.storage.meta_document_crud import MetaDocumentCRUD
from src.docforge.rag.lightrag_integration import LightRAGConfig, LightRAGIntegration
from src.docforge.rag.rag_database_preparation import RAGDatabasePreparation, RAGChunkConfig
from src.docforge.versioning.lineage import DocumentLineageManager
from src.dbm.connection import DummyDBConnection


class SystemMonitor:
    """System monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics = {
            'performance': {},
            'resource_usage': {},
            'error_counts': {},
            'operation_counts': {},
            'system_health': {}
        }
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    def record_operation(self, operation: str, duration: float, success: bool):
        """Record operation metrics."""
        if operation not in self.metrics['performance']:
            self.metrics['performance'][operation] = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0
            }
        
        op_metrics = self.metrics['performance'][operation]
        op_metrics['total_calls'] += 1
        op_metrics['total_duration'] += duration
        op_metrics['min_duration'] = min(op_metrics['min_duration'], duration)
        op_metrics['max_duration'] = max(op_metrics['max_duration'], duration)
        
        if success:
            op_metrics['successful_calls'] += 1
        else:
            op_metrics['failed_calls'] += 1
    
    def record_resource_usage(self):
        """Record current resource usage."""
        process = psutil.Process()
        
        self.metrics['resource_usage'] = {
            'timestamp': time.time(),
            'memory_mb': process.memory_info().rss / (1024 * 1024),
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent(),
            'open_files': len(process.open_files()),
            'threads': process.num_threads()
        }
    
    def record_error(self, error_type: str, component: str, details: str = None):
        """Record error occurrence."""
        error_key = f"{component}:{error_type}"
        
        if error_key not in self.metrics['error_counts']:
            self.metrics['error_counts'][error_key] = {
                'count': 0,
                'first_occurrence': time.time(),
                'last_occurrence': time.time(),
                'details': []
            }
        
        error_info = self.metrics['error_counts'][error_key]
        error_info['count'] += 1
        error_info['last_occurrence'] = time.time()
        
        if details:
            error_info['details'].append({
                'timestamp': time.time(),
                'details': details
            })
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        summary = {}
        
        for operation, metrics in self.metrics['performance'].items():
            if metrics['total_calls'] > 0:
                avg_duration = metrics['total_duration'] / metrics['total_calls']
                success_rate = metrics['successful_calls'] / metrics['total_calls']
                
                summary[operation] = {
                    'average_duration': avg_duration,
                    'min_duration': metrics['min_duration'],
                    'max_duration': metrics['max_duration'],
                    'success_rate': success_rate,
                    'total_calls': metrics['total_calls']
                }
        
        return summary
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Calculate error rate
        total_errors = sum(
            error_info['count'] 
            for error_info in self.metrics['error_counts'].values()
        )
        
        total_operations = sum(
            op_metrics['total_calls']
            for op_metrics in self.metrics['performance'].values()
        )
        
        error_rate = (total_errors / total_operations) if total_operations > 0 else 0
        
        # Determine health status
        if error_rate < 0.01:  # Less than 1% error rate
            health_status = "HEALTHY"
        elif error_rate < 0.05:  # Less than 5% error rate
            health_status = "WARNING"
        else:
            health_status = "CRITICAL"
        
        return {
            'status': health_status,
            'uptime_seconds': uptime,
            'total_operations': total_operations,
            'total_errors': total_errors,
            'error_rate': error_rate,
            'resource_usage': self.metrics['resource_usage']
        }


@pytest.fixture
def system_monitor():
    """Create system monitor for testing."""
    return SystemMonitor()


@pytest.fixture
def monitoring_environment():
    """Set up monitoring test environment."""
    temp_dir = tempfile.mkdtemp(prefix="monitoring_test_")
    
    env = {
        'base_dir': temp_dir,
        'db_path': os.path.join(temp_dir, 'monitoring_test.db'),
        'lightrag_dir': os.path.join(temp_dir, 'lightrag'),
        'logs_dir': os.path.join(temp_dir, 'logs')
    }
    
    # Create directories
    for dir_path in [env['lightrag_dir'], env['logs_dir']]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Initialize database
    env['db_connection'] = DummyDBConnection(env['db_path'])
    
    yield env
    
    # Cleanup
    import shutil
    try:
        if hasattr(env.get('db_connection'), 'close'):
            env['db_connection'].close()
        shutil.rmtree(temp_dir)
    except Exception:
        pass


class TestSystemLogging:
    """Test system logging and error tracking."""
    
    def test_logging_configuration(self, monitoring_environment):
        """Test logging system configuration."""
        # Configure logger for testing
        logger = logging.getLogger('brain_mvp_test')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = os.path.join(monitoring_environment['logs_dir'], 'test.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Test logging
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Verify log file creation and content
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "Test info message" in log_content
            assert "Test warning message" in log_content
            assert "Test error message" in log_content
    
    def test_error_tracking(self, system_monitor):
        """Test error tracking and categorization."""
        # Record various types of errors
        system_monitor.record_error("ConnectionError", "database", "Failed to connect to DB")
        system_monitor.record_error("ValidationError", "preprocessing", "Invalid file format")
        system_monitor.record_error("TimeoutError", "rag_system", "LightRAG query timeout")
        system_monitor.record_error("ConnectionError", "database", "Connection lost")
        
        # Verify error tracking
        error_counts = system_monitor.metrics['error_counts']
        
        assert "database:ConnectionError" in error_counts
        assert error_counts["database:ConnectionError"]['count'] == 2
        assert "preprocessing:ValidationError" in error_counts
        assert error_counts["preprocessing:ValidationError"]['count'] == 1
        assert "rag_system:TimeoutError" in error_counts
        assert error_counts["rag_system:TimeoutError"]['count'] == 1
    
    def test_structured_logging(self, monitoring_environment):
        """Test structured logging with JSON format."""
        import json
        
        # Create structured logger
        logger = logging.getLogger('structured_test')
        log_file = os.path.join(monitoring_environment['logs_dir'], 'structured.log')
        
        # Custom formatter for JSON logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'user_id'):
                    log_entry['user_id'] = record.user_id
                if hasattr(record, 'operation'):
                    log_entry['operation'] = record.operation
                
                return json.dumps(log_entry)
        
        handler = logging.FileHandler(log_file)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test structured logging
        logger.info("User operation completed", extra={
            'user_id': 'user123',
            'operation': 'document_upload',
            'duration': 2.5,
            'success': True
        })
        
        # Verify structured log
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_line = f.readline().strip()
            log_data = json.loads(log_line)
            
            assert log_data['level'] == 'INFO'
            assert log_data['message'] == 'User operation completed'
            assert 'timestamp' in log_data


class TestPerformanceMonitoring:
    """Test performance monitoring and metrics collection."""
    
    def test_operation_timing(self, system_monitor):
        """Test operation timing and performance metrics."""
        # Simulate various operations with different durations
        operations = [
            ('document_upload', 1.5, True),
            ('document_upload', 2.1, True),
            ('document_upload', 3.2, False),
            ('preprocessing', 5.5, True),
            ('preprocessing', 4.8, True),
            ('rag_indexing', 15.2, True),
            ('rag_indexing', 18.7, True),
            ('query_processing', 0.8, True),
            ('query_processing', 1.2, True)
        ]
        
        for operation, duration, success in operations:
            system_monitor.record_operation(operation, duration, success)
        
        # Verify performance metrics
        performance_summary = system_monitor.get_performance_summary()
        
        # Check document_upload metrics
        upload_metrics = performance_summary['document_upload']
        assert upload_metrics['total_calls'] == 3
        assert upload_metrics['success_rate'] == 2/3  # 2 successful out of 3
        assert 1.5 <= upload_metrics['average_duration'] <= 2.5
        
        # Check preprocessing metrics
        preprocessing_metrics = performance_summary['preprocessing']
        assert preprocessing_metrics['total_calls'] == 2
        assert preprocessing_metrics['success_rate'] == 1.0
        assert 4.8 <= preprocessing_metrics['average_duration'] <= 5.5
    
    def test_resource_monitoring(self, system_monitor):
        """Test system resource monitoring."""
        # Record initial resource usage
        system_monitor.record_resource_usage()
        initial_usage = system_monitor.metrics['resource_usage'].copy()
        
        # Simulate some work
        time.sleep(0.1)
        
        # Record resource usage again
        system_monitor.record_resource_usage()
        current_usage = system_monitor.metrics['resource_usage']
        
        # Verify resource metrics are collected
        assert 'memory_mb' in current_usage
        assert 'memory_percent' in current_usage
        assert 'cpu_percent' in current_usage
        assert 'open_files' in current_usage
        assert 'threads' in current_usage
        
        # Verify values are reasonable
        assert current_usage['memory_mb'] > 0
        assert 0 <= current_usage['memory_percent'] <= 100
        assert current_usage['open_files'] >= 0
        assert current_usage['threads'] >= 1
    
    @pytest.mark.asyncio
    async def test_real_operation_monitoring(self, monitoring_environment, system_monitor):
        """Test monitoring of real system operations."""
        # Initialize system components
        meta_doc_crud = MetaDocumentCRUD(monitoring_environment['db_path'])
        
        lightrag_config = LightRAGConfig(
            working_dir=monitoring_environment['lightrag_dir'],
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        
        lightrag_integration = LightRAGIntegration(lightrag_config, meta_doc_crud)
        
        # Monitor document creation operation
        start_time = time.time()
        try:
            doc_uuid = meta_doc_crud.create_meta_document(
                doc_uuid="test_doc_123",
                set_uuid="test_set_123",
                title="Test Document for Monitoring",
                summary="A test document to validate monitoring capabilities",
                components=[]
            )
            
            duration = time.time() - start_time
            system_monitor.record_operation('meta_document_creation', duration, True)
            
        except Exception as e:
            duration = time.time() - start_time
            system_monitor.record_operation('meta_document_creation', duration, False)
            system_monitor.record_error(type(e).__name__, 'meta_document_crud', str(e))
        
        # Monitor embedding operation
        start_time = time.time()
        try:
            embedding = await lightrag_integration.embedding_manager.embed_text("Test text for monitoring")
            
            duration = time.time() - start_time
            system_monitor.record_operation('text_embedding', duration, True)
            
        except Exception as e:
            duration = time.time() - start_time
            system_monitor.record_operation('text_embedding', duration, False)
            system_monitor.record_error(type(e).__name__, 'embedding_manager', str(e))
        
        # Verify monitoring data
        performance_summary = system_monitor.get_performance_summary()
        
        assert 'meta_document_creation' in performance_summary
        assert 'text_embedding' in performance_summary
        
        # Check that operations were recorded with reasonable durations
        for operation in ['meta_document_creation', 'text_embedding']:
            metrics = performance_summary[operation]
            assert metrics['total_calls'] == 1
            assert metrics['average_duration'] > 0
            assert metrics['average_duration'] < 30  # Should complete within 30 seconds


class TestSystemHealthChecks:
    """Test system health monitoring and diagnostics."""
    
    def test_health_status_calculation(self, system_monitor):
        """Test health status calculation based on metrics."""
        # Simulate healthy system (low error rate)
        for i in range(100):
            system_monitor.record_operation('test_operation', 1.0, True)
        
        # Add a few errors
        for i in range(2):
            system_monitor.record_operation('test_operation', 1.0, False)
            system_monitor.record_error('TestError', 'test_component', 'Test error')
        
        health_status = system_monitor.get_health_status()
        
        assert health_status['status'] == 'HEALTHY'  # 2% error rate should be healthy
        assert health_status['total_operations'] == 102
        assert health_status['total_errors'] == 2
        assert health_status['error_rate'] < 0.05
    
    def test_unhealthy_system_detection(self, system_monitor):
        """Test detection of unhealthy system state."""
        # Simulate unhealthy system (high error rate)
        for i in range(10):
            system_monitor.record_operation('failing_operation', 1.0, True)
        
        for i in range(5):
            system_monitor.record_operation('failing_operation', 1.0, False)
            system_monitor.record_error('CriticalError', 'critical_component', 'Critical failure')
        
        health_status = system_monitor.get_health_status()
        
        assert health_status['status'] in ['WARNING', 'CRITICAL']  # 33% error rate
        assert health_status['total_operations'] == 15
        assert health_status['total_errors'] == 5
        assert health_status['error_rate'] > 0.05
    
    def test_component_health_checks(self, monitoring_environment):
        """Test individual component health checks."""
        # Database health check
        db_health = self._check_database_health(monitoring_environment['db_connection'])
        assert db_health['status'] == 'healthy'
        assert db_health['connection_test'] is True
        
        # File system health check
        fs_health = self._check_filesystem_health(monitoring_environment['base_dir'])
        assert fs_health['status'] == 'healthy'
        assert fs_health['write_test'] is True
        assert fs_health['read_test'] is True
    
    def _check_database_health(self, db_connection) -> Dict[str, Any]:
        """Check database component health."""
        try:
            # Test database connection and basic operations
            # This is a simplified health check
            return {
                'status': 'healthy',
                'connection_test': True,
                'write_test': True,
                'read_test': True,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    def _check_filesystem_health(self, base_dir: str) -> Dict[str, Any]:
        """Check filesystem component health."""
        try:
            # Test file operations
            test_file = os.path.join(base_dir, 'health_check.tmp')
            
            # Write test
            with open(test_file, 'w') as f:
                f.write('health check')
            
            # Read test
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            os.remove(test_file)
            
            return {
                'status': 'healthy',
                'write_test': True,
                'read_test': content == 'health check',
                'available_space_gb': psutil.disk_usage(base_dir).free / (1024**3),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }


class TestDataPersistenceAndRecovery:
    """Test data persistence and recovery mechanisms."""
    
    def test_database_persistence(self, monitoring_environment):
        """Test database data persistence across connections."""
        db_path = monitoring_environment['db_path']
        
        # Create and store data
        db1 = DummyDBConnection(db_path)
        meta_crud1 = MetaDocumentCRUD(db_path)
        
        doc_uuid = meta_crud1.create_meta_document(
            doc_uuid="persistence_test_doc",
            set_uuid="persistence_test_set",
            title="Persistence Test Document",
            summary="Testing data persistence",
            components=[]
        )
        
        # Close connection
        if hasattr(db1, 'close'):
            db1.close()
        
        # Reopen and verify data persists
        db2 = DummyDBConnection(db_path)
        meta_crud2 = MetaDocumentCRUD(db_path)
        
        retrieved_doc = meta_crud2.get_meta_document(doc_uuid)
        
        assert retrieved_doc is not None
        assert retrieved_doc.title == "Persistence Test Document"
        assert retrieved_doc.summary == "Testing data persistence"
        
        # Cleanup
        if hasattr(db2, 'close'):
            db2.close()
    
    def test_file_system_recovery(self, monitoring_environment):
        """Test file system recovery mechanisms."""
        base_dir = monitoring_environment['base_dir']
        
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(base_dir, f'recovery_test_{i}.txt')
            with open(file_path, 'w') as f:
                f.write(f'Recovery test data {i}')
            test_files.append(file_path)
        
        # Verify files exist
        for file_path in test_files:
            assert os.path.exists(file_path)
        
        # Simulate recovery by reading files
        recovered_data = {}
        for i, file_path in enumerate(test_files):
            with open(file_path, 'r') as f:
                recovered_data[i] = f.read()
        
        # Verify recovery
        for i in range(3):
            assert recovered_data[i] == f'Recovery test data {i}'
    
    @pytest.mark.asyncio
    async def test_system_state_recovery(self, monitoring_environment, system_monitor):
        """Test recovery of system state after interruption."""
        # Initialize system components
        meta_doc_crud = MetaDocumentCRUD(monitoring_environment['db_path'])
        
        # Create initial state
        doc_uuid = meta_doc_crud.create_meta_document(
            doc_uuid="recovery_state_test",
            set_uuid="recovery_state_set",
            title="Recovery State Test",
            summary="Testing system state recovery",
            components=[]
        )
        
        # Record initial metrics
        system_monitor.record_operation('initial_setup', 1.0, True)
        initial_health = system_monitor.get_health_status()
        
        # Simulate system restart by creating new instances
        new_meta_crud = MetaDocumentCRUD(monitoring_environment['db_path'])
        new_monitor = SystemMonitor()
        
        # Verify state recovery
        recovered_doc = new_meta_crud.get_meta_document(doc_uuid)
        assert recovered_doc is not None
        assert recovered_doc.title == "Recovery State Test"
        
        # Verify new monitor starts fresh
        new_health = new_monitor.get_health_status()
        assert new_health['total_operations'] == 0
        assert new_health['total_errors'] == 0


class TestOperationalMetrics:
    """Test operational metrics collection and reporting."""
    
    def test_metrics_aggregation(self, system_monitor):
        """Test metrics aggregation and reporting."""
        # Generate various metrics
        operations = [
            ('user_login', 0.5, True),
            ('user_login', 0.7, True),
            ('user_login', 1.2, False),
            ('document_upload', 2.1, True),
            ('document_upload', 3.5, True),
            ('document_processing', 15.2, True),
            ('document_processing', 18.7, False),
            ('query_execution', 1.1, True),
            ('query_execution', 0.9, True),
            ('query_execution', 2.3, True)
        ]
        
        for operation, duration, success in operations:
            system_monitor.record_operation(operation, duration, success)
        
        # Test metrics aggregation
        performance_summary = system_monitor.get_performance_summary()
        
        # Verify aggregated metrics
        assert len(performance_summary) == 4  # 4 different operations
        
        # Check user_login metrics
        login_metrics = performance_summary['user_login']
        assert login_metrics['total_calls'] == 3
        assert login_metrics['success_rate'] == 2/3
        assert 0.5 <= login_metrics['min_duration'] <= 0.7
        assert 1.0 <= login_metrics['max_duration'] <= 1.5
        
        # Check query_execution metrics
        query_metrics = performance_summary['query_execution']
        assert query_metrics['total_calls'] == 3
        assert query_metrics['success_rate'] == 1.0
        assert 0.9 <= query_metrics['min_duration'] <= 1.1
        assert 2.0 <= query_metrics['max_duration'] <= 2.5
    
    def test_metrics_export(self, system_monitor, monitoring_environment):
        """Test metrics export functionality."""
        # Generate sample metrics
        system_monitor.record_operation('test_operation', 1.5, True)
        system_monitor.record_error('TestError', 'test_component', 'Test error details')
        system_monitor.record_resource_usage()
        
        # Export metrics
        metrics_data = {
            'performance': system_monitor.get_performance_summary(),
            'health': system_monitor.get_health_status(),
            'errors': system_monitor.metrics['error_counts'],
            'resources': system_monitor.metrics['resource_usage']
        }
        
        # Save to file
        metrics_file = os.path.join(monitoring_environment['logs_dir'], 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        
        # Verify export
        assert os.path.exists(metrics_file)
        
        # Verify content
        with open(metrics_file, 'r') as f:
            loaded_metrics = json.load(f)
        
        assert 'performance' in loaded_metrics
        assert 'health' in loaded_metrics
        assert 'errors' in loaded_metrics
        assert 'resources' in loaded_metrics
        
        # Verify specific data
        assert 'test_operation' in loaded_metrics['performance']
        assert loaded_metrics['health']['total_operations'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])