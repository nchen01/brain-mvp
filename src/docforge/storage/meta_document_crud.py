"""CRUD operations for Meta Document Database."""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from .meta_document_db import (
    MetaDocumentDatabase,
    MetaDocumentRecord,
    MetaDocumentComponent
)
from utils.error_handling import (
    handle_errors, ErrorCategory, ErrorSeverity,
    graceful_degradation, RecoverableError
)

logger = logging.getLogger(__name__)


class MetaDocumentCRUD:
    """CRUD operations interface for meta document management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize CRUD operations."""
        self.db_path = db_path or "data/meta_document.db"
        self.db = MetaDocumentDatabase(self.db_path)
    
    # CREATE operations
    @handle_errors(
        component="meta_document_crud",
        operation="create_meta_document",
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        max_retries=2
    )
    def create_meta_document(
        self,
        doc_uuid: str,
        set_uuid: str,
        title: str,
        summary: str,
        components: List[MetaDocumentComponent],
        processing_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create a new meta document."""
        logger.info(f"CRUD: Creating meta document for doc_uuid={doc_uuid}, set_uuid={set_uuid}, title='{title}' in database {self.db_path}")
        
        try:
            meta_doc_uuid = self.db.create_meta_document(
                doc_uuid=doc_uuid,
                set_uuid=set_uuid,
                title=title,
                summary=summary,
                components=components,
                processing_history=processing_history or []
            )
            logger.info(f"CRUD: Successfully created meta document {meta_doc_uuid}")
            return meta_doc_uuid
        except Exception as e:
            logger.error(f"CRUD: Failed to create meta document: {e}")
            raise
    
    def create_component(
        self,
        meta_doc_uuid: str,
        component_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        vector_embedding: Optional[List[float]] = None,
        parent_component_id: Optional[str] = None,
        order_index: int = 0,
        confidence_score: float = 1.0
    ) -> str:
        """Create a new component for a meta document."""
        import uuid
        
        component = MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type=component_type,
            content=content,
            metadata=metadata or {},
            vector_embedding=vector_embedding,
            parent_component_id=parent_component_id,
            order_index=order_index,
            confidence_score=confidence_score
        )
        
        return self.db.add_component(meta_doc_uuid, component)
    
    def create_document_relationship(
        self,
        source_meta_doc_uuid: str,
        target_meta_doc_uuid: str,
        relationship_type: str,
        relationship_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a relationship between two meta documents."""
        try:
            self.db.add_document_relationship(
                source_meta_doc_uuid=source_meta_doc_uuid,
                target_meta_doc_uuid=target_meta_doc_uuid,
                relationship_type=relationship_type,
                relationship_strength=relationship_strength,
                metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create document relationship: {e}")
            return False
    
    # READ operations
    @handle_errors(
        component="meta_document_crud",
        operation="get_meta_document",
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.MEDIUM,
        max_retries=2
    )
    def get_meta_document(self, meta_doc_uuid: str) -> Optional[MetaDocumentRecord]:
        """Get a meta document by UUID."""
        logger.debug(f"CRUD: Attempting to retrieve meta document {meta_doc_uuid} from database {self.db.db_path}")
        
        with graceful_degradation(
            fallback_value=None,
            component="meta_document_crud",
            operation="get_meta_document"
        ):
            result = self.db.get_meta_document(meta_doc_uuid)
            if result:
                logger.debug(f"CRUD: Successfully retrieved meta document {meta_doc_uuid}")
            else:
                logger.warning(f"CRUD: Meta document {meta_doc_uuid} not found in database {self.db.db_path}")
            return result
    
    def get_meta_documents_by_doc_uuid(self, doc_uuid: str) -> List[MetaDocumentRecord]:
        """Get all meta documents for a specific document UUID."""
        return self.db.get_meta_documents_by_doc_uuid(doc_uuid)
    
    def get_meta_documents_by_set_uuid(self, set_uuid: str) -> List[MetaDocumentRecord]:
        """Get all meta documents for a specific processing set UUID."""
        return self.db.get_meta_documents_by_set_uuid(set_uuid)
    
    def get_meta_documents_by_uuids(self, meta_doc_uuids: List[str]) -> List[MetaDocumentRecord]:
        """Get multiple meta documents by their UUIDs."""
        results = []
        for meta_doc_uuid in meta_doc_uuids:
            meta_doc = self.get_meta_document(meta_doc_uuid)
            if meta_doc:
                results.append(meta_doc)
            else:
                logger.warning(f"CRUD: Meta document {meta_doc_uuid} not found")
        return results
    
    def get_components_by_type(
        self,
        meta_doc_uuid: str,
        component_type: str
    ) -> List[MetaDocumentComponent]:
        """Get components of a specific type from a meta document."""
        return self.db.get_components_by_type(meta_doc_uuid, component_type)
    
    def get_rag_ready_documents(self, limit: Optional[int] = None) -> List[MetaDocumentRecord]:
        """Get all RAG-ready meta documents."""
        return self.db.get_rag_ready_documents(limit)
    
    def get_pending_rag_documents(self, limit: Optional[int] = None) -> List[MetaDocumentRecord]:
        """Get meta documents that are not yet RAG-ready."""
        return self.db.get_pending_rag_documents(limit)
    
    def get_document_relationships(
        self,
        meta_doc_uuid: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for a meta document."""
        return self.db.get_document_relationships(meta_doc_uuid, relationship_type)
    
    def get_rag_preparation_status(self, meta_doc_uuid: str) -> Dict[str, Dict[str, Any]]:
        """Get RAG preparation status for all stages."""
        return self.db.get_rag_preparation_status(meta_doc_uuid)
    
    def search_meta_documents(
        self,
        query: str,
        fields: List[str] = None,
        limit: int = 50
    ) -> List[MetaDocumentRecord]:
        """Search meta documents by text query."""
        # Simple implementation - could be enhanced with full-text search
        fields = fields or ['title', 'summary']
        
        # Get all documents and filter (in a real implementation, this would be done in SQL)
        all_docs = self.get_rag_ready_documents()
        
        results = []
        query_lower = query.lower()
        
        for doc in all_docs:
            match_score = 0
            for field in fields:
                field_value = getattr(doc, field, '')
                if field_value and query_lower in field_value.lower():
                    match_score += 1
            
            # Also search in component content
            for component in doc.components:
                if query_lower in component.content.lower():
                    match_score += 0.5
            
            if match_score > 0:
                # Add match score to the document for sorting
                doc._match_score = match_score
                results.append(doc)
        
        # Sort by match score and limit results
        results.sort(key=lambda x: getattr(x, '_match_score', 0), reverse=True)
        return results[:limit]
    
    def get_documents_by_component_type(
        self,
        component_type: str,
        limit: Optional[int] = None
    ) -> List[MetaDocumentRecord]:
        """Get meta documents that have components of a specific type."""
        # This would be more efficient with a proper SQL query
        all_docs = self.get_rag_ready_documents()
        
        filtered_docs = []
        for doc in all_docs:
            if any(comp.component_type == component_type for comp in doc.components):
                filtered_docs.append(doc)
        
        return filtered_docs[:limit] if limit else filtered_docs
    
    # UPDATE operations
    def update_rag_ready_status(
        self,
        meta_doc_uuid: str,
        rag_ready: bool,
        vector_index_id: Optional[str] = None,
        knowledge_graph_id: Optional[str] = None
    ) -> bool:
        """Update RAG ready status for a meta document."""
        try:
            self.db.update_rag_ready_status(
                meta_doc_uuid=meta_doc_uuid,
                rag_ready=rag_ready,
                vector_index_id=vector_index_id,
                knowledge_graph_id=knowledge_graph_id
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update RAG ready status: {e}")
            return False
    
    def update_component_embedding(
        self,
        component_id: str,
        vector_embedding: List[float]
    ) -> bool:
        """Update the vector embedding for a component."""
        try:
            self.db.update_component_embedding(component_id, vector_embedding)
            return True
        except Exception as e:
            logger.error(f"Failed to update component embedding: {e}")
            return False
    
    def update_rag_preparation_status(
        self,
        meta_doc_uuid: str,
        preparation_stage: str,
        status: str,
        progress_percentage: float = 0.0,
        error_message: Optional[str] = None
    ) -> bool:
        """Update RAG preparation status for a specific stage."""
        try:
            self.db.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage=preparation_stage,
                status=status,
                progress_percentage=progress_percentage,
                error_message=error_message
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update RAG preparation status: {e}")
            return False
    
    def bulk_update_rag_status(
        self,
        meta_doc_uuids: List[str],
        rag_ready: bool
    ) -> Dict[str, int]:
        """Bulk update RAG ready status for multiple documents."""
        success_count = 0
        error_count = 0
        
        for meta_doc_uuid in meta_doc_uuids:
            if self.update_rag_ready_status(meta_doc_uuid, rag_ready):
                success_count += 1
            else:
                error_count += 1
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'total_processed': len(meta_doc_uuids)
        }
    
    # UTILITY operations
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.db.get_storage_statistics()
    
    def cleanup_old_documents(self, retention_days: int = 30) -> Dict[str, int]:
        """Clean up old meta documents."""
        deleted_count = self.db.cleanup_old_documents(retention_days)
        return {'documents_cleaned': deleted_count}
    
    def validate_meta_document_integrity(self, meta_doc_uuid: str) -> Dict[str, Any]:
        """Validate meta document data integrity."""
        meta_doc = self.get_meta_document(meta_doc_uuid)
        if not meta_doc:
            return {'valid': False, 'errors': ['Meta document not found']}
        
        errors = []
        warnings = []
        
        # Check required fields
        if not meta_doc.title:
            errors.append("Missing title")
        if not meta_doc.summary:
            warnings.append("Missing summary")
        if not meta_doc.components:
            errors.append("No components found")
        
        # Check component integrity
        component_types = set()
        for component in meta_doc.components:
            component_types.add(component.component_type)
            if not component.content:
                warnings.append(f"Component {component.component_id} has no content")
            if component.confidence_score < 0.5:
                warnings.append(f"Component {component.component_id} has low confidence score")
        
        # Check if document has essential component types
        essential_types = {'chunk', 'summary'}
        missing_types = essential_types - component_types
        if missing_types:
            warnings.extend([f"Missing component type: {t}" for t in missing_types])
        
        # Check RAG preparation status
        rag_status = self.get_rag_preparation_status(meta_doc_uuid)
        if not rag_status:
            warnings.append("No RAG preparation status found")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'component_count': len(meta_doc.components),
            'component_types': list(component_types),
            'rag_ready': meta_doc.rag_ready,
            'rag_preparation_stages': list(rag_status.keys()) if rag_status else []
        }
    
    def get_processing_pipeline_status(self, doc_uuid: str) -> Dict[str, Any]:
        """Get the complete processing pipeline status for a document."""
        meta_docs = self.get_meta_documents_by_doc_uuid(doc_uuid)
        
        if not meta_docs:
            return {
                'doc_uuid': doc_uuid,
                'meta_documents_count': 0,
                'processing_complete': False,
                'rag_ready_count': 0,
                'total_components': 0
            }
        
        rag_ready_count = sum(1 for doc in meta_docs if doc.rag_ready)
        total_components = sum(len(doc.components) for doc in meta_docs)
        
        # Get detailed status for each meta document
        detailed_status = []
        for meta_doc in meta_docs:
            rag_prep_status = self.get_rag_preparation_status(meta_doc.meta_doc_uuid)
            detailed_status.append({
                'meta_doc_uuid': meta_doc.meta_doc_uuid,
                'set_uuid': meta_doc.set_uuid,
                'title': meta_doc.title,
                'rag_ready': meta_doc.rag_ready,
                'component_count': len(meta_doc.components),
                'rag_preparation_status': rag_prep_status
            })
        
        return {
            'doc_uuid': doc_uuid,
            'meta_documents_count': len(meta_docs),
            'processing_complete': rag_ready_count == len(meta_docs),
            'rag_ready_count': rag_ready_count,
            'total_components': total_components,
            'detailed_status': detailed_status
        }
    
    def validate_api_interface(self) -> Dict[str, Any]:
        """Validate that all expected API methods are available and working."""
        validation_results = {
            'interface_valid': True,
            'available_methods': [],
            'missing_methods': [],
            'method_signatures': {},
            'errors': []
        }
        
        try:
            # List of expected methods and their signatures
            expected_methods = {
                'create_meta_document': ['doc_uuid', 'set_uuid', 'title', 'summary', 'components'],
                'get_meta_document': ['meta_doc_uuid'],
                'get_meta_documents_by_doc_uuid': ['doc_uuid'],
                'get_meta_documents_by_set_uuid': ['set_uuid'],
                'get_meta_documents_by_uuids': ['meta_doc_uuids'],
                'get_rag_ready_documents': ['limit'],
                'update_rag_ready_status': ['meta_doc_uuid', 'rag_ready'],
                'search_meta_documents': ['query', 'fields', 'limit'],
                'get_document_relationships': ['meta_doc_uuid', 'relationship_type'],
                'create_document_relationship': ['source_meta_doc_uuid', 'target_meta_doc_uuid', 'relationship_type']
            }
            
            # Check each method
            for method_name, expected_params in expected_methods.items():
                if hasattr(self, method_name):
                    validation_results['available_methods'].append(method_name)
                    
                    # Get method signature
                    method = getattr(self, method_name)
                    import inspect
                    sig = inspect.signature(method)
                    validation_results['method_signatures'][method_name] = {
                        'parameters': list(sig.parameters.keys()),
                        'expected_parameters': expected_params
                    }
                else:
                    validation_results['missing_methods'].append(method_name)
                    validation_results['interface_valid'] = False
            
            # Test a few key methods with dummy data
            test_results = self._test_key_methods()
            validation_results['method_tests'] = test_results
            
        except Exception as e:
            validation_results['errors'].append(f"API validation failed: {e}")
            validation_results['interface_valid'] = False
        
        return validation_results
    
    def _test_key_methods(self) -> Dict[str, Any]:
        """Test key methods with dummy data to ensure they work."""
        test_results = {}
        
        try:
            # Test get_meta_documents_by_uuids with empty list
            result = self.get_meta_documents_by_uuids([])
            test_results['get_meta_documents_by_uuids'] = {
                'status': 'passed',
                'result_type': type(result).__name__,
                'result_length': len(result) if isinstance(result, list) else 'N/A'
            }
        except Exception as e:
            test_results['get_meta_documents_by_uuids'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Test get_rag_ready_documents
            result = self.get_rag_ready_documents(limit=1)
            test_results['get_rag_ready_documents'] = {
                'status': 'passed',
                'result_type': type(result).__name__,
                'result_length': len(result) if isinstance(result, list) else 'N/A'
            }
        except Exception as e:
            test_results['get_rag_ready_documents'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Test search_meta_documents
            result = self.search_meta_documents("test", limit=1)
            test_results['search_meta_documents'] = {
                'status': 'passed',
                'result_type': type(result).__name__,
                'result_length': len(result) if isinstance(result, list) else 'N/A'
            }
        except Exception as e:
            test_results['search_meta_documents'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return test_results
    
    def export_meta_document_for_rag(self, meta_doc_uuid: str) -> Optional[Dict[str, Any]]:
        """Export meta document in a format suitable for RAG systems."""
        meta_doc = self.get_meta_document(meta_doc_uuid)
        if not meta_doc or not meta_doc.rag_ready:
            return None
        
        # Group components by type
        components_by_type = {}
        for component in meta_doc.components:
            if component.component_type not in components_by_type:
                components_by_type[component.component_type] = []
            components_by_type[component.component_type].append({
                'id': component.component_id,
                'content': component.content,
                'metadata': component.metadata,
                'vector_embedding': component.vector_embedding,
                'confidence_score': component.confidence_score,
                'order_index': component.order_index
            })
        
        # Get relationships
        relationships = self.get_document_relationships(meta_doc_uuid)
        
        return {
            'meta_doc_uuid': meta_doc.meta_doc_uuid,
            'doc_uuid': meta_doc.doc_uuid,
            'set_uuid': meta_doc.set_uuid,
            'title': meta_doc.title,
            'summary': meta_doc.summary,
            'components_by_type': components_by_type,
            'relationships': relationships,
            'vector_index_id': meta_doc.vector_index_id,
            'knowledge_graph_id': meta_doc.knowledge_graph_id,
            'processing_history': meta_doc.processing_history,
            'created_at': meta_doc.created_at.isoformat(),
            'updated_at': meta_doc.updated_at.isoformat()
        }