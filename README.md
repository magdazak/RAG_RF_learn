# LLM Local

A local RAG (Retrieval Augmented Generation) pipeline for processing PDF documents into chunked, markdown-formatted content suitable for vector databases and language model integration.

## Overview

This project provides a complete pipeline for:

1. **PDF Extraction**: Convert PDF documents to raw text
2. **Text Processing**: Clean, normalize, and convert text to Markdown format
3. **Semantic Chunking**: Split Markdown content into semantically meaningful chunks
4. **Output Generation**: Save chunks as JSONL files for downstream processing

## Features

- 📄 **PDF Text Extraction** using `pdfminer-six`
- 🧹 **Intelligent Text Cleaning**:
  - Page number removal
  - Hyphenation fixing
  - Whitespace normalization
- 📝 **Markdown Conversion**:
  - Automatic heading detection (ALL CAPS → ## , Title Case → ###)
  - Bullet point standardization
  - List formatting
- 🔀 **Smart Chunking**:
  - Heading-aware section splitting
  - Configurable chunk size and overlap
  - Semantic preservation of document structure
- 💾 **JSONL Output**: Save chunks with heading context for RAG pipelines

## Project Structure

```
LLM_Local/
├── src/
│   ├── __init__.py
│   ├── data_extract/              # PDF to Markdown pipeline
│   │   ├── __init__.py
│   │   ├── pdf_loader.py         # PDF text extraction
│   │   ├── markdown_converter.py  # Text to Markdown conversion
│   │   └── text_cleaning.py      # Text normalization & formatting
│   └── rag/                        # Document chunking for RAG
│       ├── __init__.py
│       ├── chunking.py            # Markdown-aware chunking logic
│       ├── chunking_utils.py      # JSONL save utilities
│       ├── embeddings.py          # Embedding generation via local Ollama
│       └── vectorstore.py         # TODO: Vector store integration
├── main.py                         # Pipeline orchestration (draft)
├── pyproject.toml                  # Project metadata & dependencies
├── requirements.txt                # Dependency pinning
├── .gitignore                      # Git ignore rules
├── .python-version                 # Python version spec
└── README.md                       # This file
```

## Installation

### Prerequisites
- Python 3.12+
- pip or uv package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd LLM_Local
   ```

2. **Create virtual environment** (optional but recommended):
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

## Quick Start

### Basic Usage Example

```python
from src.data_extract.pdf_loader import load_pdf
from src.data_extract.markdown_converter import pdf_text_to_markdown
from src.rag.chunking import markdown_chunker
from src.rag.chunking_utils import save_chunks_to_jsonl

# 1. Extract text from PDF
pdf_path = "path/to/document.pdf"
raw_text = load_pdf(pdf_path)

# 2. Convert to Markdown
markdown_text = pdf_text_to_markdown(raw_text)

# 3. Create semantic chunks
chunks = markdown_chunker(markdown_text, max_chunk_size=1000, overlap=100)

# 4. Save as JSONL
save_chunks_to_jsonl(chunks, "output/chunks.jsonl")
```

### Running the Pipeline

```bash
python main.py
```

**Note**: `main.py` is currently a draft. Review TODOs and adjust file paths as needed.

## API Reference

### Data Extract Module

#### `load_pdf(path: str) -> str`
Extracts text from a PDF file.

**Parameters:**
- `path` (str): Path to the PDF file

**Returns:**
- str: Extracted text content

---

#### `pdf_text_to_markdown(raw_text: str) -> str`
Converts raw text to Markdown format.

**Parameters:**
- `raw_text` (str): Raw extracted text

**Returns:**
- str: Markdown-formatted text

---

#### Text Cleaning Functions

- `normalize_text(text: str) -> str`: Normalize text (remove page numbers, fix hyphens)
- `convert_lists(text: str) -> str`: Convert bullet points to Markdown lists
- `convert_headings(text: str) -> str`: Convert text to Markdown headings

### RAG Module

#### `markdown_chunker(md_text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict]`
Main chunking function for semantic splitting.

**Parameters:**
- `md_text` (str): Markdown text to chunk
- `max_chunk_size` (int): Maximum characters per chunk (default: 1000)
- `overlap` (int): Character overlap between chunks (default: 100)

**Returns:**
- List[Dict]: Chunks with structure `{"text": str, "heading": str}`

---

#### `save_chunks_to_jsonl(chunks: List[Dict], output_path: str)`
Saves chunks to JSONL format.

**Parameters:**
- `chunks` (List[Dict]): List of chunk dictionaries
- `output_path` (str): Output file path

---

#### `get_embedding(text: str, model: str = "nomic-embed-text") -> List[float]`
Generates a vector embedding for a single text string using a local Ollama model.

**Parameters:**
- `text` (str): Input text to embed
- `model` (str): Ollama embedding model name (default: `"nomic-embed-text"`)

**Returns:**
- `List[float]`: The embedding vector

**Recommended models** (pull with `ollama pull <model>` before use):
- `nomic-embed-text` — fast, 768-dim, good for most RAG use cases
- `mxbai-embed-large` — higher quality, 1024-dim, better retrieval scores

> ⚠️ Use a **dedicated embedding model**, not a generative model like `llama3.1:8b`.

---

#### `embed_chunks(chunks: List[Dict], model: str = "nomic-embed-text") -> List[Dict]`
Adds an `"embedding"` field to each chunk dict and returns the enriched list.

**Parameters:**
- `chunks` (List[Dict]): Chunk dicts from `markdown_chunker()` — `{"text": str, "heading": str}`
- `model` (str): Ollama embedding model name (default: `"nomic-embed-text"`)

**Returns:**
- `List[Dict]`: Same list with `"embedding": List[float]` added to every chunk

---

## Configuration

### Chunking Parameters

Adjust these in `main.py` or when calling `markdown_chunker()`:

- **max_chunk_size**: Size threshold (characters) for splitting chunks
  - Smaller values: More granular, more chunks
  - Larger values: Coarser, fewer chunks
  
- **overlap**: Character overlap between consecutive chunks
  - Prevents loss of context at chunk boundaries
  - Typical: 10-20% of max_chunk_size

## Data Directories

- `data_raw/`: Place raw PDF files here (ignored by git)
- `data_processed/`: Output markdown files (ignored by git)
- `json_chunks/`: Generated JSONL chunks (ignored by git)

## Dependencies

- **pdfminer-six** (≥20260107): PDF text extraction
- **cffi**, **cryptography**, **charset-normalizer**, **pycparser**: Transitive dependencies

See `requirements.txt` for exact versions.

## Roadmap

- [x] **Embeddings Module**: Local embedding generation via Ollama (`nomic-embed-text` / `mxbai-embed-large`)
- [ ] **Vector Store**: FAISS or Pinecone integration
- [ ] **LangChain Integration**: Seamless RAG pipeline
- [ ] **Enhanced CLI**: Command-line interface for batch processing
- [ ] **Web API**: FastAPI endpoint for document processing
- [ ] **Docker Support**: Containerized deployment
- [ ] **Testing Suite**: Unit and integration tests
- [ ] **Documentation**: Extended guides and examples

## Known Issues & TODOs

1. **main.py**: Currently a draft version - see inline TODOs
2. **vectorstore.py**: Placeholder module - implementation pending
3. **Error Handling**: Consider adding more robust error handling for edge cases
4. **Type Hints**: Could be enhanced with more specific return types

## Contributing

Contributions are welcome! Please:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

[Specify your license here - e.g., MIT, Apache 2.0]

## Contact

For questions or support, please contact the project maintainer.

---

## Development Notes

### Python Version
- Requires: Python 3.12+
- Configured in `.python-version`

### Virtual Environment
- Pre-configured for uv package manager
- `uv.lock` provides reproducible builds

### Code Style
- Follow PEP 8
- Use type hints for public APIs
- Add docstrings to all functions and modules

---

**Last Updated**: April 2026

