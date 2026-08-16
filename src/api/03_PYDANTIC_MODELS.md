## FastAPI Todo 3 Learning Notes: Pydantic Models

### Big Picture

Without Pydantic:

```python
@app.post("/query")
async def query(data: dict):
    ...
```

Anything can arrive:

```json
{
  "question": 123
}
```

or

```json
{
  "foo": "bar"
}
```

You must validate everything manually.

With Pydantic:

```python
class QueryRequest(BaseModel):
    question: str
```

FastAPI automatically checks:

- Does `question` exist?
- Is it a string?
- Is the JSON valid?

before your code runs.

---

### Think Like an API Contract

Imagine your API is a function.

Without a contract:

```text
User can send anything.
```

With a contract:

```text
Input:
    question: string

Output:
    answer: string
```

Everyone knows exactly what is expected.

---

### QueryRequest

This model describes:

```text
What client must send
```

Example:

```python
class QueryRequest(BaseModel):
    question: str
    collection_name: str = "product_docs"
    n_results: int = 5
    web_search: bool = False
```

Example request:

```json
{
  "question": "How do I configure Jenkins?"
}
```

This is valid because defaults exist.

Internally FastAPI creates:

```json
{
  "question": "How do I configure Jenkins?",
  "collection_name": "product_docs",
  "n_results": 5,
  "web_search": false
}
```

#### Why defaults are powerful

Without defaults:

```python
question: str
collection_name: str
n_results: int
web_search: bool
```

Every user would need to send all fields.

Defaults make the API friendlier and easier to use.

---

### QueryResponse

This model describes:

```text
What the API returns
```

Example:

```python
class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    processing_time: float
    used_web_search: bool
```

Example response:

```json
{
  "answer": "RAG stands for Retrieval Augmented Generation",
  "sources": [
    {
      "document": "manual.pdf",
      "chunk": "..."
    }
  ],
  "processing_time": 2.3,
  "used_web_search": false
}
```

#### Why define response models?

Responses should be predictable.

If tomorrow you accidentally return:

```json
{
  "answer": null
}
```

Pydantic can catch the inconsistency.

---

### DocumentUploadResponse

This is for upload workflows.

Client uploads:

```text
manual.pdf
```

API responds:

```json
{
  "job_id": "2b044df1",
  "status": "queued",
  "message": "Document accepted",
  "filename": "manual.pdf"
}
```

#### Why Job IDs?

Document processing may take time:

- parsing
- chunking
- embeddings
- storage

Rather than keeping the user waiting, the API returns a job identifier.

Later:

```text
GET /status/{job_id}
```

can be used to check progress.

---

### ProcessingStatus

This model tracks long-running jobs.

Example:

```json
{
  "job_id": "abc123",
  "status": "processing",
  "progress": 65
}
```

### Typical states

```text
pending
processing
completed
failed
```

This is a common backend pattern.

---

### Optional Fields

Example:

```python
progress: Optional[int]
```

means:

```python
progress: int | None
```

Valid examples:

```json
{
  "progress": 50
}
```

or

```json
{
  "progress": null
}
```

Similarly:

```python
error: Optional[str]
```

Normal case:

```json
{
  "error": null
}
```

Failure case:

```json
{
  "error": "Failed to parse PDF"
}
```

---

### CollectionInfo

This model represents metadata about a Chroma collection.

Example:

```json
{
  "name": "product_docs",
  "document_count": 245,
  "created_at": "2026-07-01T10:00:00"
}
```

It describes the collection itself, not the documents inside it.

---

### Type Hints

Examples:

```python
question: str
count: int
web_search: bool
```

Type hints become very important in FastAPI.

#### IDE Benefits

Example:

```python
request.question
```

Your IDE knows it is a string and provides autocomplete.

If you accidentally write:

```python
request.quesiton
```

many IDEs will immediately flag the typo.

---

### Testing Perspective

Pydantic automatically handles many negative test scenarios.

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

Examples:

#### Positive Test

```json
{
  "question": "What is RAG?"
}
```

✅ 200 OK

#### Invalid Type

```json
{
  "question": 123
}
```

✅ 422

#### Missing Field

```json
{}
```

✅ 422

Much of the validation comes for free.

---

### OpenAPI Magic

From:

```python
class QueryRequest(BaseModel):
    question: str
    n_results: int = 5
```

FastAPI automatically generates Swagger documentation.

In `/docs` you'll see something similar to:

```text
QueryRequest
-------------------------
question    string
n_results   integer
```

without writing documentation manually.

---

### Why 'Part 3 - Pydantic models' Matters So Much

After Part 3 you'll have:

```text
FastAPI App
    |
    +--> QueryRequest
    |
    +--> QueryResponse
    |
    +--> DocumentUploadResponse
    |
    +--> ProcessingStatus
    |
    +--> CollectionInfo
```

These models become the shared language between:

- Frontend
- API
- Swagger UI
- Automated tests
- Future developers
- Future AI agents

#### Key Mental Model

> Pydantic models are not just Python classes. They are API contracts, validators, documentation generators, type definitions, and testable schemas all at the same time.

That is why FastAPI developers spend significant effort designing models before implementing endpoint logic. In many projects, the models effectively define the API design itself.

