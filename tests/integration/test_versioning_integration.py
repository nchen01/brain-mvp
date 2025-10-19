"""Integration tests for document registration and versioning system."""

import pytest
import tempfile
import os
from pathlib import Path

from src.dbm.connection import DummyDBConnection
from src.docforge.versioning.management import VersionManagementService
from src.docforge.versioning.versions import VersionManager
from src.docforge.versioning.lineage import LineageManager
from src.docforge.versioning.deletion import DeletionManager
from src.docforge.versioning.storage import RawDocumentStorage
from src.docforge.versioning.models import (
    DocumentRegistrationRequest,
    DeletionReason,
    VersionStatus
)
from src.core.exceptions import DuplicateDocumentError


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
def services(test_db_setup, temp_storage_path):
    """Create all versioning services."""
    return {
        "version_manager": VersionManager(),
        "lineage_manager": LineageManager(),
        "deletion_manager": DeletionManager(),
        "storage": RawDocumentStorage(temp_storage_path),
        "management": VersionManagementService(temp_storage_path)
    }


@pytest.mark.asyncio
async def test_end_to_end_document_registration_flow(services, temp_storage_path):
    """Test complete end-to-end document registration flow."""
    version_manager = services["version_manager"]
    lineage_manager = services["lineage_manager"]
    storage = services["storage"]
    
    # Step 1: Register initial document
    request = DocumentRegistrationRequest(
        filename="business_plan.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="john_doe",
        labels=["business", "plan", "2024"],
        metadata={"department": "strategy", "confidential": True}
    )
    
    file_content = b"Business Plan Content - Version 1"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Verify registration
    assert response.doc_uuid.startswith("doc-")
    assert response.lineage_uuid.startswith("lineage-")
    assert response.version_number == 1
    assert response.is_new_lineage is True
    assert response.is_duplicate is False
    
    # Step 2: Verify lineage creation
    lineage = await lineage_manager.get_lineage(response.lineage_uuid)
    assert lineage is not None
    assert lineage.original_filename == "business_plan.pdf"
    assert lineage.created_by == "john_doe"
    assert lineage.current_version == 1
    assert lineage.total_versions == 1
    assert lineage.is_active is True
    
    # Step 3: Verify version storage
    version = await version_manager.get_version(response.doc_uuid)
    assert version is not None
    assert version.filename == "business_plan.pdf"
    assert version.file_type == "pdf"
    assert version.file_size == 1024
    assert version.user_id == "john_doe"
    assert version.labels == ["business", "plan", "2024"]
    assert version.metadata["department"] == "strategy"
    assert version.is_current is True
    assert version.status == VersionStatus.ACTIVE
    
    # Step 4: Verify file storage
    stored_content = await storage.retrieve_document_file(response.doc_uuid)
    assert stored_content == file_content
    
    # Step 5: Verify file path exists
    file_path = Path(response.file_path)
    assert file_path.exists()
    assert file_path.read_bytes() == file_content


