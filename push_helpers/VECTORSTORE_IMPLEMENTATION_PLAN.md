# Vector Store Module — Implementation Plan

> **Date**: April 26, 2026  
> **Target file**: `src/rag/vectorstore.py`  
> **Status**: 🔲 Pending

---

## Current Pipeline Status

| Layer | Status | Module |
|---|---|---|
| PDF → Markdown | ✅ Done | `src/data_extract/` |
| Chunking | ✅ Done | `src/rag/chunking.py` |
| Embeddings (Ollama) | ✅ Done | `src/rag/embeddings.py` (768-dim via `nomic-embed-text`) |
| **Vector Store** | ❌ Placeholder | `src/rag/vectorstore.py` |

---

## Recommended Tool: ChromaDB

Since the project is **fully local** (using local Ollama), **ChromaDB** is the best fit.

### Comparison: ChromaDB vs FAISS

| Criteria | ChromaDB | FAISS |
|---|---|---|
| Local / no server | ✅ | ✅ |
| Persistent on disk | ✅ native | ⚠️ manual save/load |
| Metadata filtering | ✅ | ❌ |
| Simple Python API | ✅ | ⚠️ lower-level |
| Custom embeddings | ✅ | ✅ |

### Why ChromaDB?
- Pure Python, no Docker or external server needed
- Persists the index on disk automatically (survives restarts)
- Supports **metadata filtering** (e.g. filter chunks by `heading`)
- Designed exactly for RAG use cases
- Works seamlessly with pre-computed embeddings from Ollama

---

## Implementation Steps

### Step 1 — Install ChromaDB

```powershell
pip install chromadb
```

Or using `uv`:

```powershell
uv pip install chromadb
```

Then add `chromadb` to `requirements.txt`.

> #### ⚖️ Installation Weight — What to Expect
>
> Installing `chromadb` pulls in **~60 transitive dependencies** totalling approximately **~189 MB** on disk.
> This is largely unavoidable with ChromaDB 1.x.
>
> **Main contributors:**
>
> | Package | Size | Notes |
> |---|---|---|
> | `chromadb_rust_bindings` | ~60 MB | Compiled Rust core — unavoidable |
> | `onnxruntime` | ~36 MB | Built-in embeddings engine — **not used** in our pipeline (we use Ollama) |
> | `numpy` + `numpy.libs` | ~39 MB | Numerical arrays |
> | `kubernetes` | ~16 MB | Client-server mode support — not needed locally |
> | `hf_xet` + `tokenizers` | ~15 MB | HuggingFace large-file & tokenizer support |
> | Everything else | ~23 MB | grpcio, opentelemetry, rich, fsspec, uvicorn, etc. |
>
> **Key note**: `onnxruntime` (~36 MB) is only invoked when ChromaDB generates embeddings *internally*.
> Since this project injects **pre-computed embeddings from Ollama**, `onnxruntime` is dead weight —
> but there is no install flag to exclude it in the current ChromaDB release.

---

### Step 2 — Implement `src/rag/vectorstore.py`

The module should expose two main functions:

#### `build_vectorstore(embedded_chunks, collection_name, persist_dir)`
- Takes the output of `embed_chunks()` (list of `{"text", "heading", "embedding"}`)
- Creates (or updates) a ChromaDB collection on disk
- Stores text, embeddings, and metadata (`heading`) per chunk

#### `query_vectorstore(query_text, collection_name, persist_dir, n_results, model)`
- Embeds the query string using Ollama (`get_embedding()`)
- Queries the ChromaDB collection for the top-k most similar chunks
- Returns a list of result dicts: `{"text", "heading", "distance"}`

---

### Step 3 — Update `main.py`

After the existing `embed_chunks()` call, add:

```python
from src.rag.vectorstore import build_vectorstore

# 6. Store embedded chunks in ChromaDB
build_vectorstore(
    embedded_chunks,
    collection_name="product_docs",
    persist_dir="./chroma_db"
)
```

---

### Step 4 — Query the Vector Store

```python
from src.rag.vectorstore import query_vectorstore

results = query_vectorstore(
    query_text="How do I reset a user password?",
    collection_name="product_docs",
    persist_dir="./chroma_db",
    n_results=5
)

for r in results:
    print(r["heading"], r["text"][:200])
```

---

## Updated Architecture Flow

```
PDF
 └─► Markdown  (data_extract/)
       └─► Chunks  (rag/chunking.py)
             └─► Embeddings  (rag/embeddings.py  ←  Ollama nomic-embed-text)
                   └─► ChromaDB on disk  (rag/vectorstore.py)
                               ▲
                    query_vectorstore("question")
                               │
                    Top-k chunks  ──►  LLM prompt  ──►  Answer
```

---

## Directory Structure After Implementation

```
LLM_Local/
├── src/rag/
│   ├── vectorstore.py       ← implement here
│   └── embeddings.py        ← already done
├── chroma_db/               ← auto-created, add to .gitignore
│   └── <collection data>
└── main.py                  ← wire build_vectorstore() here
```

> ⚠️ Add `chroma_db/` to `.gitignore` — it can be large and is machine-specific.

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Vector DB | ChromaDB | Local, persistent, simple API |
| Embedding model | `nomic-embed-text` (768-dim) | Already in use, fast, good quality |
| Persist location | `./chroma_db/` | Relative to project root |
| IDs | `chunk_{i}` | Simple, reproducible indexing |
| Metadata stored | `heading` | Enables heading-level filtering |

---

## Dependencies to Add

```
chromadb>=0.5.0
```

---

## Roadmap Checklist Update

- [x] Embeddings Module
- [ ] **Vector Store** ← _this plan_
- [ ] LangChain Integration
- [ ] Enhanced CLI
- [ ] Web API
- [ ] Docker Support
- [ ] Testing Suite
- [ ] Documentation

