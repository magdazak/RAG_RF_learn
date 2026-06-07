"""
RAG Pipeline CLI - Build and query vector stores from PDF documents.

COMMANDS:
  build      - Process PDF and build vector store
  query      - Query the vector store with a question
  interactive - Interactive Q&A mode

EXAMPLES:
  python main.py build path/to/document.pdf
  python main.py query "How do I configure the system?"
  python main.py interactive
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
        console.print(f"  python main.py build \"{pdf_path}\" --force\n")
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
    show_distance: bool = typer.Option(False, help="Show similarity distances"),
):
    """
    Query the vector store with a question.
    
    Returns the most relevant chunks from the document collection.
    """
    # Import only when needed
    from src.rag.vectorstore import query_vectorstore
    
    console.print(f"\n[bold cyan]Querying:[/bold cyan] {question}\n")
    
    results = query_vectorstore(
        query_text=question,
        collection_name=collection_name,
        persist_dir=persist_dir,
        n_results=n_results,
    )
    
    if not results:
        console.print("[yellow]No results found.[/yellow]\n")
        return
    
    console.print(f"[bold green]Found {len(results)} relevant chunks:[/bold green]\n")
    
    for i, result in enumerate(results, 1):
        console.print(f"[bold]Result {i}:[/bold]")
        if result.get("heading"):
            console.print(f"[dim]Section: {result['heading']}[/dim]")
        if show_distance:
            console.print(f"[dim]Distance: {result['distance']:.4f}[/dim]")
        console.print(Markdown(result['text']))
        console.print()


@app.command()
def interactive(
    collection_name: str = typer.Option("product_docs", help="ChromaDB collection name"),
    persist_dir: str = typer.Option("./chroma_db", help="ChromaDB persistence directory"),
    n_results: int = typer.Option(3, help="Number of results per query"),
):
    """
    Interactive Q&A mode.
    
    Ask questions and get answers from the vector store in an interactive loop.
    Type 'quit', 'exit', or press Ctrl+C to exit.
    """
    # Import only when needed
    from src.rag.vectorstore import query_vectorstore
    
    console.print("\n[bold cyan]Interactive Q&A Mode[/bold cyan]")
    console.print(f"Collection: '{collection_name}' at '{persist_dir}'")
    console.print("Type 'quit' or 'exit' to stop.\n")
    
    try:
        while True:
            question = typer.prompt("\n❓ Your question")
            
            if question.lower() in ["quit", "exit", "q"]:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                break
            
            results = query_vectorstore(
                query_text=question,
                collection_name=collection_name,
                persist_dir=persist_dir,
                n_results=n_results,
            )
            
            if not results:
                console.print("[yellow]No results found.[/yellow]")
                continue
            
            console.print(f"\n[bold green]Top {len(results)} relevant chunks:[/bold green]\n")
            
            for i, result in enumerate(results, 1):
                console.print(f"[bold]Result {i}:[/bold]")
                if result.get("heading"):
                    console.print(f"[dim]Section: {result['heading']}[/dim]")
                console.print(Markdown(result['text']))
                console.print()
                
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[yellow]Goodbye![/yellow]\n")


if __name__ == "__main__":
    app()

