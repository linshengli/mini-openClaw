"""
RAG (Retrieval-Augmented Generation) context retrieval.

Provides semantic search and retrieval of context from multiple sources.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from core.paths import KNOWLEDGE_DIR, STORAGE_DIR


@dataclass
class KnowledgeDocument:
    """A document in the knowledge base"""
    id: str
    title: str
    content: str
    source: str  # file path or URL
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class RetrievedChunk:
    """A retrieved chunk of context"""
    doc_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleVectorStore:
    """
    Simple in-memory vector store for document retrieval.

    In production, this should be replaced with a proper vector database
    like Chroma, Pinecone, or Qdrant.
    """

    def __init__(self):
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._chunks: Dict[str, Dict[str, str]] = {}  # doc_id -> {chunk_id: content}
        self._index_dirty = True
        self._builtins_embedded = False

    def add_document(self, doc: KnowledgeDocument, chunk_size: int = 500) -> None:
        """Add a document to the store"""
        self._documents[doc.id] = doc

        # Chunk the document
        chunks = self._chunk_text(doc.content, chunk_size)
        self._chunks[doc.id] = chunks
        self._index_dirty = True

    def _chunk_text(self, text: str, chunk_size: int) -> Dict[str, str]:
        """Split text into overlapping chunks"""
        chunks = {}
        words = text.split()

        for i in range(0, len(words), chunk_size // 2):  # 50% overlap
            chunk_words = words[i:i + chunk_size]
            chunk_id = hashlib.md5(" ".join(chunk_words).encode()).hexdigest()[:8]
            chunks[chunk_id] = " ".join(chunk_words)

        return chunks

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.1
    ) -> List[RetrievedChunk]:
        """
        Search for relevant chunks.

        Uses simple keyword matching as a fallback.
        For proper semantic search, integrate with an embedding model.
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for doc_id, chunks in self._chunks.items():
            doc = self._documents.get(doc_id)
            if not doc:
                continue

            for chunk_id, chunk_content in chunks.items():
                # Simple keyword overlap score
                chunk_lower = chunk_content.lower()
                chunk_words = set(chunk_lower.split())

                # Calculate overlap
                overlap = query_words & chunk_words
                if not overlap:
                    continue

                score = len(overlap) / max(len(query_words), len(chunk_words))

                if score >= threshold:
                    results.append(RetrievedChunk(
                        doc_id=doc_id,
                        chunk_id=chunk_id,
                        content=chunk_content,
                        score=score,
                        metadata={
                            "title": doc.title,
                            "source": doc.source,
                            "tags": doc.tags
                        }
                    ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get a document by ID"""
        return self._documents.get(doc_id)

    def clear(self) -> None:
        """Clear all documents"""
        self._documents.clear()
        self._chunks.clear()
        self._index_dirty = True


class RAGRetriever:
    """
    RAG retriever that combines multiple retrieval strategies.
    """

    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = storage_dir
        self.vector_store = SimpleVectorStore()
        self._index_file = storage_dir / "rag_index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load index from disk if available"""
        if self._index_file.exists():
            try:
                data = json.loads(self._index_file.read_text())
                # Rebuild documents from index
                for doc_data in data.get("documents", []):
                    doc = KnowledgeDocument(**doc_data)
                    self.vector_store.add_document(doc)
            except Exception:
                pass  # Start fresh if index is corrupted

    def _save_index(self) -> None:
        """Save index to disk"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "source": doc.source,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "metadata": doc.metadata,
                    "tags": doc.tags
                }
                for doc in self.vector_store._documents.values()
            ],
            "last_updated": datetime.now().isoformat()
        }
        self._index_file.write_text(json.dumps(data, indent=2))

    def ingest_file(self, file_path: Path, tags: Optional[List[str]] = None) -> KnowledgeDocument:
        """Ingest a file into the knowledge base"""
        content = file_path.read_text(encoding="utf-8")
        doc_id = hashlib.md5(str(file_path).encode()).hexdigest()

        doc = KnowledgeDocument(
            id=doc_id,
            title=file_path.stem,
            content=content,
            source=str(file_path),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=tags or [],
            metadata={"type": "file", "path": str(file_path)}
        )

        self.vector_store.add_document(doc)
        self._save_index()
        return doc

    def ingest_directory(
        self,
        dir_path: Path,
        pattern: str = "*.md",
        tags: Optional[List[str]] = None
    ) -> List[KnowledgeDocument]:
        """Ingest all matching files in a directory"""
        docs = []
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                doc = self.ingest_file(file_path, tags)
                docs.append(doc)
        return docs

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
        filter_tags: Optional[List[str]] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant context for a query.

        Args:
            query: The search query
            top_k: Number of results to return
            threshold: Minimum similarity score
            filter_tags: Optional tags to filter by
        """
        results = self.vector_store.search(query, top_k, threshold)

        # Filter by tags if specified
        if filter_tags:
            filtered = []
            for chunk in results:
                chunk_tags = chunk.metadata.get("tags", [])
                if any(tag in chunk_tags for tag in filter_tags):
                    filtered.append(chunk)
            results = filtered

        return results

    def build_context(
        self,
        query: str,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Build context string for RAG-augmented generation.

        Combines retrieved chunks into a single context string.
        """
        chunks = self.retrieve(query, **kwargs)

        if not chunks:
            return ""

        context_parts = []
        current_tokens = 0

        # Rough token estimation (4 chars ≈ 1 token)
        max_chars = max_tokens * 4

        for chunk in chunks:
            chunk_text = f"[{chunk.metadata.get('title', 'Unknown')}]\n{chunk.content}"
            if current_tokens + len(chunk_text) > max_chars:
                break

            context_parts.append(chunk_text)
            current_tokens += len(chunk_text)

        if not context_parts:
            return ""

        return "Relevant Context:\n\n" + "\n\n---\n\n".join(context_parts)


# Default retriever instance
_default_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """Get the default RAG retriever instance"""
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = RAGRetriever()
    return _default_retriever


def retrieve_context(query: str, top_k: int = 5) -> str:
    """
    Retrieve context for a query.

    Main entry point for RAG-augmented generation.
    """
    retriever = get_retriever()
    return retriever.build_context(query, top_k=top_k)
