"""Tests for Meta Document Database and CRUD operations."""

import pytest
import tempfile
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.docforge.storage.meta_document_db import (
    MetaDocumentDatabase,
    MetaDocumentRecord,
    MetaDocumentComponent
)
from src.docforge.storage.meta_document_crud import MetaDocumentCRUD


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
def meta_db(temp_db):
    """Create a MetaDocumentDatabase instance for testing."""
    return MetaDocumentDatabase(temp_db)


@pytest.fixture
def meta_crud(temp_db):
    """Create a MetaDocumentCRUD instance for testing."""
    return MetaDocumentCRUD(temp_db)


def create_sample_components():
    """Create sample meta document components with unique IDs."""
    return [
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="This is the first chunk of the document containing important information.",
            metadata={"page": 1, "section": "introduction"},
            order_index=0,
            confidence_score=0.95
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="chunk",
            content="This is the second chunk with more detailed analysis and findings.",
            metadata={"page": 2, "section": "analysis"},
            order_index=1,
            confidence_score=0.88
        ),
        MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="summary",
            content="Document summary: This paper discusses advanced techniques in AI processing.",
            metadata={"type": "abstract"},
            order_index=2,
            confidence_score=0.92
        )
    ]


@pytest.fixture
def sample_components():
    """Create sample meta document components."""
    return create_sample_components()


@pytest.fixture
def sample_processing_history():
    """Create sample processing history."""
    return [
        {
            "stage": "preprocessing",
            "processor": "mineru",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration": 5.2,
            "status": "completed"
        },
        {
            "stage": "postprocessing",
            "processor": "chunker",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration": 2.1,
            "status": "completed"
        }
    ]


