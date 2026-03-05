# Brain MVP - Advanced Document Processing & RAG System

A production-ready document processing system that extracts text from PDF documents using advanced multi-library processing and prepares it for high-precision RAG (Retrieval-Augmented Generation).

## Key Features

- **Modern Web Interface**: Premium drag-and-drop interface for document management, real-time status monitoring, and chunking visualization.
- **Advanced PDF Processing**: Multi-library approach with **MinerU API** (primary) and fallback to **PyMuPDF**, **pdfplumber**, and **pdfminer** for maximum extraction reliability.
- **MinerU Integration**: High-quality PDF parsing with layout detection (DocLayout-YOLO), OCR support (109 languages via PaddleOCR), table structure recognition, and formula recognition (UniMERNet).
- **High-Precision RAG Pipeline**:
  - **Multiple Chunking Strategies**: Recursive, Fixed-size, Semantic, and Hybrid Structure-Aware chunking.
  - **Hybrid Structure-Aware Chunking**: Normalizes documents into a hierarchical section model, routes sections by length (SHORT/MEDIUM/LONG), and chunks respecting section, paragraph, and sentence boundaries.
  - **Summarization Stage**: Optional LLM-based (Anthropic/OpenAI) or extractive document and section summarization, injected between parsing and chunking to enrich every chunk with doc-level and section-level context.
  - **Context Enrichment**: Anthropic-style context-enriched chunking for improved retrieval accuracy.
- **Individual Document Management**: Support for individual document deletion with full cleanup of associated chunks and metadata.
- **Robust Storage Architecture**: Multi-tier storage system supporting both SQLite (development) and PostgreSQL (production).
- **Production Ready**: Fully containerized with Docker, including PostgreSQL and Redis for caching and background tasks.
- **Multiple Deployment Profiles**: CPU, GPU (NVIDIA), and Mac Model Runner profiles for flexible deployment.

---

## Architecture Overview

### Processing Pipeline
1. **Upload**: Document received via Web UI or REST API.
2. **Extraction**: `MinerUProcessor` (primary) or `AdvancedPDFProcessor` (fallback) extracts text, tables, and images using the best available backend.
3. **Abbreviation Expansion**: Acronyms and abbreviations are expanded inline before chunking.
4. **Summarization** *(optional)*: `SummarizationService` generates a 2–3 sentence document summary and per-section summaries, which are attached to every downstream chunk.
5. **Chunking**: Documents are split into chunks using configurable strategies (Recursive, Semantic, Hybrid, etc.). Each chunk carries `doc_summary`, `section_summary`, and `section_path`.
6. **Enrichment**: An enriched embedding string (`Document: … Summary: … Section: … Content: …`) is built per chunk and stored as `enriched_content` for the vector store.
7. **Storage**: Content is stored across specialized databases (Raw, Post, Meta, and Chunks).

### Database Schema
The system uses a comprehensive schema to track document lineage and processing history:
- `document_lineage`: Tracks document versions and history.
- `raw_document_register`: Stores original file information and status.
- `document_chunks`: Stores processed chunks with strategy metadata, summary fields (`doc_summary`, `section_summary`, `section_path` in `chunk_metadata` JSON), and enriched embedding content.
- `meta_document_register`: Stores structural metadata and processing status.

---

