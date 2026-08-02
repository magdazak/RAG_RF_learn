"""
RAG Pipeline CLI - Build and query vector stores from PDF documents.

PRECONDITIONS:
  1. Ollama must be running
     - Install: https://ollama.ai/
     - Start Ollama service (e.g., `ollama serve`)

  2. Required Ollama models:
     - Embedding model: nomic-embed-text
       $ ollama pull nomic-embed-text
     - Generation model: llama3.1:8b (or custom via --model)
       $ ollama pull llama3.1:8b

  3. Python dependencies:
     $ pip install -r requirements.txt
     (or use uv: uv sync)

COMMANDS:
  build      - Process PDF and build vector store
  query      - Query the vector store with a question
  interactive - Interactive Q&A mode

EXAMPLES:
  python rag_cli.py build path/to/document.pdf
  python rag_cli.py query "How do I configure the system?"
  python rag_cli.py interactive
  
  # Use web search to augment answers (⚠️ sends query to DuckDuckGo)
  python rag_cli.py query "How does OAuth work?" --web-search
  python rag_cli.py interactive --web-search

WEB SEARCH:
  The --web-search flag augments answers with information from the internet.
  
  ⚠️ PRIVACY WARNING:
  - Your query is sent to DuckDuckGo servers
  - Do NOT use if your questions contain sensitive/internal information
  - Only use for generic, non-confidential questions
  
  Without --web-search: Answers come ONLY from your local documents
  With --web-search:    Answers combine local docs + web results
"""

import os
import logging
import typer
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(help="RAG Pipeline - Build and query document vector stores")
console = Console()

logging.basicConfig(level=logging.INFO)

# Suppress httpx INFO logs unless in debug mode
if logging.getLogger().level > logging.DEBUG:
    logging.getLogger("httpx").setLevel(logging.WARNING)

@app.command()
def build(
    pdf_path: str = typer.Argument(..., help="Path to the PDF file to process"),
    collection_name: str = typer.Option("product_docs", help="ChromaDB collection name"),
    persist_dir: str = typer.Option("./chroma_db", help="ChromaDB persistence directory"),
    max_chunk_size: int = typer.Option(1000, help="Maximum chunk size in characters"),
    overlap: int = typer.Option(100, help="Overlap between chunks in characters"),
    force: bool = typer.Option(False, "--force", "-f", help="Force rebuild even if file was already processed"),
):
    """
    Build vector store from a PDF document.
    
    Processes the PDF through the full pipeline:
    1. Extract text from PDF
    2. Convert to Markdown
    3. Chunk the text
    4. Generate embeddings
    5. Store in ChromaDB vector store
    """
    # --- Check if file was already processed (before imports for early exit) ---
    base_file_name = os.path.basename(pdf_path)
    embedded_jsonl_path = f"./json_chunks/{os.path.splitext(base_file_name)[0]}_embedded.jsonl"
    
    if os.path.exists(embedded_jsonl_path) and not force:
        console.print(f"\n[yellow]⚠ Warning:[/yellow] This PDF appears to have been processed already.")
        console.print(f"[dim]Existing file: {embedded_jsonl_path}[/dim]")
        console.print(f"\n[bold]Use --force to rebuild:[/bold]")
        console.print(f"  python rag_cli.py build \"{pdf_path}\" --force\n")
        raise typer.Exit(0)
    
    if force and os.path.exists(embedded_jsonl_path):
        console.print(f"[yellow]🔄 Force rebuild enabled - overwriting existing files...[/yellow]\n")
    
    # Import only when needed (after duplicate check)
    from src.data_extract.pdf_loader import load_pdf
    from src.data_extract.markdown_converter import pdf_text_to_markdown
    from src.rag.chunking import markdown_chunker
    from src.rag.chunking_utils import save_chunks_to_jsonl
    from src.rag.embeddings import embed_chunks
    from src.rag.vectorstore import build_vectorstore
    
    # --- PDF → Text extraction ---
    console.print(f"\n[bold cyan]Starting pipeline for:[/bold cyan] {base_file_name}\n")

    raw = load_pdf(pdf_path)
    md = pdf_text_to_markdown(raw)

    md_output_path = f"data_processed/{os.path.splitext(base_file_name)[0]}.md"
    os.makedirs(os.path.dirname(md_output_path), exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md)
    console.print(f"[green]✓[/green] Converted to markdown: {md_output_path}")

    # --- RAG chunking and saving as JSONL ---
    console.print(f"\n[bold cyan]Chunking document...[/bold cyan]")

    # 1. Ensure the 'chunks' output directory exists
    jsonl_path = f"./json_chunks/{os.path.splitext(base_file_name)[0]}.jsonl"
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)

    # 2. Read Markdown content
    md = open(md_output_path, encoding="utf-8").read()

    # 3. Chunk the markdown text
    chunks = markdown_chunker(md, max_chunk_size=max_chunk_size, overlap=overlap)

    # 4. Save chunks to JSONL
    save_chunks_to_jsonl(chunks, jsonl_path)
    console.print(f"[green]✓[/green] Saved {len(chunks)} chunks to {jsonl_path}")

    # 5. Generate embeddings and save enriched chunks to a separate JSONL
    console.print(f"\n[bold cyan]Generating embeddings...[/bold cyan] (this may take a while)")
    embedded_chunks = embed_chunks(chunks)

    # embedded_jsonl_path was already defined during duplicate check
    save_chunks_to_jsonl(embedded_chunks, embedded_jsonl_path)
    console.print(f"[green]✓[/green] Saved {len(embedded_chunks)} embedded chunks to {embedded_jsonl_path}")

    # 6. Store embedded chunks in ChromaDB
    console.print(f"\n[bold cyan]Building vector store...[/bold cyan]")
    build_vectorstore(
        embedded_chunks,
        collection_name=collection_name,
        persist_dir=persist_dir
    )
    console.print(f"[green]✓[/green] Vector store built successfully!")
    console.print(f"\n[bold green]Pipeline complete![/bold green] Collection: '{collection_name}' at '{persist_dir}'\n")


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask the vector store"),
    collection_name: str = typer.Option("product_docs", help="ChromaDB collection name"),
    persist_dir: str = typer.Option("./chroma_db", help="ChromaDB persistence directory"),
    n_results: int = typer.Option(5, help="Number of results to return"),
    model: str = typer.Option("llama3.1:8b", help="Ollama model for answer generation"),
    web_search: bool = typer.Option(False, "--web-search", help="⚠️ Augment with web search (sends query to DuckDuckGo)"),
):
    """
    Query the vector store and generate a concise answer.
    
    Retrieves relevant chunks from your local documents and synthesizes them 
    into a direct answer using a local LLM (Ollama).
    
    \b
    WEB SEARCH (--web-search):
    ⚠️  WARNING: Sends your query to DuckDuckGo servers!
    - Use ONLY for generic, non-sensitive questions
    - Do NOT use if question contains internal/confidential information
    - Augments local docs with internet search results
    
    \b
    Examples:
      python rag_cli.py query "How does JWT authentication work?"
      python rag_cli.py query "What is OAuth 2.0?" --web-search
    """
    from src.rag.vectorstore import query_and_generate
    
    # Display warning if web search is enabled
    if web_search:
        console.print("\n[bold yellow]⚠️  PRIVACY WARNING ⚠️[/bold yellow]")
        console.print("[yellow]Web search is enabled. Your query will be sent to DuckDuckGo servers.[/yellow]")
        console.print("[yellow]Do NOT use this if your question contains sensitive/internal information.[/yellow]\n")
    
    console.print(f"\n[bold cyan]Querying:[/bold cyan] {question}\n")
    console.print(f"[bold cyan]Generating answer...[/bold cyan]\n")
    
    answer = query_and_generate(
        query_text=question,
        collection_name=collection_name,
        persist_dir=persist_dir,
        n_results=n_results,
        generation_model=model,
        use_web_search=web_search,
    )
    
    console.print(f"[bold green]Answer:[/bold green]\n")
    console.print(answer)
    console.print()


