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

    # Auto-reload on code changes (dev only). Disable via API_RELOAD=false.
    reload_enabled = os.getenv("API_RELOAD", "true").lower() != "false"

    # Run the server
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        # Only watch actual source files for changes. Without this, uvicorn watches the whole project tree, including
        # runtime/data directories that get written to during PDF processing (uploads/, chroma_db/, data_processed/,
        # json_chunks/). Those writes look like "code changes" to the watcher and trigger a full server restart, which
        # wipes the in-memory job-tracking dict (jobs stuck as "completed" in the logs but 404
        # on GET /api/v1/documents/{job_id} afterwards).
        reload_dirs=["src"] if reload_enabled else None,
        reload_excludes=[
            "uploads/*",
            "chroma_db/*",
            "data_processed/*",
            "data_raw/*",
            "json_chunks/*",
        ] if reload_enabled else None,
        log_level="info"
    )

