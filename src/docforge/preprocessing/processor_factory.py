"""Processor factory for creating and managing document processors."""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base_processor import BaseDocumentProcessor, processor_registry
from .text_processor import TextDocumentProcessor
from .mineru_processor import MinerUProcessor
from .markitdown_processor import MarkItDownProcessor
from .router import DocumentPreprocessingRouter, ProcessorType

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """Factory for creating and managing document processors."""
    
    def __init__(self):
        """Initialize the processor factory."""
        self.router = DocumentPreprocessingRouter()
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Initialize and register all available processors."""
        try:
            # Register all processors for full functionality

            # MinerU PDF processor (primary PDF processor with fallback to AdvancedPDFProcessor)
            mineru_processor = MinerUProcessor()
            processor_registry.register_processor("mineru", mineru_processor)

            # Log MinerU availability status
            if mineru_processor.is_available():
                logger.info("MinerU processor initialized (magic-pdf available)")
            else:
                logger.info("MinerU processor initialized (using AdvancedPDFProcessor fallback)")

            # Text processor for basic text files
            text_processor = TextDocumentProcessor()
            processor_registry.register_processor("text", text_processor)

            # MarkItDown processor for Office documents (placeholder)
            markitdown_processor = MarkItDownProcessor()
            processor_registry.register_processor("markitdown", markitdown_processor)

            logger.info("All processors initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing processors: {e}")
            # Don't raise - allow system to work with available processors
            logger.warning("Some processors may not be available - continuing with available ones")
    
    def get_processor_for_file(
        self,
        filename: str,
        file_content: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseDocumentProcessor]:
        """
        Get the appropriate processor for a file.
        
        Args:
            filename: Name of the file
            file_content: Optional file content for better detection
            mime_type: Optional MIME type
            user_preferences: Optional user preferences
            
        Returns:
            Appropriate processor or None if unsupported
        """
        try:
            # Route the document to get processor type
            routing_decision = self.router.route_document(
                filename=filename,
                file_content=file_content,
                mime_type=mime_type,
                user_preferences=user_preferences
            )
            
            if not routing_decision["can_process"]:
                logger.warning(f"No processor available for file: {filename}")
                return None
            
            processor_type = routing_decision["processor_type"]
            
            # Map processor types to registered processors
            processor_mapping = {
                ProcessorType.MINERU_PDF.value: "mineru",
                ProcessorType.TEXT_PLAIN.value: "text",
                # Future processors:
                # ProcessorType.MARKITDOWN_OFFICE.value: "markitdown",
                # ProcessorType.MARKITDOWN_EXCEL.value: "markitdown",
                # ProcessorType.MARKITDOWN_POWERPOINT.value: "markitdown",
                # ProcessorType.MARKITDOWN_GENERIC.value: "markitdown"
            }
            
            processor_name = processor_mapping.get(processor_type)
            if not processor_name:
                logger.error(f"No processor mapping for type: {processor_type}")
                return None
            
            processor = processor_registry.get_processor(processor_name)
            if not processor:
                logger.error(f"Processor not found in registry: {processor_name}")
                return None
            
            # Configure processor with routing decision
            processor_config = routing_decision.get("processor_config", {})
            if hasattr(processor, 'update_config'):
                processor.update_config(processor_config)
            
            logger.info(f"Selected processor '{processor_name}' for file: {filename}")
            return processor
            
        except Exception as e:
            logger.error(f"Error selecting processor for file {filename}: {e}")
            return None
    
    def get_routing_decision(
        self,
        filename: str,
        file_content: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get routing decision for a file without creating processor.
        
        Args:
            filename: Name of the file
            file_content: Optional file content for better detection
            mime_type: Optional MIME type
            user_preferences: Optional user preferences
            
        Returns:
            Routing decision dictionary
        """
        return self.router.route_document(
            filename=filename,
            file_content=file_content,
            mime_type=mime_type,
            user_preferences=user_preferences
        )
    
    def list_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get all supported file formats.
        
        Returns:
            Dictionary mapping processor names to supported formats
        """
        return processor_registry.get_supported_formats()
    
    def is_file_supported(self, filename: str) -> bool:
        """
        Check if a file is supported by any processor.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file is supported
        """
        return self.router.is_file_supported(filename)
    
    def get_processor_info(self, processor_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific processor.
        
        Args:
            processor_name: Name of the processor
            
        Returns:
            Processor information or None if not found
        """
        processor = processor_registry.get_processor(processor_name)
        if processor:
            return processor.get_processor_info()
        return None
    
    def validate_all_processors(self) -> Dict[str, List[str]]:
        """
        Validate all registered processors.
        
        Returns:
            Dictionary mapping processor names to validation errors
        """
        validation_results = {}
        
        for processor_name in processor_registry.list_processors():
            processor = processor_registry.get_processor(processor_name)
            if processor:
                errors = processor.validate_config()
                validation_results[processor_name] = errors
        
        return validation_results
    
    def create_processor_with_config(
        self,
        processor_type: str,
        config: Dict[str, Any]
    ) -> Optional[BaseDocumentProcessor]:
        """
        Create a processor instance with custom configuration.
        
        Args:
            processor_type: Type of processor to create
            config: Configuration dictionary
            
        Returns:
            Configured processor instance or None if invalid type
        """
        try:
            # MVP: Only MinerU processor is supported
            if processor_type == "mineru":
                return MinerUProcessor(config)
            else:
                logger.warning(f"Processor type '{processor_type}' not supported in MVP. Only 'mineru' (PDF) is available.")
                return None
                
            # Future processors:
            # elif processor_type == "text":
            #     return TextDocumentProcessor(config)
            # elif processor_type == "markitdown":
            #     return MarkItDownProcessor(config)
                
        except Exception as e:
            logger.error(f"Error creating processor {processor_type}: {e}")
            return None
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about available processors.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_processors": len(processor_registry.list_processors()),
            "processors": processor_registry.list_processors(),
            "supported_formats": self.list_supported_formats(),
            "router_supported_types": self.router.get_supported_file_types()
        }
        
        return stats


# Global processor factory instance
processor_factory = ProcessorFactory()