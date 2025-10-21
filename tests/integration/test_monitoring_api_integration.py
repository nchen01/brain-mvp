"""
Integration tests for monitoring API endpoints.

This test suite validates:
- Monitoring API endpoint functionality
- Real-time monitoring data accuracy
- Alert system integration with API
- Performance metrics API responses
- Health check endpoint reliability
"""

import pytest
import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from api.app import app
from utils.monitoring_dashboard import get_dashboard
from utils.logging_system import setup_logging


class TestMonitoringAPIEndpoints:
    """Test monitoring API endpoints functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def monitoring_setup(self):
        """Set up monitoring system for testing."""
        # Start monitoring
        dashboard = get_dashboard()
        dashboard.start_monitoring(interval_seconds=1)
        
        # Record some initial activity
        dashboard.record_api_request(0.5, 200)
        dashboard.record_component_activity("api", success=True)
        dashboard.record_processing_task("test_task", "test_operation")
        
        yield dashboard
        
        # Cleanup
        dashboard.stop_monitoring()
    
    def test_health_check_endpoint(self, client, monitoring_setup):
        """Test health check endpoint."""
        response = client.get("/api/v1/monitoring/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "components" in data
        assert "details" in data
        
        # Verify data types and values
        assert isinstance(data["status"], str)
        assert data["status"] in ["healthy", "warning", "degraded", "critical", "unknown"]
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["components"], dict)
    
    def test_simple_health_check_endpoint(self, client):
        """Test simple health check endpoint."""
        response = client.get("/api/v1/monitoring/health/simple")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["service"] == "docforge-brain-mvp"
    
    def test_system_metrics_endpoint(self, client, monitoring_setup):
        """Test system metrics endpoint."""
        # Wait for metrics collection
        time.sleep(2)
        
        response = client.get("/api/v1/monitoring/metrics")
        
        # May return 503 if metrics not available yet
        if response.status_code == 200:
            data = response.json()
            
            # Verify required fields
            required_fields = [
                "timestamp", "cpu_percent", "memory_percent", "memory_used_mb",
                "disk_usage_percent", "active_connections", "processing_queue_size",
                "error_rate", "avg_response_time"
            ]
            
            for field in required_fields:
                assert field in data
            
            # Verify data ranges
            assert 0 <= data["cpu_percent"] <= 100
            assert 0 <= data["memory_percent"] <= 100
            assert data["memory_used_mb"] >= 0
            assert 0 <= data["disk_usage_percent"] <= 100
            assert data["active_connections"] >= 0
            assert data["processing_queue_size"] >= 0
            assert data["error_rate"] >= 0
            assert data["avg_response_time"] >= 0
        else:
            assert response.status_code == 503
    
    def test_metrics_history_endpoint(self, client, monitoring_setup):
        """Test metrics history endpoint."""
        # Wait for some metrics collection
        time.sleep(2)
        
        response = client.get("/api/v1/monitoring/metrics/history?hours=1")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "time_period_hours" in data
        assert "data_points" in data
        assert "metrics" in data
        
        assert data["time_period_hours"] == 1
        assert isinstance(data["data_points"], int)
        assert isinstance(data["metrics"], list)
    
    def test_component_health_endpoint(self, client, monitoring_setup):
        """Test component health endpoint."""
        response = client.get("/api/v1/monitoring/components")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check component structure
        if data:
            component = data[0]
            required_fields = [
                "component", "status", "last_activity", "error_count",
                "performance_score", "details"
            ]
            
            for field in required_fields:
                assert field in component
            
            assert component["status"] in ["healthy", "warning", "critical", "unknown"]
            assert isinstance(component["error_count"], int)
            assert isinstance(component["performance_score"], (int, float))
    
    def test_specific_component_endpoint(self, client, monitoring_setup):
        """Test specific component details endpoint."""
        # Test valid component
        response = client.get("/api/v1/monitoring/components/api")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["component"] == "api"
        assert "status" in data
        assert "last_activity" in data
        assert "error_count" in data
        assert "performance_score" in data
        
        # Test invalid component
        response = client.get("/api/v1/monitoring/components/nonexistent")
        assert response.status_code == 404
    
    def test_processing_queue_endpoint(self, client, monitoring_setup):
        """Test processing queue status endpoint."""
        response = client.get("/api/v1/monitoring/queue")
        
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "queue_size", "oldest_task_age_seconds", "active_tasks",
            "completed_tasks_last_hour", "failed_tasks_last_hour",
            "average_processing_time"
        ]
        
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["queue_size"], int)
        assert isinstance(data["oldest_task_age_seconds"], (int, float))
        assert isinstance(data["active_tasks"], list)
        assert data["queue_size"] >= 0
        assert data["oldest_task_age_seconds"] >= 0
    
    def test_alerts_endpoint(self, client, monitoring_setup):
        """Test active alerts endpoint."""
        response = client.get("/api/v1/monitoring/alerts")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check alert structure if any alerts exist
        if data:
            alert = data[0]
            required_fields = ["alert_type", "severity", "message", "timestamp"]
            
            for field in required_fields:
                assert field in alert
            
            assert alert["severity"] in ["warning", "critical"]
    
    def test_performance_summary_endpoint(self, client, monitoring_setup):
        """Test performance summary endpoint."""
        # Wait for metrics collection
        time.sleep(2)
        
        response = client.get("/api/v1/monitoring/performance?hours=1")
        
        # May return 503 if no performance data available yet
        if response.status_code == 200:
            data = response.json()
            
            required_fields = [
                "time_period_hours", "avg_cpu_percent", "avg_memory_percent",
                "avg_response_time", "avg_queue_size", "total_errors",
                "uptime_hours", "requests_per_hour"
            ]
            
            for field in required_fields:
                assert field in data
            
            assert data["time_period_hours"] == 1
            assert data["avg_cpu_percent"] >= 0
            assert data["avg_memory_percent"] >= 0
            assert data["avg_response_time"] >= 0
            assert data["total_errors"] >= 0
            assert data["uptime_hours"] >= 0
        else:
            assert response.status_code == 503
    
    def test_log_summary_endpoint(self, client, monitoring_setup):
        """Test log summary endpoint."""
        response = client.get("/api/v1/monitoring/logs/summary?hours=1")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # For unauthenticated request, should get limited info
        expected_fields = ["time_range", "total_entries", "error_count", "warning_count", "note"]
        
        for field in expected_fields:
            assert field in data
        
        assert isinstance(data["total_entries"], int)
        assert isinstance(data["error_count"], int)
        assert isinstance(data["warning_count"], int)
        assert data["note"] == "Login for detailed log information"
    
    def test_dashboard_data_endpoint(self, client, monitoring_setup):
        """Test comprehensive dashboard data endpoint."""
        # Wait for metrics collection
        time.sleep(2)
        
        response = client.get("/api/v1/monitoring/status/dashboard")
        
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "timestamp", "system_status", "performance_summary",
            "recent_metrics", "uptime_seconds", "version"
        ]
        
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["version"] == "1.0.0"
        assert isinstance(data["system_status"], dict)
    
    def test_component_health_check_trigger(self, client, monitoring_setup):
        """Test manual component health check trigger."""
        response = client.post("/api/v1/monitoring/health/check/api")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["component"] == "api"
        assert "check_timestamp" in data
        assert "triggered_by" in data
        assert "result" in data
        
        # Check result structure
        result = data["result"]
        assert "status" in result
        assert result["status"] == "healthy"
    
    def test_monitoring_control_endpoints_require_auth(self, client):
        """Test that monitoring control endpoints require authentication."""
        # Test start monitoring without auth
        response = client.post("/api/v1/monitoring/monitoring/start")
        assert response.status_code == 403
        
        # Test stop monitoring without auth
        response = client.post("/api/v1/monitoring/monitoring/stop")
        assert response.status_code == 403


class TestMonitoringAPIWithRealData:
    """Test monitoring API with real system data."""
    
    @pytest.fixture
    def client_with_data(self):
        """Create test client with real monitoring data."""
        client = TestClient(app)
        dashboard = get_dashboard()
        
        # Start monitoring
        dashboard.start_monitoring(interval_seconds=1)
        
        # Generate realistic data
        self._generate_realistic_monitoring_data(dashboard)
        
        yield client
        
        # Cleanup
        dashboard.stop_monitoring()
    
    def _generate_realistic_monitoring_data(self, dashboard):
        """Generate realistic monitoring data for testing."""
        # Simulate API requests
        api_requests = [
            (0.2, 200), (0.5, 200), (1.1, 200), (0.3, 201),
            (2.5, 500), (0.8, 404), (1.2, 200), (0.4, 200)
        ]
        
        for response_time, status_code in api_requests:
            dashboard.record_api_request(response_time, status_code)
        
        # Simulate processing tasks
        tasks = [
            ("upload_task_1", "document_upload"),
            ("process_task_1", "preprocessing"),
            ("post_task_1", "postprocessing"),
            ("rag_task_1", "rag_indexing")
        ]
        
        for task_id, operation in tasks:
            dashboard.record_processing_task(task_id, operation)
        
        # Complete some tasks
        dashboard.complete_processing_task("upload_task_1", success=True)
        dashboard.complete_processing_task("process_task_1", success=False)
        
        # Record component activities
        components = ["preprocessing", "postprocessing", "storage", "rag", "api"]
        for component in components:
            dashboard.record_component_activity(component, success=True)
            if component in ["preprocessing", "rag"]:
                dashboard.record_component_activity(component, success=False)
    
    def test_realistic_metrics_endpoint(self, client_with_data):
        """Test metrics endpoint with realistic data."""
        # Wait for metrics collection
        time.sleep(3)
        
        response = client_with_data.get("/api/v1/monitoring/metrics")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have realistic error rate (2 errors out of 8 requests = 25%)
            assert data["error_rate"] > 0
            assert data["error_rate"] <= 100
            
            # Should have realistic response time
            assert data["avg_response_time"] > 0
            assert data["avg_response_time"] < 10  # Should be reasonable
            
            # Should have processing queue
            assert data["processing_queue_size"] >= 0
    
    def test_realistic_component_health(self, client_with_data):
        """Test component health with realistic error data."""
        # Wait for component health updates
        time.sleep(2)
        
        response = client_with_data.get("/api/v1/monitoring/components")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Find components with errors
        components_with_errors = ["preprocessing", "rag"]
        
        for component_data in data:
            component_name = component_data["component"]
            
            if component_name in components_with_errors:
                # Should have error count > 0
                assert component_data["error_count"] > 0
                # Status might be warning or critical
                assert component_data["status"] in ["healthy", "warning", "critical"]
            
            # All components should have reasonable performance scores
            assert 0 <= component_data["performance_score"] <= 100
    
    def test_realistic_queue_status(self, client_with_data):
        """Test queue status with realistic task data."""
        response = client_with_data.get("/api/v1/monitoring/queue")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have some tasks in queue (2 remaining after completions)
        assert data["queue_size"] >= 0
        
        # If there are tasks, oldest task age should be reasonable
        if data["queue_size"] > 0:
            assert data["oldest_task_age_seconds"] >= 0
            assert data["oldest_task_age_seconds"] < 3600  # Less than 1 hour for test
    
    def test_realistic_alerts(self, client_with_data):
        """Test alerts with realistic error conditions."""
        response = client_with_data.get("/api/v1/monitoring/alerts")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # May or may not have alerts depending on thresholds
        # But response should be valid
        assert isinstance(data, list)
        
        for alert in data:
            assert "alert_type" in alert
            assert "severity" in alert
            assert "message" in alert
            assert alert["severity"] in ["warning", "critical"]


class TestMonitoringAPIErrorHandling:
    """Test monitoring API error handling scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_metrics_unavailable_handling(self, client):
        """Test handling when metrics are unavailable."""
        # Stop monitoring to make metrics unavailable
        dashboard = get_dashboard()
        dashboard.stop_monitoring()
        
        response = client.get("/api/v1/monitoring/metrics")
        
        # Should handle gracefully - either return 503 or empty data
        assert response.status_code in [200, 503]
        
        if response.status_code == 503:
            data = response.json()
            assert "detail" in data
    
    def test_invalid_component_handling(self, client):
        """Test handling of invalid component requests."""
        response = client.get("/api/v1/monitoring/components/invalid_component")
        
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "invalid_component" in data["detail"]
    
    def test_invalid_parameters_handling(self, client):
        """Test handling of invalid parameters."""
        # Test invalid hours parameter
        response = client.get("/api/v1/monitoring/metrics/history?hours=0")
        assert response.status_code == 422  # Validation error
        
        response = client.get("/api/v1/monitoring/metrics/history?hours=25")
        assert response.status_code == 422  # Validation error
        
        # Test invalid performance summary hours
        response = client.get("/api/v1/monitoring/performance?hours=0")
        assert response.status_code == 422
        
        response = client.get("/api/v1/monitoring/performance?hours=25")
        assert response.status_code == 422
    
    @patch('src.utils.monitoring_dashboard.MonitoringDashboard.get_current_status')
    def test_monitoring_system_failure_handling(self, mock_get_status, client):
        """Test handling when monitoring system fails."""
        # Mock monitoring system failure
        mock_get_status.side_effect = Exception("Monitoring system failure")
        
        response = client.get("/api/v1/monitoring/health")
        
        # Should return degraded status instead of crashing
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"
        assert "error" in data["details"]
    
    def test_concurrent_requests_handling(self, client):
        """Test handling of concurrent monitoring requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.get("/api/v1/monitoring/health/simple")
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        # All requests should succeed
        assert len(status_codes) == 10
        assert all(code == 200 for code in status_codes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])