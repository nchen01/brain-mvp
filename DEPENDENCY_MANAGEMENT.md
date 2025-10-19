# Dependency Management Guide

This document explains how to manage dependencies for the Brain MVP project and resolve common dependency-related issues.

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script to automatically configure the environment
python3 scripts/setup_dev_env.py
```

### Option 2: Manual Setup with uv (Recommended)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync

# Install development dependencies
uv add --dev pytest pytest-asyncio pytest-cov
```

### Option 3: Manual Setup with pip
```bash
# Install the package in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev]

# Or install specific dependencies
pip install pytest pytest-asyncio pydantic pydantic-settings sentence-transformers
```

## Running Tests

### Check Dependencies First
```bash
# Check what dependencies are missing
python3 scripts/run_tests.py --check-only
```

### Run Tests with Dependency Management
```bash
# Run all tests (will check dependencies first)
python3 scripts/run_tests.py

# Run specific test with automatic dependency installation
python3 scripts/run_tests.py --install-deps tests/integration/test_meta_document_rag_integration.py::TestLightRAGIntegration::test_lightrag_vector_embeddings

# Run tests quietly
python3 scripts/run_tests.py --quiet
```

### Traditional pytest (if all dependencies are installed)
```bash
# Run the specific test that was failing
python3 -m pytest tests/integration/test_meta_document_rag_integration.py::TestLightRAGIntegration::test_lightrag_vector_embeddings -v --tb=short
```

## Dependency Categories

### Core Dependencies (Required)
- `pydantic>=2.5.0` - Data validation and settings
- `pydantic-settings>=2.1.0` - Settings management

### AI/ML Dependencies (Optional but recommended)
- `sentence-transformers>=2.2.0` - Text embeddings
- `lightrag>=0.0.1` - RAG framework
- `openai>=1.0.0` - OpenAI API client

### Test Dependencies
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `pytest-cov>=4.1.0` - Coverage reporting

### Document Processing Dependencies
- `magic-pdf>=0.7.0` - PDF processing (MinerU)
- `markitdown>=0.0.1a2` - Multi-format document processing

## Graceful Degradation

The codebase is designed to work with missing dependencies through graceful degradation:

### 1. Optional Imports
```python
# Example: Optional pydantic import
try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback implementations provided
```

### 2. Test Skipping
Tests automatically skip when required dependencies are missing:
```python
@pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence_transformers required")
def test_embedding_functionality():
    # Test only runs if sentence_transformers is available
    pass
```

### 3. Feature Detection
```python
# Check if features are available before using them
if LIGHTRAG_AVAILABLE:
    # Use LightRAG features
else:
    # Use fallback implementation or skip feature
```

## Common Issues and Solutions

### Issue: "No module named 'pydantic_settings'"
**Solution:**
```bash
pip install pydantic-settings>=2.1.0
# or
uv add pydantic-settings>=2.1.0
```

### Issue: "No module named 'sentence_transformers'"
**Solution:**
```bash
pip install sentence-transformers>=2.2.0
# or
uv add sentence-transformers>=2.2.0
```

### Issue: "No module named 'lightrag'"
**Solution:**
```bash
pip install lightrag>=0.0.1
# or
uv add lightrag>=0.0.1
```

### Issue: Tests fail with import errors
**Solution:**
1. Use the test runner script: `python3 scripts/run_tests.py --install-deps`
2. Or install missing dependencies manually
3. Tests will automatically skip if optional dependencies are missing

## Development Workflow

### 1. Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd brain_mvp

# Set up development environment
python3 scripts/setup_dev_env.py
```

### 2. Daily Development
```bash
# Check dependencies before starting work
python3 scripts/run_tests.py --check-only

# Run tests for your changes
python3 scripts/run_tests.py tests/path/to/your/test.py

# Run all tests
python3 scripts/run_tests.py
```

### 3. Adding New Dependencies
```bash
# With uv (recommended)
uv add new-package>=1.0.0

# With pip
pip install new-package>=1.0.0
# Then add to pyproject.toml dependencies list
```

## Continuous Integration

For CI/CD environments, use:
```bash
# Install all dependencies
uv sync

# Or with pip
pip install -e .[dev]

# Run tests with dependency checking
python3 scripts/run_tests.py
```

## Troubleshooting

### Check Python Version
```bash
python3 --version  # Should be 3.11+
```

### Check Package Manager
```bash
# Check if uv is available
uv --version

# Check pip
pip --version
```

### Manual Dependency Check
```bash
python3 -c "
import sys
sys.path.append('.')
from src.utils.dependency_checker import dependency_checker, check_test_dependencies
test_available, missing = check_test_dependencies()
dependency_checker.print_dependency_report()
"
```

### Reset Environment
```bash
# Remove virtual environment (if using one)
rm -rf venv/

# Clean pip cache
pip cache purge

# Reinstall everything
python3 scripts/setup_dev_env.py
```

## Best Practices

1. **Always check dependencies before running tests**
2. **Use the provided scripts for consistent environment setup**
3. **Add new dependencies to pyproject.toml**
4. **Make new features gracefully degrade when dependencies are missing**
5. **Use pytest.mark.skipif for tests requiring optional dependencies**
6. **Document any new dependencies in this guide**

## Support

If you encounter dependency issues not covered here:

1. Check the dependency report: `python3 scripts/run_tests.py --check-only`
2. Try the automated setup: `python3 scripts/setup_dev_env.py`
3. Check the project's pyproject.toml for the correct dependency versions
4. Create an issue with the full error message and your environment details