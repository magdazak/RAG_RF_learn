"""
Embeddings module for generating vector embeddings from text chunks.
Uses a local Ollama embedding model (default: nomic-embed-text).

Note: Use a dedicated embedding model, NOT a generative model like llama3.1:8b.
Recommended models (pull first with `ollama pull <model>`):
  - nomic-embed-text   (fast, 768-dim)
  - mxbai-embed-large  (higher quality, 1024-dim)
"""

import logging
from typing import List, Dict
import ollama

logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "nomic-embed-text"


def get_embedding(text: str, model: str = DEFAULT_EMBED_MODEL) -> List[float]:
    """
    Generate a vector embedding for a single text string using a local Ollama model.

    Parameters:
        text  (str): The input text to embed.
        model (str): Ollama embedding model name. Defaults to 'nomic-embed-text'.

    Returns:
        List[float]: The embedding vector.

    Raises:
        ollama.ResponseError: If the model is not available or Ollama is not running.
    """
    response = ollama.embeddings(model=model, prompt=text)
    return response["embedding"]


def embed_chunks(
    chunks: List[Dict],
    model: str = DEFAULT_EMBED_MODEL,
    ) -> List[Dict]:
    """
    Add an 'embedding' field to each chunk dict in-place and return the enriched list.

    Each chunk is expected to follow the structure produced by markdown_chunker:
        {"text": str, "heading": str | None}

    After calling this function each chunk will also contain:
        {"text": str, "heading": str | None, "embedding": List[float]}

    Parameters:
        chunks (List[Dict]): List of chunk dicts from the chunking pipeline.
        model  (str):        Ollama embedding model name. Defaults to 'nomic-embed-text'.

    Returns:
        List[Dict]: The same list with 'embedding' added to every chunk.
    """
    total = len(chunks)
    logger.info("Embedding %d chunk(s) with model '%s' ...", total, model)

    for i, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "")
        chunk["embedding"] = get_embedding(text, model=model)
        logger.debug("  [%d/%d] embedded heading='%s' (%d chars)", i, total, chunk.get("heading"), len(text))

    logger.info("Embedding complete.")
    return chunks
