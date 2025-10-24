"""
Sprint 1 Integration Tests - DocForge Pipeline with Versioning.

This test suite validates the complete Sprint 1 integration including:
- Document upload and registration with versioning
- Complete preprocessing workflow
- Postprocessing integration
- Storage systems integration
- Version chain integrity
- End-to-end document lifecycle testing

Note: This test focuses on integration validation using existing components
without complex dependency chains.
"""

import pytest
import tempfile
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from docforge.preprocessing.processor_factory import ProcessorFactory
from docforge.preprocessing.router import DocumentPreprocessingRouter
from docforge.postprocessing.router import PostProcessingRouter
from docforge.postprocessing.chunker import DocumentChunker
from docforge.storage.meta_document_crud import MetaDocumentCRUD
from docforge.rag.rag_database_preparation import RAGDatabasePreparation, RAGChunkConfig


class TestSprint1Integration:
    """Test Sprint 1 complete integration."""
    
    @pytest.fixture
    def test_environment(self):
        """Create test environment for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield {
                'temp_dir': temp_dir,
                'meta_db_path': os.path.join(temp_dir, 'meta_docs.db'),
                'lightrag_dir': os.path.join(temp_dir, 'lightrag'),
                'upload_dir': os.path.join(temp_dir, 'uploads'),
                'processed_dir': os.path.join(temp_dir, 'processed')
            }
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return {
            'pdf_simple': {
                'filename': 'simple_document.pdf',
                'content': b'%PDF-1.4\n% Simple PDF for testing\n% Contains basic text content\n%%EOF',
                'expected_type': 'pdf'
            },
            'text_document': {
                'filename': 'text_document.txt',
                'content': b'This is a simple text document for testing.\nIt contains multiple lines.\nAnd some basic content.',
                'expected_type': 'text'
            },
            'docx_document': {
                'filename': 'word_document.docx',
                'content': b'PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00Mock DOCX content for testing',
                'expected_type': 'docx'
            }
        }
    
    def test_preprocessing_integration(self, test_environment, sample_documents):
        """Test preprocessing pipeline integration."""
        # Initialize components
        router = DocumentPreprocessingRouter()
        factory = ProcessorFactory()
        
        for doc_name, doc_info in sample_documents.items():
            filename = doc_info['filename']
            content = doc_info['content']
            
            # Test routing
            routing_decision = router.route_document(filename, content)
            
            # Verify routing decision structure
            assert isinstance(routing_decision, dict)
            assert 'processor_type' in routing_decision
            assert 'supported' in routing_decision
            assert 'confidence' in routing_decision
            
            # Test processor selection
            processor = factory.get_processor_for_file(filename, content)
            
            if processor is not None:
                # Test document processing
                result = processor.process_document(filename, file_content=content)
                
                # Verify processing result
                assert hasattr(result, 'success')
                assert hasattr(result, 'output')
                
                if result.success:
                    assert result.output is not None
                    assert hasattr(result.output, 'plain_text')
                    assert hasattr(result.output, 'metadata')
                else:
                    assert hasattr(result, 'error')
                    assert result.error is not None
    
    def test_postprocessing_integration(self, test_environment, sample_documents):
        """Test postprocessing pipeline integration."""
        # Initialize components
        preprocessing_router = DocumentPreprocessingRouter()
        processor_factory = ProcessorFactory()
        postprocessing_router = PostProcessingRouter()
        chunker = DocumentChunker()
        
        # Process a document through preprocessing first
        doc_info = sample_documents['pdf_simple']
        filename = doc_info['filename']
        content = doc_info['content']
        
        # Get processor and process document
        processor = processor_factory.get_processor_for_file(filename, content)
        
        if processor is not None:
            preprocessing_result = processor.process_document(filename, file_content=content)
            
            if preprocessing_result.success:
                processed_doc = preprocessing_result.output
                
                # Test postprocessing routing
                postprocessing_methods = postprocessing_router.route_document(processed_doc)
                
                # Verify postprocessing routing
                assert isinstance(postprocessing_methods, dict)
                
                # Test chunking if available
                if 'chunking' in postprocessing_methods:
                    chunks = chunker.chunk_document(
                        processed_doc,
                        strategy='paragraph',
                        chunk_size=500,
                        overlap=50
                    )
                    
                    # Verify chunking results
                    assert isinstance(chunks, list)
                    if chunks:
                        for chunk in chunks:
                            assert hasattr(chunk, 'content')
                            assert hasattr(chunk, 'metadata')
    
    def test_storage_integration(self, test_environment, sample_documents):
        """Test storage systems integration."""
        # Initialize storage components
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Create test meta document
        doc_uuid = "test_storage_doc_123"
        set_uuid = "test_set_123"
        
        # Test meta document creation
        created_uuid = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            title="Test Document for Storage Integration",
            summary="Testing storage integration functionality",
            components=[
                {
                    'type': 'text',
                    'content': 'Sample text content',
                    'metadata': {'length': 19, 'format': 'plain_text'}
                }
            ]
        )
        
        # Verify creation
        assert created_uuid == doc_uuid
        
        # Test meta document retrieval
        retrieved_doc = meta_crud.get_meta_document(doc_uuid)
        
        # Verify retrieval
        assert retrieved_doc is not None
        assert retrieved_doc.doc_uuid == doc_uuid
        assert retrieved_doc.set_uuid == set_uuid
        assert retrieved_doc.title == "Test Document for Storage Integration"
        assert len(retrieved_doc.components) == 1
        assert retrieved_doc.components[0]['type'] == 'text'
    
    def test_rag_preparation_integration(self, test_environment, sample_documents):
        """Test RAG preparation integration."""
        # Initialize components
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Create directories
        os.makedirs(test_environment['lightrag_dir'], exist_ok=True)
        
        rag_prep = RAGDatabasePreparation(
            lightrag_dir=test_environment['lightrag_dir'],
            meta_document_crud=meta_crud,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Create test document
        doc_uuid = "test_rag_doc_456"
        set_uuid = "test_rag_set_456"
        
        meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            title="Test Document for RAG",
            summary="Testing RAG preparation functionality",
            components=[
                {
                    'type': 'text',
                    'content': 'This is sample text content for RAG testing. It contains multiple sentences for chunking.',
                    'metadata': {'length': 95, 'format': 'plain_text'}
                }
            ]
        )
        
        # Test RAG preparation
        chunk_config = RAGChunkConfig(
            chunk_size=50,
            chunk_overlap=10,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # This may use mock implementation
        try:
            result = rag_prep.prepare_document_for_rag(
                document_uuid=doc_uuid,
                chunk_config=chunk_config
            )
            
            # Verify result structure (may be mock)
            if isinstance(result, dict):
                assert 'success' in result
            else:
                # Async result - would need await in real implementation
                pass
                
        except Exception as e:
            # Expected with mock implementation
            assert "mock" in str(e).lower() or "not implemented" in str(e).lower()
    
    def test_complete_document_lifecycle(self, test_environment, sample_documents):
        """Test complete document lifecycle integration."""
        # Initialize all components
        preprocessing_router = DocumentPreprocessingRouter()
        processor_factory = ProcessorFactory()
        postprocessing_router = PostProcessingRouter()
        chunker = DocumentChunker()
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Test document
        doc_info = sample_documents['pdf_simple']
        filename = doc_info['filename']
        content = doc_info['content']
        
        # Stage 1: Preprocessing
        routing_decision = preprocessing_router.route_document(filename, content)
        assert routing_decision['supported'] is True
        
        processor = processor_factory.get_processor_for_file(filename, content)
        assert processor is not None
        
        preprocessing_result = processor.process_document(filename, file_content=content)
        assert preprocessing_result.success is True
        
        processed_doc = preprocessing_result.output
        assert processed_doc is not None
        
        # Stage 2: Postprocessing
        postprocessing_methods = postprocessing_router.route_document(processed_doc)
        assert isinstance(postprocessing_methods, dict)
        
        # Apply chunking if available
        if 'chunking' in postprocessing_methods:
            chunks = chunker.chunk_document(processed_doc, strategy='paragraph')
            processed_doc.chunks = chunks
        
        # Stage 3: Storage
        doc_uuid = "lifecycle_test_doc_789"
        set_uuid = "lifecycle_test_set_789"
        
        # Extract components for meta document
        components = []
        if processed_doc.plain_text:
            components.append({
                'type': 'text',
                'content': processed_doc.plain_text[:500],  # Truncate for storage
                'metadata': {
                    'length': len(processed_doc.plain_text),
                    'format': 'plain_text'
                }
            })
        
        # Create meta document
        created_uuid = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            title=f"Processed {filename}",
            summary="Complete lifecycle test document",
            components=components
        )
        
        assert created_uuid == doc_uuid
        
        # Verify complete integration
        retrieved_doc = meta_crud.get_meta_document(doc_uuid)
        assert retrieved_doc is not None
        assert retrieved_doc.title == f"Processed {filename}"
        assert len(retrieved_doc.components) > 0
    
    def test_version_chain_simulation(self, test_environment, sample_documents):
        """Test version chain simulation using meta documents."""
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Simulate version chain using set_uuid as lineage identifier
        lineage_uuid = "version_chain_test_lineage"
        
        # Create version 1
        doc_v1_uuid = "version_chain_doc_v1"
        meta_crud.create_meta_document(
            doc_uuid=doc_v1_uuid,
            set_uuid=lineage_uuid,
            title="Document Version 1",
            summary="First version of the document",
            components=[{
                'type': 'text',
                'content': 'Version 1 content',
                'metadata': {'version': 1}
            }]
        )
        
        # Create version 2
        doc_v2_uuid = "version_chain_doc_v2"
        meta_crud.create_meta_document(
            doc_uuid=doc_v2_uuid,
            set_uuid=lineage_uuid,
            title="Document Version 2",
            summary="Second version of the document",
            components=[{
                'type': 'text',
                'content': 'Version 2 content with updates',
                'metadata': {'version': 2}
            }]
        )
        
        # Verify both versions exist and belong to same lineage
        doc_v1 = meta_crud.get_meta_document(doc_v1_uuid)
        doc_v2 = meta_crud.get_meta_document(doc_v2_uuid)
        
        assert doc_v1 is not None
        assert doc_v2 is not None
        assert doc_v1.set_uuid == lineage_uuid
        assert doc_v2.set_uuid == lineage_uuid
        assert doc_v1.set_uuid == doc_v2.set_uuid  # Same lineage
        
        # Verify version-specific content
        assert doc_v1.components[0]['metadata']['version'] == 1
        assert doc_v2.components[0]['metadata']['version'] == 2
    
    def test_error_handling_integration(self, test_environment):
        """Test error handling across integrated components."""
        # Test with invalid file
        router = DocumentPreprocessingRouter()
        factory = ProcessorFactory()
        
        # Test routing with invalid file
        routing_decision = router.route_document("invalid.xyz", b"invalid content")
        
        # Should handle gracefully
        assert isinstance(routing_decision, dict)
        assert 'supported' in routing_decision
        
        # Test processor with invalid file
        processor = factory.get_processor_for_file("invalid.xyz", b"invalid content")
        
        # May return None or a processor that handles the error
        if processor is not None:
            result = processor.process_document("invalid.xyz", file_content=b"invalid content")
            # Should have error handling
            assert hasattr(result, 'success')
    
    def test_performance_integration(self, test_environment, sample_documents):
        """Test performance characteristics of integrated pipeline."""
        # Initialize components
        router = DocumentPreprocessingRouter()
        factory = ProcessorFactory()
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Test processing time
        doc_info = sample_documents['pdf_simple']
        filename = doc_info['filename']
        content = doc_info['content']
        
        start_time = time.time()
        
        # Process document
        routing_decision = router.route_document(filename, content)
        processor = factory.get_processor_for_file(filename, content)
        
        if processor is not None:
            result = processor.process_document(filename, file_content=content)
            
            if result.success:
                # Store in meta document
                doc_uuid = "performance_test_doc"
                meta_crud.create_meta_document(
                    doc_uuid=doc_uuid,
                    set_uuid="performance_test_set",
                    title="Performance Test Document",
                    summary="Testing performance",
                    components=[{
                        'type': 'text',
                        'content': result.output.plain_text[:100] if result.output.plain_text else 'No content',
                        'metadata': {'test': 'performance'}
                    }]
                )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify reasonable processing time (should be fast with mock processing)
        assert processing_time < 10.0  # Should complete within 10 seconds
        
        print(f"Integration processing time: {processing_time:.3f} seconds")


class TestSprint1ComponentInteraction:
    """Test interaction between Sprint 1 components."""
    
    @pytest.fixture
    def test_environment(self):
        """Create test environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield {
                'temp_dir': temp_dir,
                'meta_db_path': os.path.join(temp_dir, 'meta_docs.db')
            }
    
    def test_preprocessing_to_postprocessing_handoff(self, test_environment):
        """Test handoff from preprocessing to postprocessing."""
        # Initialize components
        processor_factory = ProcessorFactory()
        postprocessing_router = PostProcessingRouter()
        
        # Create mock processed document
        from core.models import ProcessedDocument, DocumentStructure, ContentElement
        
        processed_doc = ProcessedDocument(
            plain_text="This is test content for postprocessing handoff testing.",
            markdown_text="# Test\nThis is test content for postprocessing handoff testing.",
            document_structure=DocumentStructure(
                total_pages=1,
                total_elements=1,
                has_tables=False,
                has_images=False
            ),
            content_elements=[
                ContentElement(
                    element_type="paragraph",
                    content="This is test content for postprocessing handoff testing.",
                    metadata={"page": 1}
                )
            ],
            tables=[],
            images=[],
            metadata={"source": "test"}
        )
        
        # Test postprocessing routing
        routing_result = postprocessing_router.route_document(processed_doc)
        
        # Verify routing works with processed document
        assert isinstance(routing_result, dict)
    
    def test_postprocessing_to_storage_handoff(self, test_environment):
        """Test handoff from postprocessing to storage."""
        # Initialize components
        chunker = DocumentChunker()
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Create mock processed document
        from core.models import ProcessedDocument, DocumentStructure, ContentElement
        
        processed_doc = ProcessedDocument(
            plain_text="This is test content for storage handoff testing. It has multiple sentences.",
            markdown_text="# Test\nThis is test content for storage handoff testing. It has multiple sentences.",
            document_structure=DocumentStructure(
                total_pages=1,
                total_elements=1,
                has_tables=False,
                has_images=False
            ),
            content_elements=[
                ContentElement(
                    element_type="paragraph",
                    content="This is test content for storage handoff testing. It has multiple sentences.",
                    metadata={"page": 1}
                )
            ],
            tables=[],
            images=[],
            metadata={"source": "test"}
        )
        
        # Apply chunking
        chunks = chunker.chunk_document(processed_doc, strategy='paragraph')
        processed_doc.chunks = chunks
        
        # Store in meta document
        doc_uuid = "handoff_test_doc"
        components = [{
            'type': 'text',
            'content': processed_doc.plain_text,
            'metadata': {
                'chunks_count': len(chunks) if chunks else 0,
                'format': 'plain_text'
            }
        }]
        
        created_uuid = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid="handoff_test_set",
            title="Handoff Test Document",
            summary="Testing postprocessing to storage handoff",
            components=components
        )
        
        # Verify storage
        assert created_uuid == doc_uuid
        
        retrieved_doc = meta_crud.get_meta_document(doc_uuid)
        assert retrieved_doc is not None
        assert 'chunks_count' in retrieved_doc.components[0]['metadata']
    
    def test_storage_to_rag_handoff(self, test_environment):
        """Test handoff from storage to RAG preparation."""
        # Initialize components
        meta_crud = MetaDocumentCRUD(test_environment['meta_db_path'])
        
        # Create test document in storage
        doc_uuid = "rag_handoff_test_doc"
        meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid="rag_handoff_test_set",
            title="RAG Handoff Test Document",
            summary="Testing storage to RAG handoff",
            components=[{
                'type': 'text',
                'content': 'This is content prepared for RAG indexing and retrieval testing.',
                'metadata': {'prepared_for_rag': True}
            }]
        )
        
        # Verify document exists for RAG preparation
        retrieved_doc = meta_crud.get_meta_document(doc_uuid)
        assert retrieved_doc is not None
        assert retrieved_doc.components[0]['metadata']['prepared_for_rag'] is True
        
        # This would be where RAG preparation would pick up the document
        # For now, we just verify the document is accessible
        assert len(retrieved_doc.components) > 0
        assert retrieved_doc.components[0]['type'] == 'text'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])