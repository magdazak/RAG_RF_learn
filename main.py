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
import logging

logging.basicConfig(level=logging.INFO)

def run_pipeline(pdf_path: str):
    """
    Run the RAG pipeline: markdown chunking + JSONL saving.

    Args:
        pdf_path (str): Path to the PDF file to process. The output markdown file will be saved in data_processed/ with the same base name.

    Returns:
        None

    Raises:
        FileNotFoundError: If Markdown file does not exist at output_path
    """
    # --- PDF → Text extraction ---
    base_file_name = os.path.basename(pdf_path)
    logging.info("=" * 50)
    logging.info(f"Starting with file: {base_file_name}...")

    raw = load_pdf(pdf_path)
    md = pdf_text_to_markdown(raw)

    md_output_path = f"data_processed/{os.path.splitext(base_file_name)[0]}.md"
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md)

    # --- RAG chunking and saving as JSONL ---
    #
    # # test only: get file content from existing .md file from 'data_processed' instead of re-processing the PDF
    # # below 'md' is only for testing the chunking and saving part, should replace with actual .md file content
    #
    # # Check if the output markdown file exists
    # if not os.path.exists(output_path):
    #     raise FileNotFoundError(f"Markdown file not found: {output_path}")

    logging.info("=" * 50)
    logging.info(f"Processing: {base_file_name} to chunks")

    # 1. Ensure the 'chunks' output directory exists
    jsonl_path = f"./json_chunks/{os.path.splitext(base_file_name)[0]}.jsonl"
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)

    # 2. Read Markdown content
    md = open(md_output_path, encoding="utf-8").read()

    # 3. Chunk the markdown text
    chunks = markdown_chunker(md, max_chunk_size=1000, overlap=100)

    # 4. Save chunks to JSONL
    save_chunks_to_jsonl(chunks, jsonl_path)
    logging.info("=" * 50)
    logging.info(f"✓ Saved {len(chunks)} chunks to {jsonl_path}")

    # TODO: add embeddings part

if __name__ == "__main__":
    # file_to_convert = "sample_final_part_1.pdf"
    file_to_convert = "BackupTool.pdf"

    run_pipeline(
        pdf_path=f"C:/CLIENT/PRODUCT_NET2/doc/{file_to_convert}"
    )
