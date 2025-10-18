"""
Pydantic models for RAG-based SOP retrieval.

This module defines data structures for storing retrieved SOP snippets
and the enriched context output (RAG only, no database validation).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Import IncidentReport from parsing_agent
import sys
from pathlib import Path
# Add parsing_module to path to import IncidentReport
parsing_module_path = Path(__file__).parent.parent.parent.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))

from parsing_agent.models import IncidentReport


class SopSnippet(BaseModel):
    """
    Represents a retrieved SOP (Standard Operating Procedure) snippet from the knowledge base.

    Attributes:
        content: The actual text content of the retrieved SOP chunk
        metadata: Associated metadata like sop_title, module, source, page number, etc.
        score: Relevance/similarity score from the vector store retrieval
    """
    content: str = Field(..., description="Text content of the SOP snippet")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with this snippet (e.g., sop_title, module, source)"
    )
    score: Optional[float] = Field(
        None,
        description="Relevance score from vector similarity search (higher is more relevant)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "VAS: VESSEL_ERR_4 - System Vessel Name has been used by other vessel advice...",
                "metadata": {
                    "sop_title": "VAS: VESSEL_ERR_4",
                    "module": "Vessel",
                    "source": "Knowledge Base.docx"
                },
                "score": 0.89
            }
        }


class EnrichedContext(BaseModel):
    """
    Main output model containing the enriched context for incident resolution.

    Combines the original incident report with retrieved SOP snippets from knowledge base.
    """
    original_report: IncidentReport = Field(
        ...,
        description="The original parsed incident report from Agent 1"
    )

    retrieved_sops: List[SopSnippet] = Field(
        default_factory=list,
        description="Relevant SOP snippets retrieved from knowledge base via RAG"
    )

    retrieval_summary: str = Field(
        ...,
        description="Human-readable summary of retrieved SOPs and relevance"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_report": {
                    "incident_id": "ALR-861631",
                    "source_type": "Email",
                    "urgency": "High",
                    "problem_summary": "Unable to create vessel advice due to duplicate system vessel name"
                },
                "retrieved_sops": [
                    {
                        "content": "VAS: VESSEL_ERR_4 troubleshooting steps...",
                        "metadata": {"sop_title": "VAS: VESSEL_ERR_4", "module": "Vessel"},
                        "score": 0.92
                    }
                ],
                "retrieval_summary": "Retrieved 3 relevant SOPs for vessel advice error. Top match: VAS: VESSEL_ERR_4 (score: 0.92)"
            }
        }
