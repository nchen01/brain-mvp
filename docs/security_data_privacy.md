# Security and Data Privacy System

This document describes the comprehensive security and data privacy system implemented for DocForge, ensuring compliance with GDPR, CCPA, and other privacy regulations.

## Overview

The security system provides:

- **Input Validation and Sanitization**: Comprehensive validation to prevent injection attacks
- **Secure File Handling**: Encrypted storage with access controls and secure deletion
- **Audit Logging**: Complete audit trail for all document and system operations
- **Access Control**: Role-based permissions with resource-level access control
- **Privacy Compliance**: GDPR/CCPA compliance with data subject rights and retention policies

## Architecture

### Core Components

1. **SecurityValidation**: Input validation and sanitization
2. **SecureStorage**: Encrypted file storage with metadata management
3. **AuditLogging**: Comprehensive audit logging with risk assessment
4. **AccessControl**: Role-based access control with session management
5. **PrivacyCompliance**: Data protection and privacy rights management
6. **SecurityIntegration**: Central integration layer

## Usage

### Basic Setup

```python
from src.utils.security_integration import setup_docforge_security

# Initialize with default security configuration
setup_docforge_security()
```

### Custom Configuration

```python
from src.utils.security_integration import initialize_docforge_security

config = {
    'validation': {
        'level': 'high'  # low, medium, high, strict
    },
    'storage': {
        'encryption_level': 'strong',  # none, basic, strong
        'max_file_size': 200 * 1024 * 1024  # 200MB
    },
    'audit': {
        'console_logging': True
    },
    'access_control': {
        'max_failed_attempts': 3,
        'session_timeout_hours': 8
    },
    'privacy': {
        'auto_delete': True
    },
    'admin_user': {
        'user_id': 'admin@docforge.com'
    }
}

initialize_docforge_security(config)
```

## Input Validation and Sanitization

### Validation Rules

```python
from src.utils.security_validation import InputValidator, ValidationRule, SecurityLevel

# Create validator with security level
validator = InputValidator(SecurityLevel.HIGH)

# Add custom validation rule
rule = ValidationRule(
    name="document_title",
    min_length=1,
    max_length=255,
    pattern=r'^[a-zA-Z0-9\s._-]+$',
    forbidden_chars='<>"|',
    sanitizer=lambda x: x.strip()
)

validator.add_rule("document_title", rule)

# Validate input
try:
    clean_title = validator.validate_field("document_title", user_input)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### File Upload Validation

```python
from src.utils.security_validation import validate_filename

# Validate and sanitize filename
safe_filename = validate_filename("../../../etc/passwd")
# Returns: "___etc_passwd" (sanitized)

# Validate file upload
validation_result = validator.validate_file_upload(
    filename="document.pdf",
    content=file_bytes,
    allowed_types=['.pdf', '.docx', '.txt'],
    max_size=10 * 1024 * 1024  # 10MB
)

if validation_result['valid']:
    print(f"File is safe: {validation_result['filename']}")
else:
    print(f"File rejected: {validation_result['errors']}")
```

### Input Sanitization

```python
from src.utils.security_validation import sanitize_for_logs, sanitize_error_message

# Sanitize data for logging (removes sensitive information)
safe_log_data = sanitize_for_logs({
    'user': 'john@example.com',
    'password': 'secret123',
    'action': 'login'
})
# Returns: {'user': 'john@example.com', 'password': '***', 'action': 'login'}

# Sanitize error messages (removes paths and sensitive details)
safe_error = sanitize_error_message("File not found: /home/user/secret/file.txt")
# Returns: "File not found: [PATH]"
```

## Secure File Storage

### File Storage with Encryption

```python
from src.utils.secure_storage import store_file_securely, retrieve_file_securely

# Store file securely
file_id = store_file_securely(
    file_path="/tmp/document.pdf",
    filename="important_document.pdf",
    owner="user123"
)

# Retrieve file securely
retrieved_path = retrieve_file_securely(
    file_id=file_id,
    requester="user123"
)
```

### Advanced Storage Operations

```python
from src.utils.secure_storage import SecureFileStorage, EncryptionLevel

