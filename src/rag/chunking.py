"""
Markdown chunker optimized for RAG (Retrieval Augmented Generation).
Splits markdown text into semantically meaningful chunks based on headings, lists, and paragraphs.
"""
import re
from typing import List, Dict

# Optional: If you want to count tokens, you can use tiktoken or nltk. For now, we'll use character count.

def split_markdown_by_headings(md_text: str) -> List[Dict]:
    """
    Splits markdown text into sections based on headings.
    Returns a list of dicts: {heading, content, start_idx, end_idx}
    """
    heading_pattern = re.compile(r'^(#{1,6})\s*(.+)', re.MULTILINE)
    sections = []
    last_pos = 0
    matches = list(heading_pattern.finditer(md_text))
    if not matches:
        return [{"heading": None, "content": md_text, "start_idx": 0, "end_idx": len(md_text)}]
    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(md_text)
        content = md_text[start:end]
        sections.append({"heading": heading, "content": content, "start_idx": start, "end_idx": end})
    return sections

def chunk_section(section: Dict, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
    """
    Further splits a section into chunks by paragraphs/lists, with optional overlap.
    Returns list of chunk dicts.
    Parameters: section - a section dict;
                max_chunk_size - the maximum number of chunks to split;
                overlap - the maximum number of chunks to split the text into
    """
    content = section["content"]
    heading = section["heading"]
    paragraphs = re.split(r'\n\s*\n', content)
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size:
            chunks.append({"text": current_chunk.strip(), "heading": heading})
            # Add overlap
            if overlap > 0 and chunks:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + para
            else:
                current_chunk = para
        else:
            current_chunk += para + "\n\n"
    if current_chunk.strip():
        chunks.append({"text": current_chunk.strip(), "heading": heading})
    return chunks

def markdown_chunker(md_text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
    """
    Main chunking function. Splits markdown by headings, then chunks sections.
    Returns list of chunk dicts: {text, heading}
    Parameters: md_text - a markdown text;
                max_chunk_size - the maximum number of chunks to split;
                overlap - the maximum number of chunks to split the text into
    """
    sections = split_markdown_by_headings(md_text)
    all_chunks = []
    for section in sections:
        chunks = chunk_section(section, max_chunk_size, overlap)
        all_chunks.extend(chunks)
    return all_chunks

# Example usage:
# md_text = open('data_processed/BackupTool_2.md', encoding='utf-8').read()
# chunks = markdown_chunker(md_text, max_chunk_size=1000, overlap=100)
# for chunk in chunks:
#     print(chunk['heading'], chunk['text'][:100])
