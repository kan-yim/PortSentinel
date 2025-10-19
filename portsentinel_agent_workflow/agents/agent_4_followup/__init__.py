"""
Agent 4: Resolution Follow-up Agent.

This module implements post-resolution follow-up including L2 status checking,
L3 escalation, and summary generation.
"""

from .agent import ResolutionFollowupAgent
from .models import (
    L2ExecutionStatus,
    EscalationContact,
    EscalationEmail,
    ResolutionSummary,
    FollowupResult
)

__all__ = [
    'ResolutionFollowupAgent',
    'L2ExecutionStatus',
    'EscalationContact',
    'EscalationEmail',
    'ResolutionSummary',
    'FollowupResult',
]
