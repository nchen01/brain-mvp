"""Security integration layer for DocForge system."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .security_validation import input_validator, SecurityLevel
from .secure_storage import secure_storage, EncryptionLevel
from .audit_logging import audit_logger, AuditEventType, log_document_operation, log_security_event
from .access_control import access_control, Permission, Role, create_user_session
from .privacy_compliance import privacy_manager, DataCategory, LegalBasis, record_user_data_processing

logger = logging.getLogger(__name__)


class SecurityIntegration:
    """Central security integration for DocForge."""
    
    def __init__(self):
        """Initialize security integration."""
        self.initialized = False
        self.security_config = {}
    
    def initialize_security(self, config: Dict[str, Any]):
        """Initialize security system with configuration."""
        try:
            self.security_config = config
            
            # Configure input validation
            security_level = SecurityLevel(config.get('validation', {}).get('level', 'medium'))
            global input_validator
            input_validator.security_level = security_level
            
            # Configure secure storage
            storage_config = config.get('storage', {})
            secure_storage.encryption_level = EncryptionLevel(
                storage_config.get('encryption_level', 'basic')
            )
            secure_storage.max_file_size = storage_config.get('max_file_size', 100 * 1024 * 1024)
            
            # Configure audit logging
            audit_config = config.get('audit', {})
            audit_logger.enable_console = audit_config.get('console_logging', False)
            
            # Configure access control
            access_config = config.get('access_control', {})
            access_control.max_failed_attempts = access_config.get('max_failed_attempts', 5)
            access_control.session_timeout = access_config.get('session_timeout_hours', 24) * 3600
            
            # Configure privacy compliance
            privacy_config = config.get('privacy', {})
            privacy_manager.auto_delete_enabled = privacy_config.get('auto_delete', True)
            
            # Setup default admin user if specified
            admin_config = config.get('admin_user')
            if admin_config:
                self._setup_admin_user(admin_config)
            
            self.initialized = True
            logger.info("Security system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security system: {e}")
            raise
    
    def _setup_admin_user(self, admin_config: Dict[str, Any]):
        """Setup default admin user."""
        try:
            user_id = admin_config['user_id']
            
            # Assign admin role
            access_control.assign_role(user_id, Role.ADMIN)
            
            # Log admin setup
            log_security_event(
                "admin_setup",
                f"Admin user configured: {user_id}",
                user_id=user_id
            )
            
            logger.info(f"Admin user configured: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup admin user: {e}")
    
    def secure_document_upload(self,
                             file_path: str,
                             filename: str,
                             user_id: str,
                             session_id: Optional[str] = None) -> Dict[str, Any]:
        """Securely handle document upload with full security pipeline."""
        try:
            # Validate session
            if session_id:
                context = access_control.validate_session(session_id)
                if not context or context.user_id != user_id:
                    raise PermissionError("Invalid session")
            
            # Check upload permission
            if not access_control.has_permission(user_id, Permission.DOCUMENT_WRITE):
                log_security_event(
                    "access_denied",
                    f"Document upload denied for user {user_id}",
                    user_id=user_id
                )
                raise PermissionError("Upload permission denied")
            
            # Validate filename
            sanitized_filename = input_validator.validate_field('filename', filename)
            
            # Validate file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            validation_result = input_validator.validate_file_upload(
                sanitized_filename,
                content,
                allowed_types=secure_storage.allowed_extensions,
                max_size=secure_storage.max_file_size
            )
            
            if not validation_result['valid']:
                log_security_event(
                    "security_violation",
                    f"File upload validation failed: {validation_result['errors']}",
                    user_id=user_id
                )
                raise ValueError(f"File validation failed: {validation_result['errors']}")
            
            # Store file securely
            file_id = secure_storage.store_file(
                file_path,
                sanitized_filename,
                owner=user_id
            )
            
            # Create resource access control
            access_control.create_resource_access(
                "document",
                file_id,
                user_id,
                {Permission.DOCUMENT_READ, Permission.DOCUMENT_WRITE, 
                 Permission.DOCUMENT_DELETE, Permission.DOCUMENT_SHARE}
            )
            
            # Record data processing for privacy compliance
            record_user_data_processing(
                user_id,
                DataCategory.DOCUMENT_CONTENT,
                "Document storage and processing",
                LegalBasis.LEGITIMATE_INTERESTS
            )
            
            # Log successful upload
            log_document_operation(
                "upload",
                file_id,
                user_id=user_id,
                details={
                    'filename': sanitized_filename,
                    'file_size': len(content),
                    'mime_type': validation_result.get('mime_type')
                }
            )
            
            return {
                'success': True,
                'file_id': file_id,
                'filename': sanitized_filename,
                'size': len(content)
            }
            
        except Exception as e:
            # Log failed upload
            log_document_operation(
                "upload",
                "unknown",
                user_id=user_id,
                result="failure",
                details={'error': str(e), 'filename': filename}
            )
            
            logger.error(f"Secure document upload failed: {e}")
            raise
    
    def secure_document_access(self,
                             file_id: str,
                             user_id: str,
                             session_id: Optional[str] = None,
                             operation: str = "read") -> Dict[str, Any]:
        """Securely handle document access with permission checking."""
        try:
            # Validate session
            if session_id:
                context = access_control.validate_session(session_id)
                if not context or context.user_id != user_id:
                    raise PermissionError("Invalid session")
            
            # Map operation to permission
            permission_map = {
                'read': Permission.DOCUMENT_READ,
                'write': Permission.DOCUMENT_WRITE,
                'delete': Permission.DOCUMENT_DELETE,
                'share': Permission.DOCUMENT_SHARE
            }
            
            required_permission = permission_map.get(operation, Permission.DOCUMENT_READ)
            
            # Check resource access
            has_access = access_control.check_resource_access(
                user_id, "document", file_id, required_permission
            )
            
            if not has_access:
                log_security_event(
                    "access_denied",
                    f"Document {operation} denied for user {user_id}",
                    user_id=user_id,
                    resource_id=file_id
                )
                raise PermissionError(f"Document {operation} permission denied")
            
            # Get file metadata
            metadata = secure_storage.get_file_metadata(file_id)
            if not metadata:
                raise FileNotFoundError("Document not found")
            
            # Log access
            log_document_operation(
                operation,
                file_id,
                user_id=user_id,
                details={
                    'filename': metadata.original_filename,
                    'file_size': metadata.file_size
                }
            )
            
            return {
                'success': True,
                'file_id': file_id,
                'metadata': metadata.to_dict(),
                'access_granted': True
            }
            
        except Exception as e:
            # Log failed access
            log_document_operation(
                operation,
                file_id,
                user_id=user_id,
                result="failure",
                details={'error': str(e)}
            )
            
            logger.error(f"Secure document access failed: {e}")
            raise
    
    def secure_document_deletion(self,
                               file_id: str,
                               user_id: str,
                               session_id: Optional[str] = None) -> Dict[str, Any]:
        """Securely handle document deletion with audit trail."""
        try:
            # Validate session and permissions
            access_result = self.secure_document_access(
                file_id, user_id, session_id, "delete"
            )
            
            if not access_result['success']:
                raise PermissionError("Delete access denied")
            
            # Get metadata before deletion
            metadata = secure_storage.get_file_metadata(file_id)
            
            # Delete file securely
            secure_storage.delete_file(file_id, requester=user_id, secure_delete=True)
            
            # Record privacy compliance action
            privacy_manager.record_data_processing(
                DataCategory.DOCUMENT_CONTENT,
                LegalBasis.LEGITIMATE_INTERESTS,
                "Document deletion",
                user_id
            )
            
            # Log successful deletion
            log_document_operation(
                "delete",
                file_id,
                user_id=user_id,
                details={
                    'filename': metadata.original_filename if metadata else 'unknown',
                    'secure_delete': True
                }
            )
            
            return {
                'success': True,
                'file_id': file_id,
                'deleted': True
            }
            
        except Exception as e:
            logger.error(f"Secure document deletion failed: {e}")
            raise
    
    def authenticate_user(self,
                         user_id: str,
                         credentials: Dict[str, Any],
                         ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate user with security controls."""
        try:
            # Validate input
            validated_user_id = input_validator.validate_field('user_input', user_id)
            
            # Check if account is locked (handled by access_control)
            # This is a simplified authentication - in production, verify actual credentials
            
            # For demo purposes, assume authentication succeeds if user has a role
            if validated_user_id not in access_control.user_roles:
                # Record failed attempt
                access_control.record_failed_attempt(validated_user_id)
                
                log_security_event(
                    "access_denied",
                    f"Authentication failed for unknown user",
                    user_id=validated_user_id,
                    details={'ip_address': ip_address}
                )
                
                raise PermissionError("Authentication failed")
            
            # Create session
            session_id = create_user_session(validated_user_id, ip_address)
            
            # Record successful authentication
            from .audit_logging import log_authentication_event
            log_authentication_event(
                "login",
                user_id=validated_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                result="success"
            )
            
            # Record data processing for session
            record_user_data_processing(
                validated_user_id,
                DataCategory.TECHNICAL_DATA,
                "User session management",
                LegalBasis.LEGITIMATE_INTERESTS
            )
            
            return {
                'success': True,
                'user_id': validated_user_id,
                'session_id': session_id,
                'permissions': list(access_control.get_user_permissions(validated_user_id))
            }
            
        except Exception as e:
            # Record failed authentication
            access_control.record_failed_attempt(user_id)
            
            log_authentication_event(
                "login",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                result="failure",
                details={'error': str(e)}
            )
            
            logger.error(f"User authentication failed: {e}")
            raise
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security system status."""
        try:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'initialized': self.initialized,
                'components': {
                    'input_validation': {
                        'security_level': input_validator.security_level.value,
                        'rules_count': len(input_validator.validation_rules)
                    },
                    'secure_storage': {
                        'encryption_level': secure_storage.encryption_level.value,
                        'total_files': len(secure_storage.metadata_store),
                        'storage_stats': secure_storage.get_storage_stats()
                    },
                    'audit_logging': {
                        'recent_events': len(audit_logger.recent_events),
                        'security_summary': audit_logger.get_security_summary()
                    },
                    'access_control': {
                        'total_users': len(access_control.user_roles),
                        'active_sessions': len(access_control.active_sessions),
                        'access_summary': access_control.get_access_summary()
                    },
                    'privacy_compliance': {
                        'processing_records': len(privacy_manager.processing_records),
                        'subject_requests': len(privacy_manager.subject_requests),
                        'compliance_report': privacy_manager.get_compliance_report()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get security status: {e}")
            return {'error': str(e)}
    
    def run_security_maintenance(self) -> Dict[str, Any]:
        """Run security maintenance tasks."""
        try:
            maintenance_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tasks_completed': []
            }
            
            # Apply data retention policies
            retention_result = privacy_manager.apply_retention_policies()
            maintenance_results['tasks_completed'].append({
                'task': 'data_retention',
                'result': retention_result
            })
            
            # Clean up expired sessions (simplified)
            expired_sessions = []
            for session_id in list(access_control.active_sessions.keys()):
                if not access_control.validate_session(session_id):
                    expired_sessions.append(session_id)
            
            maintenance_results['tasks_completed'].append({
                'task': 'session_cleanup',
                'expired_sessions': len(expired_sessions)
            })
            
            # Log maintenance completion
            log_security_event(
                "system_maintenance",
                f"Security maintenance completed: {len(maintenance_results['tasks_completed'])} tasks",
                details=maintenance_results
            )
            
            return maintenance_results
            
        except Exception as e:
            logger.error(f"Security maintenance failed: {e}")
            return {'error': str(e)}


# Global security integration instance
security_integration = SecurityIntegration()


# Convenience functions for DocForge integration
def initialize_docforge_security(config: Dict[str, Any]):
    """Initialize DocForge security system."""
    security_integration.initialize_security(config)


def secure_upload_document(file_path: str, filename: str, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Securely upload document."""
    return security_integration.secure_document_upload(file_path, filename, user_id, session_id)


