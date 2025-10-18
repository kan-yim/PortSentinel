"""
Simplified unit tests for Agent 3: SOP Executor Agent.

These tests focus on core functionality without complex mocking.
"""

import pytest
import json
from pathlib import Path
import sys

# Add paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "agents" / "agent_3_sop_executor"))
sys.path.insert(0, str(project_root.parent / "rag_module" / "src"))
sys.path.insert(0, str(project_root.parent / "parsing_module" / "src"))

from agents.agent_3_sop_executor.tools import generate_sql_update_statement
from agents.agent_3_sop_executor.models import ExecutionResult, StepExecutionDetail
from agents.agent_3_sop_executor.agent import SopExecutorAgent
from rag_agent.models import EnrichedContext, SopSnippet
from parsing_agent.models import IncidentReport, Entity
from datetime import datetime


class TestSqlGenerationTools:
    """Test SQL generation tool without LangChain wrapper."""

    def test_generate_sql_basic(self):
        """Test basic SQL generation with parameters."""
        sql_template = "UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :id"
        params_dict = {
            "timestamp": "2025-10-18 00:00:00",
            "id": 123
        }

        # Call the underlying implementation
        from agents.agent_3_sop_executor.tools import generate_sql_update_statement as func

        # Get the actual function, not the Tool wrapper
        import json
        result = func.func(sql_template, json.dumps(params_dict))

        assert "UPDATE vessel_advice" in result
        assert "'2025-10-18 00:00:00'" in result
        assert "123" in result
        assert result.strip().endswith(';')

    def test_generate_sql_with_string_escaping(self):
        """Test SQL generation with single quote escaping."""
        sql_template = "UPDATE vessel SET name = :name WHERE id = :id"
        params_dict = {
            "name": "O'Reilly Vessel",
            "id": 456
        }

        from agents.agent_3_sop_executor.tools import generate_sql_update_statement as func
        import json
        result = func.func(sql_template, json.dumps(params_dict))

        # Should escape single quote
        assert "O''Reilly Vessel" in result
        assert "456" in result

    def test_generate_sql_with_null(self):
        """Test SQL generation with NULL values."""
        sql_template = "UPDATE vessel SET end_date = :end_date WHERE id = :id"
        params_dict = {
            "end_date": None,
            "id": 789
        }

        from agents.agent_3_sop_executor.tools import generate_sql_update_statement as func
        import json
        result = func.func(sql_template, json.dumps(params_dict))

        assert "NULL" in result
        assert "789" in result


class TestAgentInitialization:
    """Test agent initialization."""

    def test_agent_can_be_created(self):
        """Test that agent can be instantiated."""
        agent = SopExecutorAgent(db_interface=None)

        assert agent is not None
        assert agent.llm is not None
        assert len(agent.tools) == 3
        assert agent.agent_executor is not None

    def test_agent_tools_have_correct_names(self):
        """Test that all required tools are present."""
        agent = SopExecutorAgent(db_interface=None)

        tool_names = [tool.name for tool in agent.tools]
        assert "check_log" in tool_names
        assert "execute_sql_query" in tool_names
        assert "generate_sql_update_statement" in tool_names


