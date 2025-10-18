"""
Unit tests for Agent 3: SOP Executor Agent.

Tests the execution of SOPs step-by-step, including:
- Tool calling (check_log, execute_sql_query, generate_sql_update_statement)
- Decision logic based on tool results
- Correct execution result structure
- Safety checks (SQL generation but not execution)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import sys
from pathlib import Path

# Add paths for imports
project_root = Path(__file__).parent.parent.parent
agent_path = project_root / "agents" / "agent_3_sop_executor"
rag_module_path = project_root.parent / "rag_module" / "src"

sys.path.insert(0, str(agent_path))
sys.path.insert(0, str(rag_module_path))

# Import from agent_3_sop_executor package
from agents.agent_3_sop_executor.models import ExecutionResult, StepExecutionDetail
from agents.agent_3_sop_executor.agent import SopExecutorAgent
from rag_agent.models import EnrichedContext, SopSnippet

# Import from parsing_module
parsing_module_path = project_root.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))
from parsing_agent.models import IncidentReport, Entity


# ===== Test Fixtures =====

@pytest.fixture
def mock_llm():
    """Mock Azure OpenAI LLM for testing."""
    with patch('agents.agent_3_sop_executor.agent.AzureChatOpenAI') as mock:
        yield mock


@pytest.fixture
def sample_vessel_err_4_incident():
    """Sample incident report for VESSEL_ERR_4 scenario."""
    return IncidentReport(
        incident_id="ALR-861631",
        problem_summary="Customer unable to create vessel advice for LIONCITY07 in Vessel Advice Service (VAS). Error code VESSEL_ERR_4: 'Vessel Name has been used by other vessel advice'.",
        affected_module="Vessel Advice Service (VAS)",
        error_code="VESSEL_ERR_4",
        urgency="High",
        entities=[
            Entity(type="VESSEL_NAME", value="LIONCITY07", confidence=0.95),
            Entity(type="ERROR_CODE", value="VESSEL_ERR_4", confidence=1.0),
            Entity(type="MODULE", value="VAS", confidence=0.9)
        ]
    )


@pytest.fixture
def sample_vessel_err_4_sop():
    """Sample SOP for VESSEL_ERR_4 scenario."""
    sop_content = """Title: VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice

Overview:
Error Code: VESSEL_ERR_4
Module: Vessel Advice Service (VAS)
Description: This error occurs when attempting to create a new vessel advice with a vessel name that is already in use by another active vessel advice record.

Resolution Steps:
1. Query the database to check for active vessel advice with the given system_vessel_name:
   SELECT vessel_advice_no, system_vessel_name, effective_start_datetime, effective_end_datetime
   FROM vessel_advice
   WHERE system_vessel_name = :system_vessel_name
   AND effective_end_datetime IS NULL;

2. Decision Logic:
   - If no active vessel advice found: Escalate to L3 (unusual case)
   - If active vessel advice found:
     a. Check if there are active berth applications linked to this vessel advice:
        SELECT * FROM berth_application
        WHERE vessel_advice_no = :active_vessel_advice_no
        AND status = 'Active';

     b. Decision Logic:
        - If no active berth applications: Safe to expire the vessel advice
          Generate SQL: UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no;
        - If active berth applications exist: Cannot expire automatically, escalate to L3

Preconditions:
- Database connection to vessel_advice and berth_application tables
- Valid system_vessel_name from incident report

