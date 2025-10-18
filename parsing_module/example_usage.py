"""
Example usage of the Incident Report Parser.

This script demonstrates how to use the parsing module with sample
incident reports from different sources. All outputs are in unified JSON format.
"""

from parsing_agent import parse_incident_report, IncidentReportParser, ParsingError
import json


def print_result(example_num, example_name, report):
    """Print parsing result in unified JSON format."""
    print("=" * 80)
    print(f"EXAMPLE {example_num}: {example_name}")
    print("=" * 80)
    print("\n✓ Parsing successful!\n")
    print("📄 Structured JSON Output:")
    print("-" * 80)

    # Convert to JSON with proper formatting
    output = report.model_dump()
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print("-" * 80)
    print()


def example_1_email_container_error():
    """Example: Parse an email about a container error."""
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
        print_result(1, "Email - Duplicate Container", report)

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_2_sms_vessel_error():
    """Example: Parse an SMS about a vessel timestamp error."""
    raw_text = """RE: Email ALR-861631 | VESSEL_ERR_4 - System Vessel Name has been used by other vessel advice
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
            source_type="Email",
            raw_text=raw_text
        )
        print_result(2, "Email - Vessel Error", report)

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_3_call_transcript_edi():
    """Example: Parse a call transcript about EDI errors."""
    raw_text = """Alert: SMS INC-154599
Issue: EDI message REF-IFT-0007 stuck in ERROR status (Sender: LINE-PSA,
Recipient: PSA-TOS, State: No acknowledgment sent, ack_at is NULL)."""

    try:
        report = parse_incident_report(
            source_type="SMS",
            raw_text=raw_text
        )
        print_result(3, "SMS - EDI Error", report)

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_4_custom_parser():
    """Example: Using a custom parser instance with specific settings."""
    raw_text = """Alert: Call TCK-742311

Issues: Vessel MV PACIFIC DAWN/07E exception at Pasir Panjang Terminal 4
Details: BAPLIE inconsistency for MV PACIFIC DAWN/07E: COARRI shows load completed for bay
14, but BAPLIE still lists units in those slots. Older timestamp regressed the plan. All numeric
identifiers are randomized placeholders; no credentials stored. Please investigate and resolve
urgently. Contact the relevant team if needed."""

    try:
        # Create a parser instance with custom settings
        parser = IncidentReportParser(
            model_name="gpt-4.1-mini",  # Azure deployment name
            temperature=0.0
        )

        report = parser.parse(
            source_type="Call",
            raw_text=raw_text
        )
        print_result(4, "Call - BAPLIE Inconsistency", report)

    except ParsingError as e:
        print(f"✗ Parsing failed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def save_all_results_to_file():
    """Parse all examples and save to a single JSON file."""
    print("\n" + "=" * 80)
    print("SAVING ALL RESULTS TO JSON FILE")
    print("=" * 80 + "\n")

    all_results = []

    # Define all test cases
    test_cases = [
        {
            "name": "Email - Duplicate Container",
            "source_type": "Email",
            "raw_text": """RE: Email ALR-861600 | CMAU0000020 - Duplicate Container information received
To: Ops Team Duty; Jen
Cc: Customer Service
Hi Jen,
Please assist in checking container CMAU0000020. Customer on PORTNET is seeing 2
identical containers information.
Thanks.
Regards,
Kenny"""
        },
        {
            "name": "Email - Vessel Error",
            "source_type": "Email",
            "raw_text": """RE: Email ALR-861631 | VESSEL_ERR_4 - System Vessel Name has been used by other vessel advice
To: Ops Team Duty; Vedu
Cc: Customer Service
Hi Vedu,
Customer reported that they were unable to create vessel advice for MV Lion City 07 and
hit error VESSEL_ERR_4. The local vessel name had been used by other vessel advice.

Please assist, thanks.
Regards,
Jia Xuan"""
        },
        {
            "name": "SMS - EDI Error",
            "source_type": "SMS",
            "raw_text": """Alert: SMS INC-154599
Issue: EDI message REF-IFT-0007 stuck in ERROR status (Sender: LINE-PSA,
Recipient: PSA-TOS, State: No acknowledgment sent, ack_at is NULL)."""
        },
        {
            "name": "Call - BAPLIE Inconsistency",
            "source_type": "Call",
            "raw_text": """Alert: Call TCK-742311

Issues: Vessel MV PACIFIC DAWN/07E exception at Pasir Panjang Terminal 4
Details: BAPLIE inconsistency for MV PACIFIC DAWN/07E: COARRI shows load completed for bay
14, but BAPLIE still lists units in those slots. Older timestamp regressed the plan. All numeric
identifiers are randomized placeholders; no credentials stored. Please investigate and resolve
urgently. Contact the relevant team if needed."""
        }
    ]

    # Parse all test cases
    for i, test_case in enumerate(test_cases, 1):
        try:
            report = parse_incident_report(
                source_type=test_case["source_type"],
                raw_text=test_case["raw_text"]
            )
            result = {
                "example_number": i,
                "example_name": test_case["name"],
                "status": "success",
                "parsed_data": report.model_dump()
            }
            all_results.append(result)
            print(f"✓ Parsed example {i}: {test_case['name']}")
        except Exception as e:
            result = {
                "example_number": i,
                "example_name": test_case["name"],
                "status": "failed",
                "error": str(e)
            }
            all_results.append(result)
            print(f"✗ Failed example {i}: {test_case['name']} - {e}")

    # Save to file
    output_file = "parsed_incidents.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ All results saved to: {output_file}")
    print(f"  Total incidents processed: {len(all_results)}")
    print(f"  Successful: {sum(1 for r in all_results if r['status'] == 'success')}")
    print(f"  Failed: {sum(1 for r in all_results if r['status'] == 'failed')}\n")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "INCIDENT REPORT PARSER - USAGE EXAMPLES" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\nAll outputs will be in unified JSON format\n")

    # Run individual examples
    example_1_email_container_error()
    example_2_sms_vessel_error()
    example_3_call_transcript_edi()
    example_4_custom_parser()

    # Save all results to a single JSON file
    save_all_results_to_file()

    print("=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
