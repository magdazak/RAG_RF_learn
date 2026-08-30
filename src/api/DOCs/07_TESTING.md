## Detailed Test Plan

**NOTE:** Add examples to the README.md after this test plan is executed successfully.

This is a concrete, executable test plan for validating the entire FastAPI
implementation (Todos 2–6) before writing the final `README.md` docs.

Scope: `GET /health`, `POST /api/v1/documents`, `GET /api/v1/documents/{job_id}`,
`POST /api/v1/query`, `GET /api/v1/collections`, `DELETE /api/v1/collections/{name}`.

---

### 0. Test Environment Setup

Two Ollama states are needed across the plan — prepare both:

| State | How | Used for |
|---|---|---|
| **Ollama running** | `ollama serve` (or already running as a service) + models pulled: `nomic-embed-text`, `llama3.1:8b` | Happy-path tests, real answer quality checks |
| **Ollama stopped** | Stop the Ollama process/service | 503 error-handling tests |

Server under test:
```powershell
python api_server.py
# or: uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

Test fixtures needed:
- A small valid PDF (e.g. reuse `data_raw/sample.pdf`)
- A non-PDF file (e.g. a `.txt` or `.png`) to test rejection
- (Optional) A PDF >50MB to test the size-limit branch — can be faked by editing `MAX_FILE_SIZE_BYTES` temporarily downward instead of finding a huge file

Track results in a simple table (pass/fail + notes) as you go — see the checklist at the bottom.

---

### 1. Health & Meta

| # | Test | Steps | Expected |
|---|---|---|---|
| 1.1 | Health check | `GET /health` | `200`, JSON with `status: "healthy"` |
| 1.2 | Root endpoint | `GET /` | `200`, welcome message with `/docs` link |
| 1.3 | Swagger UI loads | Open `http://localhost:8000/docs` in browser | Page loads, all 3 route groups visible (Documents, Query, Collections) |
| 1.4 | ReDoc loads | Open `http://localhost:8000/redoc` | Page loads |
| 1.5 | Process-time header | Inspect response headers of any request | `X-Process-Time` header present |

---

### 2. Document Upload — `POST /api/v1/documents`

**Ollama state: doesn't matter for these (upload accepts before processing).**

| # | Test | Input | Expected |
|---|---|---|---|
| 2.1 | Valid PDF upload | `file=@sample.pdf` | `202 Accepted`, body has `job_id` (UUID), `status: "queued"`, `filename` matches |
| 2.2 | Non-PDF rejected | `file=@notes.txt` | `400`, clear error message mentioning allowed extensions |
| 2.3 | Empty file rejected | Upload a 0-byte `.pdf` | `400`, "empty" message |
| 2.4 | Oversized file rejected | File > `MAX_FILE_SIZE_BYTES` (or temporarily lower the constant to test with a small file) | `413`, mentions size limit in MB |
| 2.5 | Custom collection name | `file=@sample.pdf`, form field `collection_name=test_upload_docs` | `202`, job later completes into that collection (verify via 3.x) |
| 2.6 | Missing file field | POST with no `file` part | `422` (FastAPI/Pydantic validation) |
| 2.7 | Upload file cleanup | After 2.1 completes (success or failure), check `./uploads/` | Temp file `{job_id}_{filename}` no longer exists |

---

### 3. Job Status — `GET /api/v1/documents/{job_id}`

**Run immediately after test 2.1/2.5 above, using the returned `job_id`.**

| # | Test | Steps | Expected |
|---|---|---|---|
| 3.1 | Immediately after upload | `GET /documents/{job_id}` right away | `200`, `status` is `pending` or `processing`, `progress` low (0–40) |
| 3.2 | Poll until done (Ollama running) | Poll every ~2s | Eventually `status: "completed"`, `progress: 100`, `collection_name` set |
| 3.3 | Poll until done (Ollama stopped) | Repeat 2.1 with Ollama down | Eventually `status: "failed"`, `error` field contains a clear Ollama connection message (not a raw traceback) |
| 3.4 | Unknown job_id | `GET /documents/00000000-0000-0000-0000-000000000000` | `404` |
| 3.5 | Malformed job_id | `GET /documents/not-a-uuid` | `404` (still handled gracefully, no 500) |
| 3.6 | TTL cleanup (optional/manual) | Temporarily lower `JOB_TTL_SECONDS` in `dependencies.py`, wait past it, then hit status endpoint | `404` — job was purged by the hourly cleanup loop |

---

### 4. Query — `POST /api/v1/query`

#### 4a. Validation (no Ollama needed — fails before reaching it)

| # | Test | Body | Expected |
|---|---|---|---|
| 4.1 | Missing `question` | `{}` | `422` |
| 4.2 | Wrong type | `{"question": 123}` | `422` |
| 4.3 | `n_results` out of bounds | `{"question": "x", "n_results": 0}` and `{"n_results": 100}` | `422` (bounded 1–50 per model) |
| 4.4 | Unknown collection | `{"question": "x", "collection_name": "does_not_exist"}` | `404` |

#### 4b. Ollama stopped

| # | Test | Body | Expected |
|---|---|---|---|
| 4.5 | Existing collection, Ollama down | `{"question": "How do I configure the system?", "collection_name": "product_docs"}` | `503`, message mentions `ollama serve` |

#### 4c. Happy path (Ollama running)

