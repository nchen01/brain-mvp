"""
Integration tests for logging system with pipeline components.

This test suite validates:
- Logging integration with preprocessing pipeline
- Logging integration with postprocessing pipeline
- Logging integration with RAG pipeline
- Logging integration with storage operations
- End-to-end logging through complete document lifecycle
"""

import pytest
import tempfile
import asyncio
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from utils.logging_system import setup_logging, get_logger, LogCategory
from utils.logging_integration import (
    document_processing_context, postprocessing_context, rag_operation_context,
    preprocessing_logger, postprocessing_logger, storage_logger, rag_logger
)
from docforge.preprocessing.router import DocumentPreprocessingRouter
from docforge.postprocessing.router import PostProcessingRouter
# Note: Some imports may not be available in current implementation
# Tests focus on logging functionality rather than actual component integration


class TestPreprocessingLoggingIntegration:
    """Test logging integration with preprocessing pipeline."""
    
    @pytest.fixture
    def logging_environment(self):
        """Set up logging environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(temp_dir, enable_console=False)
            yield {
                'logger': logger,
                'log_dir': temp_dir
            }
    
    @pytest.fixture
    def preprocessing_components(self):
        """Set up preprocessing components."""
        return {
            'router': DocumentPreprocessingRouter()
        }
    
    def test_document_registration_logging(self, logging_environment, preprocessing_components):
        """Test logging during document registration."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        # Simulate document registration with logging
        doc_uuid = "test_doc_registration_123"
        
        with logger.context(document_id=doc_uuid, user_id="test_user"):
            preprocessing_logger.info(
                "Starting document registration",
                details={
                    "filename": "test_document.pdf",
                    "file_size": 1024000,
                    "file_type": "application/pdf"
                }
            )
            
            # Simulate registration process
            time.sleep(0.1)
            
            preprocessing_logger.info(
                "Document registration completed",
                details={
                    "doc_uuid": doc_uuid,
                    "lineage_uuid": "lineage_123",
                    "version": 1
                },
                performance_metrics={
                    "duration_seconds": 0.1,
                    "success": True
                }
            )
        
        # Verify logging
        preprocessing_log = Path(log_dir) / "docforge_preprocessing.log"
        assert preprocessing_log.exists()
        
        with open(preprocessing_log, 'r') as f:
            log_content = f.read()
            assert "Starting document registration" in log_content
            assert "Document registration completed" in log_content
            assert doc_uuid in log_content
            assert "test_document.pdf" in log_content
    
    def test_routing_decision_logging(self, logging_environment, preprocessing_components):
        """Test logging of routing decisions."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        router = preprocessing_components['router']
        
        # Test routing with logging
        doc_uuid = "test_routing_doc_456"
        
        with document_processing_context(doc_uuid, "routing"):
            # Simulate routing decision
            preprocessing_logger.info(
                "Analyzing document for routing",
                details={
                    "file_type": "application/pdf",
                    "file_size": 2048000,
                    "available_processors": ["mineru", "markitdown"]
                }
            )
            
            # Mock routing decision
            selected_processor = "mineru"
            
            preprocessing_logger.info(
                "Routing decision completed",
                details={
                    "selected_processor": selected_processor,
                    "reason": "PDF format detected",
                    "confidence": 0.95
                }
            )
        
        # Verify routing logs
        main_log = Path(log_dir) / "docforge_main.log"
        assert main_log.exists()
        
        with open(main_log, 'r') as f:
            log_content = f.read()
            assert "routing" in log_content
            assert "started" in log_content
            assert "completed" in log_content
            assert "Analyzing document for routing" in log_content
            assert "mineru" in log_content
    
    def test_processor_execution_logging(self, logging_environment, preprocessing_components):
        """Test logging during processor execution."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_processor_doc_789"
        
        # Test MinerU processor logging
        with document_processing_context(doc_uuid, "mineru_processing"):
            preprocessing_logger.info(
                "Starting MinerU processing",
                details={
                    "input_file": "test.pdf",
                    "processor_config": {"extract_images": True, "extract_tables": True}
                }
            )
            
            # Simulate processing
            time.sleep(0.2)
            
            preprocessing_logger.info(
                "MinerU processing completed",
                details={
                    "pages_processed": 10,
                    "text_extracted": True,
                    "images_extracted": 3,
                    "tables_extracted": 2,
                    "output_size": 15000
                },
                performance_metrics={
                    "duration_seconds": 0.2,
                    "memory_used_mb": 120,
                    "success": True
                }
            )
        
        # Test MarkItDown processor logging
        with document_processing_context(doc_uuid, "markitdown_processing"):
            preprocessing_logger.info(
                "Starting MarkItDown processing",
                details={
                    "input_file": "test.xlsx",
                    "processor_config": {"extract_formulas": True}
                }
            )
            
            time.sleep(0.1)
            
            preprocessing_logger.info(
                "MarkItDown processing completed",
                details={
                    "sheets_processed": 3,
                    "cells_extracted": 500,
                    "formulas_extracted": 25,
                    "output_size": 8000
                },
                performance_metrics={
                    "duration_seconds": 0.1,
                    "success": True
                }
            )
        
        # Verify processor logs
        preprocessing_log = Path(log_dir) / "docforge_preprocessing.log"
        performance_log = Path(log_dir) / "docforge_performance.log"
        
        assert preprocessing_log.exists()
        assert performance_log.exists()
        
        with open(preprocessing_log, 'r') as f:
            content = f.read()
            assert "Starting MinerU processing" in content
            assert "MinerU processing completed" in content
            assert "Starting MarkItDown processing" in content
            assert "MarkItDown processing completed" in content
            assert "pages_processed" in content
            assert "sheets_processed" in content
        
        with open(performance_log, 'r') as f:
            perf_content = f.read()
            assert "duration_seconds" in perf_content
            assert "memory_used_mb" in perf_content


class TestPostprocessingLoggingIntegration:
    """Test logging integration with postprocessing pipeline."""
    
    @pytest.fixture
    def logging_environment(self):
        """Set up logging environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(temp_dir, enable_console=False)
            yield {
                'logger': logger,
                'log_dir': temp_dir
            }
    
    @pytest.fixture
    def postprocessing_components(self):
        """Set up postprocessing components."""
        return {
            'router': PostProcessingRouter()
        }
    
    def test_chunking_strategy_logging(self, logging_environment, postprocessing_components):
        """Test logging during chunking strategy selection and execution."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_chunking_doc_123"
        
        with postprocessing_context(doc_uuid, "chunking_strategy_selection"):
            postprocessing_logger.info(
                "Analyzing document for chunking strategy",
                details={
                    "document_length": 5000,
                    "document_type": "research_paper",
                    "structure_detected": True,
                    "available_strategies": ["paragraph", "section", "semantic"]
                }
            )
            
            selected_strategy = "paragraph"
            
            postprocessing_logger.info(
                "Chunking strategy selected",
                details={
                    "selected_strategy": selected_strategy,
                    "reason": "Well-structured paragraphs detected",
                    "expected_chunks": 25
                }
            )
        
        with postprocessing_context(doc_uuid, "paragraph_chunking"):
            postprocessing_logger.info(
                "Starting paragraph chunking",
                details={
                    "strategy": "paragraph",
                    "input_length": 5000,
                    "min_chunk_size": 100,
                    "max_chunk_size": 500
                }
            )
            
            time.sleep(0.1)
            
            postprocessing_logger.info(
                "Paragraph chunking completed",
                details={
                    "chunks_created": 23,
                    "avg_chunk_size": 217,
                    "min_chunk_size": 95,
                    "max_chunk_size": 485,
                    "overlap_tokens": 20
                },
                performance_metrics={
                    "duration_seconds": 0.1,
                    "chunks_per_second": 230,
                    "success": True
                }
            )
        
        # Verify chunking logs
        postprocessing_log = Path(log_dir) / "docforge_postprocessing.log"
        assert postprocessing_log.exists()
        
        with open(postprocessing_log, 'r') as f:
            content = f.read()
            assert "Analyzing document for chunking strategy" in content
            assert "Chunking strategy selected" in content
            assert "Starting paragraph chunking" in content
            assert "Paragraph chunking completed" in content
            assert "chunks_created" in content
            assert "paragraph" in content
    
    def test_abbreviation_expansion_logging(self, logging_environment, postprocessing_components):
        """Test logging during abbreviation expansion."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_abbrev_doc_456"
        
        with postprocessing_context(doc_uuid, "abbreviation_detection"):
            postprocessing_logger.info(
                "Starting abbreviation detection",
                details={
                    "text_length": 3000,
                    "domain": "technical",
                    "detection_method": "pattern_matching"
                }
            )
            
            postprocessing_logger.info(
                "Abbreviation detection completed",
                details={
                    "abbreviations_found": 12,
                    "unique_abbreviations": 8,
                    "confidence_scores": [0.95, 0.87, 0.92, 0.78, 0.89, 0.94, 0.83, 0.91]
                }
            )
        
        with postprocessing_context(doc_uuid, "abbreviation_expansion"):
            postprocessing_logger.info(
                "Starting abbreviation expansion",
                details={
                    "abbreviations_to_expand": 8,
                    "expansion_source": "domain_dictionary",
                    "confidence_threshold": 0.8
                }
            )
            
            time.sleep(0.05)
            
            postprocessing_logger.info(
                "Abbreviation expansion completed",
                details={
                    "abbreviations_expanded": 6,
                    "abbreviations_skipped": 2,
                    "skip_reasons": ["low_confidence", "ambiguous"],
                    "avg_confidence": 0.88
                },
                performance_metrics={
                    "duration_seconds": 0.05,
                    "expansions_per_second": 120,
                    "success": True
                }
            )
        
        # Verify abbreviation logs
        postprocessing_log = Path(log_dir) / "docforge_postprocessing.log"
        assert postprocessing_log.exists()
        
        with open(postprocessing_log, 'r') as f:
            content = f.read()
            assert "Starting abbreviation detection" in content
            assert "Abbreviation detection completed" in content
            assert "Starting abbreviation expansion" in content
            assert "Abbreviation expansion completed" in content
            assert "abbreviations_found" in content
            assert "abbreviations_expanded" in content
    
    def test_postprocessing_router_logging(self, logging_environment, postprocessing_components):
        """Test logging for postprocessing router decisions."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_router_doc_789"
        
        with logger.context(document_id=doc_uuid):
            postprocessing_logger.info(
                "Starting postprocessing routing analysis",
                details={
                    "document_metadata": {
                        "type": "research_paper",
                        "length": 4500,
                        "language": "english",
                        "domain": "computer_science"
                    },
                    "available_processors": ["chunker", "abbreviation_expander", "normalizer"]
                }
            )
            
            # Simulate routing decisions
            selected_processors = ["chunker", "abbreviation_expander"]
            
            postprocessing_logger.info(
                "Postprocessing routing completed",
                details={
                    "selected_processors": selected_processors,
                    "processing_order": ["chunker", "abbreviation_expander"],
                    "routing_rules_applied": ["length_based", "domain_based"],
                    "estimated_processing_time": 2.5
                }
            )
        
        # Verify router logs
        postprocessing_log = Path(log_dir) / "docforge_postprocessing.log"
        assert postprocessing_log.exists()
        
        with open(postprocessing_log, 'r') as f:
            content = f.read()
            assert "Starting postprocessing routing analysis" in content
            assert "Postprocessing routing completed" in content
            assert "selected_processors" in content
            assert "chunker" in content
            assert "abbreviation_expander" in content


