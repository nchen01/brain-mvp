# Multi-stage Dockerfile for Brain MVP
# Stage 1: Base Python environment with system dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # HuggingFace and model cache directories
    HF_HOME=/app/data/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/data/.cache/transformers \
    SENTENCE_TRANSFORMERS_HOME=/app/data/.cache/sentence-transformers

# Install system dependencies (slimmed down - MinerU runs in separate container)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    # PDF processing dependencies for fallback processor
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Stage 2: Dependencies installation
FROM base AS dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install uv for faster package installation, then install dependencies
RUN pip install --upgrade pip uv && \
    uv pip install --system -r requirements.txt

# Stage 3: Development image
FROM dependencies AS development

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/uploads /app/processed \
    /app/data/.cache/huggingface \
    /app/data/.cache/transformers \
    /app/data/.cache/sentence-transformers \
    /app/data/mineru_output

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Development command with hot reload
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Production image
FROM dependencies AS production

# Copy only necessary files
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY pyproject.toml .
COPY README.md .

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/uploads /app/processed \
    /app/data/.cache/huggingface \
    /app/data/.cache/transformers \
    /app/data/.cache/sentence-transformers \
    /app/data/mineru_output

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
