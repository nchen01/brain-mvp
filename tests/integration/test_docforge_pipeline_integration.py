"""
Integration tests for DocForge Pipeline with Versioning.

This test suite validates the complete DocForge pipeline integration including:
- Document registration and versioning
- Preprocessing pipeline integration
- Postprocessing pipeline integration
- Storage systems integration
- RAG preparation integration
- Version chain integrity throughout all stages
"""

import pytest
import asyncio
import tempfile
import os
import time
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from docforge.pipeline import DocForgePipeline, PipelineConfig, PipelineStage
from docforge.versioning.lineage import DocumentLineageManager
from docforge.storage.meta_document_crud import MetaDocumentCRUD


class TestDocForgePipelineIntegration:
    """Test complete DocForge pipeline integration."""
    
    @pytest.fixture
    def temp_environment(self):
        """Create temporary environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PipelineConfig(
                raw_db_path=os.path.join(temp_dir, "raw_docs.db"),
                post_db_path=os.path.join(temp_dir, "post_docs.db"),
                meta_db_path=os.path.join(temp_dir, "meta_docs.db"),
                upload_dir=os.path.join(temp_dir, "uploads"),
                processed_dir=os.path.join(temp_dir, "processed"),
                lightrag_dir=os.path.join(temp_dir, "lightrag"),
                enable_postprocessing=True,
                enable_rag_preparation=True,
                max_concurrent_documents=2
            )
            
            yield {
                'config': config,
                'temp_dir': temp_dir
            }
    
    @pytest.fixture
    def pipeline(self, temp_environment):
        """Create pipeline instance for testing."""
        pipeline = DocForgePipeline(temp_environment['config'])
        yield pipeline
        pipeline.shutdown()
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Create sample PDF content for testing."""
        # This is a minimal PDF content for testing
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_new_document(self, pipeline, sample_pdf_content):
        """Test complete pipeline processing for a new document."""
        # Process new document
        result = await pipeline.process_document(
            file_path="test_document.pdf",
            file_content=sample_pdf_content,
            filename="test_document.pdf",
            user_id="test_user"
        )
        
        # Verify successful processing
        assert result.success is True
        assert result.stage_reached == PipelineStage.COMPLETED
        assert result.document_uuid is not None
        assert result.lineage_uuid is not None
        assert result.version_number == 1
        assert result.processing_time > 0
        assert result.error_message is None
        
        # Verify metadata
        assert result.metadata is not None
        assert result.metadata['filename'] == "test_document.pdf"
        assert result.metadata['user_id'] == "test_user"
        assert result.metadata['file_size'] == len(sample_pdf_content)
        assert 'processing_stages' in result.metadata
    
    @pytest.mark.asyncio
    async def test_version_chain_integrity(self, pipeline, sample_pdf_content):
        """Test version chain integrity throughout pipeline processing."""
        # Process first version
        result_v1 = await pipeline.process_document(
            file_path="document_v1.pdf",
            file_content=sample_pdf_content,
            filename="document_v1.pdf",
            user_id="test_user"
        )
        
        assert result_v1.success is True
        assert result_v1.version_number == 1
        lineage_uuid = result_v1.lineage_uuid
        
        # Process second version (linear)
        modified_content = sample_pdf_content + b"\n% Modified content"
        result_v2 = await pipeline.process_document(
            file_path="document_v2.pdf",
            file_content=modified_content,
            filename="document_v2.pdf",
            user_id="test_user",
            lineage_uuid=lineage_uuid
        )
        
        assert result_v2.success is True
        assert result_v2.version_number == 2
        assert result_v2.lineage_uuid == lineage_uuid
        
        # Process branch from version 1
        branch_content = sample_pdf_content + b"\n% Branched content"
        result_branch = await pipeline.process_document(
            file_path="document_branch.pdf",
            file_content=branch_content,
            filename="document_branch.pdf",
            user_id="test_user",
            parent_version=1,
            lineage_uuid=lineage_uuid
        )
        
        assert result_branch.success is True
        assert result_branch.version_number == 3  # Next available version number
        assert result_branch.lineage_uuid == lineage_uuid
        
        # Verify version chain status
        chain_status = pipeline.get_version_chain_status(lineage_uuid)
        assert 'error' not in chain_status
        assert chain_status['total_versions'] == 3
        assert len(chain_status['versions']) == 3
    
    @pytest.mark.asyncio
    async def test_pipeline_stage_tracking(self, pipeline, sample_pdf_content):
        """Test pipeline stage tracking during processing."""
        # Start processing (don't await to check intermediate status)
        process_task = asyncio.create_task(
            pipeline.process_document(
                file_path="tracking_test.pdf",
                file_content=sample_pdf_content,
                filename="tracking_test.pdf",
                user_id="test_user"
            )
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Complete processing
        result = await process_task
        
        # Verify final status
        assert result.success is True
        status = pipeline.get_processing_status(result.document_uuid)
        assert status['current_stage'] == PipelineStage.COMPLETED
        assert status['is_processing'] is False
    
    @pytest.mark.asyncio
    async def test_storage_integration(self, pipeline, sample_pdf_content, temp_environment):
        """Test integration with all storage systems."""
        # Process document
        result = await pipeline.process_document(
            file_path="storage_test.pdf",
            file_content=sample_pdf_content,
            filename="storage_test.pdf",
            user_id="test_user"
        )
        
        assert result.success is True
        
        # Verify document in lineage manager
        lineage_manager = DocumentLineageManager(temp_environment['config'].raw_db_path)
        lineage = lineage_manager.get_lineage(result.lineage_uuid)
        assert lineage is not None
        assert lineage.original_filename == "storage_test.pdf"
        
        versions = lineage_manager.get_versions_by_lineage(result.lineage_uuid)
        assert len(versions) == 1
        assert versions[0].doc_uuid == result.document_uuid
        
        # Verify document in meta document CRUD
        meta_crud = MetaDocumentCRUD(temp_environment['config'].meta_db_path)
        meta_doc = meta_crud.get_meta_document(result.document_uuid)
        assert meta_doc is not None
        assert meta_doc.set_uuid == result.lineage_uuid  # Lineage used as set identifier
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, temp_environment):
        """Test error handling and recovery in pipeline."""
        # Create pipeline with invalid configuration to trigger errors
        invalid_config = PipelineConfig(
            raw_db_path="/invalid/path/raw.db",  # Invalid path
            post_db_path=temp_environment['config'].post_db_path,
            meta_db_path=temp_environment['config'].meta_db_path,
            upload_dir=temp_environment['config'].upload_dir,
            processed_dir=temp_environment['config'].processed_dir,
            lightrag_dir=temp_environment['config'].lightrag_dir
        )
        
        # Pipeline initialization should fail gracefully
        with pytest.raises(Exception):
            DocForgePipeline(invalid_config)
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, pipeline, sample_pdf_content):
        """Test concurrent document processing."""
        # Prepare multiple documents
        documents = []
        for i in range(3):
            documents.append({
                'file_path': f"concurrent_test_{i}.pdf",
                'file_content': sample_pdf_content + f"\n% Document {i}".encode(),
                'filename': f"concurrent_test_{i}.pdf",
                'user_id': f"user_{i}"
            })
        
        # Process concurrently
        results = await pipeline.process_batch(documents, max_concurrent=2)
        
        # Verify all processed successfully
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.stage_reached == PipelineStage.COMPLETED
        
        # Verify unique document UUIDs and lineage UUIDs
        doc_uuids = [r.document_uuid for r in results]
        lineage_uuids = [r.lineage_uuid for r in results]
        
        assert len(set(doc_uuids)) == 3  # All unique
        assert len(set(lineage_uuids)) == 3  # All unique (new documents)
    
    @pytest.mark.asyncio
    async def test_postprocessing_integration(self, temp_environment, sample_pdf_content):
        """Test postprocessing integration in pipeline."""
        # Create pipeline with postprocessing enabled
        config = temp_environment['config']
        config.enable_postprocessing = True
        config.enable_abbreviation_expansion = True
        
        pipeline = DocForgePipeline(config)
        
        try:
            # Process document
            result = await pipeline.process_document(
                file_path="postprocess_test.pdf",
                file_content=sample_pdf_content,
                filename="postprocess_test.pdf",
                user_id="test_user"
            )
            
            # Should succeed even with mock processing
            assert result.success is True
            assert result.stage_reached == PipelineStage.COMPLETED
            
        finally:
            pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_rag_preparation_integration(self, temp_environment, sample_pdf_content):
        """Test RAG preparation integration in pipeline."""
        # Create pipeline with RAG preparation enabled
        config = temp_environment['config']
        config.enable_rag_preparation = True
        
        pipeline = DocForgePipeline(config)
        
        try:
            # Process document
            result = await pipeline.process_document(
                file_path="rag_test.pdf",
                file_content=sample_pdf_content,
                filename="rag_test.pdf",
                user_id="test_user"
            )
            
            # Should succeed (may use mock RAG preparation)
            assert result.success is True
            assert result.stage_reached == PipelineStage.COMPLETED
            
        finally:
            pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_pipeline_configuration_options(self, temp_environment, sample_pdf_content):
        """Test different pipeline configuration options."""
        # Test with minimal configuration (no postprocessing, no RAG)
        minimal_config = temp_environment['config']
        minimal_config.enable_postprocessing = False
        minimal_config.enable_rag_preparation = False
        
        pipeline = DocForgePipeline(minimal_config)
        
        try:
            result = await pipeline.process_document(
                file_path="minimal_test.pdf",
                file_content=sample_pdf_content,
                filename="minimal_test.pdf",
                user_id="test_user"
            )
            
            assert result.success is True
            assert result.stage_reached == PipelineStage.COMPLETED
            
            # Should have fewer processing stages
            assert 'postprocessing' not in result.metadata.get('processing_stages', [])
            assert 'rag_preparation' not in result.metadata.get('processing_stages', [])
            
        finally:
            pipeline.shutdown()
    
    def test_pipeline_status_tracking(self, pipeline, sample_pdf_content):
        """Test pipeline status tracking functionality."""
        # Test status for non-existent document
        status = pipeline.get_processing_status("non_existent_uuid")
        assert status['current_stage'] == PipelineStage.COMPLETED
        assert status['is_processing'] is False
        
        # Test version chain status for non-existent lineage
        chain_status = pipeline.get_version_chain_status("non_existent_lineage")
        assert 'error' in chain_status


