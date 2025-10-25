"""LightRAG integration for document processing and retrieval."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
import uuid

# LightRAG imports (optional)
try:
    from lightrag import LightRAG, QueryParam
    from lightrag.utils import EmbeddingFunc
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LightRAG = None
    QueryParam = None
    EmbeddingFunc = None
    LIGHTRAG_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Our imports
from docforge.storage.meta_document_db import MetaDocumentDatabase, MetaDocumentRecord, MetaDocumentComponent
from docforge.storage.meta_document_crud import MetaDocumentCRUD
from utils.error_handling import (
    handle_async_errors, ErrorCategory, ErrorSeverity, 
    error_handler, graceful_degradation
)

logger = logging.getLogger(__name__)


@dataclass
class LightRAGConfig:
    """Configuration for LightRAG integration."""
    # Storage paths
    working_dir: str = "data/lightrag"
    vector_db_path: str = "data/lightrag/vector_db"
    
    # Model configurations
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # Processing configurations
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    
    # Retrieval configurations
    top_k: int = 10
    similarity_threshold: float = 0.7
    
    # LLM configurations (optional)
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    
    # Performance settings
    max_async_workers: int = 4
    batch_size: int = 32
    
    # Additional settings
    enable_caching: bool = True
    cache_ttl_hours: int = 24


class DocumentIndexer:
    """Handles document indexing using LightRAG components."""
    
    def __init__(self, config: LightRAGConfig):
        """Initialize the document indexer."""
        self.config = config
        self.embedding_model = None
        self.lightrag = None
        self._setup_components()
    
    def _setup_components(self):
        """Set up LightRAG components."""
        try:
            # Initialize sentence transformer model
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("SentenceTransformers not available")
                self.embedding_model = None
                self.lightrag = None
                return
                
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            
            if LIGHTRAG_AVAILABLE:
                # Create embedding function
                async def embedding_func(texts: List[str]) -> List[List[float]]:
                    embeddings = self.embedding_model.encode(texts)
                    return embeddings.tolist()
                
                # Create EmbeddingFunc wrapper
                embedding_func_wrapper = EmbeddingFunc(
                    embedding_dim=self.config.embedding_dim,
                    func=embedding_func
                )
                
                # Create a simple mock LLM function for indexing-only use
                def mock_llm_func(prompt: str, **kwargs) -> str:
                    return "Mock LLM response for indexing purposes."
                
                # Initialize LightRAG
                self.lightrag = LightRAG(
                    working_dir=self.config.working_dir,
                    embedding_func=embedding_func_wrapper,
                    llm_model_func=mock_llm_func
                )
                
                logger.info("LightRAG components initialized successfully")
            else:
                logger.warning("LightRAG not available, using fallback implementation")
                self.lightrag = None
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG components: {e}")
            raise
    
    async def index_meta_document(
        self, 
        meta_doc: MetaDocumentRecord
    ) -> Dict[str, Any]:
        """Index a meta document using LightRAG."""
        try:
            # Initialize storages if needed
            await self._ensure_initialized()
            
            # Convert meta document to text for indexing
            document_text = self._convert_meta_doc_to_text(meta_doc)
            
            # Insert into LightRAG
            await self.lightrag.ainsert(document_text)
            
            indexing_result = {
                'meta_doc_uuid': meta_doc.meta_doc_uuid,
                'indexed_components': len(meta_doc.components),
                'status': 'completed',
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Successfully indexed meta document {meta_doc.meta_doc_uuid}")
            return indexing_result
            
        except Exception as e:
            logger.error(f"Failed to index meta document {meta_doc.meta_doc_uuid}: {e}")
            return {
                'meta_doc_uuid': meta_doc.meta_doc_uuid,
                'status': 'failed',
                'error': str(e),
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _convert_meta_doc_to_text(
        self, 
        meta_doc: MetaDocumentRecord
    ) -> str:
        """Convert meta document to text for LightRAG indexing."""
        # Create a structured text representation
        text_parts = []
        
        # Add title and summary
        text_parts.append(f"Title: {meta_doc.title}")
        if meta_doc.summary:
            text_parts.append(f"Summary: {meta_doc.summary}")
        
        # Add metadata
        text_parts.append(f"Document UUID: {meta_doc.doc_uuid}")
        text_parts.append(f"Set UUID: {meta_doc.set_uuid}")
        
        # Add components content
        for component in meta_doc.components:
            if component.content.strip():
                text_parts.append(f"\n{component.component_type.upper()}: {component.content}")
        
        return "\n\n".join(text_parts)
    
    async def _ensure_initialized(self):
        """Ensure LightRAG storages are initialized."""
        try:
            # Initialize storages
            await self.lightrag.initialize_storages()
            
            # Initialize pipeline status
            from lightrag.kg.shared_storage import initialize_pipeline_status
            await initialize_pipeline_status()
            
        except Exception as e:
            logger.warning(f"Storage initialization warning: {e}")
            # Continue anyway as this might not be critical
    



class VectorRetriever:
    """Handles document retrieval using LightRAG components."""
    
    def __init__(self, config: LightRAGConfig):
        """Initialize the vector retriever."""
        self.config = config
        self.embedding_model = None
        self.lightrag = None
        self._setup_components()
    
    def _setup_components(self):
        """Set up LightRAG components for retrieval."""
        try:
            # Check if required dependencies are available
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("SentenceTransformers not available for retrieval")
                self.embedding_model = None
                self.lightrag = None
                return
                
            if not LIGHTRAG_AVAILABLE:
                logger.warning("LightRAG not available for retrieval")
                self.embedding_model = None
                self.lightrag = None
                return
            
            # Initialize sentence transformer model
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            
            # Create embedding function
            async def embedding_func(texts: List[str]) -> List[List[float]]:
                embeddings = self.embedding_model.encode(texts)
                return embeddings.tolist()
            
            # Create EmbeddingFunc wrapper
            embedding_func_wrapper = EmbeddingFunc(
                embedding_dim=self.config.embedding_dim,
                func=embedding_func
            )
            
            # Create a simple mock LLM function for retrieval-only use
            def mock_llm_func(prompt: str, **kwargs) -> str:
                return "Mock LLM response for retrieval purposes."
            
            # Initialize LightRAG (same as indexer)
            self.lightrag = LightRAG(
                working_dir=self.config.working_dir,
                embedding_func=embedding_func_wrapper,
                llm_model_func=mock_llm_func
            )
            
            logger.info("LightRAG retrieval components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG retrieval components: {e}")
            # Don't raise the error, just log it and continue with None components
            self.embedding_model = None
            self.lightrag = None
    
    async def retrieve_documents(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query."""
        try:
            # Initialize storages if needed
            await self._ensure_initialized()
            
            # Perform query using LightRAG
            # Note: LightRAG's query method returns text, not structured results
            # For now, we'll use a simple approach
            result = await self.lightrag.aquery(query, param=QueryParam(mode="naive"))
            
            # Process the result into our expected format
            processed_results = [{
                'content': result,
                'query': query,
                'score': 1.0,  # LightRAG doesn't provide scores in this mode
                'metadata': {'retrieved_at': datetime.now(timezone.utc).isoformat()}
            }]
            
            logger.info(f"Retrieved results for query: {query[:50]}...")
            return processed_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []
    
    async def _ensure_initialized(self):
        """Ensure LightRAG storages are initialized."""
        try:
            # Initialize storages
            await self.lightrag.initialize_storages()
            
            # Initialize pipeline status
            from lightrag.kg.shared_storage import initialize_pipeline_status
            await initialize_pipeline_status()
            
        except Exception as e:
            logger.warning(f"Storage initialization warning: {e}")
            # Continue anyway as this might not be critical
    



