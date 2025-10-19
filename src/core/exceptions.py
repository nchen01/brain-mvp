"""Custom exceptions for Brain MVP."""

from typing import Any, Dict, Optional


class BrainMVPException(Exception):
    """Base exception for Brain MVP."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BRAIN_MVP_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DocumentProcessingError(BrainMVPException):
    """Exception raised during document processing."""
    
    def __init__(
        self,
        message: str,
        doc_uuid: Optional[str] = None,
        stage: Optional[str] = None,
        processor: Optional[str] = None
    ):
        details = {}
        if doc_uuid:
            details["doc_uuid"] = doc_uuid
        if stage:
            details["stage"] = stage
        if processor:
            details["processor"] = processor
            
        super().__init__(
            message=message,
            error_code="DOCUMENT_PROCESSING_ERROR",
            details=details
        )


class DocumentNotFoundError(BrainMVPException):
    """Exception raised when document is not found."""
    
    def __init__(self, doc_uuid: str):
        super().__init__(
            message=f"Document not found: {doc_uuid}",
            error_code="DOCUMENT_NOT_FOUND",
            details={"doc_uuid": doc_uuid}
        )


class DocumentVersionError(BrainMVPException):
    """Exception raised for document version-related errors."""
    
    def __init__(
        self,
        message: str,
        lineage_uuid: Optional[str] = None,
        version_number: Optional[int] = None
    ):
        details = {}
        if lineage_uuid:
            details["lineage_uuid"] = lineage_uuid
        if version_number:
            details["version_number"] = version_number
            
        super().__init__(
            message=message,
            error_code="DOCUMENT_VERSION_ERROR",
            details=details
        )


class DuplicateDocumentError(BrainMVPException):
    """Exception raised when duplicate document is detected."""
    
    def __init__(self, file_hash: str, existing_doc_uuid: str):
        super().__init__(
            message=f"Duplicate document detected",
            error_code="DUPLICATE_DOCUMENT",
            details={
                "file_hash": file_hash,
                "existing_doc_uuid": existing_doc_uuid
            }
        )


class UnsupportedFileFormatError(BrainMVPException):
    """Exception raised for unsupported file formats."""
    
    def __init__(self, file_type: str, supported_formats: list):
        super().__init__(
            message=f"Unsupported file format: {file_type}",
            error_code="UNSUPPORTED_FILE_FORMAT",
            details={
                "file_type": file_type,
                "supported_formats": supported_formats
            }
        )


class AuthenticationError(BrainMVPException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(BrainMVPException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR"
        )


class RAGIndexError(BrainMVPException):
    """Exception raised for RAG indexing errors."""
    
    def __init__(self, message: str, doc_uuid: Optional[str] = None):
        details = {}
        if doc_uuid:
            details["doc_uuid"] = doc_uuid
            
        super().__init__(
            message=message,
            error_code="RAG_INDEX_ERROR",
            details=details
        )