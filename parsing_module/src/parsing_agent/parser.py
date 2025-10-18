"""
LangChain-based incident report parser using OpenAI API.

This module provides functionality to parse raw incident reports from various
sources (Email, SMS, Call transcripts) into structured Pydantic objects using
LangChain and OpenAI's language models.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from .models import IncidentReport, ParsingError


# Load environment variables from .env file
load_dotenv()


class IncidentReportParser:
    """
    Parser for incident reports using LangChain and OpenAI.

    This class encapsulates the LangChain pipeline for parsing raw incident
    reports into structured IncidentReport objects.
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment_name: Optional[str] = None
    ):
        """
        Initialize the incident report parser.

        Args:
            model_name: Model deployment name for Azure OpenAI (default: gpt-4o)
            temperature: Sampling temperature (0.0 for deterministic, higher for creative)
            api_key: Azure OpenAI API key (if not provided, reads from AZURE_OPENAI_API_KEY env var)
            azure_endpoint: Azure OpenAI endpoint URL (if not provided, reads from AZURE_OPENAI_ENDPOINT env var)
            api_version: Azure OpenAI API version (if not provided, reads from AZURE_OPENAI_API_VERSION env var, defaults to "2024-02-15-preview")
            deployment_name: Azure deployment name (if not provided, uses model_name or reads from AZURE_OPENAI_DEPLOYMENT env var)

        Raises:
            ValueError: If required Azure credentials are not provided
        """
        # Get Azure credentials from parameters or environment
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT") or model_name

        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key must be provided either via api_key parameter "
                "or AZURE_OPENAI_API_KEY environment variable"
            )

        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint must be provided either via azure_endpoint parameter "
                "or AZURE_OPENAI_ENDPOINT environment variable"
            )

        # Initialize the output parser with the IncidentReport model
        self.output_parser = PydanticOutputParser(pydantic_object=IncidentReport)

        # Initialize Azure OpenAI LLM
        self.llm = AzureChatOpenAI(
            azure_deployment=self.deployment_name,
            api_version=self.api_version,
            temperature=temperature,
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key
        )

        # Create the prompt template
        self.prompt = self._create_prompt_template()

        # Build the LangChain Expression Language (LCEL) chain
        self.chain = self.prompt | self.llm | self.output_parser

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """
        Create the ChatPromptTemplate for incident report parsing.

        Returns:
            ChatPromptTemplate configured for incident parsing
        """
        system_message = """You are an expert NLP parser specialized in extracting structured information from IT incident reports for PORTNET®, a critical B2B port community system.

Your task is to analyze raw incident reports from various sources (Email, SMS, Call transcripts) and extract key information with high accuracy and consistency."""

        human_message = """Parse the following incident report and extract structured information.

**Source Type:** {source_type}

**Raw Text:**
{raw_text}

**Instructions:**

1. **Extract Entities**: Identify and extract the following entity types with their values:
   - **container_number**: ISO container numbers (e.g., CMAU1234567, TEMU9876543)
   - **vessel_name**: Vessel names (e.g., MAERSK VENTURE, MSC LORETTA)
   - **vessel_imo**: IMO numbers (e.g., IMO 9234567)
   - **user_id**: Email addresses or user identifiers
   - **error_code**: Specific error codes (e.g., VESSEL_ERR_4, EDI_ERR_1, CONTAINER_404)
   - **message_type**: EDI message types (e.g., COPARN, COARRI, CODECO, IFTMCS, IFTMIN)
   - **correlation_id**: System correlation/transaction IDs
   - **system_name**: Affected systems or services (e.g., TOS, CMS, DG-BOT)
   - **timestamp**: Any specific timestamps mentioned
   - **port_code**: Port codes (e.g., SGSIN)

2. **Infer Affected Module**: Determine the primary affected module:
   - **Container**: Issues related to container tracking, status, gate operations
   - **Vessel**: Issues with vessel registry, berth applications, vessel advice
   - **EDI/API**: Issues with EDI message processing, API events, integrations

3. **Infer Urgency**: Classify urgency based on:
   - **High**: Keywords like "urgent", "critical", "production down", "blocking", "immediate"; affects multiple users/systems; financial impact
   - **Medium**: Standard operational issues, single user/container affected, workarounds available
   - **Low**: Informational, questions, enhancement requests, historical data queries

4. **Extract Problem Summary**: Provide a clear, concise 1-2 sentence summary of the core issue.

5. **Identify Potential Causes**: Look for hints about root causes such as:
   - Timestamp mismatches or date/time issues
   - Database errors (timeouts, constraint violations)
   - Network/connectivity issues
   - Data validation failures
   - Integration/synchronization problems
   - Missing or incorrect data

6. **Extract Metadata**:
   - incident_id: Any reference number mentioned (ALR-*, INC-*, TCK-*, etc.)
   - reported_timestamp_hint: Time indicators ("this morning", "2 hours ago", "14:30", etc.)

{format_instructions}

Provide the output in the exact JSON format specified above."""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])

    def parse(
        self,
        source_type: str,
        raw_text: str,
        received_timestamp: Optional[datetime] = None
    ) -> IncidentReport:
        """
        Parse a raw incident report into a structured IncidentReport object.

        Args:
            source_type: Source of the report ("Email", "SMS", or "Call")
            raw_text: The raw text content of the incident report
            received_timestamp: When the report was received (defaults to current UTC time)

        Returns:
            Validated IncidentReport object

        Raises:
            ParsingError: If parsing fails or output doesn't match expected schema
            ValueError: If source_type is invalid
        """
        # Validate source_type
        valid_sources = ["Email", "SMS", "Call"]
        if source_type not in valid_sources:
            raise ValueError(
                f"Invalid source_type '{source_type}'. Must be one of: {valid_sources}"
            )

        # Generate timestamp if not provided
        if received_timestamp is None:
            received_timestamp = datetime.now(timezone.utc)

        received_timestamp_str = received_timestamp.isoformat().replace("+00:00", "Z")

        try:
            # Invoke the LangChain pipeline
            result = self.chain.invoke({
                "source_type": source_type,
                "raw_text": raw_text,
                "format_instructions": self.output_parser.get_format_instructions()
            })

            # The result is already a validated IncidentReport object from PydanticOutputParser
            # Ensure the metadata fields are set correctly
            result.source_type = source_type
            result.received_timestamp_utc = received_timestamp_str
            result.raw_text = raw_text

            return result

        except OutputParserException as e:
            raise ParsingError(
                f"Failed to parse LLM output into IncidentReport structure: {str(e)}"
            ) from e
        except Exception as e:
            raise ParsingError(
                f"Unexpected error during incident report parsing: {str(e)}"
            ) from e


# Convenience function for one-off parsing
def parse_incident_report(
    source_type: str,
    raw_text: str,
    model_name: str = "gpt-4o",
    api_key: Optional[str] = None
) -> IncidentReport:
    """
    Parse an incident report using default settings.

    This is a convenience function that creates a parser instance and
    parses the report in one call.

    Args:
        source_type: Source of the report ("Email", "SMS", or "Call")
        raw_text: The raw text content of the incident report
        model_name: OpenAI model to use (default: gpt-4o)
        api_key: OpenAI API key (optional, reads from env if not provided)

    Returns:
        Validated IncidentReport object

    Raises:
        ParsingError: If parsing fails
        ValueError: If source_type is invalid or API key is missing

    Example:
        >>> report = parse_incident_report(
        ...     source_type="Email",
        ...     raw_text="Subject: Container CMAU1234567 not found\\n\\nGetting error CONTAINER_404..."
        ... )
        >>> print(report.problem_summary)
        'Container CMAU1234567 not found in the system'
    """
    parser = IncidentReportParser(model_name=model_name, api_key=api_key)
    return parser.parse(source_type=source_type, raw_text=raw_text)
