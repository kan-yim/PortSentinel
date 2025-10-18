# RAG Module - SOP Retrieval Agent

AI-powered SOP retrieval for PORTNET® incident resolution using RAG (Retrieval-Augmented Generation).

## Overview

This module implements **Agent 2** in the incident management workflow:

1. **Agent 1** (`parsing_module`) parses raw incident reports → structured `IncidentReport`
2. **Agent 2** (`rag_module`) retrieves relevant SOPs from knowledge base using semantic search
3. **Agent 3** (future) will use retrieved SOPs to generate resolution plans

## Features

✅ **RAG-based SOP Retrieval**: Semantic search over knowledge base using Azure OpenAI embeddings
✅ **Automatic Query Construction**: Builds optimal search queries from incident details
✅ **Scored Results**: Returns SOPs ranked by relevance with similarity scores
✅ **Comprehensive Testing**: Unit tests with mocked dependencies (no API/DB costs)
✅ **Knowledge Base Vectorization**: Convert structured JSON SOPs to Chroma vector database

## Project Structure

```
rag_module/
├── src/
│   ├── rag_agent/
│   │   ├── __init__.py
│   │   ├── models.py              # Pydantic models (EnrichedContext, SopSnippet)
│   │   └── validator.py           # Core RAG logic (RagAgent class)
│   └── data_sources/
│       ├── __init__.py
│       └── vector_store_interface.py  # Chroma vector store interface
├── tests/
│   ├── __init__.py
│   └── test_rag_agent.py          # Unit tests with mocks
├── vectorize_knowledge_base.py    # Script to vectorize SOPs
├── test_vectorization.py          # Test vector database
├── .env.example                   # Environment variable template
├── requirements.txt
├── setup.py                       # For pip install -e .
└── README.md
```

## Installation

### 1. Create/Use Virtual Environment

```bash
# Option A: Use existing .venv from parsing_module
cd /Users/kanyim/portsentinel
source .venv/bin/activate

# Option B: Create new virtual environment
cd rag_module
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Module

```bash
cd rag_module
pip install -e .
```

This will install `rag_agent` as an editable package along with all dependencies.

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

Required variables:
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure endpoint URL
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` - Embedding model deployment name (e.g., text-embedding-ada-002)
- `CHROMA_PERSIST_DIRECTORY` - Path to vectorized knowledge base (default: db_chroma_kb)

### 4. Vectorize Knowledge Base

**Important**: Before using the RAG module, you must vectorize the knowledge base!

```bash
# Ensure knowledge_base_structured.json exists in parent directory
ls ../knowledge_base_structured.json

# Run vectorization script
python vectorize_knowledge_base.py

# This will create db_chroma_kb/ directory with the vector database
```

**Vectorization Process**:
- Reads `knowledge_base_structured.json` (structured SOP data)
- Splits each SOP into chunks: overview, resolution, preconditions, verification
- Embeds each chunk using Azure OpenAI embeddings
- Stores vectors in Chroma database at `db_chroma_kb/`
- Takes 2-5 minutes depending on number of SOPs

**Custom paths**:
```bash
python vectorize_knowledge_base.py \
  --input /path/to/knowledge_base.json \
  --output /path/to/output_dir
```

**Test vectorization**:
```bash
python test_vectorization.py
```

## Usage

### Basic Example

```python
from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import RagAgent
from parsing_agent.models import IncidentReport  # From parsing_module

# Initialize vector store
vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")

# Create RAG agent
rag_agent = RagAgent(vector_store_interface=vector_store)

# Load parsed incident report (from Agent 1 output)
import json
with open("parsed_incidents.json") as f:
    data = json.load(f)
    report_dict = data[0]["parsed_data"]
    report = IncidentReport(**report_dict)

# Retrieve relevant SOPs
enriched = rag_agent.retrieve(report, k=3)

# Access results
print(f"Retrieved {len(enriched.retrieved_sops)} SOP snippets")
for i, sop in enumerate(enriched.retrieved_sops, 1):
    print(f"\n{i}. {sop.metadata.get('sop_title', 'Unknown')}")
    print(f"   Score: {sop.score:.2f}")
    print(f"   Content: {sop.content[:100]}...")

print(f"\nSummary: {enriched.retrieval_summary}")

# Export to JSON
output = enriched.model_dump()
with open("enriched_context.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
```

### Example Output

