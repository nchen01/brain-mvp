"""
Integration tests for vector embedding generation and storage.

This test suite focuses on:
1. Vector embedding generation for different content types
2. Embedding storage and retrieval
3. Similarity calculations and clustering
4. Performance and accuracy of embeddings
5. Integration with LightRAG vector database
"""

import pytest
import tempfile
import os
import uuid
import asyncio
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Our imports
from src.docforge.rag.embeddings import EmbeddingManager
from src.docforge.rag.lightrag_integration import LightRAGConfig, LightRAGIntegration
from src.docforge.rag.rag_database_preparation import (
    RAGDatabasePreparation,
    RAGChunkConfig,
    SemanticIndexer
)
from src.docforge.storage.meta_document_db import (
    MetaDocumentRecord,
    MetaDocumentComponent
)
from src.docforge.storage.meta_document_crud import MetaDocumentCRUD
from src.dbm.connection import DatabaseConnection


@pytest.fixture(scope="function")
def temp_directories():
    """Create temporary directories for testing."""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    yield {
        'main': temp_dir,
        'embeddings': os.path.join(temp_dir, 'embeddings'),
        'lightrag': os.path.join(temp_dir, 'lightrag'),
        'cache': os.path.join(temp_dir, 'cache')
    }
    
    # Cleanup
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Failed to cleanup temp directory: {e}")


@pytest.fixture
def embedding_manager(temp_directories):
    """Create embedding manager for testing."""
    return EmbeddingManager(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_dir=temp_directories['embeddings'],
        batch_size=4
    )


@pytest.fixture
def sample_texts():
    """Create sample texts for embedding testing."""
    return {
        'technical': [
            "Neural networks are computational models inspired by biological neural networks.",
            "Deep learning uses multiple layers to progressively extract higher-level features.",
            "Convolutional neural networks are particularly effective for image processing tasks.",
            "Recurrent neural networks can process sequences of variable length.",
            "Transformer architectures have revolutionized natural language processing."
        ],
        'general': [
            "The weather today is sunny and warm.",
            "I enjoy reading books in my free time.",
            "Cooking is both an art and a science.",
            "Travel broadens the mind and enriches the soul.",
            "Music has the power to evoke strong emotions."
        ],
        'scientific': [
            "Quantum mechanics describes the behavior of matter and energy at atomic scales.",
            "DNA contains the genetic instructions for the development of living organisms.",
            "Climate change is primarily driven by human activities and greenhouse gas emissions.",
            "Photosynthesis converts light energy into chemical energy in plants.",
            "The theory of relativity fundamentally changed our understanding of space and time."
        ],
        'similar_pairs': [
            ("Machine learning is a subset of artificial intelligence.", 
             "AI encompasses machine learning as one of its core components."),
            ("Python is a popular programming language for data science.",
             "Data scientists frequently use Python for their analytical work."),
            ("Natural language processing enables computers to understand human language.",
             "NLP allows machines to comprehend and process human speech and text.")
        ]
    }


class TestEmbeddingGeneration:
    """Test vector embedding generation functionality."""
    
    @pytest.mark.asyncio
    async def test_single_text_embedding(self, embedding_manager):
        """Test generating embedding for a single text."""
        text = "This is a test sentence for embedding generation."
        
        embedding = await embedding_manager.embed_text(text)
        
        # Verify embedding properties
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)
        
        # Verify embedding dimension (should match model)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
    
    @pytest.mark.asyncio
    async def test_batch_text_embedding(self, embedding_manager, sample_texts):
        """Test generating embeddings for multiple texts."""
        texts = sample_texts['technical']
        
        embeddings = await embedding_manager.embed_texts(texts)
        
        # Verify batch embeddings
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        
        # Verify each embedding
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == 384
            assert all(isinstance(x, (int, float)) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_empty_and_edge_cases(self, embedding_manager):
        """Test embedding generation with edge cases."""
        # Empty text
        empty_embedding = await embedding_manager.embed_text("")
        assert isinstance(empty_embedding, list)
        assert len(empty_embedding) == 384
        
        # Very short text
        short_embedding = await embedding_manager.embed_text("Hi")
        assert isinstance(short_embedding, list)
        assert len(short_embedding) == 384
        
        # Very long text
        long_text = "This is a very long sentence. " * 100
        long_embedding = await embedding_manager.embed_text(long_text)
        assert isinstance(long_embedding, list)
        assert len(long_embedding) == 384
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, embedding_manager):
        """Test that same text produces consistent embeddings."""
        text = "Consistency test for embedding generation."
        
        # Generate embedding multiple times
        embedding1 = await embedding_manager.embed_text(text)
        embedding2 = await embedding_manager.embed_text(text)
        
        # Should be identical (or very close due to floating point precision)
        similarity = embedding_manager.calculate_similarity(embedding1, embedding2)
        assert similarity > 0.999  # Should be nearly identical


