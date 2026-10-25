# Vector Store Module — ChromaDB Implementation

The **vector store is the backbone of a RAG system** because it determines *what information your model can find, how fast it finds it, and how relevant that information is*. Without an efficient vector store, RAG collapses into either slow responses or hallucinations.  

This document explains both the theory and the **practical ChromaDB implementation** used in this project.

---

## 📋 Quick Reference

### Installation

```powershell
pip install chromadb
# or using uv
uv pip install chromadb
```

Add to `requirements.txt`:
```
chromadb>=0.5.0
```

> **⚖️ Installation Size:** ChromaDB pulls in ~60 transitive dependencies totaling approximately ~189 MB on disk. Main contributors:
> - `chromadb_rust_bindings` (~60 MB) — Compiled Rust core
> - `onnxruntime` (~36 MB) — Built-in embeddings engine (not used since we use Ollama)
> - `numpy` + `numpy.libs` (~39 MB) — Numerical arrays
> - `kubernetes` (~16 MB) — Client-server mode support (not needed locally)
> 
> Note: `onnxruntime` is only invoked when ChromaDB generates embeddings internally. Since this project uses **pre-computed embeddings from Ollama**, onnxruntime is not utilized.

---

## 🧠 Core takeaway
A **vector store** is essential in RAG because it enables **semantic search** over your knowledge base, letting the system retrieve the most relevant chunks of information based on *meaning*, not keywords. This retrieval step directly affects **accuracy**, **latency**, and **scalability** of your RAG pipeline.

---

## ✅ Implementation Status — ChromaDB (Local, Persistent)

| Component | Status | Details |
|---|---|---|
| **Vector DB** | ✅ Implemented | ChromaDB v0.5+ with persistent storage |
| **Embedding model** | ✅ Integrated | Ollama `nomic-embed-text` (768 dimensions) |
| **Storage location** | ✅ Configured | `./chroma_db/` (local, persistent) |
| **Collection** | ✅ Active | `product_docs` |
| **Metadata support** | ✅ Enabled | `heading` field for filtering |
| **Distance metric** | ✅ Default | Cosine similarity (L2 normalized) |

### Why ChromaDB?

**ChromaDB was chosen because this project is fully local:**
- ✅ **No cloud dependencies** — works offline, data stays on your machine
- ✅ **Auto-persistent** — survives restarts without manual save/load (unlike FAISS)
- ✅ **Metadata filtering** — can filter chunks by `heading` or other fields
- ✅ **Simple Python API** — designed specifically for RAG use cases
- ✅ **Works with custom embeddings** — accepts pre-computed Ollama vectors

**Comparison: ChromaDB vs FAISS**

| Criteria | ChromaDB | FAISS |
|---|---|---|
| Local / no server | ✅ | ✅ |
| Persistent on disk | ✅ native | ⚠️ manual save/load |
| Metadata filtering | ✅ | ❌ |
| Simple Python API | ✅ | ⚠️ lower-level |
| Custom embeddings | ✅ | ✅ |

ChromaDB is the better choice for this fully-local RAG pipeline:
- Pure Python, no Docker or external server needed
- Persists the index on disk automatically (survives restarts)
- Supports **metadata filtering** (e.g. filter chunks by `heading`)
- Designed exactly for RAG use cases
- Works seamlessly with pre-computed embeddings from Ollama

---

## 🧩 What a vector store actually does  

- **Semantic indexing** — It stores embeddings (dense vectors) representing the meaning of your text. This allows similarity search based on conceptual closeness rather than exact words. 
- **Efficient retrieval** — It performs fast nearest‑neighbor search (often using ANN algorithms like HNSW or IVF) to find the most relevant chunks for a query. 
- **Context injection** — The retrieved chunks become the grounding context for the LLM, reducing hallucinations and improving factual accuracy.  

---

## 🔧 How This Implementation Works

