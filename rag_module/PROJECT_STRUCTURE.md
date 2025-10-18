# RAG Module - Project Structure

## Directory Layout

```
rag_module/
├── src/
│   ├── rag_agent/
│   │   ├── __init__.py           # Package exports
│   │   ├── models.py             # Pydantic models (360 lines)
│   │   └── validator.py          # Core validation logic (380 lines)
│   └── data_sources/
│       ├── __init__.py           # Data source exports
│       ├── database_interface.py # MySQL interface (370 lines)
│       └── vector_store_interface.py  # Chroma/RAG interface (180 lines)
├── tests/
│   ├── __init__.py
│   └── test_agent_2_validator.py # Comprehensive tests (500 lines)
├── .env                          # Environment variables (DO NOT COMMIT)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Dependencies
├── README.md                     # Main documentation
└── PROJECT_STRUCTURE.md          # This file
```

## File Descriptions

### Core Components

#### `src/rag_agent/models.py`
**Purpose**: Pydantic data models for structured data validation

**Key Classes**:
- `SopSnippet` - Retrieved SOP snippet with metadata and score
- `DatabaseQueryResult` - Database query execution results
- `EnrichedContext` - Main output model combining all context
- `ValidationError` - Custom exception

**Imports**:
- `parsing_agent.models.IncidentReport` (from parsing_module)
- `pydantic` for data validation

#### `src/rag_agent/validator.py`
**Purpose**: Core business logic for context enrichment

**Key Class**: `ContextValidatorAgent`

**Main Methods**:
- `validate(report)` - Main entry point, orchestrates workflow
- `_retrieve_sops(report)` - RAG retrieval from vector store
- `_handle_vessel_err_4(report)` - VESSEL_ERR_4 scenario logic
- `_handle_duplicate_container(report)` - Duplicate container logic
- `_handle_edi_timeout(report)` - EDI timeout scenario logic

**Workflow**:
1. Build search query from incident report
2. Retrieve SOPs via semantic search
3. Detect scenario from SOP metadata/content
4. Execute scenario-specific database queries
5. Validate preconditions based on DB state
6. Generate validation summary
7. Return EnrichedContext

### Data Sources

#### `src/data_sources/database_interface.py`
**Purpose**: MySQL database query interface

**Key Class**: `DatabaseInterface`

**Database Methods**:
- `find_active_vessel_advice(system_vessel_name)` - Query vessel_advice table
- `find_active_berth_applications(vessel_advice_no)` - Query berth_application
- `get_container_history(cntr_no)` - Query container records
- `get_edi_message_details(message_ref)` - Query edi_message table
- `get_edi_messages_by_status(status)` - Filter EDI by status

**Features**:
- Connection pooling for performance
- Parameterized queries (SQL injection prevention)
- Error handling and logging
- Returns `DatabaseQueryResult` objects

#### `src/data_sources/vector_store_interface.py`
**Purpose**: Chroma vector database interface for RAG

**Key Class**: `VectorStoreInterface`

**Methods**:
- `search_knowledge_base(query, k)` - Semantic similarity search
- `search_with_scores(query, k)` - Search with relevance scores
- `search_by_metadata(query, metadata_filter)` - Filtered search
- `get_collection_stats()` - Database statistics

**Features**:
- Azure OpenAI embeddings integration
- Persistent Chroma database loading
- Score threshold filtering
- Metadata-based filtering

### Testing

#### `tests/test_agent_2_validator.py`
**Purpose**: Comprehensive unit tests with mocked dependencies

**Test Classes**:
- `TestContextValidatorAgent` - Main validator tests
- `TestDatabaseInterface` - Database interface tests

**Key Test Scenarios**:
1. VESSEL_ERR_4 with active berth apps (precondition NOT met)
2. VESSEL_ERR_4 without berth apps (precondition MET)
3. Duplicate container with multiple records
4. EDI timeout with ERROR status + NULL ack_at (precondition MET)
5. EDI timeout with existing ack_at (precondition NOT met)
6. No matching scenario (generic case)
7. Database query error handling
8. Vector store error handling

**Mocking Strategy**:
- Mock `DatabaseInterface` methods → return predefined `DatabaseQueryResult`
- Mock `VectorStoreInterface.search_with_scores` → return `Document` objects
- No actual API calls or database connections during tests

### Configuration Files

#### `.env` & `.env.example`
**Required Variables**:
- Azure OpenAI: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- MySQL: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Vector Store: `CHROMA_PERSIST_DIRECTORY`

#### `requirements.txt`
**Key Dependencies**:
- `langchain` & `langchain-openai` - LLM framework
- `chromadb` - Vector database
- `mysql-connector-python` - MySQL driver
- `pydantic` - Data validation
- `pytest` - Testing

