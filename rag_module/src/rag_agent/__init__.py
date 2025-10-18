"""
RAG Agent for PORTNET® Incident Context Enrichment.

This package provides RAG-based SOP retrieval functionality,
using semantic search to find relevant SOPs for incident resolution.
"""

from .models import EnrichedContext, SopSnippet
from .validator import RagAgent

__version__ = "1.0.0"

__all__ = [
    "EnrichedContext",
    "SopSnippet",
    "RagAgent",
]