<details>
<summary><strong>Pydantic Query deep dive</strong></summary>

### Understanding a Pydantic Model in FastAPI

#### Example Model

```python
class QueryRequest(BaseModel):
    """Request body for asking a question against a collection."""

    question: str = Field(
        ...,
        description="The question to ask",
        min_length=1,
    )

    collection_name: str = Field(
        default="product_docs",
        description="ChromaDB collection to query",
    )

    n_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of chunks to retrieve",
    )

    web_search: bool = Field(
        default=False,
        description="Enable web search augmentation",
    )
```

---

### Imports Explained

```python
from pydantic import BaseModel, Field
```

#### BaseModel

`BaseModel` is the foundation of every Pydantic model.

It provides:

- Automatic validation
- Type checking
- Serialization to JSON
- OpenAPI schema generation
- Swagger documentation integration

Without `BaseModel`, the class would just be a normal Python class.

---

#### Field

`Field()` allows you to add:

- Default values
- Validation rules
- Documentation metadata
- Constraints such as minimum and maximum values

---

#### QueryRequest Model

This model defines the expected JSON structure for a query request.

Example request:

```json
{
  "question": "What is RAG?"
}
```

FastAPI automatically converts this JSON into a `QueryRequest` object.

---

### question Field

```python
question: str = Field(
    ...,
    description="The question to ask",
    min_length=1
)
```

#### Type

```python
question: str
```

The value must be a string.

Valid:

```json
{
  "question": "What is RAG?"
}
```

Invalid:

```json
{
  "question": 123
}
```

FastAPI returns HTTP 422 automatically.

#### The `...` (Ellipsis)

```python
Field(...)
```

Means:

```text
This field is REQUIRED.
```

Missing field:

```json
{}
```

Results in validation failure.

#### Description

```python
description="The question to ask"
```

Appears automatically in Swagger documentation.

#### min_length=1

```python
min_length=1
```

Prevents empty strings.

Invalid:

```json
{
  "question": ""
}
```

---

### collection_name Field

```python
collection_name: str = Field(
    default="product_docs",
    description="ChromaDB collection to query"
)
```

Default value:

```text
product_docs
```

If the client omits the field, FastAPI automatically uses this value.

Example request:

```json
{
  "question": "What is RAG?"
}
```

Internally becomes:

```json
{
  "question": "What is RAG?",
  "collection_name": "product_docs"
}
```

---

### n_results Field

```python
n_results: int = Field(
    default=5,
    ge=1,
    le=50,
    description="Number of chunks to retrieve"
)
```

#### Default Value

```python
default=5
```

If omitted, 5 chunks are retrieved.

#### ge=1

```python
ge=1
```

Means:

```text
Greater than or equal to 1
```

Valid:

```json
{ "n_results": 1 }
```

Invalid:

```json
{ "n_results": 0 }
```

#### le=50

```python
le=50
```

Means:

```text
Less than or equal to 50
```

Valid:

```json
{ "n_results": 50 }
```

Invalid:

```json
{ "n_results": 51 }
```

#### Why This Matters

These limits protect your API from invalid or expensive requests.

---

### web_search Field

```python
web_search: bool = Field(
    default=False,
    description="Enable web search augmentation"
)
```

Valid values:

```json
{
  "web_search": true
}
```

or

```json
{
  "web_search": false
}
```

Typical meaning:

```text
False -> Use only ChromaDB
True  -> Use ChromaDB + Web Search
```

---

### Automatic Validation Example

Request:

```json
{
  "question": "",
  "n_results": 100
}
```

Validation errors:

- Question is empty (`min_length=1`)
- n_results exceeds limit (`le=50`)

FastAPI automatically returns HTTP 422.

No custom validation code is required.

---

### Swagger Documentation Benefits

Because you used `Field()`, FastAPI automatically documents:

- Field descriptions
- Default values
- Validation constraints
- Data types

Your `/docs` page becomes significantly more useful.

---

### QA / Test Automation Perspective

The model already defines many test cases.

#### Positive Test

```json
{
  "question": "What is RAG?"
}
```

Expected:

```http
200 OK
```

#### Missing Required Field

```json
{}
```

Expected:

```http
422 Unprocessable Entity
```

#### Empty Question

```json
{
  "question": ""
}
```

Expected:

```http
422 Unprocessable Entity
```

#### Invalid Type

```json
{
  "question": 123
}
```

Expected:

```http
422 Unprocessable Entity
```

#### Boundary Tests

Lower boundary:

```json
{
  "question": "test",
  "n_results": 1
}
```

Expected:

```http
200 OK
```

Upper boundary:

```json
{
  "question": "test",
  "n_results": 50
}
```

Expected:

```http
200 OK
```

Outside boundaries:

```json
{
  "question": "test",
  "n_results": 0
}
```

or

```json
{
  "question": "test",
  "n_results": 51
}
```

Expected:

```http
422 Unprocessable Entity
```

---

### Key Takeaway

> A Pydantic model is much more than a Python class. It acts as an API contract, a validator, a documentation source, a schema definition, and the first layer of automated testing.

This is why Pydantic is one of the most powerful features of FastAPI.

</details>