# Create storage with strong encryption
storage = SecureFileStorage(
    storage_root="secure_documents",
    encryption_level=EncryptionLevel.STRONG,
    max_file_size=500 * 1024 * 1024  # 500MB
)

# Store with metadata
file_id = storage.store_file(
    file_path="document.pdf",
    original_filename="contract.pdf",
    owner="user123",
    tags={"department": "legal", "confidential": "true"},
    permissions="600"  # Owner read/write only
)

# Get file metadata
metadata = storage.get_file_metadata(file_id)
print(f"File: {metadata.original_filename}")
print(f"Size: {metadata.file_size} bytes")
print(f"Encrypted: {metadata.encryption_level}")

# Secure deletion
storage.delete_file(file_id, requester="user123", secure_delete=True)
```

## Audit Logging

### Automatic Audit Logging

```python
from src.utils.audit_logging import audit_operation, AuditEventType

@audit_operation(AuditEventType.DOCUMENT_UPLOAD, "upload_document", "document")
def upload_document(file_path: str, user_id: str, session_id: str):
    # Document upload logic
    return {"success": True, "file_id": "doc123"}

# Usage automatically logs the operation
result = upload_document("file.pdf", user_id="user123", session_id="sess456")
```

### Manual Audit Logging

```python
from src.utils.audit_logging import log_document_operation, log_security_event

# Log document operations
log_document_operation(
    operation="download",
    document_id="doc123",
    user_id="user456",
    result="success",
    details={"filename": "report.pdf", "size": 1024000}
)

# Log security events
log_security_event(
    event_type="access_denied",
    action="unauthorized_file_access",
    user_id="user789",
    resource_id="doc123",
    severity=AuditSeverity.HIGH,
    details={"reason": "insufficient_permissions"}
)
```

### Audit Analysis

```python
from src.utils.audit_logging import get_audit_summary, get_recent_audit_events

# Get security summary
summary = get_audit_summary()
print(f"Total events: {summary['total_events']}")
print(f"High-risk events: {len(summary['high_risk_events'])}")

# Get recent events
recent_events = get_recent_audit_events(limit=100)
for event in recent_events:
    print(f"{event['timestamp']}: {event['event_type']} - {event['action']}")
```

## Access Control and Permissions

### Role Management

```python
from src.utils.access_control import assign_user_role, Role, Permission

# Assign roles to users
assign_user_role("admin@company.com", Role.ADMIN)
assign_user_role("user@company.com", Role.USER)
assign_user_role("moderator@company.com", Role.MODERATOR)

# Check permissions
from src.utils.access_control import check_permission

has_admin_access = check_permission("admin@company.com", Permission.SYSTEM_ADMIN)
can_delete_docs = check_permission("user@company.com", Permission.DOCUMENT_DELETE)
```

### Session Management

```python
from src.utils.access_control import create_user_session, validate_user_session

# Create user session
session_id = create_user_session(
    user_id="user123",
    ip_address="192.168.1.100"
)

# Validate session
user_id = validate_user_session(session_id)
if user_id:
    print(f"Valid session for user: {user_id}")
else:
    print("Invalid or expired session")
```

### Resource Access Control

```python
from src.utils.access_control import share_document, check_document_access

# Share document with specific permissions
success = share_document(
    document_id="doc123",
    owner_id="user123",
    target_user_id="user456",
    permissions=["document:read", "document:write"]
)

# Check document access
has_access = check_document_access(
    user_id="user456",
    document_id="doc123",
    permission="document:read"
)
```

### Permission Decorators

```python
from src.utils.access_control import require_permission, Permission

@require_permission(Permission.DOCUMENT_WRITE, resource_type="document")
def modify_document(document_id: str, user_id: str, session_id: str, content: str):
    # Document modification logic
    pass

# Usage - automatically checks permissions
modify_document(
    document_id="doc123",
    user_id="user456",
    session_id="sess789",
    content="Updated content"
)
```

## Privacy Compliance

### Data Processing Records

```python
from src.utils.privacy_compliance import record_user_data_processing, DataCategory, LegalBasis

# Record data processing activity
record_id = record_user_data_processing(
    user_id="user123",
    data_category=DataCategory.DOCUMENT_CONTENT,
    purpose="Document storage and analysis",
    legal_basis=LegalBasis.CONSENT
)
```

### Consent Management

```python
from src.utils.privacy_compliance import obtain_user_consent, DataCategory

