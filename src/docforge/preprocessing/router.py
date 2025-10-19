"""Document pre-processing router for file type detection and processor selection."""

import logging
import mimetypes
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessorType(str, Enum):
    """Available document processors."""
    MINERU_PDF = "mineru_pdf"
    MARKITDOWN_OFFICE = "markitdown_office"
    MARKITDOWN_EXCEL = "markitdown_excel"
    MARKITDOWN_POWERPOINT = "markitdown_powerpoint"
    MARKITDOWN_GENERIC = "markitdown_generic"
    TEXT_PLAIN = "text_plain"
    UNSUPPORTED = "unsupported"


class FileTypeCategory(str, Enum):
    """File type categories for processing."""
    PDF = "pdf"
    WORD_DOCUMENT = "word_document"
    EXCEL_SPREADSHEET = "excel_spreadsheet"
    POWERPOINT_PRESENTATION = "powerpoint_presentation"
    TEXT_DOCUMENT = "text_document"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


class DocumentPreprocessingRouter:
    """Routes documents to appropriate processors based on file type and metadata."""
    
    def __init__(self):
        self.supported_extensions = {
            # PDF files
            '.pdf': FileTypeCategory.PDF,
            
            # Word documents
            '.doc': FileTypeCategory.WORD_DOCUMENT,
            '.docx': FileTypeCategory.WORD_DOCUMENT,
            '.docm': FileTypeCategory.WORD_DOCUMENT,
            '.dot': FileTypeCategory.WORD_DOCUMENT,
            '.dotx': FileTypeCategory.WORD_DOCUMENT,
            '.dotm': FileTypeCategory.WORD_DOCUMENT,
            
            # Excel spreadsheets
            '.xls': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xlsx': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xlsm': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xlsb': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xlt': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xltx': FileTypeCategory.EXCEL_SPREADSHEET,
            '.xltm': FileTypeCategory.EXCEL_SPREADSHEET,
            '.csv': FileTypeCategory.EXCEL_SPREADSHEET,
            
            # PowerPoint presentations
            '.ppt': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.pptx': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.pptm': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.pot': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.potx': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.potm': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.pps': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.ppsx': FileTypeCategory.POWERPOINT_PRESENTATION,
            '.ppsm': FileTypeCategory.POWERPOINT_PRESENTATION,
            
            # Text documents
            '.txt': FileTypeCategory.TEXT_DOCUMENT,
            '.md': FileTypeCategory.TEXT_DOCUMENT,
            '.markdown': FileTypeCategory.TEXT_DOCUMENT,
            '.rst': FileTypeCategory.TEXT_DOCUMENT,
            '.rtf': FileTypeCategory.TEXT_DOCUMENT,
            
            # Images (for future OCR processing)
            '.jpg': FileTypeCategory.IMAGE,
            '.jpeg': FileTypeCategory.IMAGE,
            '.png': FileTypeCategory.IMAGE,
            '.gif': FileTypeCategory.IMAGE,
            '.bmp': FileTypeCategory.IMAGE,
            '.tiff': FileTypeCategory.IMAGE,
            '.tif': FileTypeCategory.IMAGE,
        }
        
        self.mime_type_mapping = {
            # PDF
            'application/pdf': FileTypeCategory.PDF,
            
            # Word documents
            'application/msword': FileTypeCategory.WORD_DOCUMENT,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileTypeCategory.WORD_DOCUMENT,
            'application/vnd.ms-word.document.macroEnabled.12': FileTypeCategory.WORD_DOCUMENT,
            
            # Excel spreadsheets
            'application/vnd.ms-excel': FileTypeCategory.EXCEL_SPREADSHEET,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileTypeCategory.EXCEL_SPREADSHEET,
            'application/vnd.ms-excel.sheet.macroEnabled.12': FileTypeCategory.EXCEL_SPREADSHEET,
            'text/csv': FileTypeCategory.EXCEL_SPREADSHEET,
            
            # PowerPoint presentations
            'application/vnd.ms-powerpoint': FileTypeCategory.POWERPOINT_PRESENTATION,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': FileTypeCategory.POWERPOINT_PRESENTATION,
            'application/vnd.ms-powerpoint.presentation.macroEnabled.12': FileTypeCategory.POWERPOINT_PRESENTATION,
            
            # Text documents
            'text/plain': FileTypeCategory.TEXT_DOCUMENT,
            'text/markdown': FileTypeCategory.TEXT_DOCUMENT,
            'text/x-rst': FileTypeCategory.TEXT_DOCUMENT,
            'application/rtf': FileTypeCategory.TEXT_DOCUMENT,
            
            # Images
            'image/jpeg': FileTypeCategory.IMAGE,
            'image/png': FileTypeCategory.IMAGE,
            'image/gif': FileTypeCategory.IMAGE,
            'image/bmp': FileTypeCategory.IMAGE,
            'image/tiff': FileTypeCategory.IMAGE,
        }
        
        # MVP: PDF processing with MinerU and basic text processing are supported
        # Other formats will be added in future iterations
        self.processor_mapping = {
            FileTypeCategory.PDF: ProcessorType.MINERU_PDF,
            FileTypeCategory.WORD_DOCUMENT: ProcessorType.MARKITDOWN_OFFICE,  # Basic MarkItDown support
            FileTypeCategory.EXCEL_SPREADSHEET: ProcessorType.MARKITDOWN_EXCEL,  # Basic MarkItDown support
            FileTypeCategory.POWERPOINT_PRESENTATION: ProcessorType.MARKITDOWN_POWERPOINT,  # Basic MarkItDown support
            FileTypeCategory.TEXT_DOCUMENT: ProcessorType.TEXT_PLAIN,  # Basic text processor
            FileTypeCategory.IMAGE: ProcessorType.UNSUPPORTED,  # Future: OCR support
            FileTypeCategory.UNSUPPORTED: ProcessorType.UNSUPPORTED,
        }
    
    def detect_file_type(
        self,
        filename: str,
        file_content: Optional[bytes] = None,
        mime_type: Optional[str] = None
    ) -> Tuple[FileTypeCategory, Dict[str, Any]]:
        """
        Detect file type based on filename, content, and MIME type.
        
        Args:
            filename: Name of the file
            file_content: Optional file content for magic number detection
            mime_type: Optional MIME type if already known
            
        Returns:
            Tuple of (FileTypeCategory, metadata dict)
        """
        try:
            # Input validation - handle invalid/empty filenames gracefully
            if not filename or not isinstance(filename, str) or filename.strip() == "":
                logger.warning(f"Invalid filename provided: '{filename}'")
                return FileTypeCategory.UNSUPPORTED, {
                    "filename": filename,
                    "detection_method": ["invalid_input"],
                    "confidence": 0.0,
                    "error": "Invalid or empty filename"
                }
            
            metadata = {
                "filename": filename,
                "detection_method": [],
                "confidence": 0.0,
                "file_size": len(file_content) if file_content else None,
                "mime_type": mime_type
            }
            
            detected_category = FileTypeCategory.UNSUPPORTED
            confidence = 0.0
            
            # Method 1: File extension detection
            file_path = Path(filename)
            extension = file_path.suffix.lower()
            
            if extension in self.supported_extensions:
                detected_category = self.supported_extensions[extension]
                confidence += 0.4
                metadata["detection_method"].append("file_extension")
                metadata["file_extension"] = extension
                logger.debug(f"File type detected by extension: {extension} -> {detected_category}")
            
            # Method 2: MIME type detection (higher priority than extension)
            if mime_type:
                if mime_type in self.mime_type_mapping:
                    mime_category = self.mime_type_mapping[mime_type]
                    if detected_category == FileTypeCategory.UNSUPPORTED:
                        detected_category = mime_category
                        confidence += 0.5
                    elif detected_category == mime_category:
                        confidence += 0.3  # Confirmation
                    else:
                        # MIME type conflicts with extension - MIME type wins
                        detected_category = mime_category
                        confidence = 0.6  # Higher confidence for MIME type override
                    metadata["detection_method"].append("mime_type")
                    logger.debug(f"File type detected by MIME type: {mime_type} -> {mime_category}")
            
            # Method 3: Guess MIME type from filename if not provided
            if not mime_type:
                guessed_mime, _ = mimetypes.guess_type(filename)
                if guessed_mime and guessed_mime in self.mime_type_mapping:
                    mime_category = self.mime_type_mapping[guessed_mime]
                    if detected_category == FileTypeCategory.UNSUPPORTED:
                        detected_category = mime_category
                        confidence += 0.3
                    elif detected_category == mime_category:
                        confidence += 0.2  # Confirmation
                    metadata["detection_method"].append("mime_guess")
                    metadata["guessed_mime_type"] = guessed_mime
                    logger.debug(f"File type guessed by MIME: {guessed_mime} -> {mime_category}")
            
            # Method 4: Magic number detection (basic implementation)
            if file_content and len(file_content) >= 8:
                magic_category = self._detect_by_magic_numbers(file_content)
                if magic_category != FileTypeCategory.UNSUPPORTED:
                    if detected_category == FileTypeCategory.UNSUPPORTED:
                        detected_category = magic_category
                        confidence += 0.6
                    elif detected_category == magic_category:
                        confidence += 0.4  # Strong confirmation
                    metadata["detection_method"].append("magic_numbers")
                    logger.debug(f"File type detected by magic numbers: {magic_category}")
            
            # Normalize confidence to 0-1 range
            metadata["confidence"] = min(confidence, 1.0)
            
            logger.info(f"File type detection for '{filename}': {detected_category} (confidence: {metadata['confidence']:.2f})")
            
            return detected_category, metadata
            
        except Exception as e:
            logger.error(f"Error detecting file type for '{filename}': {e}")
            return FileTypeCategory.UNSUPPORTED, {
                "filename": filename,
                "detection_method": ["error"],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _detect_by_magic_numbers(self, file_content: bytes) -> FileTypeCategory:
        """Detect file type using magic numbers (file signatures)."""
        try:
            # PDF files
            if file_content.startswith(b'%PDF-'):
                return FileTypeCategory.PDF
            
            # Office documents (ZIP-based)
            if file_content.startswith(b'PK\x03\x04'):
                # This is a ZIP file, could be Office document
                # More sophisticated detection would be needed to distinguish
                # between different Office formats
                return FileTypeCategory.WORD_DOCUMENT  # Default assumption
            
            # Legacy Office documents
            if file_content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                # Microsoft Office Compound Document
                return FileTypeCategory.WORD_DOCUMENT  # Default assumption
            
            # Text files (UTF-8 BOM)
            if file_content.startswith(b'\xef\xbb\xbf'):
                return FileTypeCategory.TEXT_DOCUMENT
            
            # Image files
            if file_content.startswith(b'\xff\xd8\xff'):  # JPEG
                return FileTypeCategory.IMAGE
            elif file_content.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return FileTypeCategory.IMAGE
            elif file_content.startswith(b'GIF8'):  # GIF
                return FileTypeCategory.IMAGE
            elif file_content.startswith(b'BM'):  # BMP
                return FileTypeCategory.IMAGE
            
            return FileTypeCategory.UNSUPPORTED
            
        except Exception as e:
            logger.error(f"Error in magic number detection: {e}")
            return FileTypeCategory.UNSUPPORTED
    
    def select_processor(
        self,
        file_category: FileTypeCategory,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[ProcessorType, Dict[str, Any]]:
        """
        Select appropriate processor for the given file category.
        
        Args:
            file_category: Detected file category
            metadata: Optional metadata for processor selection
            
        Returns:
            Tuple of (ProcessorType, processor_config dict)
        """
        try:
            metadata = metadata or {}
            
            # Get base processor type
            processor_type = self.processor_mapping.get(file_category, ProcessorType.UNSUPPORTED)
            
            # Create processor configuration
            processor_config = {
                "processor_type": processor_type.value,
                "file_category": file_category.value,
                "priority": self._get_processor_priority(processor_type),
                "estimated_processing_time": self._estimate_processing_time(file_category, metadata),
                "required_resources": self._get_required_resources(processor_type),
                "output_format": self._get_output_format(processor_type)
            }
            
            # Add processor-specific configuration
            if processor_type == ProcessorType.MINERU_PDF:
                processor_config.update({
                    "extract_images": True,
                    "extract_tables": True,
                    "ocr_enabled": True,
                    "language": "auto"
                })
            elif processor_type in [ProcessorType.MARKITDOWN_OFFICE, ProcessorType.MARKITDOWN_EXCEL, ProcessorType.MARKITDOWN_POWERPOINT]:
                processor_config.update({
                    "preserve_formatting": True,
                    "extract_metadata": True,
                    "convert_tables": True
                })
            elif processor_type == ProcessorType.TEXT_PLAIN:
                processor_config.update({
                    "encoding": "utf-8",
                    "preserve_whitespace": True
                })
            
            logger.info(f"Selected processor: {processor_type} for category: {file_category}")
            
            return processor_type, processor_config
            
        except Exception as e:
            logger.error(f"Error selecting processor for category '{file_category}': {e}")
            return ProcessorType.UNSUPPORTED, {
                "processor_type": ProcessorType.UNSUPPORTED.value,
                "error": str(e)
            }
    
    def _get_processor_priority(self, processor_type: ProcessorType) -> int:
        """Get processing priority for the processor type."""
        priority_map = {
            ProcessorType.TEXT_PLAIN: 1,  # Fastest
            ProcessorType.MARKITDOWN_OFFICE: 2,
            ProcessorType.MARKITDOWN_EXCEL: 3,
            ProcessorType.MARKITDOWN_POWERPOINT: 4,
            ProcessorType.MINERU_PDF: 5,  # Most resource intensive
            ProcessorType.UNSUPPORTED: 10
        }
        return priority_map.get(processor_type, 10)
    
    def _estimate_processing_time(self, file_category: FileTypeCategory, metadata: Dict[str, Any]) -> int:
        """Estimate processing time in seconds based on file category and size."""
        file_size = metadata.get("file_size", 0)
        
        # Base time estimates (in seconds)
        base_times = {
            FileTypeCategory.TEXT_DOCUMENT: 1,
            FileTypeCategory.WORD_DOCUMENT: 5,
            FileTypeCategory.EXCEL_SPREADSHEET: 10,
            FileTypeCategory.POWERPOINT_PRESENTATION: 15,
            FileTypeCategory.PDF: 20,
            FileTypeCategory.IMAGE: 30,
            FileTypeCategory.UNSUPPORTED: 0
        }
        
        base_time = base_times.get(file_category, 10)
        
        # Scale by file size (rough estimate: +1 second per MB)
        if file_size:
            size_factor = max(1, file_size / (1024 * 1024))  # MB
            return int(base_time * size_factor)
        
        return base_time
    
    def _get_required_resources(self, processor_type: ProcessorType) -> Dict[str, Any]:
        """Get required resources for the processor type."""
        resource_map = {
            ProcessorType.TEXT_PLAIN: {
                "memory_mb": 50,
                "cpu_cores": 1,
                "disk_space_mb": 10
            },
            ProcessorType.MARKITDOWN_OFFICE: {
                "memory_mb": 200,
                "cpu_cores": 1,
                "disk_space_mb": 50
            },
            ProcessorType.MARKITDOWN_EXCEL: {
                "memory_mb": 300,
                "cpu_cores": 1,
                "disk_space_mb": 100
            },
            ProcessorType.MARKITDOWN_POWERPOINT: {
                "memory_mb": 400,
                "cpu_cores": 1,
                "disk_space_mb": 150
            },
            ProcessorType.MINERU_PDF: {
                "memory_mb": 1000,
                "cpu_cores": 2,
                "disk_space_mb": 500,
                "gpu_optional": True
            },
            ProcessorType.UNSUPPORTED: {
                "memory_mb": 0,
                "cpu_cores": 0,
                "disk_space_mb": 0
            }
        }
        return resource_map.get(processor_type, resource_map[ProcessorType.UNSUPPORTED])
    
    def _get_output_format(self, processor_type: ProcessorType) -> str:
        """Get expected output format for the processor type."""
        format_map = {
            ProcessorType.TEXT_PLAIN: "text/plain",
            ProcessorType.MARKITDOWN_OFFICE: "text/markdown",
            ProcessorType.MARKITDOWN_EXCEL: "text/markdown",
            ProcessorType.MARKITDOWN_POWERPOINT: "text/markdown",
            ProcessorType.MINERU_PDF: "application/json",  # Structured output
            ProcessorType.UNSUPPORTED: "application/octet-stream"
        }
        return format_map.get(processor_type, "application/octet-stream")
    
    def route_document(
        self,
        filename: str,
        file_content: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete routing decision for a document.
        
        Args:
            filename: Name of the file
            file_content: Optional file content
            mime_type: Optional MIME type
            user_preferences: Optional user preferences for processing
            
        Returns:
            Complete routing decision with processor and configuration
        """
        try:
            # Detect file type
            file_category, detection_metadata = self.detect_file_type(
                filename, file_content, mime_type
            )
            
            # Select processor
            processor_type, processor_config = self.select_processor(
                file_category, detection_metadata
            )
            
            # Apply user preferences if provided
            if user_preferences:
                processor_config = self._apply_user_preferences(
                    processor_config, user_preferences
                )
            
            # Create routing decision
            routing_decision = {
                "filename": filename,
                "file_category": file_category.value,
                "processor_type": processor_type.value,
                "processor_config": processor_config,
                "detection_metadata": detection_metadata,
                "routing_timestamp": self._get_timestamp(),
                "can_process": processor_type != ProcessorType.UNSUPPORTED,
                "routing_confidence": detection_metadata.get("confidence", 0.0)
            }
            
            logger.info(f"Document routing complete for '{filename}': {processor_type} (confidence: {routing_decision['routing_confidence']:.2f})")
            
            return routing_decision
            
        except Exception as e:
            logger.error(f"Error routing document '{filename}': {e}")
            return {
                "filename": filename,
                "file_category": FileTypeCategory.UNSUPPORTED.value,
                "processor_type": ProcessorType.UNSUPPORTED.value,
                "processor_config": {},
                "detection_metadata": {"error": str(e)},
                "routing_timestamp": self._get_timestamp(),
                "can_process": False,
                "routing_confidence": 0.0,
                "error": str(e)
            }
    
    def _apply_user_preferences(
        self,
        processor_config: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply user preferences to processor configuration."""
        try:
            # Create a copy to avoid modifying the original
            config = processor_config.copy()
            
            # Apply OCR preferences
            if "ocr_enabled" in user_preferences:
                config["ocr_enabled"] = user_preferences["ocr_enabled"]
            
            # Apply language preferences
            if "language" in user_preferences:
                config["language"] = user_preferences["language"]
            
            # Apply quality preferences
            if "quality" in user_preferences:
                quality = user_preferences["quality"]
                if quality == "high":
                    config["extract_images"] = True
                    config["extract_tables"] = True
                    config["preserve_formatting"] = True
                elif quality == "fast":
                    config["extract_images"] = False
                    config["extract_tables"] = False
                    config["preserve_formatting"] = False
            
            return config
            
        except Exception as e:
            logger.error(f"Error applying user preferences: {e}")
            return processor_config
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_supported_file_types(self) -> Dict[str, List[str]]:
        """Get list of supported file types by category."""
        supported_types = {}
        
        for extension, category in self.supported_extensions.items():
            category_name = category.value
            if category_name not in supported_types:
                supported_types[category_name] = []
            supported_types[category_name].append(extension)
        
        return supported_types
    
    def is_file_supported(self, filename: str) -> bool:
        """Check if a file type is supported for processing."""
        file_category, _ = self.detect_file_type(filename)
        if file_category == FileTypeCategory.UNSUPPORTED:
            return False
        
        # Check if there's actually a processor available for this file type
        processor_type = self.processor_mapping.get(file_category, ProcessorType.UNSUPPORTED)
        return processor_type != ProcessorType.UNSUPPORTED