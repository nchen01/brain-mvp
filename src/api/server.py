#!/usr/bin/env python3
"""
DocForge Brain MVP API Server

Run the FastAPI server for document processing and management.
"""

import uvicorn
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app


def main():
    """Run the API server."""
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()