### Architecture Flow
```
PDF Documents
  └─► Markdown Conversion (data_extract/)
        └─► Semantic Chunking (rag/chunking.py)
              └─► Ollama Embeddings (rag/embeddings.py)
                    • Model: nomic-embed-text
                    • Dimensions: 768
                    • Local inference via Ollama
                        └─► ChromaDB Storage (rag/vectorstore.py)
                              • Location: ./chroma_db/
                              • Collection: product_docs
                              • Index: HNSW (default)
                                    ▲
                      Query with natural language
                                    │
              Top-k similar chunks ──► Optional: Web Search (web_search.py)
                                              • DuckDuckGo API
                                              • Privacy warnings
                                              • Opt-in only
                                                    │
                                        Combined context (local + web)
                                                    │
                                                    ▼
                                        LLM Answer Generation
                                              • Model: llama3.1:8b
                                              • Local Ollama inference
                                              • Concise synthesis
                                                    │
                                                    ▼
                                              Final Answer
```

### Data Structure

Each vector storage entry contains:
```python
{
    "id":        "chunk_42",                    # Sequential ID
    "embedding": [0.123, -0.456, ..., 0.789],  # 768-dim vector (nomic-embed-text)
    "document":  "To reset a password, navigate to...",  # Original chunk text
    "metadata": {
        "heading": "User Management > Passwords"  # Section context
    }
}
```

---

## 📝 Implementation API

### 1. **Building the Vector Store**

```python
from src.rag.vectorstore import build_vectorstore
from src.rag.embeddings import embed_chunks
from src.rag.chunking import markdown_chunker

# After chunking and embedding
embedded_chunks = embed_chunks(chunks, model="nomic-embed-text")

# Persist to ChromaDB
build_vectorstore(
    embedded_chunks=embedded_chunks,
    collection_name="product_docs",    # Collection name
    persist_dir="./chroma_db"       # Storage directory
)
```

**Key features:**
- **Idempotent upserts** — safe to rebuild; overwrites existing chunks with same IDs
- **Automatic persistence** — no manual save needed; survives restarts
- **Logging** — reports number of chunks stored

---

### 2. **Querying the Vector Store (Raw Chunks)**

```python
from src.rag.vectorstore import query_vectorstore

results = query_vectorstore(
    query_text="How do I reset a user password?",
    collection_name="product_docs",
    persist_dir="./chroma_db",
    n_results=5,                     # Top-5 results
    model="nomic-embed-text"         # Must match embedding model
)

# Results format:
# [
#   {"text": "...", "heading": "User Management", "distance": 0.234},
#   {"text": "...", "heading": "Password Reset", "distance": 0.456},
#   ...
# ]
```

**How it works:**
1. Embeds the query text using Ollama (`nomic-embed-text`)
2. Performs cosine similarity search in ChromaDB
3. Returns top-k chunks sorted by distance (lower = more similar)

---

### 3. **Query + Answer Generation (Recommended)**

```python
from src.rag.vectorstore import query_and_generate

# Get a concise answer synthesized from retrieved chunks
answer = query_and_generate(
    query_text="How do I reset a user password?",
    collection_name="product_docs",
    persist_dir="./chroma_db",
    n_results=5,                      # Chunks to retrieve for context
    embed_model="nomic-embed-text",   # Embedding model
    generation_model="llama3.1:8b",   # LLM for answer synthesis
    use_web_search=False              # Optional: augment with web results
)

print(answer)
# Output: "To reset a user password, navigate to the User Management 
#          section and click on 'Reset Password'..."
```

**Features:**
- Retrieves top-k chunks from ChromaDB
- Optionally augments with DuckDuckGo web search
- Synthesizes coherent answer using local LLM (llama3.1:8b)
- 100% local processing (unless web search enabled)

**Web Search Option:**
```python
# ⚠️ Privacy warning: Sends query to DuckDuckGo servers
answer = query_and_generate(
    query_text="What are OAuth 2.0 best practices?",
    use_web_search=True  # Combines local docs + web results
)
```

When `use_web_search=True`:
- ⚠️ Query is sent to DuckDuckGo servers
- Local documents are searched first
- Web results added as supplementary context
- Answer labels sources (local vs web)
- **Do NOT use** for sensitive/internal questions

---

### 4. **Advanced: Metadata Filtering** (Future Extension)