Verification Steps:
- After executing the UPDATE, verify effective_end_datetime is set
- Retry creating the new vessel advice
- Confirm customer can now create vessel advice successfully"""

    return SopSnippet(
        content=sop_content,
        metadata={
            "sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
            "module": "VAS",
            "error_code": "VESSEL_ERR_4",
            "chunk_type": "resolution"
        },
        score=0.92
    )


@pytest.fixture
def sample_vessel_err_4_context(sample_vessel_err_4_incident, sample_vessel_err_4_sop):
    """Sample enriched context for VESSEL_ERR_4 scenario."""
    return EnrichedContext(
        original_report=sample_vessel_err_4_incident,
        retrieved_sops=[sample_vessel_err_4_sop],
        retrieval_summary="Retrieved 1 relevant SOP(s) for incident ALR-861631. Top match: VAS: VESSEL_ERR_4 (similarity score: 0.92)"
    )


@pytest.fixture
def sample_edi_timeout_incident():
    """Sample incident report for EDI timeout scenario."""
    return IncidentReport(
        incident_id="EDI-001",
        problem_summary="EDI message processing timeout. EDIFACT message from trading partner TP-MAERSK failed to process within 30 seconds.",
        affected_module="EDI Integration Service",
        error_code="EDI_TIMEOUT",
        urgency="Medium",
        entities=[
            Entity(type="PARTNER_ID", value="TP-MAERSK", confidence=0.9),
            Entity(type="ERROR_CODE", value="EDI_TIMEOUT", confidence=1.0),
            Entity(type="MODULE", value="EDI Integration Service", confidence=0.95)
        ]
    )


@pytest.fixture
def sample_edi_timeout_sop():
    """Sample SOP for EDI timeout scenario."""
    sop_content = """Title: EDI: EDI Message Processing Timeout

Overview:
Error Code: EDI_TIMEOUT
Module: EDI Integration Service
Description: EDI message failed to process within the configured timeout period (default 30 seconds).

Resolution Steps:
1. Check the EDI service logs for timeout errors:
   check_log("edi_integration_service.log", "EDI_TIMEOUT")

2. Query the edi_message table to get message details:
   SELECT message_id, partner_id, message_type, status, received_at, error_message
   FROM edi_message
   WHERE partner_id = :partner_id
   AND status = 'TIMEOUT'
   ORDER BY received_at DESC
   LIMIT 5;

3. Decision Logic:
   - If logs show database connectivity issues: Check database status, restart EDI service
   - If message is malformed: Contact trading partner to resend valid message
   - If message is too large: Increase timeout configuration
   - If recurring issue: Escalate to L3 for performance investigation

Preconditions:
- Access to EDI service logs
- Database connection to edi_message table

