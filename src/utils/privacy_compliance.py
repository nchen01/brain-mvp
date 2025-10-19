"""Privacy compliance and data management system for GDPR, CCPA, and other regulations."""

import logging
import json
from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import uuid

from .audit_logging import log_security_event, AuditEventType, AuditSeverity
from .access_control import Permission, require_permission

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """Categories of personal data."""
    PERSONAL_IDENTIFIERS = "personal_identifiers"  # Name, email, phone
    SENSITIVE_PERSONAL = "sensitive_personal"      # Health, biometric, etc.
    BEHAVIORAL_DATA = "behavioral_data"            # Usage patterns, preferences
    TECHNICAL_DATA = "technical_data"              # IP addresses, device info
    DOCUMENT_CONTENT = "document_content"          # User-uploaded documents
    SYSTEM_LOGS = "system_logs"                    # Application logs


class LegalBasis(str, Enum):
    """Legal basis for data processing under GDPR."""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataSubjectRight(str, Enum):
    """Data subject rights under privacy regulations."""
    ACCESS = "access"                    # Right to access personal data
    RECTIFICATION = "rectification"      # Right to correct inaccurate data
    ERASURE = "erasure"                  # Right to be forgotten
    PORTABILITY = "portability"          # Right to data portability
    RESTRICTION = "restriction"          # Right to restrict processing
    OBJECTION = "objection"              # Right to object to processing
    WITHDRAW_CONSENT = "withdraw_consent" # Right to withdraw consent


class RetentionPeriod(str, Enum):
    """Data retention periods."""
    SHORT_TERM = "30_days"      # 30 days
    MEDIUM_TERM = "1_year"      # 1 year
    LONG_TERM = "7_years"       # 7 years (legal requirement)
    INDEFINITE = "indefinite"   # Until user requests deletion


@dataclass
class DataProcessingRecord:
    """Record of data processing activity."""
    record_id: str
    data_category: DataCategory
    legal_basis: LegalBasis
    purpose: str
    data_subjects: Set[str]  # User IDs
    retention_period: RetentionPeriod
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    consent_obtained: bool = False
    consent_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'record_id': self.record_id,
            'data_category': self.data_category.value,
            'legal_basis': self.legal_basis.value,
            'purpose': self.purpose,
            'data_subjects': list(self.data_subjects),
            'retention_period': self.retention_period.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'consent_obtained': self.consent_obtained,
            'consent_date': self.consent_date.isoformat() if self.consent_date else None
        }


@dataclass
class DataSubjectRequest:
    """Data subject rights request."""
    request_id: str
    user_id: str
    request_type: DataSubjectRight
    status: str  # pending, processing, completed, rejected
    requested_at: datetime
    completed_at: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)
    verification_status: str = "pending"  # pending, verified, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'request_type': self.request_type.value,
            'status': self.status,
            'requested_at': self.requested_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'details': self.details,
            'verification_status': self.verification_status
        }