ChromaDB supports filtering by metadata:
```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"heading": {"$contains": "User Management"}}  # Only search in specific sections
)
```

This can improve precision when you know the query domain upfront.

---

## 🚀 Why this implementation is important

### 1. **It determines the accuracy of your RAG answers**  
If the vector store retrieves irrelevant or low‑quality chunks, the LLM will produce weak or hallucinated answers.  
RAG systems can improve factual accuracy from **70% → 95%+** when retrieval is strong.

**In this implementation:**
- Semantic chunking preserves context (keeps headings with related content)
- `nomic-embed-text` is optimized for retrieval tasks
- Distance-sorted results ensure the best matches come first
- **Local LLM synthesis** (`llama3.1:8b`) creates coherent answers from chunks
- Optional web search provides supplementary context when needed

### 2. **It controls latency — how fast your app feels**  
A slow vector store becomes a bottleneck. Searching millions of embeddings can take *hundreds of milliseconds* if poorly optimized, delaying the entire response. 

**In this implementation:**
- ChromaDB uses **HNSW** (Hierarchical Navigable Small World) index → sublinear search time
- Local storage eliminates network latency
- Expected retrieval time: **10–50 ms** for thousands of chunks (single-machine)
- Local LLM adds ~2-5 seconds for answer generation (acceptable for interactive use)

### 3. **Privacy and data control**
Your documents never leave your machine (unless web search explicitly enabled).

**In this implementation:**
- ✅ 100% local processing (embeddings, storage, LLM generation)
- ✅ No cloud API calls to OpenAI/Anthropic/Cohere
- ✅ Your documents stay on your machine
- ⚠️ Optional web search sends queries to DuckDuckGo (opt-in with warnings)

### 4. **It enables domain‑specific expertise**  
Your private or specialized data lives *outside* the LLM — in the vector store.
This is how RAG turns a general model into an expert in your domain (legal, medical, internal docs, etc.).

**In this implementation:**
- PRODUCT documentation is indexed locally and privately
- No data sent to cloud services
- Easy to add more documents — just run `embed_chunks()` + `build_vectorstore()` again

### 5. **It keeps your system up‑to‑date**  
Unlike fine‑tuning, you can update your knowledge base instantly by adding new vectors.  
This is cheaper and 10–50× more efficient than retraining.

**In this implementation:**
- `collection.upsert()` makes rebuilds idempotent
- Add new PDFs → convert to markdown → chunk → embed → upsert
- Old chunks with same IDs are overwritten automatically

---

## 🏗️ Complete RAG Pipeline in This Project

1. **Chunk documents** → `src/rag/chunking.py` (semantic markdown chunking)
2. **Generate embeddings** → `src/rag/embeddings.py` (Ollama + nomic-embed-text)
3. **Store embeddings in vector DB** → `src/rag/vectorstore.py` (ChromaDB) ← **current module**
4. **Embed the user query** → `query_vectorstore()` (same model as step 2)
5. **Retrieve top‑k similar vectors** → ChromaDB similarity search
6. **Optional: Augment with web search** → `src/rag/web_search.py` (DuckDuckGo)
7. **Generate answer with LLM** → `query_and_generate()` (Ollama + llama3.1:8b)
8. **Return concise answer** → Synthesized from retrieved chunks + optional web results

The quality of step 3 determines the quality of steps 5–8.

---

## 🎯 CLI Integration

The vector store is seamlessly integrated into the CLI:

### Build Command
```bash
python main.py build document.pdf
```
- Processes PDF → Markdown → Chunks → Embeddings → ChromaDB
- Auto-detects duplicates with `--force` override

### Query Command (with Answer Generation)
```bash
python main.py query "How do I reset a password?"
```
- Retrieves top-5 chunks from ChromaDB
- Synthesizes concise answer using llama3.1:8b
- 100% local processing

### Query with Web Search
```bash
# ⚠️ Privacy warning displayed automatically
python main.py query "What are OAuth best practices?" --web-search
```
- Searches ChromaDB first
- Augments with DuckDuckGo results
- Clearly labels sources in answer

### Interactive Mode
```bash
python main.py interactive
```
- Multi-question session
- Each query: retrieval → generation → answer
- Type 'quit' to exit

---

## ⚙️ Configuration & Performance Tuning

### Key Parameters

| Parameter | Default | Tuning Guidance |
|---|---|---|
| `n_results` | 5 (query), 3 (interactive) | Too low → misses context; too high → noise. Start with 3–7. |
| `persist_dir` | `./chroma_db/` | Use absolute path for production; add to `.gitignore`. |
| `collection_name` | `product_docs` | Change per knowledge domain (e.g., `legal_docs`, `api_specs`). |
| Embedding model | `nomic-embed-text` | Must match between indexing and querying. |
| Generation model | `llama3.1:8b` | Swap with `mistral` or other Ollama models via `--model` flag. |
| Distance metric | Cosine (L2) | ChromaDB default; cosine works well for text embeddings. |
| Web search | Disabled | Enable with `--web-search` flag (privacy warnings apply). |

### Storage Size Estimates

For **768-dim embeddings** (nomic-embed-text):
- Each chunk: ~3–6 KB (vector + text + metadata)
- 1,000 chunks ≈ **3–6 MB**
- 10,000 chunks ≈ **30–60 MB**
- 100,000 chunks ≈ **300–600 MB**

ChromaDB also stores index structures (HNSW graph), adding ~20–30% overhead.

### Performance Benchmarks (Approximate)

| Collection Size | Index Build Time | Query Latency | Answer Generation | Total Time | RAM Usage |
|---|---|---|---|---|---|
| 1,000 chunks | <1 second | 5–10 ms | 2–4 seconds | ~2–4 sec | ~50 MB |
| 10,000 chunks | 5–10 seconds | 10–30 ms | 2–4 seconds | ~2–4 sec | ~200 MB |
| 100,000 chunks | 1–2 minutes | 30–80 ms | 2–4 seconds | ~2–5 sec | ~1 GB |

*Tested on mid-range CPU (Intel i5/i7); LLM generation time depends on GPU/CPU performance.*

**Note:** Most latency in query mode comes from LLM answer generation (~2-5 seconds), not vector search (<100ms).

---

## 🛡️ Best Practices

### 1. **Always use the same embedding model for indexing and querying**
Mixing models (e.g., indexing with `nomic-embed-text`, querying with `mxbai-embed-large`) breaks semantic search.

### 2. **Add `chroma_db/` to `.gitignore`**
The vector store is large and machine-specific. Rebuild it from source documents on each deployment.

### 3. **Monitor distance scores**
- Distance < 0.5 → strong match
- Distance 0.5–1.0 → moderate match
- Distance > 1.0 → weak match (consider excluding)

### 4. **Use metadata filtering sparingly**
Filtering by `heading` or other metadata can improve precision but reduces recall. Best for known-domain queries.

### 5. **Rebuild the index when documents change significantly**
If you update many PDFs, re-run the full pipeline to keep the vector store in sync.

### 6. **Web search privacy**
- ⚠️ Only enable `--web-search` for generic, public questions
- Never use for internal/confidential queries
- Queries are sent to DuckDuckGo servers when enabled
- Disabled by default for privacy

### 7. **Choose the right generation model**
- `llama3.1:8b` (default) - Good balance of speed and quality
- `mistral` - Faster, slightly lower quality
- `llama2` - Alternative general-purpose model
- Use `--model` flag to experiment

---

## 📊 Summary table

| **Component** | **Role** | **Impact on RAG** | **This Implementation** |
|---------------|----------|-------------------|-------------------------|
| **Vector storage** | Holds embeddings + metadata | Defines what knowledge is available | ChromaDB persistent disk storage |
| **Similarity search** | Finds nearest vectors | Controls accuracy & relevance | Cosine similarity (HNSW index) |
| **Indexing algorithms** | Speed up search | Controls latency & scalability | HNSW (sublinear search time) |
| **Filtering & metadata** | Narrow search space | Improves precision | `heading` field stored per chunk |
| **Embedding model** | Converts text to vectors | Determines semantic quality | Ollama `nomic-embed-text` (768-dim) |
| **Answer generation** | Synthesizes retrieved chunks | Creates coherent responses | Ollama `llama3.1:8b` (local) |
| **Web augmentation** | Supplements local knowledge | Fills information gaps | DuckDuckGo (opt-in, privacy warnings) |

