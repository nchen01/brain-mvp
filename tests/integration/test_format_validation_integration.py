"""Integration tests for format validation and standardization."""

import pytest
import tempfile
import os
from pathlib import Path

from src.docforge.preprocessing.mineru_processor import MinerUProcessor
from src.docforge.preprocessing.format_utils import (
    validate_processor_output_quality,
    create_format_consistency_report,
    ensure_format_consistency
)
from src.docforge.preprocessing.schemas import ProcessingStatus


class TestFormatValidationIntegration:
    """Test format validation integration with processors."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.processor = MinerUProcessor()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_mock_pdf_content(self) -> bytes:
        """Create mock PDF content for testing."""
        pdf_header = b'%PDF-1.4\\n%\\xe2\\xe3\\xcf\\xd3\\n'
        mock_content = b'Mock PDF content for validation integration testing' * 10
        return pdf_header + mock_content
    
    def test_processor_output_validation_integration(self):
        """Test that processor outputs are automatically validated."""
        # Process a mock PDF
        mock_pdf = self.create_mock_pdf_content()
        
        result = self.processor.process_document(
            "test_validation.pdf",
            file_content=mock_pdf
        )
        
        # Processing should succeed
        assert result.success is True
        assert result.output is not None
        
        # Output should be validated and standardized
        output = result.output
        assert output.processing_status == ProcessingStatus.SUCCESS
        
        # Validate the output quality
        quality_report = validate_processor_output_quality(output)
        
        # Should pass validation
        assert quality_report["overall_valid"] is True
        assert quality_report["basic_validation"]["validation_passed"] is True
        assert quality_report["standards_compliance"]["compliant"] is True
    
    def test_format_consistency_across_multiple_processing(self):
        """Test format consistency across multiple document processing."""
        mock_pdf = self.create_mock_pdf_content()
        
        # Process the same document multiple times
        results = []
        for i in range(3):
            result = self.processor.process_document(
                f"test_consistency_{i}.pdf",
                file_content=mock_pdf
            )
            assert result.success is True
            results.append(result.output)
        
        # Check format consistency
        consistency_report = create_format_consistency_report(results)
        
        # Should be consistent
        assert consistency_report["summary"]["consistency_achieved"] is True
        assert consistency_report["summary"]["validation_success_rate"] == 1.0
        assert consistency_report["summary"]["overall_quality_score"] >= 0.8
    
    def test_format_standardization_integration(self):
        """Test that format standardization works in the processing pipeline."""
        mock_pdf = self.create_mock_pdf_content()
        
        # Process document
        result = self.processor.process_document(
            "test_standardization.pdf",
            file_content=mock_pdf
        )
        
        assert result.success is True
        output = result.output
        
        # Check that standardization has been applied
        # Text should be properly formatted
        assert "\\r" not in output.plain_text  # No Windows line endings
        assert "\\r" not in output.markdown_text
        
        # Content elements should have proper IDs
        for element in output.content_elements:
            assert element.element_id is not None
            assert len(element.element_id.strip()) > 0
        
        # Tables should have proper structure
        for table in output.tables:
            if table.headers and table.rows:
                # All rows should have consistent column count
                expected_cols = len(table.headers)
                for row in table.rows:
                    # Allow some flexibility for malformed tables
                    assert isinstance(row, list)
        
        # Images should have proper IDs
        for image in output.images:
            assert image.image_id is not None
            assert len(image.image_id.strip()) > 0
    
    def test_validation_error_handling(self):
        """Test validation error handling in the processing pipeline."""
        # Test with non-existent file
        result = self.processor.process_document("nonexistent.pdf")
        
        # Should fail gracefully
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.error_message.lower()
    
    def test_batch_format_consistency_enforcement(self):
        """Test batch format consistency enforcement."""
        mock_pdf = self.create_mock_pdf_content()
        
        # Process multiple documents
        outputs = []
        for i in range(2):
            result = self.processor.process_document(
                f"test_batch_{i}.pdf",
                file_content=mock_pdf
            )
            assert result.success is True
            outputs.append(result.output)
        
        # Ensure format consistency
        standardized_outputs = ensure_format_consistency(outputs)
        
        # Should have same number of outputs
        assert len(standardized_outputs) == len(outputs)
        
        # All outputs should be properly standardized
        for output in standardized_outputs:
            assert output.processing_status == ProcessingStatus.SUCCESS
            assert len(output.content_elements) > 0
            assert output.plain_text is not None
            assert output.markdown_text is not None
    
    def test_quality_assurance_metrics(self):
        """Test quality assurance metrics collection."""
        mock_pdf = self.create_mock_pdf_content()
        
        # Process document
        result = self.processor.process_document(
            "test_qa_metrics.pdf",
            file_content=mock_pdf
        )
        
        assert result.success is True
        output = result.output
        
        # Get quality report
        quality_report = validate_processor_output_quality(output)
        
        # Check that metrics are collected
        assert "basic_validation" in quality_report
        assert "standards_compliance" in quality_report
        
        basic_validation = quality_report["basic_validation"]
        assert "error_count" in basic_validation
        assert "warning_count" in basic_validation
        assert "validation_passed" in basic_validation
        
        standards_compliance = quality_report["standards_compliance"]
        assert "compliance_score" in standards_compliance
        assert "compliant" in standards_compliance
        assert isinstance(standards_compliance["compliance_score"], (int, float))
        assert 0.0 <= standards_compliance["compliance_score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])