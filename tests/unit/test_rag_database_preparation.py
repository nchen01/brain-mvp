"""Tests for RAG database preparation system."""

import pytest
import tempfile
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from src.docforge.rag.rag_database_preparation import (
    RAGDatabasePreparation,
    RAGChunkConfig,
    RAGOptimizedChunker,
    SemanticIndexer,
    DocumentRelationshipMapper,
    KnowledgeGraphBuilder,
    DocumentRelationship,
    KnowledgeGraphNode,
    KnowledgeGraphEdge
)
from src.docforge.rag.lightrag_integration import LightRAGConfig, LightRAGIntegration
from src.docforge.rag.embeddings import EmbeddingManager
from src.docforge.storage.meta_document_db import (
    MetaDocumentRecord,
    MetaDocumentComponent
)


@pytest.fixture
def temp_working_dir():
    """Create a temporary working directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def rag_chunk_config():
    """Create RAG chunk configuration for testing."""
    return RAGChunkConfig(
        chunk_size=256,  # Smaller for testing
        chunk_overlap=32,
        min_chunk_size=50,
        max_chunk_size=512,
        semantic_similarity_threshold=0.7
    )


@pytest.fixture
def lightrag_config(temp_working_dir):
    """Create LightRAG configuration for testing."""
    return LightRAGConfig(
        working_dir=temp_working_dir,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        batch_size=2  # Smaller for testing
    )


@pytest.fixture
def sample_meta_documents():
    """Create sample meta documents for testing."""
    doc1_components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="Artificial intelligence is a rapidly growing field that focuses on creating intelligent machines. These machines can perform tasks that typically require human intelligence, such as learning, reasoning, and problem-solving.",
            metadata={"page": 1, "section": "introduction"},
            order_index=0,
            confidence_score=0.95
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data and make predictions.",
            metadata={"page": 2, "section": "machine_learning"},
            order_index=1,
            confidence_score=0.88
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document provides an introduction to artificial intelligence and machine learning concepts.",
            metadata={"type": "abstract"},
            order_index=2,
            confidence_score=0.92
        )
    ]
    
    doc2_components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="Deep learning is a specialized branch of machine learning that uses neural networks with multiple layers. These networks can automatically learn complex patterns from large amounts of data.",
            metadata={"page": 1, "section": "deep_learning"},
            order_index=0,
            confidence_score=0.90
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document explores deep learning techniques and neural network architectures.",
            metadata={"type": "abstract"},
            order_index=1,
            confidence_score=0.85
        )
    ]
    
    doc1 = MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="Introduction to Artificial Intelligence",
        summary="A comprehensive guide to AI and ML fundamentals.",
        components=doc1_components,
        processing_history=[]
    )
    
    doc2 = MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="Deep Learning Fundamentals",
        summary="An exploration of deep learning and neural networks.",
        components=doc2_components,
        processing_history=[]
    )
    
    return [doc1, doc2]


class TestRAGChunkConfig:
    """Test RAG chunk configuration."""
    
    def test_config_creation(self):
        """Test creating RAG chunk configuration."""
        config = RAGChunkConfig(
            chunk_size=512,
            chunk_overlap=64,
            semantic_similarity_threshold=0.8
        )
        
        assert config.chunk_size == 512
        assert config.chunk_overlap == 64
        assert config.semantic_similarity_threshold == 0.8
        assert config.preserve_sentences is True  # default


class TestRAGOptimizedChunker:
    """Test RAG-optimized chunking functionality."""
    
    def test_chunker_initialization(self, rag_chunk_config):
        """Test chunker initialization."""
        chunker = RAGOptimizedChunker(rag_chunk_config)
        assert chunker.config == rag_chunk_config
    
    def test_chunk_meta_document(self, rag_chunk_config, sample_meta_documents):
        """Test chunking a meta document."""
        chunker = RAGOptimizedChunker(rag_chunk_config)
        doc = sample_meta_documents[0]
        
        chunks = chunker.chunk_meta_document(doc)
        
        assert len(chunks) > 0
        assert all('chunk_id' in chunk for chunk in chunks)
        assert all('content' in chunk for chunk in chunks)
        assert all('meta_doc_uuid' in chunk for chunk in chunks)
        assert all(chunk['meta_doc_uuid'] == doc.meta_doc_uuid for chunk in chunks)
    
    def test_chunk_text_small(self, rag_chunk_config):
        """Test chunking small text that doesn't need splitting."""
        chunker = RAGOptimizedChunker(rag_chunk_config)
        
        small_text = "This is a small text that fits in one chunk."
        chunks = chunker._chunk_text(small_text)
        
        assert len(chunks) == 1
        assert chunks[0] == small_text
    
    def test_chunk_text_large(self, rag_chunk_config):
        """Test chunking large text that needs splitting."""
        chunker = RAGOptimizedChunker(rag_chunk_config)
        
        # Create text larger than chunk_size
        large_text = "This is a sentence. " * 50  # Should exceed 256 chars
        chunks = chunker._chunk_text(large_text)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= rag_chunk_config.max_chunk_size for chunk in chunks)
        assert all(len(chunk) >= rag_chunk_config.min_chunk_size for chunk in chunks)


