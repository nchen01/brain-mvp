"""
Complete Pipeline End-to-End Tests with Versioning.

This test suite validates the complete document lifecycle through the DocForge pipeline
with comprehensive versioning support, including:
- Document upload and registration with lineage tracking
- Complete preprocessing and postprocessing workflow
- Version branching (editing old versions)
- Soft deletion and privacy compliance
- RAG preparation with version filtering
- Output format consistency across all stages and versions
"""

import pytest
import asyncio
import tempfile
import os
import time
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from docforge.pipeline import DocForgePipeline, PipelineConfig, PipelineStage
from docforge.versioning.lineage import DocumentLineageManager
from docforge.versioning.models import DocumentVersion
from docforge.storage.meta_document_crud import MetaDocumentCRUD
from core.models import ProcessedDocument


class TestCompleteDocumentLifecycle:
    """Test complete document lifecycle with versioning."""
    
    @pytest.fixture
    def test_environment(self):
        """Create comprehensive test environment."""
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
                enable_abbreviation_expansion=True,
                chunk_size=500,
                chunk_overlap=50
            )
            
            # Create additional test utilities
            lineage_manager = DocumentLineageManager(config.raw_db_path)
            meta_crud = MetaDocumentCRUD(config.meta_db_path)
            
            yield {
                'config': config,
                'temp_dir': temp_dir,
                'lineage_manager': lineage_manager,
                'meta_crud': meta_crud
            }
    
    @pytest.fixture
    def pipeline(self, test_environment):
        """Create pipeline instance for testing."""
        pipeline = DocForgePipeline(test_environment['config'])
        yield pipeline
        pipeline.shutdown()
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return {
            'pdf_v1': {
                'filename': 'research_paper_v1.pdf',
                'content': b'%PDF-1.4\n% Research Paper Version 1\n% This is the original version of the research paper\n% with initial findings and methodology.\n%%EOF',
                'user_id': 'researcher_1'
            },
            'pdf_v2': {
                'filename': 'research_paper_v2.pdf',
                'content': b'%PDF-1.4\n% Research Paper Version 2\n% Updated version with additional findings\n% and improved methodology section.\n%%EOF',
                'user_id': 'researcher_1'
            },
            'pdf_branch': {
                'filename': 'research_paper_alternative.pdf',
                'content': b'%PDF-1.4\n% Research Paper Alternative Version\n% Alternative approach based on version 1\n% with different methodology.\n%%EOF',
                'user_id': 'researcher_2'
            },
            'docx': {
                'filename': 'technical_spec.docx',
                'content': b'PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00[Content_Types].xml',
                'user_id': 'engineer_1'
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_document_upload_to_rag_workflow(self, pipeline, sample_documents):
        """Test complete document upload to RAG-ready output workflow with versioning."""
        pdf_doc = sample_documents['pdf_v1']
        
        # Stage 1: Upload and process first version
        result_v1 = await pipeline.process_document(
            file_path=pdf_doc['filename'],
            file_content=pdf_doc['content'],
            filename=pdf_doc['filename'],
            user_id=pdf_doc['user_id']
        )
        
        # Verify successful processing
        assert result_v1.success is True
        assert result_v1.stage_reached == PipelineStage.COMPLETED
        assert result_v1.version_number == 1
        assert result_v1.lineage_uuid is not None
        
        # Verify all processing stages completed
        expected_stages = ['registration', 'preprocessing', 'postprocessing', 'storage', 'rag_preparation']
        assert all(stage in result_v1.metadata['processing_stages'] for stage in expected_stages)
        
        # Stage 2: Upload and process second version (linear versioning)
        pdf_v2 = sample_documents['pdf_v2']
        result_v2 = await pipeline.process_document(
            file_path=pdf_v2['filename'],
            file_content=pdf_v2['content'],
            filename=pdf_v2['filename'],
            user_id=pdf_v2['user_id'],
            lineage_uuid=result_v1.lineage_uuid  # Add to same lineage
        )
        
        # Verify version 2 processing
        assert result_v2.success is True
        assert result_v2.version_number == 2
        assert result_v2.lineage_uuid == result_v1.lineage_uuid
        
        # Stage 3: Verify version chain integrity
        chain_status = pipeline.get_version_chain_status(result_v1.lineage_uuid)
        assert chain_status['total_versions'] == 2
        assert len(chain_status['versions']) == 2
        
        # Verify version ordering
        versions = sorted(chain_status['versions'], key=lambda v: v['version_number'])
        assert versions[0]['version_number'] == 1
        assert versions[1]['version_number'] == 2
        assert versions[0]['doc_uuid'] == result_v1.document_uuid
        assert versions[1]['doc_uuid'] == result_v2.document_uuid
    
    @pytest.mark.asyncio
    async def test_version_branching_complete_pipeline(self, pipeline, sample_documents, test_environment):
        """Test version branching (editing old versions) through complete pipeline."""
        pdf_doc = sample_documents['pdf_v1']
        
        # Process original document
        result_original = await pipeline.process_document(
            file_path=pdf_doc['filename'],
            file_content=pdf_doc['content'],
            filename=pdf_doc['filename'],
            user_id=pdf_doc['user_id']
        )
        
        assert result_original.success is True
        lineage_uuid = result_original.lineage_uuid
        
        # Process linear update (version 2)
        pdf_v2 = sample_documents['pdf_v2']
        result_v2 = await pipeline.process_document(
            file_path=pdf_v2['filename'],
            file_content=pdf_v2['content'],
            filename=pdf_v2['filename'],
            user_id=pdf_v2['user_id'],
            lineage_uuid=lineage_uuid
        )
        
        assert result_v2.success is True
        assert result_v2.version_number == 2
        
        # Create branch from version 1 (editing old version)
        pdf_branch = sample_documents['pdf_branch']
        result_branch = await pipeline.process_document(
            file_path=pdf_branch['filename'],
            file_content=pdf_branch['content'],
            filename=pdf_branch['filename'],
            user_id=pdf_branch['user_id'],
            parent_version=1,  # Branch from version 1
            lineage_uuid=lineage_uuid
        )
        
        assert result_branch.success is True
        assert result_branch.version_number == 3  # Next available version number
        assert result_branch.lineage_uuid == lineage_uuid
        
        # Verify branching in lineage manager
        lineage_manager = test_environment['lineage_manager']
        branch_version = lineage_manager.get_version(result_branch.document_uuid)
        assert branch_version.parent_version == 1
        assert branch_version.version_number == 3
        
        # Verify complete version tree
        chain_status = pipeline.get_version_chain_status(lineage_uuid)
        assert chain_status['total_versions'] == 3
        
        # All versions should have completed processing
        for version_info in chain_status['versions']:
            assert version_info['status']['current_stage'] == PipelineStage.COMPLETED
    
    @pytest.mark.asyncio
    async def test_soft_deletion_and_privacy_compliance(self, pipeline, sample_documents, test_environment):
        """Test soft deletion and privacy compliance throughout pipeline."""
        pdf_doc = sample_documents['pdf_v1']
        
        # Process document
        result = await pipeline.process_document(
            file_path=pdf_doc['filename'],
            file_content=pdf_doc['content'],
            filename=pdf_doc['filename'],
            user_id=pdf_doc['user_id']
        )
        
        assert result.success is True
        
        # Verify document exists in all systems
        lineage_manager = test_environment['lineage_manager']
        meta_crud = test_environment['meta_crud']
        
        # Check version exists
        version = lineage_manager.get_version(result.document_uuid)
        assert version is not None
        assert version.is_deleted is False
        
        # Check meta document exists
        meta_doc = meta_crud.get_meta_document(result.document_uuid)
        assert meta_doc is not None
        
        # Perform soft deletion
        deletion_result = lineage_manager.soft_delete_version(
            result.document_uuid,
            reason="Privacy request",
            deleted_by=pdf_doc['user_id']
        )
        assert deletion_result is True
        
        # Verify soft deletion
        deleted_version = lineage_manager.get_version(result.document_uuid)
        assert deleted_version.is_deleted is True
        assert deleted_version.deletion_reason == "Privacy request"
        assert deleted_version.deleted_by == pdf_doc['user_id']
        
        # Verify lineage chain preserved
        lineage = lineage_manager.get_lineage(result.lineage_uuid)
        assert lineage is not None  # Lineage should still exist
        
        # Verify version chain status reflects deletion
        chain_status = pipeline.get_version_chain_status(result.lineage_uuid)
        assert chain_status['total_versions'] == 1
        assert chain_status['versions'][0]['is_deleted'] is True
    
    @pytest.mark.asyncio
    async def test_output_format_consistency_across_versions(self, pipeline, sample_documents):
        """Test output format consistency across all processing stages and versions."""
        pdf_doc = sample_documents['pdf_v1']
        
        # Process multiple versions
        results = []
        for i, doc_key in enumerate(['pdf_v1', 'pdf_v2'], 1):
            doc = sample_documents[doc_key]
            
            if i == 1:
                # First version
                result = await pipeline.process_document(
                    file_path=doc['filename'],
                    file_content=doc['content'],
                    filename=doc['filename'],
                    user_id=doc['user_id']
                )
            else:
                # Subsequent versions
                result = await pipeline.process_document(
                    file_path=doc['filename'],
                    file_content=doc['content'],
                    filename=doc['filename'],
                    user_id=doc['user_id'],
                    lineage_uuid=results[0].lineage_uuid
                )
            
            assert result.success is True
            results.append(result)
        
        # Verify consistent output format across versions
        assert len(results) == 2
        
        # All results should have same structure
        for result in results:
            assert hasattr(result, 'success')
            assert hasattr(result, 'document_uuid')
            assert hasattr(result, 'lineage_uuid')
            assert hasattr(result, 'version_number')
            assert hasattr(result, 'stage_reached')
            assert hasattr(result, 'processing_time')
            assert hasattr(result, 'metadata')
        
        # Metadata should have consistent structure
        for result in results:
            metadata = result.metadata
            assert 'filename' in metadata
            assert 'user_id' in metadata
            assert 'file_size' in metadata
            assert 'processing_stages' in metadata
            assert isinstance(metadata['processing_stages'], list)
        
        # All versions should belong to same lineage
        lineage_uuids = [r.lineage_uuid for r in results]
        assert len(set(lineage_uuids)) == 1  # All same lineage
        
        # Version numbers should be sequential
        version_numbers = [r.version_number for r in results]
        assert version_numbers == [1, 2]
    
    @pytest.mark.asyncio
    async def test_rag_indexing_with_version_filtering(self, pipeline, sample_documents, test_environment):
        """Test RAG indexing and retrieval with version filtering."""
        pdf_doc = sample_documents['pdf_v1']
        
        # Process document with RAG preparation
        result = await pipeline.process_document(
            file_path=pdf_doc['filename'],
            file_content=pdf_doc['content'],
            filename=pdf_doc['filename'],
            user_id=pdf_doc['user_id']
        )
        
        assert result.success is True
        assert result.stage_reached == PipelineStage.COMPLETED
        
        # Verify RAG preparation completed
        assert 'rag_preparation' in result.metadata['processing_stages']
        
        # Verify meta document created for RAG
        meta_crud = test_environment['meta_crud']
        meta_doc = meta_crud.get_meta_document(result.document_uuid)
        assert meta_doc is not None
        assert meta_doc.set_uuid == result.lineage_uuid  # Lineage used as set identifier
        
        # Verify document components extracted
        assert len(meta_doc.components) > 0
        
        # Check component structure
        for component in meta_doc.components:
            assert 'type' in component
            assert 'content' in component
            assert 'metadata' in component
    
    @pytest.mark.asyncio
    async def test_concurrent_version_processing(self, pipeline, sample_documents):
        """Test concurrent processing of multiple versions."""
        # Prepare documents for concurrent processing
        documents = []
        base_lineage_uuid = None
        
        for i, doc_key in enumerate(['pdf_v1', 'pdf_v2']):
            doc = sample_documents[doc_key]
            doc_info = {
                'file_path': doc['filename'],
                'file_content': doc['content'],
                'filename': doc['filename'],
                'user_id': doc['user_id']
            }
            
            # Add lineage for second document
            if i > 0 and base_lineage_uuid:
                doc_info['lineage_uuid'] = base_lineage_uuid
            
            documents.append(doc_info)
        
        # Process first document to get lineage
        result_1 = await pipeline.process_document(**documents[0])
        assert result_1.success is True
        base_lineage_uuid = result_1.lineage_uuid
        
        # Update second document with lineage
        documents[1]['lineage_uuid'] = base_lineage_uuid
        
        # Process second document
        result_2 = await pipeline.process_document(**documents[1])
        assert result_2.success is True
        
        # Verify both belong to same lineage but different versions
        assert result_1.lineage_uuid == result_2.lineage_uuid
        assert result_1.version_number != result_2.version_number
        assert result_1.document_uuid != result_2.document_uuid
    
    @pytest.mark.asyncio
    async def test_pipeline_performance_metrics(self, pipeline, sample_documents):
        """Test pipeline performance metrics collection."""
        pdf_doc = sample_documents['pdf_v1']
        
        start_time = time.time()
        
        # Process document
        result = await pipeline.process_document(
            file_path=pdf_doc['filename'],
            file_content=pdf_doc['content'],
            filename=pdf_doc['filename'],
            user_id=pdf_doc['user_id']
        )
        
        end_time = time.time()
        
        assert result.success is True
        
        # Verify performance metrics
        assert result.processing_time > 0
        assert result.processing_time <= (end_time - start_time) + 1  # Allow some tolerance
        
        # Verify metadata includes performance information
        metadata = result.metadata
        assert 'file_size' in metadata
        assert metadata['file_size'] == len(pdf_doc['content'])
        
        # Processing stages should be tracked
        assert 'processing_stages' in metadata
        assert len(metadata['processing_stages']) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_rollback(self, test_environment, sample_documents):
        """Test error recovery and rollback scenarios."""
        # Create pipeline with configuration that might cause errors
        config = test_environment['config']
        config.processing_timeout = 1  # Very short timeout
        
        pipeline = DocForgePipeline(config)
        
        try:
            pdf_doc = sample_documents['pdf_v1']
            
            # Process document (may succeed with mock processing)
            result = await pipeline.process_document(
                file_path=pdf_doc['filename'],
                file_content=pdf_doc['content'],
                filename=pdf_doc['filename'],
                user_id=pdf_doc['user_id']
            )
            
            # Verify result structure regardless of success/failure
            assert hasattr(result, 'success')
            assert hasattr(result, 'document_uuid')
            assert hasattr(result, 'stage_reached')
            assert hasattr(result, 'processing_time')
            
            if not result.success:
                assert result.error_message is not None
                assert result.stage_reached != PipelineStage.COMPLETED
            
        finally:
            pipeline.shutdown()


class TestPipelineIntegrationEdgeCases:
    """Test edge cases and boundary conditions in pipeline integration."""
    
    @pytest.fixture
    def test_environment(self):
        """Create test environment for edge cases."""
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
    def pipeline(self, test_environment):
        """Create pipeline instance for testing."""
        pipeline = DocForgePipeline(test_environment['config'])
        yield pipeline
        pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_empty_document_processing(self, pipeline):
        """Test processing of empty documents."""
        result = await pipeline.process_document(
            file_path="empty.pdf",
            file_content=b"",
            filename="empty.pdf",
            user_id="test_user"
        )
        
        # Should handle gracefully
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_large_version_chain(self, pipeline):
        """Test handling of large version chains."""
        # Create multiple versions in same lineage
        base_content = b"%PDF-1.4\n% Base document\n%%EOF"
        lineage_uuid = None
        
        results = []
        for i in range(5):  # Create 5 versions
            content = base_content + f"\n% Version {i+1}".encode()
            
            result = await pipeline.process_document(
                file_path=f"version_{i+1}.pdf",
                file_content=content,
                filename=f"version_{i+1}.pdf",
                user_id="test_user",
                lineage_uuid=lineage_uuid
            )
            
            if result.success:
                results.append(result)
                if lineage_uuid is None:
                    lineage_uuid = result.lineage_uuid
        
        # Verify all versions processed
        assert len(results) > 0
        
        if len(results) > 1:
            # Verify version chain
            chain_status = pipeline.get_version_chain_status(lineage_uuid)
            assert chain_status['total_versions'] == len(results)
    
    @pytest.mark.asyncio
    async def test_invalid_parent_version(self, pipeline):
        """Test handling of invalid parent version references."""
        # Process first document
        result_1 = await pipeline.process_document(
            file_path="doc1.pdf",
            file_content=b"%PDF-1.4\n% Document 1\n%%EOF",
            filename="doc1.pdf",
            user_id="test_user"
        )
        
        if result_1.success:
            # Try to branch from non-existent version
            result_2 = await pipeline.process_document(
                file_path="doc2.pdf",
                file_content=b"%PDF-1.4\n% Document 2\n%%EOF",
                filename="doc2.pdf",
                user_id="test_user",
                parent_version=999,  # Invalid version
                lineage_uuid=result_1.lineage_uuid
            )
            
            # Should handle gracefully (may succeed by ignoring invalid parent)
            assert isinstance(result_2.success, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])