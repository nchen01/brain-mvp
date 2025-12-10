"""
Helper method for pipeline.py to chunk and store documents.

Add this method to the DocForgePipeline class in pipeline.py
"""

async def _chunk_and_store_document(
    self,
    document_uuid: str,
    lineage_uuid: str,
    version_number: int,
    processed_document
) -> Dict[str, Any]:
    """Chunk document and store chunks in database.
    
    Args:
        document_uuid: Document UUID
        lineage_uuid: Lineage UUID
        version_number: Version number
        processed_document: Processed document output
        
    Returns:
        Result dictionary with success status
    """
    try:
        import os
        from docforge.postprocessing.chunker import DocumentChunker
        from docforge.postprocessing.schemas import ChunkingStrategy
        from storage.chunk_storage import ChunkStorage
        
        # Get chunking strategy from config
        strategy_name = getattr(self.config, 'default_chunking_strategy', 'recursive')
        try:
            strategy = ChunkingStrategy[strategy_name.upper()]
        except KeyError:
            storage_logger.warning(f"Unknown strategy {strategy_name}, using RECURSIVE")
            strategy = ChunkingStrategy.RECURSIVE
        
        # Build chunker config
        chunker_config = {
            'chunk_size': getattr(self.config, 'default_chunk_size', 800),
            'chunk_overlap': getattr(self.config, 'chunk_overlap', 100),
            'min_chunk_size': getattr(self.config, 'min_chunk_size', 30),
        }
        
        # Add enrichment if enabled
        if getattr(self.config, 'enable_context_enrichment', False):
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                chunker_config.update({
                    'enrich_contexts': True,
                    'openai_api_key': api_key,
                    'context_model': getattr(self.config, 'context_enrichment_model', 'gpt-3.5-turbo'),
                    'context_prompt_style': getattr(self.config, 'context_enrichment_prompt_style', 'default'),
                    'context_max_words': getattr(self.config, 'context_enrichment_max_words', 100),
                    'context_temperature': getattr(self.config, 'context_enrichment_temperature', 0.3),
                })
        
        # Create chunker and chunk document
        chunker = DocumentChunker(strategy=strategy, config=chunker_config)
        chunks = chunker.chunk_document(processed_document)
        
        storage_logger.info(f"Created {len(chunks)} chunks for document {document_uuid}")
        
        # Enrich chunks if configured
        if chunker_config.get('enrich_contexts'):
            enriched_chunks = chunker.enrich_chunks_with_context(
                chunks=chunks,
                full_document_text=processed_document.plain_text,
                document_metadata={
                    'doc_uuid': document_uuid,
                    'lineage_uuid': lineage_uuid,
                    'version': version_number
                }
            )
            chunks = enriched_chunks
            storage_logger.info(f"Enriched chunks for document {document_uuid}")
        
        # Convert ChunkData objects to dicts for storage
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'content': chunk.content,
                'metadata': {
                    'word_count': chunk.metadata.word_count,
                    'character_count': chunk.metadata.character_count,
                    'chunk_type': chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type),
                },
                'relationships': chunk.relationships
            }
            
            # Add enriched content if present
            if hasattr(chunk, 'enriched_content') and chunk.enriched_content:
                chunk_dict['enriched_content'] = chunk.enriched_content
            
            # Add original content if stored in metadata
            if hasattr(chunk.metadata, 'original_content') and chunk.metadata.original_content:
                chunk_dict['metadata']['original_content'] = chunk.metadata.original_content
            
            if hasattr(chunk.metadata, 'enriched'):
                chunk_dict['enrichment_metadata'] = {'enriched': chunk.metadata.enriched}
            
            chunk_dicts.append(chunk_dict)
        
        # Store chunks in database
        storage = ChunkStorage()
        chunk_ids = storage.store_chunks(
            doc_uuid=document_uuid,
            lineage_uuid=lineage_uuid,
            version_number=version_number,
            chunks=chunk_dicts,
            chunking_strategy=strategy_name
        )
        
        storage_logger.info(f"Stored {len(chunk_ids)} chunks for document {document_uuid}")
        
        return {
            'success': True,
            'chunk_count': len(chunk_ids),
            'chunk_ids': chunk_ids,
            'strategy': strategy_name
        }
        
    except Exception as e:
        error_msg = f"Chunking failed: {str(e)}"
        storage_logger.error(f"Error chunking document {document_uuid}: {e}", exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }
