"""Integration tests for MinerU PDF processing."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.preprocessing.mineru_processor import MinerUProcessor
from src.docforge.preprocessing.schemas import ProcessingStatus


class TestMinerUIntegration:
    """Test MinerU processor integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.processor = MinerUProcessor({
            "extract_images": True,
            "extract_tables": True,
            "ocr_enabled": False,  # Disable OCR for faster testing
            "language": "en"
        })
    
    def test_processor_initialization(self):
        """Test that MinerU processor initializes correctly."""
        assert self.processor.processor_name == "MinerUProcessor"
        assert self.processor.processor_version == "1.0.0"
        assert self.processor.extract_images is True
        assert self.processor.extract_tables is True
        assert self.processor.ocr_enabled is False
    
    def test_supported_formats(self):
        """Test that processor reports correct supported formats."""
        formats = self.processor.get_supported_formats()
        assert '.pdf' in formats
        assert len(formats) == 1  # Only PDF in MVP
    
    def test_config_validation(self):
        """Test configuration validation."""
        errors = self.processor.validate_config()
        # Should not have errors with default config
        assert isinstance(errors, list)
    
    def test_mock_pdf_processing(self):
        """Test PDF processing with mock data (when MinerU not available)."""
        # Create a mock PDF file
        mock_pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' + b'Mock PDF content' * 100
        
        # Process the mock PDF
        result = self.processor.process_document(
            "test_document.pdf",
            file_content=mock_pdf_content
        )
        
        # Verify result structure
        assert result.success is True
        assert result.output.processing_status == ProcessingStatus.SUCCESS
        assert len(result.output.content_elements) > 0
        assert result.output.plain_text is not None
        assert result.output.markdown_text is not None
        
        # Verify docume   
     # Verify document structure
        assert result.output.document_structure.total_elements > 0
        assert result.output.document_structure.total_pages >= 1
        
        # Verify processing metadata
        assert result.output.processing_metadata.processor_name == "MinerUProcessor"
        assert result.output.processing_metadata.processor_version == "1.0.0"
    
    def test_mineru_fallback_behavior(self):
        """Test that processor falls back to mock when MinerU is not available."""
        # This test verifies the fallback behavior works correctly
        mock_pdf_content = b'%PDF-1.4\n' + b'Test content' * 50
        
        # The processor should handle the case where MinerU is not installed
        result = self.processor._process_with_mineru("test.pdf", mock_pdf_content)
        
        # Should return a valid result structure
        assert isinstance(result, dict)
        assert "total_pages" in result
        assert "content" in result
        assert "metadata" in result
    
    def test_content_element_conversion(self):
        """Test conversion of MinerU results to standardized format."""
        # Mock MinerU result
        mock_result = {
            "total_pages": 2,
            "detected_language": "en",
            "content": [
                {
                    "type": "heading",
                    "text": "Test Heading",
                    "page": 1,
                    "bbox": [100, 700, 400, 750]
                },
                {
                    "type": "paragraph", 
                    "text": "Test paragraph content.",
                    "page": 1,
                    "bbox": [100, 600, 400, 680]
                }
            ]
        }
        
        # Convert to content elements
        elements = self.processor._convert_to_content_elements(mock_result)
        
        assert len(elements) == 2
        assert elements[0].content_type == "heading"
        assert elements[0].content == "Test Heading"
        assert elements[1].content_type == "paragraph"
        assert elements[1].content == "Test paragraph content."
    
    def test_table_extraction(self):
        """Test table extraction from MinerU results."""
        mock_result = {
            "content": [
                {
                    "type": "table",
                    "page": 1,
                    "headers": ["Name", "Age", "City"],
                    "rows": [
                        ["John", "30", "NYC"],
                        ["Jane", "25", "LA"]
                    ],
                    "caption": "Test Table"
                }
            ]
        }
        
        tables = self.processor._extract_tables_from_result(mock_result)
        
        assert len(tables) == 1
        assert tables[0].headers == ["Name", "Age", "City"]
        assert len(tables[0].rows) == 2
        assert tables[0].caption == "Test Table"
    
    def test_image_extraction(self):
        """Test image extraction from MinerU results."""
        mock_result = {
            "content": [
                {
                    "type": "image",
                    "page": 1,
                    "image_path": "/tmp/image_1.png",
                    "alt_text": "Test image",
                    "caption": "Figure 1"
                }
            ]
        }
        
        images = self.processor._extract_images_from_result(mock_result)
        
        assert len(images) == 1
        assert images[0].file_path == "/tmp/image_1.png"
        assert images[0].alt_text == "Test image"
        assert images[0].caption == "Figure 1"
    
    def test_markdown_generation(self):
        """Test markdown generation from processed content."""
        # Create mock content elements
        from src.docforge.preprocessing.schemas import create_content_element, ContentType
        
        elements = [
            create_content_element(
                element_id="1",
                content_type=ContentType.HEADING,
                content="Test Document",
                formatting={"font_size": 18}
            ),
            create_content_element(
                element_id="2", 
                content_type=ContentType.PARAGRAPH,
                content="This is a test paragraph."
            )
        ]
        
        markdown = self.processor._generate_markdown(elements, [], [])
        
        assert "# Test Document" in markdown
        assert "This is a test paragraph." in markdown
    
    def test_plain_text_generation(self):
        """Test plain text generation from content elements."""
        from src.docforge.preprocessing.schemas import create_content_element, ContentType
        
        elements = [
            create_content_element(
                element_id="1",
                content_type=ContentType.HEADING,
                content="Test Heading"
            ),
            create_content_element(
                element_id="2",
                content_type=ContentType.PARAGRAPH, 
                content="Test paragraph."
            )
        ]
        
        plain_text = self.processor._generate_plain_text(elements)
        
        assert "Test Heading" in plain_text
        assert "Test paragraph." in plain_text
    
    @pytest.mark.skipif(
        not os.environ.get("MINERU_AVAILABLE"),
        reason="MinerU not available - set MINERU_AVAILABLE=1 to test real integration"
    )
    def test_real_mineru_integration(self):
        """Test real MinerU integration if available."""
        # This test only runs if MinerU is actually installed
        # Set environment variable MINERU_AVAILABLE=1 to enable
        
        # Create a simple PDF for testing
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                # Create a simple PDF
                c = canvas.Canvas(tmp_file.name, pagesize=letter)
                c.drawString(100, 750, "Test Document")
                c.drawString(100, 700, "This is a test paragraph.")
                c.save()
                
                # Process with MinerU
                with open(tmp_file.name, 'rb') as f:
                    pdf_content = f.read()
                
                result = self.processor.process_document(
                    tmp_file.name,
                    file_content=pdf_content
                )
                
                # Verify processing succeeded
                assert result.success is True
                assert result.output.processing_status == ProcessingStatus.SUCCESS
                
                # Clean up
                os.unlink(tmp_file.name)
                
        except ImportError:
            pytest.skip("reportlab not available for PDF generation")
        except Exception as e:
            pytest.fail(f"Real MinerU integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])