## ⚡ Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI or Anthropic API Key (optional — required only for semantic chunking, context enrichment, or LLM summarization)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nchen01/brain-mvp.git
   cd brain-mvp
   ```

2. **Configure Environment**:
   Create a `.env` file or set environment variables:
   ```bash
   OPENAI_API_KEY=your_key_here          # optional
   ANTHROPIC_API_KEY=your_key_here       # optional, for LLM summarization
   PROCESSING__DEFAULT_CHUNKING_STRATEGY=recursive
   PROCESSING__SUMMARIZATION__ENABLED=false   # set true to enable summarization
   ```

3. **Start the System**:
   ```bash
   docker-compose up -d
   ```

4. **Access the Interface**:
   - **Web UI**: [http://localhost:8088](http://localhost:8088)
   - **API Docs (Swagger)**: [http://localhost:8088/docs](http://localhost:8088/docs)

---

## 🧠 Advanced RAG Capabilities

### Abbreviation Expansion
Before chunking, the system expands abbreviations and acronyms inline (e.g., "API" becomes "API (Application Programming Interface)") to improve RAG retrieval accuracy. This ensures that when users search for either the abbreviation or the full term, relevant chunks are retrieved.

**Features:**
- **Domain-Aware Detection**: Recognizes abbreviations from technical, academic, business, medical, and general domains
- **Confidence-Based Expansion**: Only expands abbreviations above a configurable confidence threshold (default: 0.7)
- **Inline Expansion**: Preserves the original abbreviation while adding the expansion in parentheses
- **Persistence**: Expansion data is stored and retrievable via API

**API Endpoint:**
```bash
# Get abbreviation expansions for a document
curl "http://localhost:8088/api/v1/documents/{document_id}/abbreviations"
```

**Configuration:**
- `PROCESSING__ENABLE_ABBREVIATION_EXPANSION=true` (enabled by default)
- `PROCESSING__ABBREVIATION_CONFIDENCE_THRESHOLD=0.7`

### Chunking Strategies
The system supports four chunking strategies to optimize for different RAG use cases:
- **Recursive Character**: Splits text based on character hierarchy (paragraphs, sentences, words).
- **Fixed Size**: Simple fixed-token windows with configurable overlap.
- **Semantic**: Uses embeddings to find natural semantic boundaries in the text.
- **Hybrid Structure-Aware** *(New)*: A multi-stage pipeline that normalizes MinerU output into a hierarchical document model, routes sections by length, and chunks respecting structural boundaries. See details below.

### Hybrid Structure-Aware Chunking
The hybrid chunker is a structure-aware pipeline designed for documents with rich heading/section structure (e.g., MinerU-processed PDFs).

**Pipeline stages:**
1. **Normalization**: MinerU `StandardizedDocumentOutput` is transformed into a `NormalizedDocument` with hierarchical sections, headings (H1-H6), paragraphs, and pre-split sentences.
2. **Section Routing**: Each section is classified by word count:
   - **SHORT** (< 150 words): Kept as a single chunk or merged with adjacent short sections.
   - **MEDIUM** (150-800 words): Recursively split at paragraph/sentence boundaries.
   - **LONG** (> 800 words): Recursively split and flagged as candidates for future semantic refinement.
3. **Structure-Aware Recursive Chunking**: Splits follow a Section → Paragraph → Sentence boundary hierarchy, preserving heading context (breadcrumb path) across chunks.
4. **Overlap & Linking**: Adjacent chunks receive configurable word overlap for context continuity and are linked with previous/next relationships.

**Configuration:**
```python
short_section_threshold: 150   # words
long_section_threshold: 800    # words
target_chunk_size: 500         # words
max_chunk_size: 800            # words
min_chunk_size: 50             # words
chunk_overlap: 50              # words
```

**Module location:** `src/docforge/postprocessing/hybrid_chunking/`

### Summarization Stage
The summarization stage runs between parsing and chunking, producing a `DocumentSummaries` object that is threaded through to every chunk produced downstream.

**Modes:**
- **`llm`** (default): Calls an LLM (Anthropic Claude Haiku or OpenAI) to produce 2–3 sentence document summaries and 1–2 sentence section summaries for large sections.
- **`extractive`**: Pure-Python TF-IDF sentence scorer — no API calls, zero latency cost.

**Enriched embedding text format:**
```
Document: {title}. Overall summary: {doc_summary}. Section: {section_path}. Section summary: {section_summary}. Content: {raw_text}
```

**Configuration** (env vars or `settings.py`):
```bash
PROCESSING__SUMMARIZATION__ENABLED=true
PROCESSING__SUMMARIZATION__MODE=llm                      # or extractive
PROCESSING__SUMMARIZATION__MODEL_NAME=claude-haiku-4-5-20251001
PROCESSING__SUMMARIZATION__API_PROVIDER=anthropic        # or openai
PROCESSING__SUMMARIZATION__MAX_DOC_TOKENS_FOR_DIRECT_SUMMARY=8000
PROCESSING__SUMMARIZATION__SECTION_SUMMARY_MIN_TOKENS=200
```

Summarization is **off by default** — existing deployments are unaffected until opted in.

**Module location:** `src/docforge/postprocessing/summarizer.py`

### Context Enrichment
Inspired by Anthropic's "Contextual Retrieval", the system can enrich each chunk with document-level context. This significantly improves retrieval accuracy by providing the LLM with the necessary background for each individual chunk.

---

## Docker Orchestration

The system is composed of multiple services with different deployment profiles:

### Core Services

| Service | Container Name | Port | Description |
|---------|----------------|------|-------------|
| **App** | `brain-mvp-app` | 8088 | FastAPI application & PDF processing engine |
| **Postgres** | `brain-mvp-postgres` | 5433 | Primary database for document metadata & chunks |
| **Redis** | `brain-mvp-redis` | 6380 | Cache for background tasks and session management |
| **MinerU API** | `mineru-api` | 8001 | MinerU PDF processing service (GPU/CPU profiles) |
| **MinerU Gradio** | `mineru-gradio` | 7860 | MinerU web interface (GPU profile only) |

### MinerU Profiles

| Profile | Command | Description |
|---------|---------|-------------|
| **Default** | `docker compose up -d` | Core services only (uses fallback PDF processor) |
| **CPU** | `docker compose --profile cpu up -d` | MinerU with CPU-based pipeline backend |
| **GPU** | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile gpu up -d` | MinerU with NVIDIA GPU acceleration |
| **Mac Model Runner** | `docker compose --profile mac-modelrunner up -d` | MinerU with Docker Model Runner VLM backend |