class TestRAGPipelineLoggingIntegration:
    """Test logging integration with RAG pipeline."""
    
    @pytest.fixture
    def logging_environment(self):
        """Set up logging environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(temp_dir, enable_console=False)
            yield {
                'logger': logger,
                'log_dir': temp_dir,
                'temp_dir': temp_dir
            }
    
    def test_embedding_generation_logging(self, logging_environment):
        """Test logging during embedding generation."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_embedding_doc_123"
        
        with rag_operation_context(doc_uuid, "embedding_generation"):
            rag_logger.info(
                "Starting embedding generation",
                details={
                    "chunks_to_embed": 15,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "embedding_dimension": 384,
                    "batch_size": 5
                }
            )
            
            # Simulate embedding generation
            time.sleep(0.2)
            
            rag_logger.info(
                "Embedding generation completed",
                details={
                    "embeddings_created": 15,
                    "total_tokens": 3500,
                    "avg_tokens_per_chunk": 233,
                    "embedding_cache_hits": 2,
                    "embedding_cache_misses": 13
                },
                performance_metrics={
                    "duration_seconds": 0.2,
                    "tokens_per_second": 17500,
                    "embeddings_per_second": 75,
                    "memory_used_mb": 85,
                    "success": True
                }
            )
        
        # Verify embedding logs
        rag_log = Path(log_dir) / "docforge_rag.log"
        assert rag_log.exists()
        
        with open(rag_log, 'r') as f:
            content = f.read()
            assert "Starting embedding generation" in content
            assert "Embedding generation completed" in content
            assert "embeddings_created" in content
            assert "sentence-transformers" in content
    
    def test_lightrag_indexing_logging(self, logging_environment):
        """Test logging during LightRAG indexing."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        temp_dir = logging_environment['temp_dir']
        
        doc_uuid = "test_lightrag_doc_456"
        
        with rag_operation_context(doc_uuid, "lightrag_indexing"):
            rag_logger.info(
                "Starting LightRAG indexing",
                details={
                    "documents_to_index": 1,
                    "chunks_count": 15,
                    "existing_index_size": 50,
                    "lightrag_config": {
                        "working_dir": temp_dir,
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                }
            )
            
            # Simulate indexing process
            time.sleep(0.3)
            
            rag_logger.info(
                "LightRAG indexing completed",
                details={
                    "index_updated": True,
                    "new_index_size": 51,
                    "relationships_created": 12,
                    "entities_extracted": 25,
                    "knowledge_graph_nodes": 38,
                    "knowledge_graph_edges": 45
                },
                performance_metrics={
                    "duration_seconds": 0.3,
                    "chunks_per_second": 50,
                    "relationships_per_second": 40,
                    "success": True
                }
            )
        
        # Verify LightRAG logs
        rag_log = Path(log_dir) / "docforge_rag.log"
        assert rag_log.exists()
        
        with open(rag_log, 'r') as f:
            content = f.read()
            assert "Starting LightRAG indexing" in content
            assert "LightRAG indexing completed" in content
            assert "relationships_created" in content
            assert "knowledge_graph_nodes" in content
    
    def test_rag_query_logging(self, logging_environment):
        """Test logging during RAG query processing."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        query_id = "test_query_789"
        
        with logger.context(query_id=query_id, user_id="test_user"):
            rag_logger.info(
                "Starting RAG query processing",
                details={
                    "query": "What are the main findings in the research?",
                    "query_type": "summarization",
                    "max_results": 5,
                    "similarity_threshold": 0.7
                }
            )
            
            # Simulate query processing
            time.sleep(0.15)
            
            rag_logger.info(
                "RAG query processing completed",
                details={
                    "relevant_chunks_found": 8,
                    "chunks_returned": 5,
                    "avg_similarity_score": 0.82,
                    "context_length": 2500,
                    "response_generated": True
                },
                performance_metrics={
                    "duration_seconds": 0.15,
                    "query_processing_time": 0.05,
                    "retrieval_time": 0.08,
                    "generation_time": 0.02,
                    "success": True
                }
            )
        
        # Verify query logs
        rag_log = Path(log_dir) / "docforge_rag.log"
        assert rag_log.exists()
        
        with open(rag_log, 'r') as f:
            content = f.read()
            assert "Starting RAG query processing" in content
            assert "RAG query processing completed" in content
            assert "relevant_chunks_found" in content
            assert "What are the main findings" in content


class TestStorageOperationsLoggingIntegration:
    """Test logging integration with storage operations."""
    
    @pytest.fixture
    def logging_environment(self):
        """Set up logging environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(temp_dir, enable_console=False)
            yield {
                'logger': logger,
                'log_dir': temp_dir,
                'temp_dir': temp_dir
            }
    
    def test_meta_document_crud_logging(self, logging_environment):
        """Test logging for meta document CRUD operations."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        temp_dir = logging_environment['temp_dir']
        
        doc_uuid = "test_meta_doc_123"
        
        # Test document creation logging
        with logger.context(document_id=doc_uuid):
            storage_logger.info(
                "Starting meta document creation",
                details={
                    "doc_uuid": doc_uuid,
                    "set_uuid": "set_123",
                    "title": "Test Document",
                    "components_count": 3
                }
            )
            
            # Simulate creation
            time.sleep(0.1)
            
            storage_logger.info(
                "Meta document creation completed",
                details={
                    "doc_uuid": doc_uuid,
                    "meta_file_uuids": ["meta_1", "meta_2", "meta_3"],
                    "storage_path": "/meta/documents/",
                    "total_size_bytes": 15000
                },
                performance_metrics={
                    "duration_seconds": 0.1,
                    "write_speed_mbps": 1.5,
                    "success": True
                }
            )
        
        # Test document retrieval logging
        with logger.context(document_id=doc_uuid):
            storage_logger.info(
                "Starting meta document retrieval",
                details={
                    "doc_uuid": doc_uuid,
                    "include_components": True,
                    "cache_check": True
                }
            )
            
            storage_logger.info(
                "Meta document retrieval completed",
                details={
                    "doc_uuid": doc_uuid,
                    "components_loaded": 3,
                    "cache_hit": False,
                    "total_size_bytes": 15000
                },
                performance_metrics={
                    "duration_seconds": 0.05,
                    "read_speed_mbps": 3.0,
                    "success": True
                }
            )
        
        # Verify storage logs
        storage_log = Path(log_dir) / "docforge_storage.log"
        assert storage_log.exists()
        
        with open(storage_log, 'r') as f:
            content = f.read()
            assert "Starting meta document creation" in content
            assert "Meta document creation completed" in content
            assert "Starting meta document retrieval" in content
            assert "Meta document retrieval completed" in content
            assert doc_uuid in content
    
    def test_versioning_operations_logging(self, logging_environment):
        """Test logging for versioning operations."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        lineage_uuid = "test_lineage_456"
        doc_uuid = "test_version_doc_789"
        
        # Test lineage creation logging
        with logger.context(lineage_uuid=lineage_uuid):
            storage_logger.info(
                "Starting document lineage creation",
                details={
                    "lineage_uuid": lineage_uuid,
                    "original_filename": "research_paper.pdf",
                    "created_by": "test_user",
                    "initial_version": 1
                }
            )
            
            storage_logger.info(
                "Document lineage creation completed",
                details={
                    "lineage_uuid": lineage_uuid,
                    "version_chain_initialized": True,
                    "metadata_stored": True
                }
            )
        
        # Test version creation logging
        with logger.context(lineage_uuid=lineage_uuid, document_id=doc_uuid, version_id="v2"):
            storage_logger.info(
                "Starting new version creation",
                details={
                    "lineage_uuid": lineage_uuid,
                    "parent_version": 1,
                    "version_number": 2,
                    "edit_type": "content_update"
                }
            )
            
            storage_logger.info(
                "New version creation completed",
                details={
                    "doc_uuid": doc_uuid,
                    "version_number": 2,
                    "version_chain_updated": True,
                    "parent_preserved": True
                },
                performance_metrics={
                    "duration_seconds": 0.08,
                    "success": True
                }
            )
        
        # Verify versioning logs
        versioning_log = Path(log_dir) / "docforge_versioning.log"
        assert versioning_log.exists()
        
        with open(versioning_log, 'r') as f:
            content = f.read()
            assert "Starting document lineage creation" in content
            assert "Document lineage creation completed" in content
            assert "Starting new version creation" in content
            assert "New version creation completed" in content
            assert lineage_uuid in content
            assert doc_uuid in content


class TestEndToEndPipelineLogging:
    """Test end-to-end logging through complete document lifecycle."""
    
    @pytest.fixture
    def logging_environment(self):
        """Set up logging environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(temp_dir, enable_console=False)
            yield {
                'logger': logger,
                'log_dir': temp_dir,
                'temp_dir': temp_dir
            }
    
    def test_complete_document_lifecycle_logging(self, logging_environment):
        """Test logging through complete document processing lifecycle."""
        logger = logging_environment['logger']
        log_dir = logging_environment['log_dir']
        
        doc_uuid = "test_lifecycle_doc_complete"
        lineage_uuid = "test_lifecycle_lineage"
        
        # Stage 1: Document Upload and Registration
        with logger.context(document_id=doc_uuid, lineage_uuid=lineage_uuid, user_id="test_user"):
            preprocessing_logger.info(
                "Document lifecycle started - Upload and Registration",
                details={
                    "filename": "complete_test.pdf",
                    "file_size": 2048000,
                    "user_id": "test_user",
                    "upload_method": "api"
                }
            )
        
        # Stage 2: Preprocessing
        with document_processing_context(doc_uuid, "complete_preprocessing"):
            preprocessing_logger.info(
                "Preprocessing stage completed",
                details={
                    "processor": "mineru",
                    "pages_processed": 15,
                    "text_extracted": True,
                    "images_extracted": 5,
                    "tables_extracted": 3
                },
                performance_metrics={"duration_seconds": 12.5}
            )
        
        # Stage 3: Postprocessing
        with postprocessing_context(doc_uuid, "complete_postprocessing"):
            postprocessing_logger.info(
                "Postprocessing stage completed",
                details={
                    "chunking_strategy": "paragraph",
                    "chunks_created": 45,
                    "abbreviations_expanded": 12,
                    "content_normalized": True
                },
                performance_metrics={"duration_seconds": 3.2}
            )
        
        # Stage 4: Storage Operations
        with logger.context(document_id=doc_uuid):
            storage_logger.info(
                "Storage operations completed",
                details={
                    "meta_documents_created": 1,
                    "components_stored": 4,
                    "version_tracking_enabled": True,
                    "storage_location": "/meta/documents/"
                },
                performance_metrics={"duration_seconds": 0.8}
            )
        
        # Stage 5: RAG Preparation
        with rag_operation_context(doc_uuid, "complete_rag_preparation"):
            rag_logger.info(
                "RAG preparation completed",
                details={
                    "embeddings_generated": 45,
                    "lightrag_indexed": True,
                    "relationships_created": 28,
                    "knowledge_graph_updated": True
                },
                performance_metrics={"duration_seconds": 18.7}
            )
        
        # Stage 6: Lifecycle Completion
        with logger.context(document_id=doc_uuid, lineage_uuid=lineage_uuid):
            preprocessing_logger.info(
                "Document lifecycle completed successfully",
                details={
                    "total_stages": 5,
                    "all_stages_successful": True,
                    "document_ready_for_queries": True,
                    "processing_summary": {
                        "preprocessing_time": 12.5,
                        "postprocessing_time": 3.2,
                        "storage_time": 0.8,
                        "rag_preparation_time": 18.7,
                        "total_time": 35.2
                    }
                },
                performance_metrics={
                    "total_duration_seconds": 35.2,
                    "success": True
                }
            )
        
        # Verify complete lifecycle logging
        log_files = {
            'main': Path(log_dir) / "docforge_main.log",
            'preprocessing': Path(log_dir) / "docforge_preprocessing.log",
            'postprocessing': Path(log_dir) / "docforge_postprocessing.log",
            'storage': Path(log_dir) / "docforge_storage.log",
            'rag': Path(log_dir) / "docforge_rag.log",
            'performance': Path(log_dir) / "docforge_performance.log"
        }
        
        # Verify all log files exist
        for log_name, log_path in log_files.items():
            assert log_path.exists(), f"{log_name} log file should exist"
        
        # Verify main log contains all stages
        with open(log_files['main'], 'r') as f:
            main_content = f.read()
            assert "Document lifecycle started" in main_content
            assert "complete_preprocessing" in main_content
            assert "complete_postprocessing" in main_content
            assert "complete_rag_preparation" in main_content
            assert "Document lifecycle completed successfully" in main_content
            assert doc_uuid in main_content
        
        # Verify performance log contains metrics from all stages
        with open(log_files['performance'], 'r') as f:
            perf_content = f.read()
            assert "12.5" in perf_content  # preprocessing time
            assert "3.2" in perf_content   # postprocessing time
            assert "18.7" in perf_content  # rag preparation time
            assert "35.2" in perf_content  # total time
        
        # Verify component-specific logs contain relevant information
        with open(log_files['preprocessing'], 'r') as f:
            prep_content = f.read()
            assert "mineru" in prep_content
            assert "pages_processed" in prep_content
        
        with open(log_files['postprocessing'], 'r') as f:
            post_content = f.read()
            assert "chunking_strategy" in post_content
            assert "abbreviations_expanded" in post_content
        
        with open(log_files['rag'], 'r') as f:
            rag_content = f.read()
            assert "embeddings_generated" in rag_content
            assert "lightrag_indexed" in rag_content
            assert "relationships_created" in rag_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])