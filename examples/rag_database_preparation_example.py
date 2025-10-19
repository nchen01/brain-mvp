#!/usr/bin/env python3
"""
Example demonstrating RAG database preparation system.

This example shows how to:
1. Create RAG-optimized chunks from meta documents
2. Build semantic indexes for efficient retrieval
3. Map document relationships
4. Create knowledge graphs for context-aware retrieval
"""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Our imports
from src.docforge.rag.rag_database_preparation import (
    RAGDatabasePreparation,
    RAGChunkConfig,
    RAGOptimizedChunker,
    SemanticIndexer,
    DocumentRelationshipMapper,
    KnowledgeGraphBuilder
)
from src.docforge.rag.lightrag_integration import LightRAGConfig, LightRAGIntegration
from src.docforge.rag.embeddings import EmbeddingManager
from src.docforge.storage.meta_document_db import (
    MetaDocumentRecord,
    MetaDocumentComponent
)


def create_sample_documents():
    """Create sample meta documents for demonstration."""
    
    # Document 1: AI Overview
    doc1_components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="""
            Artificial Intelligence (AI) represents one of the most transformative technologies 
            of our time. It encompasses the development of computer systems that can perform 
            tasks typically requiring human intelligence, such as visual perception, speech 
            recognition, decision-making, and language translation. The field has evolved 
            significantly since its inception in the 1950s, moving from rule-based expert 
            systems to modern machine learning approaches that can learn from data.
            """.strip(),
            metadata={"page": 1, "section": "introduction"},
            order_index=0,
            confidence_score=0.95
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="""
            Machine Learning (ML) is a subset of AI that focuses on algorithms that can 
            learn and improve their performance on a specific task through experience. 
            Rather than being explicitly programmed for every scenario, ML systems use 
            statistical techniques to identify patterns in data and make predictions or 
            decisions. This approach has proven particularly effective in areas such as 
            image recognition, natural language processing, and recommendation systems.
            """.strip(),
            metadata={"page": 2, "section": "machine_learning"},
            order_index=1,
            confidence_score=0.92
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document provides a comprehensive overview of artificial intelligence and machine learning technologies, their evolution, and current applications.",
            metadata={"type": "abstract"},
            order_index=2,
            confidence_score=0.88
        )
    ]
    
    # Document 2: Deep Learning Focus
    doc2_components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="""
            Deep Learning represents a revolutionary approach within machine learning that 
            uses artificial neural networks with multiple layers (hence "deep") to model 
            and understand complex patterns in data. These networks are inspired by the 
            structure and function of the human brain, with interconnected nodes (neurons) 
            that process and transmit information. Deep learning has achieved remarkable 
            success in computer vision, natural language processing, and game playing.
            """.strip(),
            metadata={"page": 1, "section": "deep_learning_intro"},
            order_index=0,
            confidence_score=0.94
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="""
            Neural network architectures have evolved to address specific challenges in 
            different domains. Convolutional Neural Networks (CNNs) excel at image 
            processing tasks, while Recurrent Neural Networks (RNNs) and their variants 
            like LSTMs are designed for sequential data such as text and time series. 
            More recently, Transformer architectures have revolutionized natural language 
            processing and are being adapted for various other applications.
            """.strip(),
            metadata={"page": 2, "section": "architectures"},
            order_index=1,
            confidence_score=0.90
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document explores deep learning techniques, neural network architectures, and their applications across different domains.",
            metadata={"type": "abstract"},
            order_index=2,
            confidence_score=0.87
        )
    ]
    
    # Document 3: AI Applications
    doc3_components = [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="""
            The practical applications of artificial intelligence span virtually every 
            industry and aspect of modern life. In healthcare, AI systems assist in 
            medical diagnosis, drug discovery, and personalized treatment plans. 
            Autonomous vehicles rely on AI for navigation and safety systems. In finance, 
            AI powers fraud detection, algorithmic trading, and risk assessment. 
            Entertainment platforms use AI for content recommendation and creation.
            """.strip(),
            metadata={"page": 1, "section": "applications"},
            order_index=0,
            confidence_score=0.93
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="This document examines real-world applications of AI across various industries and their impact on society.",
            metadata={"type": "abstract"},
            order_index=1,
            confidence_score=0.89
        )
    ]
    
    # Create meta documents
    doc1 = MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="Artificial Intelligence and Machine Learning: A Comprehensive Overview",
        summary="An introduction to AI and ML concepts, covering fundamental principles and methodologies.",
        components=doc1_components,
        processing_history=[]
    )
    
    doc2 = MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="Deep Learning: Neural Networks and Modern Architectures",
        summary="A detailed exploration of deep learning techniques and neural network architectures.",
        components=doc2_components,
        processing_history=[]
    )
    
    doc3 = MetaDocumentRecord(
        meta_doc_uuid=str(uuid.uuid4()),
        doc_uuid=str(uuid.uuid4()),
        set_uuid=str(uuid.uuid4()),
        title="AI in Practice: Real-World Applications and Impact",
        summary="An examination of AI applications across industries and their societal implications.",
        components=doc3_components,
        processing_history=[]
    )
    
    return [doc1, doc2, doc3]


