"""Test document versioning system."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime

from src.dbm.connection import DummyDBConnection
from src.docforge.versioning.models import (
    DocumentLineageModel,
    DocumentVersionModel,
    DocumentRegistrationRequest,
    VersionBranchRequest,
    SoftDeleteRequest,
    DeletionReason,
    VersionStatus,
    generate_document_uuid,
    generate_lineage_uuid,
    calculate_file_hash,
    validate_file_type
)
from src.docforge.versioning.lineage import LineageManager
from src.docforge.versioning.versions import VersionManager
from src.docforge.versioning.deletion import DeletionManager


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
def lineage_manager(test_db_setup):
    """Create test lineage manager."""
    return LineageManager()


@pytest.fixture
def version_manager(test_db_setup):
    """Create test version manager."""
    return VersionManager()


@pytest.fixture
def deletion_manager(test_db_setup):
    """Create test deletion manager."""
    return DeletionManager()


# Test Data Models

def test_document_lineage_model_creation():
    """Test DocumentLineageModel creation and validation."""
    lineage = DocumentLineageModel(
        lineage_uuid="lineage-123",
        original_filename="test.pdf",
        created_by="user123",
        created_at=datetime.utcnow(),
        current_version=1,
        total_versions=1,
        is_active=True
    )
    
    assert lineage.lineage_uuid == "lineage-123"
    assert lineage.original_filename == "test.pdf"
    assert lineage.created_by == "user123"
    assert lineage.current_version == 1
    assert lineage.total_versions == 1
    assert lineage.is_active is True


def test_document_version_model_creation():
    """Test DocumentVersionModel creation and validation."""
    version = DocumentVersionModel(
        doc_uuid="doc-123",
        lineage_uuid="lineage-123",
        version_number=1,
        filename="test.pdf",
        file_path="/path/to/test.pdf",
        file_type="pdf",
        file_hash="a" * 64,  # Valid SHA-256 hash
        file_size=1024,
        timestamp=datetime.utcnow(),
        user_id="user123",
        labels=["test", "document"],
        is_current=True,
        status=VersionStatus.ACTIVE
    )
    
    assert version.doc_uuid == "doc-123"
    assert version.lineage_uuid == "lineage-123"
    assert version.version_number == 1
    assert version.file_size == 1024
    assert version.status == VersionStatus.ACTIVE
    assert version.labels == ["test", "document"]


def test_document_version_model_validation():
    """Test DocumentVersionModel validation rules."""
    # Test invalid file hash
    with pytest.raises(ValueError, match="File hash must be a valid SHA-256 hash"):
        DocumentVersionModel(
            doc_uuid="doc-123",
            lineage_uuid="lineage-123",
            version_number=1,
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_type="pdf",
            file_hash="invalid_hash",  # Invalid hash
            file_size=1024,
            timestamp=datetime.utcnow(),
            user_id="user123"
        )
    
    # Test invalid file size
    with pytest.raises(ValueError, match="File size must be positive"):
        DocumentVersionModel(
            doc_uuid="doc-123",
            lineage_uuid="lineage-123",
            version_number=1,
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_type="pdf",
            file_hash="a" * 64,
            file_size=0,  # Invalid size
            timestamp=datetime.utcnow(),
            user_id="user123"
        )


def test_document_registration_request():
    """Test DocumentRegistrationRequest model."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123",
        labels=["test"],
        metadata={"source": "upload"}
    )
    
    assert request.filename == "test.pdf"
    assert request.file_type == "pdf"
    assert request.file_size == 1024
    assert request.user_id == "user123"
    assert request.labels == ["test"]
    assert request.metadata == {"source": "upload"}


def test_soft_delete_request():
    """Test SoftDeleteRequest model."""
    request = SoftDeleteRequest(
        doc_uuid="doc-123",
        reason=DeletionReason.PRIVACY_REQUEST,
        user_id="user123",
        notes="User requested deletion"
    )
    
    assert request.doc_uuid == "doc-123"
    assert request.reason == DeletionReason.PRIVACY_REQUEST
    assert request.user_id == "user123"
    assert request.notes == "User requested deletion"


# Test Utility Functions

def test_generate_document_uuid():
    """Test document UUID generation."""
    uuid1 = generate_document_uuid()
    uuid2 = generate_document_uuid()
    
    assert uuid1.startswith("doc-")
    assert uuid2.startswith("doc-")
    assert uuid1 != uuid2
    assert len(uuid1) > 10  # Should be reasonably long


def test_generate_lineage_uuid():
    """Test lineage UUID generation."""
    uuid1 = generate_lineage_uuid()
    uuid2 = generate_lineage_uuid()
    
    assert uuid1.startswith("lineage-")
    assert uuid2.startswith("lineage-")
    assert uuid1 != uuid2
    assert len(uuid1) > 15  # Should be reasonably long