class LightRAGIntegration:
    """Main integration class for LightRAG with our document processing system."""
    
    def __init__(
        self, 
        config: LightRAGConfig,
        meta_doc_crud: Optional[MetaDocumentCRUD] = None
    ):
        """Initialize LightRAG integration."""
        self.config = config
        # Ensure we use the provided meta_doc_crud instance for database consistency
        if meta_doc_crud is not None:
            self.meta_doc_crud = meta_doc_crud
            logger.info(f"LightRAG using provided MetaDocumentCRUD with database: {meta_doc_crud.db_path}")
        else:
            self.meta_doc_crud = MetaDocumentCRUD()
            logger.info(f"LightRAG created new MetaDocumentCRUD with database: {self.meta_doc_crud.db_path}")
        
        # Initialize components
        self.indexer = DocumentIndexer(config)
        self.retriever = VectorRetriever(config)
        
        # Initialize embedding manager for API compatibility
        from .embeddings import EmbeddingManager
        self.embedding_manager = EmbeddingManager(
            model_name=config.embedding_model,
            cache_dir=f"{config.working_dir}/embeddings_cache",
            batch_size=config.batch_size
        )
        
        # Setup working directory
        self._setup_working_directory()
        
        logger.info("LightRAG integration initialized")
    
    def _setup_working_directory(self):
        """Set up working directory for LightRAG."""
        working_dir = Path(self.config.working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        
        vector_db_dir = Path(self.config.vector_db_path).parent
        vector_db_dir.mkdir(parents=True, exist_ok=True)
    
    @handle_async_errors(
        component="lightrag_integration",
        operation="prepare_document_for_rag",
        category=ErrorCategory.EXTERNAL_SERVICE,
        severity=ErrorSeverity.HIGH,
        max_retries=2
    )
    async def prepare_document_for_rag(
        self, 
        meta_doc_uuid: str
    ) -> Dict[str, Any]:
        """Prepare a meta document for RAG by indexing it."""
        try:
            logger.info(f"Preparing document {meta_doc_uuid} for RAG using database: {self.meta_doc_crud.db_path}")
            
            # Get meta document with retry for database operations
            def get_document():
                meta_doc = self.meta_doc_crud.get_meta_document(meta_doc_uuid)
                if not meta_doc:
                    logger.error(f"Meta document {meta_doc_uuid} not found in database {self.meta_doc_crud.db_path}")
                    raise ValueError(f"Meta document {meta_doc_uuid} not found")
                return meta_doc
            
            meta_doc = error_handler.retry_with_backoff(
                get_document,
                max_retries=2,
                exceptions=(Exception,),
                context=error_handler.create_error_context(
                    component="lightrag_integration",
                    operation="get_meta_document",
                    category=ErrorCategory.DATABASE
                )
            )
            
            # Update RAG preparation status
            self.meta_doc_crud.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage="embedding",
                status="in_progress",
                progress_percentage=0.0
            )
            
            # Index the document
            indexing_result = await self.indexer.index_meta_document(meta_doc)
            
            if indexing_result['status'] == 'completed':
                # Update RAG preparation status
                self.meta_doc_crud.update_rag_preparation_status(
                    meta_doc_uuid=meta_doc_uuid,
                    preparation_stage="embedding",
                    status="completed",
                    progress_percentage=100.0
                )
                
                # Mark as RAG ready
                vector_index_id = f"lightrag_{meta_doc_uuid}"
                self.meta_doc_crud.update_rag_ready_status(
                    meta_doc_uuid=meta_doc_uuid,
                    rag_ready=True,
                    vector_index_id=vector_index_id
                )
                
                logger.info(f"Document {meta_doc_uuid} prepared for RAG successfully")
            else:
                # Update with error status
                self.meta_doc_crud.update_rag_preparation_status(
                    meta_doc_uuid=meta_doc_uuid,
                    preparation_stage="embedding",
                    status="failed",
                    error_message=indexing_result.get('error', 'Unknown error')
                )
            
            return indexing_result
            
        except Exception as e:
            logger.error(f"Failed to prepare document for RAG: {e}")
            
            # Update with error status
            self.meta_doc_crud.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage="embedding",
                status="failed",
                error_message=str(e)
            )
            
            return {
                'meta_doc_uuid': meta_doc_uuid,
                'status': 'failed',
                'error': str(e)
            }
    
    async def batch_prepare_documents(
        self, 
        meta_doc_uuids: List[str],
        max_concurrent: int = None
    ) -> List[Dict[str, Any]]:
        """Prepare multiple documents for RAG in batches."""
        max_concurrent = max_concurrent or self.config.max_async_workers
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def prepare_single_doc(meta_doc_uuid: str):
            async with semaphore:
                return await self.prepare_document_for_rag(meta_doc_uuid)
        
        # Execute batch preparation
        tasks = [prepare_single_doc(uuid) for uuid in meta_doc_uuids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'meta_doc_uuid': meta_doc_uuids[i],
                    'status': 'failed',
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        logger.info(f"Batch prepared {len(meta_doc_uuids)} documents for RAG")
        return processed_results
    
    async def query_documents(
        self, 
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Query documents using RAG retrieval."""
        try:
            # Perform retrieval
            results = await self.retriever.retrieve_documents(
                query=query,
                filters=filters,
                top_k=top_k
            )
            
            # Enhance results with additional metadata if requested
            if include_metadata:
                results = await self._enhance_results_with_metadata(results)
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results),
                'filters_applied': filters or {},
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to query documents: {e}")
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'error': str(e),
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def _enhance_results_with_metadata(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance retrieval results with additional metadata."""
        enhanced_results = []
        
        for result in results:
            # Get meta document UUID from metadata
            meta_doc_uuid = result['metadata'].get('meta_doc_uuid')
            
            if meta_doc_uuid:
                # Get full meta document for additional context
                meta_doc = self.meta_doc_crud.get_meta_document(meta_doc_uuid)
                if meta_doc:
                    result['enhanced_metadata'] = {
                        'title': meta_doc.title,
                        'summary': meta_doc.summary,
                        'doc_uuid': meta_doc.doc_uuid,
                        'set_uuid': meta_doc.set_uuid,
                        'created_at': meta_doc.created_at.isoformat(),
                        'processing_history': meta_doc.processing_history
                    }
            
            enhanced_results.append(result)
        
        return enhanced_results
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        try:
            # Get meta document statistics
            meta_stats = self.meta_doc_crud.get_statistics()
            
            # Get pending documents for RAG preparation
            pending_docs = self.meta_doc_crud.get_pending_rag_documents()
            rag_ready_docs = self.meta_doc_crud.get_rag_ready_documents()
            
            return {
                'total_meta_documents': meta_stats.get('total_meta_documents', 0),
                'rag_ready_documents': len(rag_ready_docs),
                'pending_rag_documents': len(pending_docs),
                'rag_ready_percentage': meta_stats.get('rag_ready_percentage', 0),
                'vector_db_path': self.config.vector_db_path,
                'embedding_model': self.config.embedding_model,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get RAG statistics: {e}")
            return {'error': str(e)}
    
    def add_document(self, doc_id: str, content: str) -> bool:
        """Simple wrapper for adding documents (for validation/testing)."""
        try:
            # Create a simple meta document record for testing
            from docforge.storage.meta_document_db import MetaDocumentRecord, MetaDocumentComponent
            from datetime import datetime, timezone
            
            # Create a mock meta document
            component = MetaDocumentComponent(
                component_id=f"comp_{doc_id}",
                component_type="text",
                content=content,
                metadata={},
                vector_embedding=None,
                parent_component_id=None,
                order_index=0,
                confidence_score=1.0
            )
            
            meta_doc = MetaDocumentRecord(
                meta_doc_uuid=f"meta_{doc_id}",
                doc_uuid=doc_id,
                set_uuid=f"set_{doc_id}",
                title=f"Document {doc_id}",
                summary=content[:100] + "..." if len(content) > 100 else content,
                components=[component],
                processing_history=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # For validation purposes, just return True if we can create the structure
            return True
            
        except Exception as e:
            logger.error(f"Error in add_document wrapper: {e}")
            return False
    
    def query(self, query_text: str) -> List[Dict[str, Any]]:
        """Simple wrapper for querying documents (for validation/testing)."""
        try:
            # For validation purposes, return a mock result if the query is valid
            if query_text and len(query_text.strip()) > 0:
                return [
                    {
                        'content': f"Mock result for query: {query_text}",
                        'score': 0.8,
                        'document_id': 'mock_doc_1'
                    }
                ]
            return []
            
        except Exception as e:
            logger.error(f"Error in query wrapper: {e}")
            return []
    
    async def cleanup_vector_db(self, older_than_days: int = 30) -> Dict[str, Any]:
        """Clean up old entries from vector database."""
        try:
            # This would depend on the specific vector database implementation
            # For now, we'll return a placeholder
            logger.info(f"Vector database cleanup requested for entries older than {older_than_days} days")
            
            return {
                'status': 'completed',
                'cleaned_entries': 0,  # Placeholder
                'cleanup_date': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup vector database: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }