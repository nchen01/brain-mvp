"""Integration tests for the complete post-processing pipeline."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.postprocessing.router import PostProcessingRouter
from src.docforge.postprocessing.chunker import DocumentChunker
from src.docforge.postprocessing.abbreviation_expander import AbbreviationExpander
from src.docforge.postprocessing.schemas import (
    ProcessingMethod,
    ChunkingStrategy,
    PostProcessingConfig,
    PostProcessingResult
)
from src.docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingMetadata,
    DocumentStructure,
    ProcessingStatus,
    create_content_element,
    create_processing_metadata,
    create_document_structure
)


class TestPostProcessingPipelineIntegration:
    """Integration tests for the complete post-processing pipeline."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.router_db_path = os.path.join(self.temp_dir, "router_km.json")
        self.abbrev_db_path = os.path.join(self.temp_dir, "abbreviations.json")
        
        # Initialize components
        self.router = PostProcessingRouter(self.router_db_path)
        self.expander = AbbreviationExpander(self.abbrev_db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_complex_document(self) -> StandardizedDocumentOutput:
        """Create a complex document for testing the complete pipeline."""
        content_elements = [
            # Title
            create_content_element(
                element_id="title",
                content_type=ContentType.HEADING,
                content="API Integration Guide for ML Systems",
                metadata={"level": 1}
            ),
            
            # Abstract
            create_content_element(
                element_id="abstract",
                content_type=ContentType.PARAGRAPH,
                content="This document describes API integration patterns for ML systems. "
                       "The REST architecture uses HTTP protocols with JSON data formats. "
                       "AI algorithms process NLP tasks efficiently through these APIs."
            ),
            
            # Introduction section
            create_content_element(
                element_id="intro_heading",
                content_type=ContentType.HEADING,
                content="Introduction",
                metadata={"level": 2}
            ),
            
            create_content_element(
                element_id="intro_para1",
                content_type=ContentType.PARAGRAPH,
                content="Modern AI systems rely heavily on API integrations. "
                       "The HTTP protocol enables communication between ML services. "
                       "JSON format is commonly used for data exchange in REST APIs. " * 5
            ),
            
            create_content_element(
                element_id="intro_para2",
                content_type=ContentType.PARAGRAPH,
                content="Machine Learning algorithms require efficient data processing. "
                       "Natural Language Processing techniques analyze text data. "
                       "Computer Vision systems process image data through specialized APIs. " * 5
            ),
            
            # Technical Details section
            create_content_element(
                element_id="tech_heading",
                content_type=ContentType.HEADING,
                content="Technical Implementation",
                metadata={"level": 2}
            ),
            
            create_content_element(
                element_id="tech_para1",
                content_type=ContentType.PARAGRAPH,
                content="The SQL database stores configuration data for API endpoints. "
                       "XML configuration files define service parameters. "
                       "HTML interfaces provide user interaction capabilities. " * 8
            ),
            
            create_content_element(
                element_id="code_example",
                content_type=ContentType.CODE,
                content="# Example API call\nimport requests\nresponse = requests.get('/api/ml/predict')"
            ),
            
            # Business Impact section
            create_content_element(
                element_id="business_heading",
                content_type=ContentType.HEADING,
                content="Business Impact",
                metadata={"level": 2}
            ),
            
            create_content_element(
                element_id="business_para",
                content_type=ContentType.PARAGRAPH,
                content="The CEO emphasized the importance of API strategy for ROI improvement. "
                       "The CTO outlined technical requirements for system integration. "
                       "Market analysis shows significant revenue potential from API services. " * 6
            ),
            
            # Conclusion
            create_content_element(
                element_id="conclusion_heading",
                content_type=ContentType.HEADING,
                content="Conclusion",
                metadata={"level": 2}
            ),
            
            create_content_element(
                element_id="conclusion_para",
                content_type=ContentType.PARAGRAPH,
                content="API integration is crucial for modern ML systems. "
                       "Proper implementation ensures scalable and efficient AI solutions. "
                       "Future research should focus on optimizing API performance for NLP tasks. " * 4
            )
        ]
        
        # Create full text
        full_text = " ".join([elem.content for elem in content_elements])
        
        # Create markdown version
        markdown_lines = []
        for elem in content_elements:
            if elem.content_type == ContentType.HEADING:
                level = elem.metadata.get("level", 1)
                markdown_lines.append(f"{'#' * level} {elem.content}")
            elif elem.content_type == ContentType.CODE:
                markdown_lines.append(f"```\n{elem.content}\n```")
            else:
                markdown_lines.append(elem.content)
        
        markdown_text = "\n\n".join(markdown_lines)
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            document_metadata={
                "title": "API Integration Guide for ML Systems",
                "file_extension": ".pdf",
                "author": "Test Author"
            },
            document_structure=create_document_structure(
                total_elements=len(content_elements),
                total_pages=5,
                has_tables=False,
                has_images=False,
                language="en"
            ),
            processing_metadata=create_processing_metadata(
                source_file="api_ml_guide.pdf",
                processor_name="integration_test",
                processor_version="1.0.0",
                processing_duration=2.5
            ),
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=full_text,
            markdown_text=markdown_text
        )
    
    def test_complete_pipeline_technical_document(self):
        """Test the complete post-processing pipeline with a technical document."""
        document = self.create_complex_document()
        
        # Step 1: Route the document
        config, decision = self.router.route_document(document, "tech_doc_001")
        
        assert config is not None
        assert decision is not None
        assert len(config.methods) > 0
        assert decision.confidence > 0.0
        
        # Step 2: Expand abbreviations
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Verify abbreviations were expanded
        expanded_text = expanded_doc.plain_text
        technical_expansions = [
            "Application Programming Interface",
            "Machine Learning",
            "HyperText Transfer Protocol",
            "JavaScript Object Notation",
            "Representational State Transfer",
            "Artificial Intelligence",
            "Natural Language Processing"
        ]
        
        expansion_count = sum(1 for exp in technical_expansions if exp in expanded_text)
        assert expansion_count >= 4  # Should expand most technical abbreviations
        
        # Step 3: Chunk the document
        chunking_config = {
            "chunk_size": config.chunk_size or 150,
            "chunk_overlap": config.chunk_overlap or 20
        }
        chunker = DocumentChunker(config.chunking_strategy, chunking_config)
        chunks = chunker.chunk_document(expanded_doc)
        
        assert len(chunks) > 0
        
        # Verify chunks have proper structure
        for chunk in chunks:
            assert chunk.chunk_id is not None
            assert len(chunk.content) > 0
            assert chunk.metadata.word_count > 0
            assert chunk.metadata.character_count > 0
        
        # Step 4: Verify pipeline results
        pipeline_result = {
            "original_document": document,
            "expanded_document": expanded_doc,
            "chunks": chunks,
            "config": config,
            "decision": decision,
            "expansions": expansions
        }
        
        # Validate complete pipeline
        assert len(pipeline_result["chunks"]) > 0  # Should create chunks
        assert len(pipeline_result["expanded_document"].plain_text) > len(document.plain_text)  # Should be expanded
        assert len(pipeline_result["expansions"]) > 0  # Should have expansions
        
        return pipeline_result
    
    def test_pipeline_with_different_document_types(self):
        """Test pipeline with different document types."""
        document_types = [
            {
                "name": "academic_paper",
                "content_types": [
                    ContentType.HEADING,  # Title
                    ContentType.PARAGRAPH,  # Abstract with AI, ML, NLP
                    ContentType.HEADING,  # Introduction
                    ContentType.PARAGRAPH,  # Content with research terms
                    ContentType.HEADING,  # Methodology
                    ContentType.PARAGRAPH,  # Methods with PhD, MSc references
                    ContentType.HEADING,  # Results
                    ContentType.PARAGRAPH,  # Results content
                ],
                "text_content": "AI and ML research methodology. PhD students analyzed NLP techniques. CV algorithms process data efficiently.",
                "expected_domain": "academic"
            },
            {
                "name": "business_report",
                "content_types": [
                    ContentType.HEADING,  # Executive Summary
                    ContentType.PARAGRAPH,  # CEO and CTO discussion
                    ContentType.HEADING,  # Financial Analysis
                    ContentType.PARAGRAPH,  # ROI and revenue content
                ],
                "text_content": "The CEO and CTO discussed ROI improvements. API strategy will increase company revenue and market share.",
                "expected_domain": "business"
            },
            {
                "name": "technical_manual",
                "content_types": [
                    ContentType.HEADING,  # Configuration
                    ContentType.PARAGRAPH,  # Technical content
                    ContentType.CODE,  # Code examples
                    ContentType.PARAGRAPH,  # More technical content
                ],
                "text_content": "Configure the API using HTTP protocols. JSON data format with SQL database integration. XML configuration files.",
                "expected_domain": "technical"
            }
        ]
        
        results = {}
        
        for doc_type in document_types:
            # Create document
            content_elements = []
            for i, content_type in enumerate(doc_type["content_types"]):
                if content_type == ContentType.HEADING:
                    content = f"Section {i+1}"
                elif content_type == ContentType.CODE:
                    content = "# Sample code\nprint('Hello World')"
                else:
                    content = doc_type["text_content"] + " " * 10  # Repeat for length
                
                element = create_content_element(
                    element_id=f"elem_{i}",
                    content_type=content_type,
                    content=content,
                    metadata={"level": 1} if content_type == ContentType.HEADING else {}
                )
                content_elements.append(element)
            
            document = StandardizedDocumentOutput(
                content_elements=content_elements,
                document_metadata={"file_extension": ".pdf"},
                document_structure=create_document_structure(
                    total_elements=len(content_elements),
                    total_pages=3
                ),
                processing_metadata=create_processing_metadata(
                    source_file=f"{doc_type['name']}.pdf",
                    processor_name="test",
                    processor_version="1.0.0",
                    processing_duration=1.0
                ),
                processing_status=ProcessingStatus.SUCCESS,
                plain_text=" ".join([elem.content for elem in content_elements]),
                markdown_text=" ".join([elem.content for elem in content_elements])
            )
            
            # Process through pipeline
            config, decision = self.router.route_document(document, doc_type["name"])
            expanded_doc, expansions = self.expander.expand_abbreviations(document)
            chunking_config = {
                "chunk_size": config.chunk_size or 150,
                "chunk_overlap": config.chunk_overlap or 20
            }
            chunker = DocumentChunker(config.chunking_strategy, chunking_config)
            chunks = chunker.chunk_document(expanded_doc)
            
            results[doc_type["name"]] = {
                "config": config,
                "decision": decision,
                "expansions": expansions,
                "chunks": chunks,
                "expansion_count": len(expansions),
                "chunk_count": len(chunks)
            }
        
        # Verify all document types were processed
        assert len(results) == len(document_types)
        
        # Each document type should have some processing
        for doc_name, result in results.items():
            assert result["chunk_count"] > 0
            assert result["config"] is not None
            assert result["decision"].confidence > 0.0
        
        return results
    
    def test_pipeline_performance_with_large_document(self):
        """Test pipeline performance with a large document."""
        # Create a large document
        large_content_elements = []
        
        for section in range(10):  # 10 sections
            # Section heading
            large_content_elements.append(
                create_content_element(
                    element_id=f"heading_{section}",
                    content_type=ContentType.HEADING,
                    content=f"Section {section + 1}: API Integration Patterns",
                    metadata={"level": 2}
                )
            )
            
            # Multiple paragraphs per section
            for para in range(5):  # 5 paragraphs per section
                content = (
                    f"This is paragraph {para + 1} in section {section + 1}. "
                    "The API framework uses HTTP protocols for REST communication. "
                    "JSON data format enables efficient ML algorithm processing. "
                    "AI systems utilize NLP techniques for text analysis. "
                    "The SQL database stores configuration data for API endpoints. "
                ) * 20  # Make each paragraph substantial
                
                large_content_elements.append(
                    create_content_element(
                        element_id=f"para_{section}_{para}",
                        content_type=ContentType.PARAGRAPH,
                        content=content
                    )
                )
        
        # Create large document
        full_text = " ".join([elem.content for elem in large_content_elements])
        
        large_document = StandardizedDocumentOutput(
            content_elements=large_content_elements,
            document_metadata={"file_extension": ".pdf", "title": "Large API Guide"},
            document_structure=create_document_structure(
                total_elements=len(large_content_elements),
                total_pages=50,
                has_tables=False,
                has_images=False
            ),
            processing_metadata=create_processing_metadata(
                source_file="large_api_guide.pdf",
                processor_name="performance_test",
                processor_version="1.0.0",
                processing_duration=10.0
            ),
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=full_text,
            markdown_text=full_text
        )
        
        # Process through pipeline
        import time
        
        start_time = time.time()
        
        # Route document
        config, decision = self.router.route_document(large_document, "large_doc")
        routing_time = time.time() - start_time
        
        # Expand abbreviations
        abbrev_start = time.time()
        expanded_doc, expansions = self.expander.expand_abbreviations(large_document)
        expansion_time = time.time() - abbrev_start
        
        # Chunk document
        chunk_start = time.time()
        chunking_config = {
            "chunk_size": config.chunk_size or 150,
            "chunk_overlap": config.chunk_overlap or 20
        }
        chunker = DocumentChunker(config.chunking_strategy, chunking_config)
        chunks = chunker.chunk_document(expanded_doc)
        chunking_time = time.time() - chunk_start
        
        total_time = time.time() - start_time
        
        # Performance assertions
        assert routing_time < 1.0  # Routing should be fast
        assert expansion_time < 5.0  # Expansion should be reasonable
        assert chunking_time < 3.0  # Chunking should be efficient
        assert total_time < 10.0  # Total processing should be reasonable
        
        # Quality assertions
        assert len(chunks) > 20  # Should create many chunks for large document
        assert len(expansions) > 10  # Should find many abbreviations
        assert decision.confidence > 0.0
        
        # Verify processing quality
        total_original_length = len(large_document.plain_text)
        total_expanded_length = len(expanded_doc.plain_text)
        assert total_expanded_length >= total_original_length  # Should be expanded
        
        return {
            "performance": {
                "routing_time": routing_time,
                "expansion_time": expansion_time,
                "chunking_time": chunking_time,
                "total_time": total_time
            },
            "quality": {
                "chunk_count": len(chunks),
                "expansion_count": len(expansions),
                "confidence": decision.confidence,
                "expansion_ratio": total_expanded_length / total_original_length
            }
        }
    
    def test_pipeline_error_handling_and_recovery(self):
        """Test pipeline error handling and recovery mechanisms."""
        # Test with problematic documents
        problematic_documents = [
            # Empty document
            StandardizedDocumentOutput(
                content_elements=[],
                document_metadata={},
                document_structure=create_document_structure(total_elements=0),
                processing_metadata=create_processing_metadata(
                    source_file="empty.pdf",
                    processor_name="test",
                    processor_version="1.0.0",
                    processing_duration=0.1
                ),
                processing_status=ProcessingStatus.SUCCESS,
                plain_text="",
                markdown_text=""
            ),
            
            # Document with only special characters
            StandardizedDocumentOutput(
                content_elements=[
                    create_content_element(
                        element_id="special",
                        content_type=ContentType.PARAGRAPH,
                        content="!@#$%^&*()_+-=[]{}|;':\",./<>?"
                    )
                ],
                document_metadata={},
                document_structure=create_document_structure(total_elements=1),
                processing_metadata=create_processing_metadata(
                    source_file="special.pdf",
                    processor_name="test",
                    processor_version="1.0.0",
                    processing_duration=0.1
                ),
                processing_status=ProcessingStatus.SUCCESS,
                plain_text="!@#$%^&*()_+-=[]{}|;':\",./<>?",
                markdown_text="!@#$%^&*()_+-=[]{}|;':\",./<>?"
            ),
            
            # Document with very long single paragraph
            StandardizedDocumentOutput(
                content_elements=[
                    create_content_element(
                        element_id="long",
                        content_type=ContentType.PARAGRAPH,
                        content="Very long paragraph. " * 1000  # 3000 words
                    )
                ],
                document_metadata={},
                document_structure=create_document_structure(total_elements=1),
                processing_metadata=create_processing_metadata(
                    source_file="long.pdf",
                    processor_name="test",
                    processor_version="1.0.0",
                    processing_duration=0.1
                ),
                processing_status=ProcessingStatus.SUCCESS,
                plain_text="Very long paragraph. " * 1000,
                markdown_text="Very long paragraph. " * 1000
            )
        ]
        
        results = []
        
        for i, document in enumerate(problematic_documents):
            try:
                # Process through pipeline
                config, decision = self.router.route_document(document, f"problem_doc_{i}")
                expanded_doc, expansions = self.expander.expand_abbreviations(document)
                chunker = DocumentChunker(config.chunking_strategy, config.chunking_config)
                chunks = chunker.chunk_document(expanded_doc)
                
                results.append({
                    "success": True,
                    "config": config,
                    "decision": decision,
                    "expansions": len(expansions),
                    "chunks": len(chunks),
                    "error": None
                })
                
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "config": None,
                    "decision": None,
                    "expansions": 0,
                    "chunks": 0
                })
        
        # All documents should be handled gracefully (no crashes)
        assert len(results) == len(problematic_documents)
        
        # Most should succeed (robust error handling)
        success_count = sum(1 for r in results if r["success"])
        assert success_count >= len(problematic_documents) * 0.8  # At least 80% success rate
        
        return results
    
    def test_pipeline_configuration_variations(self):
        """Test pipeline with different configuration variations."""
        document = self.create_complex_document()
        
        # Test different chunking strategies
        strategies = [
            ChunkingStrategy.PARAGRAPH,
            ChunkingStrategy.SENTENCE,
            ChunkingStrategy.SECTION_BASED,
            ChunkingStrategy.SEMANTIC
        ]
        
        results = {}
        
        for strategy in strategies:
            try:
                # Create custom config
                config = PostProcessingConfig(
                    methods=[ProcessingMethod.PARAGRAPH_CHUNKING, ProcessingMethod.ABBREVIATION_EXPANSION],
                    chunking_strategy=strategy,
                    chunk_size=150,
                    chunk_overlap=20,
                    enable_abbreviation_expansion=True,
                    abbreviation_domains=["technical", "academic"]
                )
                
                # Process with custom config
                expanded_doc, expansions = self.expander.expand_abbreviations(
                    document,
                    domains=config.abbreviation_domains,
                    confidence_threshold=0.7
                )
                
                chunking_config = {
                    "chunk_size": config.chunk_size or 150,
                    "chunk_overlap": config.chunk_overlap or 20
                }
                chunker = DocumentChunker(strategy, chunking_config)
                chunks = chunker.chunk_document(expanded_doc)
                
                results[strategy.value] = {
                    "success": True,
                    "chunk_count": len(chunks),
                    "expansion_count": len(expansions),
                    "avg_chunk_size": sum(chunk.metadata.word_count for chunk in chunks) / len(chunks) if chunks else 0
                }
                
            except Exception as e:
                results[strategy.value] = {
                    "success": False,
                    "error": str(e),
                    "chunk_count": 0,
                    "expansion_count": 0,
                    "avg_chunk_size": 0
                }
        
        # All strategies should work
        success_count = sum(1 for r in results.values() if r["success"])
        assert success_count >= len(strategies) * 0.75  # At least 75% should work
        
        # Different strategies should produce different results
        chunk_counts = [r["chunk_count"] for r in results.values() if r["success"]]
        if len(chunk_counts) > 1:
            assert len(set(chunk_counts)) > 1  # Should have variation in chunk counts
        
        return results