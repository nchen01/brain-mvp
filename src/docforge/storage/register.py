"""Post Document Register Table for efficient document registration and querying."""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .post_document_db import PostDocumentDatabase
from .schemas import (
    PostDocumentRecord,
    ProcessingVersionRecord,
    ChunkStorageRecord,
    DocumentMetadata,
    StorageConfig,
    QueryFilter,
    StorageStats,
    ProcessingStatus
)
from docforge.postprocessing.schemas import ChunkData

logger = logging.getLogger(__name__)


class DocumentRegistrationError(Exception):
    """Exception raised when document registration fails."""
    pass


class PostDocumentRegister:
    """High-level interface for document registration and management."""
    
    def __init__(self, config: StorageConfig):
        """Initialize the document register."""
        self.config = config
        self.db = PostDocumentDatabase(config)
        self._cache = {}  # Simple in-memory cache for frequently accessed documents
        self._cache_max_size = 100
        self._cache_ttl = timedelta(minutes=30)
    
    # CRUD Operations
    
    def register_document(
        self,
        file_uuid: str,
        source_file_path: str,
        source_content: str,
        metadata: Optional[DocumentMetadata] = None,
        tags: List[str] = None
    ) -> str:
        """
        Register a new document in the system.
        
        Args:
            file_uuid: Unique identifier for the source file
            source_file_path: Path to the original file
            source_content: Content of the source file
            metadata: Document metadata
            tags: Optional tags for the document
            
        Returns:
            Document UUID
            
        Raises:
            DocumentRegistrationError: If registration fails
        """
        try:
            # Enhance metadata with tags if provided
            if metadata is None:
                metadata = DocumentMetadata()
            
            if tags:
                metadata.tags.extend(tags)
            
            # Check if document already exists
            existing_docs = self.find_documents_by_file_uuid(file_uuid)
            if existing_docs:
                logger.warning(f"Document with file_uuid {file_uuid} already exists")
                return existing_docs[0].doc_uuid
            
            # Register the document
            doc_uuid = self.db.store_document(
                file_uuid=file_uuid,
                source_file_path=source_file_path,
                source_content=source_content,
                metadata=metadata
            )
            
            logger.info(f"Successfully registered document {doc_uuid}")
            return doc_uuid
            
        except Exception as e:
            logger.error(f"Failed to register document: {e}")
            raise DocumentRegistrationError(f"Document registration failed: {e}")
    
    def register_processing_version(
        self,
        doc_uuid: str,
        set_uuid: str,
        processing_method: str,
        processing_config: Dict[str, Any],
        processor_version: str,
        processing_duration: float,
        chunks: List[ChunkData],
        status: ProcessingStatus = ProcessingStatus.COMPLETED,
        error_message: Optional[str] = None,
        warnings: List[str] = None
    ) -> str:
        """
        Register a new processing version for a document.
        
        Args:
            doc_uuid: Document UUID
            set_uuid: Processing set UUID
            processing_method: Method used for processing
            processing_config: Configuration used
            processor_version: Version of the processor
            processing_duration: Time taken for processing
            chunks: Generated chunks
            status: Processing status
            error_message: Error message if failed
            warnings: Processing warnings
            
        Returns:
            Version ID
            
        Raises:
            DocumentRegistrationError: If registration fails
        """
        try:
            # Validate document exists
            if not self.document_exists(doc_uuid):
                raise DocumentRegistrationError(f"Document {doc_uuid} not found")
            
            # Check for duplicate set_uuid
            existing_version = self.get_processing_version_by_set_uuid(doc_uuid, set_uuid)
            if existing_version:
                logger.warning(f"Processing version with set_uuid {set_uuid} already exists")
                return existing_version.version_id
            
            # Register the processing version
            version_id = self.db.add_processing_version(
                doc_uuid=doc_uuid,
                set_uuid=set_uuid,
                processing_method=processing_method,
                processing_config=processing_config,
                processor_version=processor_version,
                processing_duration=processing_duration,
                chunks=chunks,
                status=status,
                error_message=error_message,
                warnings=warnings or []
            )
            
            # Clear cache for this document
            self._invalidate_cache(doc_uuid)
            
            logger.info(f"Successfully registered processing version {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to register processing version: {e}")
            raise DocumentRegistrationError(f"Processing version registration failed: {e}")
    
    def get_document(self, doc_uuid: str, use_cache: bool = True) -> Optional[PostDocumentRecord]:
        """
        Retrieve a document by UUID with optional caching.
        
        Args:
            doc_uuid: Document UUID
            use_cache: Whether to use cache
            
        Returns:
            Document record or None if not found
        """
        # Check cache first
        if use_cache and doc_uuid in self._cache:
            cached_entry = self._cache[doc_uuid]
            if datetime.now(timezone.utc) - cached_entry['timestamp'] < self._cache_ttl:
                return cached_entry['document']
            else:
                # Remove expired entry
                del self._cache[doc_uuid]
        
        # Fetch from database
        document = self.db.get_document(doc_uuid)
        
        # Cache the result
        if use_cache and document:
            self._add_to_cache(doc_uuid, document)
        
        return document
    
    def update_document_metadata(
        self,
        doc_uuid: str,
        metadata: DocumentMetadata
    ) -> bool:
        """
        Update document metadata.
        
        Args:
            doc_uuid: Document UUID
            metadata: New metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            document = self.get_document(doc_uuid, use_cache=False)
            if not document:
                return False
            
            # Update metadata
            document.metadata = metadata
            document.updated_at = datetime.now(timezone.utc)
            
            # This would require implementing an update method in the database
            # For now, we'll log that this needs to be implemented
            logger.warning("Document metadata update not yet implemented in database layer")
            
            # Clear cache
            self._invalidate_cache(doc_uuid)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document metadata: {e}")
            return False
    
    def delete_document(self, doc_uuid: str) -> bool:
        """
        Delete a document and all its associated data.
        
        Args:
            doc_uuid: Document UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db.delete_document(doc_uuid)
            
            if success:
                self._invalidate_cache(doc_uuid)
                logger.info(f"Successfully deleted document {doc_uuid}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    # Query Operations
    
    def document_exists(self, doc_uuid: str) -> bool:
        """Check if a document exists."""
        return self.get_document(doc_uuid) is not None
    
    def find_documents_by_file_uuid(self, file_uuid: str) -> List[PostDocumentRecord]:
        """Find documents by file UUID."""
        filter_obj = QueryFilter(file_uuids=[file_uuid])
        return self.db.query_documents(filter_obj)
    
    def find_documents_by_hash(self, file_hash: str) -> List[PostDocumentRecord]:
        """Find documents by file hash."""
        # This would require implementing hash-based querying in the database
        # For now, we'll return empty list and log
        logger.warning("Hash-based document search not yet implemented")
        return []
    
    def find_documents_by_tags(self, tags: List[str]) -> List[PostDocumentRecord]:
        """Find documents by tags."""
        filter_obj = QueryFilter(tags=tags)
        return self.db.query_documents(filter_obj)
    
    def find_documents_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PostDocumentRecord]:
        """Find documents by creation date range."""
        filter_obj = QueryFilter(date_range={"start": start_date, "end": end_date})
        return self.db.query_documents(filter_obj)
    
    def find_documents_by_processing_method(
        self,
        processing_method: str
    ) -> List[PostDocumentRecord]:
        """Find documents by processing method."""
        filter_obj = QueryFilter(processing_methods=[processing_method])
        return self.db.query_documents(filter_obj)
    
    def get_processing_version_by_set_uuid(
        self,
        doc_uuid: str,
        set_uuid: str
    ) -> Optional[ProcessingVersionRecord]:
        """Get processing version by set UUID."""
        document = self.get_document(doc_uuid)
        if document:
            return document.get_version_by_set_uuid(set_uuid)
        return None
    
    def get_latest_processing_version(
        self,
        doc_uuid: str
    ) -> Optional[ProcessingVersionRecord]:
        """Get the latest processing version for a document."""
        document = self.get_document(doc_uuid)
        if document:
            return document.get_latest_version()
        return None
    
    def get_successful_processing_versions(
        self,
        doc_uuid: str
    ) -> List[ProcessingVersionRecord]:
        """Get all successful processing versions for a document."""
        document = self.get_document(doc_uuid)
        if document:
            return document.get_successful_versions()
        return []
    
    def get_chunks_for_version(
        self,
        doc_uuid: str,
        set_uuid: str
    ) -> List[ChunkStorageRecord]:
        """Get chunks for a specific processing version."""
        return self.db.get_chunks(doc_uuid, set_uuid)
    
    def get_all_chunks(self, doc_uuid: str) -> List[ChunkStorageRecord]:
        """Get all chunks for a document."""
        return self.db.get_chunks(doc_uuid)
    
    # Advanced Query Operations
    
    def search_documents(
        self,
        query: str,
        filters: Optional[QueryFilter] = None,
        limit: int = 100
    ) -> List[PostDocumentRecord]:
        """
        Search documents with text query and filters.
        
        Args:
            query: Search query
            filters: Additional filters
            limit: Maximum results to return
            
        Returns:
            List of matching documents
        """
        # This is a placeholder for full-text search functionality
        # In a real implementation, this would use database full-text search
        # or integrate with a search engine like Elasticsearch
        
        if filters:
            documents = self.db.query_documents(filters)
        else:
            # Get all documents if no filters
            documents = self.db.query_documents(QueryFilter())
        
        # Simple text matching (in a real implementation, use proper search)
        if query:
            query_lower = query.lower()
            filtered_docs = []
            
            for doc in documents:
                # Search in metadata
                if (doc.metadata.title and query_lower in doc.metadata.title.lower()) or \
                   (doc.metadata.author and query_lower in doc.metadata.author.lower()) or \
                   any(query_lower in tag.lower() for tag in doc.metadata.tags):
                    filtered_docs.append(doc)
            
            documents = filtered_docs
        
        return documents[:limit]
    
    def get_documents_by_status(
        self,
        status: ProcessingStatus
    ) -> List[PostDocumentRecord]:
        """Get documents by processing status."""
        filter_obj = QueryFilter(status=[status])
        return self.db.query_documents(filter_obj)
    
    def get_documents_needing_processing(
        self,
        processing_method: str
    ) -> List[PostDocumentRecord]:
        """Get documents that need a specific type of processing."""
        all_docs = self.db.query_documents(QueryFilter())
        
        needing_processing = []
        for doc in all_docs:
            # Check if document has this processing method
            has_method = any(
                version.processing_method == processing_method and 
                version.status == ProcessingStatus.COMPLETED
                for version in doc.processing_versions
            )
            
            if not has_method:
                needing_processing.append(doc)
        
        return needing_processing
    
    # Statistics and Analytics
    
    def get_registration_stats(self) -> StorageStats:
        """Get registration statistics."""
        return self.db.get_storage_stats()
    
    def get_processing_method_stats(self) -> Dict[str, int]:
        """Get statistics by processing method."""
        stats = self.get_registration_stats()
        return stats.method_counts
    
    def get_status_distribution(self) -> Dict[str, int]:
        """Get distribution of processing statuses."""
        stats = self.get_registration_stats()
        return stats.status_counts
    
    def get_recent_registrations(
        self,
        days: int = 7
    ) -> List[PostDocumentRecord]:
        """Get recently registered documents."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return self.find_documents_by_date_range(cutoff_date, datetime.now(timezone.utc))
    
    # Vector Storage Integration
    
    def update_vector_references(
        self,
        doc_uuid: str,
        set_uuid: str,
        vector_index_id: str,
        embeddings_path: Optional[str] = None
    ) -> bool:
        """Update vector storage references for a processing version."""
        try:
            version = self.get_processing_version_by_set_uuid(doc_uuid, set_uuid)
            if not version:
                return False
            
            self.db.update_vector_references(
                version_id=version.version_id,
                vector_index_id=vector_index_id,
                embeddings_path=embeddings_path
            )
            
            # Clear cache
            self._invalidate_cache(doc_uuid)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update vector references: {e}")
            return False
    
    def get_documents_with_vectors(self) -> List[PostDocumentRecord]:
        """Get documents that have vector embeddings."""
        all_docs = self.db.query_documents(QueryFilter())
        
        with_vectors = []
        for doc in all_docs:
            has_vectors = any(
                version.vector_index_id is not None
                for version in doc.processing_versions
            )
            
            if has_vectors:
                with_vectors.append(doc)
        
        return with_vectors
    
    def get_documents_without_vectors(self) -> List[PostDocumentRecord]:
        """Get documents that don't have vector embeddings."""
        all_docs = self.db.query_documents(QueryFilter())
        
        without_vectors = []
        for doc in all_docs:
            has_vectors = any(
                version.vector_index_id is not None
                for version in doc.processing_versions
            )
            
            if not has_vectors:
                without_vectors.append(doc)
        
        return without_vectors
    
    # Cache Management
    
    def _add_to_cache(self, doc_uuid: str, document: PostDocumentRecord):
        """Add document to cache."""
        # Implement LRU eviction if cache is full
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]['timestamp']
            )
            del self._cache[oldest_key]
        
        self._cache[doc_uuid] = {
            'document': document,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def _invalidate_cache(self, doc_uuid: str):
        """Remove document from cache."""
        if doc_uuid in self._cache:
            del self._cache[doc_uuid]
    
    def clear_cache(self):
        """Clear all cached documents."""
        self._cache.clear()
        logger.info("Document cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._cache_max_size,
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60,
            "cached_documents": list(self._cache.keys())
        }
    
    # Maintenance Operations
    
    def cleanup_old_documents(self, retention_days: int) -> int:
        """Clean up old documents."""
        return self.db.cleanup_old_documents(retention_days)
    
    def validate_document_integrity(self, doc_uuid: str) -> Dict[str, Any]:
        """Validate document integrity."""
        try:
            document = self.get_document(doc_uuid, use_cache=False)
            if not document:
                return {"valid": False, "error": "Document not found"}
            
            issues = []
            
            # Check processing versions
            for version in document.processing_versions:
                chunks = self.get_chunks_for_version(doc_uuid, version.set_uuid)
                
                if version.chunk_count != len(chunks):
                    issues.append(f"Version {version.version_id}: chunk count mismatch")
                
                # Check chunk integrity
                for chunk in chunks:
                    expected_hash = self.db._calculate_hash(chunk.content)
                    if chunk.content_hash != expected_hash:
                        issues.append(f"Chunk {chunk.chunk_id}: hash mismatch")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "document_uuid": doc_uuid,
                "processing_versions": len(document.processing_versions),
                "total_chunks": sum(len(self.get_chunks_for_version(doc_uuid, v.set_uuid)) 
                                  for v in document.processing_versions)
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health information."""
        try:
            stats = self.get_registration_stats()
            cache_stats = self.get_cache_stats()
            
            return {
                "status": "healthy",
                "total_documents": stats.total_documents,
                "total_processing_versions": stats.total_processing_versions,
                "total_chunks": stats.total_chunks,
                "cache_utilization": cache_stats["cache_size"] / cache_stats["max_cache_size"],
                "average_processing_time": stats.average_processing_time,
                "average_chunk_count": stats.average_chunk_count,
                "status_distribution": stats.status_counts,
                "method_distribution": stats.method_counts
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }