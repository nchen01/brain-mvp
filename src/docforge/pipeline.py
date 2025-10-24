"""
DocForge Pipeline Integration with Versioning Support.

This module provides the main pipeline orchestrator that connects:
- Document registration and versioning
- Preprocessing (routing and processing)
- Postprocessing (chunking, abbreviation expansion)
- Storage systems (Raw, Post, Meta Document databases)
- RAG preparation with version tracking

The pipeline ensures complete version chain integrity throughout all processing stages.
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import RawDocument, ProcessedDocument
from docforge.versioning.lineage import DocumentLineageManager
from docforge.versioning.models import DocumentVersion
from docforge.preprocessing.router import DocumentPreprocessingRouter
from docforge.preprocessing.processor_factory import ProcessorFactory
from docforge.postprocessing.router import PostProcessingRouter
from docforge.storage.register import DocumentRegister
from docforge.storage.post_document_register import PostDocumentRegister
from docforge.storage.meta_document_crud import MetaDocumentCRUD
from docforge.rag.rag_database_preparation import RAGDatabasePreparation, RAGChunkConfig
from utils.logging_integration import (
    document_processing_context, postprocessing_context, rag_operation_context,
    preprocessing_logger, postprocessing_logger, storage_logger, rag_logger
)


class PipelineStage(str, Enum):
    """Pipeline processing stages."""
    REGISTRATION = "registration"
    PREPROCESSING = "preprocessing"
    POSTPROCESSING = "postprocessing"
    STORAGE = "storage"
    RAG_PREPARATION = "rag_preparation"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """Result of pipeline processing."""
    success: bool
    document_uuid: str
    lineage_uuid: str
    version_number: int
    stage_reached: PipelineStage
    processing_time: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PipelineConfig:
    """Configuration for pipeline processing."""
    # Database paths
    raw_db_path: str = "./data/raw_documents.db"
    post_db_path: str = "./data/post_documents.db"
    meta_db_path: str = "./data/meta_documents.db"
    
    # Storage directories
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"
    
    # RAG configuration
    lightrag_dir: str = "./data/lightrag"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Processing options
    enable_postprocessing: bool = True
    enable_rag_preparation: bool = True
    enable_abbreviation_expansion: bool = True
    
    # Performance settings
    max_concurrent_documents: int = 5
    processing_timeout: int = 300


class DocForgePipeline:
    """
    Main DocForge pipeline orchestrator with versioning support.
    
    Integrates all DocForge components into a cohesive processing pipeline
    that maintains version chain integrity throughout all stages.
    """
    
    def __init__(self, config: PipelineConfig):
        """Initialize the pipeline with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_components()
        
        # Track processing state
        self.active_processes: Dict[str, PipelineStage] = {}
        
    def _initialize_components(self):
        """Initialize all pipeline components."""
        try:
            # Versioning and lineage management
            self.lineage_manager = DocumentLineageManager(self.config.raw_db_path)
            
            # Document registration
            self.document_register = DocumentRegister(self.config.raw_db_path)
            self.post_document_register = PostDocumentRegister(self.config.post_db_path)
            
            # Processing components
            self.preprocessing_router = DocumentPreprocessingRouter()
            self.processor_factory = ProcessorFactory()
            self.postprocessing_router = PostProcessingRouter()
            
            # Storage systems
            self.meta_document_crud = MetaDocumentCRUD(self.config.meta_db_path)
            
            # RAG preparation
            self.rag_preparation = RAGDatabasePreparation(
                lightrag_dir=self.config.lightrag_dir,
                meta_document_crud=self.meta_document_crud,
                embedding_model=self.config.embedding_model
            )
            
            # Create necessary directories
            for directory in [self.config.upload_dir, self.config.processed_dir, self.config.lightrag_dir]:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            preprocessing_logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            preprocessing_logger.error(f"Failed to initialize pipeline components: {str(e)}")
            raise
    
    async def process_document(
        self,
        file_path: str,
        file_content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        parent_version: Optional[int] = None,
        lineage_uuid: Optional[str] = None
    ) -> PipelineResult:
        """
        Process a document through the complete pipeline with versioning.
        
        Args:
            file_path: Path to the document file
            file_content: Binary content of the document
            filename: Original filename
            user_id: User who uploaded the document
            parent_version: Version number to branch from (for editing old versions)
            lineage_uuid: Existing lineage UUID (for adding to existing lineage)
        
        Returns:
            PipelineResult with processing outcome and metadata
        """
        start_time = time.time()
        document_uuid = str(uuid.uuid4())
        
        try:
            # Stage 1: Document Registration and Versioning
            preprocessing_logger.info(f"Starting pipeline processing for document: {filename}")
            
            registration_result = await self._register_document(
                document_uuid, file_path, file_content, filename, user_id,
                parent_version, lineage_uuid
            )
            
            if not registration_result['success']:
                return PipelineResult(
                    success=False,
                    document_uuid=document_uuid,
                    lineage_uuid=registration_result.get('lineage_uuid', ''),
                    version_number=registration_result.get('version_number', 0),
                    stage_reached=PipelineStage.REGISTRATION,
                    processing_time=time.time() - start_time,
                    error_message=registration_result.get('error')
                )
            
            lineage_uuid = registration_result['lineage_uuid']
            version_number = registration_result['version_number']
            
            # Track processing
            self.active_processes[document_uuid] = PipelineStage.PREPROCESSING
            
            # Stage 2: Preprocessing
            preprocessing_result = await self._preprocess_document(
                document_uuid, file_path, file_content, filename
            )
            
            if not preprocessing_result['success']:
                return PipelineResult(
                    success=False,
                    document_uuid=document_uuid,
                    lineage_uuid=lineage_uuid,
                    version_number=version_number,
                    stage_reached=PipelineStage.PREPROCESSING,
                    processing_time=time.time() - start_time,
                    error_message=preprocessing_result.get('error')
                )
            
            processed_document = preprocessing_result['processed_document']
            
            # Stage 3: Postprocessing (if enabled)
            if self.config.enable_postprocessing:
                self.active_processes[document_uuid] = PipelineStage.POSTPROCESSING
                
                postprocessing_result = await self._postprocess_document(
                    document_uuid, processed_document
                )
                
                if not postprocessing_result['success']:
                    return PipelineResult(
                        success=False,
                        document_uuid=document_uuid,
                        lineage_uuid=lineage_uuid,
                        version_number=version_number,
                        stage_reached=PipelineStage.POSTPROCESSING,
                        processing_time=time.time() - start_time,
                        error_message=postprocessing_result.get('error')
                    )
                
                processed_document = postprocessing_result['processed_document']
            
            # Stage 4: Storage
            self.active_processes[document_uuid] = PipelineStage.STORAGE
            
            storage_result = await self._store_document(
                document_uuid, lineage_uuid, version_number, processed_document
            )
            
            if not storage_result['success']:
                return PipelineResult(
                    success=False,
                    document_uuid=document_uuid,
                    lineage_uuid=lineage_uuid,
                    version_number=version_number,
                    stage_reached=PipelineStage.STORAGE,
                    processing_time=time.time() - start_time,
                    error_message=storage_result.get('error')
                )
            
            # Stage 5: RAG Preparation (if enabled)
            if self.config.enable_rag_preparation:
                self.active_processes[document_uuid] = PipelineStage.RAG_PREPARATION
                
                rag_result = await self._prepare_for_rag(
                    document_uuid, lineage_uuid, version_number
                )
                
                if not rag_result['success']:
                    return PipelineResult(
                        success=False,
                        document_uuid=document_uuid,
                        lineage_uuid=lineage_uuid,
                        version_number=version_number,
                        stage_reached=PipelineStage.RAG_PREPARATION,
                        processing_time=time.time() - start_time,
                        error_message=rag_result.get('error')
                    )
            
            # Pipeline completed successfully
            self.active_processes[document_uuid] = PipelineStage.COMPLETED
            processing_time = time.time() - start_time
            
            preprocessing_logger.info(
                f"Pipeline processing completed successfully for document {document_uuid} "
                f"in {processing_time:.2f} seconds"
            )
            
            return PipelineResult(
                success=True,
                document_uuid=document_uuid,
                lineage_uuid=lineage_uuid,
                version_number=version_number,
                stage_reached=PipelineStage.COMPLETED,
                processing_time=processing_time,
                metadata={
                    'filename': filename,
                    'user_id': user_id,
                    'file_size': len(file_content),
                    'processing_stages': ['registration', 'preprocessing', 'postprocessing', 'storage', 'rag_preparation']
                }
            )
            
        except Exception as e:
            self.active_processes[document_uuid] = PipelineStage.FAILED
            error_msg = f"Pipeline processing failed: {str(e)}"
            preprocessing_logger.error(error_msg, exc_info=True)
            
            return PipelineResult(
                success=False,
                document_uuid=document_uuid,
                lineage_uuid=lineage_uuid if 'lineage_uuid' in locals() else '',
                version_number=version_number if 'version_number' in locals() else 0,
                stage_reached=PipelineStage.FAILED,
                processing_time=time.time() - start_time,
                error_message=error_msg
            )
        
        finally:
            # Clean up tracking
            if document_uuid in self.active_processes:
                del self.active_processes[document_uuid]
    
    async def _register_document(
        self,
        document_uuid: str,
        file_path: str,
        file_content: bytes,
        filename: str,
        user_id: Optional[str],
        parent_version: Optional[int],
        lineage_uuid: Optional[str]
    ) -> Dict[str, Any]:
        """Register document with versioning support."""
        try:
            with document_processing_context(document_uuid, "registration"):
                # Create or get lineage
                if lineage_uuid:
                    # Adding to existing lineage
                    lineage = self.lineage_manager.get_lineage(lineage_uuid)
                    if not lineage:
                        return {'success': False, 'error': f'Lineage {lineage_uuid} not found'}
                else:
                    # Create new lineage
                    lineage_uuid = self.lineage_manager.create_lineage(
                        original_filename=filename,
                        created_by=user_id or 'anonymous'
                    )
                
                # Determine version number
                if parent_version:
                    # Branching from specific version
                    version_number = self.lineage_manager.get_next_version_number(lineage_uuid)
                else:
                    # Linear versioning
                    version_number = self.lineage_manager.get_next_version_number(lineage_uuid)
                
                # Create document version
                document_version = self.lineage_manager.create_version(
                    lineage_uuid=lineage_uuid,
                    doc_uuid=document_uuid,
                    version_number=version_number,
                    parent_version=parent_version,
                    created_by=user_id or 'anonymous',
                    file_hash=self._calculate_file_hash(file_content),
                    metadata={'filename': filename, 'file_size': len(file_content)}
                )
                
                # Register in document register
                raw_document = RawDocument(
                    uuid=document_uuid,
                    filename=filename,
                    file_path=file_path,
                    file_size=len(file_content),
                    file_type=self._detect_file_type(filename),
                    created_by=user_id or 'anonymous'
                )
                
                self.document_register.register_document(raw_document, file_content)
                
                preprocessing_logger.info(
                    f"Document registered successfully: {document_uuid} "
                    f"(lineage: {lineage_uuid}, version: {version_number})"
                )
                
                return {
                    'success': True,
                    'lineage_uuid': lineage_uuid,
                    'version_number': version_number,
                    'document_version': document_version
                }
                
        except Exception as e:
            error_msg = f"Document registration failed: {str(e)}"
            preprocessing_logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _preprocess_document(
        self,
        document_uuid: str,
        file_path: str,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Preprocess document using appropriate processor."""
        try:
            with document_processing_context(document_uuid, "preprocessing"):
                # Route to appropriate processor
                routing_decision = self.preprocessing_router.route_document(filename, file_content)
                processor = self.processor_factory.get_processor_for_file(filename, file_content)
                
                preprocessing_logger.info(
                    f"Processing document {document_uuid} with {routing_decision.get('processor_type', 'unknown')}"
                )
                
                # Process document
                result = processor.process_document(filename, file_content=file_content)
                
                if not result.success:
                    return {
                        'success': False,
                        'error': f"Preprocessing failed: {result.error.error_message if result.error else 'Unknown error'}"
                    }
                
                preprocessing_logger.info(
                    f"Document {document_uuid} preprocessed successfully "
                    f"({result.output.document_structure.total_pages} pages, "
                    f"{len(result.output.content_elements)} elements)"
                )
                
                return {
                    'success': True,
                    'processed_document': result.output,
                    'processor_type': routing_decision.get('processor_type', 'unknown')
                }
                
        except Exception as e:
            error_msg = f"Preprocessing failed: {str(e)}"
            preprocessing_logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _postprocess_document(
        self,
        document_uuid: str,
        processed_document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Postprocess document with chunking and enhancement."""
        try:
            with postprocessing_context(document_uuid, "postprocessing"):
                # Route to appropriate postprocessing methods
                postprocessing_methods = self.postprocessing_router.route_document(
                    processed_document
                )
                
                postprocessing_logger.info(
                    f"Postprocessing document {document_uuid} with methods: {postprocessing_methods}"
                )
                
                enhanced_document = processed_document
                
                # Apply chunking if requested
                if 'chunking' in postprocessing_methods:
                    from docforge.postprocessing.chunker import DocumentChunker
                    chunker = DocumentChunker()
                    
                    chunks = chunker.chunk_document(
                        enhanced_document,
                        strategy=postprocessing_methods['chunking'].get('strategy', 'paragraph'),
                        chunk_size=self.config.chunk_size,
                        overlap=self.config.chunk_overlap
                    )
                    
                    # Update document with chunks
                    enhanced_document.chunks = chunks
                    
                    postprocessing_logger.info(
                        f"Document {document_uuid} chunked into {len(chunks)} chunks"
                    )
                
                # Apply abbreviation expansion if enabled and requested
                if (self.config.enable_abbreviation_expansion and 
                    'abbreviation_expansion' in postprocessing_methods):
                    
                    from docforge.postprocessing.abbreviation_expander import AbbreviationExpander
                    expander = AbbreviationExpander()
                    
                    expanded_document = expander.expand_abbreviations(enhanced_document)
                    enhanced_document = expanded_document
                    
                    postprocessing_logger.info(
                        f"Document {document_uuid} abbreviations expanded"
                    )
                
                return {
                    'success': True,
                    'processed_document': enhanced_document,
                    'methods_applied': list(postprocessing_methods.keys())
                }
                
        except Exception as e:
            error_msg = f"Postprocessing failed: {str(e)}"
            postprocessing_logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _store_document(
        self,
        document_uuid: str,
        lineage_uuid: str,
        version_number: int,
        processed_document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Store processed document in storage systems."""
        try:
            with storage_logger.context(document_id=document_uuid, lineage_uuid=lineage_uuid):
                # Register in post-document register
                self.post_document_register.register_processed_document(
                    doc_uuid=document_uuid,
                    processed_document=processed_document,
                    processing_metadata={
                        'lineage_uuid': lineage_uuid,
                        'version_number': version_number,
                        'processing_timestamp': time.time()
                    }
                )
                
                # Create meta document
                meta_doc_uuid = self.meta_document_crud.create_meta_document(
                    doc_uuid=document_uuid,
                    set_uuid=lineage_uuid,  # Use lineage as set identifier
                    title=processed_document.metadata.get('title', f'Document {document_uuid}'),
                    summary=processed_document.metadata.get('summary', ''),
                    components=self._extract_components(processed_document)
                )
                
                storage_logger.info(
                    f"Document {document_uuid} stored successfully "
                    f"(meta document: {meta_doc_uuid})"
                )
                
                return {
                    'success': True,
                    'meta_doc_uuid': meta_doc_uuid
                }
                
        except Exception as e:
            error_msg = f"Storage failed: {str(e)}"
            storage_logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _prepare_for_rag(
        self,
        document_uuid: str,
        lineage_uuid: str,
        version_number: int
    ) -> Dict[str, Any]:
        """Prepare document for RAG system."""
        try:
            with rag_operation_context(document_uuid, "rag_preparation"):
                # Configure RAG chunking
                chunk_config = RAGChunkConfig(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    embedding_model=self.config.embedding_model
                )
                
                # Prepare document for RAG
                rag_result = await self.rag_preparation.prepare_document_for_rag(
                    document_uuid=document_uuid,
                    chunk_config=chunk_config
                )
                
                if not rag_result['success']:
                    return {
                        'success': False,
                        'error': f"RAG preparation failed: {rag_result.get('error', 'Unknown error')}"
                    }
                
                rag_logger.info(
                    f"Document {document_uuid} prepared for RAG successfully "
                    f"({rag_result.get('chunks_created', 0)} chunks, "
                    f"{rag_result.get('embeddings_created', 0)} embeddings)"
                )
                
                return {
                    'success': True,
                    'rag_metadata': rag_result
                }
                
        except Exception as e:
            error_msg = f"RAG preparation failed: {str(e)}"
            rag_logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        import hashlib
        return hashlib.sha256(file_content).hexdigest()
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename."""
        suffix = Path(filename).suffix.lower()
        type_mapping = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.txt': 'text/plain'
        }
        return type_mapping.get(suffix, 'application/octet-stream')
    
    def _extract_components(self, processed_document: ProcessedDocument) -> List[Dict[str, Any]]:
        """Extract components from processed document for meta document."""
        components = []
        
        # Add text content as primary component
        if processed_document.plain_text:
            components.append({
                'type': 'text',
                'content': processed_document.plain_text[:1000],  # Truncate for storage
                'metadata': {
                    'length': len(processed_document.plain_text),
                    'format': 'plain_text'
                }
            })
        
        # Add markdown content if available
        if processed_document.markdown_text:
            components.append({
                'type': 'markdown',
                'content': processed_document.markdown_text[:1000],  # Truncate for storage
                'metadata': {
                    'length': len(processed_document.markdown_text),
                    'format': 'markdown'
                }
            })
        
        # Add tables as components
        for i, table in enumerate(processed_document.tables):
            components.append({
                'type': 'table',
                'content': str(table.data)[:500],  # Truncate for storage
                'metadata': {
                    'table_index': i,
                    'rows': len(table.data) if table.data else 0,
                    'caption': table.caption
                }
            })
        
        # Add images as components
        for i, image in enumerate(processed_document.images):
            components.append({
                'type': 'image',
                'content': image.alt_text or f'Image {i+1}',
                'metadata': {
                    'image_index': i,
                    'file_path': image.file_path,
                    'caption': image.caption
                }
            })
        
        return components
    
    def get_processing_status(self, document_uuid: str) -> Dict[str, Any]:
        """Get current processing status for a document."""
        stage = self.active_processes.get(document_uuid, PipelineStage.COMPLETED)
        
        return {
            'document_uuid': document_uuid,
            'current_stage': stage,
            'is_processing': stage not in [PipelineStage.COMPLETED, PipelineStage.FAILED],
            'timestamp': time.time()
        }
    
    def get_version_chain_status(self, lineage_uuid: str) -> Dict[str, Any]:
        """Get processing status for all versions in a lineage chain."""
        try:
            lineage = self.lineage_manager.get_lineage(lineage_uuid)
            if not lineage:
                return {'error': f'Lineage {lineage_uuid} not found'}
            
            versions = self.lineage_manager.get_versions_by_lineage(lineage_uuid)
            version_statuses = []
            
            for version in versions:
                status = self.get_processing_status(version.doc_uuid)
                version_statuses.append({
                    'version_number': version.version_number,
                    'doc_uuid': version.doc_uuid,
                    'status': status,
                    'created_at': version.created_at,
                    'is_deleted': version.is_deleted
                })
            
            return {
                'lineage_uuid': lineage_uuid,
                'original_filename': lineage.original_filename,
                'versions': version_statuses,
                'total_versions': len(versions)
            }
            
        except Exception as e:
            return {'error': f'Failed to get version chain status: {str(e)}'}
    
    async def process_batch(
        self,
        documents: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[PipelineResult]:
        """Process multiple documents concurrently."""
        max_concurrent = max_concurrent or self.config.max_concurrent_documents
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(doc_info):
            async with semaphore:
                return await self.process_document(**doc_info)
        
        tasks = [process_single(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(PipelineResult(
                    success=False,
                    document_uuid=documents[i].get('filename', f'doc_{i}'),
                    lineage_uuid='',
                    version_number=0,
                    stage_reached=PipelineStage.FAILED,
                    processing_time=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def shutdown(self):
        """Shutdown pipeline and cleanup resources."""
        preprocessing_logger.info("Shutting down DocForge pipeline")
        
        # Wait for active processes to complete (with timeout)
        if self.active_processes:
            preprocessing_logger.warning(
                f"Shutting down with {len(self.active_processes)} active processes"
            )
        
        # Cleanup components
        try:
            if hasattr(self.rag_preparation, 'cleanup'):
                self.rag_preparation.cleanup()
        except Exception as e:
            preprocessing_logger.error(f"Error during RAG cleanup: {str(e)}")
        
        preprocessing_logger.info("DocForge pipeline shutdown completed")


# Convenience function for creating configured pipeline
def create_pipeline(config: Optional[PipelineConfig] = None) -> DocForgePipeline:
    """Create a DocForge pipeline with default or custom configuration."""
    if config is None:
        config = PipelineConfig()
    
    return DocForgePipeline(config)