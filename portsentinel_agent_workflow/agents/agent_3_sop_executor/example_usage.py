"""
Example usage of Agent 3: SOP Executor Agent.

This script demonstrates how to use the SOP Executor Agent to execute
SOPs step-by-step based on enriched context from Agent 2.

It loads example data from Agent 1 and Agent 2, then executes the SOPs
and displays the results.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add paths for imports
rag_module_path = Path(__file__).parent.parent.parent.parent / "rag_module" / "src"
sys.path.insert(0, str(rag_module_path))

from rag_agent.models import EnrichedContext
from agents.agent_3_sop_executor.agent import SopExecutorAgent
from agents.agent_3_sop_executor.models import ExecutionResult

# Optional: Load environment variables if needed
from dotenv import load_dotenv
load_dotenv()


def load_enriched_context(file_path: str, index: int = 0) -> EnrichedContext:
    """
    Load enriched context from Agent 2 output file.

    Args:
        file_path: Path to the enriched context JSON file
        index: Index of the case to load (for files with multiple cases)

    Returns:
        EnrichedContext object
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both single case and multiple cases
    if isinstance(data, list):
        case_data = data[index]
    else:
        case_data = data

    return EnrichedContext(**case_data)


def print_execution_result(result: ExecutionResult):
    """
    Pretty print the execution result.

    Args:
        result: ExecutionResult from agent execution
    """
    print("\n" + "=" * 80)
    print("EXECUTION RESULT")
    print("=" * 80)

    # Original incident
    report = result.original_context.original_report
    print(f"\nIncident ID: {report.incident_id}")
    print(f"Problem Summary: {report.problem_summary}")
    print(f"Error Code: {report.error_code}")
    print(f"Affected Module: {report.affected_module}")

    # Selected SOP
    print(f"\nSelected SOP: {result.selected_sop_title or 'None'}")

    # Executed steps
    print(f"\nExecuted Steps: {len(result.executed_steps)}")
    for i, step in enumerate(result.executed_steps, 1):
        print(f"\n  Step {i}: {step.summary}")
        print(f"    Tool: {step.tool_called}")
        print(f"    Status: {step.status}")
        if step.tool_input:
            print(f"    Input: {json.dumps(step.tool_input, indent=6)}")
        if step.tool_output:
            output_str = str(step.tool_output)
            if len(output_str) > 200:
                output_str = output_str[:200] + "..."
            print(f"    Output: {output_str}")

    # Proposed SQL
    if result.proposed_sql_action:
        print("\n" + "-" * 80)
        print("PROPOSED SQL ACTION (Requires Manual Review):")
        print("-" * 80)
        print(result.proposed_sql_action)
        print("-" * 80)

    # Final status
    print(f"\nFinal Status: {result.final_status}")
    print(f"Next Action: {result.next_action_description}")
    print("\n" + "=" * 80)


def example_1_vessel_err_4():
    """
    Example 1: Execute VESSEL_ERR_4 SOP.

    This example shows how to handle the common scenario where a vessel name
    is already in use by another vessel advice.
    """
    print("\n" + "#" * 80)
    print("# Example 1: VESSEL_ERR_4 - Vessel Name Already in Use")
    print("#" * 80)

    # Load enriched context from Agent 2
    rag_output_path = Path(__file__).parent.parent.parent.parent / "rag_module" / "all_enriched_results.json"

    # Find the VESSEL_ERR_4 case (ALR-861631)
    with open(rag_output_path, 'r') as f:
        all_cases = json.load(f)

    vessel_err_4_case = None
    for case in all_cases:
        if case['original_report']['incident_id'] == 'ALR-861631':
            vessel_err_4_case = case
            break

    if not vessel_err_4_case:
        print("ERROR: Could not find VESSEL_ERR_4 case in enriched results")
        return None

    context = EnrichedContext(**vessel_err_4_case)

    print(f"\nLoaded incident: {context.original_report.incident_id}")
    print(f"Error Code: {context.original_report.error_code}")
    print(f"Retrieved SOPs: {len(context.retrieved_sops)}")

    # Create SOP Executor Agent
    print("\nInitializing SOP Executor Agent...")
    agent = SopExecutorAgent(db_interface=None)

    # Execute the SOP
    print("\nExecuting SOP...")
    result = agent.execute_sop(context)

    # Display results
    print_execution_result(result)

    # Save result to file
    output_file = "example_1_vessel_err_4_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\nResult saved to: {output_file}")

    return result