def test_calculate_file_hash():
    """Test file hash calculation."""
    content1 = b"test content"
    content2 = b"different content"
    
    hash1 = calculate_file_hash(content1)
    hash2 = calculate_file_hash(content1)  # Same content
    hash3 = calculate_file_hash(content2)  # Different content
    
    assert len(hash1) == 64  # SHA-256 hash length
    assert hash1 == hash2  # Same content should produce same hash
    assert hash1 != hash3  # Different content should produce different hash


def test_validate_file_type():
    """Test file type validation."""
    allowed_types = ["pdf", "docx", "txt"]
    
    assert validate_file_type("document.pdf", allowed_types) is True
    assert validate_file_type("document.PDF", allowed_types) is True  # Case insensitive
    assert validate_file_type("document.docx", allowed_types) is True
    assert validate_file_type("document.jpg", allowed_types) is False
    assert validate_file_type("document", allowed_types) is False  # No extension


# Test Lineage Manager

@pytest.mark.asyncio
async def test_lineage_manager_create_lineage(lineage_manager):
    """Test creating a new document lineage."""
    lineage_uuid = await lineage_manager.create_lineage(
        original_filename="test.pdf",
        created_by="user123",
        metadata={"source": "upload"}
    )
    
    assert lineage_uuid is not None
    assert lineage_uuid.startswith("lineage-")
    
    # Verify lineage was created
    lineage = await lineage_manager.get_lineage(lineage_uuid)
    assert lineage is not None
    assert lineage.original_filename == "test.pdf"
    assert lineage.created_by == "user123"
    assert lineage.current_version == 1
    assert lineage.total_versions == 1
    assert lineage.is_active is True


@pytest.mark.asyncio
async def test_lineage_manager_get_nonexistent_lineage(lineage_manager):
    """Test getting a non-existent lineage."""
    lineage = await lineage_manager.get_lineage("nonexistent-lineage")
    assert lineage is None


@pytest.mark.asyncio
async def test_lineage_manager_update_version_info(lineage_manager):
    """Test updating lineage version information."""
    # Create a lineage first
    lineage_uuid = await lineage_manager.create_lineage(
        original_filename="test.pdf",
        created_by="user123"
    )
    
    # Update version info
    success = await lineage_manager.update_lineage_version_info(
        lineage_uuid,
        current_version=2,
        increment_total=True
    )
    
    assert success is True
    
    # Verify update
    lineage = await lineage_manager.get_lineage(lineage_uuid)
    assert lineage.current_version == 2
    assert lineage.total_versions == 2


@pytest.mark.asyncio
async def test_lineage_manager_soft_delete_lineage(lineage_manager):
    """Test soft deleting a lineage."""
    # Create a lineage first
    lineage_uuid = await lineage_manager.create_lineage(
        original_filename="test.pdf",
        created_by="user123"
    )
    
    # Soft delete the lineage
    success = await lineage_manager.soft_delete_lineage(
        lineage_uuid,
        DeletionReason.PRIVACY_REQUEST,
        "user123",
        force=True
    )
    
    assert success is True
    
    # Verify lineage is marked as inactive
    lineage = await lineage_manager.get_lineage(lineage_uuid)
    assert lineage.is_active is False


# Test Version Manager

@pytest.mark.asyncio
async def test_version_manager_register_version(version_manager, temp_storage_path):
    """Test registering a new document version."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123",
        labels=["test"],
        metadata={"source": "upload"}
    )
    
    file_content = b"test document content"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    assert response.doc_uuid.startswith("doc-")
    assert response.lineage_uuid.startswith("lineage-")
    assert response.version_number == 1
    assert response.is_new_lineage is True
    assert response.is_duplicate is False
    
    # Verify file was saved
    file_path = Path(response.file_path)
    assert file_path.exists()
    
    # Verify content
    with open(file_path, 'rb') as f:
        saved_content = f.read()
    assert saved_content == file_content


@pytest.mark.asyncio
async def test_version_manager_duplicate_detection(version_manager, temp_storage_path):
    """Test duplicate document detection."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    # Register first version
    response1 = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Try to register same content again (should detect duplicate)
    from src.core.exceptions import DocumentVersionError
    with pytest.raises(DocumentVersionError, match="Duplicate document detected"):
        await version_manager.register_version(
            request,
            file_content,  # Same content
            temp_storage_path
        )


