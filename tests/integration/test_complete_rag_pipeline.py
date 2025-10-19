"""
Complete RAG pipeline integration test.

This test demonstrates the entire pipeline from raw document processing
to RAG-ready retrieval system, including:
1. Document registration and versioning
2. Content processing and post-processing
3. Meta document creation
4. RAG database preparation
5. Vector embedding generation
6. LightRAG indexing
7. Knowledge graph creation
8. End-to-end retrieval testing
"""

import pytest
import tempfile
import os
import uuid
import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Our imports
from src.docforge.versioning.models import DocumentRegistration, DocumentVersion
from src.docforge.versioning.lineage import DocumentLineageManager
from src.docforge.storage.post_document_db import PostDocumentRecord
from src.docforge.storage.post_document_register import PostDocumentRegister
from src.docforge.storage.meta_document_db import (
    MetaDocumentRecord,
    MetaDocumentComponent
)
from src.docforge.storage.meta_document_crud import MetaDocumentCRUD
from src.docforge.rag.rag_database_preparation import (
    RAGDatabasePreparation,
    RAGChunkConfig
)
from src.docforge.rag.lightrag_integration import (
    LightRAGConfig,
    LightRAGIntegration
)
from src.docforge.postprocessing.chunker import DocumentChunker, ChunkingConfig
from src.docforge.postprocessing.abbreviation_expander import AbbreviationExpander
from src.dbm.connection import DummyDBConnection


@pytest.fixture(scope="function")
def complete_test_environment():
    """Set up complete test environment with all necessary components."""
    # Create temporary directory structure
    temp_dir = tempfile.mkdtemp()
    
    env = {
        'base_dir': temp_dir,
        'db_path': os.path.join(temp_dir, 'complete_test.db'),
        'lightrag_dir': os.path.join(temp_dir, 'lightrag'),
        'rag_db_dir': os.path.join(temp_dir, 'rag_database'),
        'storage_dir': os.path.join(temp_dir, 'document_storage'),
        'cache_dir': os.path.join(temp_dir, 'cache')
    }
    
    # Create directories
    for dir_path in [env['lightrag_dir'], env['rag_db_dir'], env['storage_dir'], env['cache_dir']]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Initialize database
    db_connection = DummyDBConnection(env['db_path'])
    
    env['db_connection'] = db_connection
    
    yield env
    
    # Cleanup
    try:
        db_connection.close()
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Failed to cleanup test environment: {e}")


