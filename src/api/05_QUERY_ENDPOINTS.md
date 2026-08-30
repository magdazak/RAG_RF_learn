## FastAPI Learning Notes: Query Endpoints

### Goal

Expose the existing RAG query functionality through a REST API.

Current CLI usage:

```bash
python main.py query "How do I configure the system?"
```

Future API usage:

```http
POST /api/v1/query
```

Request:

```json
{
  "question": "How do I configure the system?"
}
```

Response:

```json
{
  "answer": "...",
  "sources": [...]
}
```

---

## Big Picture

This endpoint is the heart of the RAG service.

Request flow:

```text
Client
   |
   v
POST /query
   |
   v
Pydantic Validation
   |
   v
Check Collection Exists
   |
   v
query_and_generate()
   |
   +--> Chroma Search
   |
   +--> Retrieve Chunks
   |
   +--> Ollama
   |
   v
Generate Answer
   |
   v
Return Response
```

---

## QueryRequest

The request model:

```python
class QueryRequest(BaseModel):
    question: str
    collection_name: str = "product_docs"
    n_results: int = 5
    web_search: bool = False
```

Incoming JSON:

```json
{
  "question": "How do I configure Jenkins?"
}
```

FastAPI automatically converts the JSON into a Python object.

No manual JSON parsing is required.

---

## query_and_generate()

Example import:

```python
from src.rag.vectorstore import query_and_generate
```

### Good Architecture

```text
RAG Logic
     |
     +--> query_and_generate()

FastAPI
     |
     +--> calls query_and_generate()
```

FastAPI exposes the functionality.

The RAG implementation remains separate and reusable.

### Avoid

Putting retrieval and generation logic directly into the endpoint itself.

Keeping business logic separate improves:

- Maintainability
- Testing
- Reusability

---

## Collection Validation

Example request:

```json
{
  "question": "Hello",
  "collection_name": "banana"
}
```

If the collection does not exist, return:

```http
404 Not Found
```

Response:

```json
{
  "detail": "Collection not found"
}
```

This provides clearer feedback than allowing ChromaDB to fail later.

---

## Why 404?

Many people think 404 only means:

```text
Page not found
```

In REST APIs it means:

```text
Requested resource does not exist.
```

Examples:

```text
GET /users/999
```

or

```text
Collection does not exist.
```

Both are valid uses of HTTP 404.

---

## Measuring Processing Time

Example:

```python
start = time.time()

answer = query_and_generate(...)

elapsed = time.time() - start
```

Response:

```json
{
  "processing_time": 2.7
}
```

---

## Why Measure Time?

Performance matters in AI systems.

Example timing:

```text
Chroma Search     0.2s
Ollama           1.8s
Formatting       0.1s
----------------------
Total            2.1s
```

Tracking processing time helps:

- Monitor performance
- Detect regressions
- Benchmark improvements
- Compare models

---

## Sources

Instead of returning only:

```json
{
  "answer": "Do X, Y and Z"
}
```

Return:

```json
{
  "answer": "Do X, Y and Z",
  "sources": [
    {
      "document": "manual.pdf",
      "page": 15
    }
  ]
}
```

---

## Why Sources Matter

Without sources:

```text
Trust me.
```

With sources:

```text
Here is the answer.
Here is where it came from.
```

This increases trust and makes verification easier.

---

## Traditional LLM vs RAG

Traditional LLM:

```text
Question
   |
   v
Model
   |
   v
Answer
```

RAG:

```text
Question
   |
   v
Retrieve Sources
   |
   v
Model
   |
   v
Answer + Sources
```

Showing source chunks is one of the key benefits of RAG.

---

## Error Handling

### Invalid Request

Example:

```json
{
  "question": 123
}
```

Response:

```http
422 Unprocessable Entity
```

Generated automatically by Pydantic.

---

### Collection Not Found

Example:

```json
{
  "question": "Hello",
  "collection_name": "does_not_exist"
}
```

Response:

```http
404 Not Found
```

---

### Ollama Not Running

If Ollama is unavailable:

```http
503 Service Unavailable
```

Reason:

```text
The service exists but is temporarily unavailable.
```

---

### Unexpected Errors

Examples:

- Programming bug
- Database problem
- Unexpected exception

Response:

```http
500 Internal Server Error
```

---

## HTTPException

Import:

```python
from fastapi import HTTPException
```

Example:

```python
raise HTTPException(
    status_code=404,
    detail="Collection not found"
)
```

Response:

```json
{
  "detail": "Collection not found"
}
```

This is the standard FastAPI mechanism for returning API errors.

---

## Learning Point 1
### Automatic Validation

Pydantic validates requests before endpoint logic executes.

Example model:

```python
class QueryRequest(BaseModel):
    question: str
```

Invalid request:

```json
{
  "question": 123
}
```

FastAPI automatically returns:

```http
422
```

without custom validation code.

---

## Learning Point 2
### HTTPException

APIs should communicate errors using proper HTTP status codes.

Examples:

```http
404 Not Found
422 Unprocessable Entity
500 Internal Server Error
503 Service Unavailable
```

This helps:

- Frontends
- Monitoring tools
- Automated tests
- API consumers

understand what happened.

---

## Learning Point 3
### Time Measurement

Performance is a feature.

Including:

```python
processing_time
```

allows you to:

- Monitor latency
- Detect slowdowns
- Compare models
- Measure improvements

---

## Learning Point 4
### Show Your Work

Returning source chunks provides traceability.

Example:

```json
{
  "answer": "...",
  "sources": [...]
}
```

Possible UI display:

```text
Answer
--------------------------------
According to the documentation...

Sources:
- manual.pdf page 12
- setup_guide.pdf page 3
```

This helps users verify and trust the answer.

---

## QA / Test Engineer Perspective

### Happy Path

Request:

```json
{
  "question": "How do I configure the system?"
}
```

Verify:

```text
HTTP 200
answer exists
sources exist
processing_time > 0
```

---

### Missing Question

```json
{}
```

Expected:

```http
422
```

---

### Invalid Type

```json
{
  "question": 123
}
```

Expected:

```http
422
```

---

### Missing Collection

```json
{
  "question": "Hello",
  "collection_name": "does_not_exist"
}
```

Expected:

```http
404
```

---

### Ollama Down

Stop Ollama.

Expected:

```http
503
```

---

### Performance Testing

Track:

```text
processing_time
```

and verify it remains within acceptable limits.

---

## Key Takeaway

> 'FastAPI: Query Endpoints' is where your RAG engine becomes a proper REST service.

The endpoint transforms:

```text
Question
    |
    v
RAG Engine
    |
    v
Answer + Sources
```

into an API that can be consumed by:

- React frontends
- Robot Framework tests
- Other backend services
- Future AI agents
- Swagger UI
