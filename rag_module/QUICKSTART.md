# Quick Start Guide - RAG Module

快速开始使用 RAG Agent（SOP 检索模块）

## 5 分钟快速设置

### 1. 安装依赖

```bash
cd /Users/kanyim/portsentinel/rag_module
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入以下信息：

```env
# Azure OpenAI (必需)
AZURE_OPENAI_API_KEY=1c7d7bdaa6324d8291b5ca1d5265d10e
AZURE_OPENAI_ENDPOINT=https://psacodesprint2025.azure-api.net/gpt-4-1-mini/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002  # 你的嵌入模型部署名称

# Chroma 向量数据库 (必需)
CHROMA_PERSIST_DIRECTORY=db_chroma_kb
```

### 3. 向量化知识库 (重要！)

在使用 RAG 模块之前，必须先向量化知识库：

```bash
# 确认知识库文件存在
ls ../knowledge_base_structured.json

# 运行向量化脚本
python vectorize_knowledge_base.py
```

输出示例：
```
================================================================================
知识库向量化开始
================================================================================

正在加载知识库...
  ✓ 成功加载 50 个 SOP

正在创建文档块...
  ✓ 创建了 180 个文档块 (来自 50 个 SOP)

正在初始化嵌入模型...
  ✓ 嵌入模型初始化成功

正在创建向量数据库...
  - 将向量化 180 个文档
  - 这可能需要几分钟时间...
  - 处理批次 1/2 (100 个文档)...
  - 处理批次 2/2 (80 个文档)...
  ✓ 向量数据库创建成功!
  ✓ 保存位置: db_chroma_kb

正在验证向量数据库...
  ✓ 数据库中共有 180 个向量

✓ 知识库向量化完成!
```

### 4. 验证安装

```bash
python -c "
from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import RagAgent
print('✓ 导入成功！')
"
```

### 5. 运行测试

```bash
pytest -v
```

所有测试都使用 mocked 数据，不需要实际的 API 连接！

### 6. 测试向量检索

```bash
python test_vectorization.py
```

这将测试向量数据库的检索功能。

## 基本使用

### 方式 1: Python 代码

```python
from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import RagAgent
from parsing_agent.models import IncidentReport
import json

# 1. 初始化 RAG Agent
vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
rag_agent = RagAgent(vector_store_interface=vector_store)

# 2. 加载已解析的报告 (来自 Agent 1)
with open("../parsing_module/parsed_incidents.json") as f:
    data = json.load(f)
    report = IncidentReport(**data[0]["parsed_data"])

# 3. 检索相关 SOP
enriched = rag_agent.retrieve(report, k=3)

# 4. 查看结果
print(f"检索到 {len(enriched.retrieved_sops)} 个 SOP")
for i, sop in enumerate(enriched.retrieved_sops, 1):
    print(f"\n{i}. {sop.metadata.get('sop_title', '未知')}")
    print(f"   相似度分数: {sop.score:.2f}")
    print(f"   内容预览: {sop.content[:100]}...")

print(f"\n摘要: {enriched.retrieval_summary}")

# 5. 保存结果
with open("enriched_output.json", "w") as f:
    json.dump(enriched.model_dump(), f, indent=2, ensure_ascii=False)
```

### 方式 2: 使用示例脚本

```python
# example_rag.py
from data_sources.vector_store_interface import VectorStoreInterface
from rag_agent.validator import RagAgent
from parsing_agent.models import IncidentReport, Entity

# 创建测试报告
test_report = IncidentReport(
    incident_id="TEST-001",
    source_type="Email",
    urgency="High",
    reported_by="Test User",
    reported_at="2025-10-18T10:00:00",
    problem_summary="Unable to create vessel advice due to duplicate system vessel name",
    affected_module="Vessel",
    error_code="VESSEL_ERR_4",
    entities=[
        Entity(type="vessel_name", value="LIONCITY07"),
        Entity(type="error_code", value="VESSEL_ERR_4")
    ],
    steps_already_taken=[],
    additional_notes=""
)

# 初始化并检索
vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
rag_agent = RagAgent(vector_store_interface=vector_store)
enriched = rag_agent.retrieve(test_report, k=3)