@pytest.mark.asyncio
async def test_version_chain_creation_and_management(services, temp_storage_path):
    """Test version chain creation and management."""
    version_manager = services["version_manager"]
    lineage_manager = services["lineage_manager"]
    
    # Create initial version
    request_v1 = DocumentRegistrationRequest(
        filename="document_v1.docx",
        file_type="docx",
        file_size=512,
        user_id="alice",
        labels=["draft"]
    )
    
    content_v1 = b"Document Version 1 Content"
    
    response_v1 = await version_manager.register_version(
        request_v1,
        content_v1,
        temp_storage_path
    )
    
    # Create version 2 in same lineage
    request_v2 = DocumentRegistrationRequest(
        filename="document_v2.docx",
        file_type="docx",
        file_size=768,
        user_id="alice",
        labels=["revision"],
        parent_lineage=response_v1.lineage_uuid
    )
    
    content_v2 = b"Document Version 2 Content - Updated"
    
    response_v2 = await version_manager.register_version(
        request_v2,
        content_v2,
        temp_storage_path
    )
    
    # Create version 3 in same lineage
    request_v3 = DocumentRegistrationRequest(
        filename="document_v3.docx",
        file_type="docx",
        file_size=1024,
        user_id="bob",
        labels=["final"],
        parent_lineage=response_v1.lineage_uuid
    )
    
    content_v3 = b"Document Version 3 Content - Final"
    
    response_v3 = await version_manager.register_version(
        request_v3,
        content_v3,
        temp_storage_path
    )
    
    # Verify version chain
    assert response_v1.lineage_uuid == response_v2.lineage_uuid == response_v3.lineage_uuid
    assert response_v1.version_number == 1
    assert response_v2.version_number == 2
    assert response_v3.version_number == 3
    
    # Verify lineage state
    lineage = await lineage_manager.get_lineage(response_v1.lineage_uuid)
    assert lineage.current_version == 3
    assert lineage.total_versions == 3
    
    # Verify version history
    history = await lineage_manager.get_version_history(response_v1.lineage_uuid)
    assert len(history.versions) == 3
    assert history.total_versions == 3
    assert history.current_version == 3
    
    # Verify only latest version is current
    v1 = await version_manager.get_version(response_v1.doc_uuid)
    v2 = await version_manager.get_version(response_v2.doc_uuid)
    v3 = await version_manager.get_version(response_v3.doc_uuid)
    
    assert v1.is_current is False
    assert v2.is_current is False
    assert v3.is_current is True


@pytest.mark.asyncio
async def test_version_branching_editing_old_versions(services, temp_storage_path):
    """Test version branching by editing old versions."""
    management = services["management"]
    version_manager = services["version_manager"]
    
    # Create initial version chain
    request_v1 = DocumentRegistrationRequest(
        filename="report_v1.txt",
        file_type="txt",
        file_size=100,
        user_id="researcher1"
    )
    
    content_v1 = b"Initial research findings"
    
    response_v1 = await version_manager.register_version(
        request_v1,
        content_v1,
        temp_storage_path
    )
    
    # Create version 2
    request_v2 = DocumentRegistrationRequest(
        filename="report_v2.txt",
        file_type="txt",
        file_size=150,
        user_id="researcher1",
        parent_lineage=response_v1.lineage_uuid
    )
    
    content_v2 = b"Updated research findings with more data"
    
    response_v2 = await version_manager.register_version(
        request_v2,
        content_v2,
        temp_storage_path
    )
    
    # Now branch from version 1 (edit old version)
    branch_content = b"Alternative research approach from v1"
    
    branch_result = await management.create_version_branch(
        lineage_uuid=response_v1.lineage_uuid,
        source_version=1,
        new_filename="report_alternative.txt",
        file_content=branch_content,
        user_id="researcher2",
        labels=["alternative", "branch"],
        metadata={"branch_reason": "different_methodology"}
    )
    
    # Verify branch creation
    assert branch_result["lineage_uuid"] == response_v1.lineage_uuid
    assert branch_result["source_version"] == 1
    assert branch_result["version_number"] == 3  # Should be next version number
    assert branch_result["is_branch"] is True
    assert branch_result["created_by"] == "researcher2"
    
    # Verify branch version details
    branch_version = await version_manager.get_version(branch_result["doc_uuid"])
    assert branch_version.edit_source_version == 1  # Branched from version 1
    assert branch_version.version_number == 3
    assert branch_version.filename == "report_alternative.txt"
    
    # Test editing old version directly
    edit_content = b"Direct edit of version 1 with new insights"
    
    edit_result = await management.edit_old_version(
        doc_uuid=response_v1.doc_uuid,
        new_filename="report_v1_edited.txt",
        file_content=edit_content,
        user_id="researcher3",
        labels=["edited", "insights"]
    )
    
    # Verify edit result
    assert edit_result["lineage_uuid"] == response_v1.lineage_uuid
    assert edit_result["source_version"] == 1
    assert edit_result["version_number"] == 4  # Next version number
    assert edit_result["created_by"] == "researcher3"
    
    # Verify lineage now has 4 versions
    lineage = await services["lineage_manager"].get_lineage(response_v1.lineage_uuid)
    assert lineage.total_versions == 4


