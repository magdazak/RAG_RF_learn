## FastAPI and `python-multipart` for a RAG API

Great first step. As a test automation engineer, you're actually in a very good position to learn FastAPI because a lot of concepts will feel familiar: requests, responses, validation, fixtures/dependencies, mocking, status codes, etc.

### 1. What is FastAPI?

**FastAPI** is a modern Python framework for building REST APIs.

Think of it as:

> Flask + automatic validation + automatic API documentation + type hints

A minimal example:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "Hello World"}
```

When you run it, FastAPI automatically gives you:

- HTTP endpoint (`GET /hello`)
- JSON serialization
- Validation
- Interactive Swagger UI documentation
- OpenAPI specification

#### How big is it?

It's actually quite lightweight:

- Core framework itself is relatively small.
- Built on top of:
  - **Starlette** (web framework)
  - **Pydantic** (validation)
- Widely used in ML/AI projects because it's easy to expose models through APIs.

For your RAG project:

```text
CLI user
   |
   v
FastAPI
   |
   v
Your existing RAG pipeline
   |
   +--> Chroma
   +--> Embeddings
   +--> Ollama
```

You'll simply replace:

```bash
python main.py ask "What is RAG?"
```

with:

```http
POST /query
{
   "question": "What is RAG?"
}
```

---

### 2. What is `python-multipart`?

This package enables FastAPI to receive **uploaded files**.

Without it:

```python
from fastapi import UploadFile
```

will not work.

Example:

```python
@app.post("/upload")
async def upload(file: UploadFile):
    ...
```

A client can send:

```http
POST /upload
Content-Type: multipart/form-data
```

with:

```text
manual.pdf
requirements.docx
specification.txt
```

FastAPI internally uses `python-multipart` to parse that data.

#### How big is it?

Very small.

Its only job is parsing multipart form requests.

You usually don't interact with it directly.

Think of it as:

> "The engine behind file uploads."

---

## Learning Point 1
### FastAPI uses Pydantic for automatic validation

This is one of FastAPI's biggest superpowers.

You create a model:

```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str
    collection: str
```

Then:

```python
@app.post("/query")
async def query(request: QueryRequest):
    ...
```

Client sends:

```json
{
  "question": "What is RAG?",
  "collection": "manuals"
}
```

✅ Accepted

Client sends:

```json
{
  "question": 123
}
```

❌ Rejected automatically

FastAPI returns HTTP 422.

#### Why this is awesome

In Flask you often write:

```python
data = request.json

if "question" not in data:
    return error

if not isinstance(data["question"], str):
    return error
```

In FastAPI:

```python
class QueryRequest(BaseModel):
    question: str
```

Done.

The validation is automatic.

#### Testing perspective

As a QA/Test Engineer you can think of Pydantic as:

> Built-in contract testing for request payloads.

---

## Learning Point 2
### `python-multipart` enables `UploadFile`

Suppose you want users to upload PDFs.

Endpoint:

```python
@app.post("/documents")
async def upload_document(file: UploadFile):
    ...
```

Request:

```http
POST /documents
```

with:

```text
user_manual.pdf
```

Without `python-multipart`:

```text
RuntimeError:
Form data requires "python-multipart" to be installed.
```

With it installed:

```bash
pip install python-multipart
```

FastAPI can parse the file.

#### Why you need this in RAG

Typical workflow:

```text
User uploads PDF
        |
        v
API stores file
        |
        v
Extract text
        |
        v
Create chunks
        |
        v
Generate embeddings
        |
        v
Store in Chroma
```

Most document ingestion APIs rely on file uploads.

---

## Learning Point 3
### Uvicorn runs the server

FastAPI itself is not a web server.

Think of it like this:

```text
FastAPI = Application
Uvicorn = Engine
```

You create:

```python
app = FastAPI()
```

Then start it:

```bash
uvicorn src.api.app:app --reload
```

Meaning:

```text
src/api/app.py
           |
           +--> app = FastAPI()
```

#### `--reload`

Very useful during development.

Whenever you change code and save the file, Uvicorn automatically restarts.

---

## Real-world request flow

#### Query endpoint

```http
POST /query
```

Request:

```json
{
  "question": "How do I configure Jenkins?"
}
```

FastAPI:

1. Receives request
2. Pydantic validates JSON
3. Calls your RAG pipeline
4. Returns answer

Response:

```json
{
  "answer": "According to the documentation..."
}
```

---

#### Upload endpoint

```http
POST /documents
```

Request:

```text
manual.pdf
```

FastAPI:

1. Uses `python-multipart`
2. Parses uploaded file
3. Saves file
4. Runs ingestion
5. Returns success

Response:

```json
{
  "status": "uploaded"
}
```

---

## Mental model for your project

At this stage, don't think:

> "I'm building an API."

Think:

> "I'm wrapping my already-working CLI RAG pipeline with HTTP endpoints."

Your existing code probably already has functions like:

```python
ingest_document(path)
query(question)
```

FastAPI mainly provides a network interface around those functions:

```text
CLI
 |
 +--> query()
 |
 +--> ingest_document()

becomes

POST /query ----------> query()
POST /documents -----> ingest_document()
```

That's why Todo 1 is a great first step: you're only adding the API layer, not changing the RAG logic itself. This separation (RAG engine vs API wrapper) is exactly how production AI services are typically structured.
