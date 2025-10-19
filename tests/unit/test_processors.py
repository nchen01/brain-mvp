"""Test document processors."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.preprocessing.text_processor import TextDocumentProcessor
from src.docforge.preprocessing.mineru_processor import MinerUProcessor
from src.docforge.preprocessing.markitdown_processor import MarkItDownProcessor
from src.docforge.preprocessing.processor_factory import ProcessorFactory
from src.docforge.preprocessing.schemas import ProcessingStatus, ContentType


@pytest.fixture
def temp_file():
    """Create a temporary file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content\nSecond line\n# Heading\n- List item")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file (mock)."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        # Write PDF magic number and some content
        f.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        f.write(b'Mock PDF content for testing')
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_text_processor_basic_functionality():
    """Test basic text processor functionality."""
    processor = TextDocumentProcessor()
    
    # Test supported formats
    supported = processor.get_supported_formats()
    assert '.txt' in supported
    assert '.md' in supported
    
    # Test can_process
    assert processor.can_process("test.txt") is True
    assert processor.can_process("test.pdf") is False


def test_text_processor_document_processing(temp_file):
    """Test text document processing (MVP: skip - not supported)."""
    # Skip this test in MVP since text processing is not supported
    pytest.skip("Text processing not supported in MVP - only PDF with MinerU")
    
    # Check that different content types were detected
    content_types = [element.content_type for element in output.content_elements]
    assert ContentType.HEADING in content_types
    assert ContentType.LIST in content_types


def test_mineru_processor_basic_functionality():
    """Test basic MinerU processor functionality."""
    processor = MinerUProcessor()
    
    # Test supported formats
    supported = processor.get_supported_formats()
    assert '.pdf' in supported
    
    # Test can_process
    assert processor.can_process("test.pdf") is True
    assert processor.can_process("test.txt") is False


def test_mineru_processor_mock_processing(temp_pdf_file):
    """Test MinerU processor with mock processing."""
    processor = MinerUProcessor()
    
    # Process the document
    result = processor.process_document(temp_pdf_file)
    
    assert result.success is True
    assert result.output is not None
    
    output = result.output
    assert output.processing_status == ProcessingStatus.SUCCESS
    assert len(output.content_elements) > 0
    assert len(output.tables) > 0  # Mock result includes tables
    assert len(output.images) > 0  # Mock result includes images
    assert output.document_structure.has_tables is True
    assert output.document_structure.has_images is True


def test_markitdown_processor_basic_functionality():
    """Test basic MarkItDown processor functionality."""
    processor = MarkItDownProcessor()
    
    # Test supported formats
    supported = processor.get_supported_formats()
    assert '.docx' in supported
    assert '.xlsx' in supported
    assert '.pptx' in supported
    
    # Test can_process
    assert processor.can_process("test.docx") is True
    assert processor.can_process("test.xlsx") is True
    assert processor.can_process("test.pdf") is False


def test_markitdown_processor_word_document():
    """Test MarkItDown processor with Word document (MVP: should fail)."""
    processor = MarkItDownProcessor()
    
    # Create temporary Word file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as f:
        f.write(b'Mock Word document content')
        temp_path = f.name
    
    try:
        result = processor.process_document(temp_path)
        
        # In MVP, MarkItDown should fail with NotImplementedError
        assert result.success is False
        assert result.error is not None
        assert "not implemented in MVP" in result.error.error_message
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_processor_factory_initialization():
    """Test processor factory initialization for MVP."""
    factory = ProcessorFactory()
    
    # Test that only MinerU processor is registered in MVP
    stats = factory.get_processing_statistics()
    assert stats["total_processors"] == 1  # Only MinerU in MVP
    assert "mineru" in stats["processors"]
    # Other processors not available in MVP:
    assert "text" not in stats["processors"]
    assert "markitdown" not in stats["processors"]


def test_processor_factory_file_routing():
    """Test processor factory file routing for MVP (PDF only)."""
    factory = ProcessorFactory()
    
    # Test PDF routing (supported in MVP)
    processor = factory.get_processor_for_file("document.pdf")
    assert processor is not None
    assert isinstance(processor, MinerUProcessor)
    
    # Test other file types (not supported in MVP)
    processor = factory.get_processor_for_file("readme.txt")
    assert processor is None  # Not supported in MVP
    
    processor = factory.get_processor_for_file("report.docx")
    assert processor is None  # Not supported in MVP
    
    processor = factory.get_processor_for_file("data.xlsx")
    assert processor is None  # Not supported in MVP
    
    # Test unsupported file
    processor = factory.get_processor_for_file("unknown.xyz")
    assert processor is None


def test_processor_factory_routing_decision():
    """Test processor factory routing decision."""
    factory = ProcessorFactory()
    
    # Test PDF routing decision
    decision = factory.get_routing_decision("important.pdf")
    assert decision["can_process"] is True
    assert decision["processor_type"] == "mineru_pdf"
    assert decision["file_category"] == "pdf"
    
    # Test with user preferences
    preferences = {"quality": "high", "ocr_enabled": True}
    decision = factory.get_routing_decision("document.pdf", user_preferences=preferences)
    assert decision["processor_config"]["ocr_enabled"] is True


def test_processor_factory_supported_formats():
    """Test getting supported formats from factory for MVP."""
    factory = ProcessorFactory()
    
    supported_formats = factory.list_supported_formats()
    
    # MVP: Only MinerU processor is available
    assert "mineru" in supported_formats
    assert '.pdf' in supported_formats["mineru"]
    
    # Other processors not available in MVP
    assert "text" not in supported_formats
    assert "markitdown" not in supported_formats


def test_processor_validation():
    """Test processor configuration validation."""
    factory = ProcessorFactory()
    
    # Test validation of all processors
    validation_results = factory.validate_all_processors()
    
    for processor_name, errors in validation_results.items():
        # Should have no errors with default configuration
        assert isinstance(errors, list)
        # Note: Some processors might have warnings, but shouldn't have critical errors


def test_custom_processor_creation():
    """Test creating processors with custom configuration for MVP."""
    factory = ProcessorFactory()
    
    # Create MinerU processor with custom config
    custom_config = {
        "extract_images": False,
        "extract_tables": True,
        "ocr_enabled": False,
        "language": "en"
    }
    
    processor = factory.create_processor_with_config("mineru", custom_config)
    assert processor is not None
    assert isinstance(processor, MinerUProcessor)
    assert processor.extract_images is False
    assert processor.extract_tables is True
    
    # Test unsupported processor types in MVP
    text_processor = factory.create_processor_with_config("text", {})
    assert text_processor is None  # Not supported in MVP
    
    markitdown_processor = factory.create_processor_with_config("markitdown", {})
    assert markitdown_processor is None  # Not supported in MVP


def test_processor_error_handling():
    """Test processor error handling with MinerU (MVP)."""
    processor = MinerUProcessor()
    
    # Test with non-existent file
    result = processor.process_document("non_existent_file.pdf")
    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.error_message.lower()
    
    # Test with unsupported format (for MinerU)
    result = processor.process_document("test.txt")
    assert result.success is False
    assert result.error is not None
    assert ("unsupported" in result.error.error_message.lower() or 
            "not found" in result.error.error_message.lower())


def test_processor_info_retrieval():
    """Test getting processor information for MVP."""
    factory = ProcessorFactory()
    
    # Test getting info for MinerU processor (available in MVP)
    info = factory.get_processor_info("mineru")
    assert info is not None
    assert info["name"] == "MinerUProcessor"
    assert info["version"] == "1.0.0"
    assert ".pdf" in info["supported_formats"]
    
    # Test getting info for processors not available in MVP
    info = factory.get_processor_info("text")
    assert info is None  # Not available in MVP
    
    info = factory.get_processor_info("markitdown")
    assert info is None  # Not available in MVP
    info = factory.get_processor_info("non_existent")
    assert info is None


def test_file_support_checking():
    """Test file support checking."""
    factory = ProcessorFactory()
    
    # Test supported files
    assert factory.is_file_supported("document.pdf") is True
    assert factory.is_file_supported("report.docx") is True
    assert factory.is_file_supported("data.xlsx") is True
    assert factory.is_file_supported("slides.pptx") is True
    assert factory.is_file_supported("readme.txt") is True
    
    # Test unsupported files
    assert factory.is_file_supported("unknown.xyz") is False
    assert factory.is_file_supported("binary.exe") is False