async def demonstrate_rag_chunking():
    """Demonstrate RAG-optimized chunking."""
    print("\\n" + "="*60)
    print("RAG-OPTIMIZED CHUNKING DEMONSTRATION")
    print("="*60)
    
    # Create configuration
    chunk_config = RAGChunkConfig(
        chunk_size=400,  # Smaller for demonstration
        chunk_overlap=50,
        min_chunk_size=100,
        preserve_sentences=True,
        semantic_similarity_threshold=0.75
    )
    
    # Create chunker
    chunker = RAGOptimizedChunker(chunk_config)
    
    # Get sample documents
    documents = create_sample_documents()
    
    print(f"\\nProcessing {len(documents)} documents...")
    
    for i, doc in enumerate(documents, 1):
        print(f"\\n--- Document {i}: {doc.title[:50]}... ---")
        
        # Chunk the document
        chunks = chunker.chunk_meta_document(doc)
        
        print(f"Original components: {len(doc.components)}")
        print(f"Generated chunks: {len(chunks)}")
        
        # Show first few chunks
        for j, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
            print(f"\\nChunk {j+1} (ID: {chunk['chunk_id'][:8]}...):")
            print(f"  Type: {chunk['source_component_type']}")
            print(f"  Size: {len(chunk['content'])} characters")
            print(f"  Content preview: {chunk['content'][:100]}...")


async def demonstrate_semantic_indexing():
    """Demonstrate semantic indexing."""
    print("\\n" + "="*60)
    print("SEMANTIC INDEXING DEMONSTRATION")
    print("="*60)
    
    # Create embedding manager
    embedding_manager = EmbeddingManager(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=4
    )
    
    # Create semantic indexer
    indexer = SemanticIndexer(embedding_manager, similarity_threshold=0.7)
    
    # Create chunker
    chunk_config = RAGChunkConfig(chunk_size=300, chunk_overlap=40)
    chunker = RAGOptimizedChunker(chunk_config)
    
    # Get sample documents and create chunks
    documents = create_sample_documents()
    all_chunks = []
    
    for doc in documents:
        chunks = chunker.chunk_meta_document(doc)
        all_chunks.extend(chunks)
    
    print(f"\\nCreating semantic index for {len(all_chunks)} chunks...")
    
    # Create semantic index
    semantic_index = await indexer.create_semantic_index(all_chunks)
    
    print(f"\\nSemantic Index Results:")
    print(f"  Total chunks indexed: {semantic_index['total_chunks']}")
    print(f"  Semantic clusters found: {semantic_index['total_clusters']}")
    print(f"  Semantic relationships: {semantic_index['total_relationships']}")
    
    # Show cluster information
    if semantic_index['semantic_clusters']:
        print(f"\\nCluster Details:")
        for i, cluster in enumerate(semantic_index['semantic_clusters'][:2]):  # Show first 2
            print(f"  Cluster {i+1}:")
            print(f"    Size: {cluster['cluster_size']} chunks")
            print(f"    Average similarity: {cluster['average_similarity']:.3f}")
            print(f"    Topics: {', '.join(cluster['topics'][:3])}")
    
    # Show relationship information
    if semantic_index['semantic_relationships']:
        print(f"\\nRelationship Examples:")
        for i, rel in enumerate(semantic_index['semantic_relationships'][:3]):  # Show first 3
            print(f"  Relationship {i+1}:")
            print(f"    Type: {rel['relationship_type']}")
            print(f"    Strength: {rel['strength']:.3f}")
            print(f"    Cross-document: {rel['metadata']['cross_document']}")


async def demonstrate_document_relationships():
    """Demonstrate document relationship mapping."""
    print("\\n" + "="*60)
    print("DOCUMENT RELATIONSHIP MAPPING DEMONSTRATION")
    print("="*60)
    
    # Create embedding manager
    embedding_manager = EmbeddingManager(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=4
    )
    
    # Create relationship mapper
    mapper = DocumentRelationshipMapper(embedding_manager)
    
    # Get sample documents
    documents = create_sample_documents()
    
    print(f"\\nMapping relationships between {len(documents)} documents...")
    
    # Map relationships
    relationships = await mapper.map_document_relationships(documents)
    
    print(f"\\nFound {len(relationships)} relationships:")
    
    for i, rel in enumerate(relationships):
        source_doc = next(d for d in documents if d.meta_doc_uuid == rel.source_doc_uuid)
        target_doc = next(d for d in documents if d.meta_doc_uuid == rel.target_doc_uuid)
        
        print(f"\\n  Relationship {i+1}:")
        print(f"    Source: {source_doc.title[:40]}...")
        print(f"    Target: {target_doc.title[:40]}...")
        print(f"    Type: {rel.relationship_type}")
        print(f"    Strength: {rel.strength:.3f}")
        
        if rel.relationship_type == "follows":
            time_diff = rel.metadata.get('time_difference', 0)
            print(f"    Time difference: {time_diff:.1f} seconds")