class TestMetaDocumentDatabase:
    """Test the MetaDocumentDatabase class."""
    
    def test_database_creation(self, temp_db):
        """Test that database and tables are created properly."""
        db = MetaDocumentDatabase(temp_db)
        
        # Check that database file exists
        assert os.path.exists(temp_db)
        
        # Check that we can get a connection
        conn = db._get_connection()
        assert conn is not None
        conn.close()
    
    def test_create_meta_document(self, meta_db, sample_components, sample_processing_history):
        """Test creating a meta document."""
        doc_uuid = str(uuid.uuid4())
        set_uuid = str(uuid.uuid4())
        title = "Test Research Paper"
        summary = "This is a comprehensive test document for AI research."
        
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            title=title,
            summary=summary,
            components=sample_components,
            processing_history=sample_processing_history
        )
        
        assert meta_doc_uuid is not None
        assert len(meta_doc_uuid) > 0
        
        # Verify the document was stored
        stored_doc = meta_db.get_meta_document(meta_doc_uuid)
        assert stored_doc is not None
        assert stored_doc.doc_uuid == doc_uuid
        assert stored_doc.set_uuid == set_uuid
        assert stored_doc.title == title
        assert stored_doc.summary == summary
        assert len(stored_doc.components) == 3
        assert len(stored_doc.processing_history) == 2
        assert stored_doc.rag_ready is False
    
    def test_get_meta_document_not_found(self, meta_db):
        """Test getting a non-existent meta document."""
        doc = meta_db.get_meta_document("non-existent-uuid")
        assert doc is None
    
    def test_get_meta_documents_by_doc_uuid(self, meta_db, sample_components):
        """Test getting meta documents by document UUID."""
        doc_uuid = str(uuid.uuid4())
        
        # Create multiple meta documents for the same doc_uuid
        components1 = create_sample_components()
        components2 = create_sample_components()
        
        meta_doc_uuid1 = meta_db.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            title="Version 1",
            summary="First version",
            components=components1[:2]
        )
        
        meta_doc_uuid2 = meta_db.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            title="Version 2",
            summary="Second version",
            components=components2[1:]
        )
        
        # Retrieve by doc_uuid
        meta_docs = meta_db.get_meta_documents_by_doc_uuid(doc_uuid)
        assert len(meta_docs) == 2
        
        meta_doc_uuids = [doc.meta_doc_uuid for doc in meta_docs]
        assert meta_doc_uuid1 in meta_doc_uuids
        assert meta_doc_uuid2 in meta_doc_uuids
    
    def test_get_meta_documents_by_set_uuid(self, meta_db, sample_components):
        """Test getting meta documents by set UUID."""
        set_uuid = str(uuid.uuid4())
        
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=set_uuid,
            title="Test Document",
            summary="Test summary",
            components=sample_components
        )
        
        # Retrieve by set_uuid
        meta_docs = meta_db.get_meta_documents_by_set_uuid(set_uuid)
        assert len(meta_docs) == 1
        assert meta_docs[0].meta_doc_uuid == meta_doc_uuid
        assert meta_docs[0].set_uuid == set_uuid
    
    def test_update_rag_ready_status(self, meta_db, sample_components):
        """Test updating RAG ready status."""
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components
        )
        
        # Update RAG ready status
        vector_index_id = "vector_index_123"
        knowledge_graph_id = "kg_456"
        
        meta_db.update_rag_ready_status(
            meta_doc_uuid=meta_doc_uuid,
            rag_ready=True,
            vector_index_id=vector_index_id,
            knowledge_graph_id=knowledge_graph_id
        )
        
        # Verify update
        updated_doc = meta_db.get_meta_document(meta_doc_uuid)
        assert updated_doc.rag_ready is True
        assert updated_doc.vector_index_id == vector_index_id
        assert updated_doc.knowledge_graph_id == knowledge_graph_id
    
    def test_add_component(self, meta_db, sample_components):
        """Test adding a component to an existing meta document."""
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components[:2]  # Only first 2 components
        )
        
        # Add a new component
        new_component = MetaDocumentComponent(
            component_id=str(uuid.uuid4()),
            component_type="metadata",
            content="Additional metadata component",
            metadata={"source": "manual"},
            order_index=3,
            confidence_score=0.85
        )
        
        component_id = meta_db.add_component(meta_doc_uuid, new_component)
        assert component_id == new_component.component_id
        
        # Verify component was added
        updated_doc = meta_db.get_meta_document(meta_doc_uuid)
        assert len(updated_doc.components) == 3
        
        # Find the new component
        added_component = next(
            (comp for comp in updated_doc.components if comp.component_id == component_id),
            None
        )
        assert added_component is not None
        assert added_component.component_type == "metadata"
        assert added_component.content == "Additional metadata component"
    
    def test_get_components_by_type(self, meta_db, sample_components):
        """Test getting components by type."""
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components
        )
        
        # Get chunk components
        chunk_components = meta_db.get_components_by_type(meta_doc_uuid, "chunk")
        assert len(chunk_components) == 2
        assert all(comp.component_type == "chunk" for comp in chunk_components)
        
        # Get summary components
        summary_components = meta_db.get_components_by_type(meta_doc_uuid, "summary")
        assert len(summary_components) == 1
        assert summary_components[0].component_type == "summary"
    
    def test_update_component_embedding(self, meta_db, sample_components):
        """Test updating component vector embedding."""
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components
        )
        
        # Update embedding for first component
        component_id = sample_components[0].component_id
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        meta_db.update_component_embedding(component_id, test_embedding)
        
        # Verify embedding was updated
        updated_doc = meta_db.get_meta_document(meta_doc_uuid)
        updated_component = next(
            (comp for comp in updated_doc.components if comp.component_id == component_id),
            None
        )
        assert updated_component is not None
        assert updated_component.vector_embedding == test_embedding
    
    def test_rag_preparation_status(self, meta_db, sample_components):
        """Test RAG preparation status tracking."""
        meta_doc_uuid = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components
        )
        
        # Update preparation status for different stages
        meta_db.update_rag_preparation_status(
            meta_doc_uuid=meta_doc_uuid,
            preparation_stage="embedding",
            status="completed",
            progress_percentage=100.0
        )
        
        meta_db.update_rag_preparation_status(
            meta_doc_uuid=meta_doc_uuid,
            preparation_stage="indexing",
            status="in_progress",
            progress_percentage=50.0
        )
        
        # Get preparation status
        status = meta_db.get_rag_preparation_status(meta_doc_uuid)
        
        assert "embedding" in status
        assert status["embedding"]["status"] == "completed"
        assert status["embedding"]["progress_percentage"] == 100.0
        
        assert "indexing" in status
        assert status["indexing"]["status"] == "in_progress"
        assert status["indexing"]["progress_percentage"] == 50.0
    
    def test_document_relationships(self, meta_db, sample_components):
        """Test document relationships."""
        # Create two meta documents
        components1 = create_sample_components()
        components2 = create_sample_components()
        
        meta_doc_uuid1 = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Document 1",
            summary="First document",
            components=components1[:2]
        )
        
        meta_doc_uuid2 = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Document 2",
            summary="Second document",
            components=components2[1:]
        )
        
        # Add relationship
        meta_db.add_document_relationship(
            source_meta_doc_uuid=meta_doc_uuid1,
            target_meta_doc_uuid=meta_doc_uuid2,
            relationship_type="similar",
            relationship_strength=0.85,
            metadata={"similarity_score": 0.85, "method": "cosine"}
        )
        
        # Get relationships
        relationships = meta_db.get_document_relationships(meta_doc_uuid1)
        assert len(relationships) == 1
        
        rel = relationships[0]
        assert rel["source_meta_doc_uuid"] == meta_doc_uuid1
        assert rel["target_meta_doc_uuid"] == meta_doc_uuid2
        assert rel["relationship_type"] == "similar"
        assert rel["relationship_strength"] == 0.85
        assert rel["metadata"]["similarity_score"] == 0.85
    
    def test_get_rag_ready_documents(self, meta_db, sample_components):
        """Test getting RAG-ready documents."""
        # Create documents with different RAG ready status
        components1 = create_sample_components()
        components2 = create_sample_components()
        
        meta_doc_uuid1 = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Ready Document",
            summary="This document is ready",
            components=components1
        )
        
        meta_doc_uuid2 = meta_db.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Not Ready Document",
            summary="This document is not ready",
            components=components2
        )
        
        # Mark first document as RAG ready
        meta_db.update_rag_ready_status(meta_doc_uuid1, True)
        
        # Get RAG ready documents
        rag_ready_docs = meta_db.get_rag_ready_documents()
        assert len(rag_ready_docs) == 1
        assert rag_ready_docs[0].meta_doc_uuid == meta_doc_uuid1
        assert rag_ready_docs[0].rag_ready is True
        
        # Get pending RAG documents
        pending_docs = meta_db.get_pending_rag_documents()
        assert len(pending_docs) == 1
        assert pending_docs[0].meta_doc_uuid == meta_doc_uuid2
        assert pending_docs[0].rag_ready is False
    
    def test_storage_statistics(self, meta_db, sample_components):
        """Test getting storage statistics."""
        # Create some test data
        for i in range(3):
            components = create_sample_components()
            meta_doc_uuid = meta_db.create_meta_document(
                doc_uuid=str(uuid.uuid4()),
                set_uuid=str(uuid.uuid4()),
                title=f"Document {i}",
                summary=f"Summary {i}",
                components=components
            )
            
            # Mark some as RAG ready
            if i < 2:
                meta_db.update_rag_ready_status(meta_doc_uuid, True)
        
        stats = meta_db.get_storage_statistics()
        
        assert stats["total_meta_documents"] == 3
        assert stats["rag_ready_documents"] == 2
        assert stats["pending_rag_documents"] == 1
        assert stats["rag_ready_percentage"] == pytest.approx(66.67, rel=1e-2)
        assert "components_by_type" in stats
        assert stats["components_by_type"]["chunk"] == 6  # 2 chunks per doc * 3 docs
        assert stats["components_by_type"]["summary"] == 3  # 1 summary per doc * 3 docs


