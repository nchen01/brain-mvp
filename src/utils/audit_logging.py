"""Comprehensive audit logging system for security and compliance."""

import logging
import json
import threading
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import uuid

from .security_validation import sanitize_for_logs

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    
    # Document operations
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_MODIFY = "document_modify"
    DOCUMENT_SHARE = "document_share"
    
    # Data operations
    DATA_CREATE = "data_create"
    DATA_READ = "data_read"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # System operations
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    
    # Security events
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    SECURITY_VIOLATION = "security_violation"
    ENCRYPTION_KEY_CHANGE = "encryption_key_change"
    
    # Privacy events
    DATA_RETENTION_POLICY_APPLIED = "data_retention_applied"
    DATA_ANONYMIZATION = "data_anonymization"
    GDPR_REQUEST = "gdpr_request"
    DATA_BREACH_DETECTED = "data_breach_detected"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    result: str  # success, failure, error
    details: Dict[str, Any]
    risk_score: int = 0  # 0-100 risk assessment
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'result': self.result,
            'details': self.details,
            'risk_score': self.risk_score,
            'tags': self.tags
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Centralized audit logging system."""
    
    def __init__(self, 
                 log_file: Optional[str] = None,
                 max_file_size: int = 100 * 1024 * 1024,  # 100MB
                 backup_count: int = 10,
                 enable_console: bool = False):
        """Initialize audit logger."""
        self.log_file = log_file or "logs/audit.log"
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        
        # Create logs directory
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Event storage for analysis
        self.recent_events: List[AuditEvent] = []
        self.max_recent_events = 1000
        self._lock = threading.RLock()
        
        # Risk assessment rules
        self.risk_rules = self._setup_risk_rules()
    
    def _setup_logging(self):
        """Setup audit logging configuration."""
        # Create audit logger
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.audit_logger.handlers.clear()
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        
        # JSON formatter for structured logging
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        self.audit_logger.addHandler(file_handler)
        
        # Console handler if enabled
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.audit_logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.audit_logger.propagate = False
    
    def _setup_risk_rules(self) -> Dict[str, int]:
        """Setup risk assessment rules."""
        return {
            # High-risk events
            AuditEventType.LOGIN_FAILURE.value: 30,
            AuditEventType.ACCESS_DENIED.value: 40,
            AuditEventType.SECURITY_VIOLATION.value: 80,
            AuditEventType.DATA_BREACH_DETECTED.value: 100,
            AuditEventType.DOCUMENT_DELETE.value: 50,
            
            # Medium-risk events
            AuditEventType.DOCUMENT_DOWNLOAD.value: 20,
            AuditEventType.DATA_EXPORT.value: 30,
            AuditEventType.PERMISSION_CHANGE.value: 40,
            AuditEventType.CONFIG_CHANGE.value: 35,
            
            # Low-risk events
            AuditEventType.LOGIN_SUCCESS.value: 5,
            AuditEventType.DOCUMENT_VIEW.value: 5,
            AuditEventType.DATA_READ.value: 5,
        }
    
    def _calculate_risk_score(self, event_type: AuditEventType, details: Dict[str, Any]) -> int:
        """Calculate risk score for an event."""
        base_score = self.risk_rules.get(event_type.value, 10)
        
        # Adjust based on details
        risk_factors = {
            'failed_attempts': details.get('failed_attempts', 0) * 10,
            'admin_action': 20 if details.get('admin_action') else 0,
            'bulk_operation': 15 if details.get('bulk_operation') else 0,
            'external_access': 25 if details.get('external_ip') else 0,
            'off_hours': 10 if details.get('off_hours') else 0,
        }
        
        total_score = base_score + sum(risk_factors.values())
        return min(100, max(0, total_score))
    
    def log_event(self,
                  event_type: AuditEventType,
                  action: str,
                  result: str = "success",
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  severity: Optional[AuditSeverity] = None,
                  tags: Optional[List[str]] = None) -> str:
        """Log an audit event."""
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Sanitize details for logging
        safe_details = {}
        if details:
            for key, value in details.items():
                safe_details[key] = sanitize_for_logs(value)
        
        # Determine severity if not provided
        if severity is None:
            risk_score = self._calculate_risk_score(event_type, safe_details)
            if risk_score >= 80:
                severity = AuditSeverity.CRITICAL
            elif risk_score >= 60:
                severity = AuditSeverity.HIGH
            elif risk_score >= 30:
                severity = AuditSeverity.MEDIUM
            else:
                severity = AuditSeverity.LOW
        
        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=safe_details,
            risk_score=self._calculate_risk_score(event_type, safe_details),
            tags=tags or []
        )
        
        # Store in recent events
        with self._lock:
            self.recent_events.append(event)
            if len(self.recent_events) > self.max_recent_events:
                self.recent_events.pop(0)
        
        # Log to file
        self.audit_logger.info(event.to_json())
        
        # Check for security alerts
        self._check_security_alerts(event)
        
        return event_id
    
    def _check_security_alerts(self, event: AuditEvent):
        """Check if event should trigger security alerts."""
        if event.risk_score >= 80:
            logger.warning(f"High-risk audit event: {event.event_type.value} - {event.action}")
        
        # Check for patterns that might indicate attacks
        if event.event_type == AuditEventType.LOGIN_FAILURE:
            recent_failures = self._count_recent_events(
                AuditEventType.LOGIN_FAILURE,
                user_id=event.user_id,
                minutes=15
            )
            
            if recent_failures >= 5:
                logger.critical(f"Potential brute force attack detected for user: {event.user_id}")
        
        elif event.event_type == AuditEventType.ACCESS_DENIED:
            recent_denials = self._count_recent_events(
                AuditEventType.ACCESS_DENIED,
                ip_address=event.ip_address,
                minutes=10
            )
            
            if recent_denials >= 10:
                logger.critical(f"Potential unauthorized access attempt from IP: {event.ip_address}")
    
    def _count_recent_events(self,
                           event_type: AuditEventType,
                           user_id: Optional[str] = None,
                           ip_address: Optional[str] = None,
                           minutes: int = 15) -> int:
        """Count recent events matching criteria."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        count = 0
        
        with self._lock:
            for event in self.recent_events:
                if event.timestamp.timestamp() < cutoff_time:
                    continue
                
                if event.event_type != event_type:
                    continue
                
                if user_id and event.user_id != user_id:
                    continue
                
                if ip_address and event.ip_address != ip_address:
                    continue
                
                count += 1
        
        return count
    
    def get_recent_events(self,
                         event_type: Optional[AuditEventType] = None,
                         user_id: Optional[str] = None,
                         severity: Optional[AuditSeverity] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit events with filtering."""
        filtered_events = []
        
        with self._lock:
            for event in reversed(self.recent_events):
                if event_type and event.event_type != event_type:
                    continue
                
                if user_id and event.user_id != user_id:
                    continue
                
                if severity and event.severity != severity:
                    continue
                
                filtered_events.append(event.to_dict())
                
                if len(filtered_events) >= limit:
                    break
        
        return filtered_events
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary from recent events."""
        with self._lock:
            total_events = len(self.recent_events)
            
            # Count by severity
            severity_counts = {}
            for event in self.recent_events:
                severity = event.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by event type
            type_counts = {}
            for event in self.recent_events:
                event_type = event.event_type.value
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
            
            # High-risk events
            high_risk_events = [
                event.to_dict() for event in self.recent_events
                if event.risk_score >= 70
            ]
            
            # Recent failures
            recent_failures = [
                event.to_dict() for event in self.recent_events
                if event.result == "failure"
            ]
        
        return {
            'total_events': total_events,
            'severity_counts': severity_counts,
            'type_counts': type_counts,
            'high_risk_events': high_risk_events[-10:],  # Last 10
            'recent_failures': recent_failures[-10:],  # Last 10
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global audit logger instance
audit_logger = AuditLogger()


# Decorator for automatic audit logging
def audit_operation(event_type: AuditEventType, 
                   action: Optional[str] = None,
                   resource_type: Optional[str] = None):
    """Decorator for automatic audit logging of operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract context information
            user_id = kwargs.get('user_id') or getattr(args[0] if args else None, 'user_id', None)
            session_id = kwargs.get('session_id')
            
            operation_action = action or func.__name__
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful operation
                audit_logger.log_event(
                    event_type=event_type,
                    action=operation_action,
                    result="success",
                    user_id=user_id,
                    session_id=session_id,
                    resource_type=resource_type,
                    details={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed operation
                audit_logger.log_event(
                    event_type=event_type,
                    action=operation_action,
                    result="failure",
                    user_id=user_id,
                    session_id=session_id,
                    resource_type=resource_type,
                    details={
                        'function': func.__name__,
                        'module': func.__module__,
                        'error': str(e)
                    },
                    severity=AuditSeverity.HIGH
                )
                
                raise
        
        return wrapper
    return decorator


# Convenience functions
def log_document_operation(operation: str, 
                          document_id: str,
                          user_id: Optional[str] = None,
                          result: str = "success",
                          details: Optional[Dict[str, Any]] = None):
    """Log document operation."""
    event_type_map = {
        'upload': AuditEventType.DOCUMENT_UPLOAD,
        'download': AuditEventType.DOCUMENT_DOWNLOAD,
        'view': AuditEventType.DOCUMENT_VIEW,
        'delete': AuditEventType.DOCUMENT_DELETE,
        'modify': AuditEventType.DOCUMENT_MODIFY,
        'share': AuditEventType.DOCUMENT_SHARE
    }
    
    event_type = event_type_map.get(operation, AuditEventType.DOCUMENT_VIEW)
    
    audit_logger.log_event(
        event_type=event_type,
        action=operation,
        result=result,
        user_id=user_id,
        resource_type="document",
        resource_id=document_id,
        details=details or {}
    )


def log_authentication_event(event_type: str,
                           user_id: Optional[str] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None,
                           result: str = "success",
                           details: Optional[Dict[str, Any]] = None):
    """Log authentication event."""
    event_type_map = {
        'login': AuditEventType.LOGIN_SUCCESS if result == "success" else AuditEventType.LOGIN_FAILURE,
        'logout': AuditEventType.LOGOUT,
        'password_change': AuditEventType.PASSWORD_CHANGE
    }
    
    audit_event_type = event_type_map.get(event_type, AuditEventType.LOGIN_SUCCESS)
    
    audit_logger.log_event(
        event_type=audit_event_type,
        action=event_type,
        result=result,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {}
    )


def log_security_event(event_type: str,
                      action: str,
                      user_id: Optional[str] = None,
                      resource_id: Optional[str] = None,
                      severity: AuditSeverity = AuditSeverity.HIGH,
                      details: Optional[Dict[str, Any]] = None):
    """Log security event."""
    event_type_map = {
        'access_denied': AuditEventType.ACCESS_DENIED,
        'permission_change': AuditEventType.PERMISSION_CHANGE,
        'security_violation': AuditEventType.SECURITY_VIOLATION,
        'data_breach': AuditEventType.DATA_BREACH_DETECTED
    }
    
    audit_event_type = event_type_map.get(event_type, AuditEventType.SECURITY_VIOLATION)
    
    audit_logger.log_event(
        event_type=audit_event_type,
        action=action,
        result="detected",
        user_id=user_id,
        resource_id=resource_id,
        severity=severity,
        details=details or {}
    )


def get_audit_summary() -> Dict[str, Any]:
    """Get audit summary."""
    return audit_logger.get_security_summary()


def get_recent_audit_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent audit events."""
    return audit_logger.get_recent_events(limit=limit)