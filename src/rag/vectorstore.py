"""
Vector store module for storing and querying embeddings using ChromaDB.

Exposes two main functions:
  - build_vectorstore()  : persist embedded chunks to a local ChromaDB collection
  - query_vectorstore()  : embed a query and retrieve the top-k similar chunks

This code is using ChromaDB in persistent client mode, meaning:
1. No separate server needed - ChromaDB runs embedded in your Python application
2. Automatic start - It starts when you run main.py
3. Local storage - Data persists to the ./chroma_db directory
"""

import logging
import chromadb
from typing import List, Dict
from src.rag.embeddings import get_embedding, DEFAULT_EMBED_MODEL

logger = logging.getLogger(__name__)


def build_vectorstore(
    embedded_chunks: List[Dict],
    collection_name: str = "product_docs",
    persist_dir: str = "./chroma_db",
) -> None:
    """
    Store embedded chunks inside a persistent ChromaDB collection.

    Each chunk must already contain an 'embedding' field (output of embed_chunks()).
    Expected chunk structure: {"text": str, "heading": str | None, "embedding": List[float]}

    Existing documents with the same IDs are upserted (overwritten), so this
    function is safe to call repeatedly on the same data.

    Parameters:
        embedded_chunks  (List[Dict]): Chunks enriched with embeddings.
        collection_name  (str):        ChromaDB collection name.
        persist_dir      (str):        Directory where ChromaDB persists its data.
    """
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name=collection_name)

    ids         = [f"chunk_{i}"               for i, _ in enumerate(embedded_chunks)]
    embeddings  = [c["embedding"]             for c in embedded_chunks]
    documents   = [c.get("text", "")          for c in embedded_chunks]
    metadatas   = [{"heading": c.get("heading") or ""} for c in embedded_chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info(
        "Stored %d chunk(s) in collection '%s' at '%s'.",
        len(embedded_chunks), collection_name, persist_dir,
    )


def query_vectorstore(
    query_text: str,
    collection_name: str = "product_docs",
    persist_dir: str = "./chroma_db",
    n_results: int = 5,
    model: str = DEFAULT_EMBED_MODEL,
) -> List[Dict]:
    """
    Embed a query string and return the top-k most similar chunks.

    Parameters:
        query_text      (str): Natural-language question or search phrase.
        collection_name (str): ChromaDB collection to search.
        persist_dir     (str): Directory where ChromaDB data is stored.
        n_results       (int): Number of top results to return.
        model           (str): Ollama model used to embed the query.

    Returns:
        List[Dict]: Each dict contains:
            {"text": str, "heading": str, "distance": float}
        Sorted from most to least similar (lowest distance first).
    """
    client     = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name=collection_name)

    query_embedding = get_embedding(query_text, model=model)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text":     text,
            "heading":  meta.get("heading", ""),
            "distance": dist,
        })

    return output