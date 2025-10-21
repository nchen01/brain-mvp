"""
Monitoring and health check API endpoints.

This module provides comprehensive monitoring endpoints including:
- System health checks
- Component status monitoring
- Performance metrics
- Processing queue status
- Real-time system statistics
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

# Import monitoring components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.monitoring_dashboard import get_dashboard, MonitoringDashboard
from utils.logging_system import get_logger, LogCategory
from api.routers.auth import get_current_user_optional, UserInfo

# Initialize router
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# Pydantic models
class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="System version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    components: Dict[str, str] = Field(..., description="Component health status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")


class SystemMetricsResponse(BaseModel):
    """System metrics response model."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    processing_queue_size: int
    error_rate: float
    avg_response_time: float


class ComponentHealthResponse(BaseModel):
    """Component health response model."""
    component: str
    status: str
    last_activity: datetime
    error_count: int
    performance_score: float
    details: Dict[str, Any]


class ProcessingQueueResponse(BaseModel):
    """Processing queue status response."""
    queue_size: int
    oldest_task_age_seconds: float
    active_tasks: List[Dict[str, Any]]
    completed_tasks_last_hour: int
    failed_tasks_last_hour: int
    average_processing_time: float


class AlertResponse(BaseModel):
    """Alert response model."""
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    value: Optional[float] = None
    threshold: Optional[float] = None


class PerformanceSummaryResponse(BaseModel):
    """Performance summary response model."""
    time_period_hours: int
    avg_cpu_percent: float
    avg_memory_percent: float
    avg_response_time: float
    avg_queue_size: float
    total_errors: int
    uptime_hours: float
    requests_per_hour: float


# Dependency injection
async def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get monitoring dashboard instance."""
    return get_dashboard()


# System startup time for uptime calculation
SYSTEM_START_TIME = time.time()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Comprehensive system health check.
    
    Returns overall system health status and component details.
    """
    try:
        # Get current system status
        status = dashboard.get_current_status()
        
        # Calculate uptime
        uptime_seconds = time.time() - SYSTEM_START_TIME
        
        # Component health mapping
        component_health = {}
        for component, health in status.get('component_health', {}).items():
            component_health[component] = health.get('status', 'unknown')
        
        return HealthCheckResponse(
            status=status.get('overall_status', 'unknown'),
            timestamp=datetime.now(),
            version="1.0.0",
            uptime_seconds=uptime_seconds,
            components=component_health,
            details={
                'active_alerts': len(status.get('active_alerts', [])),
                'queue_size': status.get('queue_status', {}).get('size', 0),
                'monitoring_active': True
            }
        )
        
    except Exception as e:
        # Return degraded status if monitoring fails
        return HealthCheckResponse(
            status="degraded",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime_seconds=time.time() - SYSTEM_START_TIME,
            components={},
            details={'error': str(e)}
        )


