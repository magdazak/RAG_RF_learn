## FastAPI Learning Notes: Collection Management Endpoints

### Goal

Implement API endpoints that allow users to view and manage ChromaDB collections.

Think of collections as the equivalent of databases, repositories, or libraries inside your RAG system.

```text
ChromaDB
   |
   +--> product_docs
   +--> test_docs
   +--> product_manuals
   +--> release_notes
```

These endpoints provide visibility and administrative control over those collections.

---

### Big Picture

So far you have built:

```text
Upload PDF
    |
    v
Create Embeddings
    |
    v
Store in Collection
    |
    v
Query Collection
```

Now you are adding:

```text
List Collections
Delete Collections
```

This is the beginning of the administration layer of your API.

---

### What is a Collection?

In ChromaDB, a collection is a logical container for embeddings.

Example:

```text
Collection: product_docs

Contains:
- User Manual
- Installation Guide
- Release Notes
```

Another collection:

```text
Collection: test_docs

Contains:
- Test Plan
- Test Strategy
- Test Procedures
```

Keeping collections separate allows different document sets to be queried independently.

---

### Endpoint 1: GET /api/v1/collections

Purpose:

```text
Show all available collections.
```

Example:

```http
GET /api/v1/collections
```

Possible response:

```json
[
  {
    "name": "product_docs",
    "document_count": 120
  },
  {
    "name": "test_docs",
    "document_count": 45
  }
]
```

---

### Why Is This Useful?

A future UI might need to display:

```text
Available Collections
--------------------
product_docs        120 docs
product_docs      62 docs
release_notes     18 docs
```

Without this endpoint, users would have to remember collection names manually.

---

### Connecting to ChromaDB

Typical code:

```python
import chromadb

client = chromadb.PersistentClient(
    path="../chroma_db"
)
```

Think of this as:

```text
Open connection
       |
       v
Access Vector Database
```

Similar to:

```python
sqlite.connect(...)
```

or:

```python
psycopg.connect(...)
```

for traditional databases.

---

### list_collections()

Example:

```python
collections = client.list_collections()
```

Returns information about collections stored inside ChromaDB.

Conceptually:

```text
[
   product_docs,
   test_docs,
   release_notes
]
```

FastAPI then converts the results into your CollectionInfo model.

---

### CollectionInfo Model

You created:

```python
class CollectionInfo(BaseModel):
    name: str
    document_count: int
    created_at: Optional[str]
```

This becomes the API contract for collection data.

Example response:

```json
{
  "name": "product_docs",
  "document_count": 245,
  "created_at": "2026-07-01T10:00:00"
}
```

---

### Endpoint 2: DELETE /api/v1/collections/{name}

Purpose:

```text
Delete a collection.
```

Example:

```http
DELETE /api/v1/collections/test_docs
```

Response:

```json
{
  "message": "Collection deleted successfully"
}
```

---

### Why DELETE?

REST APIs use conventional HTTP methods:

```text
GET     -> Read
POST    -> Create
PUT     -> Update
DELETE  -> Delete
```

This makes APIs predictable.

---

### Validate Collection Exists First

Before deletion:

```text
Does collection exist?
```

If not:

```http
404 Not Found
```

Response:

```json
{
  "detail": "Collection not found"
}
```

This is much better than generating a generic internal error.

---

### Prevent Deletion of Default Collection

The guide suggests protecting:

```text
product_docs
```

or whichever collection is considered critical.

Example:

```http
DELETE /collections/product_docs
```

Response:

```http
403 Forbidden
```

Possible message:

```json
{
  "detail": "Default collection cannot be deleted"
}
```

This is a common safety mechanism.

---

### Why Safety Checks Matter

Imagine a UI bug.

User accidentally clicks:

```text
Delete Collection
```

Without safeguards:

```text
Production data lost
```

With safeguards:

```text
Deletion blocked
```

---

### Optional Cleanup

Deleting a collection may leave related files behind.

Example:

```text
uploads/
cache/
logs/
```

You can optionally clean them up.

For a first implementation, focusing only on ChromaDB deletion is perfectly reasonable.

---

## Audit Logging

The guide recommends logging deletions.

Example log:

```text
2026-08-30 14:20
Collection deleted: test_docs
```

Benefits:

- Troubleshooting
- Compliance
- Tracking mistakes
- Security investigations

---

### Soft Delete vs Hard Delete

#### Hard Delete

```text
Collection removed permanently.
```

#### Soft Delete

```text
Collection marked as deleted.
```

Example:

```json
{
  "deleted": true
}
```

Data still exists and can potentially be restored.

Many production systems prefer soft deletion.

---

### Learning Point 1

#### ChromaDB Provides list_collections()

This allows your API to discover available collections dynamically.

You do not need to maintain a separate list manually.

Conceptually:

```text
ChromaDB
   |
   v
list_collections()
   |
   v
API response
```

---

### Learning Point 2

#### DELETE Should Be Idempotent

Idempotent means:

> Repeating the request does not create additional side effects.

Example:

First request:

```http
DELETE /collections/test_docs
```

Result:

```text
Collection removed.
```

Second request:

```http
DELETE /collections/test_docs
```

Result:

```http
404 Not Found
```

No additional damage occurs.

This is an important REST principle.

---

### Learning Point 3

#### Collection Metadata Helps the UI

Without metadata:

```text
product_docs
product_docs
```

With metadata:

```text
product_docs      245 docs
product_docs    67 docs
```

Users immediately understand what is available.

A future React UI can easily display collection statistics.

---

### QA / Test Engineer Perspective

#### List Collections

Request:

```http
GET /collections
```

Verify:

- HTTP 200
- Response is a list
- Collection names exist
- Document counts are non-negative

---

#### Delete Existing Collection

Request:

```http
DELETE /collections/test_docs
```

Verify:

- HTTP 200
- Success message returned

---

#### Delete Missing Collection

Request:

```http
DELETE /collections/not_existing
```

Expected:

```http
404
```

---

#### Delete Protected Collection

Request:

```http
DELETE /collections/product_docs
```

Expected:

```http
403
```

---

#### Verify Actual Removal

Workflow:

```text
List collections
      |
Delete collection
      |
List collections again
```

Verify collection is no longer present.

---

### Key Takeaway

> 'Collection Management Endpoints' introduces collection administration. You are no longer only querying data, you are now managing the lifecycle of your vector database resources.

The main pattern is:

```text
GET /collections
        |
        v
Inspect system

DELETE /collections/{name}
        |
        v
Manage system
```

These kinds of endpoints form the foundation of operational and administration APIs used in many production systems.
