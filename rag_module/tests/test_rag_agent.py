"""
Unit tests for RagAgent - RAG-based SOP retrieval.

All tests use mocked vector store - no actual API calls required.
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add paths for imports
rag_module_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(rag_module_path))
parsing_module_path = Path(__file__).parent.parent.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))

from parsing_agent.models import IncidentReport, Entity
from rag_agent.validator import RagAgent
from rag_agent.models import EnrichedContext, SopSnippet
from langchain_core.documents import Document


@pytest.fixture
def mock_vector_store():
    """Fixture for mocked vector store interface."""
    mock = Mock()
    mock.search_with_scores = Mock()
    return mock


@pytest.fixture
def rag_agent(mock_vector_store):
    """Fixture for RagAgent with mocked vector store."""
    return RagAgent(vector_store_interface=mock_vector_store)


@pytest.fixture
def sample_incident_report():
    """Fixture for a sample incident report."""
    return IncidentReport(
        incident_id="ALR-861631",
        source_type="Email",
        received_timestamp_utc="2025-10-18T10:00:00Z",
        urgency="High",
        reported_by="John Doe",
        reported_at="2025-10-18T10:00:00",
        problem_summary="Unable to create vessel advice due to duplicate system vessel name",
        affected_module="Vessel",
        error_code="VESSEL_ERR_4",
        entities=[
            Entity(type="vessel_name", value="LIONCITY07"),
            Entity(type="error_code", value="VESSEL_ERR_4")
        ],
        steps_already_taken=["Checked vessel advice table"],
        additional_notes="Customer needs urgent resolution",
        raw_text="Subject: Unable to create vessel advice\n\nError VESSEL_ERR_4..."
    )


def test_build_search_query(rag_agent, sample_incident_report):
    """Test that search query is correctly built from incident report."""
    query = rag_agent._build_search_query(sample_incident_report)

    # Check that query contains key components
    assert "VESSEL_ERR_4" in query
    assert "duplicate system vessel name" in query
    assert "Vessel" in query
    assert "LIONCITY07" in query


def test_retrieve_sops_success(rag_agent, mock_vector_store, sample_incident_report):
    """Test successful SOP retrieval from vector store."""
    # Mock vector store response
    mock_doc1 = Document(
        page_content="VAS: VESSEL_ERR_4 - System Vessel Name has been used by other vessel advice...",
        metadata={
            "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
            "module": "Vessel",
            "source": "Knowledge Base.docx",
            "chunk_type": "overview"
        }
    )

    mock_doc2 = Document(
        page_content="Resolution steps: 1. Check active vessel advice...",
        metadata={
            "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
            "module": "Vessel",
            "source": "Knowledge Base.docx",
            "chunk_type": "resolution"
        }
    )

    mock_vector_store.search_with_scores.return_value = [
        (mock_doc1, 0.92),
        (mock_doc2, 0.85)
    ]

    # Test retrieval
    sops = rag_agent._retrieve_sops(sample_incident_report, k=3)

    # Verify results
    assert len(sops) == 2
    assert isinstance(sops[0], SopSnippet)
    assert sops[0].score == 0.92
    assert "VESSEL_ERR_4" in sops[0].content
    assert sops[0].metadata["module"] == "Vessel"
    assert sops[1].score == 0.85


def test_retrieve_sops_empty_result(rag_agent, mock_vector_store, sample_incident_report):
    """Test handling of empty vector store results."""
    mock_vector_store.search_with_scores.return_value = []

    sops = rag_agent._retrieve_sops(sample_incident_report, k=3)

    assert sops == []


def test_retrieve_sops_error_handling(rag_agent, mock_vector_store, sample_incident_report):
    """Test that SOP retrieval failures are gracefully handled."""
    # Mock vector store to raise exception
    mock_vector_store.search_with_scores.side_effect = Exception("Vector store connection failed")

    # Should return empty list instead of raising
    sops = rag_agent._retrieve_sops(sample_incident_report, k=3)

    assert sops == []


def test_generate_summary_with_results(rag_agent, sample_incident_report):
    """Test summary generation when SOPs are found."""
    mock_sops = [
        SopSnippet(
            content="VAS: VESSEL_ERR_4 content...",
            metadata={"sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name"},
            score=0.92
        ),
        SopSnippet(
            content="Another SOP content...",
            metadata={"sop_title": "VAS: General Troubleshooting"},
            score=0.78
        )
    ]

    summary = rag_agent._generate_summary(sample_incident_report, mock_sops)

    assert "ALR-861631" in summary
    assert "2" in summary  # Number of SOPs
    assert "VAS: VESSEL_ERR_4" in summary
    assert "0.92" in summary  # Score
    assert "Vessel" in summary  # Module
    assert "VESSEL_ERR_4" in summary  # Error code


def test_generate_summary_no_results(rag_agent, sample_incident_report):
    """Test summary generation when no SOPs are found."""
    summary = rag_agent._generate_summary(sample_incident_report, [])

    assert "未找到" in summary
    assert "ALR-861631" in summary
    assert "人工审查" in summary


def test_retrieve_full_workflow(rag_agent, mock_vector_store, sample_incident_report):
    """Test the complete retrieve workflow."""
    # Mock vector store response
    mock_doc = Document(
        page_content="VAS: VESSEL_ERR_4 - Complete troubleshooting guide...",
        metadata={
            "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
            "module": "Vessel",
            "chunk_type": "overview"
        }
    )

    mock_vector_store.search_with_scores.return_value = [(mock_doc, 0.95)]

    # Execute retrieval
    result = rag_agent.retrieve(sample_incident_report, k=3)

    # Verify EnrichedContext
    assert isinstance(result, EnrichedContext)
    assert result.original_report == sample_incident_report
    assert len(result.retrieved_sops) == 1
    assert result.retrieved_sops[0].score == 0.95
    assert "VESSEL_ERR_4" in result.retrieval_summary
    assert "0.95" in result.retrieval_summary


def test_retrieve_with_custom_k(rag_agent, mock_vector_store, sample_incident_report):
    """Test retrieval with custom k parameter."""
    mock_docs = [
        (Document(page_content=f"SOP {i}", metadata={"sop_title": f"SOP {i}"}), 0.9 - i*0.1)
        for i in range(5)
    ]

    mock_vector_store.search_with_scores.return_value = mock_docs

    # Request k=5
    result = rag_agent.retrieve(sample_incident_report, k=5)

    assert len(result.retrieved_sops) == 5
    # Verify scores are in descending order
    assert result.retrieved_sops[0].score == 0.9
    assert result.retrieved_sops[4].score == 0.5


def test_retrieve_different_incident_types(rag_agent, mock_vector_store):
    """Test retrieval for different incident types."""
    # Test 1: Container incident
    container_incident = IncidentReport(
        incident_id="CONT-001",
        source_type="Email",
        received_timestamp_utc="2025-10-18T11:00:00Z",
        urgency="Medium",
        reported_by="Jane Smith",
        reported_at="2025-10-18T11:00:00",
        problem_summary="Duplicate container number in system",
        affected_module="Container",
        error_code=None,
        entities=[
            Entity(type="container_number", value="CMAU0000020")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Subject: Duplicate container\n\nContainer CMAU0000020 appears twice..."
    )

    mock_doc = Document(
        page_content="Container duplicate resolution...",
        metadata={"sop_title": "Container: Duplicate Records"}
    )

    mock_vector_store.search_with_scores.return_value = [(mock_doc, 0.88)]

    result = rag_agent.retrieve(container_incident, k=3)

    assert "CONT-001" in result.retrieval_summary
    assert "Container" in rag_agent._build_search_query(container_incident)

    # Test 2: EDI incident
    edi_incident = IncidentReport(
        incident_id="EDI-002",
        source_type="SMS",
        received_timestamp_utc="2025-10-18T12:00:00Z",
        urgency="High",
        reported_by="System Monitor",
        reported_at="2025-10-18T12:00:00",
        problem_summary="EDI message stuck in ERROR status",
        affected_module="EDI/API",
        error_code=None,
        entities=[
            Entity(type="correlation_id", value="EDI-MSG-12345")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Alert: EDI message EDI-MSG-12345 stuck in ERROR status..."
    )

    mock_doc_edi = Document(
        page_content="EDI timeout troubleshooting...",
        metadata={"sop_title": "EDI: Message Timeout Resolution"}
    )

    mock_vector_store.search_with_scores.return_value = [(mock_doc_edi, 0.91)]

    result = rag_agent.retrieve(edi_incident, k=3)

    assert "EDI-002" in result.retrieval_summary
    assert "EDI/API" in rag_agent._build_search_query(edi_incident)


def test_retrieval_with_no_entities(rag_agent, mock_vector_store):
    """Test retrieval when incident has no entities."""
    minimal_incident = IncidentReport(
        incident_id="MIN-001",
        source_type="Email",
        received_timestamp_utc="2025-10-18T13:00:00Z",
        urgency="Low",
        reported_by="User",
        reported_at="2025-10-18T13:00:00",
        problem_summary="General system slowness",
        affected_module=None,
        error_code=None,
        entities=[],
        steps_already_taken=[],
        additional_notes="",
        raw_text="System is running slow today..."
    )

    mock_doc = Document(
        page_content="General performance troubleshooting...",
        metadata={"sop_title": "System Performance"}
    )

    mock_vector_store.search_with_scores.return_value = [(mock_doc, 0.65)]

    result = rag_agent.retrieve(minimal_incident, k=3)

    # Should still work with just problem summary
    query = rag_agent._build_search_query(minimal_incident)
    assert "General system slowness" in query
    assert len(result.retrieved_sops) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