Verification Steps:
- After resolution, verify message can be reprocessed successfully
- Check that similar messages are processing normally"""

    return SopSnippet(
        content=sop_content,
        metadata={
            "sop_title": "EDI: EDI Message Processing Timeout",
            "module": "EDI Integration Service",
            "error_code": "EDI_TIMEOUT",
            "chunk_type": "resolution"
        },
        score=0.88
    )


@pytest.fixture
def sample_edi_timeout_context(sample_edi_timeout_incident, sample_edi_timeout_sop):
    """Sample enriched context for EDI timeout scenario."""
    return EnrichedContext(
        original_report=sample_edi_timeout_incident,
        retrieved_sops=[sample_edi_timeout_sop],
        retrieval_summary="Retrieved 1 relevant SOP(s) for incident EDI-001. Top match: EDI: EDI Message Processing Timeout (similarity score: 0.88)"
    )


# ===== Test Cases =====

class TestSopExecutorAgentInitialization:
    """Test agent initialization and setup."""

    def test_agent_initialization_without_db(self, mock_llm):
        """Test that agent can be initialized without database interface."""
        agent = SopExecutorAgent(db_interface=None)

        assert agent is not None
        assert agent.llm is not None
        assert len(agent.tools) == 3
        assert agent.agent_executor is not None

    def test_agent_tools_created(self, mock_llm):
        """Test that all required tools are created."""
        agent = SopExecutorAgent(db_interface=None)

        tool_names = [tool.name for tool in agent.tools]
        assert "check_log" in tool_names
        assert "execute_sql_query" in tool_names
        assert "generate_sql_update_statement" in tool_names


class TestVesselErr4Scenario:
    """Test VESSEL_ERR_4 scenario execution."""

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_vessel_err_4_no_berth_applications(self, mock_executor_class, mock_llm, sample_vessel_err_4_context):
        """Test VESSEL_ERR_4 when no active berth applications exist (safe to expire)."""

        # Mock the agent executor's invoke method
        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance

        # Simulate agent execution steps
        mock_executor_instance.invoke.return_value = {
            "output": "I have identified an active vessel advice (ID: 123) for LIONCITY07 with no active berth applications. I've generated the SQL to expire this advice. Execute the proposed SQL statement after manual review and approval.",
            "intermediate_steps": [
                # Step 1: Query active vessel advice
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={
                            "query": "SELECT vessel_advice_no, system_vessel_name FROM vessel_advice WHERE system_vessel_name = :system_vessel_name AND effective_end_datetime IS NULL",
                            "params": '{"system_vessel_name": "LIONCITY07"}'
                        },
                        log="Querying for active vessel advice with system_vessel_name=LIONCITY07"
                    ),
                    json.dumps([{
                        "vessel_advice_no": 123,
                        "system_vessel_name": "LIONCITY07",
                        "effective_end_datetime": None
                    }])
                ),
                # Step 2: Check berth applications
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={
                            "query": "SELECT * FROM berth_application WHERE vessel_advice_no = :vessel_advice_no AND status = 'Active'",
                            "params": '{"vessel_advice_no": 123}'
                        },
                        log="Checking for active berth applications linked to vessel advice 123"
                    ),
                    json.dumps([])  # No active berth applications
                ),
                # Step 3: Generate SQL
                (
                    Mock(
                        tool="generate_sql_update_statement",
                        tool_input={
                            "sql_template": "UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no",
                            "params": '{"timestamp": "2025-10-18 00:00:00", "vessel_advice_no": 123}'
                        },
                        log="Generating SQL to expire vessel advice 123"
                    ),
                    "UPDATE vessel_advice SET effective_end_datetime = '2025-10-18 00:00:00' WHERE vessel_advice_no = 123;"
                )
            ]
        }

        # Create agent and execute
        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_vessel_err_4_context)

        # Assertions
        assert isinstance(result, ExecutionResult)
        assert result.selected_sop_title == "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice"
        assert len(result.executed_steps) == 3

        # Check step 1
        assert result.executed_steps[0].tool_called == "execute_sql_query"
        assert "LIONCITY07" in str(result.executed_steps[0].tool_input)
        assert result.executed_steps[0].status == "Success"

        # Check step 2
        assert result.executed_steps[1].tool_called == "execute_sql_query"
        assert "berth_application" in str(result.executed_steps[1].tool_input)
        assert result.executed_steps[1].status == "Success"

        # Check step 3
        assert result.executed_steps[2].tool_called == "generate_sql_update_statement"
        assert result.executed_steps[2].status == "Pending Manual Action"

        # Check proposed SQL
        assert result.proposed_sql_action is not None
        assert "UPDATE vessel_advice" in result.proposed_sql_action
        assert "vessel_advice_no = 123" in result.proposed_sql_action

        # Check final status
        assert result.final_status == "Requires Manual Confirmation"
        assert "manual review" in result.next_action_description.lower()

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_vessel_err_4_with_berth_applications(self, mock_executor_class, mock_llm, sample_vessel_err_4_context):
        """Test VESSEL_ERR_4 when active berth applications exist (must escalate)."""

        # Mock the agent executor's invoke method
        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance

        # Simulate agent execution steps with active berth applications
        mock_executor_instance.invoke.return_value = {
            "output": "Found active vessel advice (ID: 123) for LIONCITY07, but there are active berth applications linked to it. Cannot expire automatically. Escalate to L3 support for further investigation.",
            "intermediate_steps": [
                # Step 1: Query active vessel advice
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={
                            "query": "SELECT vessel_advice_no FROM vessel_advice WHERE system_vessel_name = :system_vessel_name AND effective_end_datetime IS NULL",
                            "params": '{"system_vessel_name": "LIONCITY07"}'
                        },
                        log="Querying for active vessel advice"
                    ),
                    json.dumps([{"vessel_advice_no": 123}])
                ),
                # Step 2: Check berth applications - FOUND ACTIVE ONES
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={
                            "query": "SELECT * FROM berth_application WHERE vessel_advice_no = :vessel_advice_no AND status = 'Active'",
                            "params": '{"vessel_advice_no": 123}'
                        },
                        log="Checking for active berth applications"
                    ),
                    json.dumps([
                        {
                            "berth_application_id": 456,
                            "vessel_advice_no": 123,
                            "status": "Active"
                        }
                    ])
                )
            ]
        }

        # Create agent and execute
        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_vessel_err_4_context)

        # Assertions
        assert isinstance(result, ExecutionResult)
        assert len(result.executed_steps) == 2  # Only 2 steps - no SQL generation

        # Check that no SQL was generated
        assert result.proposed_sql_action is None

        # Check final status is escalation
        assert result.final_status == "Escalation Required"
        assert "escalate" in result.next_action_description.lower()


class TestEdiTimeoutScenario:
    """Test EDI timeout scenario execution."""

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_edi_timeout_execution(self, mock_executor_class, mock_llm, sample_edi_timeout_context):
        """Test EDI timeout scenario - check logs and query messages."""

        # Mock the agent executor's invoke method
        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance

        # Simulate agent execution steps
        mock_executor_instance.invoke.return_value = {
            "output": "Checked logs and found EDI_TIMEOUT errors. Queried the database and found 3 timeout messages from TP-MAERSK. Logs indicate database connectivity issues. Recommend restarting EDI service and checking database status.",
            "intermediate_steps": [
                # Step 1: Check logs
                (
                    Mock(
                        tool="check_log",
                        tool_input={
                            "log_file": "edi_integration_service.log",
                            "pattern": "EDI_TIMEOUT"
                        },
                        log="Checking EDI service logs for timeout errors"
                    ),
                    "Searched edi_integration_service.log for pattern 'EDI_TIMEOUT'. Found 5 matches in last hour. [Database connection pool exhausted]"
                ),
                # Step 2: Query EDI messages
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={
                            "query": "SELECT message_id, partner_id, status, received_at FROM edi_message WHERE partner_id = :partner_id AND status = 'TIMEOUT' ORDER BY received_at DESC LIMIT 5",
                            "params": '{"partner_id": "TP-MAERSK"}'
                        },
                        log="Querying for timeout messages from TP-MAERSK"
                    ),
                    json.dumps([
                        {"message_id": "MSG001", "partner_id": "TP-MAERSK", "status": "TIMEOUT", "received_at": "2025-10-18 10:30:00"},
                        {"message_id": "MSG002", "partner_id": "TP-MAERSK", "status": "TIMEOUT", "received_at": "2025-10-18 10:25:00"},
                        {"message_id": "MSG003", "partner_id": "TP-MAERSK", "status": "TIMEOUT", "received_at": "2025-10-18 10:20:00"}
                    ])
                )
            ]
        }

        # Create agent and execute
        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_edi_timeout_context)

        # Assertions
        assert isinstance(result, ExecutionResult)
        assert result.selected_sop_title == "EDI: EDI Message Processing Timeout"
        assert len(result.executed_steps) == 2

        # Check step 1: check_log
        assert result.executed_steps[0].tool_called == "check_log"
        assert result.executed_steps[0].status == "Success"

        # Check step 2: execute_sql_query
        assert result.executed_steps[1].tool_called == "execute_sql_query"
        assert "TP-MAERSK" in str(result.executed_steps[1].tool_input)
        assert result.executed_steps[1].status == "Success"

        # EDI timeout should not generate SQL - just investigation
        assert result.proposed_sql_action is None

        # Final status should be completed (investigation done)
        assert result.final_status in ["Completed Successfully", "Escalation Required"]


class TestExecutionResultStructure:
    """Test ExecutionResult structure and content."""

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_execution_result_contains_original_context(self, mock_executor_class, mock_llm, sample_vessel_err_4_context):
        """Test that ExecutionResult preserves original context."""

        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance
        mock_executor_instance.invoke.return_value = {
            "output": "Execution completed.",
            "intermediate_steps": []
        }

        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_vessel_err_4_context)

        assert result.original_context == sample_vessel_err_4_context
        assert result.original_context.original_report.incident_id == "ALR-861631"

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_execution_result_step_details(self, mock_executor_class, mock_llm, sample_vessel_err_4_context):
        """Test that StepExecutionDetail contains all required fields."""

        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance
        mock_executor_instance.invoke.return_value = {
            "output": "Test output",
            "intermediate_steps": [
                (
                    Mock(
                        tool="execute_sql_query",
                        tool_input={"query": "SELECT * FROM test", "params": "{}"},
                        log="Test log"
                    ),
                    json.dumps([{"id": 1}])
                )
            ]
        }

        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_vessel_err_4_context)

        assert len(result.executed_steps) == 1
        step = result.executed_steps[0]

        assert step.step_description is not None
        assert step.tool_called == "execute_sql_query"
        assert step.tool_input is not None
        assert step.tool_output is not None
        assert step.status in ["Success", "Failure", "Skipped", "Pending Manual Action"]
        assert step.summary is not None

    def test_no_sop_available(self, mock_llm):
        """Test behavior when no SOPs are available."""

        # Create context with no SOPs
        incident = IncidentReport(
            incident_id="TEST-001",
            problem_summary="Unknown error",
            affected_module="Unknown",
            error_code=None,
            urgency="Low",
            entities=[]
        )

        context = EnrichedContext(
            original_report=incident,
            retrieved_sops=[],
            retrieval_summary="No relevant SOPs found."
        )

        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(context)

        assert result.selected_sop_title is None
        assert result.final_status == "Failed"
        assert "manual investigation" in result.next_action_description.lower()
        assert len(result.executed_steps) == 0


class TestSqlGenerationSafety:
    """Test that SQL generation is safe and doesn't execute."""

    def test_generate_sql_update_statement_tool(self):
        """Test the generate_sql_update_statement tool directly."""
        from agents.agent_3_sop_executor.tools import generate_sql_update_statement

        sql_template = "UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no"
        params = '{"timestamp": "2025-10-18 00:00:00", "vessel_advice_no": 123}'

        result = generate_sql_update_statement(sql_template, params)

        assert "UPDATE vessel_advice" in result
        assert "'2025-10-18 00:00:00'" in result
        assert "123" in result
        assert result.strip().endswith(';')

    def test_generate_sql_with_string_escaping(self):
        """Test that SQL generation properly escapes single quotes."""
        from agents.agent_3_sop_executor.tools import generate_sql_update_statement

        sql_template = "UPDATE vessel SET name = :name WHERE id = :id"
        params = '{"name": "O\'Reilly Vessel", "id": 456}'

        result = generate_sql_update_statement(sql_template, params)

        # Should escape single quote
        assert "O''Reilly Vessel" in result or "O\\'Reilly Vessel" in result

    def test_generate_sql_with_null_values(self):
        """Test SQL generation with NULL values."""
        from agents.agent_3_sop_executor.tools import generate_sql_update_statement

        sql_template = "UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :id"
        params = '{"timestamp": null, "id": 789}'

        result = generate_sql_update_statement(sql_template, params)

        assert "NULL" in result
        assert "789" in result


class TestErrorHandling:
    """Test error handling in agent execution."""

    @patch('agents.agent_3_sop_executor.agent.AgentExecutor')
    def test_agent_execution_error(self, mock_executor_class, mock_llm, sample_vessel_err_4_context):
        """Test that agent handles execution errors gracefully."""

        mock_executor_instance = MagicMock()
        mock_executor_class.return_value = mock_executor_instance

        # Simulate execution error
        mock_executor_instance.invoke.side_effect = Exception("Test execution error")

        agent = SopExecutorAgent(db_interface=None)
        result = agent.execute_sop(sample_vessel_err_4_context)

        assert result.final_status == "Failed"
        assert "error" in result.next_action_description.lower()
        assert len(result.executed_steps) == 1
        assert result.executed_steps[0].status == "Failure"
        assert "Test execution error" in result.executed_steps[0].tool_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
