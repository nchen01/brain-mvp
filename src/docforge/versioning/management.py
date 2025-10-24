"""Comprehensive version management operations."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dbm.operations import get_db_operations
from core.exceptions import DocumentVersionError, DocumentNotFoundError
from .models import (
    DocumentVersionModel,
    DocumentLineageModel,
    VersionBranchRequest,
    SoftDeleteRequest,
    RestoreVersionRequest,
    LineageDeletionRequest,
    DeletionReason,
    VersionStatus,
    DocumentRegistrationRequest
)
from .versions import VersionManager
from .lineage import LineageManager
from .deletion import DeletionManager
from .storage import RawDocumentStorage

logger = logging.getLogger(__name__)


class VersionManagementService:
    """Comprehensive version management service."""
    
    def __init__(self, storage_base_path: str = "./data/raw_documents"):
        self.db = get_db_operations()
        self.version_manager = VersionManager()
        self.lineage_manager = LineageManager()
        self.deletion_manager = DeletionManager()
        self.storage = RawDocumentStorage(storage_base_path)
    
    async def create_version_branch(
        self,
        lineage_uuid: str,
        source_version: int,
        new_filename: str,
        file_content: bytes,
        user_id: str,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new version by branching from an existing version."""
        try:
            # Verify source version exists
            source_version_model = await self.version_manager.get_version_by_number(
                lineage_uuid, source_version
            )
            
            if not source_version_model:
                raise DocumentNotFoundError(
                    f"Source version {source_version} not found in lineage {lineage_uuid}"
                )
            
            # Create branch request
            branch_request = VersionBranchRequest(
                lineage_uuid=lineage_uuid,
                source_version=source_version,
                filename=new_filename,
                file_size=len(file_content),
                user_id=user_id,
                labels=labels or [],
                metadata=metadata or {}
            )
            
            # Create the branch
            response = await self.version_manager.create_version_branch(
                branch_request,
                file_content
            )
            
            # Get the created version details
            new_version = await self.version_manager.get_version(response.doc_uuid)
            
            return {
                "doc_uuid": response.doc_uuid,
                "lineage_uuid": response.lineage_uuid,
                "version_number": response.version_number,
                "source_version": source_version,
                "filename": new_filename,
                "file_path": response.file_path,
                "file_hash": response.file_hash,
                "created_at": response.timestamp.isoformat(),
                "created_by": user_id,
                "is_branch": True,
                "branch_info": {
                    "source_doc_uuid": source_version_model.doc_uuid,
                    "source_filename": source_version_model.filename,
                    "source_created_by": source_version_model.user_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating version branch: {e}")
            raise DocumentVersionError(f"Failed to create version branch: {str(e)}")
    
    async def edit_old_version(
        self,
        doc_uuid: str,
        new_filename: str,
        file_content: bytes,
        user_id: str,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Edit an old version by creating a branch from it."""
        try:
            # Get the version to edit
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                raise DocumentNotFoundError(doc_uuid)
            
            # Create branch from this version
            return await self.create_version_branch(
                version.lineage_uuid,
                version.version_number,
                new_filename,
                file_content,
                user_id,
                labels,
                metadata
            )
            
        except Exception as e:
            logger.error(f"Error editing old version {doc_uuid}: {e}")
            raise DocumentVersionError(f"Failed to edit old version: {str(e)}")
    
    async def soft_delete_version_with_tracking(
        self,
        doc_uuid: str,
        reason: DeletionReason,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Soft delete a version with comprehensive tracking."""
        try:
            # Get version info before deletion
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                raise DocumentNotFoundError(doc_uuid)
            
            # Create deletion request
            delete_request = SoftDeleteRequest(
                doc_uuid=doc_uuid,
                reason=reason,
                user_id=user_id,
                notes=notes
            )
            
            # Perform deletion
            delete_response = await self.deletion_manager.soft_delete_version(delete_request)
            
            return {
                "doc_uuid": doc_uuid,
                "lineage_uuid": version.lineage_uuid,
                "version_number": version.version_number,
                "filename": version.filename,
                "deletion_reason": reason.value,
                "deleted_by": user_id,
                "deletion_notes": notes,
                "deletion_timestamp": delete_response.deletion_timestamp.isoformat(),
                "success": delete_response.success,
                "was_current": version.is_current
            }
            
        except Exception as e:
            logger.error(f"Error soft deleting version {doc_uuid}: {e}")
            raise DocumentVersionError(f"Failed to soft delete version: {str(e)}")
    
    async def restore_version_with_tracking(
        self,
        doc_uuid: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Restore a soft-deleted version with tracking."""
        try:
            # Get version info before restoration
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                raise DocumentNotFoundError(doc_uuid)
            
            if version.status != VersionStatus.DELETED:
                raise DocumentVersionError(f"Version {doc_uuid} is not deleted")
            
            # Create restoration request
            restore_request = RestoreVersionRequest(
                doc_uuid=doc_uuid,
                user_id=user_id,
                notes=notes
            )
            
            # Perform restoration
            success = await self.deletion_manager.restore_version(restore_request)
            
            return {
                "doc_uuid": doc_uuid,
                "lineage_uuid": version.lineage_uuid,
                "version_number": version.version_number,
                "filename": version.filename,
                "restored_by": user_id,
                "restoration_notes": notes,
                "restoration_timestamp": datetime.utcnow().isoformat(),
                "success": success,
                "previous_deletion_reason": version.deletion_reason.value if version.deletion_reason else None
            }
            
        except Exception as e:
            logger.error(f"Error restoring version {doc_uuid}: {e}")
            raise DocumentVersionError(f"Failed to restore version: {str(e)}")
    
    async def delete_lineage_for_privacy(
        self,
        lineage_uuid: str,
        reason: DeletionReason,
        user_id: str,
        notes: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Delete an entire lineage for privacy compliance."""
        try:
            # Get lineage info before deletion
            lineage = await self.lineage_manager.get_lineage(lineage_uuid)
            if not lineage:
                raise DocumentNotFoundError(lineage_uuid)
            
            # Get all versions in the lineage
            versions = await self.version_manager.get_versions_by_lineage(
                lineage_uuid, include_deleted=True
            )
            
            # Create deletion request
            deletion_request = LineageDeletionRequest(
                lineage_uuid=lineage_uuid,
                reason=reason,
                user_id=user_id,
                notes=notes,
                force=force
            )
            
            # Perform lineage deletion
            success = await self.deletion_manager.soft_delete_lineage(deletion_request)
            
            return {
                "lineage_uuid": lineage_uuid,
                "original_filename": lineage.original_filename,
                "created_by": lineage.created_by,
                "total_versions": len(versions),
                "deletion_reason": reason.value,
                "deleted_by": user_id,
                "deletion_notes": notes,
                "deletion_timestamp": datetime.utcnow().isoformat(),
                "success": success,
                "force_used": force,
                "affected_versions": [
                    {
                        "doc_uuid": v.doc_uuid,
                        "version_number": v.version_number,
                        "filename": v.filename,
                        "previous_status": v.status.value
                    }
                    for v in versions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error deleting lineage {lineage_uuid} for privacy: {e}")
            raise DocumentVersionError(f"Failed to delete lineage for privacy: {str(e)}")
    
    async def get_version_management_history(
        self,
        lineage_uuid: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get version management history (deletions, restorations, etc.)."""
        try:
            # Get deleted versions
            deleted_versions = await self.deletion_manager.get_deleted_versions(
                user_id=user_id,
                limit=limit
            )
            
            history = []
            for version_data in deleted_versions:
                if lineage_uuid and version_data.get('lineage_uuid') != lineage_uuid:
                    continue
                
                history.append({
                    "doc_uuid": version_data.get('doc_uuid'),
                    "lineage_uuid": version_data.get('lineage_uuid'),
                    "version_number": version_data.get('version_number'),
                    "filename": version_data.get('filename'),
                    "action": "soft_delete",
                    "reason": version_data.get('deletion_reason'),
                    "user_id": version_data.get('user_id'),
                    "timestamp": version_data.get('timestamp'),
                    "status": version_data.get('status')
                })
            
            # Sort by timestamp (most recent first)
            history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting version management history: {e}")
            return []
    
    async def get_version_relationships(self, doc_uuid: str) -> Dict[str, Any]:
        """Get the relationship tree for a version (parent, children, siblings)."""
        try:
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                raise DocumentNotFoundError(doc_uuid)
            
            # Get all versions in the lineage
            all_versions = await self.version_manager.get_versions_by_lineage(
                version.lineage_uuid, include_deleted=True
            )
            
            # Build relationship map
            relationships = {
                "current_version": {
                    "doc_uuid": version.doc_uuid,
                    "version_number": version.version_number,
                    "filename": version.filename,
                    "status": version.status.value,
                    "is_current": version.is_current
                },
                "parent": None,
                "children": [],
                "siblings": [],
                "lineage_info": {
                    "lineage_uuid": version.lineage_uuid,
                    "total_versions": len(all_versions),
                    "active_versions": len([v for v in all_versions if v.status == VersionStatus.ACTIVE])
                }
            }
            
            # Find parent (if this is a branch)
            if version.edit_source_version:
                parent = next(
                    (v for v in all_versions if v.version_number == version.edit_source_version),
                    None
                )
                if parent:
                    relationships["parent"] = {
                        "doc_uuid": parent.doc_uuid,
                        "version_number": parent.version_number,
                        "filename": parent.filename,
                        "status": parent.status.value
                    }
            
            # Find children (versions that branch from this one)
            children = [
                v for v in all_versions 
                if v.edit_source_version == version.version_number and v.doc_uuid != version.doc_uuid
            ]
            relationships["children"] = [
                {
                    "doc_uuid": child.doc_uuid,
                    "version_number": child.version_number,
                    "filename": child.filename,
                    "status": child.status.value
                }
                for child in children
            ]
            
            # Find siblings (versions that branch from the same parent)
            if version.edit_source_version:
                siblings = [
                    v for v in all_versions 
                    if (v.edit_source_version == version.edit_source_version and 
                        v.doc_uuid != version.doc_uuid)
                ]
                relationships["siblings"] = [
                    {
                        "doc_uuid": sibling.doc_uuid,
                        "version_number": sibling.version_number,
                        "filename": sibling.filename,
                        "status": sibling.status.value
                    }
                    for sibling in siblings
                ]
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error getting version relationships for {doc_uuid}: {e}")
            return {}
    
    async def bulk_version_operation(
        self,
        operation: str,
        doc_uuids: List[str],
        user_id: str,
        reason: Optional[DeletionReason] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform bulk operations on multiple versions."""
        try:
            results = {
                "operation": operation,
                "total_requested": len(doc_uuids),
                "successful": 0,
                "failed": 0,
                "results": [],
                "errors": []
            }
            
            for doc_uuid in doc_uuids:
                try:
                    if operation == "soft_delete":
                        if not reason:
                            raise ValueError("Deletion reason required for soft_delete operation")
                        
                        result = await self.soft_delete_version_with_tracking(
                            doc_uuid, reason, user_id, notes
                        )
                        results["results"].append(result)
                        results["successful"] += 1
                        
                    elif operation == "restore":
                        result = await self.restore_version_with_tracking(
                            doc_uuid, user_id, notes
                        )
                        results["results"].append(result)
                        results["successful"] += 1
                        
                    else:
                        raise ValueError(f"Unsupported operation: {operation}")
                        
                except Exception as e:
                    error_info = {
                        "doc_uuid": doc_uuid,
                        "error": str(e)
                    }
                    results["errors"].append(error_info)
                    results["failed"] += 1
                    logger.error(f"Bulk operation {operation} failed for {doc_uuid}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk version operation: {e}")
            raise DocumentVersionError(f"Bulk operation failed: {str(e)}")
    
    async def get_privacy_compliance_report(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a privacy compliance report."""
        try:
            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "summary": {
                    "total_lineages": 0,
                    "active_lineages": 0,
                    "deleted_lineages": 0,
                    "total_versions": 0,
                    "active_versions": 0,
                    "deleted_versions": 0
                },
                "deletion_reasons": {},
                "recent_deletions": [],
                "storage_impact": {}
            }
            
            # Get lineage summary
            lineage_summary = await self.lineage_manager.get_lineage_summary(user_id)
            report["summary"].update(lineage_summary)
            
            # Get deletion history
            deletion_history = await self.get_version_management_history(
                user_id=user_id, limit=50
            )
            report["recent_deletions"] = deletion_history[:10]  # Last 10 deletions
            
            # Count deletion reasons
            for deletion in deletion_history:
                reason = deletion.get("reason", "unknown")
                report["deletion_reasons"][reason] = report["deletion_reasons"].get(reason, 0) + 1
            
            # Get storage statistics
            storage_stats = await self.storage.get_storage_statistics()
            report["storage_impact"] = {
                "total_files": storage_stats.get("total_files", 0),
                "deleted_files": storage_stats.get("deleted_files", 0),
                "deleted_size_bytes": storage_stats.get("deleted_size", 0),
                "potential_cleanup_space": storage_stats.get("deleted_size", 0)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating privacy compliance report: {e}")
            return {"error": str(e)}