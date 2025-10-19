"""Tests for the security and privacy system."""

import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.utils.security_validation import (
    InputValidator, SecurityLevel, ValidationRule, ValidationError,
    validate_document_id, validate_filename, sanitize_for_logs
)
from src.utils.secure_storage import (
    SecureFileStorage, EncryptionLevel, FileMetadata,
    store_file_securely, retrieve_file_securely
)
from src.utils.audit_logging import (
    AuditLogger, AuditEventType, AuditSeverity, AuditEvent,
    log_document_operation, log_authentication_event
)
from src.utils.access_control import (
    AccessControlManager, Permission, Role, AccessContext,
    assign_user_role, check_permission, create_user_session
)
from src.utils.privacy_compliance import (
    PrivacyComplianceManager, DataCategory, LegalBasis, DataSubjectRight,
    record_user_data_processing, obtain_user_consent, submit_erasure_request
)


class TestInputValidator:
    """Test input validation and sanitization."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = InputValidator(SecurityLevel.HIGH)
        
        assert validator.security_level == SecurityLevel.HIGH
        assert isinstance(validator.validation_rules, dict)
        assert len(validator.validation_rules) > 0
    
    def test_field_validation_success(self):
        """Test successful field validation."""
        validator = InputValidator()
        
        # Add test rule
        rule = ValidationRule(
            name="test_field",
            min_length=3,
            max_length=10,
            pattern=r'^[a-zA-Z]+$'
        )
        validator.add_rule("test_field", rule)
        
        # Valid input
        result = validator.validate_field("test_field", "hello")
        assert result == "hello"
    
    def test_field_validation_failure(self):
        """Test field validation failure."""
        validator = InputValidator()
        
        rule = ValidationRule(
            name="test_field",
            min_length=5,
            max_length=10,
            required=True
        )
        validator.add_rule("test_field", rule)
        
        # Too short
        with pytest.raises(ValidationError):
            validator.validate_field("test_field", "hi")
        
        # Required field missing
        with pytest.raises(ValidationError):
            validator.validate_field("test_field", None)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        validator = InputValidator()
        
        dangerous_filename = "../../../etc/passwd"
        sanitized = validator._sanitize_filename(dangerous_filename)
        
        assert ".." not in sanitized
        assert "/" not in sanitized
        assert sanitized != dangerous_filename
    
    def test_html_sanitization(self):
        """Test HTML sanitization."""
        validator = InputValidator()
        
        malicious_html = '<script>alert("xss")</script><p>Safe content</p>'
        sanitized = validator._sanitize_html(malicious_html)
        
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
        assert '&lt;' in sanitized or '&gt;' in sanitized  # HTML escaped
    
    def test_file_upload_validation(self):
        """Test file upload validation."""
        validator = InputValidator()
        
        # Valid file
        content = b"This is a test file content"
        result = validator.validate_file_upload(
            "test.txt", 
            content, 
            allowed_types=['.txt'], 
            max_size=1000
        )
        
        assert result['valid'] is True
        assert result['filename'] == "test.txt"
        assert result['size'] == len(content)
    
    def test_malicious_content_detection(self):
        """Test malicious content detection."""
        validator = InputValidator()
        
        malicious_content = b'<script>document.cookie</script>'
        is_malicious = validator._contains_malicious_content(malicious_content)
        
        assert is_malicious is True
        
        safe_content = b'This is safe content'
        is_safe = validator._contains_malicious_content(safe_content)
        
        assert is_safe is False


class TestSecureStorage:
    """Test secure file storage system."""
    
    def test_storage_initialization(self):
        """Test storage system initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SecureFileStorage(
                storage_root=temp_dir,
                encryption_level=EncryptionLevel.BASIC
            )
            
            assert storage.storage_root == temp_dir
            assert storage.encryption_level == EncryptionLevel.BASIC
            assert storage.storage_root.exists()
    
    def test_file_storage_and_retrieval(self):
        """Test file storage and retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SecureFileStorage(storage_root=temp_dir)
            
            # Create test file
            test_content = "This is test content"
            test_file = os.path.join(temp_dir, "test_input.txt")
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            # Store file
            file_id = storage.store_file(test_file, "test.txt", owner="user123")
            
            assert file_id is not None
            assert len(file_id) > 0
            
            # Retrieve file
            retrieved_path = storage.retrieve_file(file_id, requester="user123")
            
            assert os.path.exists(retrieved_path)
            
            # Verify content
            with open(retrieved_path, 'r') as f:
                retrieved_content = f.read()
            
            assert retrieved_content == test_content
    
    def test_file_metadata(self):
        """Test file metadata management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SecureFileStorage(storage_root=temp_dir)
            
            # Create and store test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            file_id = storage.store_file(test_file, "test.txt", owner="user123")
            
            # Get metadata
            metadata = storage.get_file_metadata(file_id)
            
            assert metadata is not None
            assert metadata.file_id == file_id
            assert metadata.original_filename == "test.txt"
            assert metadata.owner == "user123"
            assert metadata.file_size > 0
    
    def test_secure_file_deletion(self):
        """Test secure file deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SecureFileStorage(storage_root=temp_dir)
            
            # Create and store test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("sensitive content")
            
            file_id = storage.store_file(test_file, "test.txt", owner="user123")
            
            # Delete file
            storage.delete_file(file_id, requester="user123", secure_delete=True)
            
            # Verify file is deleted
            metadata = storage.get_file_metadata(file_id)
            assert metadata is None


class TestAuditLogging:
    """Test audit logging system."""
    
    def test_audit_logger_initialization(self):
        """Test audit logger initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "audit.log")
            logger = AuditLogger(log_file=log_file)
            
            assert logger.log_file == log_file
            assert isinstance(logger.recent_events, list)
            assert len(logger.recent_events) == 0
    
    def test_event_logging(self):
        """Test audit event logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "audit.log")
            logger = AuditLogger(log_file=log_file)
            
            # Log an event
            event_id = logger.log_event(
                event_type=AuditEventType.DOCUMENT_UPLOAD,
                action="upload_document",
                user_id="user123",
                resource_id="doc456",
                details={"filename": "test.pdf"}
            )
            
            assert event_id is not None
            assert len(logger.recent_events) == 1
            
            # Check event details
            event = logger.recent_events[0]
            assert event.event_type == AuditEventType.DOCUMENT_UPLOAD
            assert event.user_id == "user123"
            assert event.resource_id == "doc456"
    
    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "audit.log")
            logger = AuditLogger(log_file=log_file)
            
            # High-risk event
            logger.log_event(
                event_type=AuditEventType.SECURITY_VIOLATION,
                action="unauthorized_access",
                user_id="user123"
            )
            
            event = logger.recent_events[0]
            assert event.risk_score >= 70  # Should be high risk
    
    def test_security_summary(self):
        """Test security summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "audit.log")
            logger = AuditLogger(log_file=log_file)
            
            # Log various events
            logger.log_event(AuditEventType.LOGIN_SUCCESS, "login", user_id="user1")
            logger.log_event(AuditEventType.LOGIN_FAILURE, "login", user_id="user2")
            logger.log_event(AuditEventType.DOCUMENT_UPLOAD, "upload", user_id="user1")
            
            summary = logger.get_security_summary()
            
            assert summary['total_events'] == 3
            assert 'severity_counts' in summary
            assert 'type_counts' in summary