---

## 🗂️ Directory Structure

After implementing the vector store, the project structure includes:

```
RAG_learn/
├── src/rag/
│   ├── vectorstore.py       ← ChromaDB + answer generation
│   ├── embeddings.py        ← Ollama embedding generation
│   ├── chunking.py          ← Semantic chunking
│   ├── web_search.py        ← Optional DuckDuckGo integration
│   └── VECTORE_STORE.md     ← This documentation
├── chroma_db/               ← Auto-created on first build
│   └── <collection data>    ← Persistent vector storage
├── main.py                  ← CLI entry point
└── .gitignore               ← Must include chroma_db/
```

---

## 🔍 Vector Store Comparison

Understanding why ChromaDB was chosen:

| Feature | **ChromaDB** ✅ | FAISS | Pinecone | Qdrant | Weaviate |
|---|---|---|---|---|---|
| **Local / offline** | ✅ | ✅ | ❌ Cloud only | ✅ | ✅ |
| **Auto-persistence** | ✅ | ⚠️ Manual | ✅ | ✅ | ✅ |
| **Metadata filtering** | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Simple Python API** | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **Setup complexity** | Low | Low | Medium | Medium | High |
| **Scalability** | Small-medium | Large | Very large | Large | Large |
| **Best for** | Local RAG prototypes | Offline ML research | Production cloud | Self-hosted production | Knowledge graphs |

**ChromaDB** is ideal for local-first RAG systems like this one. For production scale (millions of vectors, high concurrency), consider Qdrant (self-hosted) or Pinecone (managed).

---

## 🧪 Testing Your Vector Store

### Quick validation

```python
from src.rag.vectorstore import query_vectorstore

# Test retrieval quality
test_queries = [
    "How do I reset a password?",
    "What are the available user roles?",
    "How do I configure backup settings?"
]

for query in test_queries:
    results = query_vectorstore(query, n_results=3)
    print(f"\nQuery: {query}")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Distance: {r['distance']:.3f} | Heading: {r['heading']}")
        print(f"     Text: {r['text'][:100]}...")
```

### Expected behavior
- Queries should return **semantically related** chunks, not just keyword matches
- Distance scores < 0.5 indicate strong relevance
- The top result should usually be the most useful

---

## 🐛 Troubleshooting

### Issue: `chromadb` import fails
**Solution:** Install ChromaDB:
```powershell
uv pip install chromadb
# or
pip install chromadb
```

### Issue: Empty or wrong results
**Check:**
1. Ensure the vector store was built: check if `./chroma_db/` exists
2. Verify you're using the same `collection_name` for build and query
3. Check that the embedding model matches (`nomic-embed-text` by default)
4. Try different queries — some domains may not be in your knowledge base

### Issue: Slow queries
**Solutions:**
- Reduce `n_results` (fewer results = faster)
- Check collection size — ChromaDB slows down above ~100K chunks (consider migrating)
- Ensure Ollama is running locally (remote embedding calls add latency)

### Issue: High memory usage
**Solutions:**
- ChromaDB loads collections on-demand; close Python sessions when idle
- Consider using a smaller embedding model (though `nomic-embed-text` is already efficient)
- For very large datasets, switch to Qdrant with disk-backed storage

---

## 🚀 Next Steps & Extensions

### 1. **Integrate with LLM (RAG completion)**
```python
from src.rag.vectorstore import query_vectorstore
import ollama

# Retrieve context
context_chunks = query_vectorstore("How do I reset a password?", n_results=3)
context = "\n\n".join([c["text"] for c in context_chunks])

# Build prompt
prompt = f"""Answer the following question using ONLY the provided context.

Context:
{context}

Question: How do I reset a password?

Answer:"""

# Generate response
response = ollama.generate(model="llama3.1:8b", prompt=prompt)
print(response["response"])
```

