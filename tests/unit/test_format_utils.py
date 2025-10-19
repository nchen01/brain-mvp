"""Tests for format utilities and consistency management."""

import pytest
import json
from typing import List

from src.docforge.preprocessing.format_utils import (
    FormatConsistencyManager,
    OutputFormatConverter,
    create_format_consistency_report,
    validate_processor_output_quality,
    ensure_format_consistency
)
from src.docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingStatus,
    TableData,
    ImageData,
    ProcessingMetadata,
    DocumentStructure,
    create_content_element,
    create_processing_metadata,
    create_document_structure,
    create_table_data,
    create_image_data
)


class TestFormatConsistencyManager:
    """Test format consistency management."""
    
    def setup_method(self):
        """Set up test environment."""
        self.manager = FormatConsistencyManager()
    
    def create_test_output(self, processor_name: str = "TestProcessor") -> StandardizedDocumentOutput:
        """Create a test output for validation."""
        content_elements = [
            create_content_element(
                element_id="heading_1",
                content_type=ContentType.HEADING,
                content="Test Heading",
                metadata={"level": 1}
            ),
            create_content_element(
                element_id="paragraph_1",
                content_type=ContentType.PARAGRAPH,
                content="This is a test paragraph with sufficient content."
            )
        ]
        
        tables = [
            create_table_data(
                headers=["Column 1", "Column 2"],
                rows=[["Row 1 Col 1", "Row 1 Col 2"], ["Row 2 Col 1", "Row 2 Col 2"]]
            )
        ]
        
        images = [
            create_image_data(
                image_id="image_1",
                alt_text="Test image"
            )
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name=processor_name,
            processor_version="1.0.0",
            processing_duration=1.5
        )
        
        document_structure = create_document_structure(
            total_elements=len(content_elements),
            has_tables=True,
            has_images=True,
            total_pages=1
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            tables=tables,
            images=images,
            document_metadata={"title": "Test Document"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test Heading\\n\\nThis is a test paragraph with sufficient content.",
            markdown_text="# Test Heading\\n\\nThis is a test paragraph with sufficient content."
        )
    
    def test_validate_output_against_standards(self):
        """Test validation against format standards."""
        output = self.create_test_output()
        
        report = self.manager.validate_output_against_standards(output)
        
        assert "basic_validation" in report
        assert "standards_compliance" in report
        assert "overall_valid" in report
        assert "standardized_output" in report
        
        # Should be valid for a well-formed output
        assert report["overall_valid"] is True
        assert report["standards_compliance"]["compliant"] is True
        assert report["standards_compliance"]["compliance_score"] >= 0.8
    
    def test_batch_validate_outputs(self):
        """Test batch validation of multiple outputs."""
        outputs = [
            self.create_test_output("Processor1"),
            self.create_test_output("Processor2"),
            self.create_test_output("Processor3")
        ]
        
        batch_report = self.manager.batch_validate_outputs(outputs)
        
        assert "batch_valid" in batch_report
        assert "overall_score" in batch_report
        assert "individual_reports" in batch_report
        assert "consistency_report" in batch_report
        assert "total_outputs" in batch_report
        assert "valid_outputs" in batch_report
        
        assert batch_report["total_outputs"] == 3
        assert batch_report["valid_outputs"] == 3
        assert len(batch_report["individual_reports"]) == 3
    
    def test_generate_format_report(self):
        """Test comprehensive format report generation."""
        outputs = [
            self.create_test_output("Processor1"),
            self.create_test_output("Processor2")
        ]
        
        report = self.manager.generate_format_report(outputs)
        
        assert "summary" in report
        assert "detailed_results" in report
        assert "format_standards_version" in report
        assert "report_timestamp" in report
        
        # Check summary structure
        summary = report["summary"]
        assert "total_outputs_processed" in summary
        assert "validation_success_rate" in summary
        assert "overall_quality_score" in summary
        assert "consistency_achieved" in summary
        assert "recommendations" in summary
        
        assert summary["total_outputs_processed"] == 2
        assert isinstance(summary["recommendations"], list)


class TestOutputFormatConverter:
    """Test output format conversion with validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.converter = OutputFormatConverter()
    
    def create_test_output(self) -> StandardizedDocumentOutput:
        """Create a test output for conversion."""
        content_elements = [
            create_content_element(
                element_id="heading_1",
                content_type=ContentType.HEADING,
                content="Test Heading",
                metadata={"level": 1}
            ),
            create_content_element(
                element_id="paragraph_1",
                content_type=ContentType.PARAGRAPH,
                content="Test paragraph content."
            )
        ]
        
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
            document_metadata={"title": "Test Document"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test Heading\\n\\nTest paragraph content.",
            markdown_text="# Test Heading\\n\\nTest paragraph content."
        )
    
    def test_convert_with_validation_json(self):
        """Test conversion to JSON with validation."""
        output = self.create_test_output()
        
        converted, validation_report = self.converter.convert_with_validation(output, "json")
        
        assert isinstance(converted, str)
        assert validation_report["validation_passed"] is True
        
        # Should be valid JSON
        parsed = json.loads(converted)
        assert "content_elements" in parsed
        assert "processing_metadata" in parsed
    
    def test_convert_with_validation_markdown(self):
        """Test conversion to Markdown with validation."""
        output = self.create_test_output()
        
        converted, validation_report = self.converter.convert_with_validation(output, "markdown")
        
        assert isinstance(converted, str)
        assert validation_report["validation_passed"] is True
        assert "# Test Heading" in converted
        assert "Test paragraph content." in converted
    
    def test_convert_unsupported_format(self):
        """Test conversion to unsupported format."""
        output = self.create_test_output()
        
        with pytest.raises(ValueError, match="Unsupported format"):
            self.converter.convert_with_validation(output, "unsupported")


class TestFormatUtilityFunctions:
    """Test utility functions for format management."""
    
    def create_test_output(self, processor_name: str = "TestProcessor") -> StandardizedDocumentOutput:
        """Create a test output."""
        content_elements = [
            create_content_element(
                element_id="element_1",
                content_type=ContentType.HEADING,
                content="Test Heading",
                metadata={"level": 1}
            )
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name=processor_name,
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(content_elements),
            total_pages=1
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            document_metadata={"title": "Test Document"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test Heading",
            markdown_text="# Test Heading"
        )
    
    def test_create_format_consistency_report(self):
        """Test format consistency report creation."""
        outputs = [
            self.create_test_output("Processor1"),
            self.create_test_output("Processor2")
        ]
        
        report = create_format_consistency_report(outputs)
        
        assert "summary" in report
        assert "detailed_results" in report
        assert "format_standards_version" in report
        
        summary = report["summary"]
        assert summary["total_outputs_processed"] == 2
        assert isinstance(summary["validation_success_rate"], (int, float))
        assert isinstance(summary["overall_quality_score"], (int, float))
    
    def test_validate_processor_output_quality(self):
        """Test single output quality validation."""
        output = self.create_test_output()
        
        quality_report = validate_processor_output_quality(output)
        
        assert "basic_validation" in quality_report
        assert "standards_compliance" in quality_report
        assert "overall_valid" in quality_report
        assert quality_report["overall_valid"] is True
    
    def test_ensure_format_consistency(self):
        """Test format consistency enforcement."""
        outputs = [
            self.create_test_output("Processor1"),
            self.create_test_output("Processor2")
        ]
        
        standardized_outputs = ensure_format_consistency(outputs)
        
        assert len(standardized_outputs) == 2
        
        for output in standardized_outputs:
            assert isinstance(output, StandardizedDocumentOutput)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])