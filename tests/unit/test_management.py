"""Test version management operations."""

import pytest
import tempfile
import os

from src.dbm.connection import DummyDBConnection
from src.docforge.versioning.management import VersionManagementService
from src.docforge.versioning.models import (
    DocumentRegistrationRequest,
    DeletionReason,
    VersionStatus
)
from src.docforge.versioning.versions import VersionManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_db_setup(temp_db_path):
    """Set up test database with versioning schema."""
    # Override the global connection for testing
    from src.dbm import connection, operations
    original_connection = connection._db_connection
    original_operations = operations._db_operations
    
    # Create test connection with updated schema
    test_connection = DummyDBConnection(temp_db_path)
    connection._db_connection = test_connection
    operations._db_operations = None  # Reset to create new instance
    
    yield test_connection
    
    # Restore original instances
    connection._db_connection = original_connection
    operations._db_operations = original_operations


@pytest.fixture
def management_service(test_db_setup, temp_storage_path):
    """Create test version management service."""
    return VersionManagementService(temp_storage_path)


@pytest.fixture
def version_manager(test_db_setup):
    """Create test version manager."""
    return VersionManager()


@pytest.mark.asyncio
async def test_create_version_branch(management_service, version_manager, temp_storage_path):
    """Test creating a version branch."""
    # Create initial version
    request = DocumentRegistrationRequest(
        filename="original.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    original_content = b"Original text"
    
    response = await version_manager.register_version(
        request,
        original_content,
        temp_storage_path
    )
    
    # Create branch from version 1
    branch_content = b"Modified text"
    
    branch_result = await management_service.create_version_branch(
        lineage_uuid=response.lineage_uuid,
        source_version=1,
        new_filename="modified.txt",
        file_content=branch_content,
        user_id="user456",
        labels=["branch", "modified"],
        metadata={"branch_reason": "content_update"}
    )
    
    assert branch_result["lineage_uuid"] == response.lineage_uuid
    assert branch_result["source_version"] == 1
    assert branch_result["filename"] == "modified.txt"
    assert branch_result["created_by"] == "user456"
    assert branch_result["is_branch"] is True
    assert "branch_info" in branch_result


@pytest.mark.asyncio
async def test_edit_old_version(management_service, version_manager, temp_storage_path):
    """Test editing an old version by creating a branch."""
    # Create initial version
    request = DocumentRegistrationRequest(
        filename="document.txt",
        file_type="txt",
        file_size=15,
        user_id="user123"
    )
    
    original_content = b"Original content"
    
    response = await version_manager.register_version(
        request,
        original_content,
        temp_storage_path
    )
    
    # Edit the version
    edited_content = b"Edited content"
    
    edit_result = await management_service.edit_old_version(
        doc_uuid=response.doc_uuid,
        new_filename="document_edited.txt",
        file_content=edited_content,
        user_id="user456",
        labels=["edited"],
        metadata={"edit_reason": "content_improvement"}
    )
    
    assert edit_result["lineage_uuid"] == response.lineage_uuid
    assert edit_result["source_version"] == 1
    assert edit_result["filename"] == "document_edited.txt"
    assert edit_result["created_by"] == "user456"
    assert edit_result["is_branch"] is True


@pytest.mark.asyncio
async def test_soft_delete_with_tracking(management_service, version_manager, temp_storage_path):
    """Test soft deleting a version with comprehensive tracking."""
    # Create a version
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Test content"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Soft delete with tracking
    delete_result = await management_service.soft_delete_version_with_tracking(
        doc_uuid=response.doc_uuid,
        reason=DeletionReason.USER_REQUEST,
        user_id="user123",
        notes="User requested deletion"
    )
    
    assert delete_result["doc_uuid"] == response.doc_uuid
    assert delete_result["lineage_uuid"] == response.lineage_uuid
    assert delete_result["deletion_reason"] == "user_request"
    assert delete_result["deleted_by"] == "user123"
    assert delete_result["deletion_notes"] == "User requested deletion"
    assert delete_result["success"] is True


@pytest.mark.asyncio
async def test_restore_version_with_tracking(management_service, version_manager, temp_storage_path):
    """Test restoring a version with tracking."""
    # Create and delete a version
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Test content"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Delete it first
    await management_service.soft_delete_version_with_tracking(
        doc_uuid=response.doc_uuid,
        reason=DeletionReason.USER_REQUEST,
        user_id="user123"
    )
    
    # Restore it
    restore_result = await management_service.restore_version_with_tracking(
        doc_uuid=response.doc_uuid,
        user_id="admin123",
        notes="Restoration requested by admin"
    )
    
    assert restore_result["doc_uuid"] == response.doc_uuid
    assert restore_result["restored_by"] == "admin123"
    assert restore_result["restoration_notes"] == "Restoration requested by admin"
    assert restore_result["success"] is True
    assert restore_result["previous_deletion_reason"] == "user_request"


@pytest.mark.asyncio
async def test_get_version_relationships(management_service, version_manager, temp_storage_path):
    """Test getting version relationships."""
    # Create initial version
    request = DocumentRegistrationRequest(
        filename="original.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    original_content = b"Original text"
    
    response = await version_manager.register_version(
        request,
        original_content,
        temp_storage_path
    )
    
    # Create a branch
    branch_content = b"Branch content"
    
    branch_result = await management_service.create_version_branch(
        lineage_uuid=response.lineage_uuid,
        source_version=1,
        new_filename="branch.txt",
        file_content=branch_content,
        user_id="user456"
    )
    
    # Get relationships for the branch
    relationships = await management_service.get_version_relationships(
        branch_result["doc_uuid"]
    )
    
    assert relationships["current_version"]["doc_uuid"] == branch_result["doc_uuid"]
    assert relationships["parent"] is not None
    assert relationships["parent"]["doc_uuid"] == response.doc_uuid
    assert relationships["lineage_info"]["lineage_uuid"] == response.lineage_uuid
    assert relationships["lineage_info"]["total_versions"] == 2


@pytest.mark.asyncio
async def test_bulk_version_operation(management_service, version_manager, temp_storage_path):
    """Test bulk version operations."""
    # Create multiple versions
    doc_uuids = []
    
    for i in range(3):
        request = DocumentRegistrationRequest(
            filename=f"test{i}.txt",
            file_type="txt",
            file_size=10 + i,
            user_id="user123"
        )
        
        file_content = f"Content {i}".encode()
        
        response = await version_manager.register_version(
            request,
            file_content,
            temp_storage_path
        )
        doc_uuids.append(response.doc_uuid)
    
    # Bulk soft delete
    bulk_result = await management_service.bulk_version_operation(
        operation="soft_delete",
        doc_uuids=doc_uuids,
        user_id="admin123",
        reason=DeletionReason.ADMIN_ACTION,
        notes="Bulk cleanup"
    )
    
    assert bulk_result["operation"] == "soft_delete"
    assert bulk_result["total_requested"] == 3
    assert bulk_result["successful"] == 3
    assert bulk_result["failed"] == 0
    assert len(bulk_result["results"]) == 3


@pytest.mark.asyncio
async def test_privacy_compliance_report(management_service, version_manager, temp_storage_path):
    """Test generating privacy compliance report."""
    # Create and delete some versions
    request = DocumentRegistrationRequest(
        filename="private.txt",
        file_type="txt",
        file_size=20,
        user_id="user123"
    )
    
    file_content = b"Private information"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Delete for privacy
    await management_service.soft_delete_version_with_tracking(
        doc_uuid=response.doc_uuid,
        reason=DeletionReason.PRIVACY_REQUEST,
        user_id="user123",
        notes="Privacy compliance"
    )
    
    # Generate report
    report = await management_service.get_privacy_compliance_report(
        user_id="user123"
    )
    
    assert "generated_at" in report
    assert "summary" in report
    assert "deletion_reasons" in report
    assert "recent_deletions" in report
    assert "storage_impact" in report
    assert report["user_id"] == "user123"