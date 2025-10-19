"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.exceptions import BrainMVPException
from config.settings import settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Brain MVP",
        description="AI-powered document processing and retrieval system",
        version="0.1.0",
        debug=settings.debug
    )
    
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
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Brain MVP - AI-powered document processing system",
            "version": "0.1.0",
            "docs": "/docs"
        }
    
    return app