"""
Document upload and background processing endpoints.
"""

import logging
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from src.api.dependencies import (
    ALLOWED_EXTENSIONS,
    CHROMA_PERSIST_DIR,
    MAX_FILE_SIZE_BYTES,
    UPLOAD_DIR,
    get_jobs,
    jobs,  # used directly by the background task (_process_document)
    register_job,
)
from src.api.models import DocumentUploadResponse, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter()


def _process_document(job_id: str, file_path: Path, collection_name: str, persist_dir: str = CHROMA_PERSIST_DIR) -> None:
    """
    Background task that runs the full PDF -> vector store pipeline for one document.

    Mirrors the pipeline used by `rag_cli.py build`:
      1. Extract text from PDF
      2. Convert to Markdown
      3. Chunk the markdown text
      4. Generate embeddings
      5. Store the embedded chunks in ChromaDB
    """
    # Import heavy dependencies lazily (only needed when a job actually runs)
    from src.data_extract.pdf_loader import load_pdf
    from src.data_extract.markdown_converter import pdf_text_to_markdown
    from src.rag.chunking import markdown_chunker
    from src.rag.embeddings import embed_chunks
    from src.rag.vectorstore import build_vectorstore

    try:
        jobs[job_id].status = "processing"
        jobs[job_id].progress = 0

        raw_text = load_pdf(str(file_path))
        jobs[job_id].progress = 20

        markdown = pdf_text_to_markdown(raw_text)
        jobs[job_id].progress = 40

        chunks = markdown_chunker(markdown)
        jobs[job_id].progress = 60

        embedded_chunks = embed_chunks(chunks)
        jobs[job_id].progress = 80

        # doc_id is namespaced on the ORIGINAL filename (not the job_id-prefixed saved path), so re-uploading the same
        # filename overwrites its own previous chunks in ChromaDB, while different filenames never collide.
        original_filename = file_path.name.split(f"{job_id}_", 1)[-1]
        doc_id = Path(original_filename).stem

        build_vectorstore(
            embedded_chunks,
            collection_name=collection_name,
            persist_dir=persist_dir,
            doc_id=doc_id,
        )

        jobs[job_id].status = "completed"
        jobs[job_id].progress = 100
        jobs[job_id].collection_name = collection_name

        logger.info(
            "Job %s completed: %d chunk(s) stored in collection '%s'.",
            job_id, len(embedded_chunks), collection_name,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        logger.exception("Job %s failed", job_id)
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(exc)
    finally:
        # Clean up the temporary upload regardless of outcome.
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove temporary upload: %s", file_path)


@router.post("/documents", response_model=DocumentUploadResponse, status_code=202, tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document to process"),
    collection_name: str = Form(default="product_docs", description="Target ChromaDB collection"),
    job_store: Dict[str, ProcessingStatus] = Depends(get_jobs),
) -> DocumentUploadResponse:
    """
    Upload a PDF document and queue it for background processing into the vector store.
    """
    filename = file.filename or "upload.pdf"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Only {', '.join(sorted(ALLOWED_EXTENSIONS))} are allowed.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    job_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{job_id}_{filename}"
    saved_path.write_bytes(contents)

    job_store[job_id] = ProcessingStatus(job_id=job_id, status="pending", progress=0)
    register_job(job_id)
    background_tasks.add_task(_process_document, job_id, saved_path, collection_name)

    logger.info("Queued job %s for file '%s' -> collection '%s'.", job_id, filename, collection_name)

    return DocumentUploadResponse(
        job_id=job_id,
        status="queued",
        message="Document accepted and queued for processing.",
        filename=filename,
    )


@router.get("/documents/{job_id}", response_model=ProcessingStatus, tags=["Documents"])
async def get_document_status(
    job_id: str,
    job_store: Dict[str, ProcessingStatus] = Depends(get_jobs),
) -> ProcessingStatus:
    """
    Get the processing status of a previously uploaded document.
    """
    status = job_store.get(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return status



