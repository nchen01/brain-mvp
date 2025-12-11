"""Document management API endpoints with versioning support."""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import hashlib

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import io

# Import our system components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from docforge.versioning.versions import VersionManager
from docforge.versioning.models import DocumentRegistrationRequest, DocumentRegistrationResponse, DocumentVersionModel, VersionBranchRequest
from core.exceptions import DocumentVersionError, DuplicateDocumentError
from docforge.preprocessing.processor_factory import ProcessorFactory
from docforge.postprocessing.router import PostProcessingRouter
from docforge.storage.post_document_db import PostDocumentDatabase
from docforge.storage.meta_document_db import MetaDocumentDatabase, MetaDocumentComponent
from docforge.storage.schemas import StorageConfig, DocumentMetadata
from docforge.rag.lightrag_integration import LightRAGIntegration
from storage.chunk_storage import ChunkStorage
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy
from config.config_manager import ConfigManager
from utils.error_handling import handle_async_errors, ErrorCategory, ErrorSeverity

# Import authentication
from api.routers.auth import get_current_user, get_current_user_optional, UserInfo

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Pydantic models for API requests/responses
class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str = Field(..., description="Unique document UUID")
    lineage_id: str = Field(..., description="Document lineage UUID")
    version_number: int = Field(..., description="Version number in lineage")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_hash: str = Field(..., description="SHA-256 hash of content")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    processing_status: str = Field(..., description="Current processing status")
    processing_queue_id: Optional[str] = Field(None, description="Background processing task ID")


class DocumentVersionInfo(BaseModel):
    """Document version information."""
    document_id: str
    lineage_id: str
    version_number: int
    filename: str
    file_size: int
    content_hash: str
    created_at: datetime
    parent_version_id: Optional[str] = None
    is_current: bool
    processing_status: str
    metadata: Dict[str, Any] = {}


class DocumentLineageResponse(BaseModel):
    """Document lineage information."""
    lineage_id: str
    total_versions: int
    current_version: DocumentVersionInfo
    version_history: List[DocumentVersionInfo]
    created_at: datetime
    last_modified: datetime


class ProcessingStatusResponse(BaseModel):
    """Processing status information."""
    document_id: str
    status: str = Field(..., description="Processing status: pending, processing, completed, failed")
    stage: str = Field(..., description="Current processing stage")
    progress: float = Field(..., description="Progress percentage (0-100)")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_details: Dict[str, Any] = {}