class TestAccessControl:
    """Test access control system."""
    
    def test_access_control_initialization(self):
        """Test access control manager initialization."""
        acm = AccessControlManager()
        
        assert isinstance(acm.user_roles, dict)
        assert isinstance(acm.resource_access, dict)
        assert isinstance(acm.role_permissions, dict)
    
    def test_role_assignment(self):
        """Test user role assignment."""
        acm = AccessControlManager()
        
        # Assign role
        success = acm.assign_role("user123", Role.USER)
        assert success is True
        
        # Check permissions
        permissions = acm.get_user_permissions("user123")
        assert Permission.DOCUMENT_READ in permissions
        assert Permission.DOCUMENT_WRITE in permissions
    
    def test_permission_checking(self):
        """Test permission checking."""
        acm = AccessControlManager()
        
        # Assign role
        acm.assign_role("user123", Role.ADMIN)
        
        # Check permissions
        assert acm.has_permission("user123", Permission.DOCUMENT_READ) is True
        assert acm.has_permission("user123", Permission.SYSTEM_ADMIN) is False
        assert acm.has_permission("user123", Permission.USER_WRITE) is True
    
    def test_resource_access_control(self):
        """Test resource access control."""
        acm = AccessControlManager()
        
        # Create resource
        acm.create_resource_access("document", "doc123", "user123")
        
        # Check owner access
        has_access = acm.check_resource_access(
            "user123", "document", "doc123", Permission.DOCUMENT_READ
        )
        assert has_access is True
        
        # Check non-owner access
        has_access = acm.check_resource_access(
            "user456", "document", "doc123", Permission.DOCUMENT_READ
        )
        assert has_access is False
    
    def test_resource_sharing(self):
        """Test resource sharing."""
        acm = AccessControlManager()
        
        # Create resource
        acm.create_resource_access("document", "doc123", "user123")
        
        # Share resource
        success = acm.share_resource(
            "document", "doc123", "user123", "user456", 
            {Permission.DOCUMENT_READ}
        )
        assert success is True
        
        # Check shared access
        has_access = acm.check_resource_access(
            "user456", "document", "doc123", Permission.DOCUMENT_READ
        )
        assert has_access is True
    
    def test_session_management(self):
        """Test session management."""
        acm = AccessControlManager()
        
        # Create session
        context = AccessContext(user_id="user123", ip_address="192.168.1.1")
        session_id = acm.create_session("user123", context)
        
        assert session_id is not None
        assert len(session_id) > 0
        
        # Validate session
        validated_context = acm.validate_session(session_id)
        assert validated_context is not None
        assert validated_context.user_id == "user123"
        
        # Revoke session
        success = acm.revoke_session(session_id)
        assert success is True
        
        # Validate revoked session
        validated_context = acm.validate_session(session_id)
        assert validated_context is None


