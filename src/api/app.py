"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.exceptions import BrainMVPException
from config.settings import settings
from api.routers import documents, auth, monitoring


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
    app.include_router(monitoring.router)
    
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
        from utils.monitoring_dashboard import get_dashboard
        
        try:
            dashboard = get_dashboard()
            status = dashboard.get_current_status()
            
            return {
                "status": status.get('overall_status', 'healthy'),
                "version": "1.0.0",
                "system": "DocForge Brain MVP",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    name: health.get('status', 'unknown')
                    for name, health in status.get('component_health', {}).items()
                },
                "details_endpoint": "/api/v1/monitoring/health"
            }
        except Exception:
            return {
                "status": "degraded",
                "version": "1.0.0", 
                "system": "DocForge Brain MVP",
                "timestamp": datetime.now().isoformat(),
                "error": "Monitoring system unavailable"
            }
    
    # Root endpoint
    @app.get("/")
    async def root():
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
    
    return app


# Create app instance for direct import (needed for Docker/uvicorn)
app = create_app()