"""
Example usage of Agent 4: Resolution Follow-up Agent.

This script demonstrates:
1. L2 Success scenario - Generate summary
2. L2 Failure scenario - Find L3 contact, draft email, generate summary
3. L2 Timeout scenario - Escalate and generate summary
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "agent_3_sop_executor"))

from agents.agent_4_followup.agent import ResolutionFollowupAgent
from agents.agent_4_followup.models import L2ExecutionStatus
from agents.agent_3_sop_executor.models import ExecutionResult


def load_agent3_result(file_path: str) -> ExecutionResult:
    """
    Load Agent 3 execution result from JSON file.

    Args:
        file_path: Path to Agent 3 result JSON

    Returns:
        ExecutionResult object
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return ExecutionResult(**data)


def example_1_l2_success():
    """
    Example 1: L2 successfully executed the resolution.

    Expected output:
    - No escalation needed
    - Generate success summary
    """
    print("\n" + "=" * 80)
    print("Example 1: L2 Success Scenario")
    print("=" * 80)

    # Load Agent 3 result
    agent3_result_path = Path(__file__).parent.parent / "agent_3_sop_executor" / "database_test_result.json"

    if not agent3_result_path.exists():
        print(f"❌ Agent 3 result not found at: {agent3_result_path}")
        print("Please run Agent 3 example first to generate this file.")
        return None

    print(f"\n[1] Loading Agent 3 execution result...")
    execution_result = load_agent3_result(str(agent3_result_path))
    print(f"    ✓ Loaded incident: {execution_result.original_context.original_report.incident_id}")

    # Create L2 success status
    print("\n[2] Simulating L2 successful execution...")
    l2_status = L2ExecutionStatus(
        execution_success=True,
        execution_timestamp=datetime.utcnow().isoformat(),
        time_elapsed_hours=2.5,
        execution_notes="Successfully executed the proposed SQL statement. Verified vessel advice is now expired.",
        timeout_threshold_hours=24.0,
        is_timeout=False
    )
    print(f"    ✓ L2 Status: Success")
    print(f"    ✓ Time elapsed: {l2_status.time_elapsed_hours} hours")

    # Initialize Agent 4
    print("\n[3] Initializing Agent 4...")
    contacts_path = "/Users/kanyim/portsentinel/escalation_contacts/Product_Team_Escalation_Contacts.csv"
    agent = ResolutionFollowupAgent(escalation_contacts_path=contacts_path)
    print("    ✓ Agent 4 initialized")

    # Process follow-up
    print("\n[4] Processing follow-up...")
    result = agent.process_followup(
        execution_result=execution_result,
        l2_status=l2_status
    )

    # Display results
    print("\n" + "=" * 80)
    print("FOLLOW-UP RESULT")
    print("=" * 80)

    print(f"\n✓ Escalation Required: {result.escalation_required}")
    print(f"✓ Resolution Outcome: {result.resolution_summary.resolution_outcome}")

    print(f"\n📋 Summary:")
    print(f"  - Incident ID: {result.resolution_summary.incident_id}")
    print(f"  - Error: {result.resolution_summary.error_identified}")
    print(f"  - Root Cause: {result.resolution_summary.root_cause}")
    print(f"  - Actions Taken: {len(result.resolution_summary.actions_taken)} actions")

    # Save summary to file
    print("\n[5] Saving summary to file...")
    summary_path = agent.save_summary_to_file(
        result.resolution_summary,
        output_dir="."
    )
    print(f"    ✓ Summary saved to: {summary_path}")

    # Save full result to JSON
    output_file = "example_1_l2_success_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"    ✓ Full result saved to: {output_file}")

    print("\n" + "=" * 80)

    return result


