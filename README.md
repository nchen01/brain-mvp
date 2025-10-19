# Brain MVP - Intelligent Document Processing System

## Overview

Brain MVP is an AI-powered document processing and retrieval system that transforms your documents into a searchable, intelligent knowledge base. Upload documents in various formats (PDF, Excel, PowerPoint, etc.) and get them processed, enhanced, and prepared for intelligent querying.

## Quick Start

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- PostgreSQL database
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brain-mvp
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the application**
   ```bash
   uv run src/main.py
   ```

The API will be available at `http://localhost:8000`

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