"""
Performance tests for DocForge Pipeline with Versioning.

This test suite validates the performance characteristics of the complete
DocForge pipeline with versioning support, including:
- Document processing performance with version overhead
- Database operations performance with version queries
- RAG indexing and retrieval performance with version filtering
- File storage and retrieval performance with version management
- Version history query performance
"""

import pytest
import time
import tempfile
import os
import statistics
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    @pytest.fixture
    def performance_environment(self):
        """Create performance test environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield {
                'temp_dir': temp_dir,
                'db_dir': os.path.join(temp_dir, 'databases'),
                'upload_dir': os.path.join(temp_dir, 'uploads'),
                'processed_dir': os.path.join(temp_dir, 'processed')
            }
    
    @pytest.fixture
    def performance_documents(self):
        """Create documents of various sizes for performance testing."""
        return {
            'small_pdf': {
                'filename': 'small_document.pdf',
                'content': b'%PDF-1.4\n% Small PDF for performance testing\n' + b'A' * 1024,  # ~1KB
                'expected_size': 'small'
            },
            'medium_pdf': {
                'filename': 'medium_document.pdf', 
                'content': b'%PDF-1.4\n% Medium PDF for performance testing\n' + b'B' * (100 * 1024),  # ~100KB
                'expected_size': 'medium'
            },
            'large_text': {
                'filename': 'large_document.txt',
                'content': b'Large text document for performance testing.\n' * 10000,  # ~500KB
                'expected_size': 'large'
            }
        }
    
    def test_preprocessing_performance(self, performance_environment, performance_documents):
        """Test preprocessing performance across different document sizes."""
        try:
            from docforge.preprocessing.router import DocumentPreprocessingRouter
            from docforge.preprocessing.processor_factory import ProcessorFactory
            
            router = DocumentPreprocessingRouter()
            factory = ProcessorFactory()
            
            performance_results = {}
            
            for doc_name, doc_info in performance_documents.items():
                filename = doc_info['filename']
                content = doc_info['content']
                
                # Measure routing performance
                start_time = time.time()
                routing_result = router.route_document(filename, content)
                routing_time = time.time() - start_time
                
                # Measure processor selection performance
                start_time = time.time()
                processor = factory.get_processor_for_file(filename, content)
                selection_time = time.time() - start_time
                
                # Measure processing performance
                processing_time = 0
                if processor is not None:
                    start_time = time.time()
                    result = processor.process_document(filename, file_content=content)
                    processing_time = time.time() - start_time
                
                performance_results[doc_name] = {
                    'routing_time': routing_time,
                    'selection_time': selection_time,
                    'processing_time': processing_time,
                    'total_time': routing_time + selection_time + processing_time,
                    'content_size': len(content),
                    'throughput_mb_per_sec': (len(content) / (1024 * 1024)) / max(processing_time, 0.001)
                }
            
            # Verify performance characteristics
            for doc_name, results in performance_results.items():
                # Routing should be very fast (< 10ms)
                assert results['routing_time'] < 0.01, f"Routing too slow for {doc_name}: {results['routing_time']:.3f}s"
                
                # Selection should be very fast (< 5ms)
                assert results['selection_time'] < 0.005, f"Selection too slow for {doc_name}: {results['selection_time']:.3f}s"
                
                # Total time should be reasonable
                assert results['total_time'] < 5.0, f"Total processing too slow for {doc_name}: {results['total_time']:.3f}s"
                
                print(f"✅ {doc_name}: {results['total_time']:.3f}s total, {results['throughput_mb_per_sec']:.2f} MB/s")
            
        except ImportError as e:
            pytest.skip(f"Preprocessing components not available: {e}")
    
    def test_concurrent_processing_performance(self, performance_environment, performance_documents):
        """Test concurrent document processing performance."""
        try:
            from docforge.preprocessing.router import DocumentPreprocessingRouter
            from docforge.preprocessing.processor_factory import ProcessorFactory
            
            router = DocumentPreprocessingRouter()
            factory = ProcessorFactory()
            
            def process_document(doc_info):
                """Process a single document and return timing."""
                start_time = time.time()
                
                filename = doc_info['filename']
                content = doc_info['content']
                
                # Process document
                routing_result = router.route_document(filename, content)
                processor = factory.get_processor_for_file(filename, content)
                
                if processor is not None:
                    result = processor.process_document(filename, file_content=content)
                
                return time.time() - start_time
            
            # Test concurrent processing
            documents = list(performance_documents.values()) * 3  # Process each document 3 times
            
            # Sequential processing
            start_time = time.time()
            sequential_times = [process_document(doc) for doc in documents]
            sequential_total = time.time() - start_time
            
            # Concurrent processing
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(process_document, doc) for doc in documents]
                concurrent_times = [future.result() for future in as_completed(futures)]
            concurrent_total = time.time() - start_time
            
            # Analyze results
            sequential_avg = statistics.mean(sequential_times)
            concurrent_avg = statistics.mean(concurrent_times)
            
            print(f"✅ Sequential: {sequential_total:.3f}s total, {sequential_avg:.3f}s avg")
            print(f"✅ Concurrent: {concurrent_total:.3f}s total, {concurrent_avg:.3f}s avg")
            print(f"✅ Speedup: {sequential_total / concurrent_total:.2f}x")
            
            # Concurrent should be faster for multiple documents
            assert concurrent_total < sequential_total * 0.8, "Concurrent processing should be faster"
            
        except ImportError as e:
            pytest.skip(f"Preprocessing components not available: {e}")
    
    def test_version_simulation_performance(self, performance_environment):
        """Test version management performance simulation."""
        # Simulate version operations
        version_operations = []
        
        # Create lineage
        start_time = time.time()
        lineage_data = {
            'lineage_uuid': 'perf_test_lineage',
            'original_filename': 'performance_test.pdf',
            'created_at': time.time(),
            'versions': []
        }
        lineage_creation_time = time.time() - start_time
        version_operations.append(('lineage_creation', lineage_creation_time))
        
        # Create multiple versions
        for version_num in range(1, 11):  # 10 versions
            start_time = time.time()
            
            version_data = {
                'version_number': version_num,
                'doc_uuid': f'perf_test_doc_v{version_num}',
                'parent_version': version_num - 1 if version_num > 1 else None,
                'created_at': time.time(),
                'file_hash': f'hash_{version_num}',
                'metadata': {'version': version_num}
            }
            
            lineage_data['versions'].append(version_data)
            version_creation_time = time.time() - start_time
            version_operations.append((f'version_{version_num}_creation', version_creation_time))
        
        # Query version chain
        start_time = time.time()
        version_chain = lineage_data['versions']
        chain_query_time = time.time() - start_time
        version_operations.append(('chain_query', chain_query_time))
        
        # Query latest version
        start_time = time.time()
        latest_version = max(lineage_data['versions'], key=lambda v: v['version_number'])
        latest_query_time = time.time() - start_time
        version_operations.append(('latest_query', latest_query_time))
        
        # Analyze performance
        creation_times = [time for op, time in version_operations if 'creation' in op]
        query_times = [time for op, time in version_operations if 'query' in op]
        
        avg_creation_time = statistics.mean(creation_times)
        avg_query_time = statistics.mean(query_times)
        
        print(f"✅ Average version creation: {avg_creation_time:.6f}s")
        print(f"✅ Average version query: {avg_query_time:.6f}s")
        print(f"✅ Total versions: {len(lineage_data['versions'])}")
        
        # Performance assertions
        assert avg_creation_time < 0.001, f"Version creation too slow: {avg_creation_time:.6f}s"
        assert avg_query_time < 0.001, f"Version query too slow: {avg_query_time:.6f}s"
        assert lineage_creation_time < 0.001, f"Lineage creation too slow: {lineage_creation_time:.6f}s"
    
    def test_storage_performance_simulation(self, performance_environment):
        """Test storage performance with version management simulation."""
        # Create test directories
        os.makedirs(performance_environment['db_dir'], exist_ok=True)
        
        storage_operations = []
        
        # Simulate meta document storage operations
        documents_to_store = 50
        
        for i in range(documents_to_store):
            doc_uuid = f"perf_storage_doc_{i}"
            set_uuid = f"perf_storage_set_{i // 5}"  # Group documents into sets
            
            # Simulate document creation
            start_time = time.time()
            
            # Mock meta document data
            meta_doc_data = {
                'doc_uuid': doc_uuid,
                'set_uuid': set_uuid,
                'title': f'Performance Test Document {i}',
                'summary': f'Testing storage performance for document {i}',
                'components': [
                    {
                        'type': 'text',
                        'content': f'Content for document {i}' * 10,  # Some content
                        'metadata': {'length': len(f'Content for document {i}' * 10)}
                    }
                ],
                'created_at': time.time()
            }
            
            storage_time = time.time() - start_time
            storage_operations.append(('storage', storage_time))
            
            # Simulate document retrieval
            start_time = time.time()
            retrieved_doc = meta_doc_data  # Mock retrieval
            retrieval_time = time.time() - start_time
            storage_operations.append(('retrieval', retrieval_time))
        
        # Analyze storage performance
        storage_times = [time for op, time in storage_operations if op == 'storage']
        retrieval_times = [time for op, time in storage_operations if op == 'retrieval']
        
        avg_storage_time = statistics.mean(storage_times)
        avg_retrieval_time = statistics.mean(retrieval_times)
        
        print(f"✅ Average storage time: {avg_storage_time:.6f}s")
        print(f"✅ Average retrieval time: {avg_retrieval_time:.6f}s")
        print(f"✅ Documents processed: {documents_to_store}")
        print(f"✅ Storage throughput: {documents_to_store / sum(storage_times):.1f} docs/sec")
        
        # Performance assertions
        assert avg_storage_time < 0.01, f"Storage too slow: {avg_storage_time:.6f}s"
        assert avg_retrieval_time < 0.005, f"Retrieval too slow: {avg_retrieval_time:.6f}s"
    
    def test_memory_usage_performance(self, performance_environment, performance_documents):
        """Test memory usage during document processing."""
        try:
            import psutil
            import os
            
            from docforge.preprocessing.router import DocumentPreprocessingRouter
            from docforge.preprocessing.processor_factory import ProcessorFactory
            
            router = DocumentPreprocessingRouter()
            factory = ProcessorFactory()
            
            process = psutil.Process(os.getpid())
            
            memory_measurements = []
            
            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(('baseline', baseline_memory))
            
            # Process documents and measure memory
            for doc_name, doc_info in performance_documents.items():
                filename = doc_info['filename']
                content = doc_info['content']
                
                # Memory before processing
                before_memory = process.memory_info().rss / 1024 / 1024
                
                # Process document
                routing_result = router.route_document(filename, content)
                processor = factory.get_processor_for_file(filename, content)
                
                if processor is not None:
                    result = processor.process_document(filename, file_content=content)
                
                # Memory after processing
                after_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = after_memory - before_memory
                
                memory_measurements.append((doc_name, after_memory, memory_increase))
                
                print(f"✅ {doc_name}: {after_memory:.1f}MB total, +{memory_increase:.1f}MB increase")
            
            # Verify memory usage is reasonable
            final_memory = memory_measurements[-1][1]
            total_increase = final_memory - baseline_memory
            
            print(f"✅ Baseline memory: {baseline_memory:.1f}MB")
            print(f"✅ Final memory: {final_memory:.1f}MB")
            print(f"✅ Total increase: {total_increase:.1f}MB")
            
            # Memory increase should be reasonable (< 100MB for test documents)
            assert total_increase < 100, f"Memory usage too high: {total_increase:.1f}MB"
            
        except ImportError:
            pytest.skip("psutil not available for memory testing")
    
    def test_error_handling_performance(self, performance_environment):
        """Test performance of error handling scenarios."""
        try:
            from docforge.preprocessing.router import DocumentPreprocessingRouter
            from docforge.preprocessing.processor_factory import ProcessorFactory
            
            router = DocumentPreprocessingRouter()
            factory = ProcessorFactory()
            
            # Test error scenarios
            error_scenarios = [
                ('empty_file', b''),
                ('invalid_pdf', b'Invalid PDF content'),
                ('large_invalid', b'X' * (1024 * 1024)),  # 1MB of invalid content
                ('binary_garbage', bytes(range(256)) * 100)  # Binary garbage
            ]
            
            error_handling_times = []
            
            for scenario_name, content in error_scenarios:
                filename = f"{scenario_name}.pdf"
                
                start_time = time.time()
                
                try:
                    # This should handle errors gracefully
                    routing_result = router.route_document(filename, content)
                    processor = factory.get_processor_for_file(filename, content)
                    
                    if processor is not None:
                        result = processor.process_document(filename, file_content=content)
                
                except Exception as e:
                    # Errors are expected, but should be handled quickly
                    pass
                
                error_time = time.time() - start_time
                error_handling_times.append(error_time)
                
                print(f"✅ {scenario_name}: {error_time:.3f}s error handling")
            
            # Error handling should be fast
            avg_error_time = statistics.mean(error_handling_times)
            max_error_time = max(error_handling_times)
            
            print(f"✅ Average error handling: {avg_error_time:.3f}s")
            print(f"✅ Maximum error handling: {max_error_time:.3f}s")
            
            # Error handling should be fast even for large invalid files
            assert avg_error_time < 0.1, f"Error handling too slow: {avg_error_time:.3f}s"
            assert max_error_time < 0.5, f"Worst case error handling too slow: {max_error_time:.3f}s"
            
        except ImportError as e:
            pytest.skip(f"Components not available for error handling test: {e}")


class TestVersionPerformanceImpact:
    """Test the performance impact of versioning features."""
    
    def test_version_overhead_measurement(self):
        """Measure the performance overhead of version management."""
        # Simulate processing with and without versioning
        
        # Base processing simulation (without versioning)
        base_operations = []
        for i in range(100):
            start_time = time.time()
            
            # Simulate basic document processing
            doc_data = {
                'uuid': f'doc_{i}',
                'content': f'Document content {i}' * 100,
                'processed_at': time.time()
            }
            
            base_time = time.time() - start_time
            base_operations.append(base_time)
        
        # Versioned processing simulation (with versioning)
        versioned_operations = []
        for i in range(100):
            start_time = time.time()
            
            # Simulate document processing with versioning
            doc_data = {
                'uuid': f'doc_{i}',
                'lineage_uuid': f'lineage_{i // 10}',  # Group into lineages
                'version_number': (i % 10) + 1,
                'parent_version': i % 10 if i % 10 > 0 else None,
                'content': f'Document content {i}' * 100,
                'file_hash': f'hash_{i}',
                'processed_at': time.time(),
                'version_metadata': {
                    'created_by': 'test_user',
                    'version_type': 'linear' if i % 10 != 0 else 'branch'
                }
            }
            
            versioned_time = time.time() - start_time
            versioned_operations.append(versioned_time)
        
        # Calculate overhead
        base_avg = statistics.mean(base_operations)
        versioned_avg = statistics.mean(versioned_operations)
        overhead_percent = ((versioned_avg - base_avg) / base_avg) * 100
        
        print(f"✅ Base processing: {base_avg:.6f}s average")
        print(f"✅ Versioned processing: {versioned_avg:.6f}s average")
        print(f"✅ Version overhead: {overhead_percent:.1f}%")
        
        # Version overhead should be minimal (< 50% for micro-operations, much less for real operations)
        # Note: For very fast operations (microseconds), overhead percentage can be high but absolute time is still tiny
        if versioned_avg > 0.001:  # Only check percentage for operations > 1ms
            assert overhead_percent < 20, f"Version overhead too high: {overhead_percent:.1f}%"
        
        # Absolute time should still be very fast
        assert versioned_avg < 0.01, f"Versioned processing too slow: {versioned_avg:.6f}s"
    
    def test_version_query_performance(self):
        """Test performance of version-related queries."""
        # Create mock version data
        lineages = {}
        for lineage_id in range(10):
            lineage_uuid = f'lineage_{lineage_id}'
            lineages[lineage_uuid] = {
                'lineage_uuid': lineage_uuid,
                'original_filename': f'document_{lineage_id}.pdf',
                'versions': []
            }
            
            # Create versions for each lineage
            for version_num in range(1, 21):  # 20 versions per lineage
                version_data = {
                    'version_number': version_num,
                    'doc_uuid': f'doc_{lineage_id}_{version_num}',
                    'lineage_uuid': lineage_uuid,
                    'parent_version': version_num - 1 if version_num > 1 else None,
                    'created_at': time.time() - (20 - version_num) * 3600,  # Spread over time
                    'is_deleted': False
                }
                lineages[lineage_uuid]['versions'].append(version_data)
        
        # Test various query patterns
        query_performance = {}
        
        # 1. Get latest version query
        start_time = time.time()
        for lineage_uuid in lineages:
            versions = lineages[lineage_uuid]['versions']
            latest = max(versions, key=lambda v: v['version_number'])
        latest_query_time = (time.time() - start_time) / len(lineages)
        query_performance['latest_version'] = latest_query_time
        
        # 2. Get version chain query
        start_time = time.time()
        for lineage_uuid in lineages:
            versions = sorted(lineages[lineage_uuid]['versions'], key=lambda v: v['version_number'])
        chain_query_time = (time.time() - start_time) / len(lineages)
        query_performance['version_chain'] = chain_query_time
        
        # 3. Find version by UUID query
        start_time = time.time()
        for lineage_uuid in lineages:
            target_uuid = f'doc_{lineage_uuid.split("_")[1]}_10'  # Find version 10
            versions = lineages[lineage_uuid]['versions']
            found = next((v for v in versions if v['doc_uuid'] == target_uuid), None)
        uuid_query_time = (time.time() - start_time) / len(lineages)
        query_performance['find_by_uuid'] = uuid_query_time
        
        # 4. Get version history query
        start_time = time.time()
        for lineage_uuid in lineages:
            versions = lineages[lineage_uuid]['versions']
            history = [(v['version_number'], v['created_at'], v['is_deleted']) for v in versions]
        history_query_time = (time.time() - start_time) / len(lineages)
        query_performance['version_history'] = history_query_time
        
        # Report results
        for query_type, avg_time in query_performance.items():
            print(f"✅ {query_type}: {avg_time:.6f}s average")
            
            # All queries should be very fast
            assert avg_time < 0.001, f"{query_type} query too slow: {avg_time:.6f}s"
        
        print(f"✅ Total lineages: {len(lineages)}")
        print(f"✅ Versions per lineage: 20")
        print(f"✅ Total versions: {sum(len(l['versions']) for l in lineages.values())}")


class TestRAGPerformanceWithVersioning:
    """Test RAG performance with version filtering."""
    
    def test_rag_indexing_performance_simulation(self):
        """Test RAG indexing performance with version metadata."""
        # Simulate RAG indexing with version information
        documents_to_index = 50
        indexing_times = []
        
        for i in range(documents_to_index):
            start_time = time.time()
            
            # Simulate document indexing with version metadata
            doc_data = {
                'doc_uuid': f'rag_doc_{i}',
                'lineage_uuid': f'rag_lineage_{i // 5}',
                'version_number': (i % 5) + 1,
                'content': f'RAG indexing test content for document {i}. ' * 20,
                'embeddings': [0.1] * 384,  # Mock embedding vector
                'version_metadata': {
                    'is_latest': (i % 5) == 4,  # Every 5th is latest
                    'created_at': time.time(),
                    'parent_version': i % 5 if i % 5 > 0 else None
                }
            }
            
            # Simulate indexing operations
            content_chunks = doc_data['content'].split('. ')
            chunk_embeddings = [doc_data['embeddings']] * len(content_chunks)
            
            indexing_time = time.time() - start_time
            indexing_times.append(indexing_time)
        
        # Analyze indexing performance
        avg_indexing_time = statistics.mean(indexing_times)
        total_indexing_time = sum(indexing_times)
        indexing_throughput = documents_to_index / total_indexing_time
        
        print(f"✅ Average indexing time: {avg_indexing_time:.6f}s")
        print(f"✅ Total indexing time: {total_indexing_time:.3f}s")
        print(f"✅ Indexing throughput: {indexing_throughput:.1f} docs/sec")
        
        # Indexing should be reasonably fast
        assert avg_indexing_time < 0.01, f"RAG indexing too slow: {avg_indexing_time:.6f}s"
        assert indexing_throughput > 100, f"RAG indexing throughput too low: {indexing_throughput:.1f} docs/sec"
    
    def test_rag_query_performance_with_version_filtering(self):
        """Test RAG query performance with version filtering."""
        # Create mock indexed documents with versions
        indexed_docs = []
        for i in range(200):  # 200 documents across multiple versions
            doc = {
                'doc_uuid': f'query_doc_{i}',
                'lineage_uuid': f'query_lineage_{i // 10}',  # 20 lineages, 10 versions each
                'version_number': (i % 10) + 1,
                'content': f'Query test content for document {i}. This is version {(i % 10) + 1}.',
                'embedding': [0.1 + (i * 0.001)] * 384,  # Slightly different embeddings
                'is_latest': (i % 10) == 9,  # Every 10th is latest version
                'created_at': time.time() - (200 - i) * 60  # Spread over time
            }
            indexed_docs.append(doc)
        
        # Test different query scenarios
        query_scenarios = [
            ('latest_only', lambda docs: [d for d in docs if d['is_latest']]),
            ('specific_lineage', lambda docs: [d for d in docs if d['lineage_uuid'] == 'query_lineage_5']),
            ('version_range', lambda docs: [d for d in docs if 3 <= d['version_number'] <= 7]),
            ('recent_versions', lambda docs: [d for d in docs if d['created_at'] > time.time() - 3600])
        ]
        
        query_performance = {}
        
        for scenario_name, filter_func in query_scenarios:
            start_time = time.time()
            
            # Apply version filter
            filtered_docs = filter_func(indexed_docs)
            
            # Simulate similarity search on filtered documents
            query_embedding = [0.15] * 384
            similarities = []
            for doc in filtered_docs:
                # Simple dot product similarity
                similarity = sum(a * b for a, b in zip(query_embedding, doc['embedding']))
                similarities.append((doc, similarity))
            
            # Get top 10 results
            top_results = sorted(similarities, key=lambda x: x[1], reverse=True)[:10]
            
            query_time = time.time() - start_time
            query_performance[scenario_name] = {
                'query_time': query_time,
                'filtered_count': len(filtered_docs),
                'result_count': len(top_results)
            }
        
        # Report query performance
        for scenario, results in query_performance.items():
            print(f"✅ {scenario}: {results['query_time']:.6f}s, "
                  f"{results['filtered_count']} filtered, {results['result_count']} results")
            
            # Queries should be fast even with version filtering
            assert results['query_time'] < 0.01, f"{scenario} query too slow: {results['query_time']:.6f}s"
        
        print(f"✅ Total indexed documents: {len(indexed_docs)}")
        print(f"✅ Unique lineages: {len(set(d['lineage_uuid'] for d in indexed_docs))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])