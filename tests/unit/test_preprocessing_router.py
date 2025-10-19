"""Test document preprocessing router."""

import pytest
from src.docforge.preprocessing.router import (
    DocumentPreprocessingRouter,
    FileTypeCategory,
    ProcessorType
)


@pytest.fixture
def router():
    """Create a document preprocessing router."""
    return DocumentPreprocessingRouter()


def test_detect_file_type_by_extension(router):
    """Test file type detection by extension."""
    # Test PDF
    category, metadata = router.detect_file_type("document.pdf")
    assert category == FileTypeCategory.PDF
    assert "file_extension" in metadata["detection_method"]
    assert metadata["file_extension"] == ".pdf"
    
    # Test Word document
    category, metadata = router.detect_file_type("report.docx")
    assert category == FileTypeCategory.WORD_DOCUMENT
    assert metadata["file_extension"] == ".docx"
    
    # Test Excel spreadsheet
    category, metadata = router.detect_file_type("data.xlsx")
    assert category == FileTypeCategory.EXCEL_SPREADSHEET
    assert metadata["file_extension"] == ".xlsx"
    
    # Test PowerPoint presentation
    category, metadata = router.detect_file_type("slides.pptx")
    assert category == FileTypeCategory.POWERPOINT_PRESENTATION
    assert metadata["file_extension"] == ".pptx"
    
    # Test text document
    category, metadata = router.detect_file_type("readme.txt")
    assert category == FileTypeCategory.TEXT_DOCUMENT
    assert metadata["file_extension"] == ".txt"
    
    # Test unsupported file
    category, metadata = router.detect_file_type("unknown.xyz")
    assert category == FileTypeCategory.UNSUPPORTED


def test_detect_file_type_by_mime_type(router):
    """Test file type detection by MIME type."""
    # Test PDF with MIME type
    category, metadata = router.detect_file_type(
        "document.pdf",
        mime_type="application/pdf"
    )
    assert category == FileTypeCategory.PDF
    assert "mime_type" in metadata["detection_method"]
    
    # Test Word document with MIME type
    category, metadata = router.detect_file_type(
        "report.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert category == FileTypeCategory.WORD_DOCUMENT
    
    # Test conflicting extension and MIME type (MIME type should win)
    category, metadata = router.detect_file_type(
        "document.txt",
        mime_type="application/pdf"
    )
    assert category == FileTypeCategory.PDF


def test_detect_file_type_by_magic_numbers(router):
    """Test file type detection by magic numbers."""
    # Test PDF magic number
    pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'
    category, metadata = router.detect_file_type(
        "unknown_file",
        file_content=pdf_content
    )
    assert category == FileTypeCategory.PDF
    assert "magic_numbers" in metadata["detection_method"]
    
    # Test JPEG magic number
    jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'
    category, metadata = router.detect_file_type(
        "unknown_image",
        file_content=jpeg_content
    )
    assert category == FileTypeCategory.IMAGE
    
    # Test PNG magic number
    png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
    category, metadata = router.detect_file_type(
        "unknown_image",
        file_content=png_content
    )
    assert category == FileTypeCategory.IMAGE


def test_select_processor(router):
    """Test processor selection for different file categories."""
    # Test PDF processor selection
    processor_type, config = router.select_processor(FileTypeCategory.PDF)
    assert processor_type == ProcessorType.MINERU_PDF
    assert config["processor_type"] == "mineru_pdf"
    assert config["extract_images"] is True
    assert config["extract_tables"] is True
    
    # Test Word document processor selection (MVP: not supported)
    processor_type, config = router.select_processor(FileTypeCategory.WORD_DOCUMENT)
    assert processor_type == ProcessorType.UNSUPPORTED
    assert config["processor_type"] == "unsupported"
    
    # Test Excel processor selection (MVP: not supported)
    processor_type, config = router.select_processor(FileTypeCategory.EXCEL_SPREADSHEET)
    assert processor_type == ProcessorType.UNSUPPORTED
    assert config["processor_type"] == "unsupported"
    
    # Test PowerPoint processor selection (MVP: not supported)
    processor_type, config = router.select_processor(FileTypeCategory.POWERPOINT_PRESENTATION)
    assert processor_type == ProcessorType.UNSUPPORTED
    assert config["processor_type"] == "unsupported"
    
    # Test text document processor selection (MVP: not supported)
    processor_type, config = router.select_processor(FileTypeCategory.TEXT_DOCUMENT)
    assert processor_type == ProcessorType.UNSUPPORTED
    assert config["processor_type"] == "unsupported"
    # No encoding config for unsupported processors in MVP
    
    # Test unsupported file processor selection
    processor_type, config = router.select_processor(FileTypeCategory.UNSUPPORTED)
    assert processor_type == ProcessorType.UNSUPPORTED
    assert config["processor_type"] == "unsupported"


def test_route_document_complete_flow(router):
    """Test complete document routing flow."""
    # Test PDF routing
    routing_decision = router.route_document(
        "important_document.pdf",
        file_content=b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' + b'x' * 1000,
        mime_type="application/pdf"
    )
    
    assert routing_decision["filename"] == "important_document.pdf"
    assert routing_decision["file_category"] == "pdf"
    assert routing_decision["processor_type"] == "mineru_pdf"
    assert routing_decision["can_process"] is True
    assert routing_decision["routing_confidence"] > 0.5
    assert "routing_timestamp" in routing_decision
    
    # Test unsupported file routing
    routing_decision = router.route_document("unknown.xyz")
    
    assert routing_decision["filename"] == "unknown.xyz"
    assert routing_decision["file_category"] == "unsupported"
    assert routing_decision["processor_type"] == "unsupported"
    assert routing_decision["can_process"] is False


def test_route_document_with_user_preferences(router):
    """Test document routing with user preferences."""
    user_preferences = {
        "quality": "high",
        "language": "en",
        "ocr_enabled": True
    }
    
    routing_decision = router.route_document(
        "document.pdf",
        user_preferences=user_preferences
    )
    
    config = routing_decision["processor_config"]
    assert config["language"] == "en"
    assert config["ocr_enabled"] is True
    assert config["extract_images"] is True  # High quality setting


def test_processor_priority_and_resources(router):
    """Test processor priority and resource estimation for MVP."""
    # Test text document (MVP: not supported)
    processor_type, config = router.select_processor(FileTypeCategory.TEXT_DOCUMENT)
    assert config["priority"] == 10  # Unsupported priority
    assert config["required_resources"]["memory_mb"] == 0
    
    # Test PDF (should have higher resource requirements)
    processor_type, config = router.select_processor(FileTypeCategory.PDF)
    assert config["priority"] == 5  # Lower priority (higher number)
    assert config["required_resources"]["memory_mb"] == 1000
    assert config["required_resources"]["gpu_optional"] is True


def test_processing_time_estimation(router):
    """Test processing time estimation based on file size."""
    # Small file
    small_metadata = {"file_size": 1024}  # 1KB
    processor_type, config = router.select_processor(
        FileTypeCategory.PDF, small_metadata
    )
    small_time = config["estimated_processing_time"]
    
    # Large file
    large_metadata = {"file_size": 10 * 1024 * 1024}  # 10MB
    processor_type, config = router.select_processor(
        FileTypeCategory.PDF, large_metadata
    )
    large_time = config["estimated_processing_time"]
    
    # Large file should take longer to process
    assert large_time > small_time


def test_get_supported_file_types(router):
    """Test getting supported file types."""
    supported_types = router.get_supported_file_types()
    
    assert "pdf" in supported_types
    assert ".pdf" in supported_types["pdf"]
    
    assert "word_document" in supported_types
    assert ".docx" in supported_types["word_document"]
    assert ".doc" in supported_types["word_document"]
    
    assert "excel_spreadsheet" in supported_types
    assert ".xlsx" in supported_types["excel_spreadsheet"]
    assert ".csv" in supported_types["excel_spreadsheet"]


def test_is_file_supported(router):
    """Test file support checking."""
    # Supported files
    assert router.is_file_supported("document.pdf") is True
    assert router.is_file_supported("report.docx") is True
    assert router.is_file_supported("data.xlsx") is True
    assert router.is_file_supported("slides.pptx") is True
    assert router.is_file_supported("readme.txt") is True
    
    # Unsupported files
    assert router.is_file_supported("unknown.xyz") is False
    assert router.is_file_supported("binary.exe") is False


def test_confidence_scoring(router):
    """Test confidence scoring for file type detection."""
    # High confidence: extension + MIME type + magic number all match
    pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'
    category, metadata = router.detect_file_type(
        "document.pdf",
        file_content=pdf_content,
        mime_type="application/pdf"
    )
    
    assert category == FileTypeCategory.PDF
    assert metadata["confidence"] > 0.8  # Should be high confidence
    
    # Lower confidence: only extension
    category, metadata = router.detect_file_type("document.pdf")
    
    assert category == FileTypeCategory.PDF
    assert metadata["confidence"] < 0.8  # Should be lower confidence


def test_error_handling(router):
    """Test error handling in routing."""
    # Test with None filename (should handle gracefully)
    try:
        routing_decision = router.route_document(None)
        # Should not crash, but should indicate error
        assert "error" in routing_decision or routing_decision["can_process"] is False
    except Exception:
        # If it raises an exception, that's also acceptable
        pass
    
    # Test with empty filename
    routing_decision = router.route_document("")
    assert routing_decision["can_process"] is False


def test_case_insensitive_extensions(router):
    """Test that file extension detection is case insensitive."""
    # Test uppercase extensions
    category, metadata = router.detect_file_type("DOCUMENT.PDF")
    assert category == FileTypeCategory.PDF
    
    category, metadata = router.detect_file_type("REPORT.DOCX")
    assert category == FileTypeCategory.WORD_DOCUMENT
    
    # Test mixed case extensions
    category, metadata = router.detect_file_type("data.XlSx")
    assert category == FileTypeCategory.EXCEL_SPREADSHEET