"""Document lineage management for tracking document families and version chains."""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dbm.operations import get_db_operations
from core.exceptions import DocumentVersionError, DocumentNotFoundError
from .models import (
    DocumentLineageModel,
    DocumentVersionModel,
    VersionHistoryResponse,
    generate_lineage_uuid,
    DeletionReason,
    VersionStatus
)

logger = logging.getLogger(__name__)


class LineageManager:
    """Manages document lineage operations."""
    
    def __init__(self):
        self.db = get_db_operations()
    
    async def create_lineage(
        self,
        original_filename: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new document lineage."""
        try:
            lineage_uuid = generate_lineage_uuid()
            
            lineage_data = {
                "lineage_uuid": lineage_uuid,
                "original_filename": original_filename,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat(),
                "current_version": 1,
                "total_versions": 1,
                "is_active": True
            }
            
            success = self.db.insert("document_lineage", lineage_data)
            
            if not success:
                raise DocumentVersionError(
                    "Failed to create document lineage",
                    lineage_uuid=lineage_uuid
                )
            
            logger.info(f"Created new lineage: {lineage_uuid} for file: {original_filename}")
            return lineage_uuid
            
        except Exception as e:
            logger.error(f"Error creating lineage: {e}")
            raise DocumentVersionError(f"Failed to create lineage: {str(e)}")
    
    async def get_lineage(self, lineage_uuid: str) -> Optional[DocumentLineageModel]:
        """Get lineage information by UUID."""
        try:
            results = self.db.select(
                "document_lineage",
                "lineage_uuid = ?",
                (lineage_uuid,)
            )
            
            if not results:
                return None
            
            lineage_data = results[0]
            return DocumentLineageModel(**lineage_data)
            
        except Exception as e:
            logger.error(f"Error getting lineage {lineage_uuid}: {e}")
            raise DocumentVersionError(f"Failed to get lineage: {str(e)}")
    
    async def update_lineage_version_info(
        self,
        lineage_uuid: str,
        current_version: Optional[int] = None,
        increment_total: bool = False
    ) -> bool:
        """Update lineage version information."""
        try:
            update_data = {}
            
            if current_version is not None:
                update_data["current_version"] = current_version
            
            if increment_total:
                # Get current total and increment
                lineage = await self.get_lineage(lineage_uuid)
                if lineage:
                    update_data["total_versions"] = lineage.total_versions + 1
            
            if not update_data:
                return True  # Nothing to update
            
            success = self.db.update(
                "document_lineage",
                update_data,
                "lineage_uuid = ?",
                (lineage_uuid,)
            )
            
            if success:
                logger.info(f"Updated lineage {lineage_uuid} version info: {update_data}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating lineage {lineage_uuid}: {e}")
            return False
    
    async def get_version_history(
        self,
        lineage_uuid: str,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Optional[VersionHistoryResponse]:
        """Get complete version history for a lineage."""
        try:
            # First get lineage info
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                return None
            
            # Build query for versions
            where_clause = "lineage_uuid = ?"
            params = [lineage_uuid]
            
            if not include_deleted:
                where_clause += " AND status != ?"
                params.append(VersionStatus.DELETED.value)
            
            # Add ordering
            where_clause += " ORDER BY version_number ASC"
            
            # Add pagination
            if limit:
                where_clause += f" LIMIT {limit}"
                if offset:
                    where_clause += f" OFFSET {offset}"
            
            # Get versions
            version_results = self.db.select(
                "raw_document_register",
                where_clause,
                tuple(params)
            )
            
            # Convert to models
            versions = []
            for version_data in version_results:
                # Convert status string to enum
                if 'status' in version_data and version_data['status']:
                    version_data['status'] = VersionStatus(version_data['status'])
                else:
                    version_data['status'] = VersionStatus.ACTIVE
                
                # Convert deletion_reason if present
                if version_data.get('deletion_reason'):
                    version_data['deletion_reason'] = DeletionReason(version_data['deletion_reason'])
                
                # Ensure metadata is a dict
                if isinstance(version_data.get('metadata'), str):
                    try:
                        version_data['metadata'] = json.loads(version_data['metadata']) if version_data['metadata'] else {}
                    except (json.JSONDecodeError, TypeError):
                        version_data['metadata'] = {}
                elif not version_data.get('metadata'):
                    version_data['metadata'] = {}
                
                # Ensure labels is a list
                if isinstance(version_data.get('labels'), str):
                    try:
                        version_data['labels'] = json.loads(version_data['labels']) if version_data['labels'] else []
                    except (json.JSONDecodeError, TypeError):
                        version_data['labels'] = []
                elif not version_data.get('labels'):
                    version_data['labels'] = []
                
                versions.append(DocumentVersionModel(**version_data))
            
            return VersionHistoryResponse(
                lineage_uuid=lineage_uuid,
                original_filename=lineage.original_filename,
                total_versions=lineage.total_versions,
                current_version=lineage.current_version,
                versions=versions
            )
            
        except Exception as e:
            logger.error(f"Error getting version history for {lineage_uuid}: {e}")
            raise DocumentVersionError(f"Failed to get version history: {str(e)}")
    
    async def get_current_version(self, lineage_uuid: str) -> Optional[DocumentVersionModel]:
        """Get the current active version of a lineage."""
        try:
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                return None
            
            # Get the current version
            results = self.db.select(
                "raw_document_register",
                "lineage_uuid = ? AND version_number = ? AND status != ?",
                (lineage_uuid, lineage.current_version, VersionStatus.DELETED.value)
            )
            
            if not results:
                return None
            
            version_data = results[0]
            
            # Convert enums
            if version_data.get('status'):
                version_data['status'] = VersionStatus(version_data['status'])
            if version_data.get('deletion_reason'):
                version_data['deletion_reason'] = DeletionReason(version_data['deletion_reason'])
            
            # Ensure metadata is a dict
            if isinstance(version_data.get('metadata'), str):
                try:
                    version_data['metadata'] = json.loads(version_data['metadata']) if version_data['metadata'] else {}
                except (json.JSONDecodeError, TypeError):
                    version_data['metadata'] = {}
            elif not version_data.get('metadata'):
                version_data['metadata'] = {}
            
            # Ensure labels is a list
            if isinstance(version_data.get('labels'), str):
                try:
                    version_data['labels'] = json.loads(version_data['labels']) if version_data['labels'] else []
                except (json.JSONDecodeError, TypeError):
                    version_data['labels'] = []
            elif not version_data.get('labels'):
                version_data['labels'] = []
            
            return DocumentVersionModel(**version_data)
            
        except Exception as e:
            logger.error(f"Error getting current version for {lineage_uuid}: {e}")
            return None
    
    async def get_next_version_number(self, lineage_uuid: str) -> int:
        """Get the next version number for a lineage."""
        try:
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                raise DocumentNotFoundError(lineage_uuid)
            
            return lineage.total_versions + 1
            
        except Exception as e:
            logger.error(f"Error getting next version number for {lineage_uuid}: {e}")
            raise DocumentVersionError(f"Failed to get next version number: {str(e)}")
    
    async def soft_delete_lineage(
        self,
        lineage_uuid: str,
        reason: DeletionReason,
        user_id: str,
        force: bool = False
    ) -> bool:
        """Soft delete an entire lineage."""
        try:
            # Check if lineage exists
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                raise DocumentNotFoundError(lineage_uuid)
            
            # If not force, check if there are active versions
            if not force:
                active_versions = self.db.select(
                    "raw_document_register",
                    "lineage_uuid = ? AND status = ?",
                    (lineage_uuid, VersionStatus.ACTIVE.value)
                )
                
                if active_versions:
                    raise DocumentVersionError(
                        f"Cannot delete lineage with active versions. Use force=True to override.",
                        lineage_uuid=lineage_uuid
                    )
            
            # Mark lineage as inactive
            lineage_success = self.db.update(
                "document_lineage",
                {"is_active": False},
                "lineage_uuid = ?",
                (lineage_uuid,)
            )
            
            # Mark all active versions as deleted (preserve existing deletion reasons)
            versions_success = self.db.update(
                "raw_document_register",
                {
                    "status": VersionStatus.DELETED.value,
                    "deletion_reason": reason.value
                },
                "lineage_uuid = ? AND status != ?",
                (lineage_uuid, VersionStatus.DELETED.value)
            )
            
            success = lineage_success and versions_success
            
            if success:
                logger.info(f"Soft deleted lineage {lineage_uuid} by user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error soft deleting lineage {lineage_uuid}: {e}")
            return False
    
    async def restore_lineage(self, lineage_uuid: str, user_id: str) -> bool:
        """Restore a soft-deleted lineage."""
        try:
            # Restore lineage
            lineage_success = self.db.update(
                "document_lineage",
                {"is_active": True},
                "lineage_uuid = ?",
                (lineage_uuid,)
            )
            
            # Restore all versions (but keep individual deletion reasons)
            versions_success = self.db.update(
                "raw_document_register",
                {"status": VersionStatus.ACTIVE.value},
                "lineage_uuid = ? AND status = ?",
                (lineage_uuid, VersionStatus.DELETED.value)
            )
            
            success = lineage_success and versions_success
            
            if success:
                logger.info(f"Restored lineage {lineage_uuid} by user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring lineage {lineage_uuid}: {e}")
            return False
    
    async def get_lineage_statistics(self, lineage_uuid: str) -> Dict[str, Any]:
        """Get statistics for a lineage."""
        try:
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                return {}
            
            # Count versions by status
            active_count = self.db.count(
                "raw_document_register",
                "lineage_uuid = ? AND status = ?",
                (lineage_uuid, VersionStatus.ACTIVE.value)
            )
            
            deleted_count = self.db.count(
                "raw_document_register",
                "lineage_uuid = ? AND status = ?",
                (lineage_uuid, VersionStatus.DELETED.value)
            )
            
            # Get creation and last update times
            versions = self.db.select(
                "raw_document_register",
                "lineage_uuid = ? ORDER BY timestamp ASC",
                (lineage_uuid,)
            )
            
            first_version_time = None
            last_version_time = None
            
            if versions:
                first_version_time = versions[0]['timestamp']
                last_version_time = versions[-1]['timestamp']
            
            return {
                "lineage_uuid": lineage_uuid,
                "total_versions": lineage.total_versions,
                "active_versions": active_count,
                "deleted_versions": deleted_count,
                "current_version": lineage.current_version,
                "is_active": lineage.is_active,
                "created_at": lineage.created_at.isoformat(),
                "first_version_at": first_version_time,
                "last_version_at": last_version_time,
                "created_by": lineage.created_by
            }
            
        except Exception as e:
            logger.error(f"Error getting lineage statistics for {lineage_uuid}: {e}")
            return {}
    
    async def get_lineages_by_user(
        self,
        user_id: str,
        include_inactive: bool = False,
        limit: Optional[int] = None
    ) -> List[DocumentLineageModel]:
        """Get all lineages created by a specific user."""
        try:
            where_clause = "created_by = ?"
            params = [user_id]
            
            if not include_inactive:
                where_clause += " AND is_active = ?"
                params.append(True)
            
            where_clause += " ORDER BY created_at DESC"
            
            if limit:
                where_clause += f" LIMIT {limit}"
            
            results = self.db.select(
                "document_lineage",
                where_clause,
                tuple(params)
            )
            
            lineages = []
            for lineage_data in results:
                lineages.append(DocumentLineageModel(**lineage_data))
            
            return lineages
            
        except Exception as e:
            logger.error(f"Error getting lineages for user {user_id}: {e}")
            return []
    
    async def get_lineage_tree(self, lineage_uuid: str) -> Dict[str, Any]:
        """Get the complete version tree for a lineage showing branching structure."""
        try:
            lineage = await self.get_lineage(lineage_uuid)
            if not lineage:
                return {}
            
            # Get all versions in the lineage
            versions = await self.get_version_history(lineage_uuid, include_deleted=True)
            if not versions:
                return {}
            
            # Build tree structure
            tree = {
                "lineage_uuid": lineage_uuid,
                "original_filename": lineage.original_filename,
                "created_by": lineage.created_by,
                "created_at": lineage.created_at.isoformat(),
                "is_active": lineage.is_active,
                "versions": []
            }
            
            # Organize versions by their parent relationships
            version_map = {}
            root_versions = []
            
            for version in versions.versions:
                version_info = {
                    "doc_uuid": version.doc_uuid,
                    "version_number": version.version_number,
                    "filename": version.filename,
                    "created_at": version.timestamp.isoformat(),
                    "created_by": version.user_id,
                    "status": version.status.value,
                    "is_current": version.is_current,
                    "parent_version": version.edit_source_version,
                    "children": []
                }
                
                version_map[version.version_number] = version_info
                
                if version.edit_source_version is None:
                    # This is a root version (not branched from another)
                    root_versions.append(version_info)
            
            # Build parent-child relationships
            for version_info in version_map.values():
                if version_info["parent_version"] is not None:
                    parent = version_map.get(version_info["parent_version"])
                    if parent:
                        parent["children"].append(version_info)
            
            tree["versions"] = root_versions
            return tree
            
        except Exception as e:
            logger.error(f"Error getting lineage tree for {lineage_uuid}: {e}")
            return {}
    
    async def find_lineages_by_filename(
        self,
        filename_pattern: str,
        exact_match: bool = False,
        include_inactive: bool = False
    ) -> List[DocumentLineageModel]:
        """Find lineages by original filename pattern."""
        try:
            if exact_match:
                where_clause = "original_filename = ?"
                params = [filename_pattern]
            else:
                where_clause = "original_filename LIKE ?"
                params = [f"%{filename_pattern}%"]
            
            if not include_inactive:
                where_clause += " AND is_active = ?"
                params.append(True)
            
            where_clause += " ORDER BY created_at DESC"
            
            results = self.db.select(
                "document_lineage",
                where_clause,
                tuple(params)
            )
            
            lineages = []
            for lineage_data in results:
                lineages.append(DocumentLineageModel(**lineage_data))
            
            return lineages
            
        except Exception as e:
            logger.error(f"Error finding lineages by filename pattern {filename_pattern}: {e}")
            return []
    
    async def get_lineage_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for lineages, optionally filtered by user."""
        try:
            where_clause = "1=1"
            params = []
            
            if user_id:
                where_clause += " AND created_by = ?"
                params.append(user_id)
            
            # Get total counts
            total_lineages = self.db.count("document_lineage", where_clause, tuple(params) if params else None)
            
            active_where = where_clause + " AND is_active = ?"
            active_params = params + [True]
            active_lineages = self.db.count("document_lineage", active_where, tuple(active_params))
            
            # Get version counts
            version_where = "1=1"
            version_params = []
            
            if user_id:
                # Join with lineage table to filter by user
                version_results = self.db.execute_query("""
                    SELECT COUNT(*) as count 
                    FROM raw_document_register rdr 
                    JOIN document_lineage dl ON rdr.lineage_uuid = dl.lineage_uuid 
                    WHERE dl.created_by = ?
                """, (user_id,), fetch=True)
                total_versions = version_results[0]['count'] if version_results else 0
                
                active_version_results = self.db.execute_query("""
                    SELECT COUNT(*) as count 
                    FROM raw_document_register rdr 
                    JOIN document_lineage dl ON rdr.lineage_uuid = dl.lineage_uuid 
                    WHERE dl.created_by = ? AND rdr.status = ?
                """, (user_id, VersionStatus.ACTIVE.value), fetch=True)
                active_versions = active_version_results[0]['count'] if active_version_results else 0
            else:
                total_versions = self.db.count("raw_document_register")
                active_versions = self.db.count(
                    "raw_document_register", 
                    "status = ?", 
                    (VersionStatus.ACTIVE.value,)
                )
            
            return {
                "total_lineages": total_lineages,
                "active_lineages": active_lineages,
                "inactive_lineages": total_lineages - active_lineages,
                "total_versions": total_versions,
                "active_versions": active_versions,
                "deleted_versions": total_versions - active_versions,
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting lineage summary: {e}")
            return {}