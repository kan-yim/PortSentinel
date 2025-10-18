# Agent 3: SOP Executor Agent

## Overview

Agent 3 is an AI-powered agent that executes Standard Operating Procedures (SOPs) step-by-step using LangChain's Tool Use / Function Calling capabilities. It takes enriched context from Agent 2 (RAG module) and systematically executes the resolution steps defined in the retrieved SOPs.

## Key Features

- **Step-by-Step SOP Execution**: Follows SOP resolution steps sequentially
- **Tool Use / Function Calling**: Uses LangChain tools to interact with systems
- **Decision Logic**: Makes conditional decisions based on tool results
- **Safety First (Strategy 1)**: Generates SQL for UPDATE/DELETE but **does not execute** (requires manual approval)
- **State Management**: Tracks values across steps (e.g., IDs from query results)
- **Detailed Execution Tracking**: Returns comprehensive execution details and recommendations

## Architecture

```
┌─────────────────────┐
│  EnrichedContext    │  (from Agent 2)
│  - IncidentReport   │
│  - Retrieved SOPs   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SopExecutorAgent   │
│  - LangChain Agent  │
│  - Azure OpenAI     │
└──────────┬──────────┘
           │
           ├──► Tool 1: check_log
           ├──► Tool 2: execute_sql_query (SELECT only)
           └──► Tool 3: generate_sql_update_statement (no execution)
           │
           ▼
┌─────────────────────┐
│  ExecutionResult    │
│  - Executed Steps   │
│  - Proposed SQL     │
│  - Next Action      │
│  - Final Status     │
└─────────────────────┘
```

## Tools

### 1. check_log
- **Purpose**: Search log files for patterns
- **Example**: `check_log("edi_integration_service.log", "EDI_TIMEOUT")`
- **Returns**: Summary of matching log entries

### 2. execute_sql_query
- **Purpose**: Execute SELECT queries against the database
- **Important**: SELECT queries only - for data retrieval
- **Example**:
  ```python
  execute_sql_query(
      "SELECT * FROM vessel_advice WHERE system_vessel_name = :name",
      '{"name": "LIONCITY07"}'
  )
  ```
- **Returns**: JSON string of query results

### 3. generate_sql_update_statement
- **Purpose**: Generate UPDATE/DELETE SQL statements for manual review
- **Critical Safety Feature**: **DOES NOT EXECUTE** the SQL
- **Example**:
  ```python
  generate_sql_update_statement(
      "UPDATE vessel_advice SET effective_end_datetime = :ts WHERE vessel_advice_no = :id",
      '{"ts": "2025-10-18 00:00:00", "id": 123}'
  )
  ```
- **Returns**: Formatted SQL statement ready for manual execution

## Data Models

### StepExecutionDetail
Represents a single SOP step execution:
- `step_description`: What step was attempted
- `tool_called`: Which tool was used
- `tool_input`: Parameters passed to the tool
- `tool_output`: Result from the tool
- `status`: "Success", "Failure", "Skipped", "Pending Manual Action"
- `summary`: Brief summary of the step

### ExecutionResult
Main output from SOP execution:
- `original_context`: The enriched context from Agent 2
- `selected_sop_title`: Which SOP was executed
- `executed_steps`: List of StepExecutionDetail objects
- `proposed_sql_action`: SQL statement for manual execution (if any)
- `next_action_description`: What to do next
- `final_status`:
  - "Requires Manual Confirmation" - SQL generated, needs approval
  - "Completed Successfully" - All steps succeeded
  - "Failed" - Execution encountered errors
  - "Escalation Required" - Needs L3 support
  - "Ambiguous" - Unclear outcome

## Usage

### Basic Usage

```python
from agents.agent_3_sop_executor import SopExecutorAgent
from rag_agent.models import EnrichedContext

# Create agent
agent = SopExecutorAgent(db_interface=None)

# Load enriched context from Agent 2
context = EnrichedContext(...)  # From Agent 2 output

# Execute SOP
result = agent.execute_sop(context)

# Display results
print(f"Selected SOP: {result.selected_sop_title}")
print(f"Steps executed: {len(result.executed_steps)}")
print(f"Final status: {result.final_status}")
print(f"Next action: {result.next_action_description}")

if result.proposed_sql_action:
    print(f"\nProposed SQL (requires manual review):")
    print(result.proposed_sql_action)
```

### Full Workflow (Agent 1 → 2 → 3)

```python
# Step 1: Parse incident (Agent 1)
from parsing_agent import ParsingAgent
parsing_agent = ParsingAgent()
incident_report = parsing_agent.parse(raw_text)

# Step 2: Retrieve SOPs (Agent 2)
from rag_agent.validator import RagAgent
rag_agent = RagAgent()
enriched_context = rag_agent.retrieve(incident_report, k=3)

# Step 3: Execute SOP (Agent 3)
from agents.agent_3_sop_executor import SopExecutorAgent
executor = SopExecutorAgent(db_interface=None)
result = executor.execute_sop(enriched_context)
```

## Example Scenarios

### Scenario 1: VESSEL_ERR_4 - No Active Berth Applications

**Input**: Incident ALR-861631 - "Vessel Name has been used by other vessel advice"

**Execution Flow**:
1. Query active vessel advice for LIONCITY07
2. Check for active berth applications
3. Generate SQL to expire the vessel advice (no active berth apps found)

