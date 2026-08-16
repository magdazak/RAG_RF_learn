"""
Pydantic request/response models for the LLM Local RAG API.

These models provide automatic validation, serialization, and
OpenAPI schema generation for FastAPI endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for asking a question against a collection."""

    question: str = Field(..., description="The question to ask", min_length=1)
    collection_name: str = Field(
        default="product_docs", description="ChromaDB collection to query"
    )
    n_results: int = Field(
        default=5, ge=1, le=50, description="Number of chunks to retrieve"
    )
    web_search: bool = Field(
        default=False, description="Enable web search augmentation"
    )


class QueryResponse(BaseModel):
    """Response body containing the generated answer and supporting sources."""

    answer: str = Field(..., description="Generated answer")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Retrieved chunks with metadata"
    )
    processing_time: float = Field(..., description="Response time in seconds")
    used_web_search: bool = Field(
        default=False, description="Whether web search was used"
    )


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after a document upload is accepted."""

    job_id: str = Field(..., description="UUID for tracking processing")
    status: str = Field(default="queued", description="Initial job status")
    message: str = Field(..., description="User-friendly message")
    filename: str = Field(..., description="Uploaded file name")


class ProcessingStatus(BaseModel):
    """Status of a document processing job."""

    job_id: str = Field(..., description="UUID identifying the job")
    status: str = Field(
        ..., description="One of: pending | processing | completed | failed"
    )
    progress: Optional[int] = Field(
        default=None, ge=0, le=100, description="Percentage complete (0-100)"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if the job failed"
    )
    collection_name: Optional[str] = Field(
        default=None, description="Collection where the document was stored"
    )


class CollectionInfo(BaseModel):
    """Metadata about a ChromaDB collection."""

    name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of documents/chunks")
    created_at: Optional[str] = Field(
        default=None, description="Creation timestamp, if available"
    )