class PrivacyComplianceManager:
    """Privacy compliance and data management system."""
    
    def __init__(self):
        """Initialize privacy compliance manager."""
        self.processing_records: Dict[str, DataProcessingRecord] = {}
        self.subject_requests: Dict[str, DataSubjectRequest] = {}
        self.user_consents: Dict[str, Dict[str, Any]] = {}
        self.retention_policies = self._setup_retention_policies()
        
        # Compliance settings
        self.auto_delete_enabled = True
        self.consent_required_categories = {
            DataCategory.BEHAVIORAL_DATA,
            DataCategory.DOCUMENT_CONTENT
        }
    
    def _setup_retention_policies(self) -> Dict[DataCategory, timedelta]:
        """Setup data retention policies."""
        return {
            DataCategory.PERSONAL_IDENTIFIERS: timedelta(days=2555),  # 7 years
            DataCategory.SENSITIVE_PERSONAL: timedelta(days=365),     # 1 year
            DataCategory.BEHAVIORAL_DATA: timedelta(days=365),        # 1 year
            DataCategory.TECHNICAL_DATA: timedelta(days=90),          # 3 months
            DataCategory.DOCUMENT_CONTENT: timedelta(days=2555),      # 7 years
            DataCategory.SYSTEM_LOGS: timedelta(days=365),            # 1 year
        }
    
    def record_data_processing(self,
                             data_category: DataCategory,
                             legal_basis: LegalBasis,
                             purpose: str,
                             user_ids: Union[str, List[str]],
                             retention_period: Optional[RetentionPeriod] = None,
                             consent_obtained: bool = False) -> str:
        """Record data processing activity."""
        try:
            # Normalize user IDs
            if isinstance(user_ids, str):
                user_ids = [user_ids]
            
            # Generate record ID
            record_id = str(uuid.uuid4())
            
            # Determine retention period
            if retention_period is None:
                default_retention = self.retention_policies.get(data_category, timedelta(days=365))
                if default_retention.days <= 30:
                    retention_period = RetentionPeriod.SHORT_TERM
                elif default_retention.days <= 365:
                    retention_period = RetentionPeriod.MEDIUM_TERM
                else:
                    retention_period = RetentionPeriod.LONG_TERM
            
            # Calculate expiration date
            now = datetime.now(timezone.utc)
            if retention_period == RetentionPeriod.SHORT_TERM:
                expires_at = now + timedelta(days=30)
            elif retention_period == RetentionPeriod.MEDIUM_TERM:
                expires_at = now + timedelta(days=365)
            elif retention_period == RetentionPeriod.LONG_TERM:
                expires_at = now + timedelta(days=2555)  # 7 years
            else:
                expires_at = None
            
            # Create processing record
            record = DataProcessingRecord(
                record_id=record_id,
                data_category=data_category,
                legal_basis=legal_basis,
                purpose=purpose,
                data_subjects=set(user_ids),
                retention_period=retention_period,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                consent_obtained=consent_obtained,
                consent_date=now if consent_obtained else None
            )
            
            self.processing_records[record_id] = record
            
            # Log the processing activity
            log_security_event(
                "data_processing_recorded",
                f"Data processing recorded for {data_category.value}",
                details={
                    'record_id': record_id,
                    'data_category': data_category.value,
                    'legal_basis': legal_basis.value,
                    'user_count': len(user_ids),
                    'retention_period': retention_period.value
                }
            )
            
            logger.info(f"Data processing recorded: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to record data processing: {e}")
            raise
    
    def obtain_consent(self,
                      user_id: str,
                      data_categories: List[DataCategory],
                      purposes: List[str],
                      consent_text: str) -> str:
        """Obtain user consent for data processing."""
        try:
            consent_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            consent_record = {
                'consent_id': consent_id,
                'user_id': user_id,
                'data_categories': [cat.value for cat in data_categories],
                'purposes': purposes,
                'consent_text': consent_text,
                'granted_at': now.isoformat(),
                'withdrawn_at': None,
                'is_active': True
            }
            
            if user_id not in self.user_consents:
                self.user_consents[user_id] = {}
            
            self.user_consents[user_id][consent_id] = consent_record
            
            # Log consent
            log_security_event(
                "consent_obtained",
                f"User consent obtained for {len(data_categories)} data categories",
                user_id=user_id,
                details={
                    'consent_id': consent_id,
                    'data_categories': [cat.value for cat in data_categories],
                    'purposes': purposes
                }
            )
            
            logger.info(f"Consent obtained from user {user_id}: {consent_id}")
            return consent_id
            
        except Exception as e:
            logger.error(f"Failed to obtain consent: {e}")
            raise
    
    def withdraw_consent(self, user_id: str, consent_id: str) -> bool:
        """Withdraw user consent."""
        try:
            if (user_id not in self.user_consents or 
                consent_id not in self.user_consents[user_id]):
                return False
            
            consent_record = self.user_consents[user_id][consent_id]
            consent_record['withdrawn_at'] = datetime.now(timezone.utc).isoformat()
            consent_record['is_active'] = False
            
            # Log consent withdrawal
            log_security_event(
                "consent_withdrawn",
                f"User consent withdrawn",
                user_id=user_id,
                details={
                    'consent_id': consent_id,
                    'data_categories': consent_record['data_categories']
                }
            )
            
            logger.info(f"Consent withdrawn by user {user_id}: {consent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to withdraw consent: {e}")
            return False
    
    def has_valid_consent(self, user_id: str, data_category: DataCategory) -> bool:
        """Check if user has valid consent for data category."""
        if user_id not in self.user_consents:
            return False
        
        for consent_record in self.user_consents[user_id].values():
            if (consent_record['is_active'] and 
                data_category.value in consent_record['data_categories']):
                return True
        
        return False 
   
    def submit_data_subject_request(self,
                                   user_id: str,
                                   request_type: DataSubjectRight,
                                   details: Optional[Dict[str, Any]] = None) -> str:
        """Submit data subject rights request."""
        try:
            request_id = str(uuid.uuid4())
            
            request = DataSubjectRequest(
                request_id=request_id,
                user_id=user_id,
                request_type=request_type,
                status="pending",
                requested_at=datetime.now(timezone.utc),
                details=details or {}
            )
            
            self.subject_requests[request_id] = request
            
            # Log the request
            log_security_event(
                "data_subject_request",
                f"Data subject request submitted: {request_type.value}",
                user_id=user_id,
                details={
                    'request_id': request_id,
                    'request_type': request_type.value
                }
            )
            
            logger.info(f"Data subject request submitted: {request_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to submit data subject request: {e}")
            raise
    
    def process_access_request(self, request_id: str) -> Dict[str, Any]:
        """Process data access request (GDPR Article 15)."""
        try:
            if request_id not in self.subject_requests:
                raise ValueError("Request not found")
            
            request = self.subject_requests[request_id]
            
            if request.request_type != DataSubjectRight.ACCESS:
                raise ValueError("Invalid request type")
            
            user_id = request.user_id
            
            # Collect all data for the user
            user_data = {
                'user_id': user_id,
                'data_collected': {},
                'processing_activities': [],
                'consents': [],
                'retention_info': {}
            }
            
            # Find processing records for this user
            for record in self.processing_records.values():
                if user_id in record.data_subjects:
                    user_data['processing_activities'].append({
                        'purpose': record.purpose,
                        'legal_basis': record.legal_basis.value,
                        'data_category': record.data_category.value,
                        'retention_period': record.retention_period.value,
                        'created_at': record.created_at.isoformat()
                    })
            
            # Find consents for this user
            if user_id in self.user_consents:
                for consent in self.user_consents[user_id].values():
                    user_data['consents'].append({
                        'consent_id': consent['consent_id'],
                        'data_categories': consent['data_categories'],
                        'purposes': consent['purposes'],
                        'granted_at': consent['granted_at'],
                        'is_active': consent['is_active']
                    })
            
            # Update request status
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            request.details['response_data'] = user_data
            
            logger.info(f"Access request processed: {request_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to process access request: {e}")
            raise
    
    def process_erasure_request(self, request_id: str) -> bool:
        """Process data erasure request (GDPR Article 17 - Right to be forgotten)."""
        try:
            if request_id not in self.subject_requests:
                raise ValueError("Request not found")
            
            request = self.subject_requests[request_id]
            
            if request.request_type != DataSubjectRight.ERASURE:
                raise ValueError("Invalid request type")
            
            user_id = request.user_id
            
            # Remove user from processing records
            records_to_update = []
            for record in self.processing_records.values():
                if user_id in record.data_subjects:
                    record.data_subjects.discard(user_id)
                    record.updated_at = datetime.now(timezone.utc)
                    records_to_update.append(record.record_id)
            
            # Remove user consents
            if user_id in self.user_consents:
                del self.user_consents[user_id]
            
            # Update request status
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            request.details['records_updated'] = records_to_update
            
            # Log erasure
            log_security_event(
                "data_erasure_completed",
                f"Data erasure completed for user",
                user_id=user_id,
                details={
                    'request_id': request_id,
                    'records_updated': len(records_to_update)
                }
            )
            
            logger.info(f"Erasure request processed: {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process erasure request: {e}")
            return False
    
    def process_portability_request(self, request_id: str) -> Dict[str, Any]:
        """Process data portability request (GDPR Article 20)."""
        try:
            if request_id not in self.subject_requests:
                raise ValueError("Request not found")
            
            request = self.subject_requests[request_id]
            
            if request.request_type != DataSubjectRight.PORTABILITY:
                raise ValueError("Invalid request type")
            
            user_id = request.user_id
            
            # Collect portable data (data provided by user or generated through use)
            portable_data = {
                'user_id': user_id,
                'export_date': datetime.now(timezone.utc).isoformat(),
                'data_format': 'JSON',
                'documents': [],
                'preferences': {},
                'usage_data': {}
            }
            
            # Find user's documents and data
            for record in self.processing_records.values():
                if (user_id in record.data_subjects and 
                    record.data_category in [DataCategory.DOCUMENT_CONTENT, DataCategory.BEHAVIORAL_DATA]):
                    
                    portable_data['usage_data'][record.record_id] = {
                        'purpose': record.purpose,
                        'data_category': record.data_category.value,
                        'created_at': record.created_at.isoformat()
                    }
            
            # Update request status
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            request.details['portable_data'] = portable_data
            
            logger.info(f"Portability request processed: {request_id}")
            return portable_data
            
        except Exception as e:
            logger.error(f"Failed to process portability request: {e}")
            raise
    
    def apply_retention_policies(self) -> Dict[str, Any]:
        """Apply data retention policies and delete expired data."""
        try:
            now = datetime.now(timezone.utc)
            deletion_summary = {
                'timestamp': now.isoformat(),
                'records_processed': 0,
                'records_deleted': 0,
                'users_affected': set()
            }
            
            records_to_delete = []
            
            for record_id, record in self.processing_records.items():
                deletion_summary['records_processed'] += 1
                
                # Check if record has expired
                if record.expires_at and now > record.expires_at:
                    records_to_delete.append(record_id)
                    deletion_summary['users_affected'].update(record.data_subjects)
            
            # Delete expired records
            for record_id in records_to_delete:
                del self.processing_records[record_id]
                deletion_summary['records_deleted'] += 1
            
            # Convert set to list for JSON serialization
            deletion_summary['users_affected'] = list(deletion_summary['users_affected'])
            
            if deletion_summary['records_deleted'] > 0:
                log_security_event(
                    "data_retention_applied",
                    f"Data retention policy applied: {deletion_summary['records_deleted']} records deleted",
                    details=deletion_summary
                )
            
            logger.info(f"Retention policies applied: {deletion_summary['records_deleted']} records deleted")
            return deletion_summary
            
        except Exception as e:
            logger.error(f"Failed to apply retention policies: {e}")
            return {'error': str(e)}
    
    def anonymize_user_data(self, user_id: str) -> bool:
        """Anonymize user data while preserving analytical value."""
        try:
            # Generate anonymous identifier
            anonymous_id = hashlib.sha256(f"anon_{user_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            
            # Update processing records
            records_updated = 0
            for record in self.processing_records.values():
                if user_id in record.data_subjects:
                    record.data_subjects.discard(user_id)
                    record.data_subjects.add(f"anon_{anonymous_id}")
                    record.updated_at = datetime.now(timezone.utc)
                    records_updated += 1
            
            # Remove personal consents (anonymized data doesn't need consent)
            if user_id in self.user_consents:
                del self.user_consents[user_id]
            
            # Log anonymization
            log_security_event(
                "data_anonymization",
                f"User data anonymized",
                user_id=user_id,
                details={
                    'anonymous_id': f"anon_{anonymous_id}",
                    'records_updated': records_updated
                }
            )
            
            logger.info(f"User data anonymized: {user_id} -> anon_{anonymous_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to anonymize user data: {e}")
            return False
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate privacy compliance report."""
        try:
            now = datetime.now(timezone.utc)
            
            # Count records by category and legal basis
            category_counts = {}
            legal_basis_counts = {}
            
            for record in self.processing_records.values():
                category = record.data_category.value
                basis = record.legal_basis.value
                
                category_counts[category] = category_counts.get(category, 0) + 1
                legal_basis_counts[basis] = legal_basis_counts.get(basis, 0) + 1
            
            # Count active consents
            active_consents = 0
            total_consents = 0
            
            for user_consents in self.user_consents.values():
                for consent in user_consents.values():
                    total_consents += 1
                    if consent['is_active']:
                        active_consents += 1
            
            # Count pending requests
            pending_requests = sum(1 for req in self.subject_requests.values() if req.status == "pending")
            
            # Check for expired records
            expired_records = sum(
                1 for record in self.processing_records.values()
                if record.expires_at and now > record.expires_at
            )
            
            report = {
                'report_date': now.isoformat(),
                'data_processing': {
                    'total_records': len(self.processing_records),
                    'by_category': category_counts,
                    'by_legal_basis': legal_basis_counts,
                    'expired_records': expired_records
                },
                'consent_management': {
                    'total_consents': total_consents,
                    'active_consents': active_consents,
                    'consent_rate': active_consents / total_consents if total_consents > 0 else 0
                },
                'data_subject_requests': {
                    'total_requests': len(self.subject_requests),
                    'pending_requests': pending_requests,
                    'by_type': {}
                },
                'compliance_status': {
                    'retention_compliance': expired_records == 0,
                    'consent_compliance': active_consents > 0,
                    'request_backlog': pending_requests
                }
            }
            
            # Count requests by type
            for request in self.subject_requests.values():
                req_type = request.request_type.value
                report['data_subject_requests']['by_type'][req_type] = \
                    report['data_subject_requests']['by_type'].get(req_type, 0) + 1
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {'error': str(e)}


# Global privacy compliance manager
privacy_manager = PrivacyComplianceManager()


# Convenience functions
def record_user_data_processing(user_id: str, 
                               data_category: DataCategory,
                               purpose: str,
                               legal_basis: LegalBasis = LegalBasis.LEGITIMATE_INTERESTS) -> str:
    """Record user data processing."""
    return privacy_manager.record_data_processing(
        data_category, legal_basis, purpose, user_id
    )


def obtain_user_consent(user_id: str, 
                       data_categories: List[DataCategory],
                       purposes: List[str],
                       consent_text: str) -> str:
    """Obtain user consent."""
    return privacy_manager.obtain_consent(user_id, data_categories, purposes, consent_text)


def submit_erasure_request(user_id: str) -> str:
    """Submit data erasure request."""
    return privacy_manager.submit_data_subject_request(user_id, DataSubjectRight.ERASURE)


def submit_access_request(user_id: str) -> str:
    """Submit data access request."""
    return privacy_manager.submit_data_subject_request(user_id, DataSubjectRight.ACCESS)


def apply_data_retention() -> Dict[str, Any]:
    """Apply data retention policies."""
    return privacy_manager.apply_retention_policies()


def get_privacy_report() -> Dict[str, Any]:
    """Get privacy compliance report."""
    return privacy_manager.get_compliance_report()


# Decorator for privacy-compliant data processing
def privacy_compliant_processing(data_category: DataCategory, 
                                purpose: str,
                                legal_basis: LegalBasis = LegalBasis.LEGITIMATE_INTERESTS):
    """Decorator for privacy-compliant data processing."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user ID
            user_id = kwargs.get('user_id')
            if not user_id:
                raise ValueError("User ID required for privacy compliance")
            
            # Check if consent is required
            if data_category in privacy_manager.consent_required_categories:
                if not privacy_manager.has_valid_consent(user_id, data_category):
                    raise PermissionError(f"Consent required for {data_category.value} processing")
            
            # Record the processing activity
            record_id = privacy_manager.record_data_processing(
                data_category, legal_basis, purpose, user_id
            )
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log processing failure
                logger.error(f"Privacy-compliant processing failed for record {record_id}: {e}")
                raise
        
        return wrapper
    return decorator