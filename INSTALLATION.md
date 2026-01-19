# Brain MVP - Installation Guide

## Quick Start (Docker - Recommended)

The fastest way to get started is using Docker:

```bash
# Clone the repository
git clone https://github.com/nchen01/brain-mvp.git
cd brain-mvp

# Start core services
docker compose up -d

# Access the application
open http://localhost:8080
```

### Docker Profiles

| Profile | Command | Best For |
|---------|---------|----------|
| Default | `docker compose up -d` | Quick start, basic PDF processing |
| CPU | `docker compose --profile cpu up -d` | MinerU with CPU (slower but accurate) |
| GPU | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile gpu up -d` | NVIDIA GPU systems |

---

## Mac-Specific Setup (Apple Silicon)

### Option 1: Basic Setup (Fallback Processors)

For basic PDF processing without MinerU's advanced features:

```bash
docker compose up -d
```

This uses PyMuPDF, pdfplumber, and pdfminer as fallback processors.

### Option 2: MinerU with CPU Backend

For better PDF processing using MinerU's pipeline backend:

```bash
docker compose --profile cpu up -d
```

### Option 3: MinerU with Vision Model (Best Quality)

For the highest quality PDF processing with vision-language model support, you need to run a llama.cpp server with a vision model. Docker Desktop's Model Runner does not support mmproj files required for vision.

#### Step 1: Install llama.cpp

```bash
# Using Homebrew
brew install llama.cpp

# Or build from source with Metal support
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make LLAMA_METAL=1 -j
```

#### Step 2: Download Vision Model + mmproj

```bash
mkdir -p ~/models

# Download LLaVA 1.6 (recommended)
wget -P ~/models https://huggingface.co/cjpais/llava-1.6-mistral-7b-gguf/resolve/main/llava-v1.6-mistral-7b.Q4_K_M.gguf
wget -P ~/models https://huggingface.co/cjpais/llava-1.6-mistral-7b-gguf/resolve/main/mmproj-model-f16.gguf
```

#### Step 3: Start llama.cpp Server

```bash
llama-server \
  --model ~/models/llava-v1.6-mistral-7b.Q4_K_M.gguf \
  --mmproj ~/models/mmproj-model-f16.gguf \
  --host 0.0.0.0 \
  --port 8001 \
  --ctx-size 4096 \
  --n-gpu-layers 99
```

#### Step 4: Configure and Start Brain MVP

```bash
# Set environment variables
export MINERU_BACKEND=vlm-http-client
export MINERU_SERVER_URL=http://host.docker.internal:8001

# Start with MinerU
docker compose --profile cpu up -d
```

See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) for more details on Mac Docker Model Runner limitations.

---

## Local Development Setup (Without Docker)

This guide will get you up and running with the Brain MVP with basic functionality.

### Prerequisites

- **Python 3.11+** (required)
- **Git** (to clone the repository)
- **10GB free disk space** (for dependencies and data)

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/nchen01/brain-mvp.git
cd brain-mvp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install basic dependencies
pip install -r requirements.txt
```

### Step 2: Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file (minimal required changes)
# - Set DATABASE_URL=sqlite:///./data/brain_mvp.db
# - Set SECRET_KEY to a random string
# - Leave other settings as defaults for now
```

### Step 3: Initialize Database

```bash
# Create data directories
mkdir -p data logs

