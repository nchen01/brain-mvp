# System Testing Suite

This directory contains comprehensive system-level tests for the Brain MVP, validating the entire system from end-to-end with focus on integration, performance, monitoring, and operational readiness.

## Test Suites

### 1. End-to-End System Tests (`test_mvp_end_to_end.py`)

Comprehensive validation of the complete document lifecycle:

**Test Coverage:**
- ✅ Document Upload and Registration with Versioning
- ✅ Preprocessing Pipeline (MinerU, MarkItDown, Text Processing)
- ✅ Format Validation and Output Validation
- ✅ Post-processing Pipeline (Chunking, Abbreviation Expansion)
- ✅ Meta Document Creation and Storage
- ✅ RAG Database Preparation and Indexing
- ✅ LightRAG Integration and Retrieval
- ✅ Cross-document Functionality and Knowledge Graphs
- ✅ System Integration and Error Handling
- ✅ Performance Benchmarking

**Key Features:**
- Complete document lifecycle testing
- Real-world document processing scenarios
- Performance metrics collection
- Quality assessment and scoring
- System health validation
- Comprehensive error handling

### 2. System Monitoring Tests (`test_system_monitoring.py`)

Validation of system monitoring, observability, and operational readiness:

**Test Coverage:**
- ✅ Logging and Error Tracking
- ✅ Performance Monitoring and Metrics Collection
- ✅ Resource Usage Monitoring
- ✅ System Health Checks and Diagnostics
- ✅ Data Persistence and Recovery
- ✅ Operational Metrics Aggregation
- ✅ System State Recovery

**Key Features:**
- Structured logging validation
- Real-time performance monitoring
- Resource usage tracking
- Component health checks
- Data persistence verification
- Metrics export and reporting

### 3. System Test Runner (`run_mvp_system_tests.py`)

Comprehensive test orchestration and reporting system:

**Features:**
- ✅ Environment and Dependency Validation
- ✅ Unit Test Suite Execution
- ✅ Integration Test Suite Execution
- ✅ End-to-End System Testing
- ✅ Performance and Load Testing
- ✅ System Health Monitoring
- ✅ Comprehensive Reporting and Analysis
- ✅ Quality Assessment and Recommendations

## Running System Tests

### Quick System Test

```bash
# Run basic system validation
python tests/system/run_mvp_system_tests.py --quick

# Run with verbose output
python tests/system/run_mvp_system_tests.py --verbose
```

### Comprehensive System Test

```bash
# Run full system test suite
python tests/system/run_mvp_system_tests.py

# Run with strict validation (fail on any issues)
python tests/system/run_mvp_system_tests.py --strict
```

### Individual Test Suites

```bash
# Run end-to-end system tests only
python -m pytest tests/system/test_mvp_end_to_end.py -v

# Run system monitoring tests only
python -m pytest tests/system/test_system_monitoring.py -v

# Run all system tests
python -m pytest tests/system/ -v
```

### Selective Test Execution

```bash
# Skip unit tests (faster execution)
python tests/system/run_mvp_system_tests.py --skip-unit

# Skip integration tests
python tests/system/run_mvp_system_tests.py --skip-integration

# Skip performance tests
python tests/system/run_mvp_system_tests.py --skip-performance
```

## Test Environment Requirements

### System Requirements

- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM available
- **Disk Space**: Minimum 10GB free space
- **CPU**: Multi-core recommended for performance tests

### Dependencies

**Critical Dependencies:**
- `pytest` and `pytest-asyncio`
- `sentence-transformers`
- `lightrag`
- `numpy`, `pandas`
- `psutil` (for resource monitoring)
- `sqlite3` (built-in)