async def demonstrate_knowledge_graph():
    """Demonstrate knowledge graph building."""
    print("\\n" + "="*60)
    print("KNOWLEDGE GRAPH BUILDING DEMONSTRATION")
    print("="*60)
    
    # Create temporary directory for LightRAG
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create LightRAG configuration
        lightrag_config = LightRAGConfig(
            working_dir=temp_dir,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        
        # Create LightRAG integration
        lightrag_integration = LightRAGIntegration(lightrag_config)
        
        # Create embedding manager
        embedding_manager = EmbeddingManager(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=4
        )
        
        # Create knowledge graph builder
        kg_builder = KnowledgeGraphBuilder(lightrag_integration, embedding_manager)
        
        # Get sample documents and relationships
        documents = create_sample_documents()
        
        # Create relationship mapper to get relationships
        mapper = DocumentRelationshipMapper(embedding_manager)
        relationships = await mapper.map_document_relationships(documents)
        
        print(f"\\nBuilding knowledge graph from {len(documents)} documents and {len(relationships)} relationships...")
        
        # Build knowledge graph
        knowledge_graph = await kg_builder.build_knowledge_graph(documents, relationships)
        
        print(f"\\nKnowledge Graph Results:")
        print(f"  Total nodes: {len(knowledge_graph['nodes'])}")
        print(f"  Total edges: {len(knowledge_graph['edges'])}")
        
        # Show node type distribution
        node_types = {}
        for node in knowledge_graph['nodes']:
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
        
        print(f"\\n  Node Types:")
        for node_type, count in node_types.items():
            print(f"    {node_type}: {count}")
        
        # Show edge type distribution
        edge_types = {}
        for edge in knowledge_graph['edges']:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        
        print(f"\\n  Edge Types:")
        for edge_type, count in edge_types.items():
            print(f"    {edge_type}: {count}")
        
        # Show statistics
        stats = knowledge_graph['statistics']
        print(f"\\n  Graph Statistics:")
        print(f"    Density: {stats['density']:.4f}")
        print(f"    Connected components: {stats['connected_components']}")


async def demonstrate_full_rag_preparation():
    """Demonstrate the complete RAG database preparation process."""
    print("\\n" + "="*60)
    print("COMPLETE RAG DATABASE PREPARATION DEMONSTRATION")
    print("="*60)
    
    # Create temporary directory for LightRAG
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create configurations
        chunk_config = RAGChunkConfig(
            chunk_size=400,
            chunk_overlap=50,
            semantic_similarity_threshold=0.75
        )
        
        lightrag_config = LightRAGConfig(
            working_dir=temp_dir,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        
        # Create LightRAG integration
        lightrag_integration = LightRAGIntegration(lightrag_config)
        
        # Create RAG database preparation system
        rag_prep = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=chunk_config
        )
        
        # Get sample documents
        documents = create_sample_documents()
        
        print(f"\\nPreparing {len(documents)} documents for RAG database...")
        
        # Prepare documents for RAG
        results = await rag_prep.prepare_documents_for_rag(documents)
        
        print(f"\\nRAG Preparation Results:")
        print(f"  Documents processed: {results['documents_processed']}")
        print(f"  Total chunks created: {results['total_chunks']}")
        print(f"  Semantic clusters: {results['semantic_clusters']}")
        print(f"  Document relationships: {results['document_relationships']}")
        print(f"  Knowledge graph nodes: {results['knowledge_graph_nodes']}")
        print(f"  Knowledge graph edges: {results['knowledge_graph_edges']}")
        
        # Get preparation statistics
        stats = rag_prep.get_preparation_statistics()
        print(f"\\nPreparation Statistics:")
        print(f"  Chunk config - Size: {stats['chunk_config']['chunk_size']}")
        print(f"  Chunk config - Overlap: {stats['chunk_config']['chunk_overlap']}")
        print(f"  LightRAG working dir: {stats['lightrag_stats']['working_dir']}")


async def main():
    """Run all demonstrations."""
    print("RAG DATABASE PREPARATION SYSTEM DEMONSTRATION")
    print("=" * 80)
    print("This example demonstrates the complete RAG database preparation pipeline:")
    print("1. RAG-optimized chunking")
    print("2. Semantic indexing")
    print("3. Document relationship mapping")
    print("4. Knowledge graph building")
    print("5. Complete RAG preparation process")
    
    try:
        # Run individual demonstrations
        await demonstrate_rag_chunking()
        await demonstrate_semantic_indexing()
        await demonstrate_document_relationships()
        await demonstrate_knowledge_graph()
        await demonstrate_full_rag_preparation()
        
        print("\\n" + "="*80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\\nThe RAG database preparation system provides:")
        print("• Optimized chunking for better retrieval performance")
        print("• Semantic indexing for similarity-based search")
        print("• Document relationship mapping for context awareness")
        print("• Knowledge graph creation for complex queries")
        print("• Integration with LightRAG for advanced retrieval")
        
    except Exception as e:
        print(f"\\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())