```json
{
  "original_report": {
    "incident_id": "ALR-861631",
    "source_type": "Email",
    "urgency": "High",
    "problem_summary": "Unable to create vessel advice due to duplicate system vessel name"
  },
  "retrieved_sops": [
    {
      "content": "VAS: VESSEL_ERR_4 - System Vessel Name has been used by other vessel advice...",
      "metadata": {
        "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
        "module": "Vessel",
        "chunk_type": "overview"
      },
      "score": 0.92
    }
  ],
  "retrieval_summary": "为事故 ALR-861631 检索到 3 个相关 SOP。最相关的 SOP: VAS: VESSEL_ERR_4 (相似度分数: 0.92) 影响模块: Vessel 错误代码: VESSEL_ERR_4"
}
```

## Data Models

### SopSnippet

```python
{
    "content": str,          # SOP text content
    "metadata": dict,        # {sop_title, module, source, chunk_type, ...}
    "score": float           # Similarity score (0-1, higher is better)
}
```

### EnrichedContext

Main output model containing:

```python
{
    "original_report": IncidentReport,      # From Agent 1
    "retrieved_sops": List[SopSnippet],     # RAG results
    "retrieval_summary": str                # Human-readable summary
}
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_rag_agent.py::test_retrieve_full_workflow -v
```

All tests use **mocked** vector store - no actual API calls required!

## How RAG Works

1. **Query Construction**: Agent builds search query from incident details:
   - Error code (high priority)
   - Problem summary
   - Affected module
   - Key entities (container numbers, vessel names, etc.)

2. **Semantic Search**: Query is embedded and compared against vectorized SOPs in Chroma

3. **Ranked Results**: Top k SOPs are returned with similarity scores

4. **Summary Generation**: Human-readable summary explains what was found

## Vector Store

The Chroma vector database at `db_chroma_kb/` contains:
- Vectorized knowledge base documents (4 chunks per SOP)
- Metadata: `sop_title`, `module`, `source`, `chunk_type`
- Embeddings generated with Azure OpenAI embedding model

**Chunk types**:
- `overview`: Problem description and context
- `resolution`: Step-by-step resolution instructions
- `preconditions`: Prerequisites for applying the SOP
- `verification`: How to verify the fix worked

## Integration with Workflow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Raw Text  │ -> │   Agent 1    │ -> │  Agent 2    │
│ (Email/SMS) │    │   (Parser)   │    │    (RAG)    │
└─────────────┘    └──────────────┘    └─────────────┘
                          │                    │
                   IncidentReport      EnrichedContext
                     (JSON)               (JSON)
                                              │
                                              v
                                    ┌──────────────────┐
                                    │   Agent 3        │
                                    │ (Action Planner) │
                                    └──────────────────┘
```

## Troubleshooting

### "Chroma persist directory not found"
- Ensure knowledge base has been vectorized
- Check `CHROMA_PERSIST_DIRECTORY` path in `.env`
- Run `python vectorize_knowledge_base.py`

### "Azure OpenAI authentication error"
- Verify `AZURE_OPENAI_API_KEY` is correct
- Check endpoint URL format (should end with `/`)
- Ensure embedding deployment exists in Azure

### Import errors
- Ensure both `parsing_module` and `rag_module` are installed
- Use `pip install -e .` in both module directories
- Check Python path configuration

## Dependencies

Key packages:
- `langchain` & `langchain-openai` - LLM and RAG framework
- `chromadb` - Vector database
- `pydantic` - Data validation
- `pytest` - Testing framework

See `requirements.txt` for complete list.

## Performance Tips

- **Vector Search**: Default k=3 is optimal for most cases
- **Batch Processing**: Reuse `RagAgent` instance for multiple incidents
- **Caching**: Chroma automatically caches embeddings

```python
rag_agent = RagAgent(vector_store)
for report in reports:
    enriched = rag_agent.retrieve(report)  # Reuse agent instance
```

## Next Steps

After Agent 2 enriches context:

1. **Agent 3** (Action Planner) - Generate resolution steps from retrieved SOPs
2. **Agent 4** (Executor) - Execute approved actions (optional automation)
3. **Monitoring** - Track resolution metrics and feedback loop

## Contributing

When adding new features:

1. Update `validator.py` with new retrieval logic
2. Add unit tests with mocked data
3. Update this README with usage examples
4. Update knowledge base and re-vectorize if needed

## License

Part of the PORTNET® incident management system.
