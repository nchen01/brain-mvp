# Multi-stage Dockerfile for Brain MVP
# Stage 1: Base Python environment with system dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/data/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/data/.cache/transformers \
    SENTENCE_TRANSFORMERS_HOME=/app/data/.cache/sentence-transformers

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    # Additional dependencies for advanced document processing
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Java for tabula-py (table extraction)
    default-jre \
    # Additional OCR languages
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    # Image processing dependencies
    libopencv-dev \
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

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 3: Development image
FROM dependencies AS development

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Create necessary directories (including cache for HuggingFace models)
RUN mkdir -p /app/data /app/logs /app/uploads /app/processed \
    /app/data/.cache/huggingface \
    /app/data/.cache/transformers \
    /app/data/.cache/sentence-transformers

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
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

# Create necessary directories (including cache for HuggingFace models)
RUN mkdir -p /app/data /app/logs /app/uploads /app/processed \
    /app/data/.cache/huggingface \
    /app/data/.cache/transformers \
    /app/data/.cache/sentence-transformers

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]