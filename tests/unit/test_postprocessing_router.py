"""Tests for post-processing router."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.postprocessing.router import PostProcessingRouter, PostProcessKnowledgeManagementDB
from src.docforge.postprocessing.schemas import (
    ProcessingMethod,
    KnowledgeManagementRule,
    ChunkingStrategy
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


class TestPostProcessKnowledgeManagementDB:
    """Test the Knowledge Management Database."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_km.json")
        self.km_db = PostProcessKnowledgeManagementDB(self.db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization_with_default_rules(self):
        """Test that KM DB initializes with default rules."""
        assert len(self.km_db.rules) > 0
        
        # Check that default rules exist
        rule_names = [rule.name for rule in self.km_db.rules]
        assert "Default Processing" in rule_names
        assert "Academic Paper Processing" in rule_names
    
    def test_add_rule(self):
        """Test adding a new rule."""
        initial_count = len(self.km_db.rules)
        
        new_rule = KnowledgeManagementRule(
            rule_id="test_rule",
            name="Test Rule",
            description="A test rule",
            conditions={"test_condition": True},
            actions=[ProcessingMethod.PARAGRAPH_CHUNKING]
        )
        
        self.km_db.add_rule(new_rule)
        
        assert len(self.km_db.rules) == initial_count + 1
        assert any(rule.rule_id == "test_rule" for rule in self.km_db.rules)
    
    def test_get_applicable_rules(self):
        """Test getting applicable rules for document features."""
        features = {
            "file_type": "pdf",
            "has_headings": True,
            "heading_levels": [1, 2, 3],
            "min_pages": 5
        }
        
        applicable_rules = self.km_db.get_applicable_rules(features)
        
        # Should get at least the default rule
        assert len(applicable_rules) > 0
        
        # Rules should be sorted by priority
        if len(applicable_rules) > 1:
            for i in range(len(applicable_rules) - 1):
                assert applicable_rules[i].priority >= applicable_rules[i + 1].priority
    
    def test_rule_matching(self):
        """Test rule matching logic."""
        # Test exact match
        rule = KnowledgeManagementRule(
            rule_id="exact_match",
            name="Exact Match",
            description="Test exact matching",
            conditions={"file_type": "pdf"},
            actions=[ProcessingMethod.PARAGRAPH_CHUNKING]
        )
        
        features = {"file_type": "pdf"}
        assert self.km_db._rule_matches(rule, features)
        
        features = {"file_type": "docx"}
        assert not self.km_db._rule_matches(rule, features)
        
        # Test boolean condition
        rule.conditions = {"has_headings": True}
        features = {"has_headings": True}
        assert self.km_db._rule_matches(rule, features)
        
        features = {"has_headings": False}
        assert not self.km_db._rule_matches(rule, features)


class TestPostProcessingRouter:
    """Test the post-processing router."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_router_km.json")
        self.router = PostProcessingRouter(self.db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_document(self, content_types: list = None) -> StandardizedDocumentOutput:
        """Create a test document for routing."""
        if content_types is None:
            content_types = [ContentType.HEADING, ContentType.PARAGRAPH, ContentType.PARAGRAPH]
        
        content_elements = []
        for i, content_type in enumerate(content_types):
            element = create_content_element(
                element_id=f"element_{i+1}",
                content_type=content_type,
                content=f"Test content {i+1}",
                metadata={"level": 1} if content_type == ContentType.HEADING else {}
            )
            content_elements.append(element)
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(content_elements),
            total_pages=1
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            document_metadata={"file_extension": ".pdf"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test heading. Test paragraph 1. Test paragraph 2.",
            markdown_text="# Test heading\\n\\nTest paragraph 1.\\n\\nTest paragraph 2."
        )
    
    def test_route_document_basic(self):
        """Test basic document routing."""
        document = self.create_test_document()
        
        config, decision = self.router.route_document(document, "test_doc_1")
        
        # Should return valid configuration and decision
        assert config is not None
        assert decision is not None
        assert len(config.methods) > 0
        assert decision.document_id == "test_doc_1"
        assert len(decision.selected_methods) > 0
        assert 0.0 <= decision.confidence <= 1.0
    
    def test_route_academic_paper(self):
        """Test routing of academic paper-like document."""
        # Create document with academic paper characteristics
        content_types = [
            ContentType.HEADING,  # Title
            ContentType.PARAGRAPH,  # Abstract
            ContentType.HEADING,  # Introduction
            ContentType.PARAGRAPH,  # Content
            ContentType.HEADING,  # Methodology
            ContentType.PARAGRAPH,  # Content
            ContentType.HEADING,  # Results
            ContentType.PARAGRAPH,  # Content
            ContentType.HEADING,  # Conclusion
            ContentType.PARAGRAPH   # Content
        ]
        
        document = self.create_test_document(content_types)
        document.document_structure.total_pages = 10
        document.plain_text = "Abstract Introduction Methodology Results Conclusion " * 20
        
        config, decision = self.router.route_document(document, "academic_paper")
        
        # Should select appropriate methods for academic papers
        assert ProcessingMethod.SECTION_CHUNKING in config.methods or ProcessingMethod.PARAGRAPH_CHUNKING in config.methods
        assert config.chunking_strategy in [ChunkingStrategy.SECTION_BASED, ChunkingStrategy.PARAGRAPH]
    
    def test_route_technical_document(self):
        """Test routing of technical document."""
        document = self.create_test_document([
            ContentType.HEADING,
            ContentType.PARAGRAPH,
            ContentType.CODE,
            ContentType.PARAGRAPH
        ])
        
        # Add technical terms
        document.plain_text = "API configuration database implementation framework algorithm"
        
        config, decision = self.router.route_document(document, "technical_doc")
        
        # Should handle technical documents appropriately
        assert len(config.methods) > 0
        assert decision.confidence > 0.0
    
    def test_feature_extraction(self):
        """Test document feature extraction."""
        document = self.create_test_document([
            ContentType.HEADING,
            ContentType.PARAGRAPH,
            ContentType.LIST,
            ContentType.PARAGRAPH
        ])
        
        features = self.router._extract_document_features(document)
        
        # Check that features are extracted
        assert "file_type" in features
        assert "has_headings" in features
        assert "has_lists" in features
        assert "has_paragraphs" in features
        assert "word_count" in features
        assert "page_count" in features
        
        # Verify feature values
        assert features["has_headings"] is True
        assert features["has_lists"] is True
        assert features["has_paragraphs"] is True
        assert features["file_type"] == "pdf"
    
    def test_abbreviation_density_calculation(self):
        """Test abbreviation density calculation."""
        document = self.create_test_document()
        document.plain_text = "The API uses HTTP and JSON for REST communication with the DB"
        
        density = self.router._extract_abbreviation_density(document)
        
        # Should detect API, HTTP, JSON, REST, DB as abbreviations
        assert density > 0.0
        assert density <= 1.0
    
    def test_user_preferences(self):
        """Test routing with user preferences."""
        document = self.create_test_document()
        
        user_preferences = {
            "preferred_chunking": "sentence",
            "enable_abbreviation_expansion": True
        }
        
        config, decision = self.router.route_document(
            document, 
            "user_pref_doc", 
            user_preferences
        )
        
        # User preferences should influence the decision
        assert config is not None
        assert decision is not None
    
    def test_processing_statistics(self):
        """Test getting processing statistics."""
        # Route a few documents to generate statistics
        for i in range(3):
            document = self.create_test_document()
            self.router.route_document(document, f"stats_doc_{i}")
        
        stats = self.router.get_processing_statistics()
        
        assert "total_decisions" in stats
        assert stats["total_decisions"] == 3
        assert "method_usage" in stats
        assert "rule_usage" in stats
        assert "average_confidence" in stats
        assert "total_rules" in stats
    
    def test_empty_document_handling(self):
        """Test handling of empty or minimal documents."""
        # Create minimal document
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=0,
            total_pages=1
        )
        
        document = StandardizedDocumentOutput(
            content_elements=[],
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="",
            markdown_text=""
        )
        
        config, decision = self.router.route_document(document, "empty_doc")
        
        # Should handle empty documents gracefully
        assert config is not None
        assert decision is not None
        assert len(config.methods) > 0  # Should at least get default processing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])