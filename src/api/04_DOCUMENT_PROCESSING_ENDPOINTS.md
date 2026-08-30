## FastAPI Learning Notes: Part 4 - Document Processing Endpoints

This note covers:
- Upload workflow architecture
- Why long-running work should be processed in the background
- POST /api/v1/documents
- GET /api/v1/documents/{job_id}
- multipart/form-data
- UploadFile and spooled temporary files
- File validation and security considerations
- UUID job IDs
- BackgroundTasks
- Reusing your existing RAG pipeline
- Job tracking dictionaries
- Progress tracking
- Error handling
- TTL cleanup
- QA/Test Engineer test scenarios
- End-to-end testing strategy
- The backend "Job ID + Status Endpoint" pattern used in enterprise systems

### Big Picture

This DOC introduces a common backend pattern:

```text
Upload Request
      |
      v
FastAPI
      |
      +--> Immediate Response
      |
      +--> Long-running Background Processing
```

The workflow becomes:

```text
Upload PDF
     |
     v
Receive Job ID
     |
     v
Check Status
     |
     v
Finished
```

This pattern is used in:

- YouTube uploads
- Jenkins builds
- GitLab pipelines
- AI document ingestion systems
- Cloud deployment systems

---

### Why Not Process Immediately?

Example processing times:

```text
PDF extraction     5s
Chunking           2s
Embedding         20s
Chroma storage     3s
----------------------
Total             30s
```

Waiting for the entire process inside a single HTTP request can lead to:

- Browser timeouts
- Reverse proxy timeouts
- Poor user experience

Instead:

```json
{
  "job_id": "abc123",
  "status": "queued"
}
```

is returned immediately while processing continues in the background.

---

### Endpoint 1: POST /api/v1/documents

Purpose:

```text
Upload a PDF document.
```

Request:

```http
POST /api/v1/documents
Content-Type: multipart/form-data
```

Example upload:

```text
manual.pdf
```

Response:

```json
{
  "job_id": "abc123",
  "status": "queued",
  "filename": "manual.pdf"
}
```

---

### What is multipart/form-data?

JSON is great for text:

```json
{
  "question": "What is RAG?"
}
```

Files require another format:

```http
multipart/form-data
```

Think of it as:

```text
One HTTP request
    |
    +-- field1
    +-- field2
    +-- file
    +-- file metadata
```

This is why `python-multipart` was installed earlier.

---

### UploadFile

FastAPI provides:

```python
from fastapi import UploadFile
```

Example:

```python
async def upload(file: UploadFile):
```

#### Why Not Use bytes?

```python
file: bytes
```

would load the entire file into memory.

For large PDFs this can be expensive.

---

#### Spooled Temporary Files

`UploadFile` uses spooled files:

```text
Small files
    |
    +--> Memory

Large files
    |
    +--> Disk
```

Benefits:

- Lower memory usage
- Better scalability
- More efficient uploads

---

### File Validation

Never trust uploaded files.

#### Extension Validation

Valid:

```text
manual.pdf
```

Invalid:

```text
virus.exe
```

Example check:

```python
if not file.filename.endswith('.pdf'):
```

---

#### File Size Validation

Requirement:

```text
Maximum 50 MB
```

Prevents:

- Huge accidental uploads
- Malicious uploads
- Excessive memory usage
- Disk abuse

---

#### Production Security Note

Checking only the filename is not fully secure.

Production systems often validate:

- MIME type
- File signatures (magic bytes)
- PDF parser validation

For learning projects, extension checks are usually sufficient.

---

### UUID Job IDs

Example:

```python
job_id = uuid4()
```

Result:

```text
8f1cf3d8-e029-4120-a2f7-9c9d39f7d555
```

#### Why UUIDs?

Avoids predictable IDs such as:

```text
1
2
3
4
```

UUIDs are effectively unique and ideal for:

- Jobs
- Sessions
- Documents
- Tracking identifiers

---

### Saving Uploaded Files

Pattern:

```text
./uploads/{job_id}_{filename}
```

Example:

