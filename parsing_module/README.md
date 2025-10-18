# Incident Report Parsing Module

AI-powered incident report parser for PORTNET® support system using LangChain and OpenAI.

## Overview

This module parses raw incident reports from multiple sources (Email, SMS, Call transcripts) and extracts structured information including:
- Incident metadata (ID, timestamp, urgency)
- Affected systems and modules
- Extracted entities (containers, vessels, error codes, users)
- Problem summaries
- Potential root cause hints

## Project Structure

```
parsing_module/
├── src/
│   └── parsing_agent/
│       ├── __init__.py          # Package exports
│       ├── models.py            # Pydantic data models
│       └── parser.py            # LangChain implementation
├── tests/
│   ├── __init__.py
│   └── test_parser.py           # Unit tests with mocked OpenAI
├── .env                         # Environment variables (API keys)
├── .env.example                 # Template for .env file
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd parsing_module
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Optional variables:
```env
OPENAI_MODEL=gpt-4o          # Default model to use
OPENAI_TEMPERATURE=0.0       # Temperature for deterministic output
```

## Usage

### Basic Usage

```python
from parsing_agent import parse_incident_report

# Parse an email incident report
raw_text = """
Subject: URGENT - Container not found

Container CMAU1234567 showing CONTAINER_404 error.
User: john.doe@psa.com
"""

report = parse_incident_report(
    source_type="Email",
    raw_text=raw_text
)

print(f"Urgency: {report.urgency}")
print(f"Affected Module: {report.affected_module}")
print(f"Summary: {report.problem_summary}")
print(f"Entities: {report.entities}")
```

### Advanced Usage

```python
from parsing_agent import IncidentReportParser
from datetime import datetime, timezone

# Create a parser instance with custom settings
parser = IncidentReportParser(
    model_name="gpt-4o",
    temperature=0.0
)

# Parse with custom timestamp
report = parser.parse(
    source_type="SMS",
    raw_text="ALR-12345: VESSEL_ERR_4 for MV PACIFIC DREAM",
    received_timestamp=datetime(2025, 10, 18, 10, 0, 0, tzinfo=timezone.utc)
)

# Access structured data
print(f"Incident ID: {report.incident_id}")
print(f"Error Code: {report.error_code}")
for entity in report.entities:
    print(f"  {entity.type}: {entity.value}")
```

### Error Handling

```python
from parsing_agent import parse_incident_report, ParsingError

try:
    report = parse_incident_report("Email", raw_text)
except ParsingError as e:
    print(f"Failed to parse report: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
```

## Data Models

### IncidentReport

Main output model with the following fields:

- `incident_id` (Optional[str]): Extracted incident/ticket ID
- `source_type` (Literal["Email", "SMS", "Call"]): Source channel
- `received_timestamp_utc` (str): Processing timestamp (ISO 8601)
- `reported_timestamp_hint` (Optional[str]): Time indicator from text
- `urgency` (Literal["High", "Medium", "Low"]): Inferred priority
- `affected_module` (Optional[Literal["Container", "Vessel", "EDI/API"]]): System module
- `entities` (List[Entity]): Extracted key entities
- `error_code` (Optional[str]): Specific error code
- `problem_summary` (str): Concise issue description
- `potential_cause_hint` (Optional[str]): Root cause indicators
- `raw_text` (str): Original input text

### Entity

Represents extracted entities:

- `type` (str): Entity category (e.g., "container_number", "vessel_name")
- `value` (str): Entity value (e.g., "CMAU1234567")

## Testing

Run the test suite using pytest:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/parsing_agent --cov-report=html

# Run specific test file
pytest tests/test_parser.py

# Run specific test
pytest tests/test_parser.py::TestIncidentReportParser::test_parse_email_container_not_found

# Run with verbose output
pytest -v
```

The tests use mocked OpenAI API calls, so they run fast and don't incur API costs.

## Development

### Adding New Entity Types

To extract additional entity types, update the prompt in `parser.py`:

```python
# In _create_prompt_template method, add to entity types list:
- **new_entity_type**: Description and examples
```

### Customizing Urgency Classification

Modify the urgency inference logic in the prompt template:

```python
# Update the "Infer Urgency" section with new criteria
```

### Extending the Data Model

1. Add new fields to `IncidentReport` in `models.py`
2. Update the prompt to instruct the LLM to extract the new fields
3. Add test cases covering the new fields

## Performance Considerations

- **API Costs**: Each parsing call uses the OpenAI API. Monitor usage via OpenAI dashboard.
- **Model Selection**:
  - `gpt-4o`: Best accuracy, higher cost
  - `gpt-3.5-turbo`: Faster, lower cost, slightly less accurate
- **Caching**: Consider implementing caching for repeated identical inputs
- **Batch Processing**: For high volumes, consider batching requests

## Troubleshooting

### "OpenAI API key must be provided" Error
- Ensure `.env` file exists and contains `OPENAI_API_KEY`
- Verify the API key is valid at https://platform.openai.com/api-keys

### Parsing Failures
- Check if the input text has sufficient information
- Review the error message for specific parsing issues
- Try with a more capable model (e.g., upgrade from gpt-3.5-turbo to gpt-4o)

### Import Errors
- Ensure you've installed dependencies: `pip install -r requirements.txt`
- Verify you're in the correct virtual environment
- Check that the `src` directory is in your Python path

## Contributing

When adding new features:

1. Update the Pydantic models in `models.py`
2. Modify the parser logic in `parser.py`
3. Add comprehensive unit tests in `tests/test_parser.py`
4. Update this README with usage examples

## License

This module is part of the PORTNET® incident management system.
