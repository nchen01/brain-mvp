"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.exceptions import BrainMVPException
from config.settings import settings
from api.routers import documents, auth, chunks


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="DocForge Brain MVP",
        description="AI-powered document processing and retrieval system with versioning support",
        version="1.0.0",
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(chunks.router, prefix="/api/v1")
    
    # Exception handlers
    @app.exception_handler(BrainMVPException)
    async def brain_mvp_exception_handler(request, exc: BrainMVPException):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    # Health check endpoint (simple version)
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "system": "DocForge Brain MVP",
            "timestamp": datetime.now().isoformat(),
            "message": "Brain MVP is running"
        }
    
    # API info endpoint
    @app.get("/api")
    async def api_info():
        """API information endpoint."""
        return {
            "message": "DocForge Brain MVP - AI-powered document processing system",
            "version": "1.0.0",
            "features": [
                "Document upload with versioning",
                "Multi-format processing (PDF, Office, Text)",
                "Intelligent post-processing and chunking",
                "RAG preparation with LightRAG",
                "Document lineage and version management",
                "Real-time processing status"
            ],
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "documents": "/api/v1/documents"
            }
        }
    
    # Serve web interface at root
    @app.get("/")
    async def serve_web_interface():
        """Serve the web interface HTML."""
        # web_interface.html is in the project root, two levels up from src/api
        web_interface_path = Path(__file__).parent.parent.parent / "web_interface.html"
        
        if web_interface_path.exists():
            return FileResponse(web_interface_path)
        else:
            # Fallback if file not found
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Web interface not found",
                    "message": "web_interface.html is missing from the project root",
                    "api_docs": "/docs"
                }
            )
    
    return app


# Create app instance for direct import (needed for Docker/uvicorn)
app = create_app()