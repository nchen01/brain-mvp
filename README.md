# Brain MVP - Intelligent Document Processing System

## Overview

Brain MVP is an AI-powered document processing and retrieval system that transforms your documents into a searchable, intelligent knowledge base. Upload documents in various formats (PDF, Excel, PowerPoint, etc.) and get them processed, enhanced, and prepared for intelligent querying.

## 🚀 Quick Start (5 minutes)

### Prerequisites
- **Python 3.11+** (required)
- **Git** (to clone the repository)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nchen01/brain-mvp.git
   cd brain-mvp
   ```

2. **Set up environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Quick setup
   python scripts/quick_setup.py
   ```

3. **Start the application**
   ```bash
   python src/main.py
   ```

4. **Test it works**
   - API: http://localhost:8000/docs
   - Health: http://localhost:8000/api/v1/monitoring/health/simple

That's it! 🎉

## 📖 Detailed Setup

For full functionality including document processing and RAG capabilities, see [INSTALLATION.md](INSTALLATION.md).

## Development

### Running Tests
```bash
# Install development dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Lint code
uv run flake8 src tests

# Type checking
uv run mypy src
```

## Documentation

- **API Documentation**: Available at `/docs` when running the application
- **Project Documentation**: See `project.md` for technical details
- **User Guide**: See the complete `readme.md` in the specs directory

## Current Status

This is Sprint 1 implementation focusing on:
- ✅ Project structure and core interfaces
- 🔄 Document versioning and registration system
- 🔄 Document processing pipeline (MinerU + MarkItDown)
- 🔄 Post-processing and RAG preparation
- 🔄 REST API with versioning support

## License

[License information to be added]