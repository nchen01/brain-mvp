"""Tests for output format validation and standardization."""

import pytest
from datetime import datetime

from src.docforge.preprocessing.output_validator import (
    OutputFormatValidator,
    OutputFormatStandardizer,
    validate_and_standardize_output
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


class TestOutputFormatValidator:
    """Test output format validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = OutputFormatValidator()
    
    def create_valid_output(self) -> StandardizedDocumentOutput:
        """Create a valid standardized document output for testing."""
        content_elements = [
            create_content_element(
                element_id="element_1",
                content_type=ContentType.HEADING,
                content="Test Heading"
            ),
            create_content_element(
                element_id="element_2",
                content_type=ContentType.PARAGRAPH,
                content="Test paragraph content."
            )
        ]
        
        tables = [
            create_table_data(
                headers=["Name", "Age"],
                rows=[["John", "30"], ["Jane", "25"]],
                caption="Test Table"
            )
        ]
        
        images = [
            create_image_data(
                image_id="image_1",
                file_path="/path/to/image.png",
                alt_text="Test image"
            )
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.5
        )
        
        document_structure = create_document_structure(
            total_elements=2,
            total_pages=1,
            has_tables=True,
            has_images=True
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            tables=tables,
            images=images,
            document_metadata={"filename": "test.pdf"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test Heading\n\nTest paragraph content.",
            markdown_text="# Test Heading\n\nTest paragraph content."
        )
    
    def test_validate_valid_output(self):
        """Test validation of a valid output."""
        output = self.create_valid_output()
        
        is_valid = self.validator.validate_output(output)
        
        assert is_valid is True
        assert len(self.validator.validation_errors) == 0
    
    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        output = self.create_valid_output()
        output.content_elements = None
        
        is_valid = self.validator.validate_output(output)
        
        assert is_valid is False
        assert len(self.validator.validation_errors) > 0
        assert any("content_elements" in error for error in self.validator.validation_errors)
    
    def test_validate_invalid_content_elements(self):
        """Test validation of invalid content elements."""
        output = self.create_valid_output()
        
        # Add invalid content element
        invalid_element = create_content_element(
            element_id="",  # Empty ID
            content_type=ContentType.TEXT,
            content="Test"
        )
        output.content_elements.append(invalid_element)
        
        is_valid = self.validator.validate_output(output)
        
        assert is_valid is False
        assert any("element_id" in error for error in self.validator.validation_errors)
    
    def test_validate_inconsistent_table_structure(self):
        """Test validation of tables with inconsistent structure."""
        output = self.create_valid_output()
        
        # Add table with inconsistent row structure
        inconsistent_table = create_table_data(
            headers=["A", "B", "C"],  # 3 headers
            rows=[["1", "2"], ["3", "4", "5", "6"]],  # Inconsistent row lengths
            caption="Inconsistent Table"
        )
        output.tables.append(inconsistent_table)
        
        is_valid = self.validator.validate_output(output)
        
        # Should still be valid but with warnings
        assert is_valid is True
        assert len(self.validator.validation_warnings) > 0
        assert any("columns" in warning for warning in self.validator.validation_warnings)
    
    def test_validate_element_count_mismatch(self):
        """Test validation with element count mismatch."""
        output = self.create_valid_output()
        
        # Set incorrect total_elements count
        output.document_structure.total_elements = 5  # But we only have 2 elements
        
        is_valid = self.validator.validate_output(output)
        
        # Should still be valid but with warnings
        assert is_valid is True
        assert len(self.validator.validation_warnings) > 0
        assert any("count mismatch" in warning for warning in self.validator.validation_warnings)
    
    def test_get_validation_report(self):
        """Test getting validation report."""
        output = self.create_valid_output()
        output.content_elements = None  # Make it invalid
        
        self.validator.validate_output(output)
        report = self.validator.get_validation_report()
        
        assert "validation_passed" in report
        assert "error_count" in report
        assert "warning_count" in report
        assert "errors" in report
        assert "warnings" in report
        assert "timestamp" in report
        
        assert report["validation_passed"] is False
        assert report["error_count"] > 0


class TestOutputFormatStandardizer:
    """Test output format standardization."""
    
    def setup_method(self):
        """Set up test environment."""
        self.standardizer = OutputFormatStandardizer()
    
    def create_messy_output(self) -> StandardizedDocumentOutput:
        """Create a messy output that needs standardization."""
        content_elements = [
            create_content_element(
                element_id="",  # Empty ID - needs generation
                content_type=ContentType.HEADING,
                content="  Test Heading  "  # Extra whitespace
            ),
            create_content_element(
                element_id="element_2",
                content_type=ContentType.PARAGRAPH,
                content="Test paragraph content.\n\n\n"  # Trailing whitespace
            )
        ]
        
        tables = [
            create_table_data(
                headers=["  Name  ", "Age"],  # Extra whitespace
                rows=[["  John  ", "30"], ["Jane", ""]],  # String types with whitespace
                metadata={}  # Empty metadata instead of None
            )
        ]
        
        images = [
            create_image_data(
                image_id="",  # Empty ID - needs generation
                file_path="/path/to/image.png",
                alt_text=""  # Empty alt text - needs generation
            )
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.5
        )
        
        document_structure = create_document_structure(
            total_elements=2,
            total_pages=1,
            has_tables=True,
            has_images=True
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            tables=tables,
            images=images,
            document_metadata={"filename": "test.pdf"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status="success",  # String instead of enum
            plain_text="Test Heading\r\n\r\nTest paragraph content.\n\n\n\n\n",  # Mixed line endings and excessive whitespace
            markdown_text="# Test Heading\nTest paragraph content."  # Missing spacing after header
        )
    
    def test_standardize_content_elements(self):
        """Test standardization of content elements."""
        output = self.create_messy_output()
        
        standardized_output = self.standardizer.standardize_output(output)
        
        # Check that whitespace was trimmed
        assert standardized_output.content_elements[0].content == "Test Heading"
        assert standardized_output.content_elements[1].content == "Test paragraph content."
        
        # Check that empty element_id was generated
        assert standardized_output.content_elements[0].element_id == "element_1"
        
        # Check standardization log
        log = self.standardizer.get_standardization_log()
        assert len(log) > 0
        assert any("Trimmed whitespace" in entry for entry in log)
        assert any("Generated element_id" in entry for entry in log)
    
    def test_standardize_tables(self):
        """Test standardization of tables."""
        output = self.create_messy_output()
        
        standardized_output = self.standardizer.standardize_output(output)
        
        # Check that headers were cleaned
        assert standardized_output.tables[0].headers == ["Name", "Age"]
        
        # Check that rows were standardized
        assert standardized_output.tables[0].rows[0] == ["John", "30"]
        assert standardized_output.tables[0].rows[1] == ["Jane", ""]
        
        # Check that metadata was added
        assert standardized_output.tables[0].metadata is not None
        assert "table_id" in standardized_output.tables[0].metadata
    
    def test_standardize_images(self):
        """Test standardization of images."""
        output = self.create_messy_output()
        
        standardized_output = self.standardizer.standardize_output(output)
        
        # Check that image_id was generated
        assert standardized_output.images[0].image_id == "image_1"
        
        # Check that alt_text was generated
        assert standardized_output.images[0].alt_text == "Image image_1"
    
    def test_standardize_text_outputs(self):
        """Test standardization of text outputs."""
        output = self.create_messy_output()
        
        standardized_output = self.standardizer.standardize_output(output)
        
        # Check that line endings were normalized
        assert '\r\n' not in standardized_output.plain_text
        assert '\r' not in standardized_output.plain_text
        
        # Check that excessive empty lines were removed
        lines = standardized_output.plain_text.split('\n')
        empty_count = 0
        max_consecutive_empty = 0
        
        for line in lines:
            if line.strip() == "":
                empty_count += 1
                max_consecutive_empty = max(max_consecutive_empty, empty_count)
            else:
                empty_count = 0
        
        assert max_consecutive_empty <= 2
    
    def test_standardize_processing_status(self):
        """Test standardization of processing status."""
        output = self.create_messy_output()
        
        standardized_output = self.standardizer.standardize_output(output)
        
        # Check that string status was converted to enum
        assert standardized_output.processing_status == ProcessingStatus.SUCCESS


class TestIntegratedValidationAndStandardization:
    """Test integrated validation and standardization."""
    
    def test_validate_and_standardize_output(self):
        """Test the integrated validation and standardization function."""
        # Create a messy but valid output
        content_elements = [
            create_content_element(
                element_id="element_1",
                content_type=ContentType.HEADING,
                content="  Test Heading  "  # Extra whitespace
            )
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.5
        )
        
        document_structure = create_document_structure(
            total_elements=1,
            total_pages=1,
            has_tables=False,
            has_images=False
        )
        
        output = StandardizedDocumentOutput(
            content_elements=content_elements,
            tables=[],
            images=[],
            document_metadata={"filename": "test.pdf"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status="success",  # String instead of enum
            plain_text="  Test Heading  ",
            markdown_text="# Test Heading"
        )
        
        is_valid, standardized_output, report = validate_and_standardize_output(output)
        
        # Should be valid after standardization
        assert is_valid is True
        
        # Should be standardized
        assert standardized_output.content_elements[0].content == "Test Heading"
        assert standardized_output.processing_status == ProcessingStatus.SUCCESS
        
        # Should have report
        assert "validation_passed" in report
        assert "standardization_log" in report
        assert report["validation_passed"] is True
    
    def test_validate_and_standardize_invalid_output(self):
        """Test validation and standardization of invalid output."""
        # Create a valid output first, then make it invalid by modifying attributes
        output = StandardizedDocumentOutput(
            content_elements=[],
            tables=[],
            images=[],
            document_metadata={"filename": "test.pdf"},
            document_structure=create_document_structure(
                total_elements=0,
                total_pages=1,
                has_tables=False,
                has_images=False
            ),
            processing_metadata=create_processing_metadata(
                processor_name="TestProcessor",
                processor_version="1.0.0",
                processing_duration=1.0
            ),
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="Test",
            markdown_text="Test"
        )
        
        # Make it invalid by setting required fields to None after creation
        output.content_elements = None
        output.document_structure = None
        output.processing_metadata = None
        
        is_valid, standardized_output, report = validate_and_standardize_output(output)
        
        # Should still be invalid after standardization
        assert is_valid is False
        
        # Should have error report
        assert report["validation_passed"] is False
        assert report["error_count"] > 0
        assert len(report["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])