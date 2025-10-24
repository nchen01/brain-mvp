"""Privacy-focused deletion management for document versions."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dbm.operations import get_db_operations
from core.exceptions import DocumentVersionError, DocumentNotFoundError
from .models import (
    SoftDeleteRequest,
    SoftDeleteResponse,
    LineageDeletionRequest,
    RestoreVersionRequest,
    DeletionReason,
    VersionStatus
)
from .versions import VersionManager
from .lineage import LineageManager

logger = logging.getLogger(__name__)


class DeletionManager:
    """Manages privacy-focused document deletion operations."""
    
    def __init__(self):
        self.db = get_db_operations()
        self.version_manager = VersionManager()
        self.lineage_manager = LineageManager()
    
    async def soft_delete_version(self, request: SoftDeleteRequest) -> SoftDeleteResponse:
        """Soft delete a document version with detailed tracking."""
        try:
            # Get version info before deletion
            version = await self.version_manager.get_version(request.doc_uuid)
            if not version:
                raise DocumentNotFoundError(request.doc_uuid)
            
            # Perform soft deletion
            success = await self.version_manager.soft_delete_version(
                request.doc_uuid,
                request.reason,
                request.user_id,
                request.notes
            )
            
            if success:
                # Log deletion event
                await self._log_deletion_event(
                    doc_uuid=request.doc_uuid,
                    lineage_uuid=version.lineage_uuid,
                    version_number=version.version_number,
                    reason=request.reason,
                    user_id=request.user_id,
                    notes=request.notes,
                    deletion_type="version"
                )
            
            return SoftDeleteResponse(
                doc_uuid=request.doc_uuid,
                lineage_uuid=version.lineage_uuid,
                version_number=version.version_number,
                deletion_timestamp=datetime.utcnow(),
                reason=request.reason,
                success=success
            )
            
        except Exception as e:
            logger.error(f"Error in soft delete version {request.doc_uuid}: {e}")
            return SoftDeleteResponse(
                doc_uuid=request.doc_uuid,
                lineage_uuid="",
                version_number=0,
                deletion_timestamp=datetime.utcnow(),
                reason=request.reason,
                success=False
            )
    
    async def soft_delete_lineage(self, request: LineageDeletionRequest) -> bool:
        """Soft delete an entire document lineage."""
        try:
            # Get lineage info before deletion
            lineage = await self.lineage_manager.get_lineage(request.lineage_uuid)
            if not lineage:
                raise DocumentNotFoundError(request.lineage_uuid)
            
            # Perform lineage deletion
            success = await self.lineage_manager.soft_delete_lineage(
                request.lineage_uuid,
                request.reason,
                request.user_id,
                request.force
            )
            
            if success:
                # Log deletion event
                await self._log_deletion_event(
                    lineage_uuid=request.lineage_uuid,
                    reason=request.reason,
                    user_id=request.user_id,
                    notes=request.notes,
                    deletion_type="lineage"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error in soft delete lineage {request.lineage_uuid}: {e}")
            return False
    
    async def restore_version(self, request: RestoreVersionRequest) -> bool:
        """Restore a soft-deleted version."""
        try:
            # Get version info before restoration
            version = await self.version_manager.get_version(request.doc_uuid)
            if not version:
                raise DocumentNotFoundError(request.doc_uuid)
            
            if version.status != VersionStatus.DELETED:
                raise DocumentVersionError(f"Version {request.doc_uuid} is not deleted")
            
            # Perform restoration
            success = await self.version_manager.restore_version(
                request.doc_uuid,
                request.user_id
            )
            
            if success:
                # Log restoration event
                await self._log_restoration_event(
                    doc_uuid=request.doc_uuid,
                    lineage_uuid=version.lineage_uuid,
                    version_number=version.version_number,
                    user_id=request.user_id,
                    notes=request.notes
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring version {request.doc_uuid}: {e}")
            return False
    
    async def restore_lineage(self, lineage_uuid: str, user_id: str) -> bool:
        """Restore a soft-deleted lineage."""
        try:
            success = await self.lineage_manager.restore_lineage(lineage_uuid, user_id)
            
            if success:
                # Log restoration event
                await self._log_restoration_event(
                    lineage_uuid=lineage_uuid,
                    user_id=user_id,
                    restoration_type="lineage"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring lineage {lineage_uuid}: {e}")
            return False
    
    async def get_deleted_versions(
        self,
        user_id: Optional[str] = None,
        reason: Optional[DeletionReason] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get list of deleted versions with optional filtering."""
        try:
            where_clause = "status = ?"
            params = [VersionStatus.DELETED.value]
            
            if user_id:
                where_clause += " AND user_id = ?"
                params.append(user_id)
            
            if reason:
                where_clause += " AND deletion_reason = ?"
                params.append(reason.value)
            
            where_clause += " ORDER BY timestamp DESC"
            
            if limit:
                where_clause += f" LIMIT {limit}"
            
            results = self.db.select(
                "raw_document_register",
                where_clause,
                tuple(params)
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting deleted versions: {e}")
            return []
    
    async def get_deletion_history(
        self,
        lineage_uuid: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get deletion history with optional filtering."""
        try:
            where_clause = "1=1"  # Base condition
            params = []
            
            if lineage_uuid:
                where_clause += " AND lineage_uuid = ?"
                params.append(lineage_uuid)
            
            if user_id:
                where_clause += " AND user_id = ?"
                params.append(user_id)
            
            where_clause += " ORDER BY timestamp DESC"
            
            if limit:
                where_clause += f" LIMIT {limit}"
            
            # Note: This would require a deletion_log table in a real implementation
            # For now, we'll return deleted versions as a proxy
            return await self.get_deleted_versions(user_id, None, limit)
            
        except Exception as e:
            logger.error(f"Error getting deletion history: {e}")
            return []
    
    async def permanent_delete_version(
        self,
        doc_uuid: str,
        user_id: str,
        confirmation_token: str
    ) -> bool:
        """Permanently delete a version (GDPR compliance)."""
        try:
            # Verify version exists and is soft-deleted
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                raise DocumentNotFoundError(doc_uuid)
            
            if version.status != VersionStatus.DELETED:
                raise DocumentVersionError(
                    f"Version {doc_uuid} must be soft-deleted before permanent deletion"
                )
            
            # TODO: Verify confirmation token in production
            
            # Delete physical file
            file_path = Path(version.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted physical file: {file_path}")
            
            # Remove from database
            success = self.db.delete(
                "raw_document_register",
                "doc_uuid = ?",
                (doc_uuid,)
            )
            
            if success:
                # Log permanent deletion
                await self._log_permanent_deletion_event(
                    doc_uuid=doc_uuid,
                    lineage_uuid=version.lineage_uuid,
                    version_number=version.version_number,
                    user_id=user_id
                )
                
                logger.warning(f"PERMANENTLY DELETED version {doc_uuid} by user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error permanently deleting version {doc_uuid}: {e}")
            return False
    
    async def get_privacy_report(
        self,
        user_id: str,
        include_deleted: bool = True
    ) -> Dict[str, Any]:
        """Generate a privacy report for a user's documents."""
        try:
            # Get all versions created by user
            where_clause = "user_id = ?"
            params = [user_id]
            
            if not include_deleted:
                where_clause += " AND status != ?"
                params.append(VersionStatus.DELETED.value)
            
            versions = self.db.select(
                "raw_document_register",
                where_clause,
                tuple(params)
            )
            
            # Count by status
            active_count = sum(1 for v in versions if v.get('status') == VersionStatus.ACTIVE.value)
            deleted_count = sum(1 for v in versions if v.get('status') == VersionStatus.DELETED.value)
            
            # Get unique lineages
            lineages = set(v['lineage_uuid'] for v in versions)
            
            # Calculate total file size
            total_size = sum(v.get('file_size', 0) for v in versions)
            
            return {
                "user_id": user_id,
                "total_versions": len(versions),
                "active_versions": active_count,
                "deleted_versions": deleted_count,
                "unique_lineages": len(lineages),
                "total_file_size_bytes": total_size,
                "report_generated_at": datetime.utcnow().isoformat(),
                "versions": versions if include_deleted else [v for v in versions if v.get('status') != VersionStatus.DELETED.value]
            }
            
        except Exception as e:
            logger.error(f"Error generating privacy report for user {user_id}: {e}")
            return {}
    
    async def _log_deletion_event(
        self,
        reason: DeletionReason,
        user_id: str,
        deletion_type: str,
        doc_uuid: Optional[str] = None,
        lineage_uuid: Optional[str] = None,
        version_number: Optional[int] = None,
        notes: Optional[str] = None
    ) -> None:
        """Log a deletion event for audit purposes."""
        try:
            # In a production system, this would write to a dedicated audit log table
            log_entry = {
                "event_type": "deletion",
                "deletion_type": deletion_type,
                "doc_uuid": doc_uuid,
                "lineage_uuid": lineage_uuid,
                "version_number": version_number,
                "reason": reason.value,
                "user_id": user_id,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"DELETION EVENT: {log_entry}")
            
        except Exception as e:
            logger.error(f"Error logging deletion event: {e}")
    
    async def _log_restoration_event(
        self,
        user_id: str,
        restoration_type: str = "version",
        doc_uuid: Optional[str] = None,
        lineage_uuid: Optional[str] = None,
        version_number: Optional[int] = None,
        notes: Optional[str] = None
    ) -> None:
        """Log a restoration event for audit purposes."""
        try:
            log_entry = {
                "event_type": "restoration",
                "restoration_type": restoration_type,
                "doc_uuid": doc_uuid,
                "lineage_uuid": lineage_uuid,
                "version_number": version_number,
                "user_id": user_id,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"RESTORATION EVENT: {log_entry}")
            
        except Exception as e:
            logger.error(f"Error logging restoration event: {e}")
    
    async def _log_permanent_deletion_event(
        self,
        doc_uuid: str,
        lineage_uuid: str,
        version_number: int,
        user_id: str
    ) -> None:
        """Log a permanent deletion event for audit purposes."""
        try:
            log_entry = {
                "event_type": "permanent_deletion",
                "doc_uuid": doc_uuid,
                "lineage_uuid": lineage_uuid,
                "version_number": version_number,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "warning": "PERMANENT DELETION - DATA CANNOT BE RECOVERED"
            }
            
            logger.critical(f"PERMANENT DELETION EVENT: {log_entry}")
            
        except Exception as e:
            logger.error(f"Error logging permanent deletion event: {e}")