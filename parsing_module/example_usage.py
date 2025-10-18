"""
Example usage of the Incident Report Parser.

This script demonstrates how to use the parsing module with sample
incident reports from different sources.
"""

from parsing_agent import parse_incident_report, IncidentReportParser, ParsingError
import json


def example_1_email_container_error():
    """Example: Parse an email about a container error."""
    print("=" * 80)
    print("EXAMPLE 1: Email - Container Not Found Error")
    print("=" * 80)

    raw_text = """RE: Email ALR-861600 | CMAU0000020 - Duplicate Container information received  
To: Ops Team Duty; Jen 
Cc: Customer Service 
Hi Jen, 
Please assist in checking container CMAU0000020. Customer on PORTNET is seeing 2 
identical containers information.  
Thanks.  
Regards, 
Kenny"""

    try:
        report = parse_incident_report(
            source_type="Email",
            raw_text=raw_text
        )

        print(f"\n✓ Parsing successful!")
        print(f"\nIncident ID: {report.incident_id}")
        print(f"Urgency: {report.urgency}")
        print(f"Affected Module: {report.affected_module}")
        print(f"Error Code: {report.error_code}")
        print(f"\nProblem Summary:")
        print(f"  {report.problem_summary}")
        print(f"\nExtracted Entities:")
        for entity in report.entities:
            print(f"  - {entity.type}: {entity.value}")
        print(f"\nPotential Cause: {report.potential_cause_hint}")

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")


def example_2_sms_vessel_error():
    """Example: Parse an SMS about a vessel timestamp error."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: SMS - Vessel Timestamp Error")
    print("=" * 80)

    raw_text = """RE: Email ALR-861631 | VESSEL_ERR_4 - System Vessel Name has been used by other vessel 
advice 
To: Ops Team Duty; Vedu 
Cc: Customer Service 
Hi Vedu, 
Customer reported that they were unable to create vessel advice for MV Lion City 07 and 
hit error VESSEL_ERR_4. The local vessel name had been used by other vessel advice.  
 
Please assist, thanks. 
Regards, 
Jia Xuan"""

    try:
        report = parse_incident_report(
            source_type="SMS",
            raw_text=raw_text
        )

        print(f"\n✓ Parsing successful!")
        print(f"\nIncident ID: {report.incident_id}")
        print(f"Urgency: {report.urgency}")
        print(f"Affected Module: {report.affected_module}")
        print(f"\nProblem Summary:")
        print(f"  {report.problem_summary}")
        print(f"\nExtracted Entities:")
        for entity in report.entities:
            print(f"  - {entity.type}: {entity.value}")

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")


def example_3_call_transcript_edi():
    """Example: Parse a call transcript about EDI errors."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Call Transcript - EDI Processing Error")
    print("=" * 80)

    raw_text = """Alert: SMS INC-154599  
Issue: EDI message REF-IFT-0007 stuck in ERROR status (Sender: LINE-PSA, 
Recipient: PSA-TOS, State: No acknowledgment sent, ack_at is NULL)."""

    try:
        report = parse_incident_report(
            source_type="Call",
            raw_text=raw_text
        )

        print(f"\n✓ Parsing successful!")
        print(f"\nIncident ID: {report.incident_id}")
        print(f"Urgency: {report.urgency}")
        print(f"Affected Module: {report.affected_module}")
        print(f"\nProblem Summary:")
        print(f"  {report.problem_summary}")
        print(f"\nExtracted Entities:")
        for entity in report.entities:
            print(f"  - {entity.type}: {entity.value}")

        # Export to JSON
        print(f"\n--- JSON Output ---")
        print(json.dumps(report.model_dump(), indent=2))

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")


def example_4_custom_parser():
    """Example: Using a custom parser instance with specific settings."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Custom Parser Configuration")
    print("=" * 80)

    # Create a parser instance with custom settings
    parser = IncidentReportParser(
        model_name="gpt-4o",  # Or gpt-3.5-turbo for faster/cheaper
        temperature=0.0       # Deterministic output
    )

    raw_text = """Alert: Call TCK-742311  
 
Issues: Vessel MV PACIFIC DAWN/07E exception at Pasir Panjang Terminal 4 
Details: BAPLIE inconsistency for MV PACIFIC DAWN/07E: COARRI shows load completed for bay 
14, but BAPLIE still lists units in those slots. Older timestamp regressed the plan. All numeric 
identifiers are randomized placeholders; no credentials stored. Please investigate and resolve 
urgently. Contact the relevant team if needed."""

    try:
        report = parser.parse(
            source_type="Email",
            raw_text=raw_text
        )

        print(f"\n✓ Parsing successful!")
        print(f"\nUrgency: {report.urgency}")
        print(f"Affected Module: {report.affected_module}")
        print(f"\nExtracted {len(report.entities)} entities:")
        for entity in report.entities:
            print(f"  - {entity.type}: {entity.value}")

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")
    except ValueError as e:
        print(f"✗ Invalid input: {e}")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "INCIDENT REPORT PARSER - USAGE EXAMPLES" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")

    # Note: Uncomment examples when you have a valid OpenAI API key configured

    print("\nNOTE: To run these examples, you need to:")
    print("  1. Set up your OpenAI API key in the .env file")
    print("  2. Uncomment the example function calls below")
    print("  3. Run: python example_usage.py")

    # Uncomment these lines when ready to test with actual API
    # example_1_email_container_error()
    # example_2_sms_vessel_error()
    # example_3_call_transcript_edi()
    # example_4_custom_parser()

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
