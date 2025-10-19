"""Tests for Post Document Register and CRUD operations."""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from src.docforge.storage.post_document_register import PostDocumentRegister
from src.docforge.storage.crud_operations import DocumentCRUD, ProcessingQueueCRUD
from src.docforge.storage.schemas import DocumentMetadata, ProcessingStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def register(temp_db):
    """Create a PostDocumentRegister instance for testing."""
    return PostDocumentRegister(temp_db)


@pytest.fixture
def crud(temp_db):
    """Create a DocumentCRUD instance for testing."""
    return DocumentCRUD(temp_db)


@pytest.fixture
def sample_metadata():
    """Create sample document metadata."""
    return DocumentMetadata(
        title="Test Document",
        author="Test Author",
        file_type="pdf",
        page_count=10,
        word_count=1000,
        language="en",
        custom_metadata={"category": "test", "priority": "high"}
    )


@pytest.fixture
def sample_file_info():
    """Create sample file information."""
    return {
        "filename": "test_document.pdf",
        "size": 1024000,
        "hash": "abc123def456",
        "mime_type": "application/pdf"
    }


class TestPostDocumentRegister:
    """Test the PostDocumentRegister class."""
    
    def test_database_creation(self, temp_db):
        """Test that database and tables are created properly."""
        register = PostDocumentRegister(temp_db)
        
        # Check that database file exists
        assert os.path.exists(temp_db)
        
        # Check that we can get a connection
        conn = register._get_connection()
        assert conn is not None
        conn.close()
    
    def test_register_document(self, register, sample_metadata, sample_file_info):
        """Test document registration."""
        doc_uuid = "doc-123"
        file_uuid = "file-456"
        source_path = "/path/to/source.pdf"
        
        result = register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path=source_path,
            metadata=sample_metadata,
            file_info=sample_file_info
        )
        
        assert result == doc_uuid
        
        # Verify document was stored
        doc = register.get_document(doc_uuid)
        assert doc is not None
        assert doc['doc_uuid'] == doc_uuid
        assert doc['file_uuid'] == file_uuid
        assert doc['source_file_path'] == source_path
        assert doc['title'] == sample_metadata.title
        assert doc['author'] == sample_metadata.author
        assert doc['original_filename'] == sample_file_info['filename']
    
    def test_get_document_not_found(self, register):
        """Test getting a non-existent document."""
        doc = register.get_document("non-existent")
        assert doc is None
    
    def test_update_processing_status(self, register, sample_metadata):
        """Test updating processing status."""
        doc_uuid = "doc-status-test"
        file_uuid = "file-status-test"
        
        # Register document
        register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=sample_metadata
        )
        
        # Update status
        register.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.IN_PROGRESS,
            error_message=None
        )
        
        # Verify status update
        doc = register.get_document(doc_uuid)
        assert doc['processing_status'] == ProcessingStatus.IN_PROGRESS.value
        assert doc['last_processed_at'] is not None
    
    def test_add_processing_version(self, register, sample_metadata):
        """Test adding processing versions."""
        doc_uuid = "doc-version-test"
        file_uuid = "file-version-test"
        set_uuid = "set-123"
        
        # Register document
        register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=sample_metadata
        )
        
        # Add processing version
        version_id = register.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            processing_method="paragraph_chunking",
            processor_version="1.0.0",
            processing_config={"chunk_size": 200},
            processing_duration=1.5,
            chunk_count=25
        )
        
        assert version_id is not None
        
        # Verify version was stored
        versions = register.get_processing_versions(doc_uuid)
        assert len(versions) == 1
        assert versions[0]['set_uuid'] == set_uuid
        assert versions[0]['processing_method'] == "paragraph_chunking"
        assert versions[0]['chunk_count'] == 25
        assert versions[0]['processing_config']['chunk_size'] == 200
    
    def test_update_indexing_status(self, register, sample_metadata):
        """Test updating indexing status."""
        doc_uuid = "doc-index-test"
        file_uuid = "file-index-test"
        
        # Register document
        register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=sample_metadata
        )
        
        # Update indexing status
        register.update_indexing_status(
            doc_uuid=doc_uuid,
            is_indexed=True,
            index_version="v1.0"
        )
        
        # Verify indexing status
        doc = register.get_document(doc_uuid)
        assert doc['is_indexed'] == 1  # SQLite stores boolean as integer
        assert doc['index_version'] == "v1.0"
        assert doc['indexed_at'] is not None
    
    def test_query_documents(self, register, sample_metadata):
        """Test querying documents with filters."""
        # Register multiple documents
        for i in range(5):
            register.register_document(
                doc_uuid=f"doc-{i}",
                file_uuid=f"file-{i}",
                source_file_path=f"/test/path/{i}",
                metadata=sample_metadata
            )
        
        # Query all documents
        all_docs = register.query_documents()
        assert len(all_docs) == 5
        
        # Query with limit
        limited_docs = register.query_documents(limit=3)
        assert len(limited_docs) == 3
        
        # Query with filters
        filtered_docs = register.query_documents(
            filters={'file_type': 'pdf'}
        )
        assert len(filtered_docs) == 5  # All are PDFs
    
    def test_get_processing_statistics(self, register, sample_metadata):
        """Test getting processing statistics."""
        # Register some documents
        for i in range(3):
            register.register_document(
                doc_uuid=f"doc-stats-{i}",
                file_uuid=f"file-stats-{i}",
                source_file_path=f"/test/path/{i}",
                metadata=sample_metadata
            )
        
        stats = register.get_processing_statistics()
        
        assert stats['total_documents'] == 3
        assert stats['indexed_documents'] == 0  # None indexed yet
        assert 'status_distribution' in stats
        assert 'file_type_distribution' in stats
        assert 'language_distribution' in stats
    
    def test_processing_queue(self, register, sample_metadata):
        """Test processing queue operations."""
        doc_uuid = "doc-queue-test"
        file_uuid = "file-queue-test"
        
        # Register document
        register.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=sample_metadata
        )
        
        # Add to queue
        queue_id = register.add_to_processing_queue(
            doc_uuid=doc_uuid,
            requested_methods=["paragraph_chunking", "abbreviation_expansion"],
            requested_config={"chunk_size": 300},
            priority=8
        )
        
        assert queue_id is not None
        
        # Get next queued document
        next_item = register.get_next_queued_document()
        assert next_item is not None
        assert next_item['doc_uuid'] == doc_uuid
        assert next_item['priority'] == 8
        assert "paragraph_chunking" in next_item['requested_methods']
        
        # Update queue status
        register.update_queue_status(queue_id, 'processing')
        
        # Should not get the same item again
        next_item_2 = register.get_next_queued_document()
        assert next_item_2 is None


