"""
Query endpoint - exposes the RAG retrieval + generation pipeline via HTTP.
"""

import logging
import time

from typing import Literal

from fastapi import APIRouter, Form, HTTPException

from src.api.dependencies import CHROMA_PERSIST_DIR
from src.api.models import QueryResponse
from src.rag.chunking_robot import PROJECTS

logger = logging.getLogger(__name__)

router = APIRouter()


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
) -> QueryResponse:
    """
    Ask a question against a ChromaDB collection and get a generated answer
    along with the source chunks used to build the context.

    Empty optional fields are ignored.
    """
    # Import lazily so the module can be imported without pulling in heavy deps
    # (ollama, embeddings) unless a query is actually made.
    from src.rag.vectorstore import build_where, build_where_document, query_and_generate

    start_time = time.time()
    where =   build_where(project=project, source_file=source_file, type=type)
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

    processing_time = time.time() - start_time

    return QueryResponse(
        answer=answer,
        sources=sources,
        processing_time=processing_time,
        used_web_search=web_search,
    )