class TestSemanticIndexer:
    """Test semantic indexing functionality."""
    
    @pytest.fixture
    def embedding_manager(self):
        """Create embedding manager for testing."""
        return EmbeddingManager(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=2
        )
    
    def test_semantic_indexer_initialization(self, embedding_manager):
        """Test semantic indexer initialization."""
        indexer = SemanticIndexer(embedding_manager, similarity_threshold=0.8)
        assert indexer.embedding_manager == embedding_manager
        assert indexer.similarity_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_create_semantic_index(self, embedding_manager, rag_chunk_config, sample_meta_documents):
        """Test creating semantic index."""
        indexer = SemanticIndexer(embedding_manager, similarity_threshold=0.7)
        chunker = RAGOptimizedChunker(rag_chunk_config)
        
        # Create chunks from sample document
        chunks = chunker.chunk_meta_document(sample_meta_documents[0])
        
        # Create semantic index
        semantic_index = await indexer.create_semantic_index(chunks)
        
        assert 'indexed_chunks' in semantic_index
        assert 'semantic_clusters' in semantic_index
        assert 'semantic_relationships' in semantic_index
        assert semantic_index['total_chunks'] == len(chunks)
        assert all('embedding' in chunk for chunk in semantic_index['indexed_chunks'])


class TestDocumentRelationshipMapper:
    """Test document relationship mapping."""
    
    @pytest.fixture
    def embedding_manager(self):
        """Create embedding manager for testing."""
        return EmbeddingManager(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=2
        )
    
    def test_relationship_mapper_initialization(self, embedding_manager):
        """Test relationship mapper initialization."""
        mapper = DocumentRelationshipMapper(embedding_manager)
        assert mapper.embedding_manager == embedding_manager
    
    @pytest.mark.asyncio
    async def test_map_document_relationships(self, embedding_manager, sample_meta_documents):
        """Test mapping relationships between documents."""
        mapper = DocumentRelationshipMapper(embedding_manager)
        
        relationships = await mapper.map_document_relationships(sample_meta_documents)
        
        assert isinstance(relationships, list)
        # Should have at least one relationship between the two similar AI documents
        assert len(relationships) >= 1
        
        for rel in relationships:
            assert isinstance(rel, DocumentRelationship)
            assert rel.source_doc_uuid in [doc.meta_doc_uuid for doc in sample_meta_documents]
            assert rel.target_doc_uuid in [doc.meta_doc_uuid for doc in sample_meta_documents]
            assert 0.0 <= rel.strength <= 1.0


