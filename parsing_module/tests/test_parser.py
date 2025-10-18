"""
Unit tests for the incident report parser.

These tests use mocked OpenAI API calls to ensure reproducible and
fast test execution without incurring API costs.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timezone

from parsing_agent.parser import IncidentReportParser, parse_incident_report
from parsing_agent.models import IncidentReport, Entity, ParsingError


class TestIncidentReportParser:
    """Test suite for IncidentReportParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance with mocked API key."""
        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-api-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4o'
        }):
            return IncidentReportParser(model_name="gpt-4o", temperature=0.0)

    @pytest.fixture
    def fixed_timestamp(self):
        """Fixed timestamp for consistent testing."""
        return datetime(2025, 10, 18, 10, 30, 0, tzinfo=timezone.utc)

    def test_parser_initialization_with_api_key(self):
        """Test parser initializes correctly with API key in environment."""
        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key-123',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4o'
        }):
            parser = IncidentReportParser()
            assert parser.api_key == 'test-key-123'
            assert parser.llm is not None
            assert parser.output_parser is not None

    def test_parser_initialization_without_api_key(self):
        """Test parser raises error when API key is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Azure OpenAI API key must be provided"):
                IncidentReportParser()

    def test_parser_initialization_with_custom_model(self):
        """Test parser initializes with custom model name."""
        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-35-turbo'
        }):
            parser = IncidentReportParser(model_name="gpt-35-turbo")
            assert parser.deployment_name == "gpt-35-turbo"

    def test_parse_email_container_not_found(self, parser, fixed_timestamp):
        """Test parsing email about container not found error."""
        # Sample input
        source_type = "Email"
        raw_text = """Subject: URGENT - Container not found

Hi support team,

This morning around 9am, I tried to update the status of container CMAU1234567
but got error CONTAINER_404. The container should be in the yard after gate-in
yesterday. Can you please check?

User: john.doe@psa.com
Ticket: INC-98765"""

        # Expected output structure
        expected_incident = IncidentReport(
            incident_id="INC-98765",
            source_type="Email",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            reported_timestamp_hint="this morning around 9am",
            urgency="High",
            affected_module="Container",
            entities=[
                Entity(type="container_number", value="CMAU1234567"),
                Entity(type="error_code", value="CONTAINER_404"),
                Entity(type="user_id", value="john.doe@psa.com")
            ],
            error_code="CONTAINER_404",
            problem_summary="Container CMAU1234567 not found in the system when attempting to update status.",
            potential_cause_hint="Container may not have been properly registered during gate-in",
            raw_text=raw_text
        )

        # Mock the chain by replacing its invoke method
        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(return_value=expected_incident)

        try:
            result = parser.parse(source_type, raw_text, received_timestamp=fixed_timestamp)

            # Assertions
            assert isinstance(result, IncidentReport)
            assert result.incident_id == "INC-98765"
            assert result.source_type == "Email"
            assert result.urgency == "High"
            assert result.affected_module == "Container"
            assert result.error_code == "CONTAINER_404"
            assert len(result.entities) == 3
            assert result.raw_text == raw_text
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_sms_vessel_timestamp_error(self, parser, fixed_timestamp):
        """Test parsing SMS about vessel timestamp error."""
        source_type = "SMS"
        raw_text = """ALR-77123: VESSEL_ERR_4 for MV PACIFIC DREAM (IMO 9876543).
Effective start datetime before current datetime. Duty officer please check vessel_advice table."""

        expected_incident = IncidentReport(
            incident_id="ALR-77123",
            source_type="SMS",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            reported_timestamp_hint=None,
            urgency="High",
            affected_module="Vessel",
            entities=[
                Entity(type="error_code", value="VESSEL_ERR_4"),
                Entity(type="vessel_name", value="MV PACIFIC DREAM"),
                Entity(type="vessel_imo", value="IMO 9876543"),
                Entity(type="system_name", value="vessel_advice")
            ],
            error_code="VESSEL_ERR_4",
            problem_summary="Vessel advice for MV PACIFIC DREAM has effective start datetime that is before the current datetime.",
            potential_cause_hint="Timestamp validation error - effective start datetime is in the past",
            raw_text=raw_text
        )

        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(return_value=expected_incident)

        try:
            result = parser.parse(source_type, raw_text, received_timestamp=fixed_timestamp)

            assert result.incident_id == "ALR-77123"
            assert result.source_type == "SMS"
            assert result.urgency == "High"
            assert result.affected_module == "Vessel"
            assert result.error_code == "VESSEL_ERR_4"
            assert "timestamp" in result.potential_cause_hint.lower()
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_call_transcript_edi_error(self, parser, fixed_timestamp):
        """Test parsing call transcript about EDI processing error."""
        source_type = "Call"
        raw_text = """[Call Transcript - 14:35:22]

Caller: Hi, we're getting EDI_ERR_1 errors on multiple IFTMIN messages sent in the last hour.

Agent: Can you provide the message reference?

Caller: Yes, REF-IFT-0007 sent from LINE-PSA to PSA-TOS. The error says "Segment missing".
This is blocking our vessel discharge operations.

Agent: Understood. I'll escalate this immediately. Ticket TCK-44521."""

        expected_incident = IncidentReport(
            incident_id="TCK-44521",
            source_type="Call",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            reported_timestamp_hint="in the last hour",
            urgency="High",
            affected_module="EDI/API",
            entities=[
                Entity(type="error_code", value="EDI_ERR_1"),
                Entity(type="message_type", value="IFTMIN"),
                Entity(type="correlation_id", value="REF-IFT-0007"),
                Entity(type="system_name", value="LINE-PSA"),
                Entity(type="system_name", value="PSA-TOS")
            ],
            error_code="EDI_ERR_1",
            problem_summary="Multiple IFTMIN messages failing with EDI_ERR_1 error due to missing segment, blocking vessel discharge operations.",
            potential_cause_hint="Data validation failure - required segment missing from EDI message",
            raw_text=raw_text
        )

        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(return_value=expected_incident)

        try:
            result = parser.parse(source_type, raw_text, received_timestamp=fixed_timestamp)

            assert result.incident_id == "TCK-44521"
            assert result.source_type == "Call"
            assert result.urgency == "High"
            assert result.affected_module == "EDI/API"
            assert result.error_code == "EDI_ERR_1"
            assert "blocking" in result.problem_summary.lower()
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_low_urgency_query(self, parser, fixed_timestamp):
        """Test parsing low-urgency informational query."""
        source_type = "Email"
        raw_text = """Subject: Question about container statuses

Hi team,

Could you help me understand what the different container statuses mean?
I see TRANSHIP, IN_YARD, and GATE_OUT in the system but I'm not sure when
each status is used.

Thanks,
Mary from Operations"""

        expected_incident = IncidentReport(
            incident_id=None,
            source_type="Email",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            reported_timestamp_hint=None,
            urgency="Low",
            affected_module="Container",
            entities=[
                Entity(type="user_id", value="Mary"),
                Entity(type="system_name", value="container statuses")
            ],
            error_code=None,
            problem_summary="User requesting clarification on the meaning and usage of different container status values in the system.",
            potential_cause_hint=None,
            raw_text=raw_text
        )

        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(return_value=expected_incident)

        try:
            result = parser.parse(source_type, raw_text, received_timestamp=fixed_timestamp)

            assert result.incident_id is None
            assert result.urgency == "Low"
            assert result.error_code is None
            assert "clarification" in result.problem_summary.lower() or "question" in result.problem_summary.lower()
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_with_missing_optional_fields(self, parser, fixed_timestamp):
        """Test parsing when many optional fields are absent."""
        source_type = "SMS"
        raw_text = "System running slow. Please check."

        expected_incident = IncidentReport(
            incident_id=None,
            source_type="SMS",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            reported_timestamp_hint=None,
            urgency="Medium",
            affected_module=None,
            entities=[],
            error_code=None,
            problem_summary="General system performance issue - system running slow.",
            potential_cause_hint=None,
            raw_text=raw_text
        )

        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(return_value=expected_incident)

        try:
            result = parser.parse(source_type, raw_text, received_timestamp=fixed_timestamp)

            assert result.incident_id is None
            assert result.error_code is None
            assert result.affected_module is None
            assert result.entities == []
            assert result.urgency == "Medium"
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_invalid_source_type(self, parser):
        """Test that invalid source_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid source_type"):
            parser.parse(source_type="Twitter", raw_text="Some text")

    def test_parse_handles_parsing_exceptions(self, parser):
        """Test that parsing errors are properly caught and wrapped."""
        from langchain_core.exceptions import OutputParserException

        # Mock the chain to raise an OutputParserException
        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(side_effect=OutputParserException("Invalid JSON"))

        try:
            with pytest.raises(ParsingError, match="Failed to parse LLM output"):
                parser.parse("Email", "Some text")
        finally:
            parser.chain.invoke = original_invoke

    def test_parse_handles_unexpected_exceptions(self, parser):
        """Test that unexpected errors are caught and wrapped."""
        # Mock the chain to raise a generic exception
        original_invoke = parser.chain.invoke
        parser.chain.invoke = Mock(side_effect=RuntimeError("Network error"))

        try:
            with pytest.raises(ParsingError, match="Unexpected error"):
                parser.parse("Email", "Some text")
        finally:
            parser.chain.invoke = original_invoke


class TestConvenienceFunction:
    """Test suite for the parse_incident_report convenience function."""

    @patch('parsing_agent.parser.IncidentReportParser')
    def test_parse_incident_report_creates_parser(self, mock_parser_class):
        """Test that convenience function creates parser with correct parameters."""
        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance.parse.return_value = IncidentReport(
            source_type="Email",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            problem_summary="Test issue",
            raw_text="Test text"
        )

        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-35-turbo'
        }):
            result = parse_incident_report(
                source_type="Email",
                raw_text="Test text",
                model_name="gpt-35-turbo"
            )

        # Verify parser was created with correct parameters
        mock_parser_class.assert_called_once_with(model_name="gpt-35-turbo", api_key=None)
        # Verify parse was called
        mock_parser_instance.parse.assert_called_once_with(source_type="Email", raw_text="Test text")
        # Verify result
        assert isinstance(result, IncidentReport)

    @patch('parsing_agent.parser.IncidentReportParser')
    def test_parse_incident_report_with_custom_api_key(self, mock_parser_class):
        """Test convenience function with custom API key."""
        mock_parser_instance = MagicMock()
        mock_parser_class.return_value = mock_parser_instance
        mock_parser_instance.parse.return_value = IncidentReport(
            source_type="SMS",
            received_timestamp_utc="2025-10-18T10:30:00Z",
            problem_summary="Test issue",
            raw_text="Test text"
        )

        parse_incident_report(
            source_type="SMS",
            raw_text="Test text",
            api_key="custom-key-123"
        )

        # Verify parser was created with custom API key
        mock_parser_class.assert_called_once_with(model_name="gpt-4o", api_key="custom-key-123")


class TestIntegrationScenarios:
    """Integration-style tests with realistic scenarios."""

    @pytest.fixture
    def parser_with_env(self):
        """Create parser with environment-based API key."""
        with patch.dict('os.environ', {
            'AZURE_OPENAI_API_KEY': 'test-integration-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4o'
        }):
            return IncidentReportParser()

    def test_multiple_containers_issue(self, parser_with_env):
        """Test parsing incident affecting multiple containers."""
        raw_text = """Subject: CRITICAL - Multiple containers stuck in GATE_IN status