#### GPU Profile Requirements
- NVIDIA GPU with compute capability 8.0+ (Ampere/Ada/Hopper architecture)
- NVIDIA Container Toolkit installed
- Tested with RTX 3060 Ti (8GB VRAM), RTX 3090, RTX 4090
- Uses `pipeline` backend for reliable processing with GPU-accelerated OCR and layout detection

### Useful Commands
```bash
# View logs
docker compose logs -f brain-mvp

# Restart the application
docker compose restart brain-mvp

# Run end-to-end tests
docker compose exec brain-mvp python tests/final_e2e_test.py

# Start with MinerU CPU profile
docker compose --profile cpu up -d
```

**Note for Mac Users**: See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) for important information about Docker Model Runner limitations on macOS.

---

## 📡 API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload and process a new PDF |
| `GET` | `/api/v1/documents/` | List all uploaded documents |
| `GET` | `/api/v1/documents/{id}/status` | Check processing progress |
| `GET` | `/api/v1/documents/{id}/content` | Retrieve extracted text/JSON/Markdown |
| `GET` | `/api/v1/documents/{id}/abbreviations` | Get abbreviation expansions for a document |
| `DELETE` | `/api/v1/documents/{id}` | Permanently delete a document and its chunks |
| `GET` | `/api/v1/chunks/document/{id}` | Retrieve all chunks for a document |

---

## 🛡 Safety and Security

### Strict Approval Commands
To prevent accidental data loss, certain operations require explicit user approval. See [`STRICT_APPROVAL_COMMANDS.md`](STRICT_APPROVAL_COMMANDS.md) for details.

### Data Privacy
- Support for encrypted storage of document content.
- Local processing of PDF documents (no external PDF APIs used).
- Configurable data retention policies.

---

## 📄 License
This project is licensed under the MIT License.

## Support
For technical support or feature requests, please check the following:
1. **Technical Overview**: [`PROJECT_EXPLANATION.md`](PROJECT_EXPLANATION.md)
2. **User Guide**: [`USAGE_GUIDE.md`](USAGE_GUIDE.md)
3. **Known Issues**: [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) - Mac Docker Runner issues and workarounds
4. **Installation Guide**: [`INSTALLATION.md`](INSTALLATION.md)
5. **Test Results**: [`END_TO_END_TEST_RESULTS.md`](tests/results/END_TO_END_TEST_RESULTS.md)