@pytest.mark.asyncio
async def test_soft_deletion_and_restoration(services, temp_storage_path):
    """Test soft deletion and restoration functionality."""
    management = services["management"]
    version_manager = services["version_manager"]
    storage = services["storage"]
    
    # Create a document
    request = DocumentRegistrationRequest(
        filename="sensitive_doc.pdf",
        file_type="pdf",
        file_size=2048,
        user_id="employee123"
    )
    
    file_content = b"Sensitive company information"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Verify document is active
    version = await version_manager.get_version(response.doc_uuid)
    assert version.status == VersionStatus.ACTIVE
    assert version.is_current is True
    
    # Soft delete for privacy
    delete_result = await management.soft_delete_version_with_tracking(
        doc_uuid=response.doc_uuid,
        reason=DeletionReason.PRIVACY_REQUEST,
        user_id="employee123",
        notes="Employee requested data removal"
    )
    
    # Verify deletion result
    assert delete_result["success"] is True
    assert delete_result["deletion_reason"] == "privacy_request"
    assert delete_result["deleted_by"] == "employee123"
    assert delete_result["deletion_notes"] == "Employee requested data removal"
    
    # Verify version is marked as deleted
    deleted_version = await version_manager.get_version(response.doc_uuid)
    assert deleted_version.status == VersionStatus.DELETED
    assert deleted_version.deletion_reason == DeletionReason.PRIVACY_REQUEST
    assert deleted_version.is_current is False
    
    # Verify file still exists (soft delete)
    stored_content = await storage.retrieve_document_file(response.doc_uuid)
    assert stored_content == file_content
    
    # Restore the version
    restore_result = await management.restore_version_with_tracking(
        doc_uuid=response.doc_uuid,
        user_id="admin456",
        notes="Restoration approved by legal"
    )
    
    # Verify restoration result
    assert restore_result["success"] is True
    assert restore_result["restored_by"] == "admin456"
    assert restore_result["restoration_notes"] == "Restoration approved by legal"
    assert restore_result["previous_deletion_reason"] == "privacy_request"
    
    # Verify version is restored
    restored_version = await version_manager.get_version(response.doc_uuid)
    assert restored_version.status == VersionStatus.ACTIVE
    assert restored_version.deletion_reason is None


@pytest.mark.asyncio
async def test_duplicate_detection_and_handling(services, temp_storage_path):
    """Test duplicate detection and handling."""
    version_manager = services["version_manager"]
    
    # Create initial document
    request1 = DocumentRegistrationRequest(
        filename="original.txt",
        file_type="txt",
        file_size=20,
        user_id="user1"
    )
    
    file_content = b"Unique file content"
    
    response1 = await version_manager.register_version(
        request1,
        file_content,
        temp_storage_path
    )
    
    # Try to register same content (should detect duplicate)
    request2 = DocumentRegistrationRequest(
        filename="duplicate.txt",
        file_type="txt",
        file_size=20,
        user_id="user2"
    )
    
    # Should raise DocumentVersionError (which wraps DuplicateDocumentError)
    from src.core.exceptions import DocumentVersionError
    with pytest.raises(DocumentVersionError, match="Duplicate document detected"):
        await version_manager.register_version(
            request2,
            file_content,  # Same content
            temp_storage_path
        )
    
    # Test duplicate detection method
    from src.docforge.versioning.models import calculate_file_hash
    file_hash = calculate_file_hash(file_content)
    duplicate_result = await version_manager.check_duplicate(file_hash)
    
    assert duplicate_result.is_duplicate is True
    assert duplicate_result.existing_doc_uuid == response1.doc_uuid
    assert duplicate_result.existing_lineage_uuid == response1.lineage_uuid
    assert duplicate_result.match_confidence == 1.0
    
    # Test adding duplicate to existing lineage (should work)
    request3 = DocumentRegistrationRequest(
        filename="same_content_v2.txt",
        file_type="txt",
        file_size=20,
        user_id="user1",
        parent_lineage=response1.lineage_uuid  # Explicitly adding to lineage
    )
    
    response3 = await version_manager.register_version(
        request3,
        file_content,  # Same content but in same lineage
        temp_storage_path
    )
    
    # Should succeed because it's explicitly added to the lineage
    assert response3.lineage_uuid == response1.lineage_uuid
    assert response3.version_number == 2
    assert response3.is_duplicate is True


