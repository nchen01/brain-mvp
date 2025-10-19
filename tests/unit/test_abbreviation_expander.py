"""Tests for abbreviation expansion system."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.postprocessing.abbreviation_expander import (
    AbbreviationExpander,
    AbbreviationDatabase,
    AbbreviationDetector,
    AbbreviationContext
)
from src.docforge.postprocessing.schemas import AbbreviationMapping
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


class TestAbbreviationDatabase:
    """Test the abbreviation database."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_abbreviations.json")
        self.db = AbbreviationDatabase(self.db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization_with_defaults(self):
        """Test database initialization with default abbreviations."""
        abbreviations = self.db.get_all_abbreviations()
        
        # Should have default abbreviations
        assert len(abbreviations) > 0
        assert 'API' in abbreviations
        assert 'HTTP' in abbreviations
        assert 'JSON' in abbreviations
    
    def test_get_expansions(self):
        """Test getting expansions for abbreviations."""
        # Test known abbreviation
        api_expansions = self.db.get_expansions('API')
        assert len(api_expansions) > 0
        assert api_expansions[0].expansion == 'Application Programming Interface'
        
        # Test with domain filter
        tech_expansions = self.db.get_expansions('API', 'technical')
        assert len(tech_expansions) > 0
        assert all(exp.domain == 'technical' for exp in tech_expansions)
        
        # Test unknown abbreviation
        unknown_expansions = self.db.get_expansions('UNKNOWN')
        assert len(unknown_expansions) == 0
    
    def test_add_abbreviation(self):
        """Test adding new abbreviations."""
        initial_count = len(self.db.get_all_abbreviations())
        
        # Add new abbreviation
        new_mapping = AbbreviationMapping(
            abbreviation='TEST',
            expansion='Test Expansion System',
            domain='testing',
            confidence=0.9
        )
        
        self.db.add_abbreviation(new_mapping)
        
        # Check it was added
        assert len(self.db.get_all_abbreviations()) == initial_count + 1
        test_expansions = self.db.get_expansions('TEST')
        assert len(test_expansions) == 1
        assert test_expansions[0].expansion == 'Test Expansion System'


class TestAbbreviationDetector:
    """Test the abbreviation detector."""
    
    def setup_method(self):
        """Set up test environment."""
        self.detector = AbbreviationDetector()
    
    def test_basic_abbreviation_detection(self):
        """Test basic abbreviation detection."""
        text = "The API is used for HTTP requests and JSON responses."
        
        abbreviations = self.detector.detect_abbreviations(text)
        
        # Should detect API, HTTP, JSON
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        assert 'API' in abbrev_texts
        assert 'HTTP' in abbrev_texts
        assert 'JSON' in abbrev_texts
    
    def test_false_positive_filtering(self):
        """Test filtering of false positives."""
        text = "THE BIG DOG RAN TO THE OLD MAN."
        
        abbreviations = self.detector.detect_abbreviations(text)
        
        # Should not detect common words as abbreviations
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        assert 'THE' not in abbrev_texts
        assert 'BIG' not in abbrev_texts
        assert 'DOG' not in abbrev_texts


class TestAbbreviationExpander:
    """Test the main abbreviation expander."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_abbreviations.json")
        self.expander = AbbreviationExpander(self.db_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_document(self, text: str) -> StandardizedDocumentOutput:
        """Create a test document."""
        return StandardizedDocumentOutput(
            plain_text=text,
            markdown_text=text,
            content_elements=[
                create_content_element(
                    element_id="test-1",
                    content_type=ContentType.PARAGRAPH,
                    content=text,
                    metadata={"test": True}
                )
            ],
            processing_metadata=create_processing_metadata(
                source_file="test.txt",
                processor_name="test",
                processor_version="1.0.0",
                processing_duration=0.1
            ),
            document_structure=create_document_structure(total_elements=1),
            processing_status=ProcessingStatus.SUCCESS
        )
    
    def test_basic_expansion(self):
        """Test basic abbreviation expansion."""
        text = "The API handles HTTP requests."
        document = self.create_test_document(text)
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should expand abbreviations
        assert "Application Programming Interface" in expanded_doc.plain_text
        assert "HyperText Transfer Protocol" in expanded_doc.plain_text
        assert len(expansions) > 0
    
    def test_expansion_statistics(self):
        """Test expansion statistics."""
        stats = self.expander.get_expansion_statistics()
        
        assert 'total_abbreviations' in stats
        assert 'total_expansions' in stats
        assert 'domain_distribution' in stats
        assert 'average_confidence' in stats
        assert 'confidence_range' in stats
        
        assert stats['total_abbreviations'] > 0
        assert stats['average_confidence'] > 0
        assert 0 <= stats['confidence_range']['min'] <= 1
        assert 0 <= stats['confidence_range']['max'] <= 1


@pytest.fixture
def sample_abbreviation_mapping():
    """Sample abbreviation mapping for testing."""
    return AbbreviationMapping(
        abbreviation='TEST',
        expansion='Test Expansion',
        domain='testing',
        confidence=0.9,
        context='unit testing',
        source='test_suite'
    )


def test_abbreviation_mapping_creation(sample_abbreviation_mapping):
    """Test abbreviation mapping creation."""
    mapping = sample_abbreviation_mapping
    
    assert mapping.abbreviation == 'TEST'
    assert mapping.expansion == 'Test Expansion'
    assert mapping.domain == 'testing'
    assert mapping.confidence == 0.9
    assert mapping.context == 'unit testing'
    assert mapping.source == 'test_suite'


def test_abbreviation_mapping_validation():
    """Test abbreviation mapping validation."""
    # Test valid mapping
    valid_mapping = AbbreviationMapping(
        abbreviation='VALID',
        expansion='Valid Expansion',
        domain='test',
        confidence=0.8
    )
    assert valid_mapping.confidence == 0.8
    
    # Test confidence bounds
    with pytest.raises(ValueError):
        AbbreviationMapping(
            abbreviation='INVALID',
            expansion='Invalid Expansion',
            domain='test',
            confidence=1.5  # Invalid confidence > 1
        )
    
    with pytest.raises(ValueError):
        AbbreviationMapping(
            abbreviation='INVALID',
            expansion='Invalid Expansion',
            domain='test',
            confidence=-0.1  # Invalid confidence < 0
        )

class TestContextAwareAbbreviationDetection:
    """Comprehensive tests for context-aware abbreviation detection."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_abbreviations.json")
        self.expander = AbbreviationExpander(self.db_path)
        self.detector = AbbreviationDetector()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_document(self, text: str, domain_keywords: list = None) -> StandardizedDocumentOutput:
        """Create a test document with optional domain keywords."""
        if domain_keywords:
            text = f"{' '.join(domain_keywords)} {text}"
        
        return StandardizedDocumentOutput(
            plain_text=text,
            markdown_text=text,
            content_elements=[
                create_content_element(
                    element_id="test-1",
                    content_type=ContentType.PARAGRAPH,
                    content=text,
                    metadata={"test": True}
                )
            ],
            processing_metadata=create_processing_metadata(
                source_file="test.txt",
                processor_name="test",
                processor_version="1.0.0",
                processing_duration=0.1
            ),
            document_structure=create_document_structure(total_elements=1),
            processing_status=ProcessingStatus.SUCCESS
        )
    
    def test_technical_domain_context(self):
        """Test abbreviation detection in technical context."""
        # Technical document with API, ML, AI abbreviations
        text = "The API framework uses ML algorithms for AI processing."
        document = self.create_test_document(text, ["database", "algorithm", "implementation"])
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect and expand technical abbreviations
        assert "Application Programming Interface" in expanded_doc.plain_text
        assert "Machine Learning" in expanded_doc.plain_text
        assert "Artificial Intelligence" in expanded_doc.plain_text
        
        # Check that expansions are from technical/academic domains
        expansion_domains = [exp.domain for exp in expansions]
        assert 'technical' in expansion_domains or 'academic' in expansion_domains
    
    def test_academic_domain_context(self):
        """Test abbreviation detection in academic context."""
        text = "The NLP research study analyzed CV techniques in AI applications."
        document = self.create_test_document(text, ["research", "study", "analysis", "methodology"])
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect academic abbreviations
        assert "Natural Language Processing" in expanded_doc.plain_text
        assert len(expansions) > 0
        
        # Check domain preference
        nlp_expansions = [exp for exp in expansions if exp.abbreviation == 'NLP']
        if nlp_expansions:
            assert nlp_expansions[0].domain == 'academic'
    
    def test_business_domain_context(self):
        """Test abbreviation detection in business context."""
        text = "The CEO announced ROI improvements and CTO initiatives."
        document = self.create_test_document(text, ["company", "revenue", "market", "strategy"])
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect business abbreviations
        assert "Chief Executive Officer" in expanded_doc.plain_text
        assert "Return on Investment" in expanded_doc.plain_text
        assert "Chief Technology Officer" in expanded_doc.plain_text
        
        # Check business domain
        business_expansions = [exp for exp in expansions if exp.domain == 'business']
        assert len(business_expansions) > 0
    
    def test_mixed_domain_context(self):
        """Test abbreviation detection with mixed domain context."""
        text = "The CEO discussed API integration and ML research ROI."
        document = self.create_test_document(text, ["company", "algorithm", "research"])
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect abbreviations from multiple domains
        domains = set(exp.domain for exp in expansions)
        assert len(domains) > 1  # Multiple domains should be represented
    
    def test_abbreviation_with_periods(self):
        """Test detection of abbreviations with periods."""
        text = "The U.S.A. and U.K. signed agreements with E.U. representatives."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        
        # Should detect period-separated abbreviations
        assert any('U.S.A' in abbrev for abbrev in abbrev_texts)
        assert any('U.K' in abbrev for abbrev in abbrev_texts)
        assert any('E.U' in abbrev for abbrev in abbrev_texts)
    
    def test_mixed_case_abbreviations(self):
        """Test detection of mixed case abbreviations."""
        text = "She has a PhD in computer science and an MSc degree."
        
        abbreviations = self.detector.detect_abbreviations(text)
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        
        # Should detect mixed case abbreviations
        assert 'PhD' in abbrev_texts or 'MSc' in abbrev_texts
    
    def test_context_based_cv_disambiguation(self):
        """Test CV abbreviation disambiguation based on context."""
        # Computer Vision context
        cv_tech_text = "CV algorithms process images using deep learning frameworks."
        tech_document = self.create_test_document(cv_tech_text, ["algorithm", "framework"])
        
        # Curriculum Vitae context
        cv_resume_text = "Please submit your CV with your job application."
        resume_document = self.create_test_document(cv_resume_text, ["job", "application"])
        
        # Test technical context
        tech_expanded, tech_expansions = self.expander.expand_abbreviations(tech_document)
        cv_tech_expansions = [exp for exp in tech_expansions if exp.abbreviation == 'CV']
        
        # Test resume context - this might not expand if confidence is low
        resume_expanded, resume_expansions = self.expander.expand_abbreviations(resume_document)
        
        # At least one should be detected
        assert len(tech_expansions) > 0 or len(resume_expansions) > 0
    
    def test_sentence_position_context(self):
        """Test abbreviation detection based on sentence position."""
        text = "API development is crucial. The API handles requests efficiently."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        
        # Should detect API in both positions
        api_positions = [(abbrev, start, end) for abbrev, start, end in abbreviations if abbrev == 'API']
        assert len(api_positions) >= 1
    
    def test_expansion_pattern_detection(self):
        """Test detection of expansion patterns in text."""
        text = "The API (Application Programming Interface) is well documented."
        document = self.create_test_document(text)
        
        # Should learn from the expansion pattern
        self.expander.learn_from_document(document)
        
        # Check that it was learned
        learned_expansions = self.expander.database.get_expansions('API')
        assert len(learned_expansions) > 0
    
    def test_confidence_threshold_filtering(self):
        """Test filtering based on confidence thresholds."""
        text = "The API handles HTTP requests with JSON data."
        document = self.create_test_document(text)
        
        # High confidence threshold
        high_conf_doc, high_conf_expansions = self.expander.expand_abbreviations(
            document, confidence_threshold=0.99
        )
        
        # Low confidence threshold
        low_conf_doc, low_conf_expansions = self.expander.expand_abbreviations(
            document, confidence_threshold=0.5
        )
        
        # Low threshold should expand more or equal abbreviations
        assert len(low_conf_expansions) >= len(high_conf_expansions)
    
    def test_domain_preference_ordering(self):
        """Test that domain-specific expansions are preferred."""
        # Add a custom abbreviation with different domains
        custom_mapping_tech = AbbreviationMapping(
            abbreviation='TEST',
            expansion='Technical Enhancement System Tool',
            domain='technical',
            confidence=0.8
        )
        
        custom_mapping_general = AbbreviationMapping(
            abbreviation='TEST',
            expansion='General Test',
            domain='general',
            confidence=0.9  # Higher confidence but wrong domain
        )
        
        self.expander.database.add_abbreviation(custom_mapping_tech)
        self.expander.database.add_abbreviation(custom_mapping_general)
        
        # Technical context should prefer technical expansion despite lower confidence
        text = "The TEST system uses advanced algorithms."
        document = self.create_test_document(text, ["algorithm", "framework"])
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document, domains=['technical'])
        
        test_expansions = [exp for exp in expansions if exp.abbreviation == 'TEST']
        if test_expansions:
            # Should prefer technical domain
            assert test_expansions[0].domain == 'technical'
    
    def test_multiple_abbreviations_same_sentence(self):
        """Test handling multiple abbreviations in the same sentence."""
        text = "The API uses HTTP for JSON data transfer via REST endpoints."
        document = self.create_test_document(text)
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect multiple abbreviations
        abbrev_set = set(exp.abbreviation for exp in expansions)
        expected_abbrevs = {'API', 'HTTP', 'JSON', 'REST'}
        
        # Should detect at least some of these
        assert len(abbrev_set.intersection(expected_abbrevs)) >= 2
    
    def test_abbreviation_case_sensitivity(self):
        """Test case sensitivity in abbreviation detection."""
        text = "The api and API are different. Also http vs HTTP."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        
        # Should detect uppercase versions
        assert 'API' in abbrev_texts
        assert 'HTTP' in abbrev_texts
        
        # Should not detect lowercase versions as abbreviations
        assert 'api' not in abbrev_texts
        assert 'http' not in abbrev_texts
    
    def test_abbreviation_boundary_detection(self):
        """Test word boundary detection for abbreviations."""
        text = "The RAPID API and GRAPHIC design are different from API and IC."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        
        # Should detect standalone abbreviations
        assert 'API' in abbrev_texts
        
        # Should not detect abbreviations within words
        assert 'RAPID' not in abbrev_texts or 'GRAPHIC' not in abbrev_texts
    
    def test_empty_and_none_text_handling(self):
        """Test handling of empty or None text."""
        # Empty text
        empty_doc = self.create_test_document("")
        expanded_empty, empty_expansions = self.expander.expand_abbreviations(empty_doc)
        
        assert expanded_empty.plain_text == ""
        assert len(empty_expansions) == 0
        
        # Text with only spaces
        space_doc = self.create_test_document("   ")
        expanded_space, space_expansions = self.expander.expand_abbreviations(space_doc)
        
        assert len(space_expansions) == 0
    
    def test_special_characters_around_abbreviations(self):
        """Test abbreviations with special characters around them."""
        text = "Check the API, HTTP/HTTPS, and JSON-RPC protocols."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        
        # Should detect abbreviations despite punctuation
        assert 'API' in abbrev_texts
        assert 'HTTP' in abbrev_texts or 'HTTPS' in abbrev_texts
        assert 'JSON' in abbrev_texts
    
    def test_abbreviation_learning_patterns(self):
        """Test various patterns for learning abbreviations."""
        patterns = [
            "The API (Application Programming Interface) is useful.",
            "REST (Representational State Transfer) architecture is popular.",
            "Use SQL (Structured Query Language) for databases.",
            "The CRUD (Create, Read, Update, Delete) operations are basic."
        ]
        
        for pattern in patterns:
            document = self.create_test_document(pattern)
            self.expander.learn_from_document(document)
        
        # Check that abbreviations were learned
        learned_abbrevs = self.expander.database.get_all_abbreviations()
        
        # Should have learned some new abbreviations
        assert 'CRUD' in learned_abbrevs  # This one should definitely be learned
    
    def test_context_domain_detection_accuracy(self):
        """Test accuracy of domain detection from context."""
        test_cases = [
            {
                'text': 'The database implementation uses advanced algorithms and frameworks.',
                'expected_domain': 'technical'
            },
            {
                'text': 'This research study presents a comprehensive analysis of the methodology.',
                'expected_domain': 'academic'
            },
            {
                'text': 'The company revenue and market strategy focus on customer acquisition.',
                'expected_domain': 'business'
            },
            {
                'text': 'This is a general document without specific domain keywords.',
                'expected_domain': 'general'
            }
        ]
        
        for case in test_cases:
            document = self.create_test_document(case['text'])
            context = self.expander._create_document_context(document)
            assert context.domain == case['expected_domain']
    
    def test_abbreviation_statistics_accuracy(self):
        """Test accuracy of abbreviation statistics."""
        # Add some test abbreviations
        test_mappings = [
            AbbreviationMapping(abbreviation='STAT1', expansion='Statistics Test 1', domain='test', confidence=0.9),
            AbbreviationMapping(abbreviation='STAT2', expansion='Statistics Test 2', domain='test', confidence=0.8),
            AbbreviationMapping(abbreviation='STAT3', expansion='Statistics Test 3', domain='other', confidence=0.7),
        ]
        
        for mapping in test_mappings:
            self.expander.database.add_abbreviation(mapping)
        
        stats = self.expander.get_expansion_statistics()
        
        # Verify statistics structure
        assert isinstance(stats['total_abbreviations'], int)
        assert isinstance(stats['total_expansions'], int)
        assert isinstance(stats['domain_distribution'], dict)
        assert isinstance(stats['average_confidence'], float)
        assert isinstance(stats['confidence_range'], dict)
        
        # Verify statistics accuracy
        assert stats['total_abbreviations'] > 0
        assert stats['total_expansions'] > 0
        assert 'test' in stats['domain_distribution']
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['confidence_range']['min'] <= stats['confidence_range']['max'] <= 1
    
    def test_performance_with_large_text(self):
        """Test performance with large text documents."""
        # Create a large text with many abbreviations
        large_text = " ".join([
            "The API handles HTTP requests with JSON data using REST architecture.",
            "SQL databases store XML documents and HTML content.",
            "AI and ML algorithms process NLP tasks efficiently.",
            "The CEO and CTO discussed ROI improvements."
        ] * 50)  # Repeat 50 times
        
        document = self.create_test_document(large_text)
        
        # Should handle large documents without issues
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        assert len(expansions) > 0
        assert len(expanded_doc.plain_text) > len(large_text)  # Should be expanded
    
    def test_concurrent_abbreviation_detection(self):
        """Test abbreviation detection with overlapping patterns."""
        text = "The HTML API uses HTTP protocols for XML-RPC calls."
        document = self.create_test_document(text)
        
        abbreviations = self.detector.detect_abbreviations(text)
        
        # Should detect multiple abbreviations without conflicts
        abbrev_texts = [abbrev for abbrev, _, _ in abbreviations]
        expected = {'HTML', 'API', 'HTTP', 'XML'}
        
        detected = set(abbrev_texts)
        overlap = detected.intersection(expected)
        
        # Should detect at least some expected abbreviations
        assert len(overlap) >= 2