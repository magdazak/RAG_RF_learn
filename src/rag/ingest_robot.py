"""
Ingest Robot Framework / Python-library files into a ChromaDB collection.

Pipeline (all steps are driven from this file):
    1. collect files (+ duplicate file-name check)
    2. chunk      -> chunking_robot.py  (chunk_robot_file / chunk_python_file)
    3. embed      -> embeddings.py      (embed_chunks, Ollama model)
    4. store      -> vectorstore.py     (build_vectorstore, upsert into the collection)
Steps 3-4 are skipped with --dry-run.

Usage (from repo root):
    python -m src.rag.ingest_robot --project net data_raw/robot/net
    python -m src.rag.ingest_robot --project general path/to/File.robot other/Lib.py --dry-run

Arguments are files and/or directories (searched recursively for .robot, .resource, .py). One project per run.
File names must be unique within a run (stored as `source_file`); duplicates abort before anything is written.
doc_id is "{project}/{file name}", so re-ingesting a file overwrites its own chunks.
"""
import argparse
import logging
from collections import Counter
from pathlib import Path
from typing import List

from src.rag.chunking_robot import PROJECTS, chunk_python_file, chunk_robot_file

logger = logging.getLogger(__name__)

EXTENSIONS = {".robot", ".resource", ".py"}
DEFAULT_COLLECTION = "product_ast"


def collect_files(inputs: List[str]) -> List[Path]:
    files: List[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            files.extend(f for f in sorted(p.rglob("*")) if f.suffix.lower() in EXTENSIONS and "__pycache__" not in f.parts)
        elif p.is_file() and p.suffix.lower() in EXTENSIONS:
            files.append(p)
        else:
            raise SystemExit(f"Not a supported file or directory: {item}")
    return files


def check_duplicates(files: List[Path]) -> None:
    dups = sorted(n for n, c in Counter(f.name for f in files).items() if c > 1)
    if dups:
        raise SystemExit(f"Duplicate file names, rename them or ingest separately: {dups}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, choices=PROJECTS)
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--persist-dir", default="./chroma_db")
    ap.add_argument("--dry-run", action="store_true", help="chunk and report only; no embedding, nothing stored")
    ap.add_argument("inputs", nargs="+", help="files and/or directories")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)

    files = collect_files(args.inputs)
    if not files:
        raise SystemExit("No .robot/.resource/.py files found.")
    check_duplicates(files)

    all_chunks = []
    for f in files:
        fn = chunk_python_file if f.suffix.lower() == ".py" else chunk_robot_file
        chunks = fn(str(f), project=args.project)
        logger.info("%s: %d chunk(s)", f.name, len(chunks))
        all_chunks.append((f, chunks))

    total = sum(len(c) for _, c in all_chunks)
    if args.dry_run:
        logger.info("Dry run: %d file(s), %d chunk(s); nothing stored.", len(files), total)
        return

    from src.rag.embeddings import embed_chunks
    from src.rag.vectorstore import build_vectorstore

    for f, chunks in all_chunks:
        if not chunks:
            continue
        build_vectorstore(
            embed_chunks(chunks),
            collection_name=args.collection,
            persist_dir=args.persist_dir,
            doc_id=f"{args.project}/{f.name}",
        )
    logger.info("Done: %d file(s), %d chunk(s) -> '%s' at '%s'.", len(files), total, args.collection, args.persist_dir)


if __name__ == "__main__":
    main()
