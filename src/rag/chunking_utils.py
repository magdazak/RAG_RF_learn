import os
import json
from typing import List, Dict

def save_chunks_to_jsonl(chunks: List[Dict], output_path: str):
    """
    Saves a list of chunk dicts to a JSONL file, one chunk per line.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            json.dump(chunk, f, ensure_ascii=False)
            f.write('\n')

# Example usage:
# from chunking import markdown_chunker
# md_text = open('data_processed/BackupTool_2.md', encoding='utf-8').read()
# chunks = markdown_chunker(md_text, max_chunk_size=1000, overlap=100)
# save_chunks_to_jsonl(chunks, 'json_chunks/BackupTool_2.jsonl')

