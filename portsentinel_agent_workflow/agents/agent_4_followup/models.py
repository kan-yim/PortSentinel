"""
Pydantic models for Agent 4: Resolution Follow-up Agent.

This module defines data structures for tracking L2 execution results,
L3 escalation, and summary generation.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Import ExecutionResult from Agent 3
import sys
from pathlib import Path
agent_3_path = Path(__file__).parent.parent / "agent_3_sop_executor"
sys.path.insert(0, str(agent_3_path))

from agents.agent_3_sop_executor.models import ExecutionResult


class L2ExecutionStatus(BaseModel):
    """
    Status of L2 execution attempt.

    Attributes:
        execution_success: Whether L2 successfully executed the resolution
        execution_timestamp: When L2 attempted execution
        time_elapsed_hours: Hours elapsed since resolution was provided
        execution_notes: Any notes from L2 about the execution
    """
    execution_success: bool = Field(
        ...,
        description="Whether L2 successfully executed the resolution"
    )

    execution_timestamp: Optional[str] = Field(
        None,
        description="ISO timestamp when L2 executed (or attempted to execute)"
    )

    time_elapsed_hours: float = Field(
        0.0,
        description="Hours elapsed since resolution was provided to L2"
    )

    execution_notes: Optional[str] = Field(
        None,
        description="Notes from L2 about execution (e.g., error encountered, partial success)"
    )

    timeout_threshold_hours: float = Field(
        24.0,
        description="Threshold for considering execution as timed out"
    )

    is_timeout: bool = Field(
        False,
        description="Whether this execution is considered timed out"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "execution_success": False,
                "execution_timestamp": "2025-10-19T10:30:00",
                "time_elapsed_hours": 26.5,
                "execution_notes": "Attempted to execute SQL but encountered permission error",
                "timeout_threshold_hours": 24.0,
                "is_timeout": True
            }
        }


class EscalationContact(BaseModel):
    """
    L3 escalation contact information.

    Attributes:
        module: Product module (Container, Vessel, EDI/API, Others)
        contact_name: Name of L3 contact person
        role: Role/title of the contact
        email: Email address
        escalation_steps: Steps to follow for escalation
    """
    module: str = Field(..., description="Product module")
    contact_name: str = Field(..., description="Name of L3 contact")
    role: str = Field(..., description="Role/title")
    email: str = Field(..., description="Email address")
    escalation_steps: str = Field(..., description="Escalation steps")

    class Config:
        json_schema_extra = {
            "example": {
                "module": "Vessel (VS)",
                "contact_name": "Jaden Smith",
                "role": "Vessel Operations",
                "email": "jaden.smith@psa123.com",
                "escalation_steps": "1. Notify Vessel Duty team. 2. If no response, escalate to Senior Ops Manager."
            }
        }


class EscalationEmail(BaseModel):
    """
    Draft escalation email to L3.

    Attributes:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject line
        body: Email body content
        cc_emails: CC recipients
        priority: Email priority
    """
    to_email: str = Field(..., description="Recipient email")
    to_name: str = Field(..., description="Recipient name")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    cc_emails: List[str] = Field(
        default_factory=list,
        description="CC email addresses"
    )
    priority: Literal["Low", "Medium", "High", "Critical"] = Field(
        "Medium",
        description="Email priority"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "to_email": "jaden.smith@psa123.com",
                "to_name": "Jaden Smith",
                "subject": "Escalation: VESSEL_ERR_4 - MV LIONCITY07 (Incident ALR-861631)",
                "body": "Dear Jaden,\n\nWe are escalating the following incident...",
                "cc_emails": ["support@psa123.com"],
                "priority": "High"
            }
        }


class ResolutionSummary(BaseModel):
    """
    Summary of incident resolution process.

    Attributes:
        incident_id: Original incident ID
        error_identified: Error code and description
        root_cause: Root cause analysis
        resolution_attempted: What resolution was attempted
        resolution_outcome: Final outcome
        actions_taken: List of actions taken
        timeline: Timeline of events
        escalated_to_l3: Whether escalated to L3
        lessons_learned: Optional lessons learned
    """
    incident_id: str = Field(..., description="Incident ID")

    error_identified: str = Field(
        ...,
        description="Error code and description"
    )

    root_cause: str = Field(
        ...,
        description="Root cause of the issue"
    )

    resolution_attempted: str = Field(
        ...,
        description="Resolution method attempted"
    )

    resolution_outcome: Literal[
        "Resolved Successfully",
        "Escalated to L3",
        "Pending L2 Action",
        "Failed"
    ] = Field(
        ...,
        description="Final outcome of resolution"
    )

    actions_taken: List[str] = Field(
        default_factory=list,
        description="List of actions taken during resolution"
    )

    timeline: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Timeline of events with timestamps"
    )

    escalated_to_l3: bool = Field(
        False,
        description="Whether issue was escalated to L3"
    )

    escalation_contact: Optional[EscalationContact] = Field(
        None,
        description="L3 contact if escalated"
    )

    lessons_learned: Optional[str] = Field(
        None,
        description="Lessons learned from this incident"
    )

    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When this summary was generated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "ALR-861631",
                "error_identified": "VESSEL_ERR_4: Vessel Name has been used by other vessel advice",
                "root_cause": "Active vessel advice exists for MV LIONCITY07 without proper expiration",
                "resolution_attempted": "Generated SQL to expire duplicate vessel advice record",
                "resolution_outcome": "Resolved Successfully",
                "actions_taken": [
                    "Identified duplicate vessel advice (ID: 123)",
                    "Verified no active berth applications",
                    "Generated SQL to expire old record"
                ],
                "timeline": [
                    {"time": "2025-10-18 10:00", "event": "Incident reported"},
                    {"time": "2025-10-18 10:05", "event": "SOP retrieved"},
                    {"time": "2025-10-18 10:10", "event": "Resolution executed"}
                ],
                "escalated_to_l3": False
            }
        }


class FollowupResult(BaseModel):
    """
    Main output model for Agent 4: Resolution Follow-up.

    Contains the complete follow-up process including L2 status check,
    optional L3 escalation, and summary generation.
    """
    original_execution_result: ExecutionResult = Field(
        ...,
        description="Original execution result from Agent 3"
    )

    l2_status: L2ExecutionStatus = Field(
        ...,
        description="L2 execution status"
    )

    escalation_required: bool = Field(
        ...,
        description="Whether L3 escalation is required"
    )

    escalation_contact: Optional[EscalationContact] = Field(
        None,
        description="L3 contact information if escalation needed"
    )

    escalation_email: Optional[EscalationEmail] = Field(
        None,
        description="Draft escalation email if escalation needed"
    )

    resolution_summary: ResolutionSummary = Field(
        ...,
        description="Summary of the resolution process"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_execution_result": {"...": "Agent 3 result"},
                "l2_status": {
                    "execution_success": False,
                    "time_elapsed_hours": 26.0,
                    "is_timeout": True
                },
                "escalation_required": True,
                "escalation_contact": {
                    "module": "Vessel (VS)",
                    "contact_name": "Jaden Smith",
                    "email": "jaden.smith@psa123.com"
                },
                "escalation_email": {
                    "to_email": "jaden.smith@psa123.com",
                    "subject": "Escalation: VESSEL_ERR_4..."
                },
                "resolution_summary": {
                    "incident_id": "ALR-861631",
                    "resolution_outcome": "Escalated to L3"
                }
            }
        }