@pytest.fixture
def sample_document_content():
    """Create sample document content for testing."""
    return {
        'ai_research': {
            'title': "Transformer Architectures in Modern NLP: A Comprehensive Analysis",
            'content': """
            # Transformer Architectures in Modern NLP: A Comprehensive Analysis

            ## Abstract
            
            This paper presents a comprehensive analysis of transformer architectures and their 
            impact on modern natural language processing. We examine the evolution from 
            attention mechanisms to full transformer models, analyzing their effectiveness 
            across various NLP tasks including machine translation, text summarization, 
            and question answering.

            ## Introduction
            
            The introduction of the transformer architecture in "Attention is All You Need" 
            (Vaswani et al., 2017) marked a paradigm shift in natural language processing. 
            Unlike previous sequence-to-sequence models that relied on recurrent or 
            convolutional layers, transformers use self-attention mechanisms to process 
            input sequences in parallel, leading to significant improvements in both 
            training efficiency and model performance.

            ## Methodology
            
            Our analysis focuses on three key aspects of transformer architectures:
            
            1. **Self-Attention Mechanisms**: The core innovation that allows transformers 
               to capture long-range dependencies without the sequential processing 
               limitations of RNNs.
            
            2. **Positional Encoding**: The method by which transformers incorporate 
               sequence order information without relying on recurrent connections.
            
            3. **Multi-Head Attention**: The parallel attention computation that enables 
               the model to focus on different aspects of the input simultaneously.

            ## Results and Discussion
            
            Our experiments demonstrate that transformer-based models consistently 
            outperform traditional RNN and CNN architectures across multiple benchmarks. 
            The BERT model, based on the transformer encoder, achieved state-of-the-art 
            results on 11 NLP tasks. Similarly, GPT models have shown remarkable 
            capabilities in text generation and few-shot learning scenarios.

            ## Conclusion
            
            Transformer architectures have fundamentally changed the landscape of natural 
            language processing. Their ability to process sequences in parallel, capture 
            long-range dependencies, and scale effectively with increased data and 
            computational resources makes them the foundation for most modern NLP systems.
            """,
            'metadata': {
                'authors': ['Dr. Jane Smith', 'Prof. John Doe'],
                'publication_year': 2023,
                'journal': 'Journal of AI Research',
                'keywords': ['transformers', 'NLP', 'attention', 'BERT', 'GPT'],
                'doi': '10.1000/182'
            }
        },
        'ml_tutorial': {
            'title': "Machine Learning Fundamentals: A Practical Guide",
            'content': """
            # Machine Learning Fundamentals: A Practical Guide

            ## Chapter 1: Introduction to Machine Learning
            
            Machine learning is a subset of artificial intelligence that enables computers 
            to learn and improve from experience without being explicitly programmed. 
            This field has revolutionized how we approach complex problems in various 
            domains, from image recognition to natural language processing.

            ### Types of Machine Learning
            
            There are three main types of machine learning:
            
            1. **Supervised Learning**: Learning with labeled examples
               - Classification: Predicting categories (e.g., spam detection)
               - Regression: Predicting continuous values (e.g., house prices)
            
            2. **Unsupervised Learning**: Finding patterns in unlabeled data
               - Clustering: Grouping similar data points
               - Dimensionality Reduction: Simplifying data while preserving information
            
            3. **Reinforcement Learning**: Learning through interaction and feedback
               - Agent learns optimal actions through trial and error
               - Applications in game playing, robotics, and autonomous systems

            ## Chapter 2: Supervised Learning Algorithms
            
            ### Linear Regression
            
            Linear regression is one of the simplest and most widely used machine learning 
            algorithms. It models the relationship between a dependent variable and 
            independent variables by fitting a linear equation to observed data.
            
            The basic form is: y = mx + b
            Where:
            - y is the predicted value
            - m is the slope (coefficient)
            - x is the input feature
            - b is the y-intercept (bias)

            ### Decision Trees
            
            Decision trees are intuitive algorithms that make decisions by asking a series 
            of questions about the features. They create a tree-like model of decisions 
            and their possible consequences, making them highly interpretable.

            ### Neural Networks
            
            Neural networks are inspired by biological neural networks and consist of 
            interconnected nodes (neurons) organized in layers. They can learn complex 
            non-linear relationships and are the foundation of deep learning.

            ## Chapter 3: Model Evaluation and Validation
            
            Proper evaluation is crucial for building reliable machine learning models. 
            Common evaluation techniques include:
            
            - **Cross-Validation**: Splitting data into multiple folds for robust evaluation
            - **Holdout Method**: Separating data into training, validation, and test sets
            - **Metrics**: Accuracy, precision, recall, F1-score, ROC-AUC for classification
            - **Overfitting Prevention**: Regularization, early stopping, dropout
            """,
            'metadata': {
                'author': 'Prof. Alice Johnson',
                'publication_year': 2024,
                'publisher': 'Tech Education Press',
                'isbn': '978-0-123456-78-9',
                'difficulty_level': 'beginner_to_intermediate'
            }
        },
        'ai_ethics': {
            'title': "Ethical AI: Addressing Bias and Fairness in Machine Learning Systems",
            'content': """
            # Ethical AI: Addressing Bias and Fairness in Machine Learning Systems

            ## Executive Summary
            
            As artificial intelligence systems become increasingly integrated into 
            decision-making processes across society, ensuring these systems are fair, 
            unbiased, and ethical has become a critical concern. This report examines 
            the sources of bias in AI systems and proposes frameworks for developing 
            more equitable machine learning models.

            ## Understanding Bias in AI Systems
            
            ### Sources of Bias
            
            Bias in AI systems can originate from multiple sources:
            
            1. **Historical Bias**: When training data reflects past discriminatory practices
            2. **Representation Bias**: When certain groups are underrepresented in datasets
            3. **Measurement Bias**: When data collection methods systematically favor certain outcomes
            4. **Algorithmic Bias**: When the algorithm itself introduces unfair treatment
            5. **Evaluation Bias**: When performance metrics don't account for fairness

            ### Case Studies
            
            #### Hiring Algorithms
            
            Several companies have faced criticism for AI hiring tools that showed bias 
            against women and minorities. These systems learned from historical hiring 
            data that reflected past discriminatory practices, perpetuating and amplifying 
            existing inequalities.

            #### Criminal Justice Risk Assessment
            
            Risk assessment tools used in criminal justice have been found to exhibit 
            racial bias, incorrectly flagging Black defendants as high-risk at nearly 
            twice the rate of white defendants. This demonstrates how algorithmic bias 
            can have serious real-world consequences.

            ## Frameworks for Ethical AI Development
            
            ### Fairness Metrics
            
            Different definitions of fairness exist, and choosing the appropriate metric 
            depends on the context:
            
            - **Demographic Parity**: Equal positive prediction rates across groups
            - **Equalized Odds**: Equal true positive and false positive rates across groups
            - **Individual Fairness**: Similar individuals receive similar predictions
            - **Counterfactual Fairness**: Predictions remain the same in a counterfactual world

            ### Best Practices
            
            1. **Diverse Teams**: Include diverse perspectives in AI development teams
            2. **Bias Testing**: Regularly test models for bias across different groups
            3. **Transparent Documentation**: Maintain clear documentation of data sources and model decisions
            4. **Stakeholder Engagement**: Involve affected communities in the development process
            5. **Continuous Monitoring**: Implement ongoing monitoring for bias in deployed systems

            ## Regulatory and Governance Considerations
            
            Governments and organizations worldwide are developing frameworks for AI governance:
            
            - **EU AI Act**: Comprehensive regulation of AI systems based on risk levels
            - **Algorithmic Accountability Act**: Proposed US legislation requiring bias assessments
            - **IEEE Standards**: Technical standards for ethical AI design
            - **Partnership on AI**: Industry collaboration on AI best practices

            ## Conclusion
            
            Building ethical AI systems requires a multifaceted approach that addresses 
            bias at every stage of the machine learning pipeline. By implementing robust 
            fairness frameworks, engaging diverse stakeholders, and maintaining ongoing 
            vigilance, we can work toward AI systems that benefit all members of society 
            equitably.
            """,
            'metadata': {
                'authors': ['Dr. Maria Rodriguez', 'Dr. David Chen', 'Prof. Sarah Williams'],
                'organization': 'Institute for Ethical AI',
                'publication_date': '2024-01-15',
                'report_type': 'policy_analysis',
                'classification': 'public'
            }
        }
    }


