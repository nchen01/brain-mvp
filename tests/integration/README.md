# RAG Integration Tests

This directory contains comprehensive integration tests for the Meta Document and RAG system. These tests verify the complete pipeline from document processing to RAG-ready retrieval.

## Test Suites

### 1. Meta Document and RAG Integration (`test_meta_document_rag_integration.py`)

Tests the complete integration between meta document storage and RAG preparation:

- **TestMetaDocumentStorage**: Meta document creation, storage, and retrieval
- **TestRAGDatabasePreparation**: RAG-optimized chunking, semantic indexing, and knowledge graph building
- **TestLightRAGIntegration**: LightRAG indexing and retrieval functionality
- **TestEndToEndPipeline**: Complete pipeline from document storage to RAG retrieval
- **TestSystemIntegration**: System-level integration scenarios and monitoring

### 2. Vector Embedding Integration (`test_vector_embedding_integration.py`)

Focuses specifically on vector embedding generation and storage:

- **TestEmbeddingGeneration**: Vector embedding creation for different content types
- **TestSimilarityCalculations**: Cosine similarity and semantic relationships
- **TestSemanticClustering**: Clustering of semantically similar content
- **TestLightRAGVectorIntegration**: Integration with LightRAG vector database
- **TestEmbeddingPerformance**: Performance benchmarks for embedding operations
- **TestEmbeddingAccuracy**: Quality and accuracy validation of embeddings

### 3. Complete RAG Pipeline (`test_complete_rag_pipeline.py`)

End-to-end testing of the entire RAG pipeline:

- **TestCompleteRAGPipeline**: Full pipeline from document registration to retrieval
- **TestSystemIntegration**: Concurrent processing and system statistics
- Document versioning and lineage integration
- Performance benchmarking and error recovery

## Key Features Tested

### Document Processing Pipeline
- ✅ Document registration and versioning
- ✅ Content processing and post-processing
- ✅ Meta document creation and storage
- ✅ Component integrity and metadata preservation

### RAG Database Preparation
- ✅ RAG-optimized chunking strategies
- ✅ Semantic indexing and clustering
- ✅ Document relationship mapping
- ✅ Knowledge graph creation
- ✅ Vector embedding generation

### LightRAG Integration
- ✅ Document indexing in LightRAG
- ✅ Vector storage and retrieval
- ✅ Query processing and results
- ✅ Performance optimization

### System Integration
- ✅ End-to-end pipeline execution
- ✅ Error handling and recovery
- ✅ Concurrent document processing
- ✅ System statistics and monitoring
- ✅ Performance benchmarking

## Running the Tests

### Individual Test Suites

```bash
# Run meta document and RAG integration tests
python -m pytest tests/integration/test_meta_document_rag_integration.py -v

# Run vector embedding integration tests
python -m pytest tests/integration/test_vector_embedding_integration.py -v

# Run complete pipeline tests
python -m pytest tests/integration/test_complete_rag_pipeline.py -v
```

### All Integration Tests

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/integration/ --cov=src --cov-report=html
```

### Using the Test Runner

```bash
# Run comprehensive test suite with reporting
python tests/integration/run_rag_integration_tests.py --verbose

# Quick tests (skip performance benchmarks)
python tests/integration/run_rag_integration_tests.py --quick

# Check dependencies only
python tests/integration/run_rag_integration_tests.py --check-deps
```

## Demo and Examples

### Integration Demo

```bash
# Run interactive demo
python examples/run_rag_integration_demo.py
```

This demo shows:
- Meta document storage and retrieval
- Vector embedding generation
- Similarity calculations
- RAG database preparation
- LightRAG integration
- System statistics

## Test Environment

### Dependencies

The integration tests require:
- `pytest` and `pytest-asyncio`
- `sentence-transformers` for embeddings
- `lightrag` for vector database
- `numpy` for numerical operations
- All project dependencies

### Temporary Resources

Tests use temporary directories and databases:
- SQLite databases for meta document storage
- Temporary directories for LightRAG working files
- Embedding cache directories
- Automatic cleanup after test completion

### Performance Considerations

- Tests download embedding models on first run
- LightRAG initialization may take time
- Performance tests have reasonable timeout limits
- Concurrent tests are limited to prevent resource exhaustion

## Test Data

### Sample Documents

Tests use realistic sample documents covering:
- **AI Research Papers**: Technical content with abstracts and methodology
- **Machine Learning Tutorials**: Educational content with structured sections
- **AI Ethics Papers**: Policy analysis with complex arguments

### Document Components

Each test document includes:
- Title and abstract components
- Multiple content chunks
- Summary components
- Processing history
- Metadata and confidence scores

## Expected Results

### Performance Benchmarks

Typical performance expectations:
- Document storage: < 1 second per document
- RAG preparation: < 30 seconds per document
- LightRAG indexing: < 20 seconds per document
- Query execution: < 10 seconds per query

### Quality Metrics

- Embedding similarity for related content: > 0.7
- Same text consistency: > 0.999
- Cross-document relationship detection: Variable based on content
- Knowledge graph node/edge creation: Proportional to document complexity

## Troubleshooting

### Common Issues

1. **Model Download Failures**
   - Ensure internet connectivity
   - Check sentence-transformers installation
   - Verify disk space for model cache

2. **Database Errors**
   - Check write permissions in test directories
   - Ensure SQLite is properly installed
   - Verify temporary directory cleanup

3. **Memory Issues**
   - Reduce batch sizes in test configurations
   - Run tests individually if system resources are limited
   - Monitor memory usage during embedding generation

4. **Timeout Errors**
   - Increase timeout limits for slower systems
   - Use `--quick` flag to skip performance benchmarks
   - Check system load during test execution

### Debug Mode

Run tests with additional debugging:

```bash
# Verbose output with debug information
python -m pytest tests/integration/ -v -s --tb=long

# Run specific test with debugging
python -m pytest tests/integration/test_meta_document_rag_integration.py::TestMetaDocumentStorage::test_meta_document_creation_and_storage -v -s
```

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate fixtures for setup and teardown
3. Include both positive and negative test cases
4. Add performance considerations for resource-intensive tests
5. Update this README with new test descriptions
6. Ensure tests are deterministic and don't depend on external services

## Requirements Coverage

These integration tests satisfy the following requirements:

- **Requirement 1.1**: Document processing and storage pipeline
- **Requirement 2.2**: Meta document creation and management
- **Requirement 5.3**: RAG system for intelligent document retrieval
- **Requirement 7.1**: System integration and error handling

The tests provide comprehensive validation of the complete RAG system from document ingestion to intelligent retrieval.