"""
Pydantic models for incident report parsing.

This module defines the data structures used for parsing and validating
incident reports from various sources (Email, SMS, Call transcripts).
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class Entity(BaseModel):
    """
    Represents a key entity extracted from an incident report.

    Attributes:
        type: The category of the entity (e.g., 'container_number', 'vessel_name', 'error_code')
        value: The actual value of the entity (e.g., 'CMAU1234567', 'MAERSK VENTURE')
    """
    type: str = Field(..., description="Type/category of the entity")
    value: str = Field(..., description="The actual value of the extracted entity")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "container_number",
                "value": "CMAU1234567"
            }
        }


class IncidentReport(BaseModel):
    """
    Structured representation of a parsed incident report.

    This model captures all essential information extracted from raw incident
    reports, including metadata, classification, entities, and the problem description.
    """

    incident_id: Optional[str] = Field(
        None,
        description="Extracted incident/ticket ID if present (e.g., ALR-12345, INC-67890, TCK-54321)"
    )

    source_type: Literal["Email", "SMS", "Call"] = Field(
        ...,
        description="Source channel of the incident report"
    )

    received_timestamp_utc: str = Field(
        ...,
        description="Timestamp when the report was processed by the system (ISO 8601 UTC format)"
    )

    reported_timestamp_hint: Optional[str] = Field(
        None,
        description="Any phrase from the text indicating when the incident occurred (e.g., 'this morning', '2 hours ago', '14:30')"
    )

    urgency: Literal["High", "Medium", "Low"] = Field(
        "Medium",
        description="Inferred urgency level based on keywords, context, and severity indicators"
    )

    affected_module: Optional[Literal["Container", "Vessel", "EDI/API"]] = Field(
        None,
        description="Primary system module affected by the incident"
    )

    entities: List[Entity] = Field(
        default_factory=list,
        description="List of key entities extracted from the report (containers, vessels, users, error codes, etc.)"
    )

    error_code: Optional[str] = Field(
        None,
        description="Specific error code mentioned in the report (e.g., VESSEL_ERR_4, EDI_ERR_1, CONTAINER_404)"
    )

    problem_summary: str = Field(
        ...,
        description="A concise, clear summary of the core issue reported (1-2 sentences)"
    )

    potential_cause_hint: Optional[str] = Field(
        None,
        description="Phrases or clues from the text that suggest a potential root cause (e.g., 'timestamp mismatch', 'database timeout', 'network issue')"
    )

    raw_text: str = Field(
        ...,
        description="The complete original input text for audit and reference purposes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "ALR-12345",
                "source_type": "Email",
                "received_timestamp_utc": "2025-10-18T10:30:00Z",
                "reported_timestamp_hint": "this morning around 9am",
                "urgency": "High",
                "affected_module": "Container",
                "entities": [
                    {"type": "container_number", "value": "CMAU1234567"},
                    {"type": "user_id", "value": "john.doe@example.com"},
                    {"type": "error_code", "value": "CONTAINER_404"}
                ],
                "error_code": "CONTAINER_404",
                "problem_summary": "Container CMAU1234567 not found in the system when attempting to update status.",
                "potential_cause_hint": "Container may not have been properly registered during gate-in",
                "raw_text": "Subject: URGENT - Container not found\n\nHi support team,\n\nThis morning around 9am, I tried to update the status of container CMAU1234567 but got error CONTAINER_404..."
            }
        }


class ParsingError(Exception):
    """
    Custom exception raised when incident report parsing fails.

    This exception is raised when the LLM fails to parse the input text
    or when the output doesn't conform to the expected Pydantic schema.
    """
    pass
