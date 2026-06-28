# Web API Implementation Guide

## Overview
This guide walks you through implementing a FastAPI-based web API for the LLM Local RAG pipeline. We'll add HTTP endpoints while keeping the existing CLI functional.

---

## Prerequisites
- Existing RAG pipeline working (CLI functional)
- Python 3.12+
- Understanding of REST APIs and FastAPI basics

---

## Implementation Todos

### ✅ Todo 1: Setup Dependencies and Project Structure
**Goal:** Add required packages and create the API module structure

**Steps:**
1. Add dependencies to `pyproject.toml`:
   - `fastapi>=0.115.0` - Web framework
   - `python-multipart>=0.0.12` - For file upload support

2. Create the API module structure:
   ```
   src/api/
   ├── __init__.py
   ├── app.py              # Main FastAPI application
   ├── models.py           # Pydantic request/response models
   ├── dependencies.py     # Shared dependencies
   └── routes/
       ├── __init__.py
       ├── documents.py    # Document upload endpoints
       ├── query.py        # Query endpoints
       └── collections.py  # Collection management
   ```

3. Update dependencies: `uv sync` or `pip install -e .`

**Learning points:**
- FastAPI uses Pydantic for automatic validation
- python-multipart enables `UploadFile` in FastAPI
- Uvicorn (already installed) will run the server

---

### ✅ Todo 2: Create Core FastAPI Application
**Goal:** Set up the main FastAPI app with basic configuration

**File:** `src/api/app.py`

**What to implement:**
1. Initialize FastAPI app with metadata (title, version, description)
2. Add CORS middleware to allow web UI access
3. Configure API versioning with `/api/v1` prefix
4. Add a health check endpoint: `GET /health`
5. Add request/response logging (optional but recommended)

**File:** `api_server.py` (project root)

**What to implement:**
- Simple entry point to run the FastAPI app with uvicorn
- Example: `uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000`

**Learning points:**
- CORS is crucial for web browsers to access your API
- API versioning (/api/v1) allows future changes without breaking clients
- Health check helps monitoring and container orchestration
- `--reload` auto-restarts server on code changes (dev only)

**Testing:**
```bash
python api_server.py
# Visit http://localhost:8000/docs for auto-generated API documentation
# Visit http://localhost:8000/health
```

---

### ✅ Todo 3: Define Pydantic Models
**Goal:** Create request/response models for type safety and validation

**File:** `src/api/models.py`

**Models to create:**

1. **QueryRequest**
   - `question: str` - The question to ask
   - `collection_name: str = "product_docs"` - ChromaDB collection
   - `n_results: int = 5` - Number of chunks to retrieve
   - `web_search: bool = False` - Enable web search augmentation

2. **QueryResponse**
   - `answer: str` - Generated answer
   - `sources: List[Dict]` - Retrieved chunks with metadata
   - `processing_time: float` - Response time in seconds
   - `used_web_search: bool` - Whether web search was used

3. **DocumentUploadResponse**
   - `job_id: str` - UUID for tracking processing
   - `status: str` - "queued" initially
   - `message: str` - User-friendly message
   - `filename: str` - Uploaded file name

4. **ProcessingStatus**
   - `job_id: str`
   - `status: str` - "pending" | "processing" | "completed" | "failed"
   - `progress: Optional[int]` - Percentage (0-100)
   - `error: Optional[str]` - Error message if failed
   - `collection_name: Optional[str]` - Where document was stored

5. **CollectionInfo**
   - `name: str` - Collection name
   - `document_count: int` - Number of documents
   - `created_at: Optional[str]` - Creation timestamp

**Learning points:**
- Pydantic models provide automatic validation and serialization
- Default values make fields optional
- Type hints enable IDE autocomplete and catch errors early
- FastAPI auto-generates OpenAPI docs from these models

---

### ✅ Todo 4: Implement Document Processing Endpoints
**Goal:** Enable PDF upload and background processing

**File:** `src/api/routes/documents.py`

**Endpoints to create:**

1. **POST /api/v1/documents**
   - Accept `UploadFile` (multipart/form-data)
   - Validate file type (.pdf only) and size (max 50MB)
   - Generate UUID job_id
   - Save file to `./uploads/{job_id}_{filename}`
   - Start background task for processing
   - Return `DocumentUploadResponse` with job_id

2. **GET /api/v1/documents/{job_id}**
   - Return `ProcessingStatus` for the given job
   - Check job tracking dict for status

**Background task logic:**
- Reuse existing pipeline from `main.py build` command:
  1. Load PDF (`load_pdf()`)
  2. Convert to markdown (`pdf_text_to_markdown()`)
  3. Chunk (`markdown_chunker()`)
  4. Embed (`embed_chunks()`)
  5. Store in ChromaDB (`build_vectorstore()`)
- Update job status in tracking dict at each step
- Handle errors gracefully

**Job tracking:**
- Use in-memory dict: `jobs: Dict[str, ProcessingStatus] = {}`
- Consider adding TTL cleanup (delete old jobs after 24h)

**Learning points:**
- `BackgroundTasks` in FastAPI runs async work without blocking response
- `UploadFile` uses spooled temporary files (memory efficient)
- File validation prevents malicious uploads
- UUIDs ensure unique job identifiers

**Testing:**
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@path/to/document.pdf"

