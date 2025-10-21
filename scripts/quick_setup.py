#!/usr/bin/env python3
"""
Quick setup script for Brain MVP.
This script sets up the minimal working environment.
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path


def create_directories():
    """Create necessary directories."""
    dirs = ['data', 'logs', 'data/uploads', 'data/processed']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")


def setup_database():
    """Initialize SQLite database."""
    db_path = Path('data/brain_mvp.db')
    
    try:
        conn = sqlite3.connect(str(db_path))
        
        # Create basic tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'uploaded',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_uuid TEXT,
                stage TEXT,
                status TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_uuid) REFERENCES documents (uuid)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized: {db_path}")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def create_env_file():
    """Create .env file if it doesn't exist."""
    env_path = Path('.env')
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
    
    env_content = """# Brain MVP - Minimal Configuration

# Database
DATABASE_URL=sqlite:///./data/brain_mvp.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=brain-mvp-secret-key-change-in-production-please
JWT_SECRET=jwt-secret-key-change-in-production

# File Processing
MAX_FILE_SIZE=104857600
UPLOAD_DIR=./data/uploads
PROCESSED_DIR=./data/processed

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs

# Development
DEBUG=true
RELOAD=true

# Optional (uncomment when available)
# OPENAI_API_KEY=your-openai-api-key-here
# REDIS_URL=redis://localhost:6379/0
"""
    
    try:
        env_path.write_text(env_content)
        print("✅ Created .env file with minimal configuration")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False


def test_installation():
    """Test basic functionality."""
    print("\n🧪 Testing installation...")
    
    # Test Python imports
    try:
        sys.path.insert(0, str(Path.cwd() / 'src'))
        
        from utils.logging_system import setup_logging, LogCategory
        logger = setup_logging('./logs', enable_console=False)
        logger.info(LogCategory.SYSTEM, 'setup', 'Installation test successful')
        print("✅ Logging system working")
        
        from utils.monitoring_dashboard import MonitoringDashboard
        dashboard = MonitoringDashboard()
        dashboard.stop_monitoring()
        print("✅ Monitoring system working")
        
        return True
        
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Brain MVP Quick Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 11):
        print(f"❌ Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return 1
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Setup steps
    steps = [
        ("Creating directories", create_directories),
        ("Setting up database", setup_database),
        ("Creating configuration", create_env_file),
        ("Testing installation", test_installation),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ Setup failed at: {step_name}")
            return 1
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Start the server: python src/main.py")
    print("   3. Visit: http://localhost:8000/docs")
    print("   4. Check health: http://localhost:8000/api/v1/monitoring/health/simple")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())