**Output**:
```json
{
  "selected_sop_title": "VAS: VESSEL_ERR_4 Vessel Name has been used by other vessel advice",
  "executed_steps": [
    {
      "tool_called": "execute_sql_query",
      "status": "Success",
      "summary": "Found active vessel advice ID 123"
    },
    {
      "tool_called": "execute_sql_query",
      "status": "Success",
      "summary": "No active berth applications found"
    },
    {
      "tool_called": "generate_sql_update_statement",
      "status": "Pending Manual Action",
      "summary": "Generated SQL to expire vessel advice"
    }
  ],
  "proposed_sql_action": "UPDATE vessel_advice SET effective_end_datetime = '2025-10-18 00:00:00' WHERE vessel_advice_no = 123;",
  "final_status": "Requires Manual Confirmation",
  "next_action_description": "Execute the proposed SQL statement after manual review and approval."
}
```

### Scenario 2: VESSEL_ERR_4 - With Active Berth Applications

**Execution Flow**:
1. Query active vessel advice for LIONCITY07
2. Check for active berth applications
3. Found active berth applications → Cannot expire automatically

**Output**:
```json
{
  "final_status": "Escalation Required",
  "next_action_description": "Escalate to L3 support for further investigation.",
  "proposed_sql_action": null
}
```

### Scenario 3: EDI Timeout Investigation

**Execution Flow**:
1. Check EDI service logs for timeout errors
2. Query edi_message table for recent timeout messages
3. Analyze results and recommend action

**Output**:
```json
{
  "final_status": "Completed Successfully",
  "next_action_description": "Restart EDI service and verify database connectivity. Monitor for recurring timeouts.",
  "proposed_sql_action": null
}
```

## Testing

### Run Unit Tests

```bash
cd /Users/kanyim/portsentinel/portsentinel_agent_workflow
source /Users/kanyim/portsentinel/.venv/bin/activate
python -m pytest tests/agents/test_agent_3_simple.py -v
```

### Test Coverage

- ✅ Agent initialization
- ✅ Tool creation and availability
- ✅ SQL generation with parameter substitution
- ✅ SQL generation with string escaping
- ✅ SQL generation with NULL values
- ✅ Execution with no SOPs available
- ✅ Execution with real SOP (live LLM test)
- ✅ Model creation and validation

### Run Examples

```bash
cd /Users/kanyim/portsentinel/portsentinel_agent_workflow/agents/agent_3_sop_executor
python example_usage.py
```

This will generate:
- `example_1_vessel_err_4_result.json` - VESSEL_ERR_4 scenario
- `example_2_edi_timeout_result.json` - EDI timeout scenario
- `example_3_full_workflow_result.json` - Full Agent 1→2→3 workflow

## Configuration

Agent 3 uses environment variables for Azure OpenAI configuration:

```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
```

## Safety Considerations

### Strategy 1: Generate But Don't Execute

**Critical Design Decision**: For all database modification operations (UPDATE, DELETE), Agent 3:
1. ✅ Generates the SQL statement
2. ❌ **Does NOT execute** the SQL
3. ✅ Returns the SQL for manual review and approval

**Why?**
- Prevents accidental data corruption
- Allows human verification before changes
- Maintains audit trail of proposed changes
- Complies with change management policies

### Execution Safety

- Temperature set to 0 for deterministic execution
- Maximum 15 iterations to prevent infinite loops
- All tool inputs and outputs are logged
- Comprehensive error handling and recovery

## File Structure

```
agents/agent_3_sop_executor/
├── __init__.py           # Package initialization
├── agent.py              # Main SopExecutorAgent class
├── models.py             # Pydantic models (ExecutionResult, StepExecutionDetail)
├── tools.py              # LangChain tools (check_log, execute_sql_query, generate_sql)
├── example_usage.py      # Example usage scripts
└── README.md             # This file

tests/agents/
├── test_agent_3_sop_executor.py  # Comprehensive tests with mocking
└── test_agent_3_simple.py        # Simplified functional tests
```

## Dependencies

- `langchain-openai`: Azure OpenAI integration
- `langchain`: Agent framework and tools
- `pydantic`: Data validation
- `python-dotenv`: Environment configuration

## Integration Points

### Input: EnrichedContext from Agent 2
```python
from rag_agent.models import EnrichedContext

# Agent 2 provides this
context = EnrichedContext(
    original_report=incident_report,    # From Agent 1
    retrieved_sops=[sop1, sop2, sop3],  # From RAG retrieval
    retrieval_summary="Retrieved 3 SOPs..."
)
```

### Output: ExecutionResult
```python
from agents.agent_3_sop_executor.models import ExecutionResult

# Agent 3 returns this
result = ExecutionResult(
    original_context=context,
    selected_sop_title="VAS: VESSEL_ERR_4...",
    executed_steps=[step1, step2, step3],
    proposed_sql_action="UPDATE ...",
    next_action_description="Execute SQL after review",
    final_status="Requires Manual Confirmation"
)
```

## Future Enhancements

1. **Database Interface Integration**: Connect execute_sql_query to actual database
2. **Enhanced Logging**: Integrate with centralized log aggregation systems
3. **Approval Workflow**: Add automated approval workflow for SQL execution
4. **Rollback Support**: Generate rollback SQL alongside modification statements
5. **Multi-SOP Execution**: Execute multiple SOPs in sequence if needed
6. **Real-time Monitoring**: Track execution metrics and success rates
7. **Learning from Execution**: Use execution outcomes to improve SOP retrieval

## Support

For issues or questions:
- Review test cases in `tests/agents/test_agent_3_simple.py`
- Check example usage in `example_usage.py`
- Refer to Agent 3 specification document

## License

Internal PSA CodeSprint 2025 Project
