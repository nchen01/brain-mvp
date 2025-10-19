# Brain MVP - Project Documentation

## Project Overview

The Brain MVP is an AI-powered document processing and retrieval system built with Python, focusing on intelligent document ingestion, processing, and retrieval-augmented generation (RAG) capabilities.

## Technology Stack

- **Package Management**: uv
- **Language**: Python 3.11+
- **AI Orchestration**: LangGraph + PydanticAI
- **RAG Framework**: LightRAG
- **Document Processing**: MinerU (PDF), MarkItDown (Excel/PowerPoint/others)
- **Database**: PostgreSQL (primary), Redis (caching)
- **API Framework**: FastAPI
- **Containerization**: Docker
- **Testing**: pytest

## Project Structure

```
brain-mvp/
├── pyproject.toml                 # uv package configuration
├── README.md                      # User documentation
├── project.md                     # Technical documentation (this file)
├── .env.example                   # Environment variables template
├── docker-compose.yml             # Docker orchestration
├── .gitignore                     # Git ignore rules
│
├── src/                           # Main source code
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py            # Application settings
│   │   └── database.py            # Database configuration
│   │
│   ├── core/                      # Core interfaces and base classes
│   │   ├── __init__.py
│   │   ├── interfaces.py          # Abstract interfaces
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── models.py              # Shared data models
│   │
│   ├── docforge/                  # Document processing pipeline
│   │   ├── __init__.py
│   │   ├── versioning/            # Document versioning and lineage system
│   │   │   ├── __init__.py
│   │   │   ├── lineage.py         # Document lineage management
│   │   │   ├── versions.py        # Version tracking and branching
│   │   │   ├── deletion.py        # Privacy-focused soft deletion
│   │   │   └── models.py          # Versioning data models
│   │   │
│   │   ├── registration/          # Document registration system
│   │   │   ├── __init__.py
│   │   │   ├── service.py         # Registration service with versioning
│   │   │   ├── duplicate_detection.py # Content hash-based duplicate detection
│   │   │   └── models.py          # Registration data models
│   │   │
│   │   ├── routing/               # Pre-processing router
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # File type routing logic
│   │   │   └── rules.py           # Routing rules engine
│   │   │
│   │   ├── processors/            # Document processors
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Base processor interface
│   │   │   ├── mineru_processor.py # PDF processor using MinerU
│   │   │   ├── markitdown_processor.py # Multi-format processor
│   │   │   └── standardizer.py    # Output format standardization
│   │   │
│   │   ├── postprocessing/        # Post-processing system
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # Post-processing router
│   │   │   ├── chunking/          # Document chunking strategies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py        # Base chunking interface
│   │   │   │   ├── paragraph.py   # Paragraph-based chunking
│   │   │   │   ├── section.py     # Section-based chunking
│   │   │   │   ├── sentence.py    # Sentence-based chunking
│   │   │   │   └── topic.py       # Topic-based chunking
│   │   │   │
│   │   │   └── enhancement/       # Content enhancement
│   │   │       ├── __init__.py
│   │   │       ├── abbreviations.py # Abbreviation expansion
│   │   │       └── normalization.py # Content normalization
│   │   │
│   │   ├── storage/               # Document storage systems
│   │   │   ├── __init__.py
│   │   │   ├── raw_storage.py     # Raw document storage
│   │   │   ├── post_storage.py    # Post-processed storage
│   │   │   └── meta_storage.py    # Meta document storage
│   │   │
│   │   └── rag/                   # RAG preparation
│   │       ├── __init__.py
│   │       ├── lightrag_integration.py # LightRAG integration
│   │       ├── indexing.py        # Document indexing
│   │       └── embeddings.py      # Vector embeddings
│   │
│   ├── queryreactor/              # Intelligent QA system (Future Sprint)
│   │   ├── __init__.py
│   │   └── placeholder.py         # Placeholder for future implementation
│   │
│   ├── dbm/                       # Database management (Dummy)
│   │   ├── __init__.py
│   │   ├── connection.py          # Basic connection management
│   │   └── operations.py          # Basic CRUD operations
│   │
│   ├── accountmatrix/             # Account management (Dummy)
│   │   ├── __init__.py
│   │   ├── auth.py                # Basic authentication
│   │   └── session.py             # Simple session management
│   │
│   └── api/                       # REST API
│       ├── __init__.py
│       ├── app.py                 # FastAPI application
│       ├── routes/                # API routes
│       │   ├── __init__.py
│       │   ├── documents.py       # Document endpoints with versioning
│       │   ├── versions.py        # Version management endpoints
│       │   ├── lineage.py         # Document lineage endpoints
│       │   ├── processing.py      # Processing status endpoints
│       │   ├── search.py          # RAG search endpoints
│       │   └── auth.py            # Authentication endpoints
│       │
│       ├── middleware/            # API middleware
│       │   ├── __init__.py
│       │   ├── auth.py            # Authentication middleware
│       │   └── logging.py         # Request logging
│       │
│       └── schemas/               # API request/response schemas
│           ├── __init__.py
│           ├── documents.py       # Document schemas with versioning
│           ├── versions.py        # Version management schemas
│           ├── lineage.py         # Document lineage schemas
│           ├── processing.py      # Processing schemas
│           └── search.py          # Search schemas
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # pytest configuration
│   ├── unit/                      # Unit tests
│   │   ├── __init__.py
│   │   ├── test_docforge/         # DocForge unit tests
│   │   ├── test_dbm/              # DBM unit tests
│   │   └── test_accountmatrix/    # AccountMatrix unit tests
│   │
│   ├── integration/               # Integration tests
│   │   ├── __init__.py
│   │   ├── test_pipeline/         # Pipeline integration tests
│   │   └── test_api/              # API integration tests
│   │
│   └── fixtures/                  # Test fixtures and sample data
│       ├── __init__.py
│       ├── sample_documents/      # Sample test documents
│       └── test_data.py           # Test data generators
│
├── scripts/                       # Utility scripts
│   ├── setup_dev.py               # Development environment setup
│   ├── migrate_db.py              # Database migration script
│   └── seed_data.py               # Test data seeding
│
├── docs/                          # Additional documentation
│   ├── api/                       # API documentation
│   ├── deployment/                # Deployment guides
│   └── development/               # Development guides
│
├── logs/                          # Log files (created at runtime)
│   ├── app.log                    # Application logs
│   ├── processing.log             # Document processing logs
│   └── prompt_history.txt         # AI prompt history
│
└── data/                          # Data storage (created at runtime)
    ├── raw_documents/             # Raw document storage
    ├── processed_documents/       # Processed document storage
    └── rag_index/                 # LightRAG index storage
```

