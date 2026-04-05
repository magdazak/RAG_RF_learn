"""
Main pipeline orchestration script (DRAFT VERSION).

This script demonstrates the RAG chunking pipeline for converting Markdown documents
into semantic chunks saved as JSONL files.

TODO / DRAFT NOTES:
- This is a draft implementation for testing the chunking and JSONL saving components
- PDF extraction is temporarily disabled (see commented code)
- Currently expects markdown files in data_processed/ directory
- Consider refactoring into proper configuration management (e.g., click, argparse)
- Add error handling and logging for production use
- Consider batch processing for multiple documents

TYPICAL WORKFLOW:
1. Place PDF files in data_raw/
2. Configure pdf_path and output_path
3. Run this script to generate JSONL chunks in json_chunks/

WARNING: File paths are currently hardcoded - update as needed for your environment.
"""

from src.data_extract.pdf_loader import load_pdf
from src.data_extract.markdown_converter import pdf_text_to_markdown
from src.rag.chunking import markdown_chunker
from src.rag.chunking_utils import save_chunks_to_jsonl
import os

def run_pipeline(file_name: str, pdf_path: str, output_path: str):
    """
    Run the RAG pipeline: markdown chunking + JSONL saving.

    Args:
        file_name (str): Name of the document (without extension)
        pdf_path (str): Path to the PDF file (currently unused in draft)
        output_path (str): Path where markdown file is expected

    Returns:
        None

    Raises:
        FileNotFoundError: If markdown file does not exist at output_path
    """
    # # DISABLED IN DRAFT: PDF → Text extraction
    # # Uncomment when ready to process PDFs from raw
    # # raw = load_pdf(pdf_path)
    # # md = pdf_text_to_markdown(raw)
    # # with open(output_path, "w", encoding="utf-8") as f:
    # #     f.write(md)

    # Ensure output_path is formatted with file_name if needed
    base_name = os.path.splitext(file_name)[0]
    output_path = output_path.format(file_name=base_name)

    # --- RAG chunking and saving as JSONL ---

    # TODO: get file content from existing .md file from 'data_processed' instead of re-processing the PDF
    # below 'md' is only for testing the chunking and saving part, should replace with actual .md file content

    # Check if the output markdown file exists
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Markdown file not found: {output_path}")

    # Read markdown content
    md = open(output_path, encoding="utf-8").read()

    print(f"Processing: {base_name}")
    jsonl_path = f"./json_chunks/{base_name}.jsonl"

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)

    # Chunk the markdown text
    chunks = markdown_chunker(md, max_chunk_size=1000, overlap=100)

    # Save chunks to JSONL
    save_chunks_to_jsonl(chunks, jsonl_path)
    print(f"✓ Saved {len(chunks)} chunks to {jsonl_path}")

# TODO: test only the RAG chunk part
if __name__ == "__main__":
    file_name = "sample_final_part_1.pdf"

    run_pipeline(
        file_name="sample_final_part_1.pdf",
        # pdf_path="data_raw/BackupTool.pdf",
        pdf_path=f"C:/CLIENT/PRODUCT_NET2/doc/{file_name}.pdf",
        output_path="data_processed/{file_name}.md"
    )