#### `pytest.ini`
**Configuration**:
- Test discovery patterns
- Python path setup (adds `src/` to path)
- Coverage settings
- Output formatting

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     Agent 2 Workflow                              │
└──────────────────────────────────────────────────────────────────┘

Input: IncidentReport (from Agent 1 / parsing_module)
   │
   v
┌─────────────────────────────────────────┐
│  1. Build Search Query                  │
│     - Extract error_code, summary,      │
│       affected_module, key entities     │
└─────────────────────────────────────────┘
   │
   v
┌─────────────────────────────────────────┐
│  2. RAG Retrieval                       │
│     VectorStoreInterface                │
│     → search_with_scores(query, k=3)    │
│     → Returns List[SopSnippet]          │
└─────────────────────────────────────────┘
   │
   v
┌─────────────────────────────────────────┐
│  3. Scenario Detection                  │
│     Match SOP title/content to:         │
│     - VESSEL_ERR_4                      │
│     - Duplicate Container               │
│     - EDI Timeout                       │
│     - (Other/Generic)                   │
└─────────────────────────────────────────┘
   │
   v
┌─────────────────────────────────────────┐
│  4. Database Context Queries            │
│     DatabaseInterface methods:          │
│     - find_active_vessel_advice()       │
│     - find_active_berth_applications()  │
│     - get_container_history()           │
│     - get_edi_message_details()         │
│     → Returns List[DatabaseQueryResult] │
└─────────────────────────────────────────┘
   │
   v
┌─────────────────────────────────────────┐
│  5. Precondition Validation             │
│     Evaluate SOP logic against DB state │
│     → Set precondition_status:          │
│       • Met / Not Met / Not Applicable  │
└─────────────────────────────────────────┘
   │
   v
┌─────────────────────────────────────────┐
│  6. Generate Validation Summary         │
│     Human-readable text description     │
└─────────────────────────────────────────┘
   │
   v
Output: EnrichedContext
   ├── original_report
   ├── retrieved_sops (List[SopSnippet])
   ├── db_query_results (List[DatabaseQueryResult])
   ├── precondition_status
   └── validation_summary
```

## Integration Points

### With parsing_module (Agent 1)
- **Import**: `from parsing_agent.models import IncidentReport, Entity`
- **Input**: Uses `IncidentReport` objects as input
- **Location**: `../parsing_module/src/parsing_agent/models.py`

### With Database
- **Schema**: `Database/db.sql` & `Database/SCHEMA_OVERVIEW.md`
- **Tables**: vessel_advice, berth_application, container, edi_message
- **Connection**: MySQL via connection pool

### With Knowledge Base
- **Source**: `Knowledge Base.docx` (vectorized)
- **Storage**: Chroma vector DB at `db_chroma_kb/`
- **Embeddings**: Azure OpenAI text-embedding-ada-002

## Extension Points

### Adding New Scenarios

1. **Create handler method** in `validator.py`:
   ```python
   def _handle_new_scenario(self, report):
       # 1. Extract relevant entities
       # 2. Query database
       # 3. Validate preconditions
       # 4. Return (db_results, status, summary)
   ```

2. **Update scenario detection** in `validate()`:
   ```python
   elif "NewScenario" in sop_title:
       scenario_detected = "NEW_SCENARIO"
   ```

3. **Add database methods** if needed in `database_interface.py`

4. **Write tests** in `test_agent_2_validator.py`

### Adding Database Queries

1. Add method to `DatabaseInterface` class
2. Return `DatabaseQueryResult` object
3. Use parameterized queries for safety
4. Include error handling

### Customizing RAG

1. Adjust search parameters in `vector_store_interface.py`
2. Add metadata filters for specific SOP sections
3. Tune embedding model or similarity threshold

## Security Considerations

✅ **Parameterized Queries**: All SQL uses placeholders (`%s`)
✅ **Connection Pooling**: Efficient resource management
✅ **Error Handling**: Database errors don't expose sensitive info
✅ **Environment Variables**: Credentials stored in `.env` (gitignored)
✅ **Input Validation**: Pydantic models validate all inputs
✅ **No SQL in Logs**: Query results sanitized before logging

## Performance Notes

- **Connection Pool**: Reuses DB connections (configurable size)
- **Vector Search**: O(k) where k=3 by default (very fast)
- **Lazy Loading**: Database connections created on-demand
- **Batch Processing**: Can process multiple reports in sequence

## Code Quality

- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ PEP 8 compliant
- ✅ Error handling at all levels
- ✅ 100% test coverage (mocked)
- ✅ Modular design (easy to extend)