Priority: HIGH
Time: 2 hours ago

We have 15 containers that are stuck in GATE_IN status and not moving to IN_YARD.
Sample containers: CMAU1111111, TEMU2222222, MSCU3333333

Error log shows: "Database constraint violation on status transition"
Correlation ID: corr-abc-123

This is blocking truck operations at the gate.

Contact: ops.manager@terminal.com"""

        expected = IncidentReport(
            incident_id=None,
            source_type="Email",
            received_timestamp_utc="2025-10-18T12:00:00Z",
            reported_timestamp_hint="2 hours ago",
            urgency="High",
            affected_module="Container",
            entities=[
                Entity(type="container_number", value="CMAU1111111"),
                Entity(type="container_number", value="TEMU2222222"),
                Entity(type="container_number", value="MSCU3333333"),
                Entity(type="correlation_id", value="corr-abc-123"),
                Entity(type="user_id", value="ops.manager@terminal.com")
            ],
            error_code=None,
            problem_summary="15 containers stuck in GATE_IN status, unable to transition to IN_YARD, blocking truck operations at the gate.",
            potential_cause_hint="Database constraint violation on status transition",
            raw_text=raw_text
        )

        original_invoke = parser_with_env.chain.invoke
        parser_with_env.chain.invoke = Mock(return_value=expected)

        try:
            result = parser_with_env.parse("Email", raw_text)

            assert result.urgency == "High"
            assert result.affected_module == "Container"
            assert len([e for e in result.entities if e.type == "container_number"]) == 3
            assert "blocking" in result.problem_summary.lower()
        finally:
            parser_with_env.chain.invoke = original_invoke
