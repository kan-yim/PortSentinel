"""
Agent 3: SOP Executor Agent.

This module implements an AI agent that executes Standard Operating Procedures (SOPs)
step-by-step using LangChain's Tool Use / Function Calling capabilities.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from dotenv import load_dotenv

# Add paths for imports
rag_module_path = Path(__file__).parent.parent.parent.parent / "rag_module" / "src"
sys.path.insert(0, str(rag_module_path))

from rag_agent.models import EnrichedContext
from .models import ExecutionResult, StepExecutionDetail
from .tools import check_log, generate_sql_update_statement

# Load environment variables
load_dotenv()


class SopExecutorAgent:
    """
    Agent 3: SOP Executor

    Executes Standard Operating Procedures step-by-step, using tools to:
    - Check logs
    - Query databases (SELECT)
    - Generate SQL statements for manual execution (UPDATE/DELETE)
    """

    def __init__(self, db_interface=None):
        """
        Initialize the SOP Executor Agent.

        Args:
            db_interface: Database interface instance for executing queries (optional for now)
        """
        self.db_interface = db_interface

        # Initialize Azure OpenAI LLM
        self.llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0,  # Deterministic for consistent execution
        )

        # Initialize tools
        self.tools = self._create_tools()

        # Create the agent
        self.agent_executor = self._create_agent_executor()

    def _create_execute_sql_query_tool(self) -> Tool:
        """
        Create the execute_sql_query tool with database interface binding.
        """
        def execute_sql_query_impl(query: str, params: Optional[str] = None) -> str:
            """
            Executes a SQL SELECT query against the database.

            Args:
                query: SQL SELECT query with named parameters
                params: JSON string of parameters

            Returns:
                JSON string of query results
            """
            if self.db_interface is None:
                return json.dumps({
                    "error": "Database interface not available",
                    "note": "This is a mock response. In production, provide a DatabaseInterface instance."
                })

            try:
                # Parse parameters
                params_dict = {}
                if params:
                    params_dict = json.loads(params) if isinstance(params, str) else params

                # Execute query using database interface
                return self.db_interface.execute_select_json(query, params_dict)

            except Exception as e:
                return json.dumps({"error": str(e)})

        return Tool(
            name="execute_sql_query",
            description="""Executes a SQL SELECT query against the database using named parameters.

**IMPORTANT**: This tool is for SELECT queries only. For UPDATE/DELETE operations, use generate_sql_update_statement instead.

Args:
    query: SQL SELECT query with named parameters (e.g., 'SELECT * FROM vessel_advice WHERE system_vessel_name = :system_vessel_name')
    params: JSON string of parameters (e.g., '{"system_vessel_name": "LIONCITY07"}')

Returns:
    JSON string containing the query results as a list of dictionaries.

Example:
    execute_sql_query("SELECT * FROM vessel_advice WHERE system_vessel_name = :name", '{"name": "LIONCITY07"}')
            """,
            func=execute_sql_query_impl
        )

    def _create_tools(self) -> List[Tool]:
        """Create the list of tools available to the agent."""
        tools = [
            Tool.from_function(
                func=check_log,
                name="check_log",
                description=check_log.description
            ),
            self._create_execute_sql_query_tool(),
            Tool.from_function(
                func=generate_sql_update_statement,
                name="generate_sql_update_statement",
                description=generate_sql_update_statement.description
            ),
        ]
        return tools

    def _create_agent_executor(self) -> AgentExecutor:
        """Create the agent executor with prompt and tools."""

        # Define the agent prompt
        system_message = """You are an AI assistant executing Standard Operating Procedures (SOPs) step-by-step to help resolve IT incidents.

**Your Task:**
You will receive incident details, relevant SOP snippets, and database validation results in the EnrichedContext. Your goal is to follow the 'Resolution Steps' section of the most relevant SOP provided.

**Available Tools:**
1. `check_log(log_file, pattern)` - Search log files for patterns
2. `execute_sql_query(query, params)` - Execute SELECT queries against the database
3. `generate_sql_update_statement(sql_template, params)` - Generate UPDATE/DELETE SQL for manual execution

**Tool Usage Guidelines:**
- For steps involving log checks: Use `check_log`
- For steps involving data queries (SELECT): Use `execute_sql_query`
  - Extract parameters from the incident context or previous results
  - Use named parameters like :system_vessel_name
