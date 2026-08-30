"""
Collection management endpoints - list and delete ChromaDB collections.
"""

import logging
from typing import List

import chromadb
from fastapi import APIRouter, HTTPException

from src.api.dependencies import CHROMA_PERSIST_DIR, DEFAULT_COLLECTION_NAME
from src.api.models import CollectionInfo

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


@router.get("/collections", response_model=List[CollectionInfo], tags=["Collections"])
async def list_collections() -> List[CollectionInfo]:
    """
    List all ChromaDB collections along with their document/chunk counts.
    """
    try:
        client = _get_client()
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


@router.delete("/collections/{name}", tags=["Collections"])
async def delete_collection(name: str) -> dict:
    """
    Delete a ChromaDB collection by name.

    Safety:
    - 404 if the collection doesn't exist (idempotent DELETE semantics)
    - 403 if attempting to delete the default collection
    """
    client = _get_client()
    existing_names = {c.name for c in client.list_collections()}
    if name not in existing_names:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.")

    if name == DEFAULT_COLLECTION_NAME:
        raise HTTPException(
            status_code=403,
            detail=f"Deleting the default collection '{DEFAULT_COLLECTION_NAME}' is not allowed.",
        )

    try:
        client.delete_collection(name=name)
    except Exception as exc:
        logger.exception("Failed to delete collection '%s'", name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete collection '{name}': {exc}",
        ) from exc

    logger.info("Deleted collection '%s'.", name)
    return {"message": f"Collection '{name}' deleted successfully."}