class TestMetaDocumentCRUD:
    """Test the MetaDocumentCRUD class."""
    
    def test_create_meta_document(self, meta_crud, sample_components, sample_processing_history):
        """Test creating a meta document via CRUD interface."""
        doc_uuid = str(uuid.uuid4())
        set_uuid = str(uuid.uuid4())
        title = "CRUD Test Document"
        summary = "Test document created via CRUD interface"
        
        meta_doc_uuid = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=set_uuid,
            title=title,
            summary=summary,
            components=sample_components,
            processing_history=sample_processing_history
        )
        
        assert meta_doc_uuid is not None
        
        # Verify via get
        meta_doc = meta_crud.get_meta_document(meta_doc_uuid)
        assert meta_doc is not None
        assert meta_doc.title == title
        assert meta_doc.summary == summary
        assert len(meta_doc.components) == 3
    
    def test_create_component(self, meta_crud, sample_components):
        """Test creating a component via CRUD interface."""
        meta_doc_uuid = meta_crud.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Test Document",
            summary="Test summary",
            components=sample_components[:1]  # Start with 1 component
        )
        
        # Add component via CRUD
        component_id = meta_crud.create_component(
            meta_doc_uuid=meta_doc_uuid,
            component_type="embedding",
            content="Vector embedding data",
            metadata={"model": "sentence-transformers"},
            vector_embedding=[0.1, 0.2, 0.3],
            confidence_score=0.9
        )
        
        assert component_id is not None
        
        # Verify component was added
        meta_doc = meta_crud.get_meta_document(meta_doc_uuid)
        assert len(meta_doc.components) == 2
        
        # Find the new component
        new_component = next(
            (comp for comp in meta_doc.components if comp.component_id == component_id),
            None
        )
        assert new_component is not None
        assert new_component.component_type == "embedding"
        assert new_component.vector_embedding == [0.1, 0.2, 0.3]
    
    def test_search_meta_documents(self, meta_crud, sample_components):
        """Test searching meta documents."""
        # Create documents with different content
        components1 = create_sample_components()
        components2 = create_sample_components()
        
        meta_crud.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Python Programming Guide",
            summary="Comprehensive guide to Python programming",
            components=components1
        )
        
        meta_crud.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="JavaScript Tutorial",
            summary="Learn JavaScript from basics to advanced",
            components=components2
        )
        
        # Mark both as RAG ready for search
        rag_ready_docs = meta_crud.get_pending_rag_documents()
        for doc in rag_ready_docs:
            meta_crud.update_rag_ready_status(doc.meta_doc_uuid, True)
        
        # Search for Python
        results = meta_crud.search_meta_documents("Python")
        assert len(results) >= 1
        assert any("Python" in doc.title for doc in results)
        
        # Search for JavaScript
        results = meta_crud.search_meta_documents("JavaScript")
        assert len(results) >= 1
        assert any("JavaScript" in doc.title for doc in results)
    
    def test_validate_meta_document_integrity(self, meta_crud, sample_components):
        """Test meta document integrity validation."""
        meta_doc_uuid = meta_crud.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Validation Test",
            summary="Test document for validation",
            components=sample_components
        )
        
        # Validate integrity
        result = meta_crud.validate_meta_document_integrity(meta_doc_uuid)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["component_count"] == 3
        assert "chunk" in result["component_types"]
        assert "summary" in result["component_types"]
    
    def test_get_processing_pipeline_status(self, meta_crud, sample_components):
        """Test getting processing pipeline status."""
        doc_uuid = str(uuid.uuid4())
        
        # Create multiple meta documents for the same doc_uuid
        components1 = create_sample_components()
        components2 = create_sample_components()
        
        meta_doc_uuid1 = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            title="Version 1",
            summary="First version",
            components=components1
        )
        
        meta_doc_uuid2 = meta_crud.create_meta_document(
            doc_uuid=doc_uuid,
            set_uuid=str(uuid.uuid4()),
            title="Version 2",
            summary="Second version",
            components=components2
        )
        
        # Mark one as RAG ready
        meta_crud.update_rag_ready_status(meta_doc_uuid1, True)
        
        # Get pipeline status
        status = meta_crud.get_processing_pipeline_status(doc_uuid)
        
        assert status["doc_uuid"] == doc_uuid
        assert status["meta_documents_count"] == 2
        assert status["processing_complete"] is False  # Only 1 out of 2 is ready
        assert status["rag_ready_count"] == 1
        assert len(status["detailed_status"]) == 2
    
    def test_export_meta_document_for_rag(self, meta_crud, sample_components):
        """Test exporting meta document for RAG systems."""
        meta_doc_uuid = meta_crud.create_meta_document(
            doc_uuid=str(uuid.uuid4()),
            set_uuid=str(uuid.uuid4()),
            title="Export Test",
            summary="Document for export testing",
            components=sample_components
        )
        
        # Mark as RAG ready
        meta_crud.update_rag_ready_status(
            meta_doc_uuid=meta_doc_uuid,
            rag_ready=True,
            vector_index_id="test_vector_index",
            knowledge_graph_id="test_kg"
        )
        
        # Export for RAG
        exported = meta_crud.export_meta_document_for_rag(meta_doc_uuid)
        
        assert exported is not None
        assert exported["meta_doc_uuid"] == meta_doc_uuid
        assert exported["title"] == "Export Test"
        assert exported["vector_index_id"] == "test_vector_index"
        assert exported["knowledge_graph_id"] == "test_kg"
        assert "components_by_type" in exported
        assert "chunk" in exported["components_by_type"]
        assert "summary" in exported["components_by_type"]
        assert len(exported["components_by_type"]["chunk"]) == 2
        assert len(exported["components_by_type"]["summary"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])