**Optional Dependencies:**
- `torch`, `transformers`
- `scikit-learn`
- `matplotlib`, `seaborn` (for visualization)

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
python tests/system/run_mvp_system_tests.py --check-deps
```

## Test Scenarios

### Document Processing Scenarios

The system tests use realistic document samples:

1. **Research Paper** (`ai_research_paper.txt`)
   - Academic paper with abstract, methodology, results
   - Complex technical content with citations
   - Multi-section structure with headings

2. **Technical Manual** (`ml_implementation_guide.md`)
   - Step-by-step implementation guide
   - Code examples and configuration files
   - Structured documentation format

3. **Policy Document** (`ai_ethics_policy.txt`)
   - Formal policy framework
   - Hierarchical structure with numbered sections
   - Compliance and governance content

### Performance Benchmarks

**Expected Performance Thresholds:**
- Document Registration: < 2 seconds
- Preprocessing: < 10 seconds per document
- Post-processing: < 15 seconds per document
- Meta Document Creation: < 5 seconds
- RAG Preparation: < 30 seconds per document
- LightRAG Indexing: < 20 seconds per document
- Query Execution: < 10 seconds per query

### Quality Metrics

**System Quality Assessment:**
- **Reliability Score**: Based on operation success rates
- **Performance Score**: Based on processing time thresholds
- **Integration Score**: Based on cross-component functionality
- **Overall Quality**: Weighted combination of all scores

**Health Status Levels:**
- **EXCELLENT**: 90-100% overall quality
- **GOOD**: 80-89% overall quality
- **FAIR**: 70-79% overall quality
- **NEEDS_IMPROVEMENT**: < 70% overall quality

## Monitoring and Observability

### System Metrics Collected

**Performance Metrics:**
- Operation durations (min, max, average)
- Success/failure rates
- Throughput measurements
- Response time percentiles

**Resource Metrics:**
- Memory usage (RSS, percentage)
- CPU utilization
- Open file descriptors
- Thread counts
- Disk space usage

**Error Metrics:**
- Error counts by type and component
- Error rates and trends
- First/last occurrence timestamps
- Error details and context

### Health Checks

**Component Health Checks:**
- Database connectivity and operations
- File system read/write capabilities
- Network connectivity (if applicable)
- Memory and disk space availability

**System Health Status:**
- **HEALTHY**: < 1% error rate
- **WARNING**: 1-5% error rate
- **CRITICAL**: > 5% error rate

### Logging and Tracing

**Log Levels and Categories:**
- **INFO**: Normal operations and milestones
- **WARNING**: Non-critical issues and degraded performance
- **ERROR**: Operation failures and exceptions
- **DEBUG**: Detailed diagnostic information

**Structured Logging:**
- JSON-formatted log entries
- Consistent field naming
- Correlation IDs for request tracing
- Performance timing information

## Test Reports and Analysis

### Automated Report Generation

The system test runner generates comprehensive reports including:

**Test Execution Summary:**
- Total modules and individual tests executed
- Success/failure rates and statistics
- Execution times and performance metrics

**Quality Assessment:**
- Component-level quality scores
- Overall system quality rating
- Performance benchmark comparisons

**System Health Analysis:**
- Resource usage patterns
- Error analysis and trends
- Component health status

**Recommendations:**
- Performance optimization suggestions
- Reliability improvement recommendations
- Operational readiness assessment

### Report Formats

**JSON Report** (`mvp_system_test_report_YYYYMMDD_HHMMSS.json`):
- Machine-readable format
- Complete test data and metrics
- Suitable for automated analysis

**Console Output**:
- Human-readable summary
- Key metrics and status indicators
- Actionable recommendations

**Log Files**:
- Detailed execution logs
- Error traces and diagnostics
- Performance timing data

## Troubleshooting

### Common Issues

1. **Model Download Failures**
   ```bash
   # Pre-download models
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
   ```

2. **Memory Issues**
   ```bash
   # Run with reduced batch sizes
   export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
   python tests/system/run_mvp_system_tests.py --quick
   ```

3. **Timeout Issues**
   ```bash
   # Run individual test suites
   python -m pytest tests/system/test_mvp_end_to_end.py::TestMVPEndToEndSystem::test_complete_document_lifecycle -v -s
   ```

4. **Database Lock Issues**
   ```bash
   # Clean up any existing test databases
   find . -name "*.db" -path "*/tmp*" -delete
   ```

### Debug Mode

```bash
# Run with maximum verbosity
python tests/system/run_mvp_system_tests.py --verbose

# Run specific test with debugging
python -m pytest tests/system/test_mvp_end_to_end.py -v -s --tb=long

# Enable debug logging
export PYTHONPATH=. && python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Run your test here
"
```

### Performance Debugging

```bash
# Profile memory usage
python -m memory_profiler tests/system/test_mvp_end_to_end.py

# Profile CPU usage
python -m cProfile -o profile_output.prof tests/system/run_mvp_system_tests.py
```

## Continuous Integration

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: System Tests
on: [push, pull_request]
jobs:
  system-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run system tests
        run: python tests/system/run_mvp_system_tests.py --quick
      - name: Upload test reports
        uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: mvp_system_test_report_*.json
```

### Automated Monitoring

```bash
# Set up automated system health checks
crontab -e
# Add: 0 */6 * * * /path/to/python /path/to/tests/system/run_mvp_system_tests.py --quick --strict
```

## Production Readiness

### Deployment Validation

Before production deployment, ensure:

- ✅ All system tests pass with EXCELLENT or GOOD quality rating
- ✅ Performance benchmarks meet requirements
- ✅ Error rates are below 1%
- ✅ Resource usage is within acceptable limits
- ✅ All component health checks pass
- ✅ Data persistence and recovery work correctly

### Operational Monitoring

Set up production monitoring based on test metrics:

- **Performance Monitoring**: Track operation durations and success rates
- **Resource Monitoring**: Monitor memory, CPU, and disk usage
- **Error Monitoring**: Track error rates and types
- **Health Monitoring**: Regular component health checks
- **Alerting**: Set up alerts for degraded performance or failures

### Maintenance and Updates

- Run system tests before and after updates
- Monitor performance trends over time
- Update performance benchmarks as system evolves
- Review and update test scenarios regularly
- Maintain test environment consistency with production

## Contributing

When adding new system tests:

1. Follow existing test structure and naming conventions
2. Include comprehensive documentation and comments
3. Add appropriate fixtures and cleanup procedures
4. Update this README with new test descriptions
5. Ensure tests are deterministic and reliable
6. Include performance expectations and thresholds
7. Add appropriate error handling and recovery testing

## Requirements Coverage

These system tests validate the following MVP requirements:

- **Requirement 1.1**: Complete document processing pipeline
- **Requirement 2.2**: Meta document creation and management
- **Requirement 3.1**: Document versioning and lineage tracking
- **Requirement 4.1**: Post-processing and content enhancement
- **Requirement 5.3**: RAG system for intelligent retrieval
- **Requirement 6.1**: System integration and error handling
- **Requirement 7.1**: Performance, monitoring, and operational readiness

The system tests provide comprehensive validation that the Brain MVP meets all functional and non-functional requirements for production deployment.