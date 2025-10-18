"""
Pydantic models for Agent 3: SOP Executor Agent.

This module defines data structures for tracking SOP execution steps
and the final execution result.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# Import EnrichedContext from Agent 2
import sys
from pathlib import Path
rag_module_path = Path(__file__).parent.parent.parent.parent / "rag_module" / "src"
sys.path.insert(0, str(rag_module_path))

from rag_agent.models import EnrichedContext


class StepExecutionDetail(BaseModel):
    """
    Represents the execution details of a single SOP step.

    Attributes:
        step_description: Description of the SOP step being attempted
        tool_called: Name of the tool used (e.g., 'execute_sql_query', 'check_log')
        tool_input: Parameters passed to the tool
        tool_output: Result returned by the tool
        status: Execution status of this step
        summary: Brief summary of what happened in this step
    """
    step_description: str = Field(
        ...,
        description="Description of the SOP step being attempted"
    )

    tool_called: Optional[str] = Field(
        None,
        description="Name of the tool used (e.g., 'execute_sql_query', 'check_log')"
    )

    tool_input: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters passed to the tool"
    )

    tool_output: Optional[Any] = Field(
        None,
        description="Result returned by the tool (could be string, list of dicts, etc.)"
    )

    status: Literal["Success", "Failure", "Skipped", "Pending Manual Action"] = Field(
        ...,
        description="Execution status of this step"
    )

    summary: str = Field(
        ...,
        description="Brief summary of what happened in this step"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "step_description": "Check for active vessel advice with system_vessel_name=LIONCITY07",
                "tool_called": "execute_sql_query",
                "tool_input": {
                    "query": "SELECT * FROM vessel_advice WHERE system_vessel_name = :system_vessel_name",
                    "params": {"system_vessel_name": "LIONCITY07"}
                },
                "tool_output": [
                    {
                        "vessel_advice_no": 123,
                        "system_vessel_name": "LIONCITY07",
                        "effective_end_datetime": None
                    }
                ],
                "status": "Success",
                "summary": "Found 1 active vessel advice (ID: 123)"
            }
        }


class ExecutionResult(BaseModel):
    """
    Main output model for SOP execution.

    Contains the original context, execution steps, proposed actions,
    and final status.
    """
    original_context: EnrichedContext = Field(
        ...,
        description="The enriched context from Agent 2"
    )

    selected_sop_title: Optional[str] = Field(
        None,
        description="Title of the SOP primarily used for execution"
    )

    executed_steps: List[StepExecutionDetail] = Field(
        default_factory=list,
        description="Details of each SOP step attempted"
    )

    proposed_sql_action: Optional[str] = Field(
        None,
        description="SQL UPDATE/DELETE statement generated for manual review and execution"
    )

    next_action_description: str = Field(
        ...,
        description="Text description of the next recommended action"
    )

    final_status: Literal[
        "Requires Manual Confirmation",
        "Completed Successfully",
        "Failed",
        "Escalation Required",
        "Ambiguous"
    ] = Field(
        ...,
        description="Final execution status"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_context": {
                    "original_report": {"incident_id": "ALR-861631"},
                    "retrieved_sops": [],
                    "retrieval_summary": "..."
                },
                "selected_sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
                "executed_steps": [
                    {
                        "step_description": "Query active vessel advice",
                        "tool_called": "execute_sql_query",
                        "tool_input": {},
                        "tool_output": [],
                        "status": "Success",
                        "summary": "Found active vessel advice"
                    }
                ],
                "proposed_sql_action": "UPDATE vessel_advice SET effective_end_datetime = '2025-10-18 00:00:00' WHERE vessel_advice_no = 123;",
                "next_action_description": "Execute the proposed SQL to expire the vessel advice, then retry creating the new advice.",
                "final_status": "Requires Manual Confirmation"
            }
        }