curl http://localhost:8000/api/v1/documents/{job_id}
```

---

### ✅ Todo 5: Implement Query Endpoints
**Goal:** Expose the RAG query functionality via HTTP

**File:** `src/api/routes/query.py`

**Endpoint to create:**

**POST /api/v1/query**
- Accept `QueryRequest` model
- Validate collection exists (check ChromaDB)
- Call existing `query_and_generate()` function
- Measure processing time
- Return `QueryResponse` with answer and sources

**Implementation details:**
1. Import `query_and_generate` from `src.rag.vectorstore`
2. Wrap in try/except for error handling
3. Return 404 if collection not found
4. Return 500 for Ollama/processing errors
5. Include source chunks in response (useful for citations)

**Error handling:**
- Collection not found → 404 Not Found
- Ollama not running → 503 Service Unavailable
- Invalid request → 422 Unprocessable Entity (automatic via Pydantic)

**Learning points:**
- FastAPI automatically validates request body against Pydantic model
- `HTTPException` provides proper status codes and error messages
- Time measurement helps track performance
- Returning sources enables "show your work" in UI

**Testing:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I configure the system?",
    "collection_name": "product_docs",
    "n_results": 5
  }'
```

---

### ✅ Todo 6: Implement Collection Management Endpoints
**Goal:** List and manage ChromaDB collections

**File:** `src/api/routes/collections.py`

**Endpoints to create:**

1. **GET /api/v1/collections**
   - Connect to ChromaDB
   - List all collections
   - Get document count for each
   - Return `List[CollectionInfo]`

2. **DELETE /api/v1/collections/{name}**
   - Validate collection exists
   - Add safety check: prevent deletion of default collection
   - Delete collection from ChromaDB
   - Clean up related files (optional)
   - Return success message

**Implementation details:**
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collections = client.list_collections()
```

**Safety considerations:**
- Warn before deleting (could add confirmation parameter)
- Log deletions for audit trail
- Consider soft-delete (mark as deleted, don't actually remove)

**Learning points:**
- ChromaDB client provides list_collections() method
- DELETE should be idempotent (deleting non-existent = 404, not error)
- Collection metadata helps UI display useful info

**Testing:**
```bash
curl http://localhost:8000/api/v1/collections

curl -X DELETE http://localhost:8000/api/v1/collections/test_collection
```

---

### ✅ Todo 7: Testing and Documentation
**Goal:** Verify everything works and document usage

**Testing tasks:**
1. **Manual testing:**
   - Upload a sample PDF → Check job status → Verify in ChromaDB
   - Query the uploaded document → Verify answer quality
   - List collections → Verify uploaded document appears
   - Delete test collection → Verify it's removed

2. **CORS testing:**
   - Access API from browser console
   - Verify no CORS errors in dev tools

3. **Error testing:**
   - Upload non-PDF file (should reject)
   - Query non-existent collection (should 404)
   - Query with Ollama stopped (should error gracefully)

**Documentation tasks:**
1. Update `README.md`:
   - Add "API Usage" section
   - Document all endpoints with examples
   - Add installation instructions for new dependencies
   - Add "Running the API Server" section

2. Create example requests:
   - curl commands for all endpoints
   - Python requests library examples
   - Postman collection (optional)

3. Document environment variables:
   - `API_HOST` - Server host (default: 0.0.0.0)
   - `API_PORT` - Server port (default: 8000)
   - `OLLAMA_HOST` - Ollama server URL (if not localhost)

**Example README section:**
```markdown
## API Usage

### Start the API Server

python api_server.py

The API will be available at http://localhost:8000
Interactive API docs: http://localhost:8000/docs

### Upload a Document

curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@document.pdf"

Response: {"job_id": "abc-123", "status": "queued", ...}

### Query Documents

curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic?"}'
```

**Learning points:**
- FastAPI auto-generates interactive docs at `/docs` (Swagger UI)
- Alternative docs at `/redoc` (ReDoc)
- Testing helps catch edge cases before production
- Good documentation reduces support burden

---

## Success Criteria

- ✅ API server starts without errors
- ✅ Can upload PDF and get job_id
- ✅ Can check upload status
- ✅ Can query and receive answers
- ✅ Can list collections
- ✅ Can delete collections
- ✅ CORS works for web UI
- ✅ Error messages are clear and helpful
- ✅ Existing CLI still works unchanged
- ✅ README documents API usage

---

## Next Steps After Implementation

### Future Enhancements:
1. **WebSocket chat endpoint** - Real-time streaming responses
2. **Authentication** - API keys or JWT tokens
3. **Rate limiting** - Prevent abuse
4. **Persistent job storage** - SQLite instead of in-memory dict
5. **Batch operations** - Upload multiple files
6. **Admin UI** - Web interface for management
7. **Docker deployment** - Containerize the application
8. **Metrics/monitoring** - Prometheus, logging

### WebSocket Chat Preview:
```python
@app.websocket("/api/v1/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        question = await websocket.receive_text()
        # Stream response token by token
        for token in generate_streaming(question):
            await websocket.send_text(token)
```

---

## Troubleshooting

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`
- **Solution:** Run `uv sync` or `pip install fastapi python-multipart`

**Problem:** CORS errors in browser
- **Solution:** Check CORS middleware configuration in app.py

**Problem:** "Collection not found" error
- **Solution:** Upload a document first, or check collection name

**Problem:** Ollama connection errors
- **Solution:** Ensure Ollama is running (`ollama serve`)

**Problem:** File upload fails
- **Solution:** Check file size limit, ensure .pdf extension

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [ChromaDB API Reference](https://docs.trychroma.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

---

**Ready to start? Let's begin with Todo 1! 🚀**