# Obtain user consent
consent_id = obtain_user_consent(
    user_id="user123",
    data_categories=[DataCategory.DOCUMENT_CONTENT, DataCategory.BEHAVIORAL_DATA],
    purposes=["Document processing", "Usage analytics"],
    consent_text="I consent to processing my documents for analysis and improvement of services"
)

# Check consent
from src.utils.privacy_compliance import privacy_manager

has_consent = privacy_manager.has_valid_consent("user123", DataCategory.DOCUMENT_CONTENT)
if not has_consent:
    print("Consent required for this operation")
```

### Data Subject Rights

```python
from src.utils.privacy_compliance import submit_access_request, submit_erasure_request

# Submit data access request (GDPR Article 15)
access_request_id = submit_access_request("user123")

# Process access request
user_data = privacy_manager.process_access_request(access_request_id)
print(f"User data: {user_data}")

# Submit erasure request (Right to be forgotten)
erasure_request_id = submit_erasure_request("user123")

# Process erasure request
success = privacy_manager.process_erasure_request(erasure_request_id)
if success:
    print("User data has been erased")
```

### Data Retention

```python
from src.utils.privacy_compliance import apply_data_retention, get_privacy_report

# Apply data retention policies
retention_summary = apply_data_retention()
print(f"Deleted {retention_summary['records_deleted']} expired records")

# Generate privacy compliance report
report = get_privacy_report()
print(f"Total processing records: {report['data_processing']['total_records']}")
print(f"Active consents: {report['consent_management']['active_consents']}")
```

### Privacy-Compliant Processing

```python
from src.utils.privacy_compliance import privacy_compliant_processing, DataCategory, LegalBasis

@privacy_compliant_processing(
    data_category=DataCategory.DOCUMENT_CONTENT,
    purpose="Document analysis",
    legal_basis=LegalBasis.CONSENT
)
def analyze_document(document_id: str, user_id: str):
    # Document analysis logic
    # Automatically records processing and checks consent
    pass
```

## Integrated Security Operations

### Secure Document Upload

```python
from src.utils.security_integration import secure_upload_document

# Complete secure upload pipeline
result = secure_upload_document(
    file_path="/tmp/document.pdf",
    filename="confidential_report.pdf",
    user_id="user123",
    session_id="sess456"
)

if result['success']:
    print(f"Document uploaded securely: {result['file_id']}")
else:
    print(f"Upload failed: {result.get('error')}")
```

### Secure Document Access

```python
from src.utils.security_integration import secure_access_document

# Secure document access with full permission checking
access_result = secure_access_document(
    file_id="doc123",
    user_id="user456",
    session_id="sess789",
    operation="read"
)

if access_result['success']:
    metadata = access_result['metadata']
    print(f"Access granted to: {metadata['original_filename']}")
```

### User Authentication

```python
from src.utils.security_integration import authenticate_docforge_user

