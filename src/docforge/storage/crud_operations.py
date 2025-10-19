"""CRUD operations interface for Post Document Register."""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from .post_document_register import PostDocumentRegister
from .schemas import DocumentMetadata, ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentCRUD:
    """CRUD operations interface for document management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize CRUD operations."""
        self.register = PostDocumentRegister(db_path or "data/post_document_register.db")
    
    # CREATE operations
    def create_document(
        self,
        doc_uuid: str,
        file_uuid: str,
        source_file_path: str,
        metadata: Optional[DocumentMetadata] = None,
        file_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new document record."""
        return self.register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path=source_file_path,
            metadata=metadata,
            file_info=file_info
        )
    
    def create_processing_version(
        self,
        doc_uuid: str,
        set_uuid: str,
        processing_method: str,
        processor_version: str = "1.0.0",
        **kwargs
    ) -> str:
        """Create a new processing version record."""
        return self.register.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            processing_method=processing_method,
            processor_version=processor_version,
            **kwargs
        )
    
    # READ operations
    def get_document(self, doc_uuid: str) -> Optional[Dict[str, Any]]:
        """Get a document by UUID."""
        return self.register.get_document(doc_uuid)
    
    def get_documents_by_file(self, file_uuid: str) -> List[Dict[str, Any]]:
        """Get all documents processed from a file."""
        return self.register.get_documents_by_file_uuid(file_uuid)
    
    def get_processing_versions(self, doc_uuid: str) -> List[Dict[str, Any]]:
        """Get all processing versions for a document."""
        return self.register.get_processing_versions(doc_uuid)
    
    def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> List[Dict[str, Any]]:
        """List documents with optional filters."""
        return self.register.query_documents(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by
        )
    
    def search_documents(
        self,
        query: str,
        fields: List[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search documents by text query."""
        # Simple implementation - could be enhanced with full-text search
        fields = fields or ['title', 'author', 'source_file_path']
        
        documents = self.register.query_documents(limit=limit * 2)  # Get more to filter
        
        results = []
        query_lower = query.lower()
        
        for doc in documents:
            match_score = 0
            for field in fields:
                if field in doc and doc[field]:
                    if query_lower in str(doc[field]).lower():
                        match_score += 1
            
            if match_score > 0:
                doc['_match_score'] = match_score
                results.append(doc)
        
        # Sort by match score and limit results
        results.sort(key=lambda x: x['_match_score'], reverse=True)
        return results[:limit]
    
    def get_unindexed_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get documents that need indexing."""
        return self.register.get_unindexed_documents(limit)
    
    def get_documents_by_status(
        self,
        status: Union[ProcessingStatus, str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get documents by processing status."""
        if isinstance(status, ProcessingStatus):
            status = status.value
        
        return self.register.query_documents(
            filters={'processing_status': status},
            limit=limit
        )
    
    def get_documents_by_type(
        self,
        file_type: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get documents by file type."""
        return self.register.query_documents(
            filters={'file_type': file_type},
            limit=limit
        )
    
    # UPDATE operations
    def update_document_metadata(
        self,
        doc_uuid: str,
        metadata: DocumentMetadata
    ) -> bool:
        """Update document metadata."""
        try:
            # Get existing document
            doc = self.register.get_document(doc_uuid)
            if not doc:
                return False
            
            # Update with new metadata
            self.register.register_document(
                doc_uuid=doc_uuid,
                file_uuid=doc['file_uuid'],
                source_file_path=doc['source_file_path'],
                metadata=metadata
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document metadata: {e}")
            return False
    
    def update_processing_status(
        self,
        doc_uuid: str,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update document processing status."""
        try:
            # Check if document exists first
            doc = self.register.get_document(doc_uuid)
            if not doc:
                logger.warning(f"Document {doc_uuid} not found for status update")
                return False
            
            self.register.update_processing_status(doc_uuid, status, error_message)
            return True
        except Exception as e:
            logger.error(f"Failed to update processing status: {e}")
            return False
    
    def update_indexing_status(
        self,
        doc_uuid: str,
        is_indexed: bool,
        index_version: Optional[str] = None
    ) -> bool:
        """Update document indexing status."""
        try:
            # Check if document exists first
            doc = self.register.get_document(doc_uuid)
            if not doc:
                logger.warning(f"Document {doc_uuid} not found for indexing status update")
                return False
            
            self.register.update_indexing_status(doc_uuid, is_indexed, index_version)
            return True
        except Exception as e:
            logger.error(f"Failed to update indexing status: {e}")
            return False
    
    def update_vector_references(
        self,
        version_id: str,
        vector_index_id: str,
        embeddings_path: Optional[str] = None
    ) -> bool:
        """Update vector storage references."""
        try:
            self.register.update_vector_references(version_id, vector_index_id, embeddings_path)
            return True
        except Exception as e:
            logger.error(f"Failed to update vector references: {e}")
            return False
    
    # DELETE operations
    def delete_document(self, doc_uuid: str, soft_delete: bool = True) -> bool:
        """Delete a document (soft delete by default)."""
        try:
            if soft_delete:
                self.register.deactivate_document(doc_uuid)
            else:
                # Hard delete would require additional implementation
                logger.warning("Hard delete not implemented, performing soft delete")
                self.register.deactivate_document(doc_uuid)
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def restore_document(self, doc_uuid: str) -> bool:
        """Restore a soft-deleted document."""
        try:
            self.register.reactivate_document(doc_uuid)
            return True
        except Exception as e:
            logger.error(f"Failed to restore document: {e}")
            return False
    
    # UTILITY operations
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing and storage statistics."""
        return self.register.get_processing_statistics()
    
    def cleanup_old_documents(self, retention_days: int = 30) -> Dict[str, int]:
        """Clean up old documents."""
        deleted_count = self.register.cleanup_old_documents(retention_days)
        return {'documents_cleaned': deleted_count}
    
    def get_document_relationships(self, doc_uuid: str) -> List[Dict[str, Any]]:
        """Get file relationships for a document."""
        return self.register.get_document_relationships(doc_uuid)
    
    def bulk_update_status(
        self,
        doc_uuids: List[str],
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> Dict[str, int]:
        """Bulk update processing status for multiple documents."""
        success_count = 0
        error_count = 0
        
        for doc_uuid in doc_uuids:
            try:
                self.register.update_processing_status(doc_uuid, status, error_message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to update status for {doc_uuid}: {e}")
                error_count += 1
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'total_processed': len(doc_uuids)
        }
    
    def get_processing_queue_status(self) -> Dict[str, Any]:
        """Get processing queue statistics."""
        # This would need additional implementation in the register
        # For now, return basic info
        return {
            'queue_length': 0,  # Would need to implement
            'processing_count': 0,  # Would need to implement
            'failed_count': 0  # Would need to implement
        }
    
    def validate_document_integrity(self, doc_uuid: str) -> Dict[str, Any]:
        """Validate document data integrity."""
        doc = self.get_document(doc_uuid)
        if not doc:
            return {'valid': False, 'errors': ['Document not found']}
        
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ['doc_uuid', 'file_uuid', 'source_file_path']
        for field in required_fields:
            if not doc.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check processing versions
        versions = self.get_processing_versions(doc_uuid)
        if not versions:
            warnings.append("No processing versions found")
        
        # Check relationships
        relationships = self.get_document_relationships(doc_uuid)
        if not relationships:
            warnings.append("No file relationships found")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'version_count': len(versions),
            'relationship_count': len(relationships)
        }


class ProcessingQueueCRUD:
    """CRUD operations for processing queue management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize processing queue CRUD operations."""
        self.register = PostDocumentRegister(db_path or "data/post_document_register.db")
    
    def add_to_queue(
        self,
        doc_uuid: str,
        requested_methods: List[str],
        requested_config: Optional[Dict[str, Any]] = None,
        priority: int = 5
    ) -> int:
        """Add document to processing queue."""
        return self.register.add_to_processing_queue(
            doc_uuid=doc_uuid,
            requested_methods=requested_methods,
            requested_config=requested_config,
            priority=priority
        )
    
    def get_next_item(self) -> Optional[Dict[str, Any]]:
        """Get next item from processing queue."""
        return self.register.get_next_queued_document()
    
    def update_status(
        self,
        queue_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update queue item status."""
        self.register.update_queue_status(queue_id, status, error_message)
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get queue processing statistics."""
        # This would need additional queries in the register
        # For now, return placeholder
        return {
            'total_queued': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }