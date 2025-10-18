"""
Tools for Agent 3: SOP Executor Agent.

This module defines LangChain tools that the agent can use to execute
SOP steps, including checking logs, querying databases, and generating
SQL statements for manual execution.
"""

from typing import Dict, List, Optional, Any
from langchain.tools import tool
import re


# Placeholder for log checking functionality
@tool
def check_log(log_file: str, pattern: str) -> str:
    """
    Searches a specified log file for lines matching a given pattern, similar to grep.

    Args:
        log_file: Name of the log file to search (e.g., 'vessel_advice_service.log')
        pattern: Pattern to search for (e.g., 'VESSEL_ERR_4', 'ERROR')

    Returns:
        A summary of matching lines or indication that the search was performed.

    Example:
        check_log("vessel_advice_service.log", "VESSEL_ERR_4")
    """
    # Placeholder implementation
    # In production, this would:
    # 1. Connect to log aggregation system (e.g., ELK, Splunk)
    # 2. Search for the pattern in the specified log file
    # 3. Return matching lines with timestamps

    return f"Searched {log_file} for pattern '{pattern}'. [Placeholder: In production, this would return actual log entries matching the pattern]"


@tool
def execute_sql_query(query: str, params: Optional[str] = None) -> str:
    """
    Executes a SQL SELECT query against the database using named parameters.

    **IMPORTANT**: This tool is for SELECT queries only. For UPDATE/DELETE operations,
    use generate_sql_update_statement instead.

    Args:
        query: SQL SELECT query with named parameters (e.g., 'SELECT * FROM vessel_advice WHERE system_vessel_name = :system_vessel_name')
        params: JSON string of parameters (e.g., '{"system_vessel_name": "LIONCITY07"}')

    Returns:
        JSON string containing the query results as a list of dictionaries.

    Example:
        execute_sql_query(
            "SELECT * FROM vessel_advice WHERE system_vessel_name = :name",
            '{"name": "LIONCITY07"}'
        )
    """
    # This tool will be bound with the actual DatabaseInterface instance
    # The implementation will be injected when creating the agent
    # This is a placeholder signature for the LangChain tool decorator

    return "This tool requires DatabaseInterface binding. See agent.py for implementation."


@tool
def generate_sql_update_statement(sql_template: str, params: str) -> str:
    """
    **Safely generates** a SQL UPDATE or DELETE statement based on a template from the SOP
    and provided parameters. **DOES NOT execute the SQL.**

    This tool is used for database modification operations that require manual approval.
    The generated SQL statement must be reviewed and executed by a human operator.

    Args:
        sql_template: SQL template with named parameters (e.g., 'UPDATE vessel_advice SET effective_end_datetime = :timestamp WHERE vessel_advice_no = :vessel_advice_no')
        params: JSON string of parameters (e.g., '{"timestamp": "2025-10-18 00:00:00", "vessel_advice_no": 123}')

    Returns:
        The formatted SQL statement ready for manual review and execution.

    Example:
        generate_sql_update_statement(
            "UPDATE vessel_advice SET effective_end_datetime = :ts WHERE vessel_advice_no = :id",
            '{"ts": "2025-10-18 00:00:00", "id": 123}'
        )
    """
    import json

    # Parse parameters
    try:
        if params:
            params_dict = json.loads(params) if isinstance(params, str) else params
        else:
            params_dict = {}
    except json.JSONDecodeError:
        return f"ERROR: Invalid JSON in params: {params}"

    # Replace named parameters in the SQL template
    formatted_sql = sql_template

    for param_name, param_value in params_dict.items():
        # Handle different types of values
        if isinstance(param_value, str):
            # Escape single quotes and wrap in quotes
            safe_value = param_value.replace("'", "''")
            replacement = f"'{safe_value}'"
        elif param_value is None:
            replacement = "NULL"
        elif isinstance(param_value, (int, float)):
            replacement = str(param_value)
        else:
            # For other types, convert to string
            replacement = f"'{str(param_value)}'"

        # Replace :param_name with the actual value
        formatted_sql = formatted_sql.replace(f":{param_name}", replacement)

    # Add semicolon if not present
    if not formatted_sql.strip().endswith(';'):
        formatted_sql += ';'

    return formatted_sql


# Additional utility function (not a tool) for parameter extraction
def extract_params_from_context(context_data: Dict[str, Any], param_names: List[str]) -> Dict[str, Any]:
    """
    Helper function to extract parameter values from context data.

    Args:
        context_data: Dictionary containing context information
        param_names: List of parameter names to extract

    Returns:
        Dictionary of extracted parameters
    """
    extracted = {}

    for param in param_names:
        # Try to find the parameter in various places in the context
        if param in context_data:
            extracted[param] = context_data[param]
        # Add more extraction logic as needed

    return extracted
