"""Shared data models for Brain MVP."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ProcessingStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    REGISTERED = "registered"
    PROCESSING = "processing"
    POST_PROCESSING = "post_processing"
    RAG_PREPARATION = "rag_preparation"
    COMPLETED = "completed"
    FAILED = "failed"


class RawDocument(BaseModel):
    """Raw document model."""
    content: bytes
    filename: str
    file_type: str
    user_id: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: List[str] = Field(default_factory=list)


class DocumentLineage(BaseModel):
    """Document lineage tracking model."""
    lineage_uuid: str
    original_filename: str
    created_by: str
    created_at: datetime
    current_version: int
    total_versions: int
    is_active: bool = True


class DocumentVersion(BaseModel):
    """Individual document version model."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    parent_version: Optional[int] = None
    filename: str
    file_path: str
    file_type: str
    file_hash: str
    timestamp: datetime
    user_id: str
    labels: List[str] = Field(default_factory=list)
    is_current: bool = False
    is_deleted: bool = False
    deletion_reason: Optional[str] = None
    edit_source_version: Optional[int] = None


class DocumentRegistration(BaseModel):
    """Document registration result model."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    filename: str
    file_path: str
    file_type: str
    file_hash: str
    timestamp: datetime
    user_id: str
    labels: List[str] = Field(default_factory=list)
    is_new_lineage: bool
    is_duplicate: bool
    parent_version: Optional[int] = None


class ProcessedDocument(BaseModel):
    """Processed document model."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    extracted_content: str
    processor_type: str
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)


class StandardizedOutput(BaseModel):
    """Uniform output format for all processors."""
    doc_uuid: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_elements: List[Dict[str, Any]] = Field(default_factory=list)
    processing_info: Dict[str, Any] = Field(default_factory=dict)
    format_version: str = "1.0"


class MetaDocument(BaseModel):
    """Meta document model for final processed output."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    meta_file_uuid: str
    component_type: str  # e.g., "text", "image", "table", "metadata"
    content: str
    file_path: str
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostDocument(BaseModel):
    """Post-processed document model."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    set_uuid: str
    file_uuid: str
    file_path: str
    processing_method: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostDocumentRegister(BaseModel):
    """Post document register model."""
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    set_uuid: str
    file_uuid: str
    file_path: str
    processing_method: str
    processing_version: str
    metadata_record: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MetaDocumentRegister(BaseModel):
    """Meta document register model."""
    meta_file_uuid: str
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    file_path: str
    component_type: str
    metadata_record: Dict[str, Any] = Field(default_factory=dict)
    processing_status: str
    chunking_strategy: Optional[str] = None
    post_processing_applied: List[str] = Field(default_factory=list)
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostProcessRule(BaseModel):
    """Post-processing rule model."""
    rule_id: str
    document_type: str
    metadata_conditions: Dict[str, Any] = Field(default_factory=dict)
    processors: List[str] = Field(default_factory=list)
    priority: int = 0
    is_active: bool = True


class AbbreviationEntry(BaseModel):
    """Abbreviation expansion entry model."""
    abbreviation: str
    full_form: str
    domain: str
    confidence_score: float = 1.0
    usage_context: List[str] = Field(default_factory=list)


class Query(BaseModel):
    """Query model for RAG operations."""
    id: str
    text: str
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_results: int = 5
    include_deleted: bool = False


class QueryResponse(BaseModel):
    """Query response model."""
    query_id: str
    doc_uuid: str
    lineage_uuid: str
    version_number: int
    relevance_score: float
    response_text: str
    context: str
    sources: List[str] = Field(default_factory=list)
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class ProjectPhase(str, Enum):
    """Project development phases."""
    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class DevelopmentLog(BaseModel):
    """Development activity log model."""
    id: str
    phase: ProjectPhase
    activity_type: str
    description: str
    files_affected: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    component: str
    details: Optional[Dict[str, Any]] = None