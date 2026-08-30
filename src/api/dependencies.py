"""
Shared dependencies and in-memory state for the API routes.
"""

import logging
import time
from pathlib import Path
from typing import Dict

import chromadb

from src.api.models import ProcessingStatus

logger = logging.getLogger(__name__)

# ChromaDB persistence directory, shared across query/documents/collections routes.
CHROMA_PERSIST_DIR = "./chroma_db"

# Collection that cannot be deleted via the API (safety guard).
DEFAULT_COLLECTION_NAME = "product_docs"

# Cached ChromaDB client (singleton) – avoids re-opening the DB on every request.
_chroma_client: chromadb.ClientAPI | None = None


def get_chroma_client(persist_dir: str = CHROMA_PERSIST_DIR) -> chromadb.ClientAPI:
    """Return a shared ChromaDB PersistentClient, creating it on first call."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info("ChromaDB client initialised (persist_dir=%s).", persist_dir)
    client = _chroma_client
    return client

# Directory where uploaded PDFs are temporarily stored before processing.
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Upload constraints
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# In-memory job tracking: job_id -> ProcessingStatus
# NOTE: resets on server restart. Swap for persistent storage (SQLite/Redis)
# in production.
jobs: Dict[str, ProcessingStatus] = {}

# job_id -> creation time (epoch seconds), used for TTL cleanup.
# Kept separate from ProcessingStatus so the public API schema stays unchanged.
job_created_at: Dict[str, float] = {}

JOB_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def get_jobs() -> Dict[str, ProcessingStatus]:
    """FastAPI dependency exposing the shared jobs tracking dict."""
    return jobs


def register_job(job_id: str) -> None:
    """Record the creation time of a job for later TTL cleanup."""
    job_created_at[job_id] = time.time()


def cleanup_expired_jobs(ttl_seconds: float = JOB_TTL_SECONDS) -> int:
    """
    Remove job records older than `ttl_seconds`.

    Returns the number of jobs removed. Safe to call periodically
    (e.g. from a background loop started in the app lifespan).
    """
    now = time.time()
    expired = [
        job_id
        for job_id, created_at in job_created_at.items()
        if now - created_at > ttl_seconds
    ]
    for job_id in expired:
        jobs.pop(job_id, None)
        job_created_at.pop(job_id, None)

    if expired:
        logger.info("TTL cleanup: removed %d expired job(s).", len(expired))

    return len(expired)