@pytest.mark.asyncio
async def test_complete_versioning_workflow(services, temp_storage_path):
    """Test complete versioning workflow with all operations."""
    management = services["management"]
    version_manager = services["version_manager"]
    lineage_manager = services["lineage_manager"]
    
    # Phase 1: Create initial document
    request = DocumentRegistrationRequest(
        filename="project_spec.md",
        file_type="md",
        file_size=1024,
        user_id="pm_alice",
        labels=["spec", "project", "v1"]
    )
    
    content_v1 = b"# Project Specification v1\n\nInitial requirements..."
    
    response_v1 = await version_manager.register_version(
        request,
        content_v1,
        temp_storage_path
    )
    
    # Phase 2: Create version 2
    request_v2 = DocumentRegistrationRequest(
        filename="project_spec_v2.md",
        file_type="md",
        file_size=1536,
        user_id="pm_alice",
        labels=["spec", "project", "v2"],
        parent_lineage=response_v1.lineage_uuid
    )
    
    content_v2 = b"# Project Specification v2\n\nUpdated requirements with feedback..."
    
    response_v2 = await version_manager.register_version(
        request_v2,
        content_v2,
        temp_storage_path
    )
    
    # Phase 3: Branch from v1 for alternative approach
    branch_content = b"# Project Specification - Alternative\n\nDifferent approach..."
    
    branch_result = await management.create_version_branch(
        lineage_uuid=response_v1.lineage_uuid,
        source_version=1,
        new_filename="project_spec_alternative.md",
        file_content=branch_content,
        user_id="dev_bob",
        labels=["spec", "alternative", "experimental"]
    )
    
    # Phase 4: Get version relationships
    relationships = await management.get_version_relationships(branch_result["doc_uuid"])
    
    assert relationships["current_version"]["version_number"] == 3
    assert relationships["parent"]["version_number"] == 1
    assert relationships["lineage_info"]["total_versions"] == 3
    
    # Phase 5: Soft delete version 2
    delete_result = await management.soft_delete_version_with_tracking(
        doc_uuid=response_v2.doc_uuid,
        reason=DeletionReason.ADMIN_ACTION,
        user_id="pm_alice",
        notes="Superseded by alternative approach"
    )
    
    assert delete_result["success"] is True
    
    # Phase 6: Get version history
    history = await lineage_manager.get_version_history(
        response_v1.lineage_uuid,
        include_deleted=True
    )
    
    assert len(history.versions) == 3
    assert history.versions[1].status == VersionStatus.DELETED  # v2 is deleted
    
    # Phase 7: Get lineage statistics
    stats = await lineage_manager.get_lineage_statistics(response_v1.lineage_uuid)
    
    assert stats["total_versions"] == 3
    assert stats["active_versions"] == 2  # v1 and v3 (branch)
    assert stats["deleted_versions"] == 1  # v2
    
    # Phase 8: Generate privacy compliance report
    privacy_report = await management.get_privacy_compliance_report(
        user_id="pm_alice"
    )
    
    assert "summary" in privacy_report
    assert "deletion_reasons" in privacy_report
    assert privacy_report["user_id"] == "pm_alice"
    
    # Phase 9: Bulk operations test
    # Create a few more versions to test bulk operations
    more_versions = []
    for i in range(2):
        req = DocumentRegistrationRequest(
            filename=f"temp_doc_{i}.txt",
            file_type="txt",
            file_size=100,
            user_id="pm_alice"
        )
        
        resp = await version_manager.register_version(
            req,
            f"Temp content {i}".encode(),
            temp_storage_path
        )
        more_versions.append(resp.doc_uuid)
    
    # Bulk delete
    bulk_result = await management.bulk_version_operation(
        operation="soft_delete",
        doc_uuids=more_versions,
        user_id="admin",
        reason=DeletionReason.ADMIN_ACTION,
        notes="Bulk cleanup operation"
    )
    
    assert bulk_result["successful"] == 2
    assert bulk_result["failed"] == 0
    
    # Final verification: Check overall system state
    final_stats = await management.get_privacy_compliance_report()
    assert final_stats["summary"]["total_versions"] >= 5  # At least 5 versions created