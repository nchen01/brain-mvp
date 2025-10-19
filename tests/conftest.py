"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import Generator
from pathlib import Path
import tempfile
import shutil

# Optional import of settings
try:
    from src.config.settings import Settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False
    
    # Fallback Settings class
    class Settings:
        def __init__(self, **kwargs):
            self.database_url = kwargs.get("database_url", "sqlite:///test.db")
            self.redis_url = kwargs.get("redis_url", "redis://localhost:6379/1")
            self.upload_dir = kwargs.get("upload_dir", "./data/uploads")
            self.processed_dir = kwargs.get("processed_dir", "./data/processed")
            self.lightrag_index_path = kwargs.get("lightrag_index_path", "./data/rag_index")
            self.log_file_path = kwargs.get("log_file_path", "./logs/test.log")
            self.debug = kwargs.get("debug", True)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        database_url="sqlite:///test.db",
        redis_url="redis://localhost:6379/1",
        upload_dir=str(temp_dir / "uploads"),
        processed_dir=str(temp_dir / "processed"),
        lightrag_index_path=str(temp_dir / "rag_index"),
        log_file_path=str(temp_dir / "test.log"),
        debug=True
    )