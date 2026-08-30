## FastAPI Learning Notes: Part 2 - Creating the Core FastAPI App

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

<details>
<summary><strong>A bit more about uvicorn</strong></summary>

## Understanding Uvicorn for FastAPI

Uvicorn is actually a great topic to understand because when people start with FastAPI, they often focus on FastAPI itself and forget that something has to actually listen on the network and handle HTTP connections.

A useful mental model is:

```text
Your RAG code
     |
     v
FastAPI
     |
     v
Uvicorn
     |
     v
Network / Browser / Postman
```

FastAPI defines what should happen when a request arrives.

Uvicorn is what actually receives the request from the network.

---

## What is Uvicorn?

Uvicorn is an **ASGI web server** for Python.

Think:

```text
FastAPI = Application
Uvicorn = Server
```

Similar to:

```text
Chrome = Browser
Windows/Linux = Operating System
```

Chrome needs an OS to run on.

FastAPI needs a server to run on.

---

## What does Uvicorn actually do?

When you start:

```bash
uvicorn src.api.app:app
```

Uvicorn:

1. Opens port 8000
2. Listens for incoming HTTP requests
3. Receives requests from clients
4. Passes them to FastAPI
5. Gets the response from FastAPI
6. Sends the response back

Example:

```text
Browser
   |
GET /health
   |
   v
Uvicorn
   |
   v
FastAPI
   |
   v
health()
   |
   v
{"status":"healthy"}
   |
   v
Uvicorn
   |
   v
Browser
```

---

## What does this command mean?

```bash
uvicorn src.api.app:app --reload
```

#### `src.api.app`

This is Python module notation.

Equivalent to:

```text
src/api/app.py
```

#### `:app`

Means:

```python
app = FastAPI()
```

inside that file.

Example:

```python
# src/api/app.py

from fastapi import FastAPI

app = FastAPI()
```

Uvicorn loads that object.

---

## Why FastAPI Likes Uvicorn

FastAPI is built around modern Python async programming.

Uvicorn is designed for:

```python
async def query():
    ...
```

and handles many concurrent requests efficiently.

This makes it very popular for:

- APIs
- AI services
- Chatbots
- RAG systems
- ML inference endpoints

---

## WSGI vs ASGI

**WSGI** and **ASGI** are Python interface standards that connect a web server to an application. WSGI (Web Server Gateway Interface) is older, synchronous, and handles one request at a time. ASGI (Asynchronous Server Gateway Interface) is a newer, asynchronous standard that handles multiple concurrent requests and WebSocket connections.

**_Key Differences_**:
- **Operation Model:** WSGI is synchronous and blocking; ASGI is asynchronous and supports async/await.
- **Supported Protocols:** WSGI only supports HTTP; ASGI supports HTTP/1.1, HTTP/2, WebSockets, and SSE.
- **Concurrency:** WSGI requires multiple threads or processes for parallel tasks, while ASGI handles multiple connections within a single event loop.
- **Server Examples:** 
   - WSGI: Gunicorn, uWSGI, mod_wsgi. 
   - ASGI: Uvicorn, Daphne, Granian.
- **Framework Examples:** 
   - WSGI: Flask, Django (traditionally), Bottle. 
   - ASGI: FastAPI, Starlette, Django (version 3.0+).

#### Older generation

```text
Flask
Django (traditional)
      |
      v
     WSGI
```

#### Modern generation

```text
FastAPI
Starlette
Quart
      |
      v
     ASGI
```

### What ASGI gives you

Support for:

- `async def`
- WebSockets
- Streaming
- High concurrency
- Long-running AI requests

For a RAG application, ASGI is particularly useful because LLM calls can take several seconds.

---

## What is Async?

Imagine 100 users ask questions at the same time.

Without async:

```text
Request 1 -> wait
Request 2 -> wait
Request 3 -> wait
```

Everything becomes sequential.

With async:

```text
Request 1 -> Ollama thinking
Request 2 -> Ollama thinking
Request 3 -> Ollama thinking
```

The server can manage many waiting requests simultaneously.

For AI applications this is a huge benefit.

---

## The Magic of `--reload`

One of the best development features.

Without it:

```text
Edit code
Stop server
Start server
```

again and again.

With:

```bash
uvicorn src.api.app:app --reload
```

Workflow becomes:

```text
Edit file
Save
Uvicorn notices change
Server restarts automatically
```

Very convenient when developing APIs.

---

## Why Not Use `--reload` In Production?

Because Uvicorn constantly watches files.

Watching files means:

- additional CPU usage
- additional memory usage
- extra process management

Production servers do not need that.

Typical production command:

```bash
uvicorn src.api.app:app
```

or

```bash
gunicorn -k uvicorn.workers.UvicornWorker
```

for larger deployments.

---

## Host and Port

You will often see:

```bash
uvicorn src.api.app:app     --host 0.0.0.0     --port 8000
```

#### Port

```text
localhost:8000
```

The port identifies the service.

Examples:

```text
8000 -> FastAPI
3000 -> React
5432 -> PostgreSQL
```

#### Host

##### Local only

```bash
--host 127.0.0.1
```

Only your own machine can access it.

##### Accessible from network

```bash
--host 0.0.0.0
```

Listen on all network interfaces.

Useful for:

- Docker
- Kubernetes
- VMs
- Other machines in the network

---

## Uvicorn Logs

When started:

```text
INFO: Started server process
INFO: Waiting for application startup
INFO: Application startup complete
INFO: Uvicorn running on http://127.0.0.1:8000
```

When requests arrive:

```text
127.0.0.1:52521 - "GET /health HTTP/1.1" 200
```

From a tester's perspective, these logs are extremely useful.

You immediately see:

- endpoint called
- HTTP method
- response code
- basic traffic information

---

## For Your RAG Project

At the beginning:

```bash
python main.py ask "What is RAG?"
```

Later:

```bash
uvicorn src.api.app:app --reload
```

And users will interact through:

```http
POST /api/v1/query
```

instead of a CLI command.

So the simplest way to think about Uvicorn is:

> FastAPI is your API application. Uvicorn is the web server that exposes that application to the outside world. Without Uvicorn, your FastAPI code exists, but nobody can send HTTP requests to it.

</details>

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