@pytest.mark.asyncio
async def test_version_manager_get_version(version_manager, temp_storage_path):
    """Test getting a version by UUID."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    # Register version
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Get version
    version = await version_manager.get_version(response.doc_uuid)
    
    assert version is not None
    assert version.doc_uuid == response.doc_uuid
    assert version.lineage_uuid == response.lineage_uuid
    assert version.filename == "test.pdf"
    assert version.file_type == "pdf"
    assert version.status == VersionStatus.ACTIVE


@pytest.mark.asyncio
async def test_version_manager_soft_delete_version(version_manager, temp_storage_path):
    """Test soft deleting a version."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    # Register version
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Soft delete version
    success = await version_manager.soft_delete_version(
        response.doc_uuid,
        DeletionReason.USER_REQUEST,
        "user123"
    )
    
    assert success is True
    
    # Verify version is marked as deleted
    version = await version_manager.get_version(response.doc_uuid)
    assert version.status == VersionStatus.DELETED
    assert version.deletion_reason == DeletionReason.USER_REQUEST
    assert version.is_current is False


@pytest.mark.asyncio
async def test_version_manager_restore_version(version_manager, temp_storage_path):
    """Test restoring a soft-deleted version."""
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    # Register and delete version
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    await version_manager.soft_delete_version(
        response.doc_uuid,
        DeletionReason.USER_REQUEST,
        "user123"
    )
    
    # Restore version
    success = await version_manager.restore_version(response.doc_uuid, "user123")
    
    assert success is True
    
    # Verify version is restored
    version = await version_manager.get_version(response.doc_uuid)
    assert version.status == VersionStatus.ACTIVE
    assert version.deletion_reason is None


# Test Deletion Manager

@pytest.mark.asyncio
async def test_deletion_manager_soft_delete_version(deletion_manager, version_manager, temp_storage_path):
    """Test deletion manager soft delete functionality."""
    # First create a version
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Create deletion request
    delete_request = SoftDeleteRequest(
        doc_uuid=response.doc_uuid,
        reason=DeletionReason.PRIVACY_REQUEST,
        user_id="user123",
        notes="User privacy request"
    )
    
    # Perform deletion
    delete_response = await deletion_manager.soft_delete_version(delete_request)
    
    assert delete_response.success is True
    assert delete_response.doc_uuid == response.doc_uuid
    assert delete_response.reason == DeletionReason.PRIVACY_REQUEST


@pytest.mark.asyncio
async def test_deletion_manager_get_deleted_versions(deletion_manager, version_manager, temp_storage_path):
    """Test getting list of deleted versions."""
    # Create and delete a version
    request = DocumentRegistrationRequest(
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content = b"test document content"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    await version_manager.soft_delete_version(
        response.doc_uuid,
        DeletionReason.PRIVACY_REQUEST,
        "user123"
    )
    
    # Get deleted versions
    deleted_versions = await deletion_manager.get_deleted_versions(
        user_id="user123",
        reason=DeletionReason.PRIVACY_REQUEST
    )
    
    assert len(deleted_versions) >= 1
    assert any(v['doc_uuid'] == response.doc_uuid for v in deleted_versions)


# Integration Tests

@pytest.mark.asyncio
async def test_version_branching_workflow(version_manager, temp_storage_path):
    """Test complete version branching workflow."""
    # Create initial version
    request = DocumentRegistrationRequest(
        filename="document_v1.pdf",
        file_type="pdf",
        file_size=1024,
        user_id="user123"
    )
    
    file_content_v1 = b"original document content"
    
    response_v1 = await version_manager.register_version(
        request,
        file_content_v1,
        temp_storage_path
    )
    
    # Create version 2
    request_v2 = DocumentRegistrationRequest(
        filename="document_v2.pdf",
        file_type="pdf",
        file_size=2048,
        user_id="user123",
        parent_lineage=response_v1.lineage_uuid
    )
    
    file_content_v2 = b"updated document content"
    
    response_v2 = await version_manager.register_version(
        request_v2,
        file_content_v2,
        temp_storage_path
    )
    
    # Create branch from version 1
    branch_request = VersionBranchRequest(
        lineage_uuid=response_v1.lineage_uuid,
        source_version=1,
        filename="document_branch.pdf",
        file_size=1536,
        user_id="user456",
        labels=["branch", "alternative"]
    )
    
    file_content_branch = b"branched document content"
    
    response_branch = await version_manager.create_version_branch(
        branch_request,
        file_content_branch,
        temp_storage_path
    )
    
    # Verify all versions exist
    assert response_v1.lineage_uuid == response_v2.lineage_uuid == response_branch.lineage_uuid
    assert response_v1.version_number == 1
    assert response_v2.version_number == 2
    assert response_branch.version_number == 3
    
    # Verify branch has correct source
    branch_version = await version_manager.get_version(response_branch.doc_uuid)
    assert branch_version.edit_source_version == 1