class TestPrivacyCompliance:
    """Test privacy compliance system."""
    
    def test_privacy_manager_initialization(self):
        """Test privacy compliance manager initialization."""
        pm = PrivacyComplianceManager()
        
        assert isinstance(pm.processing_records, dict)
        assert isinstance(pm.subject_requests, dict)
        assert isinstance(pm.user_consents, dict)
    
    def test_data_processing_recording(self):
        """Test data processing recording."""
        pm = PrivacyComplianceManager()
        
        # Record processing
        record_id = pm.record_data_processing(
            DataCategory.DOCUMENT_CONTENT,
            LegalBasis.CONSENT,
            "Document storage and processing",
            "user123"
        )
        
        assert record_id is not None
        assert record_id in pm.processing_records
        
        record = pm.processing_records[record_id]
        assert record.data_category == DataCategory.DOCUMENT_CONTENT
        assert "user123" in record.data_subjects
    
    def test_consent_management(self):
        """Test consent management."""
        pm = PrivacyComplianceManager()
        
        # Obtain consent
        consent_id = pm.obtain_consent(
            "user123",
            [DataCategory.DOCUMENT_CONTENT, DataCategory.BEHAVIORAL_DATA],
            ["Document processing", "Analytics"],
            "I consent to processing my data"
        )
        
        assert consent_id is not None
        assert "user123" in pm.user_consents
        
        # Check consent
        has_consent = pm.has_valid_consent("user123", DataCategory.DOCUMENT_CONTENT)
        assert has_consent is True
        
        # Withdraw consent
        success = pm.withdraw_consent("user123", consent_id)
        assert success is True
        
        # Check withdrawn consent
        has_consent = pm.has_valid_consent("user123", DataCategory.DOCUMENT_CONTENT)
        assert has_consent is False
    
    def test_data_subject_requests(self):
        """Test data subject rights requests."""
        pm = PrivacyComplianceManager()
        
        # Record some processing
        pm.record_data_processing(
            DataCategory.DOCUMENT_CONTENT,
            LegalBasis.CONSENT,
            "Document storage",
            "user123"
        )
        
        # Submit access request
        request_id = pm.submit_data_subject_request(
            "user123", DataSubjectRight.ACCESS
        )
        
        assert request_id is not None
        assert request_id in pm.subject_requests
        
        # Process access request
        user_data = pm.process_access_request(request_id)
        
        assert 'user_id' in user_data
        assert user_data['user_id'] == "user123"
        assert 'processing_activities' in user_data
    
    def test_data_erasure(self):
        """Test data erasure (right to be forgotten)."""
        pm = PrivacyComplianceManager()
        
        # Record processing
        record_id = pm.record_data_processing(
            DataCategory.DOCUMENT_CONTENT,
            LegalBasis.CONSENT,
            "Document storage",
            "user123"
        )
        
        # Submit erasure request
        request_id = pm.submit_data_subject_request(
            "user123", DataSubjectRight.ERASURE
        )
        
        # Process erasure request
        success = pm.process_erasure_request(request_id)
        assert success is True
        
        # Verify data is removed
        record = pm.processing_records[record_id]
        assert "user123" not in record.data_subjects
    
    def test_retention_policies(self):
        """Test data retention policies."""
        pm = PrivacyComplianceManager()
        
        # Create expired record
        record_id = pm.record_data_processing(
            DataCategory.TECHNICAL_DATA,
            LegalBasis.LEGITIMATE_INTERESTS,
            "System logs",
            "user123"
        )
        
        # Manually set expiration to past
        record = pm.processing_records[record_id]
        record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Apply retention policies
        summary = pm.apply_retention_policies()
        
        assert summary['records_deleted'] == 1
        assert record_id not in pm.processing_records
    
    def test_compliance_report(self):
        """Test compliance report generation."""
        pm = PrivacyComplianceManager()
        
        # Add some test data
        pm.record_data_processing(
            DataCategory.DOCUMENT_CONTENT,
            LegalBasis.CONSENT,
            "Document processing",
            "user123"
        )
        
        pm.obtain_consent(
            "user123",
            [DataCategory.DOCUMENT_CONTENT],
            ["Document processing"],
            "I consent"
        )
        
        # Generate report
        report = pm.get_compliance_report()
        
        assert 'data_processing' in report
        assert 'consent_management' in report
        assert 'compliance_status' in report
        assert report['data_processing']['total_records'] >= 1


class TestSecurityIntegration:
    """Test integration between security components."""
    
    def test_audit_and_access_control_integration(self):
        """Test integration between audit logging and access control."""
        # This would test that access control events are properly logged
        pass
    
    def test_privacy_and_storage_integration(self):
        """Test integration between privacy compliance and secure storage."""
        # This would test that file storage respects privacy requirements
        pass
    
    def test_validation_and_audit_integration(self):
        """Test integration between input validation and audit logging."""
        # This would test that validation failures are properly audited
        pass


if __name__ == "__main__":
    pytest.main([__file__])