## Module Documentation

### Core Modules

#### DocForge (`src/docforge/`)
The main document processing pipeline with the following components:

- **Versioning**: Complete document lineage tracking, version branching, and privacy-focused deletion
- **Registration**: Handles document upload, UUID generation, and content hash-based duplicate detection
- **Routing**: Determines appropriate processor based on file type and metadata
- **Processors**: Document processing using MinerU (PDF) and MarkItDown (others)
- **Post-processing**: Content enhancement, chunking, and abbreviation expansion
- **Storage**: Multi-tier storage system (Raw, Post, Meta documents) with version support
- **RAG**: LightRAG integration for retrieval-augmented generation preparation

#### DBM (`src/dbm/`) - Dummy Implementation
Basic database management for MVP support:
- Simple connection management
- Basic CRUD operations
- Minimal error handling

#### AccountMatrix (`src/accountmatrix/`) - Dummy Implementation
Basic authentication for MVP support:
- Simple user authentication
- Basic session management
- Minimal user data storage

### Data Flow

```mermaid
graph TD
    A[Document Upload] --> B{New Document?}
    B -->|Yes| C[Create Document Lineage]
    B -->|No| D[Add to Existing Lineage]
    C --> E[Generate lineage_uuid]
    D --> F[Increment version_number]
    E --> G[Registration with Version 1]
    F --> H[Registration with Version N]
    G --> I[Content Hash Check]
    H --> I
    I --> J[Pre-processing Router]
    J --> K[MinerU PDF Processor]
    J --> L[MarkItDown Processor]
    K --> M[Output Standardization]
    L --> M
    M --> N[Post-processing Router]
    N --> O[Chunking Strategy]
    N --> P[Abbreviation Expansion]
    O --> Q[Meta Document Storage with Version]
    P --> Q
    Q --> R[LightRAG Indexing]
    R --> S[RAG Database]
    
    T[Edit Old Version] --> U[Create Version Branch]
    U --> V[New Version with parent_version]
    V --> I
    
    W[Privacy Delete] --> X[Soft Delete Version]
    X --> Y[Preserve Lineage Chain]
```