```text
uploads/
    abc123_manual.pdf
```

#### Why Include the Job ID?

Without it:

```text
manual.pdf
manual.pdf
manual.pdf
```

could overwrite each other.

With UUIDs:

```text
abc123_manual.pdf
def456_manual.pdf
ghi789_manual.pdf
```

No collisions occur.

---

### BackgroundTasks

This is one of the most important FastAPI concepts.

Import:

```python
from fastapi import BackgroundTasks
```

Instead of:

```text
Receive request
Process PDF
Return response
```

You do:

```text
Receive request
Return response
Start processing afterward
```

Diagram:

```text
POST /documents
      |
      v
Generate Job ID
      |
      v
Return Response
      |
      v
Background Processing Starts
```

---

### Is It a Full Job Queue?

Not really.

BackgroundTasks run:

```text
Inside the FastAPI process
```

They are excellent for:

- Learning projects
- Small systems
- Internal tools

Large-scale systems often move to:

```text
FastAPI
   |
   +--> Redis Queue
   +--> Celery
   +--> RabbitMQ
```

---

### Processing Pipeline

The API reuses the existing CLI pipeline.

Workflow:

```text
Upload PDF
      |
      v
load_pdf()
      |
      v
pdf_text_to_markdown()
      |
      v
markdown_chunker()
      |
      v
embed_chunks()
      |
      v
build_vectorstore()
```

This is excellent architecture because you reuse business logic instead of rewriting it.

---

### Job Tracking Dictionary

Suggested implementation:

```python
jobs: Dict[str, ProcessingStatus] = {}
```

Example:

```python
{
    'abc123': ProcessingStatus(...),
    'xyz789': ProcessingStatus(...)
}
```

Benefits:

- Simple implementation
- Fast lookups
- Ideal for learning projects

---

### Tracking Progress

Initial:

```json
{
  "status": "pending",
  "progress": 0
}
```

During processing:

```json
{
  "status": "processing",
  "progress": 50
}
```

Completed:

```json
{
  "status": "completed",
  "progress": 100
}
```

---

### Error Handling

Examples:

```text
Corrupted PDF
Embedding model unavailable
Invalid document structure
```

Instead of crashing, return:

```json
{
  "status": "failed",
  "error": "Failed to parse PDF"
}
```

This is how production systems behave.

---

### Endpoint 2: GET /api/v1/documents/{job_id}

Purpose:

```text
Check processing status.
```

Example:

```http
GET /api/v1/documents/abc123
```

Response:

```json
{
  "job_id": "abc123",
  "status": "processing",
  "progress": 70
}
```

Later:

```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100
}
```

---

### TTL Cleanup

The guide recommends removing jobs after 24 hours.

Why?

Example:

```text
100 uploads/day
```

After one year:

```text
36,500 job records
```

Most are no longer useful.

Periodic cleanup helps control memory usage.

---

### QA/Test Engineer Perspective

#### File Upload Tests

Valid PDF:

```text
small.pdf
```

Expected:

```http
200 OK
```

#### Oversized File

```text
51 MB PDF
```

Expected:

```http
413 Payload Too Large
```

or a validation failure.

---

### Job Lifecycle Tests

Upload:

```http
POST /documents
```

Verify:

```json
{
  "job_id": "...",
  "status": "queued"
}
```

Poll status endpoint:

```http
GET /documents/{job_id}
```

Expected progression:

```text
queued
processing
completed
```

---

### End-to-End Test

A valuable integration scenario:

```text
Upload PDF
      |
      v
Wait for completion
      |
      v
Ask question
      |
      v
Verify answer comes from uploaded document
```

This is an excellent Robot Framework E2E test candidate.

---

### Key Takeaway

> 'Part 4 - Document Processing Endpoints' introduces one of the most important backend patterns: create a job, return a tracking ID immediately, process work in the background, and expose a status endpoint.

This pattern is used throughout modern software systems, including:

- Jenkins pipelines
- GitLab CI jobs
- Azure DevOps builds
- Video processing platforms
- AI ingestion services
- RAG indexing pipelines
