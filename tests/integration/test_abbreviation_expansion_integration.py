"""Integration tests for abbreviation expansion system."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.postprocessing.abbreviation_expander import AbbreviationExpander
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


class TestAbbreviationExpansionIntegration:
    """Integration tests for the complete abbreviation expansion pipeline."""
    
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
    
    def create_document(self, text: str, content_elements: list = None) -> StandardizedDocumentOutput:
        """Create a test document with multiple content elements."""
        if content_elements is None:
            content_elements = [
                create_content_element(
                    element_id="para-1",
                    content_type=ContentType.PARAGRAPH,
                    content=text
                )
            ]
        
        return StandardizedDocumentOutput(
            plain_text=text,
            markdown_text=text,
            content_elements=content_elements,
            processing_metadata=create_processing_metadata(
                source_file="test_document.pdf",
                processor_name="integration_test",
                processor_version="1.0.0",
                processing_duration=0.5
            ),
            document_structure=create_document_structure(total_elements=len(content_elements)),
            processing_status=ProcessingStatus.SUCCESS
        )
    
    def test_technical_document_expansion(self):
        """Test expansion in a technical document with multiple domains."""
        # Technical document with various abbreviations
        text = """
        The API framework integrates with SQL databases using REST architecture.
        Our ML algorithms process JSON data through HTTP endpoints.
        The system uses XML for configuration and HTML for the UI.
        """
        
        # Add technical context keywords
        technical_text = f"This technical implementation uses advanced algorithms and database frameworks. {text}"
        
        document = self.create_document(technical_text)
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Verify technical abbreviations were expanded
        expected_expansions = {
            'API': 'Application Programming Interface',
            'SQL': 'Structured Query Language',
            'REST': 'Representational State Transfer',
            'ML': 'Machine Learning',
            'JSON': 'JavaScript Object Notation',
            'HTTP': 'HyperText Transfer Protocol',
            'XML': 'eXtensible Markup Language'
        }
        
        expanded_text = expanded_doc.plain_text
        expansion_count = 0
        
        for abbrev, full_form in expected_expansions.items():
            if full_form in expanded_text:
                expansion_count += 1
        
        # Should expand most technical abbreviations
        assert expansion_count >= 4
        assert len(expansions) >= 4
        
        # Check that expansions are primarily from technical domain
        technical_expansions = [exp for exp in expansions if exp.domain in ['technical', 'academic']]
        assert len(technical_expansions) >= len(expansions) * 0.7  # At least 70% technical
    
    def test_academic_document_expansion(self):
        """Test expansion in an academic research document."""
        text = """
        This research study analyzes NLP techniques for AI applications.
        The methodology uses ML algorithms to process CV data.
        PhD students conducted the analysis using statistical methods.
        """
        
        # Add academic context
        academic_text = f"This research study presents a comprehensive analysis of the methodology. {text}"
        
        document = self.create_document(academic_text)
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Verify academic abbreviations were expanded
        expanded_text = expanded_doc.plain_text
        
        assert "Natural Language Processing" in expanded_text or "Machine Learning" in expanded_text
        assert len(expansions) >= 2
        
        # Check for academic domain preference
        academic_expansions = [exp for exp in expansions if exp.domain == 'academic']
        assert len(academic_expansions) >= 1
    
    def test_business_document_expansion(self):
        """Test expansion in a business document."""
        text = """
        The CEO announced that the CTO will focus on ROI improvements.
        The company's API strategy aligns with our revenue goals.
        """
        
        # Add business context
        business_text = f"The company revenue and market strategy focus on customer acquisition. {text}"
        
        document = self.create_document(business_text)
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Verify business abbreviations were expanded
        expanded_text = expanded_doc.plain_text
        
        business_terms = [
            "Chief Executive Officer",
            "Chief Technology Officer", 
            "Return on Investment"
        ]
        
        business_found = sum(1 for term in business_terms if term in expanded_text)
        assert business_found >= 2
        
        # Check for business domain expansions
        business_expansions = [exp for exp in expansions if exp.domain == 'business']
        assert len(business_expansions) >= 2
    
    def test_mixed_domain_document(self):
        """Test expansion in a document with mixed domains."""
        content_elements = [
            create_content_element(
                element_id="title",
                content_type=ContentType.HEADING,
                content="API Integration Strategy"
            ),
            create_content_element(
                element_id="business-section",
                content_type=ContentType.PARAGRAPH,
                content="The CEO and CTO discussed ROI for our company's market strategy."
            ),
            create_content_element(
                element_id="technical-section",
                content_type=ContentType.PARAGRAPH,
                content="The API uses HTTP protocols with JSON data and SQL databases."
            ),
            create_content_element(
                element_id="academic-section",
                content_type=ContentType.PARAGRAPH,
                content="Research shows that ML and AI techniques improve NLP processing."
            )
        ]
        
        full_text = " ".join([elem.content for elem in content_elements])
        document = self.create_document(full_text, content_elements)
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should detect abbreviations from multiple domains
        domains_found = set(exp.domain for exp in expansions)
        assert len(domains_found) >= 2  # Multiple domains
        
        # Verify content elements were expanded
        for element in expanded_doc.content_elements:
            if "API" in element.content:
                assert "Application Programming Interface" in element.content
    
    def test_abbreviation_learning_and_reuse(self):
        """Test learning abbreviations from one document and using in another."""
        # First document with expansion patterns
        learning_text = """
        The CRUD (Create, Read, Update, Delete) operations are fundamental.
        We use SOAP (Simple Object Access Protocol) for web services.
        """
        
        learning_doc = self.create_document(learning_text)
        
        # Learn from the document
        self.expander.learn_from_document(learning_doc)
        
        # Second document using the learned abbreviations
        usage_text = "The system implements CRUD operations and SOAP protocols."
        usage_doc = self.create_document(usage_text)
        
        expanded_doc, expansions = self.expander.expand_abbreviations(usage_doc)
        
        # Should use learned abbreviations
        expanded_text = expanded_doc.plain_text
        
        # Check if learned abbreviations were applied
        learned_found = 0
        if "Create, Read, Update, Delete" in expanded_text:
            learned_found += 1
        if "Simple Object Access Protocol" in expanded_text:
            learned_found += 1
        
        assert learned_found >= 1  # At least one learned abbreviation should be used
    
    def test_confidence_and_domain_filtering(self):
        """Test confidence thresholds and domain filtering."""
        text = "The API uses HTTP for JSON data transfer via REST."
        document = self.create_document(text)
        
        # Test with different confidence thresholds
        high_conf_doc, high_conf_expansions = self.expander.expand_abbreviations(
            document, confidence_threshold=0.95
        )
        
        low_conf_doc, low_conf_expansions = self.expander.expand_abbreviations(
            document, confidence_threshold=0.5
        )
        
        # Low confidence should expand more abbreviations
        assert len(low_conf_expansions) >= len(high_conf_expansions)
        
        # Test domain filtering
        tech_only_doc, tech_expansions = self.expander.expand_abbreviations(
            document, domains=['technical']
        )
        
        # Should only get technical domain expansions
        for expansion in tech_expansions:
            assert expansion.domain == 'technical'
    
    def test_performance_with_complex_document(self):
        """Test performance with a complex, realistic document."""
        # Create a complex document with multiple sections
        sections = [
            "Executive Summary: The CEO and CTO announced new API initiatives to improve ROI.",
            "Technical Overview: Our REST API uses HTTP protocols with JSON data formats.",
            "Database Integration: The system connects to SQL databases using XML configuration.",
            "Machine Learning: We implement AI and ML algorithms for NLP processing.",
            "Academic Research: PhD researchers analyzed CV techniques in computer science.",
            "Web Technologies: The UI uses HTML, CSS, and JavaScript with AJAX calls.",
            "Security: We implement SSL/TLS encryption for HTTPS connections.",
            "Standards: The system follows W3C guidelines and IEEE standards."
        ]
        
        content_elements = []
        for i, section in enumerate(sections):
            content_elements.append(
                create_content_element(
                    element_id=f"section-{i}",
                    content_type=ContentType.PARAGRAPH,
                    content=section
                )
            )
        
        full_text = " ".join(sections)
        document = self.create_document(full_text, content_elements)
        
        # Process the complex document
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Should handle complex document efficiently
        assert len(expansions) >= 8  # Should find many abbreviations
        assert len(expanded_doc.plain_text) > len(full_text)  # Should be expanded
        
        # Verify different domains are represented
        domains = set(exp.domain for exp in expansions)
        assert len(domains) >= 3  # Multiple domains
        
        # Check that all content elements were processed
        for element in expanded_doc.content_elements:
            # At least some elements should be expanded
            if any(abbrev in element.content for abbrev in ['API', 'CEO', 'HTTP', 'JSON']):
                # This element should have some expansions
                original_length = len(sections[int(element.element_id.split('-')[1])])
                assert len(element.content) >= original_length
    
    def test_statistics_and_reporting(self):
        """Test statistics generation and reporting."""
        # Process a document to generate some expansions
        text = "The API framework uses HTTP, JSON, and SQL for data processing."
        document = self.create_document(text)
        
        expanded_doc, expansions = self.expander.expand_abbreviations(document)
        
        # Get statistics
        stats = self.expander.get_expansion_statistics()
        
        # Verify statistics structure and content
        assert isinstance(stats, dict)
        assert 'total_abbreviations' in stats
        assert 'total_expansions' in stats
        assert 'domain_distribution' in stats
        assert 'average_confidence' in stats
        assert 'confidence_range' in stats
        
        # Verify statistics values
        assert stats['total_abbreviations'] > 0
        assert stats['total_expansions'] > 0
        assert isinstance(stats['domain_distribution'], dict)
        assert 0 <= stats['average_confidence'] <= 1
        assert 0 <= stats['confidence_range']['min'] <= stats['confidence_range']['max'] <= 1
        
        # Should have technical domain in distribution
        assert 'technical' in stats['domain_distribution']
    
    def test_edge_cases_and_robustness(self):
        """Test edge cases and system robustness."""
        edge_cases = [
            "",  # Empty document
            "No abbreviations here at all.",  # No abbreviations
            "API API API HTTP HTTP JSON",  # Repeated abbreviations
            "The API, HTTP, and JSON; work together!",  # Punctuation
            "api http json",  # Lowercase (should not expand)
            "VERYLONGABBREVIATIONTHATDOESNOTEXIST",  # Unknown long abbreviation
            "A B C D E F G",  # Single letters
            "API(test) HTTP[data] JSON{format}",  # Brackets and parentheses
        ]
        
        for i, text in enumerate(edge_cases):
            document = self.create_document(text)
            
            try:
                expanded_doc, expansions = self.expander.expand_abbreviations(document)
                
                # Should not crash
                assert isinstance(expanded_doc, StandardizedDocumentOutput)
                assert isinstance(expansions, list)
                
                # Expanded text should not be shorter than original
                assert len(expanded_doc.plain_text) >= len(text)
                
            except Exception as e:
                pytest.fail(f"Edge case {i} failed with text '{text}': {e}")
    
    def test_concurrent_processing_simulation(self):
        """Test processing multiple documents to simulate concurrent usage."""
        documents = [
            "Technical API documentation with HTTP and JSON protocols.",
            "Business report: CEO and CTO discuss ROI improvements.",
            "Academic paper on ML and AI techniques for NLP processing.",
            "Mixed document with API, CEO, and ML abbreviations.",
        ]
        
        results = []
        
        for i, text in enumerate(documents):
            document = self.create_document(text)
            expanded_doc, expansions = self.expander.expand_abbreviations(document)
            
            results.append({
                'original_length': len(text),
                'expanded_length': len(expanded_doc.plain_text),
                'expansion_count': len(expansions),
                'domains': set(exp.domain for exp in expansions)
            })
        
        # Verify all documents were processed successfully
        assert len(results) == len(documents)
        
        # Each document should have some processing
        for result in results:
            assert result['expanded_length'] >= result['original_length']
            assert result['expansion_count'] >= 0
        
        # Should have found different domains across documents
        all_domains = set()
        for result in results:
            all_domains.update(result['domains'])
        
        assert len(all_domains) >= 2  # Multiple domains across all documents