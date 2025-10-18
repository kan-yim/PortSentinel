# Quick Start Guide

Get up and running with the Incident Report Parser in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- OpenAI API key (get one at https://platform.openai.com/api-keys)

## Installation Steps

### 1. Navigate to the Project Directory

```bash
cd /Users/kanyim/portsentinel/parsing_module
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langchain` and `langchain-openai` for LLM integration
- `pydantic` for data validation
- `python-dotenv` for environment variable management
- `pytest` for testing

### 4. Configure Your API Key

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Replace 'your_openai_api_key_here' with your actual key
nano .env  # or use your preferred editor
```

Your `.env` file should look like:
```
OPENAI_API_KEY=sk-proj-abc123...your-actual-key
```

### 5. Verify Installation

Run the tests to verify everything is working:

```bash
pytest -v
```

You should see output like:
```
tests/test_parser.py::TestIncidentReportParser::test_parser_initialization_with_api_key PASSED
tests/test_parser.py::TestIncidentReportParser::test_parse_email_container_not_found PASSED
...
========================= X passed in Y.YYs =========================
```

## Quick Test

Create a simple test file to verify the parser works:

```python
# test_quick.py
from parsing_agent import parse_incident_report

raw_text = """
Subject: Container Error

Container CMAU1234567 not found. Error: CONTAINER_404
Contact: user@example.com
"""

report = parse_incident_report("Email", raw_text)

print(f"Urgency: {report.urgency}")
print(f"Summary: {report.problem_summary}")
print(f"Entities: {len(report.entities)} found")
for entity in report.entities:
    print(f"  - {entity.type}: {entity.value}")
```

Run it:
```bash
python test_quick.py
```

## Next Steps

1. **Read the README**: See `README.md` for detailed documentation
2. **Try Examples**: Run `python example_usage.py` (after uncommenting examples)
3. **Integrate**: Import `parse_incident_report` in your own code

## Troubleshooting

### "No module named 'pydantic'"
- Make sure you activated the virtual environment
- Run `pip install -r requirements.txt` again

### "OpenAI API key must be provided"
- Check that `.env` file exists in the project root
- Verify the API key is correctly formatted (starts with `sk-`)
- Ensure you're running from the correct directory

### Tests Fail
- If running without installing: Use `PYTHONPATH=src pytest`
- If API-related failures: Tests should use mocked API, check pytest output

### Import Errors
```bash
# If imports don't work, try:
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or use the pytest.ini configuration (already set up)
```

## Project Structure

```
parsing_module/
├── src/parsing_agent/     # Source code
├── tests/                 # Unit tests
├── .env                   # Your API key (create this)
├── requirements.txt       # Dependencies
└── README.md             # Full documentation
```

## Usage Example

```python
from parsing_agent import parse_incident_report

# Parse any incident report
report = parse_incident_report(
    source_type="Email",  # or "SMS" or "Call"
    raw_text="Your incident text here..."
)

# Access structured data
print(report.urgency)           # "High", "Medium", or "Low"
print(report.affected_module)   # "Container", "Vessel", or "EDI/API"
print(report.problem_summary)   # Concise description
print(report.entities)          # List of extracted entities
```

That's it! You're ready to start parsing incident reports. 🚀