class TestDocumentCRUD:
    """Test the DocumentCRUD class."""
    
    def test_create_document(self, crud, sample_metadata, sample_file_info):
        """Test creating a document via CRUD interface."""
        doc_uuid = "crud-doc-123"
        file_uuid = "crud-file-456"
        source_path = "/crud/test/path"
        
        result = crud.create_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path=source_path,
            metadata=sample_metadata,
            file_info=sample_file_info
        )
        
        assert result == doc_uuid
        
        # Verify via get
        doc = crud.get_document(doc_uuid)
        assert doc is not None
        assert doc['title'] == sample_metadata.title
    
    def test_list_documents(self, crud, sample_metadata):
        """Test listing documents."""
        # Create multiple documents
        for i in range(3):
            crud.create_document(
                doc_uuid=f"list-doc-{i}",
                file_uuid=f"list-file-{i}",
                source_file_path=f"/list/test/{i}",
                metadata=sample_metadata
            )
        
        # List all
        docs = crud.list_documents()
        assert len(docs) == 3
        
        # List with limit
        limited_docs = crud.list_documents(limit=2)
        assert len(limited_docs) == 2
    
    def test_search_documents(self, crud, sample_metadata):
        """Test searching documents."""
        # Create documents with different titles
        metadata1 = DocumentMetadata(
            title="Python Programming Guide",
            author="Test Author",
            file_type="pdf"
        )
        metadata2 = DocumentMetadata(
            title="JavaScript Tutorial",
            author="Test Author",
            file_type="pdf"
        )
        
        crud.create_document("search-1", "file-1", "/path/1", metadata1)
        crud.create_document("search-2", "file-2", "/path/2", metadata2)
        
        # Search for Python
        results = crud.search_documents("Python")
        assert len(results) == 1
        assert results[0]['title'] == "Python Programming Guide"
        
        # Search for Tutorial
        results = crud.search_documents("Tutorial")
        assert len(results) == 1
        assert results[0]['title'] == "JavaScript Tutorial"
    
    def test_update_processing_status(self, crud, sample_metadata):
        """Test updating processing status via CRUD."""
        doc_uuid = "crud-status-test"
        
        crud.create_document(
            doc_uuid=doc_uuid,
            file_uuid="file-status",
            source_file_path="/status/test",
            metadata=sample_metadata
        )
        
        # Update status
        success = crud.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.COMPLETED
        )
        
        assert success is True
        
        # Verify update
        doc = crud.get_document(doc_uuid)
        assert doc['processing_status'] == ProcessingStatus.COMPLETED.value
    
    def test_get_statistics(self, crud, sample_metadata):
        """Test getting statistics via CRUD."""
        # Create some documents
        for i in range(2):
            crud.create_document(
                doc_uuid=f"stats-doc-{i}",
                file_uuid=f"stats-file-{i}",
                source_file_path=f"/stats/{i}",
                metadata=sample_metadata
            )
        
        stats = crud.get_statistics()
        assert stats['total_documents'] == 2
        assert 'file_type_distribution' in stats
    
    def test_validate_document_integrity(self, crud, sample_metadata):
        """Test document integrity validation."""
        doc_uuid = "integrity-test"
        
        crud.create_document(
            doc_uuid=doc_uuid,
            file_uuid="integrity-file",
            source_file_path="/integrity/test",
            metadata=sample_metadata
        )
        
        # Add a processing version
        crud.create_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="integrity-set",
            processing_method="test_method"
        )
        
        # Validate integrity
        result = crud.validate_document_integrity(doc_uuid)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['version_count'] == 1


class TestProcessingQueueCRUD:
    """Test the ProcessingQueueCRUD class."""
    
    def test_queue_operations(self, temp_db, sample_metadata):
        """Test processing queue CRUD operations."""
        # Create document first
        crud = DocumentCRUD(temp_db)
        queue_crud = ProcessingQueueCRUD(temp_db)
        
        doc_uuid = "queue-crud-test"
        crud.create_document(
            doc_uuid=doc_uuid,
            file_uuid="queue-file",
            source_file_path="/queue/test",
            metadata=sample_metadata
        )
        
        # Add to queue
        queue_id = queue_crud.add_to_queue(
            doc_uuid=doc_uuid,
            requested_methods=["chunking", "expansion"],
            priority=7
        )
        
        assert queue_id is not None
        
        # Get next item
        next_item = queue_crud.get_next_item()
        assert next_item is not None
        assert next_item['doc_uuid'] == doc_uuid
        
        # Update status
        queue_crud.update_status(queue_id, 'processing')
        
        # Should not get same item again
        next_item_2 = queue_crud.get_next_item()
        assert next_item_2 is None


if __name__ == "__main__":
    pytest.main([__file__])