# Initialize database (SQLite for development)
python -c "
import sqlite3
import os
os.makedirs('data', exist_ok=True)
conn = sqlite3.connect('data/brain_mvp.db')
conn.execute('CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
conn.commit()
conn.close()
print('✅ Database initialized')
"
```

### Step 4: Test Installation

```bash
# Run basic tests
python -m pytest tests/test_chunk_storage.py -v

# Test the logging system
python -c "
from src.utils.logging_system import setup_logging, get_logger, LogCategory
logger = setup_logging('./logs', enable_console=True)
logger.info(LogCategory.SYSTEM, 'test', 'Installation test successful!')
print('✅ Logging system working')
"
```

### Step 5: Start the Application

```bash
# Start the development server
python src/main.py
```

The application should start on `http://localhost:8080`

Visit `http://localhost:8080/docs` to see the API documentation.

## What Works Out of the Box

With this minimal setup, you get:

✅ **Core API Framework** - FastAPI with documentation  
✅ **Logging System** - Comprehensive structured logging  
✅ **Monitoring Dashboard** - System health and metrics  
✅ **Basic Authentication** - JWT-based auth system  
✅ **Database Layer** - SQLite for development  
✅ **Test Suite** - Unit and integration tests  

## What Requires Additional Setup

❌ **Document Processing** - Requires MinerU installation (see Advanced Setup)  
❌ **RAG System** - Requires LightRAG installation (see Advanced Setup)  
❌ **PostgreSQL** - For production use (see Production Setup)  
❌ **Redis** - For caching and sessions (optional)  

## Advanced Setup (Full Functionality)

### Document Processing (MinerU)

MinerU installation can be complex. Follow these steps:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Install MinerU
pip install magic-pdf>=0.7.0

# Test MinerU installation
python -c "
try:
    import magic_pdf
    print('✅ MinerU installed successfully')
except ImportError as e:
    print(f'❌ MinerU not available: {e}')
    print('📝 Using mock processing instead')
"
```

### RAG System (LightRAG)

```bash
# Install LightRAG (if available)
pip install lightrag

# Or use alternative embedding system
pip install chromadb  # Alternative vector database
pip install faiss-cpu  # Alternative vector search
```

### Production Database (PostgreSQL)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE brain_mvp;"
sudo -u postgres psql -c "CREATE USER brain_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE brain_mvp TO brain_user;"

# Update .env file
# DATABASE_URL=postgresql://brain_user:your_password@localhost/brain_mvp
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```
ModuleNotFoundError: No module named 'src'
```
**Solution**: Make sure you're in the project root directory and Python path is set correctly.

#### 2. Database Errors
```
sqlite3.OperationalError: no such table
```
**Solution**: Run the database initialization step again.

#### 3. Permission Errors
```
PermissionError: [Errno 13] Permission denied: './logs'
```
**Solution**: Create directories with proper permissions:
```bash
mkdir -p data logs
chmod 755 data logs
```

#### 4. Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: Change the port in `.env` file or kill the process using port 8000:
```bash
lsof -ti:8000 | xargs kill -9
```

### Testing Your Installation

Run these commands to verify everything works:

```bash
# Test core functionality
python -m pytest tests/unit/test_logging_monitoring_validation.py::TestLoggingSystemValidation::test_error_logging_and_tracking -v

# Test monitoring system
python -c "
from src.utils.monitoring_dashboard import MonitoringDashboard
dashboard = MonitoringDashboard()
print('✅ Monitoring system working')
dashboard.stop_monitoring()
"

# Test API endpoints
curl http://localhost:8080/api/v1/monitoring/health/simple
```

Expected output:
```json
{"status":"ok","timestamp":"2024-01-01T12:00:00","service":"docforge-brain-mvp"}
```

## Development Workflow

Once installed, use these commands for development:

```bash
# Run tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/unit/test_logging_system.py::TestDocForgeLogger::test_basic_logging -v

# Start development server with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Check code quality
python -m pytest tests/unit/test_logging_monitoring_comprehensive.py -v
```

## Getting Help

1. **Check the logs**: `tail -f logs/docforge_main.log`
2. **Run diagnostics**: `python scripts/setup_dev_env.py`
3. **Test basic functionality**: `python test_your_pdf.py` (with any PDF file)
4. **Check system status**: Visit `http://localhost:8080/api/v1/monitoring/health`

## What's Next

After successful installation:

1. **Upload a document**: Use the API at `/api/v1/documents/upload`
2. **Check processing status**: Monitor at `/api/v1/monitoring/queue`
3. **View logs**: Check `./logs/` directory for detailed logging
4. **Explore API**: Visit `/docs` for interactive API documentation

The system is designed to work with mock data initially, so you can test all functionality even without the full document processing pipeline installed.