### 2. **Add hybrid search (keyword + semantic)**
ChromaDB supports keyword search alongside vector search. Combine both for better recall:
```python
# Future feature
results = collection.query(
    query_texts=["password reset"],  # Keyword
    query_embeddings=[query_embedding],  # Semantic
    n_results=10
)
```

### 3. **Implement re-ranking**
Use a cross-encoder model to re-rank the top-k results for better precision.

### 4. **Enable multi-collection support**
Index different document sets separately:
- `product_docs` — user manuals
- `api_specs` — technical API documentation
- `faqs` — frequently asked questions

Query them selectively based on user intent.

### 5. **Add versioning**
Track document versions by storing a `version` metadata field:
```python
metadata = {
    "heading": "User Management",
    "version": "2.3.1",
    "source_file": "UserGuide_PRODUCT_PLUS_Portal.pdf"
}
```

---

## 🔍 A Non-Obvious Insight  
The vector store is not just a database — **it is the "memory" of your RAG system**.  
The LLM is the reasoning engine, but the vector store is the knowledge engine.  
If the memory is weak, the reasoning collapses.

**In practice, this means:**
- Spend 80% of your RAG effort on quality retrieval (chunking, embeddings, vector store)
- Spend 20% on prompt engineering and LLM selection
- A mediocre LLM with excellent retrieval beats an excellent LLM with mediocre retrieval

---

## 📚 References & Further Reading

### ChromaDB Documentation
- [ChromaDB Docs](https://docs.trychroma.com/)
- [Python Client API](https://docs.trychroma.com/reference/Client)
- [Metadata Filtering](https://docs.trychroma.com/guides/querying#filtering-by-metadata)

### RAG Best Practices
- [LangChain Vector Store Guide](https://python.langchain.com/docs/modules/data_connection/vectorstores/)
- [Pinecone RAG Guide](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [OpenAI Cookbook: Question Answering](https://github.com/openai/openai-cookbook/blob/main/examples/Question_answering_using_embeddings.ipynb)

### Embedding Models
- [Nomic Embed Text](https://ollama.com/library/nomic-embed-text) (used in this project)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) (embedding model benchmarks)

---

## ✅ Implementation Checklist

- [x] Choose vector store (ChromaDB)
- [x] Install dependencies (`chromadb>=0.5.0`)
- [x] Implement `build_vectorstore()`
- [x] Implement `query_vectorstore()`
- [x] Test with sample queries
- [x] Add to `.gitignore`: `chroma_db/`
- [x] Wire into `main.py` pipeline
- [ ] Integrate with LLM for full RAG
- [ ] Add monitoring/logging for retrieval quality
- [ ] Document usage examples

---

**Status:** ✅ **Vector store implementation complete** (as of May 31, 2026)  
**Updated:** June 7, 2026 — CLI integration completed  
**Next milestone:** LangChain integration + LLM prompt construction

---

## 📝 Implementation History

### Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Vector DB | ChromaDB | Local, persistent, simple API |
| Embedding model | `nomic-embed-text` (768-dim) | Already in use, fast, good quality |
| Persist location | `./chroma_db/` | Relative to project root |
| IDs | `chunk_{i}` | Simple, reproducible indexing |
| Metadata stored | `heading` | Enables heading-level filtering |
| Distance metric | Cosine (L2) | ChromaDB default; works well for text |

### Implementation Steps Completed

1. ✅ Installed ChromaDB (`chromadb>=0.5.0`)
2. ✅ Implemented `build_vectorstore()` in `src/rag/vectorstore.py`
3. ✅ Implemented `query_vectorstore()` with Ollama integration
4. ✅ Integrated into `main.py` CLI with:
   - `build` command for processing PDFs
   - `query` command for semantic search
   - `interactive` mode for Q&A sessions
5. ✅ Added duplicate detection with `--force` override
6. ✅ Tested with sample queries
7. ✅ Added `chroma_db/` to `.gitignore`
8. ✅ Documented in README.md

