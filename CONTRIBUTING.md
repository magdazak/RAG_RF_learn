# Contributing to LLM Local

Thank you for your interest in contributing to LLM Local! This document provides guidelines for development, testing, and submitting contributions.

## Code Organization

- **`src/data_extract/`**: PDF processing and text cleaning
- **`src/rag/`**: Document chunking and vector store (RAG pipeline)
- **`main.py`**: Pipeline orchestration (currently draft)
- **Tests**: To be added in `tests/` directory

## Development Setup

### Prerequisites
- Python 3.12+
- Git
- Virtual environment (recommended)

### Steps

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/LLM_Local.git
   cd LLM_Local
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   # Optional: Install dev dependencies
   pip install pytest black isort mypy
   ```

4. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

## Code Standards

### Style Guide
- Follow **PEP 8**
- Use `black` for formatting:
  ```bash
  black src/ main.py
  ```
- Use `isort` for import organization:
  ```bash
  isort src/ main.py
  ```

### Type Hints
- Add type hints to all public functions
- Example:
  ```python
  def process_text(input_text: str, max_length: int = 1000) -> str:
      """Process text with optional length limit."""
      return input_text[:max_length]
  ```

### Docstrings
- Use docstring format with description, Args, Returns, and Raises
- Example:
  ```python
  def normalize_text(text: str) -> str:
      """
      Normalize and clean text input.
      
      Args:
          text (str): Raw text to normalize
          
      Returns:
          str: Cleaned and normalized text
          
      Raises:
          ValueError: If text is empty
      """
      if not text:
          raise ValueError("Text cannot be empty")
      return text.strip()
  ```

## Adding New Features

### Adding a New Text Cleaning Function

1. **Add function to `src/data_extract/text_cleaning.py`**:
   ```python
   def remove_special_characters(text: str) -> str:
       """Remove special characters from text."""
       import re
       return re.sub(r'[^\w\s]', '', text)
   ```

2. **Export from `src/data_extract/__init__.py`**:
   ```python
   from .text_cleaning import (
       normalize_text,
       convert_lists,
       convert_headings,
       remove_special_characters,  # Add here
   )
   
   __all__ = [
       "normalize_text",
       "convert_lists",
       "convert_headings",
       "remove_special_characters",  # Add here
   ]
   ```

3. **Update `markdown_converter.py` if needed**:
   ```python
   def pdf_text_to_markdown(raw_text: str) -> str:
       text = normalize_text(raw_text)
       text = remove_special_characters(text)  # Add call
       text = convert_lists(text)
       text = convert_headings(text)
       return text
   ```

### Adding Embedding Support

Implement functions in `src/rag/embeddings.py`:

```python
"""Embedding generation module."""
from typing import List, Dict
import numpy as np

def embed_chunks(chunks: List[Dict], model: str = "all-MiniLM-L6-v2") -> np.ndarray:
    """
    Generate embeddings for document chunks.
    
    Args:
        chunks: List of chunk dictionaries with 'text' key
        model: Embedding model identifier
        
    Returns:
        Array of embeddings (shape: n_chunks x embedding_dim)
    """
    # Implementation here
    pass
```

### Adding Vector Store Integration

Implement class in `src/rag/vectorstore.py`:

```python
"""Vector store integration."""
from typing import List, Dict, Tuple
import numpy as np

class VectorStore:
    """Base vector store interface."""
    
    def __init__(self, index_path: str = "./vector_index"):
        """Initialize vector store."""
        self.index_path = index_path
    
    def add_vectors(self, ids: List[str], embeddings: np.ndarray) -> None:
        """Add vectors to the store."""
        pass
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for nearest neighbors."""
        pass
```

## Testing

### Writing Tests

Create test file in `tests/test_module_name.py`:

```python
"""Tests for text_cleaning module."""
import pytest
from src.data_extract.text_cleaning import normalize_text

def test_normalize_text_removes_page_numbers():
    """Test that page numbers are removed."""
    text = "Page 1\nHello world\nPage 2"
    result = normalize_text(text)
    assert "Page" not in result
    assert "Hello world" in result

def test_normalize_text_empty_string():
    """Test handling of empty string."""
    result = normalize_text("")
    assert result == ""

def test_normalize_text_preserves_content():
    """Test that content is preserved after normalization."""
    text = "Hello\n\n\nWorld"
    result = normalize_text(text)
    assert "Hello" in result
    assert "World" in result
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_text_cleaning.py

# Run with coverage
pytest --cov=src tests/
```

## Git Workflow

### Committing Changes

Write clear, concise commit messages:

```bash
# Good
git commit -m "Add normalize_text function for cleaning extracted PDF text"

# Bad
git commit -m "fix stuff"
```

### Commit Message Format

```
[Type] Brief description

Optional detailed explanation of changes and reasoning.

Fixes #123 (if applicable)
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation updates
- `test`: Test additions/fixes
- `chore`: Build, dependencies, etc.

### Submitting Pull Request

1. **Push branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub**:
   - Provide clear title and description
   - Reference related issues
   - Include any testing notes

3. **PR Checklist**:
   - [ ] Code follows PEP 8 style
   - [ ] Type hints added
   - [ ] Docstrings included
   - [ ] Tests written and passing
   - [ ] README updated if needed
   - [ ] Commit messages are clear

## Documentation

### Updating README
- Keep it concise and up-to-date
- Add examples for new features
- Include API documentation

### Updating PROJECT_STRUCTURE.md
- Document new modules
- Update architecture diagrams if needed
- Keep data flow examples current

## Roadmap Features

### High Priority
- [ ] **Embeddings Module**: OpenAI/HuggingFace integration
- [ ] **Vector Store**: FAISS integration
- [ ] **Testing Suite**: Unit tests for all modules
- [ ] **Error Handling**: Robust error handling throughout

### Medium Priority
- [ ] **LangChain Integration**: Full LangChain support
- [ ] **CLI Tool**: Command-line interface
- [ ] **Batch Processing**: Process multiple documents
- [ ] **Logging**: Structured logging

### Future Enhancements
- [ ] **Web API**: FastAPI endpoint
- [ ] **Docker**: Containerized deployment
- [ ] **Configuration Management**: Config files
- [ ] **Performance Optimization**: Caching, parallel processing

## Questions & Support

- **Documentation**: See [README.md](README.md)
- **Issues**: Check GitHub issues or create a new one
- **Discussions**: Join project discussions

## Code Review Process

All submissions undergo code review for:
- ✅ Code quality and style
- ✅ Type safety and correctness
- ✅ Test coverage
- ✅ Documentation completeness
- ✅ Performance considerations

## License

By contributing to LLM Local, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🚀

