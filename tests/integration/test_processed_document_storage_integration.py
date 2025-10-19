"""Integration tests for processed document storage system."""

import pytest
import tempfile
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

from src.docforge.storage.post_document_register import PostDocumentRegister
from src.docforge.storage.post_document_db import PostDocumentDatabase
from src.docforge.storage.crud_operations import DocumentCRUD, ProcessingQueueCRUD
from src.docforge.storage.schemas import (
    DocumentMetadata,
    ProcessingStatus,
    StorageConfig,
    PostDocumentRecord,
    ProcessingVersionRecord,
    ChunkStorageRecord
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def storage_config(temp_storage_dir):
    """Create storage configuration for testing."""
    return StorageConfig(
        database_url=f"sqlite:///{temp_storage_dir}/test_storage.db",
        max_connections=5,
        connection_timeout=10,
        enable_compression=True,
        enable_encryption=False,
        retention_days=30
    )


@pytest.fixture
def register_db(temp_storage_dir):
    """Create PostDocumentRegister for testing."""
    db_path = os.path.join(temp_storage_dir, "register.db")
    return PostDocumentRegister(db_path)


@pytest.fixture
def document_db(storage_config):
    """Create PostDocumentDatabase for testing."""
    return PostDocumentDatabase(storage_config)


@pytest.fixture
def crud_interface(temp_storage_dir):
    """Create DocumentCRUD interface for testing."""
    db_path = os.path.join(temp_storage_dir, "crud.db")
    return DocumentCRUD(db_path)


@pytest.fixture
def sample_documents():
    """Create sample document data for testing."""
    return [
        {
            "doc_uuid": str(uuid.uuid4()),
            "file_uuid": str(uuid.uuid4()),
            "source_path": "/test/documents/doc1.pdf",
            "metadata": DocumentMetadata(
                title="Research Paper on AI",
                author="Dr. Smith",
                file_type="pdf",
                page_count=15,
                word_count=5000,
                language="en",
                custom_metadata={"category": "research", "department": "AI"}
            ),
            "processing_versions": [
                {
                    "set_uuid": str(uuid.uuid4()),
                    "method": "paragraph_chunking",
                    "config": {"chunk_size": 200, "overlap": 50}
                },
                {
                    "set_uuid": str(uuid.uuid4()),
                    "method": "section_chunking",
                    "config": {"chunk_size": 500, "overlap": 100}
                }
            ]
        },
        {
            "doc_uuid": str(uuid.uuid4()),
            "file_uuid": str(uuid.uuid4()),
            "source_path": "/test/documents/doc2.docx",
            "metadata": DocumentMetadata(
                title="Technical Manual",
                author="Engineering Team",
                file_type="docx",
                page_count=25,
                word_count=8000,
                language="en",
                custom_metadata={"category": "manual", "version": "2.1"}
            ),
            "processing_versions": [
                {
                    "set_uuid": str(uuid.uuid4()),
                    "method": "semantic_chunking",
                    "config": {"chunk_size": 300, "semantic_threshold": 0.8}
                }
            ]
        }
    ]


class TestDocumentStorageIntegration:
    """Integration tests for document storage system."""
    
    def test_complete_document_lifecycle(self, register_db, sample_documents):
        """Test complete document lifecycle from registration to processing."""
        doc_data = sample_documents[0]
        
        # 1. Register document
        doc_uuid = register_db.register_document(
            doc_uuid=doc_data["doc_uuid"],
            file_uuid=doc_data["file_uuid"],
            source_file_path=doc_data["source_path"],
            metadata=doc_data["metadata"]
        )
        
        assert doc_uuid == doc_data["doc_uuid"]
        
        # 2. Verify document registration
        stored_doc = register_db.get_document(doc_uuid)
        assert stored_doc is not None
        assert stored_doc["title"] == doc_data["metadata"].title
        assert stored_doc["author"] == doc_data["metadata"].author
        assert stored_doc["file_uuid"] == doc_data["file_uuid"]
        
        # 3. Add processing versions
        version_ids = []
        for version_data in doc_data["processing_versions"]:
            version_id = register_db.add_processing_version(
                doc_uuid=doc_uuid,
                set_uuid=version_data["set_uuid"],
                processing_method=version_data["method"],
                processor_version="1.0.0",
                processing_config=version_data["config"],
                processing_duration=2.5,
                chunk_count=20,
                status=ProcessingStatus.COMPLETED
            )
            version_ids.append(version_id)
        
        # 4. Verify processing versions
        versions = register_db.get_processing_versions(doc_uuid)
        assert len(versions) == 2
        
        # Check first version
        version1 = next(v for v in versions if v["processing_method"] == "paragraph_chunking")
        assert version1["set_uuid"] == doc_data["processing_versions"][0]["set_uuid"]
        assert version1["processing_config"]["chunk_size"] == 200
        assert version1["chunk_count"] == 20
        
        # Check second version
        version2 = next(v for v in versions if v["processing_method"] == "section_chunking")
        assert version2["set_uuid"] == doc_data["processing_versions"][1]["set_uuid"]
        assert version2["processing_config"]["chunk_size"] == 500
        
        # 5. Update processing status
        register_db.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.COMPLETED
        )
        
        # 6. Verify status update
        updated_doc = register_db.get_document(doc_uuid)
        assert updated_doc["processing_status"] == ProcessingStatus.COMPLETED.value
        assert updated_doc["last_processed_at"] is not None
        
        # 7. Update indexing status
        register_db.update_indexing_status(
            doc_uuid=doc_uuid,
            is_indexed=True,
            index_version="v1.0"
        )
        
        # 8. Verify indexing update
        indexed_doc = register_db.get_document(doc_uuid)
        assert indexed_doc["is_indexed"] == 1  # SQLite boolean as integer
        assert indexed_doc["index_version"] == "v1.0"
        assert indexed_doc["indexed_at"] is not None
    
    def test_multiple_documents_with_relationships(self, register_db, sample_documents):
        """Test storing multiple documents and their relationships."""
        doc_uuids = []
        
        # Register all documents
        for doc_data in sample_documents:
            doc_uuid = register_db.register_document(
                doc_uuid=doc_data["doc_uuid"],
                file_uuid=doc_data["file_uuid"],
                source_file_path=doc_data["source_path"],
                metadata=doc_data["metadata"]
            )
            doc_uuids.append(doc_uuid)
        
        # Verify all documents are stored
        assert len(doc_uuids) == 2
        
        # Check document retrieval by file UUID
        doc1_by_file = register_db.get_documents_by_file_uuid(sample_documents[0]["file_uuid"])
        assert len(doc1_by_file) == 1
        assert doc1_by_file[0]["doc_uuid"] == sample_documents[0]["doc_uuid"]
        
        # Check relationships
        relationships = register_db.get_document_relationships(doc_uuids[0])
        assert len(relationships) >= 1  # Should have at least the processed_from relationship
        
        # Verify relationship data
        processed_from_rel = next(
            (r for r in relationships if r["relationship_type"] == "processed_from"), 
            None
        )
        assert processed_from_rel is not None
        assert processed_from_rel["parent_file_uuid"] == sample_documents[0]["file_uuid"]
        assert processed_from_rel["child_doc_uuid"] == sample_documents[0]["doc_uuid"]
    
    def test_uuid_relationship_integrity(self, register_db, sample_documents):
        """Test UUID relationship integrity across the system."""
        doc_data = sample_documents[0]
        
        # Register document
        doc_uuid = register_db.register_document(
            doc_uuid=doc_data["doc_uuid"],
            file_uuid=doc_data["file_uuid"],
            source_file_path=doc_data["source_path"],
            metadata=doc_data["metadata"]
        )
        
        # Add processing versions with different setUUIDs
        set_uuids = []
        for version_data in doc_data["processing_versions"]:
            version_id = register_db.add_processing_version(
                doc_uuid=doc_uuid,
                set_uuid=version_data["set_uuid"],
                processing_method=version_data["method"],
                processor_version="1.0.0",
                processing_config=version_data["config"]
            )
            set_uuids.append(version_data["set_uuid"])
        
        # Verify UUID relationships
        # 1. fileUUID -> docUUID relationship
        docs_from_file = register_db.get_documents_by_file_uuid(doc_data["file_uuid"])
        assert len(docs_from_file) == 1
        assert docs_from_file[0]["doc_uuid"] == doc_uuid
        
        # 2. docUUID -> setUUID relationships
        versions = register_db.get_processing_versions(doc_uuid)
        stored_set_uuids = [v["set_uuid"] for v in versions]
        assert set(stored_set_uuids) == set(set_uuids)
        
        # 3. Verify each setUUID is unique and properly linked
        for version in versions:
            assert version["doc_uuid"] == doc_uuid
            assert version["set_uuid"] in set_uuids
        
        # 4. Test vector reference updates
        for version in versions:
            vector_index_id = f"vector_index_{version['set_uuid'][:8]}"
            embeddings_path = f"/vectors/{version['set_uuid']}.npy"
            
            register_db.update_vector_references(
                version_id=version["version_id"],
                vector_index_id=vector_index_id,
                embeddings_path=embeddings_path
            )
        
        # 5. Verify vector references
        updated_versions = register_db.get_processing_versions(doc_uuid)
        for version in updated_versions:
            assert version["vector_index_id"] is not None
            assert version["embeddings_path"] is not None
            assert version["vector_index_id"].startswith("vector_index_")
    
    def test_metadata_tracking_and_retrieval(self, register_db, sample_documents):
        """Test comprehensive metadata tracking and retrieval."""
        doc_data = sample_documents[0]
        
        # Register document with rich metadata
        doc_uuid = register_db.register_document(
            doc_uuid=doc_data["doc_uuid"],
            file_uuid=doc_data["file_uuid"],
            source_file_path=doc_data["source_path"],
            metadata=doc_data["metadata"],
            file_info={
                "filename": "research_paper.pdf",
                "size": 2048000,
                "hash": "sha256:abc123def456",
                "mime_type": "application/pdf"
            }
        )
        
        # Add processing version with detailed metadata
        version_id = register_db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid=doc_data["processing_versions"][0]["set_uuid"],
            processing_method="advanced_chunking",
            processor_version="2.1.0",
            processing_config={
                "chunk_size": 300,
                "overlap": 75,
                "semantic_analysis": True,
                "language_model": "gpt-4",
                "quality_threshold": 0.85
            },
            processing_duration=15.7,
            chunk_count=45,
            status=ProcessingStatus.COMPLETED,
            warnings=["Low confidence on page 3", "Table extraction partial"]
        )
        
        # Retrieve and verify document metadata
        stored_doc = register_db.get_document(doc_uuid)
        
        # Check basic metadata
        assert stored_doc["title"] == doc_data["metadata"].title
        assert stored_doc["author"] == doc_data["metadata"].author
        assert stored_doc["page_count"] == doc_data["metadata"].page_count
        assert stored_doc["word_count"] == doc_data["metadata"].word_count
        assert stored_doc["language"] == doc_data["metadata"].language
        
        # Check file info
        assert stored_doc["original_filename"] == "research_paper.pdf"
        assert stored_doc["file_size_bytes"] == 2048000
        assert stored_doc["file_hash"] == "sha256:abc123def456"
        assert stored_doc["mime_type"] == "application/pdf"
        
        # Check custom metadata
        custom_meta = stored_doc["custom_metadata"]
        assert custom_meta["category"] == "research"
        assert custom_meta["department"] == "AI"
        
        # Retrieve and verify processing version metadata
        versions = register_db.get_processing_versions(doc_uuid)
        version = versions[0]
        
        assert version["processing_method"] == "advanced_chunking"
        assert version["processor_version"] == "2.1.0"
        assert version["processing_duration"] == 15.7
        assert version["chunk_count"] == 45
        assert version["status"] == ProcessingStatus.COMPLETED.value
        
        # Check processing config
        config = version["processing_config"]
        assert config["chunk_size"] == 300
        assert config["overlap"] == 75
        assert config["semantic_analysis"] is True
        assert config["language_model"] == "gpt-4"
        assert config["quality_threshold"] == 0.85
        
        # Check warnings
        warnings = version["warnings"]
        assert len(warnings) == 2
        assert "Low confidence on page 3" in warnings
        assert "Table extraction partial" in warnings
    
    def test_processing_queue_integration(self, register_db, sample_documents):
        """Test processing queue integration with document storage."""
        doc_data = sample_documents[0]
        
        # Register document
        doc_uuid = register_db.register_document(
            doc_uuid=doc_data["doc_uuid"],
            file_uuid=doc_data["file_uuid"],
            source_file_path=doc_data["source_path"],
            metadata=doc_data["metadata"]
        )
        
        # Add to processing queue
        queue_id = register_db.add_to_processing_queue(
            doc_uuid=doc_uuid,
            requested_methods=["paragraph_chunking", "abbreviation_expansion"],
            requested_config={
                "chunk_size": 250,
                "overlap": 50,
                "expand_abbreviations": True,
                "domains": ["technical", "academic"]
            },
            priority=8
        )
        
        assert queue_id is not None
        
        # Get next queued document
        next_item = register_db.get_next_queued_document()
        assert next_item is not None
        assert next_item["doc_uuid"] == doc_uuid
        assert next_item["priority"] == 8
        assert "paragraph_chunking" in next_item["requested_methods"]
        assert "abbreviation_expansion" in next_item["requested_methods"]
        
        # Simulate processing workflow
        # 1. Mark as processing
        register_db.update_queue_status(queue_id, "processing")
        
        # 2. Update document status
        register_db.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.IN_PROGRESS
        )
        
        # 3. Complete processing and add version
        version_id = register_db.add_processing_version(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            processing_method="paragraph_chunking_with_expansion",
            processor_version="1.0.0",
            processing_config=next_item["requested_config"],
            processing_duration=8.2,
            chunk_count=32,
            status=ProcessingStatus.COMPLETED
        )
        
        # 4. Mark queue item as completed
        register_db.update_queue_status(queue_id, "completed")
        
        # 5. Update document status
        register_db.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.COMPLETED
        )
        
        # Verify final state
        final_doc = register_db.get_document(doc_uuid)
        assert final_doc["processing_status"] == ProcessingStatus.COMPLETED.value
        
        versions = register_db.get_processing_versions(doc_uuid)
        assert len(versions) == 1
        assert versions[0]["chunk_count"] == 32
        assert versions[0]["processing_config"]["chunk_size"] == 250
        
        # Verify queue is empty for next processing
        next_queued = register_db.get_next_queued_document()
        assert next_queued is None
    
    def test_statistics_and_analytics(self, register_db, sample_documents):
        """Test statistics and analytics functionality."""
        # Register multiple documents with different characteristics
        for i, doc_data in enumerate(sample_documents):
            doc_uuid = register_db.register_document(
                doc_uuid=doc_data["doc_uuid"],
                file_uuid=doc_data["file_uuid"],
                source_file_path=doc_data["source_path"],
                metadata=doc_data["metadata"]
            )
            
            # Add processing versions
            for j, version_data in enumerate(doc_data["processing_versions"]):
                register_db.add_processing_version(
                    doc_uuid=doc_uuid,
                    set_uuid=version_data["set_uuid"],
                    processing_method=version_data["method"],
                    processor_version="1.0.0",
                    processing_config=version_data["config"],
                    chunk_count=20 + j * 5,
                    status=ProcessingStatus.COMPLETED if i == 0 else ProcessingStatus.IN_PROGRESS
                )
            
            # Update document status
            status = ProcessingStatus.COMPLETED if i == 0 else ProcessingStatus.IN_PROGRESS
            register_db.update_processing_status(doc_uuid, status)
            
            # Index first document only
            if i == 0:
                register_db.update_indexing_status(doc_uuid, True, "v1.0")
        
        # Get and verify statistics
        stats = register_db.get_processing_statistics()
        
        # Check basic counts
        assert stats["total_documents"] == 2
        assert stats["indexed_documents"] == 1
        assert stats["total_processing_versions"] == 3  # 2 + 1
        
        # Check status distribution
        status_dist = stats["status_distribution"]
        assert status_dist.get(ProcessingStatus.COMPLETED.value, 0) == 1
        assert status_dist.get(ProcessingStatus.IN_PROGRESS.value, 0) == 1
        
        # Check file type distribution
        file_type_dist = stats["file_type_distribution"]
        assert file_type_dist.get("pdf", 0) == 1
        assert file_type_dist.get("docx", 0) == 1
        
        # Check language distribution
        lang_dist = stats["language_distribution"]
        assert lang_dist.get("en", 0) == 2
        
        # Check indexing rate
        assert stats["indexing_rate"] == 0.5  # 1 out of 2 documents indexed