# 打印结果
print(f"检索到 {len(enriched.retrieved_sops)} 个相关 SOP")
print(f"摘要: {enriched.retrieval_summary}")
```

## 常见问题

### Q1: "Chroma persist directory not found"

**解决方案**:
- 确保知识库已被向量化到 `db_chroma_kb/` 目录
- 检查 `.env` 中的 `CHROMA_PERSIST_DIRECTORY` 路径
- 如果还没有向量化，运行 `python vectorize_knowledge_base.py`

### Q2: "Azure OpenAI authentication failed"

**解决方案**:
- 验证 API Key 正确
- 检查 Endpoint URL 格式 (应该以 `/` 结尾)
- 确认 embedding deployment 存在于 Azure 中

### Q3: "Module not found: parsing_agent"

**解决方案**:
```bash
# 确保 parsing_module 已安装
cd ../parsing_module
pip install -e .

# 或者设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/Users/kanyim/portsentinel/parsing_module/src"
```

### Q4: "No SOPs retrieved"

**解决方案**:
- 检查向量数据库是否已创建: `ls db_chroma_kb/`
- 验证知识库文件不为空: `cat ../knowledge_base_structured.json`
- 重新运行向量化: `python vectorize_knowledge_base.py`

## 目录结构要求

```
portsentinel/
├── parsing_module/
│   ├── src/parsing_agent/  # Agent 1 必需
│   └── parsed_incidents.json  # Agent 1 输出
├── rag_module/  # 你在这里
│   ├── src/
│   │   ├── rag_agent/
│   │   └── data_sources/
│   └── db_chroma_kb/  # 向量数据库目录 (必需)
└── knowledge_base_structured.json  # 结构化 SOP 数据
```

## 输出示例

### EnrichedContext JSON

```json
{
  "original_report": {
    "incident_id": "ALR-861631",
    "source_type": "Email",
    "urgency": "High",
    "problem_summary": "Unable to create vessel advice due to duplicate system vessel name",
    "affected_module": "Vessel",
    "error_code": "VESSEL_ERR_4"
  },
  "retrieved_sops": [
    {
      "content": "VAS: VESSEL_ERR_4 - System Vessel Name has been used...",
      "metadata": {
        "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
        "module": "Vessel",
        "chunk_type": "overview"
      },
      "score": 0.92
    },
    {
      "content": "Resolution steps: 1. Check for active vessel advice...",
      "metadata": {
        "sop_title": "VAS: VESSEL_ERR_4 - Duplicate Vessel Name",
        "module": "Vessel",
        "chunk_type": "resolution"
      },
      "score": 0.88
    }
  ],
  "retrieval_summary": "为事故 ALR-861631 检索到 2 个相关 SOP。最相关的 SOP: VAS: VESSEL_ERR_4 (相似度分数: 0.92) 影响模块: Vessel 错误代码: VESSEL_ERR_4"
}
```

## 工作流程

1. **Agent 1** (parsing_module) → 解析原始文本 → `IncidentReport`
2. **Agent 2** (rag_module) → 检索相关 SOP → `EnrichedContext`
3. **Agent 3** (未来) → 生成解决方案 → 执行计划

## 调试技巧

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 检查向量搜索结果

```python
from data_sources.vector_store_interface import VectorStoreInterface

vector_store = VectorStoreInterface(persist_directory="db_chroma_kb")
docs = vector_store.search_with_scores("VESSEL_ERR_4", k=3)

for doc, score in docs:
    print(f"Score: {score:.3f}")
    print(f"Content: {doc.page_content[:100]}...")
    print(f"Metadata: {doc.metadata}")
    print()
```

### 查看向量数据库统计

```python
stats = vector_store.get_collection_stats()
print(f"集合名称: {stats.get('name')}")
print(f"向量数量: {stats.get('count')}")
```

## 性能优化

- **连接重用**: 重用 `RagAgent` 实例处理多个报告
- **向量搜索**: k=3 已足够快且准确
- **批处理**: Chroma 自动优化批量查询

```python
rag_agent = RagAgent(vector_store)
for report in reports:
    enriched = rag_agent.retrieve(report)  # 重用连接
```

## 下一步

1. 查看 `README.md` 了解详细文档
2. 运行 `pytest --cov=src` 查看测试覆盖率
3. 集成到完整工作流: Agent 1 → Agent 2 → Agent 3

Happy coding! 🚀
