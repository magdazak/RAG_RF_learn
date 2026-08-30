"""
Query endpoint - exposes the RAG retrieval + generation pipeline via HTTP.
"""

import logging
import time

import chromadb
from fastapi import APIRouter, HTTPException

from src.api.models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter()

CHROMA_PERSIST_DIR = "./chroma_db"


def _collection_exists(collection_name: str, persist_dir: str = CHROMA_PERSIST_DIR) -> bool:
    """Check whether a ChromaDB collection with the given name exists."""
    client = chromadb.PersistentClient(path=persist_dir)
    existing_names = {c.name for c in client.list_collections()}
    return collection_name in existing_names


@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(request: QueryRequest) -> QueryResponse:
    """
    Ask a question against a ChromaDB collection and get a generated answer
    along with the source chunks used to build the context.
    """
    if not _collection_exists(request.collection_name):
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{request.collection_name}' not found.",
        )

    # Import lazily so the module can be imported without pulling in heavy deps
    # (ollama, embeddings) unless a query is actually made.
    from src.rag.vectorstore import query_and_generate

    start_time = time.time()

    try:
        answer, sources = query_and_generate(
            query_text=request.question,
            collection_name=request.collection_name,
            persist_dir=CHROMA_PERSIST_DIR,
            n_results=request.n_results,
            use_web_search=request.web_search,
            return_sources=True,
        )
    except ConnectionError as exc:
        # ollama-python raises ConnectionError when it can't reach the Ollama
        # server. This can happen either while embedding the query for
        # retrieval, or while generating the final answer.
        logger.exception("Could not reach Ollama")
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable. Ensure `ollama serve` is running.",
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
        used_web_search=request.web_search,
    )