| # | Test | Body | Expected |
|---|---|---|---|
| 4.6 | Basic question | `{"question": "How do I configure the system?", "collection_name": "product_docs"}` | `200`; `answer` non-empty; `sources` is a non-empty list of `{text, heading, distance}`; `processing_time > 0`; `used_web_search: false` |
| 4.7 | `n_results` respected | Same as 4.6 with `n_results: 2` | `len(sources) <= 2` |
| 4.8 | Web search flag | `{"question": "...", "web_search": true}` | `200`, `used_web_search: true`; answer context includes web results (check logs/manually) — ⚠️ sends query to DuckDuckGo, use a generic non-sensitive question |
| 4.9 | Answer relevance (manual/subjective) | Ask a question clearly answered in the uploaded doc | Answer text is topically correct, not "No relevant information found" |
| 4.10 | Nonsense/irrelevant question | `{"question": "asdkjalksdj random gibberish"}` | `200`, still returns *something* (low-relevance sources or a graceful "couldn't find" style answer) — should not crash |

---

### 5. Collections

#### 5a. List — `GET /api/v1/collections`

| # | Test | Steps | Expected |
|---|---|---|---|
| 5.1 | List collections | `GET /collections` | `200`, array; `product_docs` present with `document_count > 0` |
| 5.2 | Response shape | Inspect one item | Has `name` (str), `document_count` (int ≥ 0), `created_at` (str or null) |

#### 5b. Delete — `DELETE /api/v1/collections/{name}`

| # | Test | Steps | Expected |
|---|---|---|---|
| 5.3 | Delete protected collection | `DELETE /collections/product_docs` | `403` |
| 5.4 | Delete nonexistent collection | `DELETE /collections/nope_123` | `404` |
| 5.5 | Delete real (throwaway) collection | Create one via upload with `collection_name=test_delete_me` (test 2.5), then `DELETE /collections/test_delete_me` | `200`, success message |
| 5.6 | Verify deletion | `GET /collections` again after 5.5 | `test_delete_me` no longer listed |
| 5.7 | Idempotent re-delete | Repeat `DELETE /collections/test_delete_me` | `404` (not 500, not silently 200 again) |

---

### 6. CORS

| # | Test | Steps | Expected |
|---|---|---|---|
| 6.1 | Preflight request | `OPTIONS /api/v1/query` with `Origin: http://localhost:3000` header (e.g. via `curl -X OPTIONS -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: POST" http://localhost:8000/api/v1/query -i`) | `200`, `Access-Control-Allow-Origin` header present |
| 6.2 | Browser fetch test | Open browser devtools console on any page (or a blank `data:` page won't work — use a local static HTML file), run `fetch('http://localhost:8000/health').then(r=>r.json()).then(console.log)` | No CORS error, JSON logged |

---

### 7. End-to-End Scenario (integration)

| # | Test | Steps | Expected |
|---|---|---|---|
| 7.1 | Full lifecycle | 1) Upload PDF → get `job_id` 2) Poll status until `completed` 3) `GET /collections` → confirm doc count increased 4) `POST /query` asking about content specific to that PDF 5) Verify answer is relevant and `sources` reference the new content | All steps succeed in sequence; final answer is topically correct |
| 7.2 | Existing CLI unaffected | Run `python rag_cli.py query "..."` directly (not via API), while API server is also running | CLI still works exactly as before — proves the API changes to `vectorstore.py` (the `return_sources` param) didn't break CLI usage |

---

### 8. Regression / Non-Functional Checks

| # | Test | Expected |
|---|---|---|
| 8.1 | Server starts cleanly | No tracebacks in stdout/stderr on startup |
| 8.2 | `--reload` still works | Edit any route file while server running → auto-reloads without crashing |
| 8.3 | Graceful shutdown | `Ctrl+C` → "Shutting down LLM Local API server..." logged, TTL cleanup task cancelled cleanly (no unhandled task exceptions) |
| 8.4 | No stray background processes | After stopping the server, `Get-Process python` shows nothing lingering |
| 8.5 | No orphaned upload files | `./uploads/` is empty after a batch of tests (success + failure cases) |

---

### Suggested Execution Order

1. Section 1 (health/meta) — sanity check server is up
2. Section 4a (query validation, no Ollama needed) — fast, no dependencies
3. Section 2 + 3 with **Ollama running** — full upload→process→complete flow
4. Section 5 (collections) — uses the collection created in step 3
5. Section 4c (query happy path, Ollama running) — now that data exists
6. Stop Ollama → Section 4b + re-run 3.3 (failed job path)
7. Section 6 (CORS) — independent, any time
8. Section 7 (end-to-end + CLI regression) — last, ties everything together
9. Section 8 (non-functional) — throughout, but double-check at the end

---

### Automation Option

Everything above can be scripted with `pytest` + `httpx.AsyncClient` or FastAPI's
`TestClient`, using `unittest.mock` to simulate Ollama up/down states without
needing the real service. If you'd like, this can be built out as
`tests/test_api.py` covering sections 1, 2, 3 (mocked pipeline), 4a/4b (mocked
Ollama), and 5 — turning this manual plan into a repeatable CI-style suite.

---

### Pass/Fail Tracking Template

Copy this table while executing:

```text
Section | Test # | Result (P/F) | Notes
--------|--------|---------------|------
1       | 1.1    |               |
1       | 1.2    |               |
...
```

