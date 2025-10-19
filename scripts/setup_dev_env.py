#!/usr/bin/env python3
"""Development environment setup script."""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible. Requires Python 3.11+")
        return False


def setup_with_uv() -> bool:
    """Set up environment using uv."""
    print("📦 Setting up with uv...")
    
    # Check if uv is installed
    if not run_command(["uv", "--version"], "Checking uv installation"):
        print("💡 Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    # Install dependencies
    commands = [
        (["uv", "sync"], "Installing dependencies with uv"),
        (["uv", "add", "--dev", "pytest", "pytest-asyncio", "pytest-cov"], "Installing test dependencies"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            return False
    
    return True


def setup_with_pip() -> bool:
    """Set up environment using pip."""
    print("📦 Setting up with pip...")
    
    # Upgrade pip
    if not run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip"):
        return False
    
    # Install dependencies
    commands = [
        ([sys.executable, "-m", "pip", "install", "-e", "."], "Installing package in development mode"),
        ([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], "Installing development dependencies"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            return False
    
    return True


def create_directories() -> bool:
    """Create necessary directories."""
    directories = [
        "data",
        "data/uploads",
        "data/processed",
        "data/embeddings_cache",
        "data/lightrag",
        "logs",
        "tests/temp"
    ]
    
    for dir_path in directories:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dir_path}")
        except Exception as e:
            print(f"❌ Failed to create directory {dir_path}: {e}")
            return False
    
    return True


def create_env_file() -> bool:
    """Create .env file if it doesn't exist."""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    env_content = """# Brain MVP Environment Configuration

# Database Configuration
DATABASE_URL=sqlite:///./data/brain_mvp.db
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-here-change-in-production

# File Processing Configuration
MAX_FILE_SIZE=104857600
PROCESSING_TIMEOUT=300
UPLOAD_DIR=./data/uploads
PROCESSED_DIR=./data/processed

# LightRAG Configuration
LIGHTRAG_INDEX_PATH=./data/rag_index
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# AI Configuration
# OPENAI_API_KEY=your-openai-api-key-here
DEFAULT_LLM_MODEL=gpt-3.5-turbo

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
ENABLE_PROMPT_LOGGING=true

# Development Configuration
DEBUG=true
RELOAD=true
"""
    
    try:
        env_file.write_text(env_content)
        print("✅ Created .env file with default configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Brain MVP development environment...")
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Create directories
    if not create_directories():
        return 1
    
    # Create .env file
    if not create_env_file():
        return 1
    
    # Try to set up with uv first, fall back to pip
    success = False
    
    # Check if we're in a uv project
    if Path("pyproject.toml").exists():
        success = setup_with_uv()
    
    if not success:
        print("📦 Falling back to pip installation...")
        success = setup_with_pip()
    
    if not success:
        print("❌ Failed to set up development environment")
        return 1
    
    print("\n🎉 Development environment setup completed!")
    print("\n📋 Next steps:")
    print("   1. Activate your virtual environment (if using one)")
    print("   2. Run tests: python scripts/run_tests.py --check-only")
    print("   3. Run a specific test: python scripts/run_tests.py tests/integration/test_meta_document_rag_integration.py::TestLightRAGIntegration::test_lightrag_vector_embeddings")
    print("   4. Start development server: uvicorn src.api.main:app --reload")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())