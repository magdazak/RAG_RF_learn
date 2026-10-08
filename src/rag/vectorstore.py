"""
Vector store module for storing and querying embeddings using ChromaDB.

Exposes three main functions:
  - build_vectorstore()     : persist embedded chunks to a local ChromaDB collection
  - query_vectorstore()     : embed a query and retrieve the top-k similar chunks
  - query_and_generate()    : retrieve chunks and synthesize a concise answer using LLM

This code is using ChromaDB in persistent client mode, meaning:
1. No separate server needed - ChromaDB runs embedded in your Python application
2. Automatic start - It starts when you run rag_cli.py
3. Local storage - Data persists to the ./chroma_db directory
"""

import logging
import uuid
import chromadb
import ollama
from typing import List, Dict, Optional, Tuple, Union
from src.rag.embeddings import get_embedding, DEFAULT_EMBED_MODEL

logger = logging.getLogger(__name__)

DEFAULT_GENERATION_MODEL = "llama3.1:8b"


def build_vectorstore(
    embedded_chunks: List[Dict],
    collection_name: str = "product_docs",
    persist_dir: str = "./chroma_db",
    doc_id: Optional[str] = None,
) -> None:
    """
    Store embedded chunks inside a persistent ChromaDB collection.

    Each chunk must already contain an 'embedding' field (output of embed_chunks()).
    Expected chunk structure: {"text": str, "heading": str | None, "embedding": List[float]}

    IDs are namespaced per-document as "{doc_id}_chunk_{i}". This matters because
    ChromaDB upserts REPLACE any existing record with the same id: without a
    document-specific prefix, chunk_0/chunk_1/... from DIFFERENT documents would
    collide and silently overwrite each other whenever two docs happened to have
    chunks at the same index (e.g. two 8-chunk PDFs both produce "chunk_0".."chunk_7").

    Passing the SAME doc_id again (e.g. reprocessing the same file with --force)
    intentionally overwrites that document's previous chunks - this preserves the
    "safe to call repeatedly" / idempotent-upsert behavior, but now scoped per
    document instead of colliding across documents.

    Parameters:
        embedded_chunks  (List[Dict]): Chunks enriched with embeddings.
        collection_name  (str):        ChromaDB collection name.
        persist_dir      (str):        Directory where ChromaDB persists its data.
        doc_id           (str | None): Stable identifier for the source document
                                        (e.g. filename without extension). If not
                                        provided, a random UUID is used (chunks will
                                        never collide, but reprocessing the same
                                        document won't overwrite old chunks either -
                                        pass a stable doc_id to get that behavior).
    """
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name=collection_name)

    prefix = doc_id or uuid.uuid4().hex

    ids         = [f"{prefix}_chunk_{i}"      for i, _ in enumerate(embedded_chunks)]
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
        "Stored %d chunk(s) in collection '%s' at '%s' (doc_id='%s').",
        len(embedded_chunks), collection_name, persist_dir, prefix,
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


def query_and_generate(
    query_text: str,
    collection_name: str = "product_docs",
    persist_dir: str = "./chroma_db",
    n_results: int = 5,
    embed_model: str = DEFAULT_EMBED_MODEL,
    generation_model: str = DEFAULT_GENERATION_MODEL,
    use_web_search: bool = False,
    return_sources: bool = False,
) -> Union[str, Tuple[str, List[Dict]]]:
    """
    Query the vector store and generate a concise answer using a local LLM.

    This combines retrieval and generation in one step:
    1. Retrieves top-k relevant chunks from the vector store
    2. Optionally searches the web for additional context
    3. Synthesizes them into a coherent answer using Ollama

    Parameters:
        query_text       (str):  Natural-language question.
        collection_name  (str):  ChromaDB collection to search.
        persist_dir      (str):  Directory where ChromaDB data is stored.
        n_results        (int):  Number of chunks to retrieve for context.
        embed_model      (str):  Ollama model for query embedding.
        generation_model (str):  Ollama model for answer generation.
        use_web_search   (bool): If True, augment with web search results.
                                 ⚠️ WARNING: Sends query to DuckDuckGo servers.
        return_sources    (bool): If True, also return the retrieved chunks
                                 alongside the answer (as a tuple), so callers
                                 (e.g. the API) don't need to run retrieval a
                                 second time just to show sources.

    Returns:
        str: A concise answer synthesized from the retrieved chunks.
        Tuple[str, List[Dict]]: (answer, source_chunks) when return_sources=True.
    """
    # Retrieve relevant chunks from vector store
    chunks = query_vectorstore(
        query_text=query_text,
        collection_name=collection_name,
        persist_dir=persist_dir,
        n_results=n_results,
        model=embed_model,
    )
    
    logger.info(f"Retrieved {len(chunks)} chunks from local vector store")

    context_parts = []
    
    # Add document chunks
    if chunks:
        context_parts.append("=== FROM YOUR DOCUMENTS ===")
        for chunk in chunks:
            if chunk.get("heading"):
                context_parts.append(f"**{chunk['heading']}**\n{chunk['text']}")
            else:
                context_parts.append(chunk["text"])
    
    # Add web search results if enabled
    if use_web_search:
        from src.rag.web_search import search_web
        web_results = search_web(query_text, max_results=3)
        
        if web_results:
            context_parts.append("\n=== FROM WEB SEARCH ===")
            for result in web_results:
                context_parts.append(f"{result['text']}\nSource: {result['source']}")

    if not context_parts:
        answer = "No relevant information found to answer this question."
        return (answer, chunks) if return_sources else answer

    context = "\n\n".join(context_parts)

    # Generate answer using LLM
    prompt = f"""Based on the following information, provide a concise and direct answer to the question.

{context}

Question: {query_text}

Answer:"""

    try:
        response = ollama.generate(
            model=generation_model,
            prompt=prompt,
            stream=False,
        )
        answer = response["response"].strip()
    except Exception as e:
        logger.error(f"Error generating answer with {generation_model}: {e}")
        answer = "Error: Could not generate an answer. Please try again."

    return (answer, chunks) if return_sources else answer