def example_2_edi_timeout():
    """
    Example 2: Execute EDI timeout SOP.

    This example shows how to investigate EDI message timeouts by checking
    logs and querying the database.
    """
    print("\n" + "#" * 80)
    print("# Example 2: EDI_TIMEOUT - EDI Message Processing Timeout")
    print("#" * 80)

    # Load enriched context from Agent 2
    rag_output_path = Path(__file__).parent.parent.parent.parent / "rag_module" / "all_enriched_results.json"

    # Find the EDI timeout case (EDI-001)
    with open(rag_output_path, 'r') as f:
        all_cases = json.load(f)

    edi_timeout_case = None
    for case in all_cases:
        if case['original_report']['incident_id'] == 'EDI-001':
            edi_timeout_case = case
            break

    if not edi_timeout_case:
        print("ERROR: Could not find EDI_TIMEOUT case in enriched results")
        return None

    context = EnrichedContext(**edi_timeout_case)

    print(f"\nLoaded incident: {context.original_report.incident_id}")
    print(f"Error Code: {context.original_report.error_code}")
    print(f"Retrieved SOPs: {len(context.retrieved_sops)}")

    # Create SOP Executor Agent
    print("\nInitializing SOP Executor Agent...")
    agent = SopExecutorAgent(db_interface=None)

    # Execute the SOP
    print("\nExecuting SOP...")
    result = agent.execute_sop(context)

    # Display results
    print_execution_result(result)

    # Save result to file
    output_file = "example_2_edi_timeout_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\nResult saved to: {output_file}")

    return result


def example_3_full_workflow():
    """
    Example 3: Full workflow from Agent 1 → Agent 2 → Agent 3.

    This example demonstrates the complete incident resolution workflow:
    1. Parse incident text (Agent 1)
    2. Retrieve relevant SOPs (Agent 2)
    3. Execute SOP steps (Agent 3)
    """
    print("\n" + "#" * 80)
    print("# Example 3: Full Workflow (Agent 1 → Agent 2 → Agent 3)")
    print("#" * 80)

    # Load Agent 1 output
    agent_1_output_path = Path(__file__).parent.parent.parent.parent / "parsing_module" / "parsed_output.json"

    if not agent_1_output_path.exists():
        print(f"ERROR: Agent 1 output not found at {agent_1_output_path}")
        print("Please run parsing_module/example_usage.py first")
        return None

    print(f"\nLoading Agent 1 output from: {agent_1_output_path}")

    # Load Agent 2 (RAG) module
    from rag_agent.validator import RagAgent
    from parsing_agent.models import IncidentReport

    # Create RAG agent
    rag_agent = RagAgent()

    # Load parsed incident from Agent 1
    with open(agent_1_output_path, 'r') as f:
        agent_1_data = json.load(f)

    incident = IncidentReport(**agent_1_data)

    print(f"Loaded incident: {incident.incident_id}")
    print(f"Problem: {incident.problem_summary[:100]}...")

    # Step 1: Retrieve SOPs (Agent 2)
    print("\n[Agent 2] Retrieving relevant SOPs...")
    enriched_context = rag_agent.retrieve(incident, k=3)
    print(f"Retrieved {len(enriched_context.retrieved_sops)} SOPs")

    # Step 2: Execute SOP (Agent 3)
    print("\n[Agent 3] Executing SOP...")
    agent_3 = SopExecutorAgent(db_interface=None)
    result = agent_3.execute_sop(enriched_context)

    # Display results
    print_execution_result(result)

    # Save complete workflow result
    workflow_result = {
        "agent_1_output": agent_1_data,
        "agent_2_context": enriched_context.model_dump(),
        "agent_3_result": result.model_dump()
    }

    output_file = "example_3_full_workflow_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(workflow_result, f, indent=2, ensure_ascii=False)
    print(f"\nComplete workflow result saved to: {output_file}")

    return result


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("AGENT 3: SOP EXECUTOR - EXAMPLE USAGE")
    print("=" * 80)

    # Example 1: VESSEL_ERR_4
    try:
        result_1 = example_1_vessel_err_4()
    except Exception as e:
        print(f"\nExample 1 failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Example 2: EDI Timeout
    try:
        result_2 = example_2_edi_timeout()
    except Exception as e:
        print(f"\nExample 2 failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Example 3: Full workflow
    try:
        result_3 = example_3_full_workflow()
    except Exception as e:
        print(f"\nExample 3 failed: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nGenerated output files:")
    print("  - example_1_vessel_err_4_result.json")
    print("  - example_2_edi_timeout_result.json")
    print("  - example_3_full_workflow_result.json")
    print("\n")


if __name__ == "__main__":
    main()
