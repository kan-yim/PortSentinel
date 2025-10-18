"""
RAG Agent - SOP retrieval for incident context enrichment.

This module implements the core logic for retrieving relevant SOPs
from the knowledge base using semantic search (RAG only).
"""

from typing import List
import sys
from pathlib import Path

# Add paths for imports
parsing_module_path = Path(__file__).parent.parent.parent.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))

from parsing_agent.models import IncidentReport, Entity
from rag_agent.models import EnrichedContext, SopSnippet
from data_sources.vector_store_interface import VectorStoreInterface


class RagAgent:
    """
    Agent 2: RAG-based SOP Retrieval

    Enriches incident reports with relevant SOP snippets from knowledge base
    using semantic search via vector embeddings.
    """

    def __init__(self, vector_store_interface: VectorStoreInterface):
        """
        Initialize the RAG Agent.

        Args:
            vector_store_interface: Vector store interface instance for knowledge base
        """
        self.vector_store = vector_store_interface

    def _build_search_query(self, report: IncidentReport) -> str:
        """
        Construct a search query from the incident report.

        Args:
            report: Parsed incident report

        Returns:
            Search query string optimized for RAG retrieval
        """
        query_parts = []

        # Add error code if present (high priority)
        if report.error_code:
            query_parts.append(f"Error code: {report.error_code}")

        # Add problem summary
        query_parts.append(report.problem_summary)

        # Add affected module if present
        if report.affected_module:
            query_parts.append(f"Module: {report.affected_module}")

        # Add key entity values (containers, vessels, etc.)
        for entity in report.entities[:5]:  # Limit to top 5 entities
            if entity.type in ["container_number", "vessel_name", "error_code", "message_type"]:
                query_parts.append(f"{entity.type}: {entity.value}")

        return " | ".join(query_parts)

    def _retrieve_sops(self, report: IncidentReport, k: int = 3) -> List[SopSnippet]:
        """
        Retrieve relevant SOP snippets from knowledge base.

        Args:
            report: Incident report
            k: Number of top results to retrieve

        Returns:
            List of SopSnippet objects
        """
        query = self._build_search_query(report)

        try:
            docs_and_scores = self.vector_store.search_with_scores(query=query, k=k)

            sop_snippets = []
            for doc, score in docs_and_scores:
                snippet = SopSnippet(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=float(score)
                )
                sop_snippets.append(snippet)

            return sop_snippets

        except Exception as e:
            # Log error but continue with empty SOPs
            print(f"Warning: SOP retrieval failed: {e}")
            return []

    def _generate_summary(self, report: IncidentReport, sops: List[SopSnippet]) -> str:
        """
        Generate a human-readable summary of retrieval results.

        Args:
            report: Original incident report
            sops: Retrieved SOP snippets

        Returns:
            Summary string (in English)
        """
        if not sops:
            return f"No relevant SOPs found for incident {report.incident_id}. Manual review recommended."

        # Get top SOP details
        top_sop = sops[0]
        top_title = top_sop.metadata.get("sop_title", "Unknown")
        top_score = top_sop.score if top_sop.score else 0.0

        summary_parts = [
            f"Retrieved {len(sops)} relevant SOP(s) for incident {report.incident_id}.",
            f"Top match: {top_title} (similarity score: {top_score:.2f})"
        ]

        # Add module information if available
        if report.affected_module:
            summary_parts.append(f"Affected module: {report.affected_module}")

        # Add error code if present
        if report.error_code:
            summary_parts.append(f"Error code: {report.error_code}")

        return " ".join(summary_parts)

    def retrieve(self, report: IncidentReport, k: int = 3) -> EnrichedContext:
        """
        Main retrieval method - enriches incident report with relevant SOPs.

        Args:
            report: Parsed incident report from Agent 1
            k: Number of top SOPs to retrieve (default: 3)

        Returns:
            EnrichedContext with retrieved SOPs and summary
        """
        # Retrieve relevant SOPs via RAG
        retrieved_sops = self._retrieve_sops(report, k=k)

        # Generate summary
        retrieval_summary = self._generate_summary(report, retrieved_sops)

        # Build and return EnrichedContext
        enriched_context = EnrichedContext(
            original_report=report,
            retrieved_sops=retrieved_sops,
            retrieval_summary=retrieval_summary
        )

        return enriched_context