@app.command()
def interactive(
    collection_name: str = typer.Option("product_docs", help="ChromaDB collection name"),
    persist_dir: str = typer.Option("./chroma_db", help="ChromaDB persistence directory"),
    n_results: int = typer.Option(3, help="Number of results per query"),
    model: str = typer.Option("llama3.1:8b", help="Ollama model for answer generation"),
    web_search: bool = typer.Option(False, "--web-search", help="⚠️ Augment with web search (sends query to DuckDuckGo)"),
):
    """
    Interactive Q&A mode with answer generation.
    
    Ask questions in an interactive loop and get concise answers synthesized 
    from your local documents using a local LLM (Ollama).
    
    Type 'quit', 'exit', or press Ctrl+C to exit.
    
    \b
    WEB SEARCH (--web-search):
    ⚠️  WARNING: Sends ALL queries to DuckDuckGo servers!
    - Use ONLY for generic, non-sensitive questions
    - Do NOT use if questions contain internal/confidential information
    - Augments local docs with internet search results
    
    \b
    Examples:
      python rag_cli.py interactive
      python rag_cli.py interactive --web-search
    """
    from src.rag.vectorstore import query_and_generate
    
    console.print("\n[bold cyan]Interactive Q&A Mode[/bold cyan]")
    console.print(f"Collection: '{collection_name}' at '{persist_dir}'")
    
    # Display warning if web search is enabled
    if web_search:
        console.print("\n[bold yellow]⚠️  PRIVACY WARNING ⚠️[/bold yellow]")
        console.print("[yellow]Web search is ENABLED. All queries will be sent to DuckDuckGo servers.[/yellow]")
        console.print("[yellow]Do NOT ask questions containing sensitive/internal information.[/yellow]")
    
    console.print("\nType 'quit' or 'exit' to stop.\n")
    
    try:
        while True:
            question = typer.prompt("\n❓ Your question")
            
            if question.lower() in ["quit", "exit", "q"]:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                break
            
            console.print(f"\n[bold cyan]Generating answer...[/bold cyan]")
            answer = query_and_generate(
                query_text=question,
                collection_name=collection_name,
                persist_dir=persist_dir,
                n_results=n_results,
                generation_model=model,
                use_web_search=web_search,
            )
            
            console.print(f"\n[bold green]Answer:[/bold green]")
            console.print(answer)
                
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[yellow]Goodbye![/yellow]\n")


if __name__ == "__main__":
    app()

