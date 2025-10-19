"""Tests for Post Document Database."""

import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

from src.docforge.storage import (
    PostDocumentDatabase,
    PostDocumentRecord,
    ProcessingVersionRecord,
    ChunkStorageRecord,
    DocumentMetadata,
    StorageConfig,
    QueryFilter,
    StorageStats,
    ProcessingStatus
)
from src.docforge.postprocessing.schemas import (
    ChunkData,
    ChunkMetadata,
    ChunkType
)


class TestPostDocumentDatabase:
    """Test the Post Document Database."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_post_docs.db")
        
        self.config = StorageConfig(
            database_url=f"sqlite:///{self.db_path}",
            max_connections=5,
            connection_timeout=10,
            enable_compression=True,
            enable_encryption=False
        )
        
        self.db = PostDocumentDatabase(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_chunks(self, count: int = 3, prefix: str = "chunk") -> List[ChunkData]:
        """Create test chunks for testing."""
        chunks = []
        for i in range(count):
            chunk_id = f"{prefix}_{i}"
            chunk = ChunkData(
                chunk_id=chunk_id,
                content=f"This is test chunk {i} with some content for testing.",
                chunk_type=ChunkType.PARAGRAPH,
                metadata=ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=i,
                    chunk_type=ChunkType.PARAGRAPH,
                    source_elements=[f"element_{i}"],
                    page_numbers=[1],
                    word_count=10 + i,
                    character_count=50 + i * 5,
                    language="en",
                    confidence_score=0.9 + i * 0.01
                ),
                position={"page": 1, "section": f"section_{i}"},
                relationships={"previous": [f"{prefix}_{i-1}"] if i > 0 else []}
            )
            chunks.append(chunk)
        return chunks
    
    def test_database_initialization(self):
        """Test database initialization."""
        # Database should be created
        assert os.path.exists(self.db_path)
        
        # Tables should exist
        with self.db._get_connection() as conn:
            tables = conn.execute('''
                SELECT name FROM sqlite_master WHERE type='table'
            ''').fetchall()
            
            table_names = [table['name'] for table in tables]
            assert 'documents' in table_names
            assert 'processing_versions' in table_names
            assert 'chunks' in table_names
    
    def test_store_document(self):
        """Test storing a document."""
        metadata = DocumentMetadata(
            title="Test Document",
            author="Test Author",
            file_type="pdf",
            page_count=5,
            word_count=1000,
            tags=["test", "document"]
        )
        
        doc_uuid = self.db.store_document(
            file_uuid="file_123",
            source_file_path="/path/to/test.pdf",
            source_content="Test document content",
            metadata=metadata
        )
        
        assert doc_uuid is not None
        assert len(doc_uuid) > 0
        
        # Verify document was stored
        stored_doc = self.db.get_document(doc_uuid)
        assert stored_doc is not None
        assert stored_doc.file_uuid == "file_123"
        assert stored_doc.source_file_path == "/path/to/test.pdf"
        assert stored_doc.metadata.title == "Test Document"
        assert stored_doc.metadata.author == "Test Author"
        assert "test" in stored_doc.metadata.tags
    
    def test_add_processing_version(self):
        """Test adding processing versions to a document."""
        # First store a document
        doc_uuid = self.db.store_document(
            file_uuid="file_456",
            source_file_path="/path/to/test2.pdf",
            source_content="Another test document"
        )
        
        # Create test chunks
        chunks = self.create_test_chunks(3)
        
        # Add processing version
        version_id = self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_789",
            processing_method="paragraph_chunking",
            processing_config={"chunk_size": 150, "overlap": 20},
            processor_version="1.0.0",
            processing_duration=2.5,
            chunks=chunks,
            status=ProcessingStatus.COMPLETED
        )
        
        assert version_id is not None
        
        # Verify processing version was added
        stored_doc = self.db.get_document(doc_uuid)
        assert len(stored_doc.processing_versions) == 1
        
        version = stored_doc.processing_versions[0]
        assert version.set_uuid == "set_789"
        assert version.processing_method == "paragraph_chunking"
        assert version.chunk_count == 3
        assert version.status == ProcessingStatus.COMPLETED
        
        # Verify chunks were stored
        stored_chunks = self.db.get_chunks(doc_uuid, "set_789")
        assert len(stored_chunks) == 3
        
        for i, chunk in enumerate(stored_chunks):
            assert chunk.chunk_id == f"chunk_{i}"
            assert chunk.chunk_index == i
            assert chunk.word_count == 10 + i
    
    def test_multiple_processing_versions(self):
        """Test storing multiple processing versions for the same document."""
        # Store document
        doc_uuid = self.db.store_document(
            file_uuid="file_multi",
            source_file_path="/path/to/multi.pdf",
            source_content="Multi-version test document"
        )
        
        # Add first processing version
        chunks1 = self.create_test_chunks(2, "v1_chunk")
        version1_id = self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_v1",
            processing_method="paragraph_chunking",
            processing_config={"chunk_size": 100},
            processor_version="1.0.0",
            processing_duration=1.5,
            chunks=chunks1
        )
        
        # Add second processing version
        chunks2 = self.create_test_chunks(4, "v2_chunk")
        version2_id = self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_v2",
            processing_method="semantic_chunking",
            processing_config={"chunk_size": 200},
            processor_version="1.1.0",
            processing_duration=3.0,
            chunks=chunks2
        )
        
        # Verify both versions exist
        stored_doc = self.db.get_document(doc_uuid)
        assert len(stored_doc.processing_versions) == 2
        
        # Verify chunks for each version
        chunks_v1 = self.db.get_chunks(doc_uuid, "set_v1")
        chunks_v2 = self.db.get_chunks(doc_uuid, "set_v2")
        
        assert len(chunks_v1) == 2
        assert len(chunks_v2) == 4
        
        # Verify version-specific data
        version1 = stored_doc.get_version_by_set_uuid("set_v1")
        version2 = stored_doc.get_version_by_set_uuid("set_v2")
        
        assert version1.processing_method == "paragraph_chunking"
        assert version2.processing_method == "semantic_chunking"
        assert version1.chunk_count == 2
        assert version2.chunk_count == 4
    
    def test_query_documents(self):
        """Test querying documents with filters."""
        # Store multiple documents
        doc1_uuid = self.db.store_document(
            file_uuid="file_query1",
            source_file_path="/path/to/query1.pdf",
            source_content="Query test document 1",
            metadata=DocumentMetadata(title="Query Doc 1", tags=["query", "test"])
        )
        
        doc2_uuid = self.db.store_document(
            file_uuid="file_query2",
            source_file_path="/path/to/query2.pdf",
            source_content="Query test document 2",
            metadata=DocumentMetadata(title="Query Doc 2", tags=["query", "example"])
        )
        
        # Query by doc UUIDs
        filter1 = QueryFilter(doc_uuids=[doc1_uuid])
        results1 = self.db.query_documents(filter1)
        assert len(results1) == 1
        assert results1[0].doc_uuid == doc1_uuid
        
        # Query by file UUIDs
        filter2 = QueryFilter(file_uuids=["file_query1", "file_query2"])
        results2 = self.db.query_documents(filter2)
        assert len(results2) == 2
        
        # Query by date range
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        filter3 = QueryFilter(date_range={"start": yesterday, "end": tomorrow})
        results3 = self.db.query_documents(filter3)
        assert len(results3) == 2  # Both documents should be in range
    
    def test_storage_stats(self):
        """Test getting storage statistics."""
        # Initially empty
        stats = self.db.get_storage_stats()
        assert stats.total_documents == 0
        assert stats.total_processing_versions == 0
        assert stats.total_chunks == 0
        
        # Add some data
        doc_uuid = self.db.store_document(
            file_uuid="file_stats",
            source_file_path="/path/to/stats.pdf",
            source_content="Stats test document"
        )
        
        chunks = self.create_test_chunks(5)
        self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_stats",
            processing_method="test_method",
            processing_config={},
            processor_version="1.0.0",
            processing_duration=1.0,
            chunks=chunks
        )
        
        # Check updated stats
        stats = self.db.get_storage_stats()
        assert stats.total_documents == 1
        assert stats.total_processing_versions == 1
        assert stats.total_chunks == 5
        assert stats.method_counts["test_method"] == 1
        assert stats.status_counts["completed"] == 1
        assert stats.average_chunk_count == 5.0
    
    def test_delete_document(self):
        """Test deleting a document and its associated data."""
        # Store document with processing version
        doc_uuid = self.db.store_document(
            file_uuid="file_delete",
            source_file_path="/path/to/delete.pdf",
            source_content="Delete test document"
        )
        
        chunks = self.create_test_chunks(2)
        self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_delete",
            processing_method="delete_test",
            processing_config={},
            processor_version="1.0.0",
            processing_duration=1.0,
            chunks=chunks
        )
        
        # Verify document exists
        assert self.db.get_document(doc_uuid) is not None
        
        # Delete document
        deleted = self.db.delete_document(doc_uuid)
        assert deleted is True
        
        # Verify document is gone
        assert self.db.get_document(doc_uuid) is None
        
        # Verify chunks are also gone
        chunks_after_delete = self.db.get_chunks(doc_uuid)
        assert len(chunks_after_delete) == 0
    
    def test_update_vector_references(self):
        """Test updating vector storage references."""
        # Store document with processing version
        doc_uuid = self.db.store_document(
            file_uuid="file_vector",
            source_file_path="/path/to/vector.pdf",
            source_content="Vector test document"
        )
        
        chunks = self.create_test_chunks(1)
        version_id = self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_vector",
            processing_method="vector_test",
            processing_config={},
            processor_version="1.0.0",
            processing_duration=1.0,
            chunks=chunks
        )
        
        # Update vector references
        self.db.update_vector_references(
            version_id=version_id,
            vector_index_id="vector_index_123",
            embeddings_path="/path/to/embeddings.bin"
        )
        
        # Verify references were updated
        stored_doc = self.db.get_document(doc_uuid)
        version = stored_doc.processing_versions[0]
        assert version.vector_index_id == "vector_index_123"
        assert version.embeddings_storage_path == "/path/to/embeddings.bin"
    
    def test_error_handling(self):
        """Test error handling for invalid operations."""
        # Test getting non-existent document
        non_existent = self.db.get_document("non_existent_uuid")
        assert non_existent is None
        
        # Test deleting non-existent document
        deleted = self.db.delete_document("non_existent_uuid")
        assert deleted is False
        
        # Test getting chunks for non-existent document
        chunks = self.db.get_chunks("non_existent_uuid")
        assert len(chunks) == 0
    
    def test_document_relationships(self):
        """Test document parent-child relationships."""
        # Store parent document
        parent_uuid = self.db.store_document(
            file_uuid="file_parent",
            source_file_path="/path/to/parent.pdf",
            source_content="Parent document"
        )
        
        # Store child document
        child_uuid = self.db.store_document(
            file_uuid="file_child",
            source_file_path="/path/to/child.pdf",
            source_content="Child document"
        )
        
        # Update relationships (would need to add this method to the database)
        # For now, just verify the structure supports it
        parent_doc = self.db.get_document(parent_uuid)
        assert parent_doc.child_doc_uuids == []
        assert parent_doc.related_doc_uuids == []
        assert parent_doc.parent_doc_uuid is None
    
    def test_chunk_content_hashing(self):
        """Test that chunk content is properly hashed."""
        doc_uuid = self.db.store_document(
            file_uuid="file_hash",
            source_file_path="/path/to/hash.pdf",
            source_content="Hash test document"
        )
        
        chunks = self.create_test_chunks(2)
        self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_hash",
            processing_method="hash_test",
            processing_config={},
            processor_version="1.0.0",
            processing_duration=1.0,
            chunks=chunks
        )
        
        stored_chunks = self.db.get_chunks(doc_uuid)
        
        for chunk in stored_chunks:
            # Verify hash exists and is not empty
            assert chunk.content_hash is not None
            assert len(chunk.content_hash) > 0
            
            # Verify hash is consistent
            expected_hash = self.db._calculate_hash(chunk.content)
            assert chunk.content_hash == expected_hash
    
    def test_processing_status_handling(self):
        """Test handling of different processing statuses."""
        doc_uuid = self.db.store_document(
            file_uuid="file_status",
            source_file_path="/path/to/status.pdf",
            source_content="Status test document"
        )
        
        # Test failed processing
        chunks = self.create_test_chunks(1)
        version_id = self.db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid="set_failed",
            processing_method="status_test",
            processing_config={},
            processor_version="1.0.0",
            processing_duration=0.5,
            chunks=chunks,
            status=ProcessingStatus.FAILED,
            error_message="Test error message",
            warnings=["Test warning 1", "Test warning 2"]
        )
        
        stored_doc = self.db.get_document(doc_uuid)
        version = stored_doc.processing_versions[0]
        
        assert version.status == ProcessingStatus.FAILED
        assert version.error_message == "Test error message"
        assert len(version.warnings) == 2
        assert "Test warning 1" in version.warnings
    
    def test_configuration_options(self):
        """Test different configuration options."""
        # Test with compression disabled
        config_no_compression = StorageConfig(
            database_url=f"sqlite:///{self.temp_dir}/no_compression.db",
            enable_compression=False
        )
        
        db_no_compression = PostDocumentDatabase(config_no_compression)
        
        # Should still work without compression
        doc_uuid = db_no_compression.store_document(
            file_uuid="file_no_compress",
            source_file_path="/path/to/no_compress.pdf",
            source_content="No compression test"
        )
        
        stored_doc = db_no_compression.get_document(doc_uuid)
        assert stored_doc is not None
        assert stored_doc.file_uuid == "file_no_compress"


class TestStorageSchemas:
    """Test storage schema models."""
    
    def test_document_metadata_creation(self):
        """Test creating document metadata."""
        metadata = DocumentMetadata(
            title="Test Document",
            author="Test Author",
            file_type="pdf",
            page_count=10,
            word_count=5000,
            tags=["test", "document", "pdf"],
            custom_metadata={"department": "engineering", "project": "test"}
        )
        
        assert metadata.title == "Test Document"
        assert metadata.author == "Test Author"
        assert metadata.page_count == 10
        assert len(metadata.tags) == 3
        assert metadata.custom_metadata["department"] == "engineering"
    
    def test_processing_version_record(self):
        """Test processing version record creation."""
        version = ProcessingVersionRecord(
            set_uuid="set_123",
            processing_method="test_method",
            processing_config={"param1": "value1"},
            processor_version="1.0.0",
            processing_duration=2.5,
            chunk_count=5
        )
        
        assert version.set_uuid == "set_123"
        assert version.processing_method == "test_method"
        assert version.chunk_count == 5
        assert version.status == ProcessingStatus.PENDING  # Default
        assert len(version.version_id) > 0  # UUID generated
    
    def test_post_document_record_methods(self):
        """Test PostDocumentRecord helper methods."""
        doc = PostDocumentRecord(
            file_uuid="file_123",
            source_file_path="/path/to/file.pdf",
            source_file_hash="hash123"
        )
        
        # Test adding processing versions
        version1 = ProcessingVersionRecord(
            set_uuid="set_1",
            processing_method="method1",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        version2 = ProcessingVersionRecord(
            set_uuid="set_2",
            processing_method="method2",
            processor_version="1.1.0",
            processing_duration=2.0
        )
        
        doc.add_processing_version(version1)
        doc.add_processing_version(version2)
        
        assert len(doc.processing_versions) == 2
        
        # Test getting latest version
        latest = doc.get_latest_version()
        assert latest.set_uuid == "set_2"  # More recent
        
        # Test getting version by set UUID
        found_version = doc.get_version_by_set_uuid("set_1")
        assert found_version.set_uuid == "set_1"
        
        # Test getting successful versions
        version1.status = ProcessingStatus.COMPLETED
        version2.status = ProcessingStatus.FAILED
        
        successful = doc.get_successful_versions()
        assert len(successful) == 1
        assert successful[0].set_uuid == "set_1"
    
    def test_query_filter(self):
        """Test query filter creation."""
        filter_obj = QueryFilter(
            doc_uuids=["doc1", "doc2"],
            file_uuids=["file1", "file2"],
            processing_methods=["method1", "method2"],
            status=[ProcessingStatus.COMPLETED, ProcessingStatus.FAILED],
            date_range={
                "start": datetime.now(timezone.utc) - timedelta(days=7),
                "end": datetime.now(timezone.utc)
            },
            tags=["tag1", "tag2"]
        )
        
        assert len(filter_obj.doc_uuids) == 2
        assert len(filter_obj.status) == 2
        assert "start" in filter_obj.date_range
        assert "end" in filter_obj.date_range
    
    def test_storage_config_validation(self):
        """Test storage configuration validation."""
        config = StorageConfig(
            database_url="sqlite:///test.db",
            max_connections=20,
            connection_timeout=60,
            enable_compression=True,
            enable_encryption=True,
            retention_days=30
        )
        
        assert config.database_url == "sqlite:///test.db"
        assert config.max_connections == 20
        assert config.enable_compression is True
        assert config.retention_days == 30