#!/usr/bin/env python3
"""
DocForge Brain MVP API Main Entry Point

This is the main entry point for the Brain MVP API server.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import app

# Export the app for uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)