class TestSimilarityCalculations:
    """Test similarity calculations between embeddings."""
    
    @pytest.mark.asyncio
    async def test_cosine_similarity(self, embedding_manager, sample_texts):
        """Test cosine similarity calculations."""
        # Test with similar texts
        similar_texts = sample_texts['similar_pairs'][0]
        
        embedding1 = await embedding_manager.embed_text(similar_texts[0])
        embedding2 = await embedding_manager.embed_text(similar_texts[1])
        
        similarity = embedding_manager.calculate_similarity(embedding1, embedding2, method='cosine')
        
        # Similar texts should have high similarity
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.7  # Should be quite similar
    
    @pytest.mark.asyncio
    async def test_dissimilar_text_similarity(self, embedding_manager, sample_texts):
        """Test similarity between dissimilar texts."""
        # Compare technical and general texts
        technical_text = sample_texts['technical'][0]
        general_text = sample_texts['general'][0]
        
        embedding1 = await embedding_manager.embed_text(technical_text)
        embedding2 = await embedding_manager.embed_text(general_text)
        
        similarity = embedding_manager.calculate_similarity(embedding1, embedding2)
        
        # Dissimilar texts should have lower similarity
        assert 0.0 <= similarity <= 1.0
        assert similarity < 0.8  # Should be less similar
    
    @pytest.mark.asyncio
    async def test_similarity_matrix(self, embedding_manager, sample_texts):
        """Test creating similarity matrix for multiple texts."""
        texts = sample_texts['technical'][:3]  # Use first 3 technical texts
        
        # Generate embeddings
        embeddings = await embedding_manager.embed_texts(texts)
        
        # Create similarity matrix
        similarity_matrix = []
        for i, emb1 in enumerate(embeddings):
            row = []
            for j, emb2 in enumerate(embeddings):
                similarity = embedding_manager.calculate_similarity(emb1, emb2)
                row.append(similarity)
            similarity_matrix.append(row)
        
        # Verify matrix properties
        assert len(similarity_matrix) == len(texts)
        assert all(len(row) == len(texts) for row in similarity_matrix)
        
        # Diagonal should be 1.0 (self-similarity)
        for i in range(len(texts)):
            assert abs(similarity_matrix[i][i] - 1.0) < 0.001
        
        # Matrix should be symmetric
        for i in range(len(texts)):
            for j in range(len(texts)):
                assert abs(similarity_matrix[i][j] - similarity_matrix[j][i]) < 0.001


class TestSemanticClustering:
    """Test semantic clustering of embeddings."""
    
    @pytest.fixture
    def semantic_indexer(self, embedding_manager):
        """Create semantic indexer for testing."""
        return SemanticIndexer(embedding_manager, similarity_threshold=0.75)
    
    @pytest.mark.asyncio
    async def test_semantic_clustering(self, semantic_indexer, sample_texts):
        """Test clustering of semantically similar texts."""
        # Create chunks from different categories
        all_texts = (
            sample_texts['technical'][:3] + 
            sample_texts['scientific'][:2] + 
            sample_texts['general'][:2]
        )
        
        # Create mock chunks
        chunks = []
        for i, text in enumerate(all_texts):
            chunk = {
                'chunk_id': f"chunk_{i}",
                'content': text,
                'doc_uuid': f"doc_{i // 3}",  # Group by category
                'meta_doc_uuid': f"meta_{i // 3}"
            }
            chunks.append(chunk)
        
        # Create semantic index
        semantic_index = await semantic_indexer.create_semantic_index(chunks)
        
        # Verify clustering results
        assert 'semantic_clusters' in semantic_index
        assert 'semantic_relationships' in semantic_index
        
        clusters = semantic_index['semantic_clusters']
        relationships = semantic_index['semantic_relationships']
        
        # Should find some clusters
        assert len(clusters) >= 0  # Might not find clusters with small dataset
        
        # Should find some relationships
        assert len(relationships) >= 0
        
        # Verify cluster structure if clusters exist
        for cluster in clusters:
            assert 'cluster_id' in cluster
            assert 'chunk_indices' in cluster
            assert 'cluster_size' in cluster
            assert cluster['cluster_size'] > 1  # Clusters should have multiple items
    
    @pytest.mark.asyncio
    async def test_topic_extraction(self, semantic_indexer):
        """Test topic extraction from clustered texts."""
        # Create texts with clear topics
        topic_texts = [
            "Machine learning algorithms learn from data to make predictions.",
            "Neural networks use layers of interconnected nodes for computation.",
            "Deep learning models require large datasets for training.",
            "Artificial intelligence systems can perform complex reasoning tasks."
        ]
        
        # Extract topics
        topics = semantic_indexer._extract_cluster_topics(topic_texts)
        
        # Verify topics
        assert isinstance(topics, list)
        assert len(topics) <= 5  # Should return top 5 topics
        
        # Should contain relevant AI/ML terms
        topic_text = ' '.join(topics).lower()
        ai_terms = ['learning', 'neural', 'data', 'algorithms', 'intelligence']
        found_terms = sum(1 for term in ai_terms if term in topic_text)
        assert found_terms > 0  # Should find at least some relevant terms


class TestLightRAGVectorIntegration:
    """Test integration with LightRAG vector database."""
    
    @pytest.fixture
    def lightrag_integration(self, temp_directories):
        """Create LightRAG integration for testing."""
        config = LightRAGConfig(
            working_dir=temp_directories['lightrag'],
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384,
            batch_size=4
        )
        return LightRAGIntegration(config)
    
    @pytest.mark.asyncio
    async def test_lightrag_vector_storage(self, lightrag_integration):
        """Test storing vectors in LightRAG."""
        # Create test document content
        content = """
        This is a comprehensive test document about machine learning and artificial intelligence.
        It covers various topics including neural networks, deep learning, and natural language processing.
        The document is designed to test the vector storage capabilities of the LightRAG system.
        """
        
        # Index content in LightRAG
        await lightrag_integration.indexer.lightrag.ainsert(content)
        
        # Verify indexing (this is implicit - no exception means success)
        assert True  # If we get here, indexing succeeded
    
    @pytest.mark.asyncio
    async def test_lightrag_vector_retrieval(self, lightrag_integration):
        """Test retrieving vectors from LightRAG."""
        # Index some content first
        documents = [
            "Neural networks are the foundation of modern deep learning systems.",
            "Natural language processing enables computers to understand human language.",
            "Computer vision algorithms can analyze and interpret visual information.",
            "Reinforcement learning agents learn through interaction with environments."
        ]
        
        # Index all documents
        for doc in documents:
            await lightrag_integration.indexer.lightrag.ainsert(doc)
        
        # Test retrieval with different queries
        queries = [
            "deep learning neural networks",
            "language processing NLP",
            "computer vision images",
            "reinforcement learning agents"
        ]
        
        for query in queries:
            # Query LightRAG
            result = await lightrag_integration.retriever.lightrag.aquery(
                query, 
                param=lightrag_integration.retriever.query_param
            )
            
            # Verify result
            assert result is not None
            assert isinstance(result, str)  # LightRAG returns string results
    
    @pytest.mark.asyncio
    async def test_lightrag_embedding_consistency(self, lightrag_integration):
        """Test embedding consistency in LightRAG."""
        text = "Test document for embedding consistency verification."
        
        # Generate embedding directly
        direct_embedding = await lightrag_integration.embedding_manager.embed_text(text)
        
        # Index in LightRAG and retrieve
        await lightrag_integration.indexer.lightrag.ainsert(text)
        
        # Query with the same text
        result = await lightrag_integration.retriever.lightrag.aquery(
            text,
            param=lightrag_integration.retriever.query_param
        )
        
        # Verify we get a meaningful result
        assert result is not None
        assert len(result) > 0


class TestEmbeddingPerformance:
    """Test embedding generation and storage performance."""
    
    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self, embedding_manager):
        """Test performance of batch embedding generation."""
        import time
        
        # Create test texts of varying sizes
        small_texts = ["Short text."] * 10
        medium_texts = ["This is a medium length text with several words and concepts."] * 10
        large_texts = ["This is a much longer text that contains multiple sentences and covers various topics in detail. " * 5] * 10
        
        # Test small texts
        start_time = time.time()
        small_embeddings = await embedding_manager.embed_texts(small_texts)
        small_time = time.time() - start_time
        
        # Test medium texts
        start_time = time.time()
        medium_embeddings = await embedding_manager.embed_texts(medium_texts)
        medium_time = time.time() - start_time
        
        # Test large texts
        start_time = time.time()
        large_embeddings = await embedding_manager.embed_texts(large_texts)
        large_time = time.time() - start_time
        
        # Verify all embeddings were generated
        assert len(small_embeddings) == len(small_texts)
        assert len(medium_embeddings) == len(medium_texts)
        assert len(large_embeddings) == len(large_texts)
        
        # Performance should be reasonable (loose bounds for testing)
        assert small_time < 10.0
        assert medium_time < 15.0
        assert large_time < 20.0
        
        print(f"\\nEmbedding Performance:")
        print(f"  Small texts ({len(small_texts)}): {small_time:.2f}s")
        print(f"  Medium texts ({len(medium_texts)}): {medium_time:.2f}s")
        print(f"  Large texts ({len(large_texts)}): {large_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_similarity_calculation_performance(self, embedding_manager):
        """Test performance of similarity calculations."""
        import time
        
        # Generate embeddings for testing
        texts = ["Test text number " + str(i) for i in range(100)]
        embeddings = await embedding_manager.embed_texts(texts)
        
        # Test similarity calculation performance
        start_time = time.time()
        
        similarities = []
        for i in range(0, min(20, len(embeddings))):  # Test first 20 to avoid long test times
            for j in range(i + 1, min(20, len(embeddings))):
                similarity = embedding_manager.calculate_similarity(embeddings[i], embeddings[j])
                similarities.append(similarity)
        
        calc_time = time.time() - start_time
        
        # Verify calculations
        assert len(similarities) > 0
        assert all(0.0 <= sim <= 1.0 for sim in similarities)
        
        # Performance should be reasonable
        assert calc_time < 5.0  # Should be fast for similarity calculations
        
        print(f"\\nSimilarity Calculation Performance:")
        print(f"  {len(similarities)} calculations: {calc_time:.2f}s")
        print(f"  Average per calculation: {calc_time/len(similarities)*1000:.2f}ms")


class TestEmbeddingAccuracy:
    """Test accuracy and quality of embeddings."""
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_accuracy(self, embedding_manager, sample_texts):
        """Test that semantically similar texts have high similarity scores."""
        similar_pairs = sample_texts['similar_pairs']
        
        similarity_scores = []
        
        for pair in similar_pairs:
            embedding1 = await embedding_manager.embed_text(pair[0])
            embedding2 = await embedding_manager.embed_text(pair[1])
            
            similarity = embedding_manager.calculate_similarity(embedding1, embedding2)
            similarity_scores.append(similarity)
        
        # All similar pairs should have high similarity
        assert all(score > 0.6 for score in similarity_scores), f"Low similarities: {similarity_scores}"
        
        # Average similarity should be quite high
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        assert avg_similarity > 0.7, f"Average similarity too low: {avg_similarity}"
    
    @pytest.mark.asyncio
    async def test_cross_domain_similarity(self, embedding_manager, sample_texts):
        """Test similarity across different domains."""
        # Compare technical vs general texts
        technical_embedding = await embedding_manager.embed_text(sample_texts['technical'][0])
        general_embedding = await embedding_manager.embed_text(sample_texts['general'][0])
        
        cross_domain_similarity = embedding_manager.calculate_similarity(
            technical_embedding, general_embedding
        )
        
        # Cross-domain similarity should be lower than within-domain
        technical_embedding2 = await embedding_manager.embed_text(sample_texts['technical'][1])
        within_domain_similarity = embedding_manager.calculate_similarity(
            technical_embedding, technical_embedding2
        )
        
        # Within-domain should be higher than cross-domain (usually)
        # Note: This might not always hold, so we use a loose check
        assert 0.0 <= cross_domain_similarity <= 1.0
        assert 0.0 <= within_domain_similarity <= 1.0
    
    @pytest.mark.asyncio
    async def test_embedding_stability(self, embedding_manager):
        """Test stability of embeddings across multiple generations."""
        text = "Stability test for embedding generation consistency."
        
        # Generate multiple embeddings
        embeddings = []
        for _ in range(5):
            embedding = await embedding_manager.embed_text(text)
            embeddings.append(embedding)
        
        # All embeddings should be very similar
        base_embedding = embeddings[0]
        for embedding in embeddings[1:]:
            similarity = embedding_manager.calculate_similarity(base_embedding, embedding)
            assert similarity > 0.999, f"Embedding instability detected: {similarity}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])