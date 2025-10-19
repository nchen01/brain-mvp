"""Storage schemas for post-processed documents."""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum
import uuid


class ProcessingStatus(str, Enum):
    """Status of document processing."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class StorageConfig(BaseModel):
    """Configuration for document storage."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    database_url: str = Field(..., description="Database connection URL")
    max_connections: int = Field(default=10, description="Maximum database connections")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    enable_compression: bool = Field(default=True, description="Enable content compression")
    enable_encryption: bool = Field(default=False, description="Enable content encryption")
    retention_days: Optional[int] = Field(default=None, description="Document retention period in days")


class DocumentMetadata(BaseModel):
    """Metadata for a processed document."""
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingVersionRecord(BaseModel):
    """Record of a specific processing version."""
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    version_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    set_uuid: str = Field(..., description="Set UUID for this processing version")
    processing_method: str = Field(..., description="Processing method used")
    processing_config: Dict[str, Any] = Field(default_factory=dict)
    processor_version: str = Field(..., description="Version of the processor")
    processing_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_duration: float = Field(..., description="Processing time in seconds")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    chunk_count: int = Field(default=0, description="Number of chunks created")
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    
    # Storage references
    chunks_storage_path: Optional[str] = None
    embeddings_storage_path: Optional[str] = None
    vector_index_id: Optional[str] = None


class PostDocumentRecord(BaseModel):
    """Main record for a processed document."""
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    doc_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_uuid: str = Field(..., description="Original file UUID")
    source_file_path: str = Field(..., description="Path to original file")
    source_file_hash: str = Field(..., description="Hash of original file")
    
    # Document metadata
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    
    # Processing versions
    processing_versions: List[ProcessingVersionRecord] = Field(default_factory=list)
    
    # Storage information
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: Optional[datetime] = None
    
    # Status and flags
    is_active: bool = Field(default=True)
    is_indexed: bool = Field(default=False)
    is_compressed: bool = Field(default=False)
    is_encrypted: bool = Field(default=False)
    
    # Relationships
    parent_doc_uuid: Optional[str] = None  # For document versions/derivatives
    child_doc_uuids: List[str] = Field(default_factory=list)
    related_doc_uuids: List[str] = Field(default_factory=list)
    
    def add_processing_version(self, version: ProcessingVersionRecord) -> None:
        """Add a new processing version."""
        self.processing_versions.append(version)
        self.updated_at = datetime.now(timezone.utc)
    
    def get_latest_version(self) -> Optional[ProcessingVersionRecord]:
        """Get the most recent processing version."""
        if not self.processing_versions:
            return None
        return max(self.processing_versions, key=lambda v: v.processing_timestamp)
    
    def get_version_by_set_uuid(self, set_uuid: str) -> Optional[ProcessingVersionRecord]:
        """Get processing version by set UUID."""
        for version in self.processing_versions:
            if version.set_uuid == set_uuid:
                return version
        return None
    
    def get_successful_versions(self) -> List[ProcessingVersionRecord]:
        """Get all successfully completed processing versions."""
        return [v for v in self.processing_versions if v.status == ProcessingStatus.COMPLETED]


class ChunkStorageRecord(BaseModel):
    """Record for storing chunk data."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_uuid: str = Field(..., description="Parent document UUID")
    set_uuid: str = Field(..., description="Processing set UUID")
    version_id: str = Field(..., description="Processing version ID")
    
    # Chunk content and metadata
    content: str = Field(..., description="Chunk content")
    content_hash: str = Field(..., description="Hash of chunk content")
    chunk_type: str = Field(..., description="Type of chunk")
    chunk_index: int = Field(..., description="Index within document")
    
    # Chunk metadata
    word_count: int = Field(default=0)
    character_count: int = Field(default=0)
    language: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Source information
    source_elements: List[str] = Field(default_factory=list)
    page_numbers: List[int] = Field(default_factory=list)
    
    # Position and relationships
    position_metadata: Dict[str, Any] = Field(default_factory=dict)
    relationships: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Storage and indexing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding_vector: Optional[List[float]] = None
    vector_index_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class QueryFilter(BaseModel):
    """Filter criteria for document queries."""
    doc_uuids: Optional[List[str]] = None
    file_uuids: Optional[List[str]] = None
    set_uuids: Optional[List[str]] = None
    processing_methods: Optional[List[str]] = None
    status: Optional[List[ProcessingStatus]] = None
    date_range: Optional[Dict[str, datetime]] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class StorageStats(BaseModel):
    """Statistics about document storage."""
    total_documents: int = 0
    total_processing_versions: int = 0
    total_chunks: int = 0
    total_storage_size: int = 0  # in bytes
    
    # Status breakdown
    status_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Processing method breakdown
    method_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Time-based stats
    documents_by_date: Dict[str, int] = Field(default_factory=dict)
    
    # Performance stats
    average_processing_time: float = 0.0
    average_chunk_count: float = 0.0
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )