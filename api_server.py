"""
API Server Entry Point for LLM Local RAG Pipeline.

This script starts the FastAPI server using uvicorn.

Usage:
    python api_server.py

The server will be available at:
    - API: http://localhost:8000
    - Interactive docs: http://localhost:8000/docs
    - Alternative docs: http://localhost:8000/redoc
"""

import uvicorn
import os

if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    # Run the server
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info"
    )