def example_2_l2_failure():
    """
    Example 2: L2 failed to execute the resolution.

    Expected output:
    - Escalation to L3 required
    - Find appropriate L3 contact
    - Draft escalation email
    - Generate escalation summary
    """
    print("\n" + "=" * 80)
    print("Example 2: L2 Failure Scenario")
    print("=" * 80)

    # Load Agent 3 result
    agent3_result_path = Path(__file__).parent.parent / "agent_3_sop_executor" / "database_test_result.json"

    if not agent3_result_path.exists():
        print(f"❌ Agent 3 result not found")
        return None

    print(f"\n[1] Loading Agent 3 execution result...")
    execution_result = load_agent3_result(str(agent3_result_path))
    print(f"    ✓ Loaded incident: {execution_result.original_context.original_report.incident_id}")

    # Create L2 failure status
    print("\n[2] Simulating L2 failed execution...")
    l2_status = L2ExecutionStatus(
        execution_success=False,
        execution_timestamp=datetime.utcnow().isoformat(),
        time_elapsed_hours=3.0,
        execution_notes="Attempted to execute SQL but encountered database permission error. Cannot modify vessel_advice table.",
        timeout_threshold_hours=24.0,
        is_timeout=False
    )
    print(f"    ✓ L2 Status: Failed")
    print(f"    ✓ Reason: {l2_status.execution_notes}")

    # Initialize Agent 4
    print("\n[3] Initializing Agent 4...")
    contacts_path = "/Users/kanyim/portsentinel/escalation_contacts/Product_Team_Escalation_Contacts.csv"
    agent = ResolutionFollowupAgent(escalation_contacts_path=contacts_path)
    print("    ✓ Agent 4 initialized")

    # Process follow-up
    print("\n[4] Processing follow-up...")
    result = agent.process_followup(
        execution_result=execution_result,
        l2_status=l2_status
    )

    # Display results
    print("\n" + "=" * 80)
    print("FOLLOW-UP RESULT")
    print("=" * 80)

    print(f"\n⚠️  Escalation Required: {result.escalation_required}")
    print(f"✓ Resolution Outcome: {result.resolution_summary.resolution_outcome}")

    if result.escalation_contact:
        print(f"\n📧 L3 Escalation Contact:")
        print(f"  - Name: {result.escalation_contact.contact_name}")
        print(f"  - Role: {result.escalation_contact.role}")
        print(f"  - Email: {result.escalation_contact.email}")
        print(f"  - Module: {result.escalation_contact.module}")

    if result.escalation_email:
        print(f"\n📨 Escalation Email Draft:")
        print(f"  - To: {result.escalation_email.to_email}")
        print(f"  - Subject: {result.escalation_email.subject}")
        print(f"  - Priority: {result.escalation_email.priority}")
        print(f"\n  Email Body Preview:")
        preview = result.escalation_email.body[:300]
        print(f"  {preview}...")

    # Save summary
    print("\n[5] Saving outputs...")
    summary_path = agent.save_summary_to_file(
        result.resolution_summary,
        output_dir="."
    )
    print(f"    ✓ Summary saved to: {summary_path}")

    # Save escalation email
    if result.escalation_email:
        email_file = "example_2_escalation_email.txt"
        with open(email_file, 'w', encoding='utf-8') as f:
            f.write(f"To: {result.escalation_email.to_email}\n")
            f.write(f"Subject: {result.escalation_email.subject}\n")
            f.write(f"Priority: {result.escalation_email.priority}\n")
            f.write(f"\n{result.escalation_email.body}")
        print(f"    ✓ Email draft saved to: {email_file}")

    # Save full result
    output_file = "example_2_l2_failure_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"    ✓ Full result saved to: {output_file}")

    print("\n" + "=" * 80)

    return result


