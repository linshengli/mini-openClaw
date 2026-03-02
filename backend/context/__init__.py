"""
Context management package for mini-openClaw.

Provides multi-layer context and RAG retrieval.
"""

from .layers import (
    ContextLayer,
    ContextConfig,
    ContextManager,
    ContextBuilder,
    get_context_manager,
    build_context_prompt,
)

from .rag import (
    KnowledgeDocument,
    RetrievedChunk,
    RAGRetriever,
    SimpleVectorStore,
    get_retriever,
    retrieve_context,
)

__all__ = [
    # Layers
    "ContextLayer",
    "ContextConfig",
    "ContextManager",
    "ContextBuilder",
    "get_context_manager",
    "build_context_prompt",
    # RAG
    "KnowledgeDocument",
    "RetrievedChunk",
    "RAGRetriever",
    "SimpleVectorStore",
    "get_retriever",
    "retrieve_context",
]
