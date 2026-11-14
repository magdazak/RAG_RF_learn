"""
Pydantic request/response models for the LLM Local RAG API.

These models provide automatic validation, serialization, and
OpenAPI schema generation for FastAPI endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Compact description of one retrieved chunk."""

    name: str = Field(default="", description="Keyword / test / section name")
    type: str = Field(default="", description="Chunk type (keyword, testcase, ...)")
    project: str = Field(default="", description="Project the chunk belongs to")
    source_file: str = Field(default="", description="Source file name")
    args: List[str] = Field(default_factory=list, description="Keyword arguments")
    tags: List[str] = Field(default_factory=list, description="Tags")
    score: Optional[float] = Field(
        default=None, description="Vector distance (lower = closer); null for lexical name matches"
    )
    match: str = Field(default="vector", description="'vector' or 'lexical'")
    snippet: str = Field(default="", description="Trimmed chunk text")
    text: Optional[str] = Field(default=None, description="Full chunk text (only if include_text=true)")


class QueryRequest(BaseModel):
    """JSON body for POST /query/json (same fields as the form endpoint)."""

    question: str = Field(..., min_length=1)
    collection_name: str = "product_docs"
    n_results: int = Field(default=5, ge=1, le=50)
    web_search: bool = False
    project: str = ""
    source_file: str = ""
    type: str = ""
    contains: str = ""
    include_text: bool = False


class QueryResponse(BaseModel):
    """Response body containing the generated answer and supporting sources."""

    answer: str = Field(..., description="Generated answer (Markdown)")
    sources: List[SourceInfo] = Field(
        default_factory=list, description="Retrieved chunks (compact)"
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


class ChunkInfo(BaseModel):
    """One stored chunk with its metadata."""

    id: str = Field(..., description="Chunk id, '{doc_id}_chunk_{i}'")
    text: str = Field(..., description="Chunk text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Stored metadata")


class ChunkListResponse(BaseModel):
    """A page of chunks from a collection."""

    collection_name: str
    total: int = Field(..., description="Total chunks in the collection matching the filters")
    limit: int
    offset: int
    chunks: List[ChunkInfo]


class CollectionInfo(BaseModel):
    """Metadata about a ChromaDB collection."""

    name: str = Field(..., description="Collection name")
    document_count: int = Field(..., description="Number of documents/chunks")
    created_at: Optional[str] = Field(
        default=None, description="Creation timestamp, if available"
    )