### Database Schema

#### Document Lineage Table
```sql
CREATE TABLE document_lineage (
    lineage_uuid UUID PRIMARY KEY,
    original_filename VARCHAR(255) NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_version INTEGER DEFAULT 1,
    total_versions INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### Raw Document Register Table
```sql
CREATE TABLE raw_document_register (
    doc_uuid UUID PRIMARY KEY,
    lineage_uuid UUID NOT NULL REFERENCES document_lineage(lineage_uuid),
    version_number INTEGER NOT NULL,
    parent_version INTEGER NULL,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100) NOT NULL,
    labels TEXT[],
    is_current BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    deletion_reason TEXT NULL,
    edit_source_version INTEGER NULL,
    UNIQUE(lineage_uuid, version_number)
);
```

#### Post Document Register Table
```sql
CREATE TABLE post_document_register (
    doc_uuid UUID NOT NULL REFERENCES raw_document_register(doc_uuid),
    set_uuid UUID NOT NULL,
    file_uuid UUID PRIMARY KEY,
    lineage_uuid UUID NOT NULL REFERENCES document_lineage(lineage_uuid),
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    processing_method VARCHAR(100) NOT NULL,
    processing_version VARCHAR(50) NOT NULL,
    metadata_record JSONB,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Meta Document Register Table
```sql
CREATE TABLE meta_document_register (
    meta_file_uuid UUID PRIMARY KEY,
    doc_uuid UUID NOT NULL REFERENCES raw_document_register(doc_uuid),
    lineage_uuid UUID NOT NULL REFERENCES document_lineage(lineage_uuid),
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    metadata_record JSONB,
    processing_status VARCHAR(50) NOT NULL,
    chunking_strategy VARCHAR(50),
    post_processing_applied TEXT[],
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Document Version History View
```sql
CREATE VIEW document_version_history AS
SELECT 
    dl.lineage_uuid,
    dl.original_filename,
    dl.created_by,
    dl.created_at as lineage_created,
    rdr.doc_uuid,
    rdr.version_number,
    rdr.parent_version,
    rdr.filename,
    rdr.file_type,
    rdr.file_hash,
    rdr.timestamp as version_created,
    rdr.user_id,
    rdr.is_current,
    rdr.is_deleted,
    rdr.deletion_reason,
    rdr.edit_source_version
FROM document_lineage dl
JOIN raw_document_register rdr ON dl.lineage_uuid = rdr.lineage_uuid
ORDER BY dl.lineage_uuid, rdr.version_number;
```

## Configuration

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/brain_mvp
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-here

# Processing Configuration
MAX_FILE_SIZE=100MB
PROCESSING_TIMEOUT=300
CHUNK_SIZE=1000

# LightRAG Configuration
LIGHTRAG_INDEX_PATH=./data/rag_index
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
```

### Development Setup

1. **Install uv**: Follow [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
2. **Clone repository**: `git clone <repository-url>`
3. **Install dependencies**: `uv sync`
4. **Set up environment**: `cp .env.example .env`
5. **Run setup script**: `uv run scripts/setup_dev.py`
6. **Start development server**: `uv run src/main.py`

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Deployment

### Docker Deployment
```bash
# Build and start all services
docker-compose up --build

# Start in production mode
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment
1. Set up Python environment with uv
2. Install dependencies: `uv sync --frozen`
3. Set up database and run migrations
4. Configure environment variables
5. Start application: `uv run src/main.py`

## Monitoring and Logging

- **Application Logs**: `logs/app.log`
- **Processing Logs**: `logs/processing.log`
- **Prompt History**: `logs/prompt_history.txt`
- **Health Check Endpoint**: `/health`
- **Metrics Endpoint**: `/metrics`

## Future Development

### Sprint 2: QueryReactor Integration
- LangGraph + PydanticAI integration
- Query processing and response generation
- Advanced RAG retrieval using LightRAG

### Sprint 3: Production Features
- Advanced authentication and authorization
- Comprehensive database management
- Production monitoring and alerting
- Docker orchestration and scaling