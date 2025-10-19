"""Test raw document storage operations."""

import pytest
import tempfile
import os
from pathlib import Path

from src.dbm.connection import DummyDBConnection
from src.docforge.versioning.storage import RawDocumentStorage
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
def storage_service(test_db_setup, temp_storage_path):
    """Create test storage service."""
    return RawDocumentStorage(temp_storage_path)


@pytest.fixture
def version_manager(test_db_setup):
    """Create test version manager."""
    return VersionManager()


@pytest.mark.asyncio
async def test_store_and_retrieve_document(storage_service, version_manager, temp_storage_path):
    """Test storing and retrieving a document."""
    # Register a document first
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Hello World!"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Retrieve the document
    retrieved_content = await storage_service.retrieve_document_file(response.doc_uuid)
    
    assert retrieved_content == file_content


@pytest.mark.asyncio
async def test_retrieve_by_lineage_version(storage_service, version_manager, temp_storage_path):
    """Test retrieving document by lineage and version number."""
    # Register a document
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Hello World!"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Retrieve by lineage and version
    retrieved_content = await storage_service.retrieve_document_by_lineage_version(
        response.lineage_uuid,
        response.version_number
    )
    
    assert retrieved_content == file_content


@pytest.mark.asyncio
async def test_get_document_versions_with_content(storage_service, version_manager, temp_storage_path):
    """Test getting document versions with content availability."""
    # Register a document
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Hello World!"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Get versions with content info
    versions_info = await storage_service.get_document_versions_with_content(
        response.lineage_uuid
    )
    
    assert len(versions_info) == 1
    assert versions_info[0]["doc_uuid"] == response.doc_uuid
    assert versions_info[0]["content_available"] is True
    assert versions_info[0]["file_size"] == 12
    assert versions_info[0]["file_size_on_disk"] == 12


@pytest.mark.asyncio
async def test_verify_storage_integrity(storage_service, version_manager, temp_storage_path):
    """Test storage integrity verification."""
    # Register a document
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Hello World!"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Verify integrity
    integrity_report = await storage_service.verify_storage_integrity(
        response.lineage_uuid
    )
    
    assert integrity_report["total_checked"] == 1
    assert integrity_report["valid_files"] == 1
    assert integrity_report["files_missing"] == 0
    assert integrity_report["hash_mismatches"] == 0
    assert len(integrity_report["issues"]) == 0


@pytest.mark.asyncio
async def test_storage_statistics(storage_service, version_manager, temp_storage_path):
    """Test getting storage statistics."""
    # Register a few documents
    for i in range(3):
        request = DocumentRegistrationRequest(
            filename=f"test{i}.txt",
            file_type="txt",
            file_size=10 + i,
            user_id="user123"
        )
        
        file_content = f"Content {i}".encode()
        
        await version_manager.register_version(
            request,
            file_content,
            temp_storage_path
        )
    
    # Get statistics
    stats = await storage_service.get_storage_statistics()
    
    assert stats["total_files"] == 3
    assert stats["active_files"] == 3
    assert stats["deleted_files"] == 0
    assert stats["lineage_count"] == 3
    assert "txt" in stats["file_types"]
    assert stats["file_types"]["txt"]["count"] == 3


@pytest.mark.asyncio
async def test_temporary_storage(storage_service):
    """Test temporary storage creation and cleanup."""
    file_content = b"Temporary content"
    filename = "temp.txt"
    
    # Create temporary storage
    temp_path = await storage_service.create_temporary_storage(
        file_content,
        filename,
        "test-temp-id"
    )
    
    # Verify file exists
    assert Path(temp_path).exists()
    
    # Verify content
    with open(temp_path, 'rb') as f:
        stored_content = f.read()
    assert stored_content == file_content
    
    # Clean up temporary storage
    cleanup_stats = await storage_service.cleanup_temporary_storage("test-temp-id")
    
    assert cleanup_stats["cleaned"] == 1
    assert len(cleanup_stats["errors"]) == 0


@pytest.mark.asyncio
async def test_cleanup_deleted_files(storage_service, version_manager, temp_storage_path):
    """Test cleanup of deleted document files."""
    # Register a document
    request = DocumentRegistrationRequest(
        filename="test.txt",
        file_type="txt",
        file_size=12,
        user_id="user123"
    )
    
    file_content = b"Hello World!"
    
    response = await version_manager.register_version(
        request,
        file_content,
        temp_storage_path
    )
    
    # Soft delete the document
    await version_manager.soft_delete_version(
        response.doc_uuid,
        DeletionReason.USER_REQUEST,
        "user123"
    )
    
    # Test dry run cleanup
    cleanup_stats = await storage_service.cleanup_deleted_files(dry_run=True)
    
    assert cleanup_stats["files_found"] == 1
    assert cleanup_stats["files_deleted"] == 0
    assert cleanup_stats["space_freed"] == 12
    assert cleanup_stats["dry_run"] is True
    
    # Test actual cleanup
    cleanup_stats = await storage_service.cleanup_deleted_files(dry_run=False)
    
    assert cleanup_stats["files_found"] == 1
    assert cleanup_stats["files_deleted"] == 1
    assert cleanup_stats["space_freed"] == 12
    assert cleanup_stats["dry_run"] is False
    
    # Verify file is gone
    file_path = Path(response.file_path)
    assert not file_path.exists()