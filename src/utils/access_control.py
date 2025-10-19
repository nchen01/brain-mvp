"""Access control and permission validation system."""

import logging
from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import hashlib
import json

from .audit_logging import log_security_event, AuditSeverity

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_SHARE = "document:share"
    DOCUMENT_ADMIN = "document:admin"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_BACKUP = "system:backup"
    
    # User management permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # Data permissions
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    
    # Privacy permissions
    PRIVACY_VIEW = "privacy:view"
    PRIVACY_MANAGE = "privacy:manage"
    PRIVACY_DELETE = "privacy:delete"


class Role(str, Enum):
    """System roles."""
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class AccessContext:
    """Access control context."""
    user_id: str
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceAccess:
    """Resource access definition."""
    resource_type: str
    resource_id: str
    owner_id: Optional[str] = None
    permissions: Set[Permission] = field(default_factory=set)
    shared_with: Dict[str, Set[Permission]] = field(default_factory=dict)
    public_permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'owner_id': self.owner_id,
            'permissions': [p.value for p in self.permissions],
            'shared_with': {
                user_id: [p.value for p in perms]
                for user_id, perms in self.shared_with.items()
            },
            'public_permissions': [p.value for p in self.public_permissions],
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class UserRole:
    """User role assignment."""
    user_id: str
    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    granted_by: Optional[str] = None
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if role assignment is expired."""
        return self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at


class AccessControlManager:
    """Centralized access control and permission management."""
    
    def __init__(self):
        """Initialize access control manager."""
        self.user_roles: Dict[str, UserRole] = {}
        self.resource_access: Dict[str, ResourceAccess] = {}
        self.role_permissions = self._setup_role_permissions()
        
        # Session tracking
        self.active_sessions: Dict[str, AccessContext] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=24)
    
    def _setup_role_permissions(self) -> Dict[Role, Set[Permission]]:
        """Setup default role permissions."""
        return {
            Role.GUEST: {
                Permission.DOCUMENT_READ,
            },
            Role.USER: {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_WRITE,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
            },
            Role.MODERATOR: {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_WRITE,
                Permission.DOCUMENT_DELETE,
                Permission.DOCUMENT_SHARE,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_DELETE,
                Permission.USER_READ,
            },
            Role.ADMIN: {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_WRITE,
                Permission.DOCUMENT_DELETE,
                Permission.DOCUMENT_SHARE,
                Permission.DOCUMENT_ADMIN,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_DELETE,
                Permission.DATA_EXPORT,
                Permission.DATA_IMPORT,
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.USER_DELETE,
                Permission.SYSTEM_MONITOR,
                Permission.PRIVACY_VIEW,
                Permission.PRIVACY_MANAGE,
            },
            Role.SUPER_ADMIN: set(Permission),  # All permissions
        }
    
    def assign_role(self, 
                   user_id: str, 
                   role: Role,
                   granted_by: Optional[str] = None,
                   expires_at: Optional[datetime] = None,
                   additional_permissions: Optional[Set[Permission]] = None) -> bool:
        """Assign role to user."""
        try:
            # Get base permissions for role
            base_permissions = self.role_permissions.get(role, set())
            
            # Add additional permissions if provided
            all_permissions = base_permissions.copy()
            if additional_permissions:
                all_permissions.update(additional_permissions)
            
            # Create user role
            user_role = UserRole(
                user_id=user_id,
                role=role,
                permissions=all_permissions,
                granted_by=granted_by,
                expires_at=expires_at
            )
            
            self.user_roles[user_id] = user_role
            
            logger.info(f"Role {role.value} assigned to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            return False
    
    def revoke_role(self, user_id: str, revoked_by: Optional[str] = None) -> bool:
        """Revoke user role."""
        try:
            if user_id in self.user_roles:
                old_role = self.user_roles[user_id].role
                del self.user_roles[user_id]
                
                logger.info(f"Role {old_role.value} revoked from user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke role: {e}")
            return False
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        if user_id not in self.user_roles:
            return set()
        
        user_role = self.user_roles[user_id]
        
        # Check if role is expired
        if user_role.is_expired():
            logger.warning(f"User {user_id} role has expired")
            return set()
        
        return user_role.permissions.copy()
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission."""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions
    
    def create_resource_access(self,
                             resource_type: str,
                             resource_id: str,
                             owner_id: str,
                             permissions: Optional[Set[Permission]] = None,
                             expires_at: Optional[datetime] = None) -> bool:
        """Create resource access control."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            
            # Default permissions for owner
            if permissions is None:
                permissions = {
                    Permission.DOCUMENT_READ,
                    Permission.DOCUMENT_WRITE,
                    Permission.DOCUMENT_DELETE,
                    Permission.DOCUMENT_SHARE
                }
            
            resource_access = ResourceAccess(
                resource_type=resource_type,
                resource_id=resource_id,
                owner_id=owner_id,
                permissions=permissions,
                expires_at=expires_at
            )
            
            self.resource_access[resource_key] = resource_access
            
            logger.info(f"Resource access created: {resource_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create resource access: {e}")
            return False
    
    def share_resource(self,
                      resource_type: str,
                      resource_id: str,
                      owner_id: str,
                      target_user_id: str,
                      permissions: Set[Permission],
                      expires_at: Optional[datetime] = None) -> bool:
        """Share resource with another user."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            
            # Check if resource exists and user is owner
            if resource_key not in self.resource_access:
                logger.warning(f"Resource not found: {resource_key}")
                return False
            
            resource = self.resource_access[resource_key]
            
            if resource.owner_id != owner_id:
                log_security_event(
                    "access_denied",
                    f"User {owner_id} attempted to share resource {resource_key} without ownership",
                    user_id=owner_id,
                    resource_id=resource_id,
                    severity=AuditSeverity.HIGH
                )
                return False
            
            # Add sharing permissions
            resource.shared_with[target_user_id] = permissions
            
            logger.info(f"Resource {resource_key} shared with user {target_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to share resource: {e}")
            return False
    
    def revoke_resource_access(self,
                             resource_type: str,
                             resource_id: str,
                             owner_id: str,
                             target_user_id: str) -> bool:
        """Revoke resource access from user."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            
            if resource_key not in self.resource_access:
                return False
            
            resource = self.resource_access[resource_key]
            
            if resource.owner_id != owner_id:
                log_security_event(
                    "access_denied",
                    f"User {owner_id} attempted to revoke access to resource {resource_key} without ownership",
                    user_id=owner_id,
                    resource_id=resource_id,
                    severity=AuditSeverity.HIGH
                )
                return False
            
            if target_user_id in resource.shared_with:
                del resource.shared_with[target_user_id]
                logger.info(f"Access revoked for user {target_user_id} to resource {resource_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke resource access: {e}")
            return False
    
    def check_resource_access(self,
                            user_id: str,
                            resource_type: str,
                            resource_id: str,
                            required_permission: Permission,
                            context: Optional[AccessContext] = None) -> bool:
        """Check if user has access to resource with specific permission."""
        try:
            resource_key = f"{resource_type}:{resource_id}"
            
            # Check if resource exists
            if resource_key not in self.resource_access:
                logger.warning(f"Resource not found: {resource_key}")
                return False
            
            resource = self.resource_access[resource_key]
            
            # Check if resource is expired
            if resource.expires_at and datetime.now(timezone.utc) > resource.expires_at:
                logger.warning(f"Resource access expired: {resource_key}")
                return False
            
            # Check if user is owner
            if resource.owner_id == user_id:
                return required_permission in resource.permissions
            
            # Check if user has shared access
            if user_id in resource.shared_with:
                shared_permissions = resource.shared_with[user_id]
                return required_permission in shared_permissions
            
            # Check public permissions
            if required_permission in resource.public_permissions:
                return True
            
            # Check system-level permissions
            user_permissions = self.get_user_permissions(user_id)
            
            # Admin permissions can override resource permissions
            if Permission.SYSTEM_ADMIN in user_permissions:
                return True
            
            if resource_type == "document" and Permission.DOCUMENT_ADMIN in user_permissions:
                return True
            
            # Log access denial
            log_security_event(
                "access_denied",
                f"User {user_id} denied access to {resource_key} for permission {required_permission.value}",
                user_id=user_id,
                resource_id=resource_id,
                details={
                    'resource_type': resource_type,
                    'required_permission': required_permission.value,
                    'context': context.additional_context if context else {}
                }
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return False
    
    def create_session(self, user_id: str, context: AccessContext) -> str:
        """Create user session."""
        try:
            # Check for account lockout
            if self._is_account_locked(user_id):
                log_security_event(
                    "access_denied",
                    f"Login attempt for locked account: {user_id}",
                    user_id=user_id,
                    severity=AuditSeverity.HIGH
                )
                raise PermissionError("Account is locked")
            
            # Generate session ID
            session_data = f"{user_id}:{context.timestamp.isoformat()}:{context.ip_address}"
            session_id = hashlib.sha256(session_data.encode()).hexdigest()
            
            # Store session
            context.session_id = session_id
            self.active_sessions[session_id] = context
            
            # Clear failed attempts on successful login
            if user_id in self.failed_attempts:
                del self.failed_attempts[user_id]
            
            logger.info(f"Session created for user {user_id}: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise
    
    def validate_session(self, session_id: str) -> Optional[AccessContext]:
        """Validate user session."""
        try:
            if session_id not in self.active_sessions:
                return None
            
            context = self.active_sessions[session_id]
            
            # Check session timeout
            if datetime.now(timezone.utc) - context.timestamp > self.session_timeout:
                del self.active_sessions[session_id]
                logger.info(f"Session expired: {session_id}")
                return None
            
            return context
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke user session."""
        try:
            if session_id in self.active_sessions:
                context = self.active_sessions[session_id]
                del self.active_sessions[session_id]
                
                logger.info(f"Session revoked for user {context.user_id}: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Session revocation failed: {e}")
            return False
    
    def record_failed_attempt(self, user_id: str):
        """Record failed authentication attempt."""
        now = datetime.now(timezone.utc)
        
        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = []
        
        self.failed_attempts[user_id].append(now)
        
        # Clean old attempts (older than lockout duration)
        cutoff = now - self.lockout_duration
        self.failed_attempts[user_id] = [
            attempt for attempt in self.failed_attempts[user_id]
            if attempt > cutoff
        ]
        
        # Check if account should be locked
        if len(self.failed_attempts[user_id]) >= self.max_failed_attempts:
            log_security_event(
                "security_violation",
                f"Account locked due to {len(self.failed_attempts[user_id])} failed attempts",
                user_id=user_id,
                severity=AuditSeverity.CRITICAL
            )
    
    def _is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if user_id not in self.failed_attempts:
            return False
        
        now = datetime.now(timezone.utc)
        cutoff = now - self.lockout_duration
        
        # Count recent failed attempts
        recent_attempts = [
            attempt for attempt in self.failed_attempts[user_id]
            if attempt > cutoff
        ]
        
        return len(recent_attempts) >= self.max_failed_attempts
    
    def get_access_summary(self) -> Dict[str, Any]:
        """Get access control summary."""
        return {
            'total_users': len(self.user_roles),
            'active_sessions': len(self.active_sessions),
            'total_resources': len(self.resource_access),
            'locked_accounts': sum(1 for user_id in self.failed_attempts.keys() if self._is_account_locked(user_id)),
            'role_distribution': {
                role.value: sum(1 for ur in self.user_roles.values() if ur.role == role)
                for role in Role
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global access control manager
access_control = AccessControlManager()


# Decorator for permission checking
def require_permission(permission: Permission, resource_type: Optional[str] = None):
    """Decorator to require specific permission."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user context
            user_id = kwargs.get('user_id')
            session_id = kwargs.get('session_id')
            resource_id = kwargs.get('resource_id')
            
            if not user_id:
                raise PermissionError("User ID required")
            
            # Validate session if provided
            if session_id:
                context = access_control.validate_session(session_id)
                if not context or context.user_id != user_id:
                    raise PermissionError("Invalid session")
            
            # Check permission
            if resource_type and resource_id:
                # Resource-specific permission check
                has_access = access_control.check_resource_access(
                    user_id, resource_type, resource_id, permission
                )
            else:
                # System-level permission check
                has_access = access_control.has_permission(user_id, permission)
            
            if not has_access:
                raise PermissionError(f"Permission denied: {permission.value}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience functions
def assign_user_role(user_id: str, role: Role, granted_by: Optional[str] = None) -> bool:
    """Assign role to user."""
    return access_control.assign_role(user_id, role, granted_by)


def check_permission(user_id: str, permission: Permission) -> bool:
    """Check if user has permission."""
    return access_control.has_permission(user_id, permission)


def create_user_session(user_id: str, ip_address: Optional[str] = None) -> str:
    """Create user session."""
    context = AccessContext(
        user_id=user_id,
        ip_address=ip_address
    )
    return access_control.create_session(user_id, context)


def validate_user_session(session_id: str) -> Optional[str]:
    """Validate session and return user ID."""
    context = access_control.validate_session(session_id)
    return context.user_id if context else None


def share_document(document_id: str, owner_id: str, target_user_id: str, 
                  permissions: List[str]) -> bool:
    """Share document with user."""
    perm_set = {Permission(p) for p in permissions}
    return access_control.share_resource("document", document_id, owner_id, target_user_id, perm_set)


def check_document_access(user_id: str, document_id: str, permission: str) -> bool:
    """Check document access."""
    return access_control.check_resource_access(
        user_id, "document", document_id, Permission(permission)
    )