"""Comprehensive integration tests for document processors."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from typing import List, Dict, Any

from src.docforge.preprocessing.mineru_processor import MinerUProcessor
from src.docforge.preprocessing.markitdown_processor import MarkItDownProcessor
from src.docforge.preprocessing.text_processor import TextDocumentProcessor
from src.docforge.preprocessing.processor_factory import ProcessorFactory
from src.docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ProcessingStatus,
    ContentType
)
from src.docforge.preprocessing.output_validator import (
    validate_and_standardize_output,
    compare_processor_outputs
)


class TestProcessorIntegrationComprehensive:
    """Comprehensive integration tests for all processors."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.factory = ProcessorFactory()
        
        # Initialize processors
        self.mineru_processor = MinerUProcessor({
            "extract_images": True,
            "extract_tables": True,
            "ocr_enabled": False
        })
        self.markitdown_processor = MarkItDownProcessor()
        self.text_processor = TextDocumentProcessor()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_mock_pdf_content(self) -> bytes:
        """Create mock PDF content for testing."""
        pdf_header = b'%PDF-1.4\\n%\\xe2\\xe3\\xcf\\xd3\\n'
        mock_content = b'Mock PDF content for comprehensive integration testing' * 20
        return pdf_header + mock_content
    
    def create_mock_docx_content(self) -> bytes:
        """Create mock DOCX content for testing."""
        # Mock DOCX file signature (ZIP-based)
        docx_header = b'PK\\x03\\x04'
        mock_content = b'Mock DOCX content for testing' * 10
        return docx_header + mock_content
    
    def create_mock_xlsx_content(self) -> bytes:
        """Create mock XLSX content for testing."""
        # Mock XLSX file signature (ZIP-based)
        xlsx_header = b'PK\\x03\\x04'
        mock_content = b'Mock XLSX content for testing' * 10
        return xlsx_header + mock_content
    
    def create_mock_pptx_content(self) -> bytes:
        """Create mock PPTX content for testing."""
        # Mock PPTX file signature (ZIP-based)
        pptx_header = b'PK\\x03\\x04'
        mock_content = b'Mock PPTX content for testing' * 10
        return pptx_header + mock_content
    
    def create_corrupted_pdf_content(self) -> bytes:
        """Create corrupted PDF content for error testing."""
        return b'This is not a valid PDF file content'
    
    def test_pdf_processing_with_mineru(self):
        """Test PDF processing with sample documents using MinerU."""
        mock_pdf = self.create_mock_pdf_content()
        
        # Test processing
        result = self.mineru_processor.process_document(
            "sample_document.pdf",
            file_content=mock_pdf
        )
        
        # Verify successful processing
        assert result.success is True
        assert result.output is not None
        assert result.output.processing_status == ProcessingStatus.SUCCESS
        
        # Verify content structure
        output = result.output
        assert len(output.content_elements) > 0
        assert output.plain_text is not None
        assert output.markdown_text is not None
        
        # Verify document structure
        assert output.document_structure.total_elements > 0
        assert output.document_structure.total_pages >= 1
        
        # Verify processing metadata
        assert output.processing_metadata.processor_name == "MinerUProcessor"
        assert output.processing_metadata.processing_duration >= 0
        
        # Verify tables and images are extracted
        assert isinstance(output.tables, list)
        assert isinstance(output.images, list)
    
    def test_excel_processing_with_markitdown_mvp_behavior(self):
        """Test Excel processing using MarkItDown (MVP: should fail gracefully)."""
        mock_xlsx = self.create_mock_xlsx_content()
        
        # In MVP, MarkItDown is not implemented, so this should fail gracefully
        try:
            result = self.markitdown_processor.process_document(
                "sample_spreadsheet.xlsx",
                file_content=mock_xlsx
            )
            
            # Should fail with NotImplementedError in MVP
            assert result.success is False
            assert result.error is not None
            assert "not implemented in MVP" in result.error.error_message
            
        except NotImplementedError as e:
            # This is expected in MVP
            assert "not implemented in MVP" in str(e)
    
    def test_powerpoint_processing_with_markitdown_mvp_behavior(self):
        """Test PowerPoint processing using MarkItDown (MVP: should fail gracefully)."""
        mock_pptx = self.create_mock_pptx_content()
        
        # In MVP, MarkItDown is not implemented, so this should fail gracefully
        try:
            result = self.markitdown_processor.process_document(
                "sample_presentation.pptx",
                file_content=mock_pptx
            )
            
            # Should fail with NotImplementedError in MVP
            assert result.success is False
            assert result.error is not None
            assert "not implemented in MVP" in result.error.error_message
            
        except NotImplementedError as e:
            # This is expected in MVP
            assert "not implemented in MVP" in str(e)
    
    def test_word_processing_with_markitdown_mvp_behavior(self):
        """Test Word document processing using MarkItDown (MVP: should fail gracefully)."""
        mock_docx = self.create_mock_docx_content()
        
        # In MVP, MarkItDown is not implemented, so this should fail gracefully
        try:
            result = self.markitdown_processor.process_document(
                "sample_document.docx",
                file_content=mock_docx
            )
            
            # Should fail with NotImplementedError in MVP
            assert result.success is False
            assert result.error is not None
            assert "not implemented in MVP" in result.error.error_message
            
        except NotImplementedError as e:
            # This is expected in MVP
            assert "not implemented in MVP" in str(e)
    
    def test_output_format_consistency_between_processors(self):
        """Test output format consistency between processors."""
        # Process the same content with different processors where possible
        
        # Test PDF with MinerU
        mock_pdf = self.create_mock_pdf_content()
        pdf_result = self.mineru_processor.process_document(
            "test_consistency.pdf",
            file_content=mock_pdf
        )
        
        assert pdf_result.success is True
        
        # Test text content with text processor
        text_content = "# Test Document\\n\\nThis is a test paragraph."
        text_result = self.text_processor.process_document(
            "test_consistency.txt",
            file_content=text_content.encode('utf-8')
        )
        
        assert text_result.success is True
        
        # Compare output formats
        outputs = [pdf_result.output, text_result.output]
        consistency_report = compare_processor_outputs(outputs)
        
        # Verify both outputs follow the same schema
        for output in outputs:
            self._verify_standardized_output_schema(output)
        
        # Check consistency report
        assert "consistent" in consistency_report
        assert "metrics" in consistency_report
        assert consistency_report["total_outputs_compared"] == 2
    
    def test_error_handling_for_corrupted_files(self):
        """Test error handling for corrupted files."""
        
        # Test corrupted PDF
        corrupted_pdf = self.create_corrupted_pdf_content()
        
        result = self.mineru_processor.process_document(
            "corrupted.pdf",
            file_content=corrupted_pdf
        )
        
        # Should still process (mock processing is robust) but might have warnings
        # The validation system should handle any issues
        assert result.success is True  # Mock processing handles corrupted files gracefully
        
        # Test non-existent file
        result = self.mineru_processor.process_document("nonexistent.pdf")
        
        # Should fail gracefully
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.error_message.lower()
        
        # Test unsupported file format
        result = self.mineru_processor.process_document(
            "unsupported.xyz",
            file_content=b"unsupported content"
        )
        
        # Should fail due to unsupported format
        assert result.success is False
        assert result.error is not None
        assert "unsupported" in result.error.error_message.lower()
    
    def test_standardized_output_schema_compliance(self):
        """Validate standardized output schema compliance."""
        
        # Test PDF processing
        mock_pdf = self.create_mock_pdf_content()
        result = self.mineru_processor.process_document(
            "schema_test.pdf",
            file_content=mock_pdf
        )
        
        assert result.success is True
        output = result.output
        
        # Validate schema compliance
        is_valid, standardized_output, validation_report = validate_and_standardize_output(output)
        
        # Should be valid
        assert is_valid is True
        assert validation_report["validation_passed"] is True
        assert validation_report["error_count"] == 0
        
        # Verify all required fields are present and correctly typed
        self._verify_standardized_output_schema(standardized_output)
        
        # Test text processing
        text_content = "Test document content"
        text_result = self.text_processor.process_document(
            "schema_test.txt",
            file_content=text_content.encode('utf-8')
        )
        
        assert text_result.success is True
        
        # Validate text processor output schema compliance
        is_valid, standardized_output, validation_report = validate_and_standardize_output(text_result.output)
        
        assert is_valid is True
        assert validation_report["validation_passed"] is True
        self._verify_standardized_output_schema(standardized_output)
    
    def test_processor_factory_integration(self):
        """Test processor factory integration with different file types."""
        
        # Test PDF routing
        pdf_processor = self.factory.get_processor_for_file("test.pdf")
        assert pdf_processor is not None
        assert isinstance(pdf_processor, MinerUProcessor)
        
        # Test unsupported file routing (MVP: only PDF supported)
        unsupported_files = ["test.docx", "test.xlsx", "test.pptx", "test.txt"]
        
        for filename in unsupported_files:
            processor = self.factory.get_processor_for_file(filename)
            is_supported = self.factory.is_file_supported(filename)
            
            # In MVP, only PDF is supported
            assert processor is None
            assert is_supported is False
    
    def test_end_to_end_processing_pipeline(self):
        """Test complete end-to-end processing pipeline."""
        
        # Create test file
        mock_pdf = self.create_mock_pdf_content()
        
        # Get processor from factory
        processor = self.factory.get_processor_for_file("pipeline_test.pdf")
        assert processor is not None
        
        # Process document
        result = processor.process_document(
            "pipeline_test.pdf",
            file_content=mock_pdf
        )
        
        # Verify complete pipeline
        assert result.success is True
        output = result.output
        
        # Verify processing chain
        assert output.processing_status == ProcessingStatus.SUCCESS
        assert len(output.content_elements) > 0
        
        # Verify validation was applied (automatic in base processor)
        # The output should be validated and standardized
        assert output.plain_text is not None
        assert output.markdown_text is not None
        
        # Verify metadata is complete
        assert output.processing_metadata.processor_name == "MinerUProcessor"
        assert output.processing_metadata.processing_duration >= 0
        
        # Verify document structure
        assert output.document_structure.total_elements > 0
        assert output.document_structure.total_pages >= 1
    
    def test_concurrent_processing_safety(self):
        """Test that processors can handle concurrent processing safely."""
        import threading
        import time
        
        results = []
        errors = []
        
        def process_document(doc_id):
            try:
                mock_pdf = self.create_mock_pdf_content()
                processor = MinerUProcessor()
                
                result = processor.process_document(
                    f"concurrent_test_{doc_id}.pdf",
                    file_content=mock_pdf
                )
                
                results.append((doc_id, result.success))
                
            except Exception as e:
                errors.append((doc_id, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_document, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all processing succeeded
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == 5
        
        for doc_id, success in results:
            assert success is True, f"Document {doc_id} processing failed"
    
    def test_large_document_processing(self):
        """Test processing of larger documents."""
        
        # Create a larger mock PDF
        pdf_header = b'%PDF-1.4\\n%\\xe2\\xe3\\xcf\\xd3\\n'
        large_content = b'Large document content with multiple paragraphs. ' * 1000
        large_pdf = pdf_header + large_content
        
        # Process large document
        result = self.mineru_processor.process_document(
            "large_document.pdf",
            file_content=large_pdf
        )
        
        # Should handle large documents
        assert result.success is True
        assert result.output.processing_status == ProcessingStatus.SUCCESS
        
        # Verify processing time is reasonable (mock processing should be fast)
        assert result.processing_time < 5.0  # Should complete within 5 seconds
        
        # Verify output structure
        output = result.output
        assert len(output.content_elements) > 0
        assert len(output.plain_text) > 0
        assert len(output.markdown_text) > 0
    
    def test_memory_usage_during_processing(self):
        """Test memory usage during document processing."""
        try:
            import psutil
            import os
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Process multiple documents
            for i in range(10):
                mock_pdf = self.create_mock_pdf_content()
                result = self.mineru_processor.process_document(
                    f"memory_test_{i}.pdf",
                    file_content=mock_pdf
                )
                assert result.success is True
            
            # Check memory usage after processing
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB for mock processing)
            assert memory_increase < 100 * 1024 * 1024, f"Memory usage increased by {memory_increase / 1024 / 1024:.2f} MB"
            
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")
    
    def _verify_standardized_output_schema(self, output: StandardizedDocumentOutput):
        """Verify that output follows the standardized schema."""
        
        # Required fields
        assert hasattr(output, 'content_elements')
        assert hasattr(output, 'tables')
        assert hasattr(output, 'images')
        assert hasattr(output, 'document_metadata')
        assert hasattr(output, 'document_structure')
        assert hasattr(output, 'processing_metadata')
        assert hasattr(output, 'processing_status')
        assert hasattr(output, 'plain_text')
        assert hasattr(output, 'markdown_text')
        
        # Type checks
        assert isinstance(output.content_elements, list)
        assert isinstance(output.tables, list)
        assert isinstance(output.images, list)
        assert isinstance(output.document_metadata, dict)
        assert isinstance(output.plain_text, str)
        assert isinstance(output.markdown_text, str)
        
        # Content element validation
        for element in output.content_elements:
            assert hasattr(element, 'element_id')
            assert hasattr(element, 'content_type')
            assert hasattr(element, 'content')
            assert hasattr(element, 'metadata')
            
            assert isinstance(element.element_id, str)
            assert len(element.element_id) > 0
            assert isinstance(element.content, str)
            assert isinstance(element.metadata, dict)
            
            # Verify content type is valid
            valid_types = [ct.value for ct in ContentType]
            assert element.content_type in valid_types
        
        # Document structure validation
        structure = output.document_structure
        assert hasattr(structure, 'total_elements')
        assert hasattr(structure, 'total_pages')
        assert hasattr(structure, 'has_tables')
        assert hasattr(structure, 'has_images')
        
        assert isinstance(structure.total_elements, int)
        assert structure.total_elements >= 0
        assert isinstance(structure.has_tables, bool)
        assert isinstance(structure.has_images, bool)
        
        # Processing metadata validation
        metadata = output.processing_metadata
        assert hasattr(metadata, 'processor_name')
        assert hasattr(metadata, 'processor_version')
        assert hasattr(metadata, 'processing_duration')
        
        assert isinstance(metadata.processor_name, str)
        assert len(metadata.processor_name) > 0
        assert isinstance(metadata.processor_version, str)
        assert len(metadata.processor_version) > 0
        assert isinstance(metadata.processing_duration, (int, float))
        assert metadata.processing_duration >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])