class DocumentSearchRequest(BaseModel):
    """Document search request."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum number of results")
    include_versions: bool = Field(False, description="Include all versions in results")
    lineage_filter: Optional[List[str]] = Field(None, description="Filter by lineage IDs")


class DocumentSearchResult(BaseModel):
    """Document search result."""
    document_id: str
    lineage_id: str
    version_number: int
    filename: str
    relevance_score: float
    snippet: str
    metadata: Dict[str, Any] = {}


# Dependency injection
async def get_version_manager() -> VersionManager:
    """Get version manager instance."""
    return VersionManager()


async def get_processor_factory() -> ProcessorFactory:
    """Get processor factory instance."""
    return ProcessorFactory()


async def get_config_manager() -> ConfigManager:
    """Get configuration manager instance."""
    return ConfigManager()


# Background processing tasks storage (in production, use Redis or similar)
processing_tasks: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parent_version_id: Optional[str] = Query(None, description="Parent version ID for branching"),
    metadata: Optional[str] = Query(None, description="JSON metadata string"),
    current_user: Optional[UserInfo] = Depends(get_current_user_optional),
    version_manager: VersionManager = Depends(get_version_manager),
    processor_factory: ProcessorFactory = Depends(get_processor_factory)
):
    """
    Upload a new document or create a new version of an existing document.
    
    - **file**: Document file to upload
    - **parent_version_id**: Optional parent version ID for creating branches
    - **metadata**: Optional JSON metadata string
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Calculate content hash
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Parse metadata if provided
        doc_metadata = {
            'uploaded_by': current_user.user_id if current_user else 'anonymous',
            'uploaded_by_username': current_user.username if current_user else 'anonymous',
            'upload_timestamp': datetime.now().isoformat()
        }
        if metadata:
            import json
            try:
                user_metadata = json.loads(metadata)
                doc_metadata.update(user_metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON metadata")
        
        # Check if this is a new document or version
        if parent_version_id:
            # Create new version of existing document
            logger.info(f"Creating new version with parent: {parent_version_id}")
            
            # Create branch request
            branch_request = VersionBranchRequest(
                lineage_uuid=parent_version_id, # This might be wrong, need to check if parent_version_id is lineage or version
                source_version=1, # This is also tricky without looking up the parent
                filename=file.filename,
                user_id=current_user.user_id if current_user else 'anonymous',
                file_size=file_size,
                metadata={
                    **doc_metadata,
                    'content_hash': content_hash
                }
            )
            
            # We need to look up the parent version first to get lineage and version number
            parent_version = await version_manager.get_version(parent_version_id)
            if not parent_version:
                raise HTTPException(status_code=404, detail="Parent version not found")
                
            branch_request.lineage_uuid = parent_version.lineage_uuid
            branch_request.source_version = parent_version.version_number
            
            # Create version branch
            version_response = await version_manager.create_version_branch(
                branch_request,
                file_content
            )
            
            version_result = version_response.doc_uuid
            document_id = version_response.doc_uuid
            
        else:
            # Create new document (new lineage)
            logger.info(f"Creating new document: {file.filename}")
            
            # Create registration request
            reg_request = DocumentRegistrationRequest(
                filename=file.filename,
                file_type=file.filename.split('.')[-1] if '.' in file.filename else 'unknown',
                file_size=file_size,
                user_id=current_user.user_id if current_user else 'anonymous',
                metadata={
                    **doc_metadata,
                    'content_hash': content_hash
                }
            )
            
            # Register version
            try:
                version_response = await version_manager.register_version(
                    reg_request,
                    file_content
                )
            except DuplicateDocumentError as e:
                logger.warning(f"Duplicate document detected: {e}")
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Document already exists",
                        "existing_document_id": e.details.get("existing_doc_uuid"),
                        "file_hash": e.details.get("file_hash")
                    }
                )
            
            version_result = version_response.doc_uuid
            document_id = version_response.doc_uuid
        
        # Get version info
        version_info = await version_manager.get_version(version_result)
        if not version_info:
            raise HTTPException(status_code=500, detail="Failed to retrieve created version")
        
        # Create processing task
        task_id = str(uuid.uuid4())
        processing_tasks[task_id] = {
            'document_id': version_info.doc_uuid,
            'version_id': version_result,
            'status': 'pending',
            'stage': 'queued',
            'progress': 0.0,
            'started_at': None,
            'completed_at': None,
            'error_message': None
        }
        
        # Start background processing
        background_tasks.add_task(
            process_document_async,
            version_info.doc_uuid, # Changed from version_result to version_info.doc_uuid
            file_content,
            file.filename,
            task_id
        )
        
        return DocumentUploadResponse(
            document_id=version_info.doc_uuid,
            lineage_id=version_info.lineage_uuid,
            version_number=version_info.version_number,
            filename=file.filename,
            file_size=file_size,
            content_hash=content_hash,
            upload_timestamp=datetime.now(),
            processing_status="pending",
            processing_queue_id=task_id
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{document_id}/versions", response_model=DocumentLineageResponse)
async def get_document_versions(
    document_id: str,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Get all versions of a document (lineage history).
    
    - **document_id**: Document UUID or lineage UUID
    """
    try:
        # Get all versions for this document
        versions = await version_manager.get_versions(document_id)
        
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Convert to API models
        version_infos = []
        current_version = None
        
        for version in versions:
            version_info = DocumentVersionInfo(
                document_id=version.document_id,
                lineage_id=version.document_id,  # Using document_id as lineage_id for now
                version_number=1,  # Will be properly calculated
                filename=version.metadata.get('filename', 'unknown'),
                file_size=version.metadata.get('file_size', 0),
                content_hash=version.metadata.get('content_hash', ''),
                created_at=version.created_at,
                parent_version_id=getattr(version, 'parent_version_id', None),
                is_current=True,  # Will be properly determined
                processing_status="completed",  # Will be properly determined
                metadata=version.metadata
            )
            
            version_infos.append(version_info)
            if current_version is None:
                current_version = version_info
        
        return DocumentLineageResponse(
            lineage_id=document_id,
            total_versions=len(version_infos),
            current_version=current_version,
            version_history=version_infos,
            created_at=min(v.created_at for v in version_infos),
            last_modified=max(v.created_at for v in version_infos)
        )
        
    except Exception as e:
        logger.error(f"Error getting document versions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")


@router.post("/{document_id}/branch", response_model=DocumentUploadResponse)
async def create_document_branch(
    document_id: str,
    version_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[str] = Query(None, description="JSON metadata string"),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Create a new branch from an existing version (edit old version).
    
    - **document_id**: Document UUID
    - **version_id**: Version UUID to branch from
    - **file**: New document content
    - **metadata**: Optional JSON metadata string
    """
    try:
        # Validate source version exists
        source_version = await version_manager.get_version(version_id)
        if not source_version or source_version.document_id != document_id:
            raise HTTPException(status_code=404, detail="Source version not found")
        
        # Read new file content
        file_content = await file.read()
        file_size = len(file_content)
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Parse metadata
        doc_metadata = {}
        if metadata:
            import json
            try:
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON metadata")
        
        # Create new version as branch
        new_version_id = version_manager.create_version(
            document_id=document_id,
            content=file_content.decode('utf-8', errors='ignore'),
            metadata={
                **doc_metadata,
                'filename': file.filename,
                'content_type': file.content_type,
                'file_size': file_size,
                'content_hash': content_hash,
                'branched_from': version_id
            },
            parent_version_id=version_id
        )
        
        # Create processing task
        task_id = str(uuid.uuid4())
        processing_tasks[task_id] = {
            'document_id': document_id,
            'version_id': new_version_id,
            'status': 'pending',
            'stage': 'queued',
            'progress': 0.0,
            'started_at': None,
            'completed_at': None,
            'error_message': None
        }
        
        # Start background processing
        background_tasks.add_task(
            process_document_async,
            new_version_id,
            file_content,
            file.filename,
            task_id
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            lineage_id=document_id,
            version_number=2,  # Will be properly calculated
            filename=file.filename,
            file_size=file_size,
            content_hash=content_hash,
            upload_timestamp=datetime.now(),
            processing_status="pending",
            processing_queue_id=task_id
        )
        
    except Exception as e:
        logger.error(f"Error creating document branch: {e}")
        raise HTTPException(status_code=500, detail=f"Branch creation failed: {str(e)}")


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    document_id: str,
    task_id: Optional[str] = Query(None, description="Processing task ID")
):
    """
    Get processing status for a document.
    
    - **document_id**: Document UUID
    - **task_id**: Optional processing task ID
    """
    try:
        # If task_id provided, get specific task status
        if task_id and task_id in processing_tasks:
            task = processing_tasks[task_id]
            return ProcessingStatusResponse(
                document_id=task['document_id'],
                status=task['status'],
                stage=task['stage'],
                progress=task['progress'],
                started_at=task['started_at'],
                completed_at=task['completed_at'],
                error_message=task['error_message'],
                processing_details={}
            )
        
        # Otherwise, find latest task for document
        latest_task = None
        for task in processing_tasks.values():
            if task['document_id'] == document_id:
                if latest_task is None or (task.get('started_at') and 
                    (not latest_task.get('started_at') or task['started_at'] > latest_task['started_at'])):
                    latest_task = task
        
        if latest_task:
            return ProcessingStatusResponse(
                document_id=document_id,
                status=latest_task['status'],
                stage=latest_task['stage'],
                progress=latest_task['progress'],
                started_at=latest_task['started_at'],
                completed_at=latest_task['completed_at'],
                error_message=latest_task['error_message'],
                processing_details={}
            )
        
        # No processing task found
        return ProcessingStatusResponse(
            document_id=document_id,
            status="unknown",
            stage="not_found",
            progress=0.0,
            processing_details={}
        )
        
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    version_id: Optional[str] = Query(None, description="Specific version ID"),
    format: str = Query("original", description="Download format: original, processed, markdown"),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Download a document in various formats.
    
    - **document_id**: Document UUID
    - **version_id**: Optional specific version ID
    - **format**: Download format (original, processed, markdown)
    """
    try:
        # Get version info
        if version_id:
            version = version_manager.get_version(version_id)
            if not version or version.document_id != document_id:
                raise HTTPException(status_code=404, detail="Version not found")
        else:
            # Get latest version
            versions = version_manager.get_versions(document_id)
            if not versions:
                raise HTTPException(status_code=404, detail="Document not found")
            version = versions[0]  # Assuming first is latest
        
        filename = version.metadata.get('filename', 'document')
        
        if format == "original":
            # Return original content
            content = version.content.encode('utf-8')
            media_type = version.metadata.get('content_type', 'application/octet-stream')
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        elif format == "processed":
            # Return processed content (would need to implement)
            raise HTTPException(status_code=501, detail="Processed format not yet implemented")
        
        elif format == "markdown":
            # Return markdown content (would need to implement)
            raise HTTPException(status_code=501, detail="Markdown format not yet implemented")
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
            
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


# Version Management Endpoints

class DocumentDeletionRequest(BaseModel):
    """Request model for document deletion."""
    reason: str = Field(..., description="Reason for deletion")
    permanent: bool = Field(False, description="Whether to permanently delete (vs soft delete)")


class DocumentRestoreRequest(BaseModel):
    """Request model for document restoration."""
    restore_reason: str = Field(..., description="Reason for restoration")


class DocumentComparisonRequest(BaseModel):
    """Request model for version comparison."""
    version_a_id: str = Field(..., description="First version ID")
    version_b_id: str = Field(..., description="Second version ID")
    comparison_type: str = Field("content", description="Type of comparison: content, metadata, structure")


class DocumentComparisonResponse(BaseModel):
    """Response model for version comparison."""
    version_a: DocumentVersionInfo
    version_b: DocumentVersionInfo
    differences: Dict[str, Any] = Field(..., description="Detailed differences between versions")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    comparison_summary: str = Field(..., description="Human-readable comparison summary")


@router.get("/{document_id}/versions/history", response_model=DocumentLineageResponse)
async def get_version_history(
    document_id: str,
    include_deleted: bool = Query(False, description="Include soft-deleted versions"),
    limit: int = Query(50, description="Maximum number of versions to return"),
    offset: int = Query(0, description="Number of versions to skip"),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Get detailed version history for a document lineage.
    
    - **document_id**: Document UUID or lineage UUID
    - **include_deleted**: Include soft-deleted versions in results
    - **limit**: Maximum number of versions to return
    - **offset**: Number of versions to skip for pagination
    """
    try:
        # Get versions with pagination
        versions = version_manager.get_versions(document_id)
        
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Apply pagination
        total_versions = len(versions)
        paginated_versions = versions[offset:offset + limit]
        
        # Convert to API models
        version_infos = []
        current_version = None
        
        for i, version in enumerate(paginated_versions):
            is_current = i == 0  # Assuming first is current
            
            version_info = DocumentVersionInfo(
                document_id=version.document_id,
                lineage_id=version.document_id,
                version_number=i + 1 + offset,
                filename=version.metadata.get('filename', 'unknown'),
                file_size=version.metadata.get('file_size', 0),
                content_hash=version.metadata.get('content_hash', ''),
                created_at=version.created_at,
                parent_version_id=getattr(version, 'parent_version_id', None),
                is_current=is_current,
                processing_status="completed",
                metadata=version.metadata
            )
            
            version_infos.append(version_info)
            if is_current:
                current_version = version_info
        
        return DocumentLineageResponse(
            lineage_id=document_id,
            total_versions=total_versions,
            current_version=current_version or version_infos[0],
            version_history=version_infos,
            created_at=min(v.created_at for v in version_infos),
            last_modified=max(v.created_at for v in version_infos)
        )
        
    except Exception as e:
        logger.error(f"Error getting version history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get version history: {str(e)}")


@router.delete("/{document_id}/versions/{version_id}")
async def delete_version(
    document_id: str,
    version_id: str,
    deletion_request: DocumentDeletionRequest,
    current_user: UserInfo = Depends(get_current_user),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Delete a specific version (soft delete by default).
    
    - **document_id**: Document UUID
    - **version_id**: Version UUID to delete
    - **deletion_request**: Deletion details including reason
    """
    try:
        # Validate version exists and belongs to document
        version = version_manager.get_version(version_id)
        if not version or version.document_id != document_id:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Check permissions - user can only delete their own documents or has admin role
        if (version.metadata.get('uploaded_by') != current_user.user_id and 
            'admin' not in current_user.roles and 
            'document:delete_all' not in current_user.permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete this document")
        
        # Perform deletion
        if deletion_request.permanent:
            # Permanent deletion (implement with caution)
            success = version_manager.delete_version_permanently(
                version_id, 
                reason=deletion_request.reason
            )
        else:
            # Soft deletion
            success = version_manager.soft_delete_version(
                version_id,
                reason=deletion_request.reason
            )
        
        if success:
            return {
                "message": "Version deleted successfully",
                "version_id": version_id,
                "deletion_type": "permanent" if deletion_request.permanent else "soft",
                "reason": deletion_request.reason,
                "deleted_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete version")
            
    except Exception as e:
        logger.error(f"Error deleting version: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.post("/{document_id}/versions/{version_id}/restore")
async def restore_version(
    document_id: str,
    version_id: str,
    restore_request: DocumentRestoreRequest,
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Restore a soft-deleted version.
    
    - **document_id**: Document UUID
    - **version_id**: Version UUID to restore
    - **restore_request**: Restoration details including reason
    """
    try:
        # Validate version exists and is deleted
        version = version_manager.get_version(version_id, include_deleted=True)
        if not version or version.document_id != document_id:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Check if version is actually deleted
        if not getattr(version, 'is_deleted', False):
            raise HTTPException(status_code=400, detail="Version is not deleted")
        
        # Restore version
        success = version_manager.restore_version(
            version_id,
            reason=restore_request.restore_reason
        )
        
        if success:
            return {
                "message": "Version restored successfully",
                "version_id": version_id,
                "restore_reason": restore_request.restore_reason,
                "restored_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to restore version")
            
    except Exception as e:
        logger.error(f"Error restoring version: {e}")
        raise HTTPException(status_code=500, detail=f"Restoration failed: {str(e)}")


@router.post("/{document_id}/versions/compare", response_model=DocumentComparisonResponse)
async def compare_versions(
    document_id: str,
    comparison_request: DocumentComparisonRequest,
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Compare two versions of a document.
    
    - **document_id**: Document UUID
    - **comparison_request**: Comparison details including version IDs and type
    """
    try:
        # Get both versions
        version_a = version_manager.get_version(comparison_request.version_a_id)
        version_b = version_manager.get_version(comparison_request.version_b_id)
        
        if not version_a or version_a.document_id != document_id:
            raise HTTPException(status_code=404, detail="Version A not found")
        
        if not version_b or version_b.document_id != document_id:
            raise HTTPException(status_code=404, detail="Version B not found")
        
        # Perform comparison
        comparison_result = version_manager.compare_versions(
            comparison_request.version_a_id,
            comparison_request.version_b_id
        )
        
        # Convert versions to API models
        version_a_info = DocumentVersionInfo(
            document_id=version_a.document_id,
            lineage_id=version_a.document_id,
            version_number=1,  # Will be calculated properly
            filename=version_a.metadata.get('filename', 'unknown'),
            file_size=version_a.metadata.get('file_size', 0),
            content_hash=version_a.metadata.get('content_hash', ''),
            created_at=version_a.created_at,
            is_current=False,
            processing_status="completed",
            metadata=version_a.metadata
        )
        
        version_b_info = DocumentVersionInfo(
            document_id=version_b.document_id,
            lineage_id=version_b.document_id,
            version_number=2,  # Will be calculated properly
            filename=version_b.metadata.get('filename', 'unknown'),
            file_size=version_b.metadata.get('file_size', 0),
            content_hash=version_b.metadata.get('content_hash', ''),
            created_at=version_b.created_at,
            is_current=False,
            processing_status="completed",
            metadata=version_b.metadata
        )
        
        return DocumentComparisonResponse(
            version_a=version_a_info,
            version_b=version_b_info,
            differences=comparison_result.get('differences', {}),
            similarity_score=comparison_result.get('similarity_score', 0.0),
            comparison_summary=comparison_result.get('summary', 'Comparison completed')
        )
        
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/{document_id}/lineage")
async def get_document_lineage(
    document_id: str,
    format: str = Query("tree", description="Response format: tree, list, graph"),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Get complete document lineage information.
    
    - **document_id**: Document UUID or lineage UUID
    - **format**: Response format (tree, list, graph)
    """
    try:
        # Get lineage information
        lineage_info = version_manager.get_lineage_info(document_id)
        
        if not lineage_info:
            raise HTTPException(status_code=404, detail="Document lineage not found")
        
        if format == "tree":
            # Return hierarchical tree structure
            return {
                "lineage_id": document_id,
                "format": "tree",
                "lineage_tree": lineage_info.get('tree_structure', {}),
                "total_versions": lineage_info.get('total_versions', 0),
                "branches": lineage_info.get('branches', []),
                "created_at": lineage_info.get('created_at'),
                "last_modified": lineage_info.get('last_modified')
            }
        
        elif format == "list":
            # Return flat list with relationships
            return {
                "lineage_id": document_id,
                "format": "list",
                "versions": lineage_info.get('version_list', []),
                "total_versions": lineage_info.get('total_versions', 0),
                "relationships": lineage_info.get('relationships', [])
            }
        
        elif format == "graph":
            # Return graph structure for visualization
            return {
                "lineage_id": document_id,
                "format": "graph",
                "nodes": lineage_info.get('graph_nodes', []),
                "edges": lineage_info.get('graph_edges', []),
                "metadata": lineage_info.get('graph_metadata', {})
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use: tree, list, or graph")
            
    except Exception as e:
        logger.error(f"Error getting document lineage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get lineage: {str(e)}")


@router.delete("/{document_id}/lineage")
async def delete_entire_lineage(
    document_id: str,
    deletion_request: DocumentDeletionRequest,
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Delete entire document lineage (for privacy compliance).
    
    - **document_id**: Document UUID or lineage UUID
    - **deletion_request**: Deletion details including reason
    """
    try:
        # Validate lineage exists
        lineage_info = version_manager.get_lineage_info(document_id)
        if not lineage_info:
            raise HTTPException(status_code=404, detail="Document lineage not found")
        
        # Perform lineage deletion
        if deletion_request.permanent:
            success = version_manager.delete_lineage_permanently(
                document_id,
                reason=deletion_request.reason
            )
        else:
            success = version_manager.soft_delete_lineage(
                document_id,
                reason=deletion_request.reason
            )
        
        if success:
            return {
                "message": "Document lineage deleted successfully",
                "lineage_id": document_id,
                "deletion_type": "permanent" if deletion_request.permanent else "soft",
                "reason": deletion_request.reason,
                "deleted_at": datetime.now().isoformat(),
                "versions_affected": lineage_info.get('total_versions', 0)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete lineage")
            
    except Exception as e:
        logger.error(f"Error deleting lineage: {e}")
        raise HTTPException(status_code=500, detail=f"Lineage deletion failed: {str(e)}")


async def process_document_async(
    version_id: str,
    file_content: bytes,
    filename: str,
    task_id: str
):
    """
    Background task to process uploaded document.
    
    This function runs the complete document processing pipeline:
    1. Preprocessing (MinerU/MarkItDown)
    2. Post-processing (chunking, abbreviation expansion)
    3. Meta document creation
    4. RAG preparation
    """
    try:
        # Update task status
        processing_tasks[task_id].update({
            'status': 'processing',
            'stage': 'preprocessing',
            'progress': 10.0,
            'started_at': datetime.now()
        })
        
        logger.info(f"Starting document processing for version {version_id}")
        
        # Initialize components
        processor_factory = ProcessorFactory()
        postprocessing_router = PostProcessingRouter()
        
        # Stage 1: Preprocessing
        processor = processor_factory.get_processor_for_file(filename, file_content)
        if not processor:
            raise Exception(f"No processor available for file: {filename}")
        
        processing_tasks[task_id].update({
            'stage': 'preprocessing',
            'progress': 25.0
        })
        
        # Process document
        result = processor.process_document(filename, file_content=file_content)
        if not result.success:
            raise Exception(f"Preprocessing failed: {result.error.error_message}")
        
        # Stage 2: Post-processing
        processing_tasks[task_id].update({
            'stage': 'postprocessing',
            'progress': 50.0
        })
        
        # Route for post-processing
        config, decision = postprocessing_router.route_document(result.output, version_id)
        
        # Apply post-processing (chunking, abbreviation expansion, etc.)
        # This would be implemented based on the routing decision
        
        # Stage 3: Storage
        processing_tasks[task_id].update({
            'stage': 'storage',
            'progress': 75.0
        })
        
        # Initialize storage components
        import os
        storage_config = StorageConfig(
            database_url=os.getenv('STORAGE__POST_DB_PATH', 'sqlite:///data/post_documents.db'),
            enable_compression=True
        )
        post_db = PostDocumentDatabase(config=storage_config)
        meta_db = MetaDocumentDatabase()
        chunk_storage = ChunkStorage()
        
        # Store processed document
        # We need to get the document_id and lineage_id from the version
        # For now, we'll query the version manager or assume we have them
        # Since we don't have direct access to version details here easily without querying,
        # we'll use the version_id to find the document_id and lineage_id if possible,
        # or rely on what we have.
        # Actually, we can get version info from version_manager
        version_manager = VersionManager()
        version_info = await version_manager.get_version(version_id)
        
        if not version_info:
             raise Exception(f"Version not found: {version_id}")
             
        document_id = version_info.doc_uuid
        lineage_id = version_info.lineage_uuid
        version_number = version_info.version_number
        
        # Store in PostDocumentDatabase
        post_doc_id = post_db.store_document(
            file_uuid=document_id,
            source_file_path=version_info.file_path,
            source_content=result.output.plain_text,
            metadata=DocumentMetadata(
                file_type=version_info.file_type,
                file_size=version_info.file_size,
                creation_date=version_info.timestamp,
                custom_metadata=version_info.metadata
            )
        )
        logger.info(f"Stored processed document: {post_doc_id}")
        
        # Generate set_uuid
        set_uuid = task_id 
        
        # Convert content elements to components
        components = []
        for i, element in enumerate(result.output.content_elements):
            components.append(MetaDocumentComponent(
                component_id=element.element_id,
                component_type=element.content_type,
                content=element.content,
                metadata=element.metadata,
                order_index=i,
                confidence_score=element.confidence
            ))
            
        # Create Meta Document
        meta_doc_id = meta_db.create_meta_document(
            doc_uuid=document_id,
            set_uuid=set_uuid,
            title=filename,
            summary=result.output.document_metadata.get('summary', ''),
            components=components
        )
        logger.info(f"Created meta document: {meta_doc_id}")

        # Chunking (Stage 3.5)
        processing_tasks[task_id].update({
            'stage': 'chunking',
            'progress': 80.0
        })
        
        # Get chunking configuration
        import os
        # Get chunking configuration
        import os
        # settings = ConfigManager.get_processing_config()
        
        # Determine strategy
        strategy_name = os.getenv('PROCESSING__DEFAULT_CHUNKING_STRATEGY', 'recursive').upper()
        try:
            strategy = ChunkingStrategy[strategy_name]
        except KeyError:
            strategy = ChunkingStrategy.RECURSIVE
            
        # Configure chunker
        chunker_config = {
            'chunk_size': int(os.getenv('PROCESSING__DEFAULT_CHUNK_SIZE', 800)),
            'chunk_overlap': int(os.getenv('PROCESSING__CHUNK_OVERLAP', 100)),
            'min_chunk_size': int(os.getenv('PROCESSING__MIN_CHUNK_SIZE', 5))
        }
        
        # Context enrichment config
        if os.getenv('PROCESSING__ENABLE_CONTEXT_ENRICHMENT', 'false').lower() == 'true':
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                chunker_config.update({
                    'enrich_contexts': True,
                    'openai_api_key': api_key,
                    'context_model': os.getenv('PROCESSING__CONTEXT_ENRICHMENT_MODEL', 'gpt-3.5-turbo'),
                    'context_prompt_style': os.getenv('PROCESSING__CONTEXT_ENRICHMENT_PROMPT_STYLE', 'default'),
                    'context_max_words': int(os.getenv('PROCESSING__CONTEXT_ENRICHMENT_MAX_WORDS', 100)),
                    'context_temperature': float(os.getenv('PROCESSING__CONTEXT_ENRICHMENT_TEMPERATURE', 0.3))
                })
        
        # Perform chunking
        # Perform chunking
        logger.info(f"Chunking document {document_id} with strategy {strategy_name}")
        
        chunker = DocumentChunker(strategy=strategy, config=chunker_config)
        chunks = chunker.chunk_document(result.output)
        
        logger.info(f"Generated {len(chunks)} chunks")
        
        # Enrich chunks if enabled
        if chunker_config.get('enrich_contexts'):
            chunks = chunker.enrich_chunks_with_context(
                chunks=chunks,
                full_document_text=result.output.plain_text,
                document_metadata={
                    'doc_uuid': document_id,
                    'lineage_uuid': lineage_id,
                    'version': version_number,
                    'filename': filename
                }
            )
            
        # Convert chunks to dicts for storage
        chunk_dicts = []
        for chunk in chunks:
            # Default: content is chunk.content
            content = chunk.content
            enriched_content = None
            
            # Check if enrichment happened (swapped content)
            # We check for original_content in metadata because chunker swaps them
            if hasattr(chunk.metadata, 'original_content') and chunk.metadata.original_content:
                content = chunk.metadata.original_content
                enriched_content = chunk.content
            
            chunk_dict = {
                'content': content,
                'metadata': {
                    'word_count': chunk.metadata.word_count,
                    'character_count': chunk.metadata.character_count,
                    'chunk_type': chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type),
                },
                'relationships': chunk.relationships
            }
            
            if enriched_content:
                chunk_dict['enriched_content'] = enriched_content
                chunk_dict['enrichment_metadata'] = {'enriched': True}
                
            chunk_dicts.append(chunk_dict)
            
        # Store chunks
        stored_chunk_ids = chunk_storage.store_chunks(
            doc_uuid=document_id,
            lineage_uuid=lineage_id,
            version_number=version_number,
            chunks=chunk_dicts,
            chunking_strategy=strategy_name.lower()
        )
        logger.info(f"Stored {len(stored_chunk_ids)} chunks for document {document_id}")

        # Stage 4: RAG Preparation
        processing_tasks[task_id].update({
            'stage': 'rag_preparation',
            'progress': 90.0
        })
        
        # Prepare for RAG (LightRAG integration)
        # This would create meta documents and prepare for search
        
        # Complete
        processing_tasks[task_id].update({
            'status': 'completed',
            'stage': 'completed',
            'progress': 100.0,
            'completed_at': datetime.now()
        })
        
        logger.info(f"Document processing completed for version {version_id}")
        
    except Exception as e:
        logger.error(f"Document processing failed for version {version_id}: {e}")
        processing_tasks[task_id].update({
            'status': 'failed',
            'stage': 'error',
            'progress': 0.0,
            'completed_at': datetime.now(),
            'error_message': str(e)
        })


# Processing Status and Document Retrieval Endpoints

class ProcessingStageInfo(BaseModel):
    """Information about a processing stage."""
    stage_name: str
    status: str  # pending, processing, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    progress_percentage: float = 0.0
    stage_details: Dict[str, Any] = {}
    error_message: Optional[str] = None


class DetailedProcessingStatus(BaseModel):
    """Detailed processing status with stage breakdown."""
    document_id: str
    version_id: str
    overall_status: str
    overall_progress: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    stages: List[ProcessingStageInfo] = []
    current_stage: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    processing_metadata: Dict[str, Any] = {}


class ProcessedDocumentInfo(BaseModel):
    """Information about processed document at different stages."""
    document_id: str
    version_id: str
    processing_stage: str  # raw, preprocessed, postprocessed, meta, rag_ready
    available_formats: List[str] = []  # original, text, markdown, json, chunks
    file_size: int
    processing_timestamp: datetime
    processor_info: Dict[str, Any] = {}
    quality_metrics: Dict[str, Any] = {}


@router.get("/{document_id}/processing/detailed", response_model=DetailedProcessingStatus)
async def get_detailed_processing_status(
    document_id: str,
    version_id: Optional[str] = Query(None, description="Specific version ID"),
    include_history: bool = Query(False, description="Include processing history")
):
    """
    Get detailed processing status with stage breakdown.
    
    - **document_id**: Document UUID
    - **version_id**: Optional specific version ID
    - **include_history**: Include processing history for all stages
    """
    try:
        # Find relevant processing tasks
        relevant_tasks = []
        for task_id, task in processing_tasks.items():
            if task['document_id'] == document_id:
                if version_id is None or task.get('version_id') == version_id:
                    relevant_tasks.append((task_id, task))
        
        if not relevant_tasks:
            raise HTTPException(status_code=404, detail="No processing tasks found for document")
        
        # Get the most recent task
        latest_task_id, latest_task = max(relevant_tasks, 
                                        key=lambda x: x[1].get('started_at') or datetime.min)
        
        # Create detailed stage information
        stages = []
        
        # Define processing stages
        stage_definitions = [
            ("queued", "Document queued for processing"),
            ("preprocessing", "Document preprocessing (MinerU/MarkItDown)"),
            ("postprocessing", "Post-processing (chunking, abbreviation expansion)"),
            ("storage", "Storing processed document"),
            ("rag_preparation", "RAG preparation and indexing"),
            ("completed", "Processing completed")
        ]
        
        current_stage = latest_task.get('stage', 'unknown')
        overall_progress = latest_task.get('progress', 0.0)
        
        for stage_name, stage_description in stage_definitions:
            if stage_name == current_stage:
                stage_status = latest_task.get('status', 'processing')
                stage_progress = overall_progress
            elif stages and stages[-1].status == 'completed':
                stage_status = 'pending'
                stage_progress = 0.0
            else:
                stage_status = 'completed' if stage_name in ['queued'] else 'pending'
                stage_progress = 100.0 if stage_status == 'completed' else 0.0
            
            stage_info = ProcessingStageInfo(
                stage_name=stage_name,
                status=stage_status,
                progress_percentage=stage_progress,
                stage_details={'description': stage_description}
            )
            
            stages.append(stage_info)
        
        # Calculate estimated completion
        estimated_completion = None
        if latest_task.get('started_at') and overall_progress > 0:
            elapsed = (datetime.now() - latest_task['started_at']).total_seconds()
            if overall_progress < 100:
                estimated_total = elapsed * (100 / overall_progress)
                estimated_completion = latest_task['started_at'] + timedelta(seconds=estimated_total)
        
        return DetailedProcessingStatus(
            document_id=document_id,
            version_id=latest_task.get('version_id', ''),
            overall_status=latest_task.get('status', 'unknown'),
            overall_progress=overall_progress,
            started_at=latest_task.get('started_at'),
            completed_at=latest_task.get('completed_at'),
            total_duration_seconds=(
                (latest_task['completed_at'] - latest_task['started_at']).total_seconds()
                if latest_task.get('completed_at') and latest_task.get('started_at')
                else None
            ),
            stages=stages,
            current_stage=current_stage,
            estimated_completion=estimated_completion,
            processing_metadata={
                'task_id': latest_task_id,
                'processor_type': 'auto-detected',
                'processing_mode': 'async'
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting detailed processing status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


@router.get("/{document_id}/processed", response_model=List[ProcessedDocumentInfo])
async def get_processed_document_info(
    document_id: str,
    version_id: Optional[str] = Query(None, description="Specific version ID"),
    stage: Optional[str] = Query(None, description="Processing stage filter"),
    format: Optional[str] = Query(None, description="Available format filter")
):
    """
    Get information about processed documents at different stages.
    
    - **document_id**: Document UUID
    - **version_id**: Optional specific version ID
    - **stage**: Filter by processing stage
    - **format**: Filter by available format
    """
    try:
        # This would query the actual storage systems
        # For now, return mock data based on processing status
        
        processed_docs = []
        
        # Check if document has been processed
        relevant_tasks = [
            task for task in processing_tasks.values()
            if task['document_id'] == document_id and 
            (version_id is None or task.get('version_id') == version_id)
        ]
        
        if not relevant_tasks:
            return []
        
        # Mock processed document info based on completion status
        for task in relevant_tasks:
            if task.get('status') == 'completed':
                # Raw document
                processed_docs.append(ProcessedDocumentInfo(
                    document_id=document_id,
                    version_id=task.get('version_id', ''),
                    processing_stage='raw',
                    available_formats=['original'],
                    file_size=1024,  # Mock size
                    processing_timestamp=task.get('started_at', datetime.now()),
                    processor_info={'stage': 'raw', 'format': 'original'}
                ))
                
                # Preprocessed document
                processed_docs.append(ProcessedDocumentInfo(
                    document_id=document_id,
                    version_id=task.get('version_id', ''),
                    processing_stage='preprocessed',
                    available_formats=['text', 'markdown', 'json'],
                    file_size=2048,  # Mock size
                    processing_timestamp=task.get('started_at', datetime.now()),
                    processor_info={'stage': 'preprocessed', 'processor': 'auto-detected'},
                    quality_metrics={'confidence': 0.95, 'completeness': 0.98}
                ))
                
                # Post-processed document
                processed_docs.append(ProcessedDocumentInfo(
                    document_id=document_id,
                    version_id=task.get('version_id', ''),
                    processing_stage='postprocessed',
                    available_formats=['chunks', 'expanded', 'structured'],
                    file_size=3072,  # Mock size
                    processing_timestamp=task.get('completed_at', datetime.now()),
                    processor_info={'stage': 'postprocessed', 'methods': ['chunking', 'abbreviation_expansion']},
                    quality_metrics={'chunk_count': 15, 'abbreviations_expanded': 5}
                ))
        
        # Apply filters
        if stage:
            processed_docs = [doc for doc in processed_docs if doc.processing_stage == stage]
        
        if format:
            processed_docs = [doc for doc in processed_docs if format in doc.available_formats]
        
        return processed_docs
        
    except Exception as e:
        logger.error(f"Error getting processed document info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processed document info: {str(e)}")


@router.get("/{document_id}/download/processed")
async def download_processed_document(
    document_id: str,
    stage: str = Query(..., description="Processing stage: raw, preprocessed, postprocessed, meta"),
    format: str = Query("json", description="Output format: json, text, markdown, chunks"),
    version_id: Optional[str] = Query(None, description="Specific version ID"),
    version_manager: VersionManager = Depends(get_version_manager)
):
    """
    Download processed document at specific stage and format.
    
    - **document_id**: Document UUID
    - **stage**: Processing stage to download
    - **format**: Output format
    - **version_id**: Optional specific version ID
    """
    try:
        # Validate document exists
        if version_id:
            version = await version_manager.get_version(version_id)
            if not version or version.document_id != document_id:
                raise HTTPException(status_code=404, detail="Version not found")
        else:
            versions = version_manager.get_versions(document_id)
            if not versions:
                raise HTTPException(status_code=404, detail="Document not found")
            version = versions[0]
        
        # Check if processing is complete
        relevant_tasks = [
            task for task in processing_tasks.values()
            if task['document_id'] == document_id and task.get('status') == 'completed'
        ]
        
        if not relevant_tasks:
            raise HTTPException(status_code=404, detail="No completed processing found for document")
        
        # Generate content based on stage and format
        filename = version.get('metadata', {}).get('filename', 'document')
        base_name = Path(filename).stem
        
        if stage == "raw" and format == "original":
            # Return original content
            content = version.get('content', '').encode('utf-8')
            media_type = version.get('metadata', {}).get('content_type', 'application/octet-stream')
            download_filename = filename
            
        elif stage == "preprocessed":
            if format == "json":
                # Mock preprocessed JSON
                content_data = {
                    "document_id": document_id,
                    "version_id": version_id or "latest",
                    "processing_stage": "preprocessed",
                    "content": {
                        "text": version.get('content', ''),
                        "metadata": version.get('metadata', {}),
                        "structure": {
                            "paragraphs": 5,
                            "headings": 2,
                            "tables": 0,
                            "images": 0
                        }
                    },
                    "processing_info": {
                        "processor": "auto-detected",
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.95
                    }
                }
                content = json.dumps(content_data, indent=2).encode('utf-8')
                media_type = "application/json"
                download_filename = f"{base_name}_preprocessed.json"
                
            elif format == "markdown":
                # Mock markdown conversion
                markdown_content = f"# {base_name}\n\n{version.get('content', '')}\n\n---\n*Processed by DocForge Brain MVP*"
                content = markdown_content.encode('utf-8')
                media_type = "text/markdown"
                download_filename = f"{base_name}_preprocessed.md"
                
            else:
                raise HTTPException(status_code=400, detail=f"Format '{format}' not supported for stage '{stage}'")
        
        elif stage == "postprocessed":
            if format == "chunks":
                # Mock chunked content
                version_content = version.get('content', '')
                chunks = [
                    {"id": 1, "content": version_content[:100], "type": "paragraph"},
                    {"id": 2, "content": version_content[100:200], "type": "paragraph"},
                    {"id": 3, "content": version_content[200:], "type": "paragraph"}
                ]
                content_data = {
                    "document_id": document_id,
                    "chunks": chunks,
                    "chunk_count": len(chunks),
                    "processing_methods": ["sentence_chunking", "abbreviation_expansion"]
                }
                content = json.dumps(content_data, indent=2).encode('utf-8')
                media_type = "application/json"
                download_filename = f"{base_name}_chunks.json"
                
            else:
                raise HTTPException(status_code=400, detail=f"Format '{format}' not supported for stage '{stage}'")
        
        else:
            raise HTTPException(status_code=400, detail=f"Stage '{stage}' not supported")
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={download_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading processed document: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/{document_id}/search", response_model=List[DocumentSearchResult])
async def search_document_content(
    document_id: str,
    search_request: DocumentSearchRequest,
    version_filter: Optional[List[str]] = Query(None, description="Filter by specific version IDs")
):
    """
    Search within document content using RAG.
    
    - **document_id**: Document UUID
    - **search_request**: Search parameters
    - **version_filter**: Optional version ID filter
    """
    try:
        # This would integrate with the actual RAG system
        # For now, return mock search results
        
        # Validate document exists
        relevant_tasks = [
            task for task in processing_tasks.values()
            if task['document_id'] == document_id and task.get('status') == 'completed'
        ]
        
        if not relevant_tasks:
            raise HTTPException(status_code=404, detail="No processed content available for search")
        
        # Mock search results
        results = []
        
        for i in range(min(search_request.limit, 3)):  # Mock up to 3 results
            result = DocumentSearchResult(
                document_id=document_id,
                lineage_id=document_id,
                version_number=i + 1,
                filename=f"document_v{i+1}.txt",
                relevance_score=0.9 - (i * 0.1),
                snippet=f"This is a search result snippet {i+1} containing '{search_request.query}'...",
                metadata={
                    "search_query": search_request.query,
                    "match_type": "content",
                    "section": f"Section {i+1}"
                }
            )
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching document content: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/processing/queue")
async def get_processing_queue():
    """
    Get current processing queue status.
    """
    try:
        queue_info = {
            "total_tasks": len(processing_tasks),
            "pending_tasks": len([t for t in processing_tasks.values() if t.get('status') == 'pending']),
            "processing_tasks": len([t for t in processing_tasks.values() if t.get('status') == 'processing']),
            "completed_tasks": len([t for t in processing_tasks.values() if t.get('status') == 'completed']),
            "failed_tasks": len([t for t in processing_tasks.values() if t.get('status') == 'failed']),
            "queue_details": []
        }
        
        # Add details for active tasks
        for task_id, task in processing_tasks.items():
            if task.get('status') in ['pending', 'processing']:
                queue_info["queue_details"].append({
                    "task_id": task_id,
                    "document_id": task.get('document_id'),
                    "status": task.get('status'),
                    "stage": task.get('stage'),
                    "progress": task.get('progress', 0.0),
                    "started_at": task.get('started_at'),
                    "estimated_completion": None  # Would calculate based on progress
                })
        
        return queue_info
        
    except Exception as e:
        logger.error(f"Error getting processing queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")