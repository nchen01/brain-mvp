"""Test dummy DBM module."""

import pytest
import tempfile
import os
from pathlib import Path

from src.dbm.connection import DummyDBConnection
from src.dbm.operations import DummyDBOperations


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
def db_connection(temp_db_path):
    """Create a test database connection."""
    return DummyDBConnection(temp_db_path)


@pytest.fixture
def db_operations(db_connection):
    """Create test database operations."""
    # Override the global connection for testing
    from src.dbm import connection, operations
    original_connection = connection._db_connection
    original_operations = operations._db_operations
    
    # Set test connection
    connection._db_connection = db_connection
    operations._db_operations = None  # Reset to create new instance
    
    ops = DummyDBOperations()
    yield ops
    
    # Restore original instances
    connection._db_connection = original_connection
    operations._db_operations = original_operations


def test_db_connection_creation(temp_db_path):
    """Test database connection creation."""
    db = DummyDBConnection(temp_db_path)
    assert db.db_path == temp_db_path
    assert db._connection is not None
    
    # Test that database file was created
    assert Path(temp_db_path).exists()


def test_db_tables_creation(db_connection):
    """Test that all required tables are created."""
    conn = db_connection.get_connection()
    cursor = conn.cursor()
    
    # Check that tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        "document_lineage",
        "raw_document_register",
        "post_document_register",
        "meta_document_register",
        "users",
        "sessions"
    ]
    
    for table in expected_tables:
        assert table in tables


def test_db_operations_insert(db_operations):
    """Test database insert operation."""
    test_data = {
        "lineage_uuid": "test-lineage-123",
        "original_filename": "test.pdf",
        "created_by": "user123",
        "current_version": 1,
        "total_versions": 1,
        "is_active": True
    }
    
    result = db_operations.insert("document_lineage", test_data)
    assert result is True


def test_db_operations_select(db_operations):
    """Test database select operation."""
    # First insert test data
    test_data = {
        "lineage_uuid": "test-lineage-456",
        "original_filename": "test2.pdf",
        "created_by": "user456",
        "current_version": 1,
        "total_versions": 1,
        "is_active": True
    }
    
    db_operations.insert("document_lineage", test_data)
    
    # Now select it
    results = db_operations.select(
        "document_lineage",
        "lineage_uuid = ?",
        ("test-lineage-456",)
    )
    
    assert len(results) == 1
    assert results[0]["lineage_uuid"] == "test-lineage-456"
    assert results[0]["original_filename"] == "test2.pdf"


def test_db_operations_update(db_operations):
    """Test database update operation."""
    # Insert test data
    test_data = {
        "lineage_uuid": "test-lineage-789",
        "original_filename": "test3.pdf",
        "created_by": "user789",
        "current_version": 1,
        "total_versions": 1,
        "is_active": True
    }
    
    db_operations.insert("document_lineage", test_data)
    
    # Update it
    update_data = {"current_version": 2, "total_versions": 2}
    result = db_operations.update(
        "document_lineage",
        update_data,
        "lineage_uuid = ?",
        ("test-lineage-789",)
    )
    
    assert result is True
    
    # Verify update
    results = db_operations.select(
        "document_lineage",
        "lineage_uuid = ?",
        ("test-lineage-789",)
    )
    
    assert results[0]["current_version"] == 2
    assert results[0]["total_versions"] == 2


def test_db_operations_soft_delete(db_operations):
    """Test soft delete operation."""
    # First insert lineage data (required for foreign key)
    lineage_data = {
        "lineage_uuid": "test-lineage-123",
        "original_filename": "test.pdf",
        "created_by": "user123",
        "current_version": 1,
        "total_versions": 1,
        "is_active": True
    }
    db_operations.insert("document_lineage", lineage_data)
    
    # Insert test data into raw_document_register with new schema
    test_data = {
        "doc_uuid": "test-doc-123",
        "lineage_uuid": "test-lineage-123",
        "version_number": 1,
        "filename": "test.pdf",
        "file_path": "/path/to/test.pdf",
        "file_type": "pdf",
        "file_hash": "abc123",
        "file_size": 1024,
        "user_id": "user123",
        "labels": ["test"],
        "is_current": True,
        "status": "active",
        "metadata": {}
    }
    
    db_operations.insert("raw_document_register", test_data)
    
    # Soft delete
    result = db_operations.soft_delete(
        "raw_document_register",
        "doc_uuid",
        "test-doc-123",
        "privacy_request"
    )
    
    assert result is True
    
    # Verify soft delete
    results = db_operations.select(
        "raw_document_register",
        "doc_uuid = ?",
        ("test-doc-123",)
    )
    
    assert len(results) == 1
    assert results[0]["status"] == "deleted"
    assert results[0]["deletion_reason"] == "privacy_request"
    assert results[0]["is_current"] == 0  # Should be set to False


def test_db_operations_count(db_operations):
    """Test count operation."""
    # Insert multiple test records
    for i in range(3):
        test_data = {
            "lineage_uuid": f"test-lineage-count-{i}",
            "original_filename": f"test{i}.pdf",
            "created_by": "user_count",
            "current_version": 1,
            "total_versions": 1,
            "is_active": True
        }
        db_operations.insert("document_lineage", test_data)
    
    # Count all records
    total_count = db_operations.count("document_lineage")
    assert total_count >= 3
    
    # Count specific records
    specific_count = db_operations.count(
        "document_lineage",
        "created_by = ?",
        ("user_count",)
    )
    assert specific_count == 3