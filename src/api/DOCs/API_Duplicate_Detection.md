## API Duplicate Detection — Analysis & Implementation Proposal

> - Status: **Proposal** 
> - Target: `POST /api/v1/documents` 
> - Related roadmap item: *"API duplicate detection: Reuse the CLI's already-processed check in `POST /api/v1/documents`"*

### 1. Problem statement

Cuurrently *Duplicate detection / `--force`* is available only for the **CLI** (`rag_cli.py`), not for the **REST API** (`api_server.py`):

As a result, re-uploading the same PDF through the API silently re-runs the whole pipeline (extract → markdown → chunk → embed → store) with no warning, wasting time and CPU/embedding work, even though the outcome is just an idempotent overwrite.

### 2. How the CLI does it today

`rag_cli.py` → `build()` performs a **filesystem check** *before* importing the heavy pipeline modules:

```python
base_file_name = os.path.basename(pdf_path)
embedded_jsonl_path = f"./json_chunks/{os.path.splitext(base_file_name)[0]}_embedded.jsonl"

if os.path.exists(embedded_jsonl_path) and not force:
    # warn and exit early
    raise typer.Exit(0)
```

Characteristics:
- **Signal:** existence of `./json_chunks/<stem>_embedded.jsonl`.
- **Override:** `--force` / `-f`.
- **Scope:** per *filename stem* (not per collection).

### 3. Why the CLI approach cannot be copied directly to the API

The API pipeline (`src/api/routes/documents.py` → `_process_document`) differs from the CLI in important ways:

1. **No JSONL files are written.** The API goes straight from `embed_chunks()` to `build_vectorstore()`. There is no `json_chunks/<stem>_embedded.jsonl` to check for. The CLI's filesystem signal simply does not exist here.
2. **Uploads are namespaced with a UUID.** Files are saved as `uploads/{job_id}_{filename}`, so the on-disk name is never a stable identifier.
3. **Processing is asynchronous.** The endpoint returns `202 Accepted` immediately and work happens in a `BackgroundTask`. A duplicate check buried inside the background task would be discovered *after* the client already got a success response — too late to be useful.
4. **Collections matter.** The same PDF can legitimately be ingested into two different collections (`product_docs`, `tech_docs`, …). Duplicate detection must therefore be scoped to **(collection_name, doc_id)**, not just the filename.

#### What *is* already there
`build_vectorstore(..., doc_id=...)` namespaces every chunk id as `"{doc_id}_chunk_{i}"`, where `doc_id = Path(original_filename).stem`. This gives us a **stable, authoritative identifier already living in ChromaDB** — the ideal signal for duplicate detection.

### 4. Recommended approach — query ChromaDB (authoritative)

Instead of relying on side-car JSONL files, **ask ChromaDB whether the document already exists** in the target collection by probing for its first chunk id (`"{doc_id}_chunk_0"`).

Advantages:
- Survives server restarts (no in-memory state).
- Scoped per collection automatically.
- Single source of truth — matches exactly what `build_vectorstore` writes.
- No dependency on CLI-only JSONL artifacts.

The check must run **synchronously inside the endpoint**, before the job is queued, so the client gets an immediate, actionable `409 Conflict`.

#### 4.1 Helper — `document_exists()` (in `src/api/dependencies.py`)

```python
def document_exists(doc_id: str, collection_name: str, persist_dir: str = CHROMA_PERSIST_DIR) -> bool:
    """
    Return True if a document with this doc_id already has chunks stored
    in the given collection. Probes for the deterministic first chunk id
    produced by build_vectorstore ("{doc_id}_chunk_0").
    """
    client = get_chroma_client(persist_dir)
    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        # Collection doesn't exist yet -> definitely not a duplicate.
        return False

    existing = collection.get(ids=[f"{doc_id}_chunk_0"])
    return bool(existing and existing.get("ids"))
```

> Note: `get_collection` raises if the collection is missing; we treat that as "not a duplicate". Using `get_collection` (not `get_or_create_collection`) avoids creating empty collections as a side effect of a check.

#### 4.2 Add a `force` field to the upload endpoint

`src/api/routes/documents.py` → `upload_document()`:

```python
@router.post("/documents", response_model=DocumentUploadResponse, status_code=202, tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document to process"),
    collection_name: str = Form(default="product_docs", description="Target ChromaDB collection"),
    force: bool = Form(default=False, description="Reprocess even if the document already exists"),
    job_store: Dict[str, ProcessingStatus] = Depends(get_jobs),
) -> DocumentUploadResponse:
    filename = file.filename or "upload.pdf"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'. ...")

    # --- Duplicate detection (before reading/queuing) ---
    doc_id = Path(filename).stem
    if not force and document_exists(doc_id, collection_name):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Document '{filename}' already exists in collection "
                f"'{collection_name}'. Re-upload with force=true to overwrite."
            ),
        )

    contents = await file.read()
    # ... existing size/empty validation, save, queue background task ...
```

#### 4.3 Wire `force` through (optional, for parity)

`force` only affects whether we *block*; the existing `build_vectorstore(doc_id=...)` upsert already overwrites cleanly, so no change to `_process_document` logic is strictly required. Passing `force` through is only needed if you later want different behavior (e.g. delete-then-insert to purge stale chunks when a re-processed PDF produces *fewer* chunks — see Edge cases).

#### 4.4 Import to add

```python
from src.api.dependencies import (
    ALLOWED_EXTENSIONS, CHROMA_PERSIST_DIR, MAX_FILE_SIZE_BYTES, UPLOAD_DIR,
    document_exists,   # <-- new
    get_jobs, jobs, register_job,
)
```

### 5. Client experience

```bash
# First upload — 202 Accepted
curl -X POST http://localhost:8000/api/v1/documents -F "file=@doc.pdf"

# Second upload of same file/collection — 409 Conflict
curl -X POST http://localhost:8000/api/v1/documents -F "file=@doc.pdf"
# {"detail": "Document 'doc.pdf' already exists in collection 'product_docs'. Re-upload with force=true to overwrite."}

# Force overwrite — 202 Accepted
curl -X POST http://localhost:8000/api/v1/documents -F "file=@doc.pdf" -F "force=true"
```

### 6. Edge cases & considerations

| Case | Behavior / mitigation |
|---|---|
| Same filename, **different** collection | Not a duplicate — check is `(collection, doc_id)` scoped. ✅ |
| Same filename, **different content** | Treated as duplicate (doc_id is filename-based, like the CLI). Document this limitation; optionally hash content for a stronger signal (see §7). |
| Re-process yields **fewer** chunks | `upsert` overwrites `chunk_0..chunk_k` but leaves stale `chunk_k+1..` behind. With `force`, consider `collection.delete(where=...)` by doc_id first. Store `doc_id` in metadata to enable this. |
| Collection not yet created | `document_exists` returns `False` (no false positives). ✅ |
| Concurrent duplicate uploads | Small race window between check and store; acceptable because the final `upsert` is idempotent. |

### 7. Optional enhancements (future)

- **Content-hash detection:** store a SHA-256 of the file in chunk metadata; detect identical *content* even under a different filename, and detect *changed* content under the same filename.
- **Stale-chunk cleanup:** add `doc_id` to chunk metadata and, on `force`, `collection.delete(where={"doc_id": doc_id})` before inserting, so chunk counts never drift.
- **Shared helper with the CLI:** extract an `already_processed(doc_id, collection, persist_dir)` utility into `src/rag/vectorstore.py` and call it from *both* the CLI and the API, so the two interfaces stay in sync.

### 8. Suggested tests (`pytest` + FastAPI `TestClient`)

1. Upload a PDF → `202`; upload again (same collection) → `409`.
2. Upload again with `force=true` → `202`.
3. Upload same PDF into a different `collection_name` → `202` (not a duplicate).
4. `document_exists()` returns `False` for an unknown collection.

### 9. Summary of changes

| File | Change |
|---|---|
| `src/api/dependencies.py` | Add `document_exists()` helper (ChromaDB probe). |
| `src/api/routes/documents.py` | Add `force` form field; run `document_exists()` check → `409`; import helper. |
| `README.md` | Flip the ❌ to ✅ in the *Choosing an Interface* table; document `force` field and `409` error code. |
| `tests/` (new) | Add duplicate-detection tests. |

This keeps the API's asynchronous design intact, reuses the identifier (`doc_id`) that `build_vectorstore` already relies on, and gives API clients the same safety the CLI users already enjoy — without depending on CLI-only JSONL files.

