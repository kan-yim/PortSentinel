# Project Structure

```
parsing_module/
├── .env                         # Environment variables (API keys) - DO NOT COMMIT
├── .env.example                 # Template for .env file
├── .gitignore                   # Git ignore rules
├── README.md                    # Main documentation
├── PROJECT_STRUCTURE.md         # This file
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── example_usage.py             # Usage examples and demos
│
├── src/
│   └── parsing_agent/
│       ├── __init__.py          # Package exports
│       ├── models.py            # Pydantic models (IncidentReport, Entity)
│       └── parser.py            # LangChain + OpenAI implementation
│
└── tests/
    ├── __init__.py
    └── test_parser.py           # Unit tests with mocked OpenAI API
```

## File Descriptions

### Configuration Files

- **.env**: Stores sensitive configuration (OpenAI API key). Never commit this file.
- **.env.example**: Template showing required environment variables.
- **.gitignore**: Specifies files Git should ignore (virtual envs, cache, .env, etc.).
- **pytest.ini**: Configures pytest behavior and coverage settings.
- **requirements.txt**: Lists all Python package dependencies.

### Documentation

- **README.md**: Complete usage guide, installation instructions, and API documentation.
- **PROJECT_STRUCTURE.md**: This file - explains the project layout.

### Source Code

- **src/parsing_agent/__init__.py**: Exports public API (IncidentReport, parse_incident_report, etc.).
- **src/parsing_agent/models.py**: Pydantic data models for structured incident reports.
- **src/parsing_agent/parser.py**: Core parsing logic using LangChain and OpenAI.

### Tests

- **tests/__init__.py**: Makes tests directory a Python package.
- **tests/test_parser.py**: Comprehensive unit tests with mocked API calls.

### Examples

- **example_usage.py**: Demonstrates how to use the parser with sample incidents.

## Key Components

### 1. Pydantic Models (models.py)

Defines the data structures:
- `Entity`: Represents extracted entities (type, value)
- `IncidentReport`: Main output structure with all parsed fields
- `ParsingError`: Custom exception for parsing failures

### 2. Parser (parser.py)

Contains:
- `IncidentReportParser`: Main class with LangChain pipeline
- `parse_incident_report()`: Convenience function for quick parsing

### 3. Tests (test_parser.py)

Includes:
- Parser initialization tests
- Email/SMS/Call parsing scenarios
- Error handling tests
- Integration-style tests with realistic data

## Development Workflow

1. **Setup**: Install dependencies, configure .env
2. **Development**: Modify code in src/parsing_agent/
3. **Testing**: Run pytest to verify changes
4. **Usage**: Import and use in your application

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Configure API key in .env file
3. Run tests: `pytest`
4. Try examples: `python example_usage.py`
