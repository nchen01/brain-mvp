"""Advanced PDF processor using PyMuPDF, pdfplumber, and pdfminer libraries."""

import logging
import json
import tempfile
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .base_processor import BaseDocumentProcessor
from .schemas import ProcessingResult, ProcessorError, StandardizedDocumentOutput

logger = logging.getLogger(__name__)


class AdvancedPDFProcessor(BaseDocumentProcessor):
    """
    Advanced PDF processor using multiple PDF libraries for robust text extraction.
    
    This processor uses a multi-library approach with fallbacks:
    1. PyMuPDF (fitz) - Primary processor for text and metadata extraction
    2. pdfplumber - Fallback for complex layouts and table extraction  
    3. pdfminer - Final fallback for difficult PDFs
    
    Features:
    - Text extraction from simple and complex PDFs
    - Multi-page document processing with page breaks
    - Table detection and extraction
    - Metadata extraction from PDF properties
    - Graceful error handling with library fallbacks
    - Local processing (no external API dependencies)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Advanced PDF processor."""
        super().__init__(config)
        self.processor_name = "Advanced PDF Processor"
        self.supported_formats = ['.pdf']
        
        # Try to import PDF processing libraries
        try:
            # Import available PDF libraries
            import fitz  # PyMuPDF
            import pdfplumber
            from pdfminer.high_level import extract_text
            
            self.libraries_available = True
            self.fitz = fitz
            self.pdfplumber = pdfplumber
            self.extract_text = extract_text
            logger.info("PDF processing libraries loaded (PyMuPDF, pdfplumber, pdfminer). Ready for advanced PDF processing.")
            
        except ImportError as e:
            self.libraries_available = False
            logger.warning(f"PDF libraries not available: {e}. Using mock processing for development.")
        except Exception as e:
            self.libraries_available = False
            logger.error(f"Error initializing PDF libraries: {e}. Using mock processing.")
    
    def get_supported_formats(self) -> List[str]:
        """Get supported PDF formats."""
        return ['.pdf']
    
    def _process_document(self, file_path: str, file_content: bytes, **kwargs) -> StandardizedDocumentOutput:
        """Process document using the base class interface."""
        # Convert to our ProcessingResult format first
        result = self.process_document(
            filename=os.path.basename(file_path),
            file_content=file_content,
            file_path=file_path
        )
        
        if result.success:
            return result.output
        else:
            raise Exception(f"Processing failed: {result.error.error_message}")
    
    def process_document(self, filename: str, file_content: bytes = None, file_path: str = None) -> ProcessingResult:
        """Process PDF document using advanced multi-library approach."""
        try:
            logger.info(f"Processing PDF document: {filename}")
            
            # Use real PDF processing if libraries are available
            if self.libraries_available:
                logger.info("Using advanced multi-library PDF processing")
                return self._process_with_advanced_libraries(filename, file_content, file_path)
            else:
                logger.info("Using mock PDF processing")
                mock_result = self._mock_pdf_processing(file_path or filename, file_content)
                
                # Create simple content element
                from .schemas import ContentType, ProcessingStatus, create_content_element, create_processing_metadata, create_standardized_output
                
                content_elements = [
                    create_content_element(
                        element_id="text_1",
                        content_type=ContentType.TEXT,
                        content=mock_result.get('content', ''),
                        metadata={"source": "mock"}
                    )
                ]
                
                processing_metadata = create_processing_metadata(
                    processor_name=self.processor_name,
                    processor_version="1.0.0-mock",
                    processing_duration=mock_result.get('processing_time', 0.1),
                    input_file_info={"filename": filename},
                    processing_parameters={"mode": "mock"}
                )
                
                output = create_standardized_output(
                    content_elements=content_elements,
                    processing_metadata=processing_metadata,
                    processing_status=ProcessingStatus.SUCCESS,
                    total_pages=mock_result.get('total_pages', 1)
                )
                
                return ProcessingResult(
                    success=True,
                    output=output,
                    processing_time=mock_result.get('processing_time', 0.1)
                )
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return ProcessingResult(
                success=False,
                error=ProcessorError(
                    error_type="PDFProcessingError",
                    error_message=str(e),
                    timestamp=datetime.now()
                ),
                processing_time=0.0
            )
    
    def _process_with_advanced_libraries(self, filename: str, file_content: bytes = None, file_path: str = None) -> ProcessingResult:
        """Process PDF using advanced PDF libraries (PyMuPDF, pdfplumber, pdfminer)."""
        import tempfile
        import os
        import time
        from pathlib import Path
        
        temp_file = None
        start_time = time.time()
        
        try:
            # Create temporary file if we have file_content and no valid file_path
            if file_content and (not file_path or not os.path.exists(file_path)):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(file_content)
                temp_file.close()
                file_path = temp_file.name
                logger.info(f"Created temp file for processing: {file_path}")

            if not file_path or not os.path.exists(file_path):
                raise ValueError("No valid file path provided for PDF processing")
            
            logger.info(f"Processing PDF with advanced libraries: {file_path}")
            
            # Multi-library PDF processing for best results
            extracted_content = ""
            metadata = {
                'processor': 'Advanced PDF Processor',
                'libraries_used': [],
                'processing_method': 'multi-library'
            }
            
            # Method 1: Try PyMuPDF (fitz) - excellent for text and metadata
            try:
                doc = self.fitz.open(file_path)
                metadata['pages_processed'] = len(doc)
                metadata['pdf_metadata'] = doc.metadata
                
                pymupdf_text = ""
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pymupdf_text += page.get_text()
                    pymupdf_text += "\n\n"  # Add page breaks
                
                if pymupdf_text.strip():
                    extracted_content = pymupdf_text.strip()
                    metadata['libraries_used'].append('PyMuPDF')
                
                doc.close()
                logger.info(f"PyMuPDF extracted {len(extracted_content)} characters")
                
            except Exception as e:
                logger.warning(f"PyMuPDF processing failed: {e}")
            
            # Method 2: Try pdfplumber if PyMuPDF didn't get good results
            if len(extracted_content) < 100:  # If we didn't get much text
                try:
                    with self.pdfplumber.open(file_path) as pdf:
                        pdfplumber_text = ""
                        tables_detected = 0
                        
                        for page in pdf.pages:
                            # Extract text
                            page_text = page.extract_text()
                            if page_text:
                                pdfplumber_text += page_text + "\n\n"
                            
                            # Extract tables
                            tables = page.extract_tables()
                            if tables:
                                tables_detected += len(tables)
                                for table in tables:
                                    # Convert table to text
                                    for row in table:
                                        if row:
                                            pdfplumber_text += " | ".join([cell or "" for cell in row]) + "\n"
                                    pdfplumber_text += "\n"
                        
                        if len(pdfplumber_text.strip()) > len(extracted_content):
                            extracted_content = pdfplumber_text.strip()
                            metadata['libraries_used'].append('pdfplumber')
                            metadata['tables_detected'] = tables_detected
                            metadata['pages_processed'] = len(pdf.pages)
                        
                        logger.info(f"pdfplumber extracted {len(pdfplumber_text)} characters, {tables_detected} tables")
                        
                except Exception as e:
                    logger.warning(f"pdfplumber processing failed: {e}")
            
            # Method 3: Fallback to pdfminer if others failed
            if len(extracted_content) < 50:  # If we still don't have good text
                try:
                    pdfminer_text = self.extract_text(file_path)
                    if pdfminer_text and len(pdfminer_text.strip()) > len(extracted_content):
                        extracted_content = pdfminer_text.strip()
                        metadata['libraries_used'].append('pdfminer')
                    
                    logger.info(f"pdfminer extracted {len(pdfminer_text)} characters")
                    
                except Exception as e:
                    logger.warning(f"pdfminer processing failed: {e}")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            metadata['processing_time'] = processing_time
            
            # Ensure we have some content
            if not extracted_content:
                extracted_content = "[PDF processing completed but no text content was extracted. This may be a scanned PDF or contain only images.]"
            
            # Create standardized output
            from .schemas import ContentType, ProcessingStatus, create_content_element, create_processing_metadata, create_standardized_output
            
            content_elements = [
                create_content_element(
                    element_id="pdf_content_1",
                    content_type=ContentType.TEXT,
                    content=extracted_content,
                    metadata={
                        "libraries_used": metadata.get('libraries_used', []),
                        "pages_processed": metadata.get('pages_processed', 0),
                        "tables_detected": metadata.get('tables_detected', 0)
                    }
                )
            ]
            
            processing_metadata = create_processing_metadata(
                processor_name=self.processor_name,
                processor_version="1.0.0-advanced",
                processing_duration=processing_time,
                input_file_info={"filename": filename},
                processing_parameters={
                    "libraries_used": metadata.get('libraries_used', []),
                    "processing_method": "multi-library"
                }
            )
            
            output = create_standardized_output(
                content_elements=content_elements,
                processing_metadata=processing_metadata,
                processing_status=ProcessingStatus.SUCCESS,
                total_pages=metadata.get('pages_processed')
            )
            
            logger.info(f"Advanced PDF processing completed. Extracted {len(extracted_content)} characters using {metadata['libraries_used']}")
            
            return ProcessingResult(
                success=True,
                output=output,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Advanced PDF processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=ProcessorError(
                    error_type="PDFProcessingError",
                    error_message=f"PDF processing failed: {str(e)}",
                    timestamp=datetime.now()
                ),
                processing_time=0.0
            )
        
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    
    def _mock_pdf_processing(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """Mock processing for when PDF libraries are not available."""
        return {
            'content': 'Mock PDF content extracted from ' + os.path.basename(file_path),
            'metadata': {
                'processor': 'Mock Advanced PDF Processor',
                'pages': 1,
                'processing_method': 'mock'
            },
            'processing_time': 0.1,
            'pages': 1
        }