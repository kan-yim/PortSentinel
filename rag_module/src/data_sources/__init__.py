"""
Data sources for RAG agent.

Provides interface to Chroma vector store for knowledge base retrieval.
"""

from .vector_store_interface import VectorStoreInterface

__all__ = [
    "VectorStoreInterface",
]
