"""Document indexing management for RAG operations."""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timezone
from pathlib import Path
import uuid

# LightRAG imports (optional)
try:
    from lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LightRAG = None
    EmbeddingFunc = None
    LIGHTRAG_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Our imports
from .embeddings import EmbeddingManager
from docforge.storage.meta_document_db import MetaDocumentRecord, MetaDocumentComponent
from docforge.storage.meta_document_crud import MetaDocumentCRUD

logger = logging.getLogger(__name__)


class DocumentIndexManager:
    """Manages document indexing for RAG operations."""
    
    def __init__(
        self,
        index_path: str = "data/document_index",
        embedding_manager: Optional[EmbeddingManager] = None,
        meta_doc_crud: Optional[MetaDocumentCRUD] = None,
        embedding_dim: int = 384
    ):
        """Initialize the document index manager."""
        self.index_path = Path(index_path)
        self.embedding_dim = embedding_dim
        
        # Create index directory
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.meta_doc_crud = meta_doc_crud or MetaDocumentCRUD()
        
        # Initialize LightRAG
        self.lightrag = None
        self._setup_lightrag()
        
        # Index metadata
        self.index_metadata = self._load_index_metadata()
    
    def _setup_lightrag(self):
        """Set up LightRAG."""
        try:
            # Initialize sentence transformer model
            embedding_model = SentenceTransformer(self.embedding_manager.model_name)
            
            # Create embedding function
            def embedding_func(texts: List[str]) -> List[List[float]]:
                embeddings = embedding_model.encode(texts)
                return embeddings.tolist()
            
            # Create EmbeddingFunc wrapper
            embedding_func_wrapper = EmbeddingFunc(
                embedding_dim=self.embedding_dim,
                func=embedding_func
            )
            
            # Create a simple mock LLM function
            def mock_llm_func(prompt: str, **kwargs) -> str:
                return "Mock LLM response for indexing purposes."
            
            # Initialize LightRAG
            self.lightrag = LightRAG(
                working_dir=str(self.index_path),
                embedding_func=embedding_func_wrapper,
                llm_model_func=mock_llm_func
            )
            
            logger.info(f"LightRAG initialized at {self.index_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            raise
    
    def _load_index_metadata(self) -> Dict[str, Any]:
        """Load index metadata from disk."""
        metadata_file = self.index_path / "index_metadata.json"
        
        try:
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                logger.info("Loaded index metadata")
                return metadata
        except Exception as e:
            logger.warning(f"Failed to load index metadata: {e}")
        
        # Return default metadata
        return {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'total_documents': 0,
            'total_components': 0,
            'embedding_model': self.embedding_manager.model_name,
            'embedding_dim': self.embedding_dim,
            'indexed_meta_docs': {}
        }
    
    def _save_index_metadata(self):
        """Save index metadata to disk."""
        metadata_file = self.index_path / "index_metadata.json"
        
        try:
            self.index_metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            with open(metadata_file, 'w') as f:
                json.dump(self.index_metadata, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save index metadata: {e}")
    
    async def index_meta_document(
        self, 
        meta_doc_uuid: str,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """Index a meta document for RAG retrieval."""
        try:
            # Check if already indexed
            if not force_reindex and meta_doc_uuid in self.index_metadata['indexed_meta_docs']:
                existing_entry = self.index_metadata['indexed_meta_docs'][meta_doc_uuid]
                logger.info(f"Meta document {meta_doc_uuid} already indexed at {existing_entry['indexed_at']}")
                return {
                    'meta_doc_uuid': meta_doc_uuid,
                    'status': 'already_indexed',
                    'indexed_at': existing_entry['indexed_at']
                }
            
            # Get meta document
            meta_doc = self.meta_doc_crud.get_meta_document(meta_doc_uuid)
            if not meta_doc:
                raise ValueError(f"Meta document {meta_doc_uuid} not found")
            
            # Update RAG preparation status
            self.meta_doc_crud.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage="indexing",
                status="in_progress",
                progress_percentage=0.0
            )
            
            # Convert components to indexable documents
            indexable_docs = await self._prepare_components_for_indexing(meta_doc)
            
            # Generate embeddings for components
            embedded_docs = await self._embed_documents(indexable_docs)
            
            # Store in vector database
            vector_ids = await self._store_in_vector_db(embedded_docs)
            
            # Update component embeddings in meta document
            await self._update_component_embeddings(meta_doc, embedded_docs)
            
            # Update index metadata
            self.index_metadata['indexed_meta_docs'][meta_doc_uuid] = {
                'indexed_at': datetime.now(timezone.utc).isoformat(),
                'component_count': len(indexable_docs),
                'vector_ids': vector_ids,
                'title': meta_doc.title,
                'doc_uuid': meta_doc.doc_uuid,
                'set_uuid': meta_doc.set_uuid
            }
            
            self.index_metadata['total_documents'] += 1
            self.index_metadata['total_components'] += len(indexable_docs)
            self._save_index_metadata()
            
            # Update RAG preparation status
            self.meta_doc_crud.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage="indexing",
                status="completed",
                progress_percentage=100.0
            )
            
            result = {
                'meta_doc_uuid': meta_doc_uuid,
                'status': 'indexed',
                'component_count': len(indexable_docs),
                'vector_ids': vector_ids,
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Successfully indexed meta document {meta_doc_uuid} with {len(indexable_docs)} components")
            return result
            
        except Exception as e:
            logger.error(f"Failed to index meta document {meta_doc_uuid}: {e}")
            
            # Update RAG preparation status with error
            self.meta_doc_crud.update_rag_preparation_status(
                meta_doc_uuid=meta_doc_uuid,
                preparation_stage="indexing",
                status="failed",
                error_message=str(e)
            )
            
            return {
                'meta_doc_uuid': meta_doc_uuid,
                'status': 'failed',
                'error': str(e),
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def _prepare_components_for_indexing(
        self, 
        meta_doc: MetaDocumentRecord
    ) -> List[Dict[str, Any]]:
        """Prepare meta document components for indexing."""
        indexable_docs = []
        
        for component in meta_doc.components:
            # Skip empty components
            if not component.content.strip():
                continue
            
            # Create indexable document
            doc_data = {
                'id': component.component_id,
                'text': component.content,
                'meta_data': {
                    'meta_doc_uuid': meta_doc.meta_doc_uuid,
                    'doc_uuid': meta_doc.doc_uuid,
                    'set_uuid': meta_doc.set_uuid,
                    'component_type': component.component_type,
                    'order_index': component.order_index,
                    'confidence_score': component.confidence_score,
                    'title': meta_doc.title,
                    'summary': meta_doc.summary,
                    'created_at': component.created_at.isoformat(),
                    **component.metadata
                },
                'parent_doc_id': meta_doc.meta_doc_uuid
            }
            
            indexable_docs.append(doc_data)
        
        return indexable_docs
    
    async def _embed_documents(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for documents."""
        try:
            # Extract texts
            texts = [doc['text'] for doc in documents]
            
            # Generate embeddings
            embeddings = await self.embedding_manager.embed_texts(texts)
            
            # Add embeddings to documents
            embedded_docs = []
            for i, doc in enumerate(documents):
                embedded_doc = doc.copy()
                embedded_doc['embedding'] = embeddings[i]
                embedded_docs.append(embedded_doc)
            
            return embedded_docs
            
        except Exception as e:
            logger.error(f"Failed to embed documents: {e}")
            raise
    
    async def _store_in_vector_db(
        self, 
        embedded_docs: List[Dict[str, Any]]
    ) -> List[str]:
        """Store embedded documents in vector database."""
        try:
            vector_ids = []
            
            for doc_data in embedded_docs:
                # Create LightRAG Document
                doc = Document(
                    id=doc_data['id'],
                    text=doc_data['text'],
                    meta_data=doc_data['meta_data'],
                    vector=doc_data['embedding'],
                    parent_doc_id=doc_data['parent_doc_id']
                )
                
                # Store in vector database
                vector_id = await self.vector_db.insert(doc)
                vector_ids.append(vector_id)
            
            return vector_ids
            
        except Exception as e:
            logger.error(f"Failed to store in vector database: {e}")
            raise
    
    async def _update_component_embeddings(
        self, 
        meta_doc: MetaDocumentRecord,
        embedded_docs: List[Dict[str, Any]]
    ):
        """Update component embeddings in meta document."""
        try:
            # Create mapping of component_id to embedding
            embedding_map = {
                doc['id']: doc['embedding'] 
                for doc in embedded_docs
            }
            
            # Update each component
            for component in meta_doc.components:
                if component.component_id in embedding_map:
                    embedding = embedding_map[component.component_id]
                    self.meta_doc_crud.update_component_embedding(
                        component.component_id,
                        embedding
                    )
            
        except Exception as e:
            logger.error(f"Failed to update component embeddings: {e}")
            # Don't raise here as this is not critical for indexing
    
    async def batch_index_documents(
        self, 
        meta_doc_uuids: List[str],
        max_concurrent: int = 4,
        force_reindex: bool = False
    ) -> List[Dict[str, Any]]:
        """Index multiple meta documents in batches."""
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def index_single_doc(meta_doc_uuid: str):
            async with semaphore:
                return await self.index_meta_document(meta_doc_uuid, force_reindex)
        
        # Execute batch indexing
        tasks = [index_single_doc(uuid) for uuid in meta_doc_uuids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'meta_doc_uuid': meta_doc_uuids[i],
                    'status': 'failed',
                    'error': str(result),
                    'indexed_at': datetime.now(timezone.utc).isoformat()
                })
            else:
                processed_results.append(result)
        
        logger.info(f"Batch indexed {len(meta_doc_uuids)} meta documents")
        return processed_results
    
    async def search_documents(
        self, 
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search indexed documents."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_manager.embed_text(query)
            
            # Search in vector database
            # Note: This is a simplified implementation
            # In practice, you'd use the vector database's search functionality
            results = await self._vector_search(query_embedding, top_k, filters)
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.get('score', 0) >= similarity_threshold
            ]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    async def _vector_search(
        self, 
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search in the database."""
        try:
            # This would use the vector database's search functionality
            # For now, we'll return a placeholder
            logger.info(f"Performing vector search with top_k={top_k}")
            
            # Placeholder implementation
            return []
            
        except Exception as e:
            logger.error(f"Failed to perform vector search: {e}")
            return []
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        try:
            # Get current metadata
            stats = self.index_metadata.copy()
            
            # Add runtime statistics
            stats.update({
                'index_path': str(self.index_path),
                'vector_db_path': str(self.index_path / "vector_db"),
                'embedding_manager_stats': self.embedding_manager.get_embedding_statistics()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            return {'error': str(e)}
    
    def remove_document_from_index(self, meta_doc_uuid: str) -> Dict[str, Any]:
        """Remove a document from the index."""
        try:
            if meta_doc_uuid not in self.index_metadata['indexed_meta_docs']:
                return {
                    'meta_doc_uuid': meta_doc_uuid,
                    'status': 'not_found',
                    'message': 'Document not in index'
                }
            
            # Get document info
            doc_info = self.index_metadata['indexed_meta_docs'][meta_doc_uuid]
            
            # Remove from vector database
            # Note: This would depend on the vector database implementation
            # For now, we'll just remove from metadata
            
            # Remove from metadata
            del self.index_metadata['indexed_meta_docs'][meta_doc_uuid]
            self.index_metadata['total_documents'] -= 1
            self.index_metadata['total_components'] -= doc_info.get('component_count', 0)
            
            self._save_index_metadata()
            
            logger.info(f"Removed document {meta_doc_uuid} from index")
            
            return {
                'meta_doc_uuid': meta_doc_uuid,
                'status': 'removed',
                'removed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to remove document from index: {e}")
            return {
                'meta_doc_uuid': meta_doc_uuid,
                'status': 'failed',
                'error': str(e)
            }
    
    def rebuild_index(self) -> Dict[str, Any]:
        """Rebuild the entire index."""
        try:
            logger.info("Starting index rebuild")
            
            # Clear current index
            self.index_metadata = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'total_documents': 0,
                'total_components': 0,
                'embedding_model': self.embedding_manager.model_name,
                'embedding_dim': self.embedding_dim,
                'indexed_meta_docs': {}
            }
            
            # Reinitialize vector database
            self._setup_vector_db()
            
            self._save_index_metadata()
            
            return {
                'status': 'rebuilt',
                'rebuilt_at': datetime.now(timezone.utc).isoformat(),
                'message': 'Index cleared and ready for reindexing'
            }
            
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }