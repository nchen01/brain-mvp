#!/usr/bin/env python3
"""
RAG Integration Demo

This script demonstrates the RAG integration testing capabilities
by running a subset of tests and showing the results.

Usage:
    python examples/run_rag_integration_demo.py
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules directly for demonstration
from tests.integration.test_meta_document_rag_integration import (
    TestMetaDocumentStorage,
    TestRAGDatabasePreparation,
    TestLightRAGIntegration
)
from tests.integration.test_vector_embedding_integration import (
    TestEmbeddingGeneration,
    TestSimilarityCalculations
)


async def run_demo_tests():
    """Run a subset of integration tests for demonstration."""
    print("RAG Integration Demo")
    print("=" * 50)
    print("This demo shows key RAG integration capabilities:")
    print("1. Meta document storage and retrieval")
    print("2. RAG database preparation")
    print("3. Vector embedding generation")
    print("4. Similarity calculations")
    print("5. LightRAG integration")
    print()
    
    try:
        # Import required fixtures and setup
        import tempfile
        import uuid
        from datetime import datetime, timezone
        
        from src.docforge.storage.meta_document_db import (
            MetaDocumentRecord,
            MetaDocumentComponent
        )
        from src.docforge.storage.meta_document_crud import MetaDocumentCRUD
        from src.docforge.rag.embeddings import EmbeddingManager
        from src.docforge.rag.lightrag_integration import LightRAGConfig, LightRAGIntegration
        from src.docforge.rag.rag_database_preparation import RAGDatabasePreparation, RAGChunkConfig
        from src.dbm.connection import DummyDBConnection
        
        # Setup test environment
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'demo.db')
        
        print(f"Setting up test environment in: {temp_dir}")
        
        # Initialize database
        db_connection = DummyDBConnection(db_path)
        
        # Create sample document
        sample_doc = MetaDocumentRecord(
            meta_doc_uuid=str(uuid.uuid4()),
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Demo: AI and Machine Learning Overview",
            summary="A demonstration document covering AI and ML concepts for testing purposes.",
            components=[
                MetaDocumentComponent(
                    component_id=str(uuid.uuid4()),
                    component_type="chunk",
                    content="""
                    Artificial Intelligence (AI) represents a transformative technology that enables 
                    machines to perform tasks requiring human-like intelligence. Machine Learning (ML), 
                    a subset of AI, allows systems to learn and improve from experience without explicit 
                    programming. Deep learning, using neural networks with multiple layers, has 
                    revolutionized fields like computer vision and natural language processing.
                    """.strip(),
                    metadata={"section": "introduction", "page": 1},
                    order_index=0,
                    confidence_score=0.95
                ),
                MetaDocumentComponent(
                    component_id=str(uuid.uuid4()),
                    component_type="chunk",
                    content="""
                    Neural networks are computational models inspired by biological neural networks. 
                    They consist of interconnected nodes (neurons) organized in layers that process 
                    information. Convolutional Neural Networks (CNNs) excel at image processing, 
                    while Recurrent Neural Networks (RNNs) are designed for sequential data like 
                    text and time series.
                    """.strip(),
                    metadata={"section": "neural_networks", "page": 2},
                    order_index=1,
                    confidence_score=0.92
                ),
                MetaDocumentComponent(
                    component_id=str(uuid.uuid4()),
                    component_type="summary",
                    content="This document provides an overview of AI, ML, and neural network technologies.",
                    metadata={"type": "generated_summary"},
                    order_index=2,
                    confidence_score=0.88
                )
            ],
            processing_history=[
                {
                    "step_name": "demo_creation",
                    "processor_name": "demo_processor",
                    "status": "completed",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"demo": True}
                }
            ]
        )
        
        # Test 1: Meta Document Storage
        print("\\n1. Testing Meta Document Storage...")
        meta_doc_crud = MetaDocumentCRUD(db_connection)
        
        # Store document
        result = meta_doc_crud.create_meta_document(sample_doc)
        print(f"   ✓ Document stored successfully: {result is not None}")
        
        # Retrieve document
        retrieved_doc = meta_doc_crud.get_meta_document(sample_doc.meta_doc_uuid)
        print(f"   ✓ Document retrieved successfully: {retrieved_doc is not None}")
        print(f"   ✓ Title matches: {retrieved_doc.title == sample_doc.title}")
        print(f"   ✓ Components count: {len(retrieved_doc.components)} components")
        
        # Test 2: Vector Embedding Generation
        print("\\n2. Testing Vector Embedding Generation...")
        embedding_manager = EmbeddingManager(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=2
        )
        
        # Generate embeddings for document components
        test_texts = [comp.content for comp in sample_doc.components if comp.component_type == "chunk"]
        embeddings = await embedding_manager.embed_texts(test_texts)
        
        print(f"   ✓ Generated embeddings for {len(test_texts)} text chunks")
        print(f"   ✓ Embedding dimension: {len(embeddings[0]) if embeddings else 0}")
        print(f"   ✓ All embeddings valid: {all(isinstance(emb, list) and len(emb) > 0 for emb in embeddings)}")
        
        # Test 3: Similarity Calculations
        print("\\n3. Testing Similarity Calculations...")
        if len(embeddings) >= 2:
            similarity = embedding_manager.calculate_similarity(embeddings[0], embeddings[1])
            print(f"   ✓ Similarity between chunks: {similarity:.3f}")
            print(f"   ✓ Similarity in valid range: {0.0 <= similarity <= 1.0}")
        
        # Test same text similarity
        same_text_emb1 = await embedding_manager.embed_text("Test text for consistency")
        same_text_emb2 = await embedding_manager.embed_text("Test text for consistency")
        same_similarity = embedding_manager.calculate_similarity(same_text_emb1, same_text_emb2)
        print(f"   ✓ Same text similarity: {same_similarity:.3f} (should be ~1.0)")
        
        # Test 4: RAG Database Preparation
        print("\\n4. Testing RAG Database Preparation...")
        
        lightrag_config = LightRAGConfig(
            working_dir=os.path.join(temp_dir, 'lightrag'),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384,
            batch_size=2
        )
        
        rag_chunk_config = RAGChunkConfig(
            chunk_size=300,
            chunk_overlap=50,
            semantic_similarity_threshold=0.7
        )
        
        lightrag_integration = LightRAGIntegration(lightrag_config, meta_doc_crud)
        rag_preparation = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=rag_chunk_config
        )
        
        # Prepare document for RAG
        rag_result = await rag_preparation.prepare_document_for_rag(sample_doc.meta_doc_uuid)
        print(f"   ✓ RAG preparation completed: {rag_result is not None}")
        print(f"   ✓ RAG preparation status: {rag_result.get('status', 'unknown')}")
        
        # Test 5: LightRAG Integration
        print("\\n5. Testing LightRAG Integration...")
        
        # Index document
        index_result = await lightrag_integration.index_meta_document(sample_doc.meta_doc_uuid)
        print(f"   ✓ Document indexed: {index_result is not None}")
        
        # Test retrieval
        query_result = await lightrag_integration.query_documents("artificial intelligence machine learning", top_k=3)
        print(f"   ✓ Query executed: {query_result is not None}")
        print(f"   ✓ Query results: {len(query_result.get('results', []))} documents found")
        
        # Test 6: System Statistics
        print("\\n6. System Statistics...")
        
        rag_stats = rag_preparation.get_preparation_statistics()
        lightrag_stats = lightrag_integration.get_rag_statistics()
        
        print(f"   ✓ RAG statistics available: {isinstance(rag_stats, dict)}")
        print(f"   ✓ LightRAG statistics available: {isinstance(lightrag_stats, dict)}")
        
        if 'chunk_config' in rag_stats:
            chunk_config = rag_stats['chunk_config']
            print(f"   ✓ Chunk size: {chunk_config.get('chunk_size', 'unknown')}")
            print(f"   ✓ Chunk overlap: {chunk_config.get('chunk_overlap', 'unknown')}")
        
        print("\\n" + "=" * 50)
        print("RAG INTEGRATION DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("\\nKey capabilities demonstrated:")
        print("• Meta document storage and retrieval")
        print("• Vector embedding generation with sentence-transformers")
        print("• Semantic similarity calculations")
        print("• RAG-optimized document chunking")
        print("• LightRAG indexing and retrieval")
        print("• Knowledge graph preparation")
        print("• System statistics and monitoring")
        
        print("\\nNext steps:")
        print("• Run full integration test suite: python tests/integration/run_rag_integration_tests.py")
        print("• Explore individual test files for detailed testing")
        print("• Check examples/ directory for more demonstrations")
        
        # Cleanup
        db_connection.close()
        
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"\\nNote: Manual cleanup may be needed for: {temp_dir}")
        
        return True
        
    except Exception as e:
        print(f"\\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main demo function."""
    print("Starting RAG Integration Demo...")
    print("This may take a few minutes to download models and run tests.\\n")
    
    try:
        success = asyncio.run(run_demo_tests())
        
        if success:
            print("\\n🎉 Demo completed successfully!")
            sys.exit(0)
        else:
            print("\\n❌ Demo failed. Check output above for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n\\nDemo interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()