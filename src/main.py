"""Main application entry point for Brain MVP."""

import asyncio
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from api.app import create_app


def setup_logging() -> None:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )


def setup_directories() -> None:
    """Set up required directories."""
    directories = [
        settings.upload_dir,
        settings.processed_dir,
        settings.lightrag_index_path,
        Path(settings.log_file_path).parent,
        "./data/raw_documents",
        "./data/processed_documents",
        "./data/rag_index"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


async def main() -> None:
    """Main application function."""
    # Setup
    setup_logging()
    setup_directories()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Brain MVP application...")
    
    # Create FastAPI app
    app = create_app()
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Start server
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
    
    server = uvicorn.Server(config)
    logger.info(f"Server starting on {settings.api_host}:{settings.api_port}")
    
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())