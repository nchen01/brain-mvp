"""Abstract interfaces for Brain MVP components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from .models import (
    RawDocument,
    DocumentRegistration,
    DocumentLineage,
    DocumentVersion,
    ProcessedDocument,
    MetaDocument,
    Query,
    QueryResponse
)


class ProcessorType(Enum):
    """Document processor types."""
    MINERU_PDF = "mineru_pdf"
    MARKITDOWN = "markitdown"


class PostProcessorType(Enum):
    """Post-processor types."""
    CHUNKING_STRATEGY = "chunking_strategy"
    ABBREVIATION_EXPANSION = "abbreviation_expansion"
    CONTENT_NORMALIZATION = "content_normalization"
    METADATA_ENRICHMENT = "metadata_enrichment"


class ChunkingStrategy(Enum):
    """Document chunking strategies."""
    PARAGRAPH = "paragraph"
    SECTION = "section"
    SENTENCE = "sentence"
    TOPIC = "topic"
    SEMANTIC = "semantic"


class DocumentProcessorInterface(ABC):
    """Abstract interface for document processors."""
    
    @abstractmethod
    async def process(self, document: RawDocument) -> ProcessedDocument:
        """Process a raw document and return processed content."""
        pass
    
    @abstractmethod
    def supports_format(self, file_type: str) -> bool:
        """Check if processor supports the given file format."""
        pass
    
    @abstractmethod
    def get_processor_type(self) -> ProcessorType:
        """Get the processor type."""
        pass


class PostProcessorInterface(ABC):
    """Abstract interface for post-processors."""
    
    @abstractmethod
    async def process(self, document: ProcessedDocument) -> ProcessedDocument:
        """Post-process a document."""
        pass
    
    @abstractmethod
    def get_processor_type(self) -> PostProcessorType:
        """Get the post-processor type."""
        pass


class StorageInterface(ABC):
    """Abstract interface for document storage."""
    
    @abstractmethod
    async def store(self, document: Any, metadata: Dict[str, Any]) -> str:
        """Store a document and return its identifier."""
        pass
    
    @abstractmethod
    async def retrieve(self, identifier: str) -> Optional[Any]:
        """Retrieve a document by identifier."""
        pass
    
    @abstractmethod
    async def delete(self, identifier: str) -> bool:
        """Delete a document by identifier."""
        pass


class VersioningInterface(ABC):
    """Abstract interface for document versioning."""
    
    @abstractmethod
    async def create_lineage(self, filename: str, user_id: str) -> str:
        """Create a new document lineage."""
        pass
    
    @abstractmethod
    async def add_version(
        self,
        lineage_uuid: str,
        document: RawDocument,
        parent_version: Optional[int] = None
    ) -> DocumentVersion:
        """Add a new version to a lineage."""
        pass
    
    @abstractmethod
    async def get_lineage(self, lineage_uuid: str) -> Optional[DocumentLineage]:
        """Get document lineage information."""
        pass
    
    @abstractmethod
    async def get_version_history(
        self,
        lineage_uuid: str,
        include_deleted: bool = False
    ) -> List[DocumentVersion]:
        """Get version history for a lineage."""
        pass
    
    @abstractmethod
    async def soft_delete_version(self, doc_uuid: str, reason: str) -> bool:
        """Soft delete a document version."""
        pass


class RAGInterface(ABC):
    """Abstract interface for RAG operations."""
    
    @abstractmethod
    async def index_document(self, document: MetaDocument) -> bool:
        """Index a document for RAG retrieval."""
        pass
    
    @abstractmethod
    async def search(self, query: Query) -> List[QueryResponse]:
        """Search documents using RAG."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, doc_uuid: str) -> bool:
        """Remove a document from the RAG index."""
        pass


class DocForgeInterface(ABC):
    """Main interface for DocForge document processing pipeline."""
    
    # Document Registration and Versioning
    @abstractmethod
    async def register_document(
        self,
        document: RawDocument,
        parent_lineage: Optional[str] = None,
        edit_source_version: Optional[int] = None
    ) -> DocumentRegistration:
        """Register a new document or version."""
        pass
    
    @abstractmethod
    async def create_document_lineage(self, filename: str, user_id: str) -> str:
        """Create a new document lineage."""
        pass
    
    @abstractmethod
    async def get_document_lineage(self, lineage_uuid: str) -> Optional[DocumentLineage]:
        """Get document lineage information."""
        pass
    
    @abstractmethod
    async def get_version_history(
        self,
        lineage_uuid: str,
        include_deleted: bool = False
    ) -> List[DocumentVersion]:
        """Get version history for a lineage."""
        pass
    
    @abstractmethod
    async def get_current_version(self, lineage_uuid: str) -> Optional[DocumentVersion]:
        """Get the current version of a lineage."""
        pass
    
    @abstractmethod
    async def soft_delete_version(self, doc_uuid: str, reason: str) -> bool:
        """Soft delete a document version."""
        pass
    
    @abstractmethod
    async def soft_delete_lineage(self, lineage_uuid: str, reason: str) -> bool:
        """Soft delete an entire lineage."""
        pass
    
    @abstractmethod
    async def restore_version(self, doc_uuid: str) -> bool:
        """Restore a soft-deleted version."""
        pass
    
    # Processing Pipeline
    @abstractmethod
    async def route_document(self, doc_uuid: str) -> ProcessorType:
        """Route document to appropriate processor."""
        pass
    
    @abstractmethod
    async def process_document(
        self,
        doc_uuid: str,
        processor_type: ProcessorType
    ) -> ProcessedDocument:
        """Process a document using specified processor."""
        pass
    
    @abstractmethod
    async def route_post_processing(
        self,
        processed_doc: ProcessedDocument
    ) -> List[PostProcessorType]:
        """Route document to appropriate post-processors."""
        pass
    
    @abstractmethod
    async def determine_chunking_strategy(
        self,
        doc_metadata: Dict[str, Any]
    ) -> ChunkingStrategy:
        """Determine optimal chunking strategy."""
        pass
    
    @abstractmethod
    async def post_process(self, processed_doc: ProcessedDocument) -> MetaDocument:
        """Apply post-processing to document."""
        pass
    
    @abstractmethod
    async def prepare_for_rag(self, meta_doc: MetaDocument) -> bool:
        """Prepare document for RAG indexing."""
        pass
    
    # Retrieval and Search
    @abstractmethod
    async def retrieve_document_by_version(self, doc_uuid: str) -> Optional[Any]:
        """Retrieve a specific document version."""
        pass
    
    @abstractmethod
    async def retrieve_lineage_documents(self, lineage_uuid: str) -> List[Any]:
        """Retrieve all documents in a lineage."""
        pass
    
    @abstractmethod
    async def search_documents(self, query: Query) -> List[QueryResponse]:
        """Search documents using RAG."""
        pass