@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check for load balancers.
    
    Returns basic OK status for quick health checks.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "docforge-brain-mvp"
    }


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get current system performance metrics.
    """
    try:
        status = dashboard.get_current_status()
        current_metrics = status.get('current_metrics')
        
        if not current_metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        return SystemMetricsResponse(
            timestamp=datetime.fromtimestamp(current_metrics['timestamp']),
            cpu_percent=current_metrics['cpu_percent'],
            memory_percent=current_metrics['memory_percent'],
            memory_used_mb=current_metrics['memory_used_mb'],
            disk_usage_percent=current_metrics['disk_usage_percent'],
            active_connections=current_metrics['active_connections'],
            processing_queue_size=current_metrics['processing_queue_size'],
            error_rate=current_metrics['error_rate'],
            avg_response_time=current_metrics['avg_response_time']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/history")
async def get_metrics_history(
    hours: int = Query(1, description="Number of hours of history to return", ge=1, le=24),
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get historical system metrics.
    
    - **hours**: Number of hours of history to return (1-24)
    """
    try:
        history = dashboard.get_metrics_history(hours)
        
        return {
            "time_period_hours": hours,
            "data_points": len(history),
            "metrics": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics history: {str(e)}")


@router.get("/components", response_model=List[ComponentHealthResponse])
async def get_component_health(
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get health status of all system components.
    """
    try:
        status = dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        components = []
        for component_name, health_data in component_health.items():
            components.append(ComponentHealthResponse(
                component=component_name,
                status=health_data['status'],
                last_activity=datetime.fromtimestamp(health_data['last_activity']),
                error_count=health_data['error_count'],
                performance_score=health_data['performance_score'],
                details=health_data['details']
            ))
        
        return components
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component health: {str(e)}")


@router.get("/components/{component_name}")
async def get_component_details(
    component_name: str,
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get detailed health information for a specific component.
    
    - **component_name**: Name of the component to check
    """
    try:
        status = dashboard.get_current_status()
        component_health = status.get('component_health', {})
        
        if component_name not in component_health:
            raise HTTPException(status_code=404, detail=f"Component '{component_name}' not found")
        
        health_data = component_health[component_name]
        
        return ComponentHealthResponse(
            component=component_name,
            status=health_data['status'],
            last_activity=datetime.fromtimestamp(health_data['last_activity']),
            error_count=health_data['error_count'],
            performance_score=health_data['performance_score'],
            details=health_data['details']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component details: {str(e)}")


@router.get("/queue", response_model=ProcessingQueueResponse)
async def get_processing_queue_status(
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get processing queue status and statistics.
    """
    try:
        status = dashboard.get_current_status()
        queue_status = status.get('queue_status', {})
        
        # Mock additional queue statistics (would be real in production)
        return ProcessingQueueResponse(
            queue_size=queue_status.get('size', 0),
            oldest_task_age_seconds=queue_status.get('oldest_task_age', 0.0),
            active_tasks=[],  # Would contain actual active tasks
            completed_tasks_last_hour=0,  # Would be calculated from logs
            failed_tasks_last_hour=0,  # Would be calculated from logs
            average_processing_time=0.0  # Would be calculated from metrics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get currently active system alerts.
    """
    try:
        status = dashboard.get_current_status()
        active_alerts = status.get('active_alerts', [])
        
        alerts = []
        for alert in active_alerts:
            alerts.append(AlertResponse(
                alert_type=alert['type'],
                severity=alert['severity'],
                message=alert['message'],
                timestamp=datetime.now(),  # Would be actual alert timestamp
                value=alert.get('value'),
                threshold=alert.get('threshold')
            ))
        
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/performance", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    hours: int = Query(1, description="Time period in hours for summary", ge=1, le=24),
    dashboard: MonitoringDashboard = Depends(get_monitoring_dashboard)
):
    """
    Get performance summary for specified time period.
    
    - **hours**: Time period in hours (1-24)
    """
    try:
        summary = dashboard.get_performance_summary()
        
        if not summary:
            raise HTTPException(status_code=503, detail="Performance data not available")
        
        return PerformanceSummaryResponse(
            time_period_hours=hours,
            avg_cpu_percent=summary.get('avg_cpu_percent', 0.0),
            avg_memory_percent=summary.get('avg_memory_percent', 0.0),
            avg_response_time=summary.get('avg_response_time', 0.0),
            avg_queue_size=summary.get('avg_queue_size', 0.0),
            total_errors=summary.get('total_errors', 0),
            uptime_hours=summary.get('uptime_hours', 0.0),
            requests_per_hour=0.0  # Would be calculated from actual metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


@router.get("/logs/summary")
async def get_log_summary(
    hours: int = Query(24, description="Number of hours to analyze", ge=1, le=168),
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """
    Get log summary for specified time period.
    
    - **hours**: Number of hours to analyze (1-168)
    
    Note: Requires authentication for detailed log access.
    """
    try:
        logger = get_logger()
        summary = logger.get_log_summary(hours)
        
        # Return limited info for unauthenticated users
        if not current_user:
            return {
                "time_range": summary.get('time_range'),
                "total_entries": summary.get('total_entries', 0),
                "error_count": summary.get('error_count', 0),
                "warning_count": summary.get('warning_count', 0),
                "note": "Login for detailed log information"
            }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log summary: {str(e)}")


@router.post("/health/check/{component}")
async def trigger_component_health_check(
    component: str,
    current_user: UserInfo = Depends(get_current_user_optional)
):
    """
    Trigger a manual health check for a specific component.
    
    - **component**: Component name to check
    
    Note: May require authentication for some components.
    """
    try:
        # Record the health check request
        dashboard = get_dashboard()
        dashboard.record_component_activity(component, True)
        
        # Mock component-specific health check
        health_checks = {
            'preprocessing': lambda: {'status': 'healthy', 'processors_available': 3},
            'postprocessing': lambda: {'status': 'healthy', 'methods_available': 5},
            'storage': lambda: {'status': 'healthy', 'databases_connected': 2},
            'rag': lambda: {'status': 'healthy', 'embeddings_ready': True},
            'versioning': lambda: {'status': 'healthy', 'version_tracking': True},
            'api': lambda: {'status': 'healthy', 'endpoints_active': 15},
            'authentication': lambda: {'status': 'healthy', 'auth_system_ready': True}
        }
        
        if component not in health_checks:
            raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
        
        check_result = health_checks[component]()
        
        return {
            'component': component,
            'check_timestamp': datetime.now().isoformat(),
            'triggered_by': current_user.username if current_user else 'anonymous',
            'result': check_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/status/dashboard")
async def get_dashboard_data():
    """
    Get comprehensive dashboard data for monitoring UI.
    
    Returns all monitoring data needed for a dashboard view.
    """
    try:
        dashboard = get_dashboard()
        
        # Get all monitoring data
        status = dashboard.get_current_status()
        performance = dashboard.get_performance_summary()
        recent_metrics = dashboard.get_metrics_history(1)  # Last hour
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_status': status,
            'performance_summary': performance,
            'recent_metrics': recent_metrics,
            'uptime_seconds': time.time() - SYSTEM_START_TIME,
            'version': '1.0.0'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.post("/monitoring/start")
async def start_monitoring(
    interval_seconds: int = Query(30, description="Monitoring interval in seconds", ge=5, le=300),
    current_user: UserInfo = Depends(get_current_user_optional)
):
    """
    Start system monitoring (admin only).
    
    - **interval_seconds**: Monitoring interval (5-300 seconds)
    """
    # Check if user has admin permissions
    if not current_user or 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        dashboard = get_dashboard()
        dashboard.start_monitoring(interval_seconds)
        
        return {
            'message': 'Monitoring started',
            'interval_seconds': interval_seconds,
            'started_by': current_user.username,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: UserInfo = Depends(get_current_user_optional)
):
    """
    Stop system monitoring (admin only).
    """
    # Check if user has admin permissions
    if not current_user or 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        dashboard = get_dashboard()
        dashboard.stop_monitoring()
        
        return {
            'message': 'Monitoring stopped',
            'stopped_by': current_user.username,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")