# Authenticate user with security controls
auth_result = authenticate_docforge_user(
    user_id="user@example.com",
    credentials={"password": "hashed_password"},
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

if auth_result['success']:
    session_id = auth_result['session_id']
    permissions = auth_result['permissions']
    print(f"Authentication successful. Session: {session_id}")
```

## Security Configuration

### Security Levels

```python
from src.utils.security_validation import SecurityLevel

# Configure different security levels
security_levels = {
    SecurityLevel.LOW: {
        'description': 'Basic validation, suitable for internal tools',
        'features': ['Basic input sanitization', 'Simple file validation']
    },
    SecurityLevel.MEDIUM: {
        'description': 'Standard security for business applications',
        'features': ['Input validation', 'File type checking', 'Basic audit logging']
    },
    SecurityLevel.HIGH: {
        'description': 'Enhanced security for sensitive data',
        'features': ['Strict validation', 'Malicious content detection', 'Comprehensive auditing']
    },
    SecurityLevel.STRICT: {
        'description': 'Maximum security for highly sensitive environments',
        'features': ['Paranoid validation', 'Advanced threat detection', 'Full audit trail']
    }
}
```

### Encryption Levels

```python
from src.utils.secure_storage import EncryptionLevel

encryption_options = {
    EncryptionLevel.NONE: 'No encryption (not recommended for production)',
    EncryptionLevel.BASIC: 'AES encryption with PBKDF2 key derivation',
    EncryptionLevel.STRONG: 'AES encryption with enhanced key management'
}
```

## Security Monitoring

### System Status

```python
from src.utils.security_integration import get_docforge_security_status

# Get comprehensive security status
status = get_docforge_security_status()

print(f"Security initialized: {status['initialized']}")
print(f"Active sessions: {status['components']['access_control']['active_sessions']}")
print(f"Recent audit events: {status['components']['audit_logging']['recent_events']}")
print(f"Stored files: {status['components']['secure_storage']['total_files']}")
```

### Security Maintenance

```python
from src.utils.security_integration import security_integration

# Run security maintenance tasks
maintenance_result = security_integration.run_security_maintenance()

for task in maintenance_result['tasks_completed']:
    print(f"Completed: {task['task']}")
```

## Best Practices

### Input Validation

1. **Always validate user input** before processing
2. **Use whitelist validation** rather than blacklist
3. **Sanitize data** for different contexts (HTML, SQL, logs)
4. **Validate file uploads** for type, size, and content
5. **Use parameterized queries** to prevent SQL injection

### File Security

1. **Store files outside web root** to prevent direct access
2. **Use encryption** for sensitive documents
3. **Implement secure deletion** for confidential data
4. **Validate file types** by content, not just extension
5. **Set proper file permissions** (600 for sensitive files)

### Access Control

1. **Use principle of least privilege** - grant minimum necessary permissions
2. **Implement session timeouts** to limit exposure
3. **Log all access attempts** for audit trails
4. **Use strong session identifiers** to prevent session hijacking
5. **Implement account lockout** after failed attempts

### Privacy Compliance

1. **Obtain explicit consent** for data processing
2. **Implement data minimization** - collect only necessary data
3. **Provide data portability** options for users
4. **Honor erasure requests** promptly
5. **Apply retention policies** automatically
6. **Document all processing activities** for compliance

### Audit Logging

1. **Log all security-relevant events** including failures
2. **Include sufficient context** for investigation
3. **Protect log integrity** from tampering
4. **Monitor for suspicious patterns** automatically
5. **Retain logs** according to compliance requirements

## Compliance Features

### GDPR Compliance

- **Article 6**: Legal basis for processing documented
- **Article 7**: Consent management with withdrawal options
- **Article 15**: Right of access with data export
- **Article 17**: Right to erasure (right to be forgotten)
- **Article 20**: Right to data portability
- **Article 25**: Data protection by design and by default
- **Article 30**: Records of processing activities
- **Article 32**: Security of processing with encryption

### CCPA Compliance

- **Right to Know**: Data access and processing transparency
- **Right to Delete**: Data erasure capabilities
- **Right to Opt-Out**: Consent withdrawal mechanisms
- **Non-Discrimination**: Equal service regardless of privacy choices

## Error Handling

### Security Exceptions

```python
from src.utils.security_validation import ValidationError
from src.utils.secure_storage import StorageError

try:
    # Security operations
    pass
except ValidationError as e:
    # Handle input validation errors
    log_security_event("validation_error", str(e))
except StorageError as e:
    # Handle storage security errors
    log_security_event("storage_error", str(e))
except PermissionError as e:
    # Handle access control errors
    log_security_event("permission_denied", str(e))
```

## Testing

### Security Testing

```python
# Run security system tests
python -m pytest tests/unit/test_security_system.py -v

# Test specific components
python -m pytest tests/unit/test_security_system.py::TestInputValidator -v
python -m pytest tests/unit/test_security_system.py::TestSecureStorage -v
python -m pytest tests/unit/test_security_system.py::TestAccessControl -v
```

### Security Validation

```python
from src.utils.security_integration import get_docforge_security_status

# Validate security configuration
status = get_docforge_security_status()
assert status['initialized'] == True
assert status['components']['secure_storage']['encryption_level'] != 'none'
```

This comprehensive security and data privacy system ensures DocForge meets enterprise security requirements while maintaining compliance with modern privacy regulations.