def secure_access_document(file_id: str, user_id: str, session_id: Optional[str] = None, operation: str = "read") -> Dict[str, Any]:
    """Securely access document."""
    return security_integration.secure_document_access(file_id, user_id, session_id, operation)


def secure_delete_document(file_id: str, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Securely delete document."""
    return security_integration.secure_document_deletion(file_id, user_id, session_id)


def authenticate_docforge_user(user_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Authenticate DocForge user."""
    return security_integration.authenticate_user(user_id, credentials, **kwargs)


def get_docforge_security_status() -> Dict[str, Any]:
    """Get DocForge security status."""
    return security_integration.get_security_status()


def setup_docforge_security():
    """Setup DocForge security with default configuration."""
    default_config = {
        'validation': {
            'level': 'medium'
        },
        'storage': {
            'encryption_level': 'basic',
            'max_file_size': 100 * 1024 * 1024  # 100MB
        },
        'audit': {
            'console_logging': False
        },
        'access_control': {
            'max_failed_attempts': 5,
            'session_timeout_hours': 24
        },
        'privacy': {
            'auto_delete': True
        }
    }
    
    initialize_docforge_security(default_config)
    
    # Setup default roles
    access_control.assign_role("admin", Role.ADMIN)
    access_control.assign_role("user", Role.USER)
    
    logger.info("DocForge security system setup completed")