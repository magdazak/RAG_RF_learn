## FastAPI Todo 2 Learning Notes

### Big Picture

After Todo 2 you'll have something like:

```text
Browser
   |
   v
FastAPI
   |
   v
/api/v1/query
/api/v1/documents
/api/v1/collections
/health
```

and it will be running continuously as a service:

```bash
http://localhost:8000
```

rather than:

```bash
python main.py ask ...
```

---

## 1. FastAPI App Metadata

Example:

```python
app = FastAPI(
    title="Local RAG API",
    version="1.0.0",
    description="REST API for document ingestion and querying"
)
```

At first glance this looks cosmetic.

It's actually much more important.

### What does it do?

FastAPI automatically generates:

```text
Swagger UI
OpenAPI specification
```

available at:

```text
http://localhost:8000/docs
```

and

```text
http://localhost:8000/openapi.json
```

The metadata appears there.

### Why developers care

Imagine your company exposes 50 APIs.

Without documentation:

```text
How do I call it?
What endpoint exists?
What payload is expected?
```

Nobody knows.

With FastAPI:

```text
Open browser
Try endpoint
Read schema
Execute request
```

Everything is self-documenting.

### QA perspective

Think about Swagger UI as:

> An automatically generated test client.

You can test endpoints without Postman or Robot Framework.

---

## 2. CORS Middleware

### What problem does CORS solve?

Suppose:

API:

```text
http://localhost:8000
```

Frontend:

```text
http://localhost:3000
```

The browser sees these as different origins.

A web page running on:

```text
localhost:3000
```

tries:

```javascript
fetch("http://localhost:8000/query")
```

Browser says:

```text
Blocked by CORS policy
```

even though the API works perfectly.

### Why?

Browsers enforce security restrictions.

Without them, a malicious website could silently call APIs using your browser session.

### CORS Middleware

You explicitly tell browsers:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
```

Meaning:

```text
I allow requests from these origins.
```

### Development vs Production

Development:

```python
allow_origins=["*"]
```

Very common.

Production:

```python
allow_origins=[
    "https://my-rag-ui.company.com"
]
```

Much safer.

### QA perspective

You'll probably encounter this situation:

```text
Swagger works
Postman works
Browser fails
```

95% chance:

```text
CORS problem
```

---

## 3. API Versioning

Guide suggests:

```text
/api/v1
```

Example:

```text
/api/v1/query
/api/v1/documents
/api/v1/collections
```

### Why version APIs?

Imagine today you have:

```json
{
  "answer": "RAG means..."
}
```

Next year you want:

```json
{
  "answer": "RAG means...",
  "sources": [...]
}
```

or maybe change request format entirely.

#### Problem

Existing clients expect:

```json
{
  "answer": "..."
}
```

Changing behavior breaks clients.

#### Solution

Keep old version:

```text
/api/v1/query
```

Create new version:

```text
/api/v2/query
```

Clients migrate when ready.

### Real-world example

Many large APIs expose:

```text
/v1
/v2
/v3
```

for years simultaneously.

### QA perspective

Versioning is essentially:

> Backward compatibility management.

---

## 4. Health Check Endpoint

Example:

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

### Why is this needed?

Imagine your API crashes.

Users see:

```text
502 Bad Gateway
```

Operations team sees:

```text
Something is wrong
```

But nobody knows what.

A health endpoint provides a quick answer:

```text
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

means:

```text
App is alive.
```

### Basic Health Check

Only verifies:

```text
FastAPI process is running
```

### Advanced Health Check

Also verifies:

```text
Chroma reachable
Ollama reachable
Embedding model loaded
Disk space available
```

Example:

```json
{
  "api": "ok",
  "ollama": "ok",
  "vector_db": "ok"
}
```

### QA perspective

Your first automated API test will probably become:

```robot
GET /health

Should Be Equal
    ${response.status_code}
    200
```

---

## 5. Request/Response Logging

Not mandatory but extremely useful.

### What is logging?

Recording API activity.

Example:

```text
2026-02-15 10:30:00
POST /query

Question:
How do I configure Jenkins?
```

Then:

```text
200 OK
Response time: 1.2s
```

### Why developers love logs

When a bug appears:

```text
User: system doesn't work
```

Logs answer:

```text
What request?
What endpoint?
What error?
How long did it take?
```

### RAG-specific examples

Useful things to log:

```text
Collection selected
Question
Retrieved chunks
Response duration
Model used
```

Not necessarily the full documents.

### QA perspective

Logs are often:

> The first thing you inspect after a test failure.

---

## api_server.py

This file is basically a startup shortcut.

Instead of:

```bash
uvicorn src.api.app:app --reload
```

you can run:

```bash
python api_server.py
```

Internally:

```python
import uvicorn

uvicorn.run(...)
```

### Why have a wrapper?

Later you may configure:

```text
host
port
logging
environment variables
SSL
```

in one place.

---

## --reload

One of the most useful developer features.

Without:

```text
Edit code
Stop server
Start server
```

every time.

With:

```bash
uvicorn ... --reload
```

Workflow:

```text
Edit file
Save
Server restarts automatically
```

### Production Warning

Never use:

```bash
--reload
```

in production.

It's intended purely for development because it continuously watches files and restarts processes.

---

## Mental Model for Todo 2

After completing Todo 2, your architecture becomes:

```text
                 Browser
                     |
                     |
                 (CORS)
                     |
                     v
            FastAPI Application
                     |
     +---------------+---------------+
     |                               |
     v                               v
  /health                     /api/v1/*
                                    |
                                    v
                           Existing RAG Engine
                                    |
                        +-----------+-----------+
                        |                       |
                        v                       v
                     Chroma                  Ollama
```

The most important thing to understand is that FastAPI is not your RAG system. FastAPI is simply the network-facing layer. Your RAG pipeline remains the core business logic, and FastAPI exposes it through HTTP endpoints. That's an architectural separation you'll see in almost every production AI service.