- **CRITICAL SAFETY INSTRUCTION (Strategy 1):**
  - For database modifications (UPDATE, DELETE): Use `generate_sql_update_statement`
  - **DO NOT execute the modification directly**
  - The generated SQL requires manual review and confirmation

**Decision Logic:**
- Follow any "Decision Logic" or conditional steps in the SOP
- Base decisions on tool call results (e.g., "if no active berth applications found...")
- Keep track of values from previous steps (e.g., :active_vessel_advice_no)

**State Management:**
- Remember important values extracted from tool results
- Use these values as parameters in subsequent tool calls
- Reference them in your reasoning

**Output:**
Provide a clear summary including:
1. Steps executed
2. Results obtained
3. Decisions made
4. Next recommended action (e.g., "Execute the proposed SQL", "Escalate to L3")
5. Any SQL statements generated for manual execution
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create the agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True,
            max_iterations=15,
            handle_parsing_errors=True
        )

        return agent_executor

    def _select_primary_sop(self, context: EnrichedContext) -> Optional[Dict[str, Any]]:
        """
        Select the most relevant SOP from the enriched context.

        Args:
            context: Enriched context from Agent 2

        Returns:
            The primary SOP to execute, or None if no SOPs available
        """
        if not context.retrieved_sops:
            return None

        # Select the first (highest scored) SOP
        top_sop = context.retrieved_sops[0]

        return {
            "title": top_sop.metadata.get("sop_title", "Unknown SOP"),
            "content": top_sop.content,
            "score": top_sop.score,
            "metadata": top_sop.metadata
        }

    def _prepare_agent_input(self, context: EnrichedContext, sop: Dict[str, Any]) -> str:
        """
        Prepare the input string for the agent executor.

        Args:
            context: Enriched context from Agent 2
            sop: Selected SOP to execute

        Returns:
            Formatted input string
        """
        report = context.original_report

        input_parts = [
            "=== INCIDENT DETAILS ===",
            f"Incident ID: {report.incident_id}",
            f"Problem Summary: {report.problem_summary}",
            f"Affected Module: {report.affected_module or 'Unknown'}",
            f"Error Code: {report.error_code or 'N/A'}",
            f"Urgency: {report.urgency}",
            "",
            "=== EXTRACTED ENTITIES ===",
        ]

        for entity in report.entities:
            input_parts.append(f"- {entity.type}: {entity.value}")

        input_parts.extend([
            "",
            "=== SELECTED SOP ===",
            f"Title: {sop['title']}",
            f"Relevance Score: {sop['score']:.2f}",
            "",
            "=== SOP CONTENT ===",
            sop['content'],
            "",
            "=== RETRIEVAL SUMMARY ===",
            context.retrieval_summary,
            "",
            "=== YOUR TASK ===",
            "Execute the Resolution Steps from the SOP above, using the available tools.",
            "Remember to:",
            "1. Use execute_sql_query for SELECT operations",
            "2. Use generate_sql_update_statement for UPDATE/DELETE (do not execute)",
            "3. Keep track of values like IDs from query results",
            "4. Follow the decision logic in the SOP",
            "5. Provide a clear summary of actions taken and next steps"
        ])

        return "\n".join(input_parts)

    def execute_sop(self, context: EnrichedContext) -> ExecutionResult:
        """
        Main execution method - executes the SOP step-by-step.

        Args:
            context: Enriched context from Agent 2

        Returns:
            ExecutionResult containing execution details and recommendations
        """
        # Select the primary SOP
        selected_sop = self._select_primary_sop(context)

        if selected_sop is None:
            return ExecutionResult(
                original_context=context,
                selected_sop_title=None,
                executed_steps=[],
                proposed_sql_action=None,
                next_action_description="No SOPs available for execution. Manual investigation required.",
                final_status="Failed"
            )

        # Prepare agent input
        agent_input = self._prepare_agent_input(context, selected_sop)

        try:
            # Execute the agent
            result = self.agent_executor.invoke({"input": agent_input})

            # Process the result
            executed_steps = self._process_intermediate_steps(
                result.get("intermediate_steps", [])
            )

            # Extract proposed SQL and next action from agent output
            output_text = result.get("output", "")
            proposed_sql = self._extract_proposed_sql(output_text, executed_steps)
            next_action = self._extract_next_action(output_text, proposed_sql)
            final_status = self._determine_final_status(proposed_sql, executed_steps, output_text)

            return ExecutionResult(
                original_context=context,
                selected_sop_title=selected_sop["title"],
                executed_steps=executed_steps,
                proposed_sql_action=proposed_sql,
                next_action_description=next_action,
                final_status=final_status
            )

        except Exception as e:
            # Handle execution errors
            error_step = StepExecutionDetail(
                step_description="Agent execution encountered an error",
                tool_called=None,
                tool_input=None,
                tool_output=str(e),
                status="Failure",
                summary=f"Error during execution: {str(e)}"
            )

            return ExecutionResult(
                original_context=context,
                selected_sop_title=selected_sop["title"],
                executed_steps=[error_step],
                proposed_sql_action=None,
                next_action_description=f"Execution failed with error: {str(e)}. Manual intervention required.",
                final_status="Failed"
            )

    def _process_intermediate_steps(self, intermediate_steps: List[tuple]) -> List[StepExecutionDetail]:
        """
        Process the intermediate steps from agent execution into StepExecutionDetail objects.

        Args:
            intermediate_steps: List of (AgentAction, observation) tuples

        Returns:
            List of StepExecutionDetail objects
        """
        processed_steps = []

        for i, (action, observation) in enumerate(intermediate_steps, 1):
            tool_name = action.tool if hasattr(action, 'tool') else None
            tool_input_raw = action.tool_input if hasattr(action, 'tool_input') else None

            # Ensure tool_input is a dictionary
            # LangChain sometimes passes strings directly, we need to wrap them
            if tool_input_raw is not None:
                if isinstance(tool_input_raw, dict):
                    tool_input = tool_input_raw
                elif isinstance(tool_input_raw, str):
                    # Wrap string input in a dictionary
                    tool_input = {"input": tool_input_raw}
                else:
                    # Convert other types to dict
                    tool_input = {"value": str(tool_input_raw)}
            else:
                tool_input = None

            # Determine status based on observation
            if observation and "error" not in str(observation).lower():
                status = "Success"
                summary = f"Step {i}: Used {tool_name}"
            else:
                status = "Failure"
                summary = f"Step {i}: {tool_name} failed"

            # Check if this is a generate_sql_update_statement call
            if tool_name == "generate_sql_update_statement":
                status = "Pending Manual Action"
                summary = f"Step {i}: Generated SQL for manual execution"

            step = StepExecutionDetail(
                step_description=f"Step {i}: {action.log if hasattr(action, 'log') else 'Execute tool'}",
                tool_called=tool_name,
                tool_input=tool_input,
                tool_output=observation,
                status=status,
                summary=summary
            )

            processed_steps.append(step)

        return processed_steps

    def _extract_proposed_sql(self, output_text: str, executed_steps: List[StepExecutionDetail]) -> Optional[str]:
        """Extract proposed SQL statement from agent output or executed steps."""
        # Check executed steps for SQL generation
        for step in executed_steps:
            if step.tool_called == "generate_sql_update_statement" and step.tool_output:
                return str(step.tool_output)

        # Also check in the output text
        if "UPDATE" in output_text.upper() or "DELETE" in output_text.upper():
            # Try to extract SQL from output
            lines = output_text.split('\n')
            sql_lines = []
            in_sql = False

            for line in lines:
                if any(kw in line.upper() for kw in ['UPDATE', 'DELETE', 'INSERT']):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if ';' in line:
                        break

            if sql_lines:
                return '\n'.join(sql_lines).strip()

        return None

    def _extract_next_action(self, output_text: str, proposed_sql: Optional[str]) -> str:
        """Extract next action description from agent output."""
        if proposed_sql:
            return "Execute the proposed SQL statement after manual review and approval."

        # Look for explicit next action in output
        if "escalate" in output_text.lower():
            return "Escalate to L3 support for further investigation."

        if "completed" in output_text.lower() or "success" in output_text.lower():
            return "SOP execution completed successfully. Verify the resolution with the customer."

        return "Review the execution steps and determine appropriate next action."

    def _determine_final_status(
        self,
        proposed_sql: Optional[str],
        executed_steps: List[StepExecutionDetail],
        output_text: str
    ) -> str:
        """Determine the final execution status."""
        if proposed_sql:
            return "Requires Manual Confirmation"

        if any(step.status == "Failure" for step in executed_steps):
            return "Failed"

        if "escalate" in output_text.lower():
            return "Escalation Required"

        if all(step.status == "Success" for step in executed_steps):
            return "Completed Successfully"

        return "Ambiguous"