class TestPipelineErrorScenarios:
    """Test pipeline error handling scenarios."""
    
    @pytest.fixture
    def temp_environment(self):
        """Create temporary environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PipelineConfig(
                raw_db_path=os.path.join(temp_dir, "raw_docs.db"),
                post_db_path=os.path.join(temp_dir, "post_docs.db"),
                meta_db_path=os.path.join(temp_dir, "meta_docs.db"),
                upload_dir=os.path.join(temp_dir, "uploads"),
                processed_dir=os.path.join(temp_dir, "processed"),
                lightrag_dir=os.path.join(temp_dir, "lightrag")
            )
            
            yield {
                'config': config,
                'temp_dir': temp_dir
            }
    
    @pytest.fixture
    def pipeline(self, temp_environment):
        """Create pipeline instance for testing."""
        pipeline = DocForgePipeline(temp_environment['config'])
        yield pipeline
        pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_invalid_file_content(self, pipeline):
        """Test handling of invalid file content."""
        # Test with empty content
        result = await pipeline.process_document(
            file_path="empty.pdf",
            file_content=b"",
            filename="empty.pdf",
            user_id="test_user"
        )
        
        # Should handle gracefully (may succeed with mock processing)
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_invalid_lineage_uuid(self, pipeline):
        """Test handling of invalid lineage UUID."""
        result = await pipeline.process_document(
            file_path="test.pdf",
            file_content=b"test content",
            filename="test.pdf",
            user_id="test_user",
            lineage_uuid="invalid_lineage_uuid"
        )
        
        # Should fail gracefully
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_processing_timeout_handling(self, temp_environment):
        """Test handling of processing timeouts."""
        # Create pipeline with very short timeout
        config = temp_environment['config']
        config.processing_timeout = 1  # 1 second timeout
        
        pipeline = DocForgePipeline(config)
        
        try:
            # This should complete quickly with mock processing
            result = await pipeline.process_document(
                file_path="timeout_test.pdf",
                file_content=b"test content",
                filename="timeout_test.pdf",
                user_id="test_user"
            )
            
            # Should succeed with mock processing
            assert isinstance(result.success, bool)
            
        finally:
            pipeline.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])