def example_3_l2_timeout():
    """
    Example 3: L2 timeout - no response after 24 hours.

    Expected output:
    - Escalation due to timeout
    - Find L3 contact
    - Draft urgent escalation email
    - Generate summary with timeout note
    """
    print("\n" + "=" * 80)
    print("Example 3: L2 Timeout Scenario")
    print("=" * 80)

    # Load Agent 3 result
    agent3_result_path = Path(__file__).parent.parent / "agent_3_sop_executor" / "database_test_result.json"

    if not agent3_result_path.exists():
        print(f"❌ Agent 3 result not found")
        return None

    print(f"\n[1] Loading Agent 3 execution result...")
    execution_result = load_agent3_result(str(agent3_result_path))
    print(f"    ✓ Loaded incident: {execution_result.original_context.original_report.incident_id}")

    # Create L2 timeout status
    print("\n[2] Simulating L2 timeout (>24 hours)...")
    timeout_time = datetime.utcnow() - timedelta(hours=26)
    l2_status = L2ExecutionStatus(
        execution_success=False,
        execution_timestamp=timeout_time.isoformat(),
        time_elapsed_hours=26.0,
        execution_notes="No response from L2 team after 26 hours.",
        timeout_threshold_hours=24.0,
        is_timeout=True
    )
    print(f"    ⏰ L2 Status: Timeout")
    print(f"    ⏰ Time elapsed: {l2_status.time_elapsed_hours} hours")

    # Initialize Agent 4
    print("\n[3] Initializing Agent 4...")
    contacts_path = "/Users/kanyim/portsentinel/escalation_contacts/Product_Team_Escalation_Contacts.csv"
    agent = ResolutionFollowupAgent(escalation_contacts_path=contacts_path)
    print("    ✓ Agent 4 initialized")

    # Process follow-up
    print("\n[4] Processing follow-up...")
    result = agent.process_followup(
        execution_result=execution_result,
        l2_status=l2_status
    )

    # Display results
    print("\n" + "=" * 80)
    print("FOLLOW-UP RESULT")
    print("=" * 80)

    print(f"\n⚠️  Escalation Required: {result.escalation_required} (Timeout)")
    print(f"✓ Resolution Outcome: {result.resolution_summary.resolution_outcome}")

    if result.escalation_contact:
        print(f"\n📧 L3 Escalation Contact:")
        print(f"  - Name: {result.escalation_contact.contact_name}")
        print(f"  - Email: {result.escalation_contact.email}")

    if result.escalation_email:
        print(f"\n📨 Escalation Email (Urgent - Timeout):")
        print(f"  - Priority: {result.escalation_email.priority}")
        print(f"  - Subject: {result.escalation_email.subject}")

    # Save outputs
    print("\n[5] Saving outputs...")
    summary_path = agent.save_summary_to_file(
        result.resolution_summary,
        output_dir="."
    )
    print(f"    ✓ Summary saved to: {summary_path}")

    # Save escalation email
    if result.escalation_email:
        email_file = "example_3_timeout_escalation_email.txt"
        with open(email_file, 'w', encoding='utf-8') as f:
            f.write(f"To: {result.escalation_email.to_email}\n")
            f.write(f"Subject: {result.escalation_email.subject}\n")
            f.write(f"Priority: {result.escalation_email.priority}\n")
            f.write(f"\n{result.escalation_email.body}")
        print(f"    ✓ Email draft saved to: {email_file}")

    output_file = "example_3_l2_timeout_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"    ✓ Full result saved to: {output_file}")

    print("\n" + "=" * 80)

    return result


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("AGENT 4: RESOLUTION FOLLOW-UP - EXAMPLES")
    print("=" * 80)

    try:
        # Example 1: L2 Success
        result1 = example_1_l2_success()

        # Example 2: L2 Failure
        result2 = example_2_l2_failure()

        # Example 3: L2 Timeout
        result3 = example_3_l2_timeout()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 80)

        print("\n📁 Generated Files:")
        print("  - resolution_summary_*.md (3 files)")
        print("  - example_1_l2_success_result.json")
        print("  - example_2_l2_failure_result.json")
        print("  - example_2_escalation_email.txt")
        print("  - example_3_l2_timeout_result.json")
        print("  - example_3_timeout_escalation_email.txt")

        print("\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
