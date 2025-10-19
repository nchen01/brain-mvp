"""Base processor interface for document processing."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from .schemas import (
    ProcessingResult,
    StandardizedDocumentOutput,
    ProcessorError,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


class BaseDocumentProcessor(ABC):
    """Base class for all document processors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.processor_name = self.__class__.__name__
        self.processor_version = "1.0.0"
        
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported file extensions (e.g., ['.pdf', '.docx'])
        """
        pass
    
    @abstractmethod
    def _process_document(
        self,
        file_path: str,
        file_content: bytes,
        **kwargs
    ) -> StandardizedDocumentOutput:
        """
        Process the document and return standardized output.
        
        Args:
            file_path: Path to the document file
            file_content: Raw file content
            **kwargs: Additional processing parameters
            
        Returns:
            StandardizedDocumentOutput with processed content
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    def process_document(
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Process a document and return the result.
        
        Args:
            file_path: Path to the document file
            file_content: Optional raw file content (will read from file if not provided)
            **kwargs: Additional processing parameters
            
        Returns:
            ProcessingResult with success status and output or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting document processing with {self.processor_name}: {file_path}")
            
            # Validate input
            if not file_path:
                raise ValueError("File path is required")
            
            # Read file content if not provided
            if file_content is None:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                with open(file_path_obj, 'rb') as f:
                    file_content = f.read()
            
            # Check if format is supported
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in self.get_supported_formats():
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Process the document
            output = self._process_document(file_path, file_content, **kwargs)
            
            # Validate and standardize the output
            from .output_validator import validate_and_standardize_output
            is_valid, standardized_output, validation_report = validate_and_standardize_output(output)
            
            if not is_valid:
                logger.warning(f"Output validation failed for {file_path}: {validation_report.get('errors', [])}")
                # Log validation errors but continue with standardized output
                for error in validation_report.get('errors', []):
                    logger.error(f"Validation error: {error}")
            
            if validation_report.get('warnings'):
                logger.info(f"Output validation warnings for {file_path}: {validation_report.get('warnings', [])}")
            
            processing_time = time.time() - start_time
            
            logger.info(f"Document processing completed successfully in {processing_time:.2f}s: {file_path}")
            
            return ProcessingResult(
                success=True,
                output=standardized_output,  # Use standardized output
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(f"Document processing failed after {processing_time:.2f}s: {file_path} - {str(e)}")
            
            error = ProcessorError(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=time.time(),
                stack_trace=self._get_stack_trace() if self.config.get("include_stack_trace", False) else None
            )
            
            return ProcessingResult(
                success=False,
                error=error,
                processing_time=processing_time
            )
    
    def can_process(self, file_path: str) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the processor can handle this file type
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            return file_extension in self.get_supported_formats()
        except Exception:
            return False
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get information about this processor.
        
        Returns:
            Dictionary with processor information
        """
        return {
            "name": self.processor_name,
            "version": self.processor_version,
            "supported_formats": self.get_supported_formats(),
            "config": self.config
        }
    
    def validate_config(self) -> List[str]:
        """
        Validate processor configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic validation - subclasses can override for specific validation
        if not isinstance(self.config, dict):
            errors.append("Config must be a dictionary")
        
        return errors
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace as string."""
        import traceback
        return traceback.format_exc()
    
    def _extract_metadata_from_path(self, file_path: str) -> Dict[str, Any]:
        """Extract basic metadata from file path."""
        try:
            path_obj = Path(file_path)
            
            metadata = {
                "filename": path_obj.name,
                "file_extension": path_obj.suffix.lower(),
                "file_stem": path_obj.stem,
                "file_size": path_obj.stat().st_size if path_obj.exists() else None,
                "file_path": str(path_obj.absolute())
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata from path {file_path}: {e}")
            return {"filename": file_path}


class ProcessorRegistry:
    """Registry for managing document processors."""
    
    def __init__(self):
        self._processors: Dict[str, BaseDocumentProcessor] = {}
    
    def register_processor(self, name: str, processor: BaseDocumentProcessor):
        """Register a processor."""
        if not isinstance(processor, BaseDocumentProcessor):
            raise ValueError("Processor must inherit from BaseDocumentProcessor")
        
        self._processors[name] = processor
        logger.info(f"Registered processor: {name}")
    
    def get_processor(self, name: str) -> Optional[BaseDocumentProcessor]:
        """Get a processor by name."""
        return self._processors.get(name)
    
    def get_processor_for_file(self, file_path: str) -> Optional[BaseDocumentProcessor]:
        """Get the best processor for a given file."""
        for processor in self._processors.values():
            if processor.can_process(file_path):
                return processor
        return None
    
    def list_processors(self) -> List[str]:
        """List all registered processor names."""
        return list(self._processors.keys())
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get all supported formats by processor."""
        formats = {}
        for name, processor in self._processors.items():
            formats[name] = processor.get_supported_formats()
        return formats


# Global processor registry
processor_registry = ProcessorRegistry()