"""
Collection management endpoints - list and delete ChromaDB collections.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies import DEFAULT_COLLECTION_NAME, get_chroma_client
from src.api.models import ChunkInfo, ChunkListResponse, CollectionInfo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/collections", response_model=List[CollectionInfo], tags=["Collections"])
async def list_collections() -> List[CollectionInfo]:
    """
    List all ChromaDB collections along with their document/chunk counts.
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
    except Exception as exc:
        logger.exception("Failed to list collections")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to the vector store: {exc}",
        ) from exc

    result = []
    for col in collections:
        try:
            count = col.count()
        except Exception:
            logger.warning("Could not get document count for collection '%s'", col.name)
            count = 0

        metadata = col.metadata or {}
        result.append(
            CollectionInfo(
                name=col.name,
                document_count=count,
                created_at=metadata.get("created_at"),
            )
        )

    return result


@router.get("/collections/{name}/chunks", response_model=ChunkListResponse, tags=["Collections"])
async def list_chunks(
    name: str,
    project: Optional[str] = None,
    source_file: Optional[str] = None,
    type: Optional[str] = None,
    contains: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ChunkListResponse:
    """
    List stored chunks (text + metadata) of a collection, optionally filtered by
    `project`, `source_file`, `type` and/or `contains` (exact, case-sensitive text substring).
    Paginated with `limit` / `offset`.
    """
    from src.rag.vectorstore import build_where, build_where_document

    try:
        collection = get_chroma_client().get_collection(name=name)
    except Exception as exc:  # noqa: BLE001 - collection does not exist
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.") from exc

    where = build_where(project=project, source_file=source_file, type=type)
    where_document = build_where_document(contains)
    try:
        matching = collection.get(where=where, where_document=where_document, include=[])["ids"]
        page = collection.get(
            where=where, where_document=where_document, limit=limit, offset=offset,
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.exception("Failed to read chunks of '%s'", name)
        raise HTTPException(status_code=500, detail=f"Failed to read chunks: {exc}") from exc

    chunks = [
        ChunkInfo(id=i, text=d or "", metadata=m or {})
        for i, d, m in zip(page["ids"], page["documents"], page["metadatas"])
    ]
    return ChunkListResponse(collection_name=name, total=len(matching), limit=limit, offset=offset, chunks=chunks)


@router.delete("/collections/{name}", tags=["Collections"])
async def delete_collection(name: str) -> dict:
    """
    Delete a ChromaDB collection by name.

    Safety:
    - 403 if attempting to delete the default collection
    - 404 if the collection doesn't exist
    """
    if name == DEFAULT_COLLECTION_NAME:
        raise HTTPException(
            status_code=403,
            detail=f"Deleting the default collection '{DEFAULT_COLLECTION_NAME}' is not allowed.",
        )

    client = get_chroma_client()

    try:
        client.delete_collection(name=name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.")
    except Exception as exc:
        logger.exception("Failed to delete collection '%s'", name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete collection '{name}': {exc}",
        ) from exc

    logger.info("Deleted collection '%s'.", name)
    return {"message": f"Collection '{name}' deleted successfully."}
