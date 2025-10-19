"""
Agent 4: Resolution Follow-up Agent.

This module implements an AI agent that handles post-resolution follow-up:
- Checks L2 execution status
- Escalates to L3 if needed
- Generates resolution summaries
"""

import os
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Add paths for imports
import sys
agent_3_path = Path(__file__).parent.parent / "agent_3_sop_executor"
sys.path.insert(0, str(agent_3_path))

from agents.agent_3_sop_executor.models import ExecutionResult
from .models import (
    L2ExecutionStatus,
    EscalationContact,
    EscalationEmail,
    ResolutionSummary,
    FollowupResult
)
from .tools import (
    EscalationContactFinder,
    generate_escalation_email_body,
    generate_summary_markdown
)

# Load environment variables
load_dotenv()


class ResolutionFollowupAgent:
    """
    Agent 4: Resolution Follow-up Agent

    Handles post-resolution follow-up process:
    1. Check L2 execution status
    2. Escalate to L3 if needed (failure or timeout)
    3. Generate resolution summary

    Two main paths:
    - L2 Success → Generate summary
    - L2 Failure/Timeout → Find L3 contact → Draft email → Generate summary
    """

    def __init__(self, escalation_contacts_path: str):
        """
        Initialize the Resolution Follow-up Agent.

        Args:
            escalation_contacts_path: Path to Product_Team_Escalation_Contacts.csv
        """
        self.escalation_contacts_path = escalation_contacts_path

        # Initialize LLM for summary generation
        self.llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.3,  # Slightly creative for summary writing
        )

        # Initialize escalation contact finder
        self.contact_finder = EscalationContactFinder(escalation_contacts_path)

    def process_followup(
        self,
        execution_result: ExecutionResult,
        l2_status: L2ExecutionStatus
    ) -> FollowupResult:
        """
        Main follow-up processing method.

        Args:
            execution_result: Result from Agent 3 execution
            l2_status: L2 execution status

        Returns:
            FollowupResult containing complete follow-up information
        """
        # Determine if escalation is needed
        escalation_required = self._should_escalate(l2_status)

        escalation_contact = None
        escalation_email = None

        # If escalation needed, find contact and draft email
        if escalation_required:
            escalation_contact = self._find_escalation_contact(execution_result)

            if escalation_contact:
                escalation_email = self._draft_escalation_email(
                    execution_result=execution_result,
                    l2_status=l2_status,
                    contact=escalation_contact
                )

        # Generate resolution summary
        resolution_summary = self._generate_summary(
            execution_result=execution_result,
            l2_status=l2_status,
            escalation_contact=escalation_contact,
            escalated=escalation_required
        )

        # Create and return FollowupResult
        return FollowupResult(
            original_execution_result=execution_result,
            l2_status=l2_status,
            escalation_required=escalation_required,
            escalation_contact=escalation_contact,
            escalation_email=escalation_email,
            resolution_summary=resolution_summary
        )

    def _should_escalate(self, l2_status: L2ExecutionStatus) -> bool:
        """
        Determine if L3 escalation is needed.

        Escalation criteria:
        - L2 execution failed (execution_success = False)
        - L2 timeout (time_elapsed > threshold)

        Args:
            l2_status: L2 execution status

        Returns:
            True if escalation needed, False otherwise
        """
        # Failed execution
        if not l2_status.execution_success:
            return True

        # Timeout
        if l2_status.is_timeout:
            return True

        return False

    def _find_escalation_contact(
        self,
        execution_result: ExecutionResult
    ) -> Optional[EscalationContact]:
        """
        Find appropriate L3 escalation contact.

        Args:
            execution_result: Execution result from Agent 3

        Returns:
            EscalationContact or None
        """
        # Extract module and error code from original report
        report = execution_result.original_context.original_report
        module = report.affected_module
        error_code = report.error_code

        # Find contact using finder
        contact = self.contact_finder.find_contact(
            module=module,
            error_code=error_code
        )

        return contact

    def _draft_escalation_email(
        self,
        execution_result: ExecutionResult,
        l2_status: L2ExecutionStatus,
        contact: EscalationContact
    ) -> EscalationEmail:
        """
        Draft escalation email to L3 contact.

        Args:
            execution_result: Execution result from Agent 3
            l2_status: L2 execution status
            contact: L3 contact information

        Returns:
            EscalationEmail object
        """
        report = execution_result.original_context.original_report

        # Determine escalation reason
        if l2_status.is_timeout:
            escalation_reason = f"L2 timeout - No response after {l2_status.time_elapsed_hours:.1f} hours"
        elif not l2_status.execution_success:
            escalation_reason = "L2 execution unsuccessful"
        else:
            escalation_reason = "Escalation required"

        # Build attempted resolution description
        attempted_resolution = self._build_resolution_description(execution_result)

        # Generate email body
        email_body = generate_escalation_email_body(
            incident_id=report.incident_id or "Unknown",
            error_code=report.error_code or "Unknown",
            error_description=report.problem_summary,
            attempted_resolution=attempted_resolution,
            l2_notes=l2_status.execution_notes,
            escalation_reason=escalation_reason
        )

        # Create email subject
        subject = f"Escalation: {report.error_code} - {report.incident_id}"

        # Determine priority
        if report.urgency == "High":
            priority = "High"
        elif l2_status.is_timeout:
            priority = "High"
        else:
            priority = "Medium"

        return EscalationEmail(
            to_email=contact.email,
            to_name=contact.contact_name,
            subject=subject,
            body=email_body,
            cc_emails=["support@psa123.com"],  # Default CC
            priority=priority
        )

    def _build_resolution_description(
        self,
        execution_result: ExecutionResult
    ) -> str:
        """
        Build description of attempted resolution.

        Args:
            execution_result: Execution result from Agent 3

        Returns:
            Description string
        """
        description_parts = []

        # SOP used
        if execution_result.selected_sop_title:
            description_parts.append(
                f"SOP Applied: {execution_result.selected_sop_title}"
            )

        # Steps executed
        if execution_result.executed_steps:
            description_parts.append(
                f"\nSteps Executed ({len(execution_result.executed_steps)}):"
            )
            for i, step in enumerate(execution_result.executed_steps, 1):
                description_parts.append(f"  {i}. {step.summary}")

        # Proposed SQL
        if execution_result.proposed_sql_action:
            description_parts.append(
                f"\nProposed SQL Statement:\n{execution_result.proposed_sql_action}"
            )

        # Next action
        description_parts.append(
            f"\nRecommended Action: {execution_result.next_action_description}"
        )

        return "\n".join(description_parts)

    def _generate_summary(
        self,
        execution_result: ExecutionResult,
        l2_status: L2ExecutionStatus,
        escalation_contact: Optional[EscalationContact],
        escalated: bool
    ) -> ResolutionSummary:
        """
        Generate resolution summary using LLM.

        Args:
            execution_result: Execution result from Agent 3
            l2_status: L2 execution status
            escalation_contact: L3 contact if escalated
            escalated: Whether escalated to L3

        Returns:
            ResolutionSummary object
        """
        report = execution_result.original_context.original_report

        # Determine outcome
        if l2_status.execution_success and not escalated:
            outcome = "Resolved Successfully"
        elif escalated:
            outcome = "Escalated to L3"
        else:
            outcome = "Failed"

        # Build actions taken
        actions_taken = []
        actions_taken.append(f"Parsed incident report (ID: {report.incident_id})")
        actions_taken.append(f"Retrieved relevant SOP: {execution_result.selected_sop_title}")

        for step in execution_result.executed_steps:
            actions_taken.append(step.summary)

        if execution_result.proposed_sql_action:
            actions_taken.append("Generated SQL statement for manual execution")

        if l2_status.execution_success:
            actions_taken.append("L2 successfully executed resolution")
        else:
            actions_taken.append(f"L2 execution failed: {l2_status.execution_notes or 'No details provided'}")

        # Build timeline
        timeline = []
        timeline.append({
            "time": report.received_timestamp_utc or datetime.utcnow().isoformat(),
            "event": "Incident reported"
        })

        if execution_result.executed_steps:
            timeline.append({
                "time": datetime.utcnow().isoformat(),
                "event": f"SOP executed ({len(execution_result.executed_steps)} steps)"
            })

        if l2_status.execution_timestamp:
            status_text = "succeeded" if l2_status.execution_success else "failed"
            timeline.append({
                "time": l2_status.execution_timestamp,
                "event": f"L2 execution {status_text}"
            })

        if escalated:
            timeline.append({
                "time": datetime.utcnow().isoformat(),
                "event": f"Escalated to L3: {escalation_contact.contact_name if escalation_contact else 'Unknown'}"
            })

        # Use LLM to generate root cause analysis
        root_cause = self._generate_root_cause_analysis(report, execution_result)

        # Create summary
        return ResolutionSummary(
            incident_id=report.incident_id or "Unknown",
            error_identified=f"{report.error_code or 'Unknown'}: {report.problem_summary}",
            root_cause=root_cause,
            resolution_attempted=self._build_resolution_description(execution_result),
            resolution_outcome=outcome,
            actions_taken=actions_taken,
            timeline=timeline,
            escalated_to_l3=escalated,
            escalation_contact=escalation_contact
        )

    def _generate_root_cause_analysis(
        self,
        report,
        execution_result: ExecutionResult
    ) -> str:
        """
        Use LLM to generate root cause analysis.

        Args:
            report: Incident report
            execution_result: Execution result

        Returns:
            Root cause analysis text
        """
        prompt = ChatPromptTemplate.from_template(
            """You are a technical analyst reviewing an incident resolution.

**Incident Details:**
- Error Code: {error_code}
- Problem Summary: {problem_summary}
- Affected Module: {affected_module}

**Resolution Applied:**
- SOP Used: {sop_title}
- Steps Taken: {steps_count} steps
- Proposed Action: {next_action}

Based on the above information, provide a concise root cause analysis (2-3 sentences).
Focus on WHY the error occurred, not just WHAT happened.

Root Cause Analysis:"""
        )

        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "error_code": report.error_code or "Unknown",
                "problem_summary": report.problem_summary,
                "affected_module": report.affected_module or "Unknown",
                "sop_title": execution_result.selected_sop_title or "None",
                "steps_count": len(execution_result.executed_steps),
                "next_action": execution_result.next_action_description
            })

            return response.content.strip()

        except Exception as e:
            # Fallback if LLM fails
            return f"Root cause analysis not available. Error: {str(e)}"

    def save_summary_to_file(
        self,
        summary: ResolutionSummary,
        output_dir: str = "."
    ) -> str:
        """
        Save resolution summary to Markdown file.

        Args:
            summary: ResolutionSummary object
            output_dir: Directory to save file

        Returns:
            Path to saved file
        """
        # Generate markdown content
        markdown_content = generate_summary_markdown(
            incident_id=summary.incident_id,
            error_identified=summary.error_identified,
            root_cause=summary.root_cause,
            resolution_attempted=summary.resolution_attempted,
            resolution_outcome=summary.resolution_outcome,
            actions_taken=summary.actions_taken,
            timeline=summary.timeline,
            escalated_to_l3=summary.escalated_to_l3,
            escalation_contact=summary.escalation_contact,
            lessons_learned=summary.lessons_learned
        )

        # Generate filename
        incident_id_safe = summary.incident_id.replace('/', '_').replace('\\', '_')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"resolution_summary_{incident_id_safe}_{timestamp}.md"

        # Save to file
        output_path = Path(output_dir) / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return str(output_path)


# Example usage
if __name__ == "__main__":
    print("Agent 4: Resolution Follow-up Agent")
    print("=" * 80)
    print("\nThis agent handles post-resolution follow-up:")
    print("  1. Check L2 execution status")
    print("  2. Escalate to L3 if needed")
    print("  3. Generate resolution summary")
    print("\nSee example_usage.py for complete examples.")
    print("=" * 80)
