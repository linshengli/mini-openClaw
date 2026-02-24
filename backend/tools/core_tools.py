from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

from langchain_community.tools import RequestsGetTool, ShellTool
from langchain_community.tools.file_management import ReadFileTool
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain_core.tools import tool
from langchain_experimental.tools import PythonREPLTool

from core.paths import KNOWLEDGE_DIR, STORAGE_DIR


def _resolve_in_root(root_dir: Path, relative_path: str) -> Path:
    candidate = (root_dir / relative_path).resolve()
    if not str(candidate).startswith(str(root_dir.resolve())):
        raise ValueError("Path is outside root_dir")
    return candidate


def build_core_tools(root_dir: Path) -> list[Any]:
    root_dir = root_dir.resolve()
    blocked_patterns = [
        r"rm\s+-rf\s+/",
        r":\(\)\s*\{\s*:\|:\s*&\s*\};:",
        r"mkfs",
        r"dd\s+if=",
    ]
    shell_tool = ShellTool()
    python_tool = PythonREPLTool()
    fetch_raw_tool = RequestsGetTool(
        name="fetch_url_raw",
        requests_wrapper=TextRequestsWrapper(headers={"User-Agent": "mini-openclaw/1.0"}),
        allow_dangerous_requests=True,
    )
    read_file_tool = ReadFileTool(root_dir=str(root_dir), name="read_file_raw")

    @tool("terminal")
    def terminal(command: str) -> str:
        """Execute a shell command in a sandboxed root directory using LangChain ShellTool."""
        for pattern in blocked_patterns:
            if re.search(pattern, command):
                return "Blocked dangerous command by policy."

        try:
            sandboxed = f"cd {shlex.quote(str(root_dir))} && {command}"
            return str(shell_tool.run({"commands": sandboxed}))
        except Exception as exc:  # noqa: BLE001
            return f"terminal error: {exc}"

    @tool("python_repl")
    def python_repl(code: str) -> str:
        """Run Python code in LangChain PythonREPLTool and return stdout."""
        try:
            output = python_tool.run(code)
            return str(output).strip() or "ok"
        except Exception as exc:  # noqa: BLE001
            return f"python_repl error: {exc}"

    @tool("fetch_url")
    def fetch_url(url: str) -> str:
        """Fetch URL with RequestsGetTool and return cleaned text."""
        try:
            html = str(fetch_raw_tool.run(url))
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
            except Exception:  # noqa: BLE001
                text = re.sub(r"<[^>]+>", " ", html)
                text = re.sub(r"\s+", " ", text).strip()
            return text[:12000]
        except Exception as exc:  # noqa: BLE001
            return f"fetch_url error: {exc}"

    @tool("read_file")
    def read_file(path: str) -> str:
        """Read a local file via LangChain ReadFileTool with project root sandbox."""
        try:
            normalized = path[2:] if path.startswith("./") else path
            target = _resolve_in_root(root_dir, normalized)
            if not target.exists():
                return "file not found"
            output = read_file_tool.run({"file_path": str(target.relative_to(root_dir))})
            return str(output)[:20000]
        except Exception as exc:  # noqa: BLE001
            return f"read_file error: {exc}"

    @tool("search_knowledge_base")
    def search_knowledge_base(query: str) -> str:
        """Hybrid search over local knowledge files."""
        try:
            if not KNOWLEDGE_DIR.exists():
                return "knowledge directory not found"

            # Prefer LlamaIndex when available; otherwise fallback to local scoring.
            try:
                from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, load_index_from_storage
                from llama_index.core.retrievers import BM25Retriever, VectorIndexRetriever
                from llama_index.core.schema import QueryBundle

                index_dir = STORAGE_DIR / "llamaindex"
                if index_dir.exists():
                    storage_context = StorageContext.from_defaults(persist_dir=str(index_dir))
                    index = load_index_from_storage(storage_context)
                else:
                    docs = SimpleDirectoryReader(str(KNOWLEDGE_DIR), recursive=True).load_data()
                    index = VectorStoreIndex.from_documents(docs)
                    index.storage_context.persist(persist_dir=str(index_dir))

                vector = VectorIndexRetriever(index=index, similarity_top_k=5)
                bm25 = BM25Retriever.from_defaults(nodes=index.docstore.docs.values(), similarity_top_k=5)
                query_bundle = QueryBundle(query_str=query)
                nodes = vector.retrieve(query_bundle) + bm25.retrieve(query_bundle)

                seen: set[str] = set()
                chunks: list[str] = []
                for node in nodes:
                    text = node.get_content().strip()
                    if not text:
                        continue
                    key = text[:120]
                    if key in seen:
                        continue
                    seen.add(key)
                    chunks.append(text[:1000])
                    if len(chunks) >= 5:
                        break
                return "\n\n---\n\n".join(chunks) if chunks else "no hits"
            except Exception:
                pass

            query_terms = [t.lower() for t in query.split() if t.strip()]
            hits: list[tuple[int, str, str]] = []
            for file in KNOWLEDGE_DIR.rglob("*"):
                if file.is_dir():
                    continue
                if file.suffix.lower() not in {".md", ".txt"}:
                    continue
                content = file.read_text(encoding="utf-8", errors="ignore")
                score = sum(content.lower().count(term) for term in query_terms)
                if score > 0:
                    hits.append((score, str(file.relative_to(root_dir)), content[:1000]))
            hits.sort(key=lambda x: x[0], reverse=True)
            if not hits:
                return "no hits"
            return "\n\n".join([f"[{path}] score={score}\n{snippet}" for score, path, snippet in hits[:5]])
        except Exception as exc:  # noqa: BLE001
            return f"search_knowledge_base error: {exc}"

    return [terminal, python_repl, fetch_url, read_file, search_knowledge_base]
