"""
Robot Framework / Python-library chunker for RAG.

Unlike `chunking.py` (markdown headings/paragraphs), a chunk here is one keyword, one test case, or one public Python
function/method. Output chunks are plain dicts: {"text", "heading", "metadata": {...}}.
Metadata values are scalars only (ChromaDB requirement); lists are joined with "|".

Metadata set on every chunk:
    source_file  File name by default; the optional `rel_path` argument overrides it (e.g. "folder/File.robot").
                 Only needed if two files can share a name. Nothing here detects duplicates - the ingestion code
                 must check that (and should use "{project}/{file name}" as doc_id).
    project      REQUIRED, one of PROJECTS ("net", "mobile2", "mobile3", "general"); anything else raises ValueError.
                 Used to filter queries (Chroma `where={"project": ...}`); it is NOT the Chroma collection name.
                 One project per run/call; shared files are ingested once as "general", never under several projects.
    type         keyword | testcase | locator (merged single-RETURN getters) | python_keyword
    name, tags, args, and for Python files also `class`.

Parsing: .robot/.resource files use Robot Framework's official `robot.api.get_model` (AST with exact names,
[Arguments], [Tags], [Documentation], line ranges; no regexes) walked by a `ModelVisitor`; Python libraries use the
stdlib `ast` module.

Usage:
    CLI: python src/rag/chunking_robot.py --project net file1.robot file2.py ...   (prints chunks, saves nothing)
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional

from robot.api import get_model
from robot.api.parsing import ModelVisitor, Token

MAX_CHUNK_CHARS = 1500
LIST_SEP = "|"
PROJECTS = ("net", "mobile2", "mobile3", "general")


def _check_project(project: str) -> str:
    if project not in PROJECTS:
        raise ValueError(f"project must be one of {PROJECTS}, got {project!r}")
    return project


def _join(values) -> str:
    return LIST_SEP.join(str(v) for v in values)


class _RobotVisitor(ModelVisitor):
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.items: List[Dict] = []

    def _source(self, node) -> str:
        return "".join(self.lines[node.lineno - 1:node.end_lineno]).rstrip()

    def _collect(self, node, kind: str):
        name = node.name
        doc, tags, args = "", [], []
        body_statements = []
        for stmt in node.body:
            t = getattr(stmt, "type", None)
            if t == Token.DOCUMENTATION:
                doc = stmt.value
            elif t == Token.TAGS:
                tags = list(stmt.values)
            elif t == Token.ARGUMENTS:
                args = list(stmt.args) if hasattr(stmt, "args") else list(stmt.values)
            elif t not in (Token.EOL, Token.COMMENT):
                body_statements.append(stmt)
        is_getter = (
            kind == "keyword"
            and len(body_statements) == 1
            and body_statements[0].type == Token.RETURN_STATEMENT
        )
        self.items.append({
            "name": name, "kind": kind, "doc": doc, "tags": tags, "args": args,
            "is_getter": is_getter, "text": self._source(node),
        })

    def visit_Keyword(self, node):
        self._collect(node, "keyword")

    def visit_TestCase(self, node):
        self._collect(node, "testcase")


def _split_text(text: str, limit: int = MAX_CHUNK_CHARS) -> List[str]:
    """Split on line boundaries so each part is <= limit chars (single long lines kept whole)."""
    parts, cur = [], ""
    for line in text.splitlines():
        if cur and len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts


def chunk_robot_file(
    path: str,
    project: str,
    rel_path: Optional[str] = None,
    merge_getters: bool = True,
) -> List[Dict]:
    """
    Parse a .robot/.resource file into one chunk per keyword / test case.
    Pure single-RETURN getters are merged into `type=locator` chunks (split ~1500 chars).
    """
    _check_project(project)
    p = Path(path)
    source_file = rel_path or p.name
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    model = get_model(str(p))  # handles *** Test Cases *** and *** Keywords *** alike
    visitor = _RobotVisitor(lines)
    visitor.visit(model)

    base = {"source_file": source_file, "project": project}
    chunks: List[Dict] = []
    getters: List[Dict] = []

    for it in visitor.items:
        if merge_getters and it["is_getter"]:
            getters.append(it)
            continue
        text = it["text"]
        if len(text) > MAX_CHUNK_CHARS:
            text = text[:MAX_CHUNK_CHARS] + "\n... [truncated]"
        chunks.append({
            "text": f"{p.stem} / {it['name']}\n{text}",
            "heading": it["name"],
            "metadata": {
                **base, "name": it["name"], "type": it["kind"],
                "tags": _join(it["tags"]), "args": _join(it["args"]),
            },
        })

    if getters:
        body = "\n".join(g["text"] for g in getters)
        for i, part in enumerate(_split_text(body)):
            chunks.append({
                "text": f"{p.stem} - selectors:\n{part}",
                "heading": f"{p.stem} selectors",
                "metadata": {**base, "name": f"{p.stem} selectors", "type": "locator",
                             "tags": "", "args": "", "part": i},
            })
    return chunks


def chunk_python_file(
    path: str,
    project: str,
    rel_path: Optional[str] = None,
) -> List[Dict]:
    """
    One chunk per public module-level function and per public method of
    a public class (no leading underscore). RF treats these as keywords
    even without @keyword.
    """
    _check_project(project)
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    tree = ast.parse(source)
    base = {"source_file": rel_path or p.name, "project": project, "type": "python_keyword"}
    chunks: List[Dict] = []

    def add(fn, cls: str = ""):
        args = [a.arg for a in fn.args.args if a.arg not in ("self", "cls")]
        qual = f"{p.stem}.{cls + '.' if cls else ''}{fn.name}({', '.join(args)})"
        body = ast.get_source_segment(source, fn) or ""
        if len(body) > MAX_CHUNK_CHARS:
            body = body[:MAX_CHUNK_CHARS] + "\n... [truncated]"
        rf_name = fn.name.replace("_", " ").title()
        chunks.append({
            "text": f"{qual}\n{body}",
            "heading": f"{cls}.{fn.name}" if cls else fn.name,
            "metadata": {**base, "name": rf_name, "class": cls,
                         "args": _join(args), "tags": ""},
        })

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            add(node)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_"):
                    add(sub, node.name)
    return chunks


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Print RF/Python chunks (nothing is saved).")
    ap.add_argument("--project", required=True, choices=PROJECTS)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    for f in args.files:
        fn = chunk_python_file if f.endswith(".py") else chunk_robot_file
        for c in fn(f, project=args.project):
            print(f"[{c['metadata']['type']}] {c['heading']}  {c['metadata']}")
            print(c["text"][:300], "\n---")