class TestCRUDIntegration:
    """Integration tests for CRUD operations."""
    
    def test_crud_complete_workflow(self, crud_interface, sample_documents):
        """Test complete CRUD workflow."""
        doc_data = sample_documents[0]
        
        # CREATE
        doc_uuid = crud_interface.create_document(
            doc_uuid=doc_data["doc_uuid"],
            file_uuid=doc_data["file_uuid"],
            source_file_path=doc_data["source_path"],
            metadata=doc_data["metadata"],
            file_info={
                "filename": "test_doc.pdf",
                "size": 1024000,
                "hash": "test_hash_123",
                "mime_type": "application/pdf"
            }
        )
        
        # READ
        retrieved_doc = crud_interface.get_document(doc_uuid)
        assert retrieved_doc is not None
        assert retrieved_doc["title"] == doc_data["metadata"].title
        
        # UPDATE
        success = crud_interface.update_processing_status(
            doc_uuid=doc_uuid,
            status=ProcessingStatus.COMPLETED
        )
        assert success is True
        
        # Verify update
        updated_doc = crud_interface.get_document(doc_uuid)
        assert updated_doc["processing_status"] == ProcessingStatus.COMPLETED.value
        
        # CREATE processing version
        version_id = crud_interface.create_processing_version(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            processing_method="test_method",
            processing_config={"test": "config"},
            chunk_count=15
        )
        assert version_id is not None
        
        # READ processing versions
        versions = crud_interface.get_processing_versions(doc_uuid)
        assert len(versions) == 1
        assert versions[0]["processing_method"] == "test_method"
        
        # SEARCH
        search_results = crud_interface.search_documents("Research Paper")
        assert len(search_results) >= 1
        found_doc = next((doc for doc in search_results if doc["doc_uuid"] == doc_uuid), None)
        assert found_doc is not None
        
        # LIST with filters
        pdf_docs = crud_interface.get_documents_by_type("pdf")
        assert len(pdf_docs) >= 1
        
        completed_docs = crud_interface.get_documents_by_status(ProcessingStatus.COMPLETED)
        assert len(completed_docs) >= 1
        
        # VALIDATE integrity
        integrity_result = crud_interface.validate_document_integrity(doc_uuid)
        assert integrity_result["valid"] is True
        assert len(integrity_result["errors"]) == 0
        assert integrity_result["version_count"] == 1
        
        # DELETE (soft delete)
        delete_success = crud_interface.delete_document(doc_uuid, soft_delete=True)
        assert delete_success is True
        
        # Verify soft delete
        deleted_doc = crud_interface.get_document(doc_uuid)
        assert deleted_doc is None  # Should not be returned in normal queries
        
        # RESTORE
        restore_success = crud_interface.restore_document(doc_uuid)
        assert restore_success is True
        
        # Verify restore
        restored_doc = crud_interface.get_document(doc_uuid)
        assert restored_doc is not None
        assert restored_doc["title"] == doc_data["metadata"].title
    
    def test_bulk_operations(self, crud_interface, sample_documents):
        """Test bulk operations through CRUD interface."""
        doc_uuids = []
        
        # Create multiple documents
        for doc_data in sample_documents:
            doc_uuid = crud_interface.create_document(
                doc_uuid=doc_data["doc_uuid"],
                file_uuid=doc_data["file_uuid"],
                source_file_path=doc_data["source_path"],
                metadata=doc_data["metadata"]
            )
            doc_uuids.append(doc_uuid)
        
        # Bulk status update
        bulk_result = crud_interface.bulk_update_status(
            doc_uuids=doc_uuids,
            status=ProcessingStatus.COMPLETED
        )
        
        assert bulk_result["success_count"] == len(doc_uuids)
        assert bulk_result["error_count"] == 0
        assert bulk_result["total_processed"] == len(doc_uuids)
        
        # Verify bulk update
        for doc_uuid in doc_uuids:
            doc = crud_interface.get_document(doc_uuid)
            assert doc["processing_status"] == ProcessingStatus.COMPLETED.value
        
        # Test statistics
        stats = crud_interface.get_statistics()
        assert stats["total_documents"] >= len(doc_uuids)
        
        # Test cleanup
        cleanup_result = crud_interface.cleanup_old_documents(retention_days=0)  # Clean all
        assert cleanup_result["documents_cleaned"] >= 0


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in storage integration."""
    
    def test_duplicate_document_handling(self, register_db):
        """Test handling of duplicate document registrations."""
        doc_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        metadata = DocumentMetadata(title="Test Doc", file_type="pdf")
        
        # Register document first time
        result1 = register_db.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=metadata
        )
        assert result1 == doc_uuid
        
        # Register same document again (should update, not fail)
        updated_metadata = DocumentMetadata(title="Updated Test Doc", file_type="pdf")
        result2 = register_db.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/path",
            metadata=updated_metadata
        )
        assert result2 == doc_uuid
        
        # Verify update
        doc = register_db.get_document(doc_uuid)
        assert doc["title"] == "Updated Test Doc"
    
    def test_invalid_uuid_handling(self, crud_interface):
        """Test handling of invalid UUIDs."""
        # Test with non-existent UUID
        doc = crud_interface.get_document("non-existent-uuid")
        assert doc is None
        
        # Test update with non-existent UUID
        success = crud_interface.update_processing_status(
            doc_uuid="non-existent-uuid",
            status=ProcessingStatus.COMPLETED
        )
        assert success is False
        
        # Test integrity validation with non-existent UUID
        integrity = crud_interface.validate_document_integrity("non-existent-uuid")
        assert integrity["valid"] is False
        assert "Document not found" in integrity["errors"]
    
    def test_concurrent_access_simulation(self, register_db):
        """Test simulation of concurrent access patterns."""
        doc_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        metadata = DocumentMetadata(title="Concurrent Test", file_type="pdf")
        
        # Register document
        register_db.register_document(
            doc_uuid=doc_uuid,
            file_uuid=file_uuid,
            source_file_path="/test/concurrent",
            metadata=metadata
        )
        
        # Simulate multiple processing versions being added concurrently
        set_uuids = [str(uuid.uuid4()) for _ in range(5)]
        
        for i, set_uuid in enumerate(set_uuids):
            register_db.add_processing_version(
                doc_uuid=doc_uuid,
                set_uuid=set_uuid,
                processing_method=f"method_{i}",
                processor_version="1.0.0",
                chunk_count=10 + i
            )
        
        # Verify all versions were stored
        versions = register_db.get_processing_versions(doc_uuid)
        assert len(versions) == 5
        
        stored_set_uuids = [v["set_uuid"] for v in versions]
        assert set(stored_set_uuids) == set(set_uuids)


if __name__ == "__main__":
    pytest.main([__file__])