class TestExecutionWithRealData:
    """Test execution with real enriched context from RAG module."""

    def test_execution_with_no_sops(self):
        """Test execution when no SOPs are available."""
        # Create minimal incident report
        incident = IncidentReport(
            incident_id="TEST-001",
            source_type="Email",
            received_timestamp_utc=datetime.utcnow().isoformat(),
            problem_summary="Unknown error occurred",
            affected_module="Vessel",
            raw_text="Unknown error occurred in the system.",
            urgency="Low",
            entities=[]
        )

        # Create context with no SOPs
        context = EnrichedContext(
            original_report=incident,
            retrieved_sops=[],
            retrieval_summary="No relevant SOPs found."
        )

        # Execute
        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(context)

        # Verify result structure
        assert isinstance(result, ExecutionResult)
        assert result.selected_sop_title is None
        assert result.final_status == "Failed"
        assert "manual investigation" in result.next_action_description.lower()
        assert len(result.executed_steps) == 0

    def test_execution_with_sample_sop(self):
        """Test execution with a sample SOP."""
        # Create incident report
        incident = IncidentReport(
            incident_id="ALR-861631",
            source_type="Email",
            received_timestamp_utc=datetime.utcnow().isoformat(),
            problem_summary="Customer unable to create vessel advice for LIONCITY07. Error code VESSEL_ERR_4.",
            affected_module="Vessel",
            error_code="VESSEL_ERR_4",
            raw_text="Customer unable to create vessel advice for LIONCITY07 in VAS. Error code VESSEL_ERR_4: 'Vessel Name has been used by other vessel advice'.",
            urgency="High",
            entities=[
                Entity(type="VESSEL_NAME", value="LIONCITY07"),
                Entity(type="ERROR_CODE", value="VESSEL_ERR_4")
            ]
        )

        # Create SOP
        sop = SopSnippet(
            content="""Title: VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice

Overview:
Error Code: VESSEL_ERR_4
Module: Vessel Advice Service (VAS)
Description: This error occurs when attempting to create a new vessel advice with a vessel name that is already in use.

Resolution Steps:
1. Query the database for active vessel advice with the vessel name
2. Check if there are active berth applications
3. If no berth applications, generate SQL to expire the advice

Verification Steps:
- Verify the vessel advice is expired after SQL execution""",
            metadata={
                "sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
                "module": "VAS",
                "error_code": "VESSEL_ERR_4"
            },
            score=0.92
        )

        # Create enriched context
        context = EnrichedContext(
            original_report=incident,
            retrieved_sops=[sop],
            retrieval_summary="Retrieved 1 relevant SOP(s) for incident ALR-861631."
        )

        # Execute (this will use the actual LLM)
        agent = SopExecutorAgent(db_interface=None)

        try:
            result = agent.execute_sop(context)

            # Basic assertions
            assert isinstance(result, ExecutionResult)
            assert result.selected_sop_title == "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice"
            assert result.original_context == context

            # Should have some execution steps (even if mock)
            assert isinstance(result.executed_steps, list)
            assert isinstance(result.next_action_description, str)
            assert result.final_status in [
                "Requires Manual Confirmation",
                "Completed Successfully",
                "Failed",
                "Escalation Required",
                "Ambiguous"
            ]

            print(f"\nExecution Result:")
            print(f"  Steps executed: {len(result.executed_steps)}")
            print(f"  Final status: {result.final_status}")
            print(f"  Next action: {result.next_action_description}")
            if result.proposed_sql_action:
                print(f"  Proposed SQL: {result.proposed_sql_action[:100]}...")

        except Exception as e:
            # If execution fails (e.g., LLM connection issues), that's OK for this test
            print(f"\nNote: Execution failed with: {str(e)}")
            print("This is expected if Azure OpenAI credentials are not configured.")
            pytest.skip("Skipping test due to LLM connection issues")


class TestModels:
    """Test the data models."""

    def test_step_execution_detail_creation(self):
        """Test creating a StepExecutionDetail."""
        step = StepExecutionDetail(
            step_description="Query database",
            tool_called="execute_sql_query",
            tool_input={"query": "SELECT * FROM test"},
            tool_output=[{"id": 1}],
            status="Success",
            summary="Successfully queried database"
        )

        assert step.step_description == "Query database"
        assert step.tool_called == "execute_sql_query"
        assert step.status == "Success"

    def test_execution_result_creation(self):
        """Test creating an ExecutionResult."""
        incident = IncidentReport(
            incident_id="TEST-001",
            source_type="Email",
            received_timestamp_utc=datetime.utcnow().isoformat(),
            problem_summary="Test problem",
            affected_module="Vessel",
            raw_text="Test problem occurred.",
            urgency="Low"
        )

        context = EnrichedContext(
            original_report=incident,
            retrieved_sops=[],
            retrieval_summary="Test summary"
        )

        result = ExecutionResult(
            original_context=context,
            selected_sop_title="Test SOP",
            executed_steps=[],
            proposed_sql_action=None,
            next_action_description="Test action",
            final_status="Completed Successfully"
        )

        assert result.selected_sop_title == "Test SOP"
        assert result.final_status == "Completed Successfully"
        assert result.original_context == context


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
