"""Pydantic models for document versioning and lineage system."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class VersionStatus(str, Enum):
    """Document version status."""
    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"


class DeletionReason(str, Enum):
    """Reasons for document deletion."""
    USER_REQUEST = "user_request"
    PRIVACY_REQUEST = "privacy_request"
    COMPLIANCE = "compliance"
    DUPLICATE = "duplicate"
    CORRUPTED = "corrupted"
    ADMIN_ACTION = "admin_action"


class DocumentLineageModel(BaseModel):
    """Document lineage tracking model."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    lineage_uuid: str = Field(..., description="Unique identifier for the document lineage")
    original_filename: str = Field(..., description="Original filename when first uploaded")
    created_by: str = Field(..., description="User ID who created the lineage")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Lineage creation timestamp")
    current_version: int = Field(default=1, description="Current active version number")
    total_versions: int = Field(default=1, description="Total number of versions created")
    is_active: bool = Field(default=True, description="Whether the lineage is active")


class DocumentVersionModel(BaseModel):
    """Individual document version model."""
    doc_uuid: str = Field(..., description="Unique identifier for this document version")
    lineage_uuid: str = Field(..., description="Lineage this version belongs to")
    version_number: int = Field(..., description="Version number within the lineage")
    parent_version: Optional[int] = Field(None, description="Parent version if this is a branch")
    filename: str = Field(..., description="Filename for this version")
    file_path: str = Field(..., description="Storage path for the document file")
    file_type: str = Field(..., description="File type/extension")
    file_hash: str = Field(..., description="Content hash for integrity verification")
    file_size: int = Field(..., description="File size in bytes")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Version creation timestamp")
    user_id: str = Field(..., description="User who created this version")
    labels: List[str] = Field(default_factory=list, description="User-defined labels")
    is_current: bool = Field(default=False, description="Whether this is the current version")
    status: VersionStatus = Field(default=VersionStatus.ACTIVE, description="Version status")
    deletion_reason: Optional[DeletionReason] = Field(None, description="Reason for deletion if deleted")
    edit_source_version: Optional[int] = Field(None, description="Source version if created by editing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    @field_validator('file_hash')
    @classmethod
    def validate_file_hash(cls, v):
        """Validate file hash format."""
        if not v or len(v) != 64:  # SHA-256 hash length
            raise ValueError("File hash must be a valid SHA-256 hash (64 characters)")
        return v
    
    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        """Validate file size is positive."""
        if v <= 0:
            raise ValueError("File size must be positive")
        return v


class DocumentRegistrationRequest(BaseModel):
    """Request model for document registration."""
    filename: str = Field(..., description="Document filename")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., description="File size in bytes")
    user_id: str = Field(..., description="User registering the document")
    labels: List[str] = Field(default_factory=list, description="User-defined labels")
    parent_lineage: Optional[str] = Field(None, description="Parent lineage UUID if adding to existing")
    edit_source_version: Optional[int] = Field(None, description="Source version if editing old version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentRegistrationResponse(BaseModel):
    """Response model for document registration."""
    doc_uuid: str = Field(..., description="Generated document UUID")
    lineage_uuid: str = Field(..., description="Document lineage UUID")
    version_number: int = Field(..., description="Version number assigned")
    file_path: str = Field(..., description="Storage path for the document")
    file_hash: str = Field(..., description="Content hash for verification")
    is_new_lineage: bool = Field(..., description="Whether a new lineage was created")
    is_duplicate: bool = Field(..., description="Whether this is a duplicate document")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Registration timestamp")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class VersionHistoryRequest(BaseModel):
    """Request model for version history."""
    lineage_uuid: str = Field(..., description="Lineage UUID to get history for")
    include_deleted: bool = Field(default=False, description="Include deleted versions")
    limit: Optional[int] = Field(None, description="Maximum number of versions to return")
    offset: Optional[int] = Field(None, description="Offset for pagination")


class VersionHistoryResponse(BaseModel):
    """Response model for version history."""
    lineage_uuid: str = Field(..., description="Lineage UUID")
    original_filename: str = Field(..., description="Original filename")
    total_versions: int = Field(..., description="Total number of versions")
    current_version: int = Field(..., description="Current active version number")
    versions: List[DocumentVersionModel] = Field(..., description="List of versions")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class VersionBranchRequest(BaseModel):
    """Request model for creating a version branch (editing old version)."""
    lineage_uuid: str = Field(..., description="Lineage UUID")
    source_version: int = Field(..., description="Version number to branch from")
    filename: str = Field(..., description="New filename")
    file_size: int = Field(..., description="File size in bytes")
    user_id: str = Field(..., description="User creating the branch")
    labels: List[str] = Field(default_factory=list, description="User-defined labels")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SoftDeleteRequest(BaseModel):
    """Request model for soft deleting a version."""
    doc_uuid: str = Field(..., description="Document UUID to delete")
    reason: DeletionReason = Field(..., description="Reason for deletion")
    user_id: str = Field(..., description="User performing the deletion")
    notes: Optional[str] = Field(None, description="Additional notes about the deletion")


class SoftDeleteResponse(BaseModel):
    """Response model for soft deletion."""
    doc_uuid: str = Field(..., description="Deleted document UUID")
    lineage_uuid: str = Field(..., description="Lineage UUID")
    version_number: int = Field(..., description="Version number deleted")
    deletion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Deletion timestamp")
    reason: DeletionReason = Field(..., description="Deletion reason")
    success: bool = Field(..., description="Whether deletion was successful")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class LineageDeletionRequest(BaseModel):
    """Request model for deleting an entire lineage."""
    lineage_uuid: str = Field(..., description="Lineage UUID to delete")
    reason: DeletionReason = Field(..., description="Reason for deletion")
    user_id: str = Field(..., description="User performing the deletion")
    notes: Optional[str] = Field(None, description="Additional notes about the deletion")
    force: bool = Field(default=False, description="Force deletion even if versions exist")


class RestoreVersionRequest(BaseModel):
    """Request model for restoring a soft-deleted version."""
    doc_uuid: str = Field(..., description="Document UUID to restore")
    user_id: str = Field(..., description="User performing the restoration")
    notes: Optional[str] = Field(None, description="Additional notes about the restoration")


class DuplicateCheckResult(BaseModel):
    """Result model for duplicate checking."""
    is_duplicate: bool = Field(..., description="Whether the document is a duplicate")
    existing_doc_uuid: Optional[str] = Field(None, description="UUID of existing document if duplicate")
    existing_lineage_uuid: Optional[str] = Field(None, description="Lineage UUID of existing document")
    file_hash: str = Field(..., description="File hash that was checked")
    match_confidence: float = Field(default=1.0, description="Confidence level of the match")


class VersionComparisonRequest(BaseModel):
    """Request model for comparing versions."""
    version1_uuid: str = Field(..., description="First version UUID")
    version2_uuid: str = Field(..., description="Second version UUID")
    comparison_type: str = Field(default="metadata", description="Type of comparison to perform")


class VersionComparisonResponse(BaseModel):
    """Response model for version comparison."""
    version1: DocumentVersionModel = Field(..., description="First version details")
    version2: DocumentVersionModel = Field(..., description="Second version details")
    differences: Dict[str, Any] = Field(..., description="Detected differences")
    similarity_score: float = Field(..., description="Similarity score between versions")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


def generate_document_uuid() -> str:
    """Generate a unique document UUID."""
    return f"doc-{secrets.token_hex(16)}"


def generate_lineage_uuid() -> str:
    """Generate a unique lineage UUID."""
    return f"lineage-{secrets.token_hex(16)}"


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate if file type is allowed."""
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return file_extension in [t.lower() for t in allowed_types]