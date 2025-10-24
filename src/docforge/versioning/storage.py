"""Raw document storage and retrieval operations."""

import os
import shutil
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dbm.operations import get_db_operations
from core.exceptions import DocumentVersionError, DocumentNotFoundError
from .models import (
    DocumentVersionModel,
    VersionStatus,
    DeletionReason,
    calculate_file_hash
)
from .versions import VersionManager
from .lineage import LineageManager

logger = logging.getLogger(__name__)


class RawDocumentStorage:
    """Manages raw document file storage and database operations."""
    
    def __init__(self, storage_base_path: str = "./data/raw_documents"):
        self.storage_base_path = Path(storage_base_path)
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        self.db = get_db_operations()
        self.version_manager = VersionManager()
        self.lineage_manager = LineageManager()
    
    def get_document_storage_path(
        self,
        lineage_uuid: str,
        version_number: int,
        filename: str
    ) -> Path:
        """Get the storage path for a document version."""
        return self.storage_base_path / lineage_uuid / f"v{version_number}" / filename
    
    def get_lineage_storage_path(self, lineage_uuid: str) -> Path:
        """Get the storage directory for a lineage."""
        return self.storage_base_path / lineage_uuid
    
    async def store_document_file(
        self,
        lineage_uuid: str,
        version_number: int,
        filename: str,
        file_content: bytes
    ) -> str:
        """Store a document file and return the file path."""
        try:
            file_path = self.get_document_storage_path(lineage_uuid, version_number, filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Verify file was written correctly
            if not file_path.exists():
                raise DocumentVersionError(f"Failed to write file to {file_path}")
            
            # Verify file integrity
            with open(file_path, 'rb') as f:
                stored_content = f.read()
            
            if calculate_file_hash(stored_content) != calculate_file_hash(file_content):
                raise DocumentVersionError(f"File integrity check failed for {file_path}")
            
            logger.info(f"Stored document file: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error storing document file: {e}")
            raise DocumentVersionError(f"Failed to store document file: {str(e)}")
    
    async def retrieve_document_file(self, doc_uuid: str) -> Optional[bytes]:
        """Retrieve document file content by UUID."""
        try:
            version = await self.version_manager.get_version(doc_uuid)
            if not version:
                return None
            
            file_path = Path(version.file_path)
            if not file_path.exists():
                logger.warning(f"Document file not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Verify file integrity
            if calculate_file_hash(content) != version.file_hash:
                logger.error(f"File integrity check failed for {doc_uuid}")
                raise DocumentVersionError(f"File integrity check failed for {doc_uuid}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving document file {doc_uuid}: {e}")
            return None
    
    async def retrieve_document_by_lineage_version(
        self,
        lineage_uuid: str,
        version_number: int
    ) -> Optional[bytes]:
        """Retrieve document file content by lineage and version number."""
        try:
            version = await self.version_manager.get_version_by_number(
                lineage_uuid, version_number
            )
            if not version:
                return None
            
            return await self.retrieve_document_file(version.doc_uuid)
            
        except Exception as e:
            logger.error(f"Error retrieving document by lineage {lineage_uuid} v{version_number}: {e}")
            return None
    
    async def get_document_versions_with_content(
        self,
        lineage_uuid: str,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all versions of a document with their content availability."""
        try:
            versions = await self.version_manager.get_versions_by_lineage(
                lineage_uuid, include_deleted
            )
            
            result = []
            for version in versions:
                file_path = Path(version.file_path)
                content_available = file_path.exists()
                
                file_size_on_disk = None
                if content_available:
                    try:
                        file_size_on_disk = file_path.stat().st_size
                    except Exception:
                        content_available = False
                
                result.append({
                    "doc_uuid": version.doc_uuid,
                    "version_number": version.version_number,
                    "filename": version.filename,
                    "file_type": version.file_type,
                    "file_hash": version.file_hash,
                    "file_size": version.file_size,
                    "file_size_on_disk": file_size_on_disk,
                    "content_available": content_available,
                    "file_path": version.file_path,
                    "status": version.status.value,
                    "is_current": version.is_current,
                    "created_at": version.timestamp.isoformat(),
                    "created_by": version.user_id
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting document versions with content for {lineage_uuid}: {e}")
            return []
    
    async def cleanup_deleted_files(
        self,
        lineage_uuid: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up files for deleted document versions."""
        try:
            cleanup_stats = {
                "files_found": 0,
                "files_deleted": 0,
                "space_freed": 0,
                "errors": [],
                "dry_run": dry_run
            }
            
            # Get deleted versions
            where_clause = "status = ?"
            params = [VersionStatus.DELETED.value]
            
            if lineage_uuid:
                where_clause += " AND lineage_uuid = ?"
                params.append(lineage_uuid)
            
            deleted_versions = self.db.select(
                "raw_document_register",
                where_clause,
                tuple(params)
            )
            
            for version_data in deleted_versions:
                file_path = Path(version_data['file_path'])
                
                if file_path.exists():
                    cleanup_stats["files_found"] += 1
                    file_size = file_path.stat().st_size
                    
                    if not dry_run:
                        try:
                            file_path.unlink()
                            cleanup_stats["files_deleted"] += 1
                            cleanup_stats["space_freed"] += file_size
                            logger.info(f"Deleted file: {file_path}")
                        except Exception as e:
                            error_msg = f"Failed to delete {file_path}: {str(e)}"
                            cleanup_stats["errors"].append(error_msg)
                            logger.error(error_msg)
                    else:
                        cleanup_stats["space_freed"] += file_size
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            return {"error": str(e)}
    
    async def verify_storage_integrity(
        self,
        lineage_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify the integrity of stored documents."""
        try:
            integrity_report = {
                "total_checked": 0,
                "files_missing": 0,
                "hash_mismatches": 0,
                "size_mismatches": 0,
                "valid_files": 0,
                "issues": []
            }
            
            # Get active versions
            where_clause = "status = ?"
            params = [VersionStatus.ACTIVE.value]
            
            if lineage_uuid:
                where_clause += " AND lineage_uuid = ?"
                params.append(lineage_uuid)
            
            versions = self.db.select(
                "raw_document_register",
                where_clause,
                tuple(params)
            )
            
            for version_data in versions:
                integrity_report["total_checked"] += 1
                doc_uuid = version_data['doc_uuid']
                file_path = Path(version_data['file_path'])
                expected_hash = version_data['file_hash']
                expected_size = version_data['file_size']
                
                # Check if file exists
                if not file_path.exists():
                    integrity_report["files_missing"] += 1
                    integrity_report["issues"].append({
                        "doc_uuid": doc_uuid,
                        "issue": "file_missing",
                        "file_path": str(file_path)
                    })
                    continue
                
                try:
                    # Check file size
                    actual_size = file_path.stat().st_size
                    if actual_size != expected_size:
                        integrity_report["size_mismatches"] += 1
                        integrity_report["issues"].append({
                            "doc_uuid": doc_uuid,
                            "issue": "size_mismatch",
                            "expected_size": expected_size,
                            "actual_size": actual_size,
                            "file_path": str(file_path)
                        })
                    
                    # Check file hash
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    actual_hash = calculate_file_hash(content)
                    if actual_hash != expected_hash:
                        integrity_report["hash_mismatches"] += 1
                        integrity_report["issues"].append({
                            "doc_uuid": doc_uuid,
                            "issue": "hash_mismatch",
                            "expected_hash": expected_hash,
                            "actual_hash": actual_hash,
                            "file_path": str(file_path)
                        })
                    
                    # If we get here, the file is valid
                    if actual_size == expected_size and actual_hash == expected_hash:
                        integrity_report["valid_files"] += 1
                
                except Exception as e:
                    integrity_report["issues"].append({
                        "doc_uuid": doc_uuid,
                        "issue": "read_error",
                        "error": str(e),
                        "file_path": str(file_path)
                    })
            
            return integrity_report
            
        except Exception as e:
            logger.error(f"Error during integrity verification: {e}")
            return {"error": str(e)}
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        try:
            stats = {
                "total_files": 0,
                "total_size": 0,
                "active_files": 0,
                "active_size": 0,
                "deleted_files": 0,
                "deleted_size": 0,
                "lineage_count": 0,
                "file_types": {},
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Get all versions
            all_versions = self.db.select("raw_document_register")
            
            # Get lineage count
            stats["lineage_count"] = self.db.count("document_lineage")
            
            for version in all_versions:
                file_path = Path(version['file_path'])
                file_type = version['file_type']
                file_size = version['file_size']
                status = version['status']
                
                # Update file type stats
                if file_type not in stats["file_types"]:
                    stats["file_types"][file_type] = {"count": 0, "size": 0}
                stats["file_types"][file_type]["count"] += 1
                stats["file_types"][file_type]["size"] += file_size
                
                # Update total stats
                stats["total_files"] += 1
                stats["total_size"] += file_size
                
                # Update status-specific stats
                if status == VersionStatus.ACTIVE.value:
                    stats["active_files"] += 1
                    stats["active_size"] += file_size
                elif status == VersionStatus.DELETED.value:
                    stats["deleted_files"] += 1
                    stats["deleted_size"] += file_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {"error": str(e)}
    
    async def create_temporary_storage(
        self,
        content: bytes,
        filename: str,
        temp_id: Optional[str] = None
    ) -> str:
        """Create temporary storage for duplicate detection and processing."""
        try:
            import uuid
            if not temp_id:
                temp_id = str(uuid.uuid4())
            
            temp_dir = self.storage_base_path / "temp" / temp_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            temp_file_path = temp_dir / filename
            
            with open(temp_file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Created temporary storage: {temp_file_path}")
            return str(temp_file_path)
            
        except Exception as e:
            logger.error(f"Error creating temporary storage: {e}")
            raise DocumentVersionError(f"Failed to create temporary storage: {str(e)}")
    
    async def cleanup_temporary_storage(
        self,
        temp_id: Optional[str] = None,
        older_than_hours: int = 24
    ) -> Dict[str, Any]:
        """Clean up temporary storage files."""
        try:
            temp_base = self.storage_base_path / "temp"
            if not temp_base.exists():
                return {"cleaned": 0, "errors": []}
            
            cleanup_stats = {"cleaned": 0, "errors": []}
            cutoff_time = datetime.utcnow().timestamp() - (older_than_hours * 3600)
            
            if temp_id:
                # Clean specific temp directory
                temp_dir = temp_base / temp_id
                if temp_dir.exists():
                    try:
                        shutil.rmtree(temp_dir)
                        cleanup_stats["cleaned"] += 1
                        logger.info(f"Cleaned temporary directory: {temp_dir}")
                    except Exception as e:
                        error_msg = f"Failed to clean {temp_dir}: {str(e)}"
                        cleanup_stats["errors"].append(error_msg)
                        logger.error(error_msg)
            else:
                # Clean old temp directories
                for temp_dir in temp_base.iterdir():
                    if temp_dir.is_dir():
                        try:
                            dir_mtime = temp_dir.stat().st_mtime
                            if dir_mtime < cutoff_time:
                                shutil.rmtree(temp_dir)
                                cleanup_stats["cleaned"] += 1
                                logger.info(f"Cleaned old temporary directory: {temp_dir}")
                        except Exception as e:
                            error_msg = f"Failed to clean {temp_dir}: {str(e)}"
                            cleanup_stats["errors"].append(error_msg)
                            logger.error(error_msg)
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during temporary storage cleanup: {e}")
            return {"error": str(e)}