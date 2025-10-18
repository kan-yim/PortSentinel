"""
Incident Report Parsing Agent for PORTNET® Support System.

This package provides AI-powered parsing of incident reports from various
sources (Email, SMS, Call transcripts) into structured data for automated
incident management and resolution.
"""

from .models import IncidentReport, Entity, ParsingError
from .parser import IncidentReportParser, parse_incident_report

__version__ = "1.0.0"

__all__ = [
    "IncidentReport",
    "Entity",
    "ParsingError",
    "IncidentReportParser",
    "parse_incident_report",
]
