"""
Query endpoint - exposes the RAG retrieval + generation pipeline via HTTP.
"""

import logging
import time

from typing import Literal

from fastapi import APIRouter, Form, HTTPException

from src.api.dependencies import CHROMA_PERSIST_DIR
from src.api.models import QueryRequest, QueryResponse, SourceInfo
from src.rag.chunking_robot import PROJECTS

logger = logging.getLogger(__name__)

router = APIRouter()

SNIPPET_CHARS = 300


def _split(value: str) -> list:
    """Split a '|'-joined metadata value back into a list."""
    return [v for v in (value or "").split("|") if v]


def _to_source(chunk: dict, include_text: bool) -> SourceInfo:
    """Convert a retrieved chunk into the compact API representation."""
    meta = chunk.get("metadata") or {}
    text = chunk.get("text", "")
    snippet = text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS].rstrip() + "..."
    return SourceInfo(
        name=meta.get("name") or chunk.get("heading", ""),
        type=meta.get("type", ""),
        project=meta.get("project", ""),
        source_file=meta.get("source_file", ""),
        args=_split(meta.get("args", "")),
        tags=_split(meta.get("tags", "")),
        score=chunk.get("distance"),
        match=chunk.get("match", "vector"),
        snippet=snippet,
        text=text if include_text else None,
    )


def _run_query(
    question: str,
    collection_name: str,
    n_results: int,
    web_search: bool,
    project: str,
    source_file: str,
    type: str,
    contains: str,
    include_text: bool,
) -> QueryResponse:
    """Shared implementation for the form and JSON query endpoints."""
    # Import lazily so the module can be imported without pulling in heavy deps
    # (ollama, embeddings) unless a query is actually made.
    from src.rag.vectorstore import build_where, build_where_document, query_and_generate

    start_time = time.time()
    where = build_where(project=project, source_file=source_file, type=type)
    where_document = build_where_document(contains)

    try:
        answer, sources = query_and_generate(
            query_text=question,
            collection_name=collection_name,
            persist_dir=CHROMA_PERSIST_DIR,
            n_results=n_results,
            use_web_search=web_search,
            return_sources=True,
            where=where,
            where_document=where_document,
        )
    except ConnectionError as exc:
        logger.exception("Could not reach Ollama")
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable. Ensure `ollama serve` is running.",
        ) from exc
    except ValueError as exc:
        # ChromaDB raises ValueError for non-existent collections in some versions
        logger.warning("Collection lookup failed: %s", exc)
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_name}' not found.",
        ) from exc
    except Exception as exc:
        logger.exception("Query processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process the query: {exc}",
        ) from exc

    return QueryResponse(
        answer=answer,
        sources=[_to_source(s, include_text) for s in sources],
        processing_time=time.time() - start_time,
        used_web_search=web_search,
    )


@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(
    question: str = Form(..., min_length=1, description="The question to ask"),
    collection_name: str = Form(default="product_docs", description="ChromaDB collection to query"),
    n_results: int = Form(default=5, ge=1, le=50, description="Number of chunks to retrieve"),
    web_search: bool = Form(default=False, description="Enable web search augmentation"),
    project: Literal["", *PROJECTS] = Form(default="", description="Metadata filter (blank = all projects)"),
    source_file: str = Form(default="", examples=[""], description="Metadata filter: source file name"),
    type: Literal["", "keyword", "testcase", "locator", "python_keyword"] = Form(
        default="", description="Metadata filter: chunk type (blank = all)"
    ),
    contains: str = Form(
        default="", examples=[""], description="Only chunks whose text contains this exact (case-sensitive) substring"
    ),
    include_text: bool = Form(default=False, description="Include full chunk text in each source"),
) -> QueryResponse:
    """
    Ask a question against a ChromaDB collection and get a generated answer
    along with compact source descriptions.

    Empty optional fields are ignored.
    """
    return _run_query(
        question, collection_name, n_results, web_search,
        project, source_file, type, contains, include_text,
    )


@router.post("/query/json", response_model=QueryResponse, tags=["Query"])
async def query_json(body: QueryRequest) -> QueryResponse:
    """Same as `POST /query`, but accepts a JSON body (convenient for chat clients)."""
    return _run_query(
        body.question, body.collection_name, body.n_results, body.web_search,
        body.project, body.source_file, body.type, body.contains, body.include_text,
    )