class TestKnowledgeGraphBuilder:
    """Test knowledge graph building."""
    
    @pytest.fixture
    def lightrag_integration(self, lightrag_config):
        """Create LightRAG integration for testing."""
        return LightRAGIntegration(lightrag_config)
    
    @pytest.fixture
    def embedding_manager(self):
        """Create embedding manager for testing."""
        return EmbeddingManager(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=2
        )
    
    def test_knowledge_graph_builder_initialization(self, lightrag_integration, embedding_manager):
        """Test knowledge graph builder initialization."""
        builder = KnowledgeGraphBuilder(lightrag_integration, embedding_manager)
        assert builder.lightrag_integration == lightrag_integration
        assert builder.embedding_manager == embedding_manager
    
    @pytest.mark.asyncio
    async def test_create_graph_nodes(self, lightrag_integration, embedding_manager, sample_meta_documents):
        """Test creating graph nodes."""
        builder = KnowledgeGraphBuilder(lightrag_integration, embedding_manager)
        
        nodes = await builder._create_graph_nodes(sample_meta_documents)
        
        assert len(nodes) > 0
        
        # Should have document nodes and component nodes
        doc_nodes = [node for node in nodes if node.node_type == "document"]
        comp_nodes = [node for node in nodes if node.node_type == "component"]
        
        assert len(doc_nodes) == len(sample_meta_documents)
        assert len(comp_nodes) > 0
        
        # All nodes should have embeddings
        assert all(node.embeddings is not None for node in nodes)


class TestRAGDatabasePreparation:
    """Test the main RAG database preparation class."""
    
    @pytest.fixture
    def lightrag_integration(self, lightrag_config):
        """Create LightRAG integration for testing."""
        return LightRAGIntegration(lightrag_config)
    
    def test_rag_preparation_initialization(self, lightrag_integration, rag_chunk_config):
        """Test RAG database preparation initialization."""
        prep = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=rag_chunk_config
        )
        
        assert prep.lightrag_integration == lightrag_integration
        assert prep.chunk_config == rag_chunk_config
        assert prep.chunker is not None
        assert prep.semantic_indexer is not None
        assert prep.relationship_mapper is not None
        assert prep.knowledge_graph_builder is not None
    
    def test_get_preparation_statistics(self, lightrag_integration, rag_chunk_config):
        """Test getting preparation statistics."""
        prep = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=rag_chunk_config
        )
        
        stats = prep.get_preparation_statistics()
        
        assert 'meta_document_stats' in stats
        assert 'lightrag_stats' in stats
        assert 'chunk_config' in stats
        assert stats['chunk_config']['chunk_size'] == rag_chunk_config.chunk_size


class TestDataStructures:
    """Test data structure classes."""
    
    def test_document_relationship_creation(self):
        """Test creating document relationship."""
        rel = DocumentRelationship(
            source_doc_uuid="doc1",
            target_doc_uuid="doc2",
            relationship_type="similar",
            strength=0.85,
            metadata={"test": "data"}
        )
        
        assert rel.source_doc_uuid == "doc1"
        assert rel.target_doc_uuid == "doc2"
        assert rel.relationship_type == "similar"
        assert rel.strength == 0.85
        assert rel.metadata["test"] == "data"
        assert isinstance(rel.created_at, datetime)
    
    def test_knowledge_graph_node_creation(self):
        """Test creating knowledge graph node."""
        node = KnowledgeGraphNode(
            node_id="node1",
            node_type="document",
            content="Test content",
            metadata={"title": "Test Document"}
        )
        
        assert node.node_id == "node1"
        assert node.node_type == "document"
        assert node.content == "Test content"
        assert node.metadata["title"] == "Test Document"
        assert node.embeddings is None  # Not set by default
    
    def test_knowledge_graph_edge_creation(self):
        """Test creating knowledge graph edge."""
        edge = KnowledgeGraphEdge(
            source_node_id="node1",
            target_node_id="node2",
            edge_type="contains",
            weight=1.0,
            metadata={"relationship": "parent-child"}
        )
        
        assert edge.source_node_id == "node1"
        assert edge.target_node_id == "node2"
        assert edge.edge_type == "contains"
        assert edge.weight == 1.0
        assert edge.metadata["relationship"] == "parent-child"


if __name__ == "__main__":
    pytest.main([__file__])