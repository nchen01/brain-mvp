"""Test core functionality."""

import pytest
from datetime import datetime

from src.core.models import RawDocument, DocumentLineage, DocumentVersion
from src.core.exceptions import BrainMVPException, DocumentNotFoundError


def test_raw_document_creation():
    """Test RawDocument model creation."""
    doc = RawDocument(
        content=b"test content",
        filename="test.pdf",
        file_type="pdf",
        user_id="user123",
        labels=["test", "document"]
    )
    
    assert doc.filename == "test.pdf"
    assert doc.file_type == "pdf"
    assert doc.user_id == "user123"
    assert doc.labels == ["test", "document"]
    assert isinstance(doc.upload_timestamp, datetime)


def test_document_lineage_creation():
    """Test DocumentLineage model creation."""
    lineage = DocumentLineage(
        lineage_uuid="lineage-123",
        original_filename="test.pdf",
        created_by="user123",
        created_at=datetime.utcnow(),
        current_version=1,
        total_versions=1
    )
    
    assert lineage.lineage_uuid == "lineage-123"
    assert lineage.original_filename == "test.pdf"
    assert lineage.created_by == "user123"
    assert lineage.current_version == 1
    assert lineage.is_active is True


def test_document_version_creation():
    """Test DocumentVersion model creation."""
    version = DocumentVersion(
        doc_uuid="doc-123",
        lineage_uuid="lineage-123",
        version_number=1,
        filename="test.pdf",
        file_path="/path/to/test.pdf",
        file_type="pdf",
        file_hash="abc123",
        timestamp=datetime.utcnow(),
        user_id="user123"
    )
    
    assert version.doc_uuid == "doc-123"
    assert version.lineage_uuid == "lineage-123"
    assert version.version_number == 1
    assert version.is_current is False
    assert version.is_deleted is False


def test_brain_mvp_exception():
    """Test BrainMVPException creation."""
    exc = BrainMVPException(
        message="Test error",
        error_code="TEST_ERROR",
        details={"key": "value"}
    )
    
    assert exc.message == "Test error"
    assert exc.error_code == "TEST_ERROR"
    assert exc.details == {"key": "value"}


def test_document_not_found_error():
    """Test DocumentNotFoundError creation."""
    exc = DocumentNotFoundError("doc-123")
    
    assert "doc-123" in exc.message
    assert exc.error_code == "DOCUMENT_NOT_FOUND"
    assert exc.details["doc_uuid"] == "doc-123"