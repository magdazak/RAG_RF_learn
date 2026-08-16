"""
FastAPI application for LLM Local RAG Pipeline.

Provides HTTP endpoints for document processing and querying.
"""

import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import cleanup_expired_jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 60 * 60  # run TTL cleanup hourly


async def _ttl_cleanup_loop() -> None:
    """Periodically remove job records older than the configured TTL (default 24h)."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            cleanup_expired_jobs()
        except Exception:
            logger.exception("Job TTL cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting LLM Local API server...")
    cleanup_task = asyncio.create_task(_ttl_cleanup_loop())
    yield
    cleanup_task.cancel()
    logger.info("Shutting down LLM Local API server...")


# Initialize FastAPI app
app = FastAPI(
    title="LLM Local RAG API",
    description="A FastAPI-based web API for the LLM Local RAG pipeline. "
                "Upload documents, manage collections, and query your knowledge base.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = time.time()

    # Log request
    logger.info(f"→ {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] {process_time:.3f}s"
    )

    # Add custom header with processing time
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and container orchestration.

    Returns:
        dict: Status information about the API
    """
    return {
        "status": "healthy",
        "service": "LLM Local RAG API",
        "version": "0.1.0",
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint with API information.

    Returns:
        dict: Welcome message and links
    """
    return {
        "message": "Welcome to LLM Local RAG API",
        "docs": "/docs",
        "health": "/health",
        "api_version": "v1"
    }


# Import and include routers
from src.api.routes import documents  # noqa: E402
# from src.api.routes import query, collections

app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
# app.include_router(query.router, prefix="/api/v1", tags=["Query"])
# app.include_router(collections.router, prefix="/api/v1", tags=["Collections"])