class TestCompleteRAGPipeline:
    """Test the complete RAG pipeline from document processing to retrieval."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, complete_test_environment, sample_document_content):
        """Test the complete end-to-end RAG pipeline."""
        env = complete_test_environment
        
        print("\\n" + "="*80)
        print("COMPLETE RAG PIPELINE INTEGRATION TEST")
        print("="*80)
        
        # Step 1: Document Registration and Versioning
        print("\\n1. Document Registration and Versioning...")
        
        lineage_manager = DocumentLineageManager(env['db_connection'])
        registered_docs = []
        
        for doc_key, doc_data in sample_document_content.items():
            # Create document registration
            registration = DocumentRegistration(
                title=doc_data['title'],
                content_hash=f"hash_{doc_key}",
                file_path=f"/test/documents/{doc_key}.txt",
                metadata=doc_data['metadata']
            )
            
            # Register document with lineage
            lineage_uuid, doc_uuid = lineage_manager.create_document_lineage(registration)
            registered_docs.append({
                'key': doc_key,
                'lineage_uuid': lineage_uuid,
                'doc_uuid': doc_uuid,
                'data': doc_data
            })
        
        print(f"   ✓ Registered {len(registered_docs)} documents with versioning")
        
        # Step 2: Content Processing (Simulated)
        print("\\n2. Content Processing and Post-Processing...")
        
        post_doc_register = PostDocumentRegister(env['db_connection'])
        processed_docs = []
        
        for doc in registered_docs:
            # Simulate content processing
            chunker = DocumentChunker(ChunkingConfig(
                strategy="paragraph_based",
                max_chunk_size=500,
                overlap_size=50
            ))
            
            # Create chunks from content
            chunks = chunker.chunk_text(doc['data']['content'])
            
            # Create post document record
            post_doc = PostDocumentRecord(
                post_doc_uuid=str(uuid.uuid4()),
                doc_uuid=doc['doc_uuid'],
                set_uuid=str(uuid.uuid4()),
                processing_method="chunking_and_expansion",
                chunks=chunks,
                metadata={
                    'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                    'chunk_count': len(chunks),
                    'processing_method': 'paragraph_based_chunking'
                }
            )
            
            # Store post document
            post_doc_register.create_post_document(post_doc)
            processed_docs.append({
                **doc,
                'post_doc': post_doc,
                'chunks': chunks
            })
        
        print(f"   ✓ Processed {len(processed_docs)} documents into chunks")
        
        # Step 3: Meta Document Creation
        print("\\n3. Meta Document Creation...")
        
        meta_doc_crud = MetaDocumentCRUD(env['db_connection'])
        meta_docs = []
        
        for doc in processed_docs:
            # Create meta document components from chunks
            components = []
            
            # Add title component
            components.append(MetaDocumentComponent(
                component_id=str(uuid.uuid4()),
                component_type="title",
                content=doc['data']['title'],
                metadata={'source': 'original_title'},
                order_index=0,
                confidence_score=1.0
            ))
            
            # Add chunk components
            for i, chunk in enumerate(doc['chunks'][:5]):  # Limit for testing
                components.append(MetaDocumentComponent(
                    component_id=str(uuid.uuid4()),
                    component_type="chunk",
                    content=chunk,
                    metadata={
                        'chunk_index': i,
                        'source': 'post_processing',
                        'word_count': len(chunk.split())
                    },
                    order_index=i + 1,
                    confidence_score=0.9
                ))
            
            # Add summary component
            summary = f"This document covers {doc['key']} with {len(doc['chunks'])} content sections."
            components.append(MetaDocumentComponent(
                component_id=str(uuid.uuid4()),
                component_type="summary",
                content=summary,
                metadata={'type': 'generated_summary'},
                order_index=len(components),
                confidence_score=0.8
            ))
            
            # Create processing history
            processing_history = [
                {
                    "step_name": "document_registration",
                    "processor_name": "lineage_manager",
                    "status": "completed",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {'lineage_uuid': doc['lineage_uuid']}
                },
                {
                    "step_name": "content_chunking",
                    "processor_name": "document_chunker",
                    "status": "completed",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {'chunk_count': len(doc['chunks'])}
                }
            ]
            
            # Create meta document
            meta_doc = MetaDocumentRecord(
                meta_doc_uuid=str(uuid.uuid4()),
                doc_uuid=doc['doc_uuid'],
                set_uuid=doc['post_doc'].set_uuid,
                title=doc['data']['title'],
                summary=summary,
                components=components,
                processing_history=processing_history,
                rag_ready=False,
                knowledge_graph_id=None
            )
            
            # Store meta document
            meta_doc_crud.create_meta_document(meta_doc)
            meta_docs.append(meta_doc)
        
        print(f"   ✓ Created {len(meta_docs)} meta documents")
        
        # Step 4: RAG Database Preparation
        print("\\n4. RAG Database Preparation...")
        
        # Configure RAG system
        lightrag_config = LightRAGConfig(
            working_dir=env['lightrag_dir'],
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384,
            batch_size=4
        )
        
        rag_chunk_config = RAGChunkConfig(
            chunk_size=400,
            chunk_overlap=50,
            semantic_similarity_threshold=0.75
        )
        
        # Create RAG preparation system
        lightrag_integration = LightRAGIntegration(lightrag_config, meta_doc_crud)
        rag_preparation = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=rag_chunk_config
        )
        
        # Prepare documents for RAG
        rag_results = []
        for meta_doc in meta_docs:
            result = await rag_preparation.prepare_document_for_rag(meta_doc.meta_doc_uuid)
            rag_results.append(result)
        
        print(f"   ✓ Prepared {len(rag_results)} documents for RAG")
        
        # Step 5: Vector Embedding Generation and Storage
        print("\\n5. Vector Embedding Generation and LightRAG Indexing...")
        
        indexing_results = []
        for meta_doc in meta_docs:
            result = await lightrag_integration.index_meta_document(meta_doc.meta_doc_uuid)
            indexing_results.append(result)
        
        print(f"   ✓ Indexed {len(indexing_results)} documents in LightRAG")
        
        # Step 6: Knowledge Graph Creation
        print("\\n6. Knowledge Graph Creation...")
        
        # Map document relationships
        relationships = await rag_preparation.relationship_mapper.map_document_relationships(meta_docs)
        
        # Build knowledge graph
        knowledge_graph = await rag_preparation.knowledge_graph_builder.build_knowledge_graph(
            meta_docs, relationships
        )
        
        print(f"   ✓ Built knowledge graph with {len(knowledge_graph['nodes'])} nodes and {len(knowledge_graph['edges'])} edges")
        
        # Step 7: End-to-End Retrieval Testing
        print("\\n7. End-to-End Retrieval Testing...")
        
        test_queries = [
            "transformer architectures and attention mechanisms",
            "machine learning supervised learning algorithms",
            "AI ethics bias fairness",
            "neural networks deep learning",
            "natural language processing NLP"
        ]
        
        retrieval_results = {}
        for query in test_queries:
            result = await lightrag_integration.query_documents(query, top_k=3)
            retrieval_results[query] = result
            
            print(f"   Query: '{query[:40]}...'")
            print(f"   Results: {len(result.get('results', []))} documents found")
        
        # Step 8: System Statistics and Validation
        print("\\n8. System Statistics and Validation...")
        
        # Get system statistics
        rag_stats = rag_preparation.get_preparation_statistics()
        lightrag_stats = lightrag_integration.get_rag_statistics()
        
        # Validate pipeline results
        pipeline_stats = {
            'documents_registered': len(registered_docs),
            'documents_processed': len(processed_docs),
            'meta_documents_created': len(meta_docs),
            'documents_rag_prepared': len([r for r in rag_results if r.get('status') == 'completed']),
            'documents_indexed': len([r for r in indexing_results if r is not None]),
            'document_relationships': len(relationships),
            'knowledge_graph_nodes': len(knowledge_graph['nodes']),
            'knowledge_graph_edges': len(knowledge_graph['edges']),
            'test_queries_executed': len(test_queries),
            'successful_retrievals': len([r for r in retrieval_results.values() if r.get('results')])
        }
        
        print(f"\\n   Pipeline Statistics:")
        for key, value in pipeline_stats.items():
            print(f"     {key.replace('_', ' ').title()}: {value}")
        
        # Verify pipeline integrity
        assert pipeline_stats['documents_registered'] == len(sample_document_content)
        assert pipeline_stats['documents_processed'] == pipeline_stats['documents_registered']
        assert pipeline_stats['meta_documents_created'] == pipeline_stats['documents_processed']
        assert pipeline_stats['documents_rag_prepared'] > 0
        assert pipeline_stats['documents_indexed'] > 0
        assert pipeline_stats['knowledge_graph_nodes'] > 0
        assert pipeline_stats['test_queries_executed'] == len(test_queries)
        
        print("\\n" + "="*80)
        print("COMPLETE RAG PIPELINE TEST SUCCESSFUL!")
        print("="*80)
        
        return pipeline_stats
    
    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, complete_test_environment):
        """Test pipeline error recovery and resilience."""
        env = complete_test_environment
        
        print("\\n" + "="*60)
        print("PIPELINE ERROR RECOVERY TEST")
        print("="*60)
        
        # Test with invalid document UUID
        meta_doc_crud = MetaDocumentCRUD(env['db_connection'])
        
        lightrag_config = LightRAGConfig(
            working_dir=env['lightrag_dir'],
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        
        lightrag_integration = LightRAGIntegration(lightrag_config, meta_doc_crud)
        rag_preparation = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=RAGChunkConfig()
        )
        
        # Test error handling
        invalid_uuid = str(uuid.uuid4())
        
        # Should handle gracefully without crashing
        result = await rag_preparation.prepare_document_for_rag(invalid_uuid)
        assert result is not None
        assert 'error' in result or result.get('status') == 'failed'
        
        print("   ✓ Pipeline handles invalid document UUIDs gracefully")
        
        # Test with empty query
        query_result = await lightrag_integration.query_documents("", top_k=5)
        assert query_result is not None
        
        print("   ✓ Pipeline handles empty queries gracefully")
        
        print("\\n" + "="*60)
        print("ERROR RECOVERY TEST SUCCESSFUL!")
        print("="*60)
    
    @pytest.mark.asyncio
    async def test_pipeline_performance_benchmarks(self, complete_test_environment, sample_document_content):
        """Test pipeline performance benchmarks."""
        env = complete_test_environment
        
        print("\\n" + "="*60)
        print("PIPELINE PERFORMANCE BENCHMARKS")
        print("="*60)
        
        import time
        
        # Setup
        meta_doc_crud = MetaDocumentCRUD(env['db_connection'])
        lightrag_config = LightRAGConfig(
            working_dir=env['lightrag_dir'],
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384
        )
        lightrag_integration = LightRAGIntegration(lightrag_config, meta_doc_crud)
        rag_preparation = RAGDatabasePreparation(
            lightrag_integration=lightrag_integration,
            chunk_config=RAGChunkConfig()
        )
        
        # Create a test meta document
        test_doc = MetaDocumentRecord(
            meta_doc_uuid=str(uuid.uuid4()),
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Performance Test Document",
            summary="Test document for performance benchmarking",
            components=[
                MetaDocumentComponent(
                    component_id=str(uuid.uuid4()),
                    component_type="chunk",
                    content=sample_document_content['ai_research']['content'][:1000],
                    metadata={},
                    order_index=0,
                    confidence_score=0.9
                )
            ],
            processing_history=[]
        )
        
        meta_doc_crud.create_meta_document(test_doc)
        
        # Benchmark RAG preparation
        start_time = time.time()
        rag_result = await rag_preparation.prepare_document_for_rag(test_doc.meta_doc_uuid)
        rag_time = time.time() - start_time
        
        # Benchmark indexing
        start_time = time.time()
        index_result = await lightrag_integration.index_meta_document(test_doc.meta_doc_uuid)
        index_time = time.time() - start_time
        
        # Benchmark querying
        start_time = time.time()
        query_result = await lightrag_integration.query_documents("test query", top_k=5)
        query_time = time.time() - start_time
        
        # Performance assertions (loose bounds for CI)
        assert rag_time < 30.0, f"RAG preparation too slow: {rag_time}s"
        assert index_time < 20.0, f"Indexing too slow: {index_time}s"
        assert query_time < 10.0, f"Querying too slow: {query_time}s"
        
        print(f"\\n   Performance Results:")
        print(f"     RAG Preparation: {rag_time:.2f}s")
        print(f"     Document Indexing: {index_time:.2f}s")
        print(f"     Query Execution: {query_time:.2f}s")
        
        print("\\n" + "="*60)
        print("PERFORMANCE BENCHMARKS PASSED!")
        print("="*60)
        
        return {
            'rag_preparation_time': rag_time,
            'indexing_time': index_time,
            'query_time': query_time
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])