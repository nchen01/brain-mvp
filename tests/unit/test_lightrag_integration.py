"""Tests for LightRAG integration."""

import pytest
import tempfile
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from src.docforge.rag.lightrag_integration import (
    LightRAGConfig,
    LightRAGIntegration,
    DocumentIndexer,
    VectorRetriever
)
from src.docforge.storage.meta_document_db import (
    MetaDocumentRecord,
    MetaDocumentComponent
)


@pytest.fixture
def temp_working_dir():
    """Create a temporary working directory for LightRAG."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def lightrag_config(temp_working_dir):
    """Create LightRAG configuration for testing."""
    return LightRAGConfig(
        working_dir=temp_working_dir,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        chunk_token_size=500,  # Smaller for testing
        batch_size=2  # Smaller for testing
    )


@pytest.fixture
def sample_meta_document():
    """Create a sample meta document for testing."""
    components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="This is a test document about artificial intelligence and machine learning.",
            metadata={"page": 1, "section": "introduction"},
            order_index=0,
            confidence_score=0.95
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="Machine learning algorithms can process large amounts of data efficiently.",
            metadata={"page": 2, "section": "methods"},
            order_index=1,
            confidence_score=0.88
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document provides an overview of AI and ML techniques.",
            metadata={"type": "abstract"},
            order_index=2,
            confidence_score=0.92
        )
    ]
    
    return MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="Introduction to AI and Machine Learning",
        summary="A comprehensive guide to artificial intelligence and machine learning concepts.",
        components=components,
        processing_history=[
            {
                "stage": "preprocessing",
                "processor": "test_processor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed"
            }
        ]
    )


class TestLightRAGConfig:
    """Test LightRAG configuration."""
    
    def test_config_creation(self, temp_working_dir):
        """Test creating LightRAG configuration."""
        config = LightRAGConfig(
            working_dir=temp_working_dir,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        
        assert config.working_dir == temp_working_dir
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding_dim == 384
        assert config.chunk_token_size == 1200  # default
        assert config.top_k == 10  # default


class TestDocumentIndexer:
    """Test document indexing functionality."""
    
    def test_indexer_initialization(self, lightrag_config):
        """Test that document indexer initializes correctly."""
        indexer = DocumentIndexer(lightrag_config)
        
        assert indexer.config == lightrag_config
        assert indexer.embedding_model is not None
        assert indexer.lightrag is not None
    
    def test_convert_meta_doc_to_text(self, lightrag_config, sample_meta_document):
        """Test converting meta document to text."""
        indexer = DocumentIndexer(lightrag_config)
        
        text = indexer._convert_meta_doc_to_text(sample_meta_document)
        
        assert "Title: Introduction to AI and Machine Learning" in text
        assert "Summary: A comprehensive guide" in text
        assert "CHUNK: This is a test document" in text
        assert "CHUNK: Machine learning algorithms" in text
        assert "SUMMARY: This document provides" in text
    
    @pytest.mark.asyncio
    async def test_index_meta_document(self, lightrag_config, sample_meta_document):
        """Test indexing a meta document."""
        indexer = DocumentIndexer(lightrag_config)
        
        result = await indexer.index_meta_document(sample_meta_document)
        
        assert result['meta_doc_uuid'] == sample_meta_document.meta_doc_uuid
        assert result['status'] == 'completed'
        assert result['indexed_components'] == len(sample_meta_document.components)
        assert 'indexed_at' in result


class TestVectorRetriever:
    """Test document retrieval functionality."""
    
    def test_retriever_initialization(self, lightrag_config):
        """Test that vector retriever initializes correctly."""
        retriever = VectorRetriever(lightrag_config)
        
        assert retriever.config == lightrag_config
        assert retriever.embedding_model is not None
        assert retriever.lightrag is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_documents_empty_index(self, lightrag_config):
        """Test retrieving documents from empty index."""
        retriever = VectorRetriever(lightrag_config)
        
        results = await retriever.retrieve_documents("artificial intelligence")
        
        # Should return empty or minimal results for empty index
        assert isinstance(results, list)


class TestLightRAGIntegration:
    """Test the main LightRAG integration class."""
    
    def test_integration_initialization(self, lightrag_config):
        """Test that LightRAG integration initializes correctly."""
        integration = LightRAGIntegration(lightrag_config)
        
        assert integration.config == lightrag_config
        assert integration.indexer is not None
        assert integration.retriever is not None
        assert integration.meta_doc_crud is not None
    
    def test_setup_working_directory(self, lightrag_config):
        """Test that working directory is set up correctly."""
        integration = LightRAGIntegration(lightrag_config)
        
        working_dir = Path(lightrag_config.working_dir)
        assert working_dir.exists()
        assert working_dir.is_dir()
    
    def test_get_rag_statistics(self, lightrag_config):
        """Test getting RAG statistics."""
        integration = LightRAGIntegration(lightrag_config)
        
        stats = integration.get_rag_statistics()
        
        assert 'total_meta_documents' in stats
        assert 'rag_ready_documents' in stats
        assert 'pending_rag_documents' in stats
        assert 'vector_db_path' in stats
        assert 'embedding_model' in stats
        assert stats['embedding_model'] == lightrag_config.embedding_model


class TestIntegrationWorkflow:
    """Test the complete integration workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, lightrag_config, sample_meta_document):
        """Test complete indexing and retrieval workflow."""
        integration = LightRAGIntegration(lightrag_config)
        
        # Note: This test would require a mock MetaDocumentCRUD
        # For now, we'll test the basic functionality
        
        # Test that we can create the integration
        assert integration is not None
        
        # Test indexing (would need mock data)
        indexer = integration.indexer
        result = await indexer.index_meta_document(sample_meta_document)
        assert result['status'] == 'completed'
        
        # Test retrieval
        retriever = integration.retriever
        results = await retriever.retrieve_documents("artificial intelligence")
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__])