"""
混合检索 RAG Agent 单元测试
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add paths
rag_module_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(rag_module_path))
parsing_module_path = Path(__file__).parent.parent.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))

from parsing_agent.models import IncidentReport, Entity
from rag_agent.validator import HybridRagAgent
from rag_agent.models import EnrichedContext
from data_sources.bm25_retriever import BM25Retriever
from rag_agent.query_expander import RuleBasedQueryExpander
from data_sources.reranker import SimpleReranker


@pytest.fixture
def mock_vector_store():
    """Mock 向量存储"""
    mock = Mock()
    mock.search_with_scores = Mock()
    return mock


@pytest.fixture
def mock_bm25_retriever():
    """Mock BM25 检索器"""
    mock = Mock(spec=BM25Retriever)
    mock.search_normalized = Mock()
    return mock


@pytest.fixture
def sample_incident_report():
    """测试用事件报告"""
    return IncidentReport(
        incident_id="TEST-001",
        source_type="Email",
        received_timestamp_utc="2025-10-18T10:00:00Z",
        urgency="High",
        reported_by="Test User",
        reported_at="2025-10-18T10:00:00",
        problem_summary="Container range error overlapping",
        affected_module="Container",
        error_code=None,
        entities=[
            Entity(type="container_number", value="BSIU323099")
        ],
        steps_already_taken=[],
        additional_notes="",
        raw_text="Overlapping container range error..."
    )


def test_hybrid_search_integration(mock_vector_store, mock_bm25_retriever, sample_incident_report):
    """测试混合检索集成"""
    # Mock BM25 结果
    mock_bm25_retriever.search_normalized.return_value = [
        (
            {
                "Title": "CNTR: Container Range Error",
                "Overview": "Overlapping ranges...",
                "Resolution": "Check serial numbers...",
                "Module": "Container"
            },
            0.85
        )
    ]
    
    # Mock 向量检索结果
    from langchain_core.documents import Document
    import json
    
    sop_json = json.dumps({
        "Title": "CNTR: Container Range Error",
        "Overview": "Overlapping ranges...",
        "Resolution": "Check serial numbers...",
        "Module": "Container"
    })
    
    mock_doc = Document(
        page_content="CNTR: Container Range Error...",
        metadata={
            "sop_title": "CNTR: Container Range Error",
            "module": "Container",
            "chunk_type": "header",
            "full_sop_json": sop_json
        }
    )
    
    mock_vector_store.search_with_scores.return_value = [(mock_doc, 0.92)]
    
    # 创建 Agent
    agent = HybridRagAgent(
        vector_store_interface=mock_vector_store,
        bm25_retriever=mock_bm25_retriever,
        query_expander=RuleBasedQueryExpander(),
        reranker=SimpleReranker(),
        use_llm=False
    )
    
    # 执行检索
    result = agent.retrieve(
        report=sample_incident_report,
        num_query_variants=2,
        k_per_query=5,
        final_top_k=3
    )
    
    # 验证
    assert isinstance(result, EnrichedContext)
    assert len(result.expanded_queries) >= 1
    assert len(result.retrieved_sops) > 0
    assert result.retrieved_sops[0]["Title"] == "CNTR: Container Range Error"
    assert "hybrid search" in result.retrieval_summary.lower()
    assert result.retrieval_metrics is not None


def test_query_expansion():
    """测试查询扩展"""
    expander = RuleBasedQueryExpander()
    
    original = "Error code: VESSEL_ERR_4 | Unable to create vessel advice"
    variants = expander.expand_query(original, num_variants=2)
    
    assert len(variants) >= 1
    assert variants[0] == original
    # 应该有至少一个变体
    assert len(variants) > 1


def test_rrf_fusion(mock_vector_store, mock_bm25_retriever, sample_incident_report):
    """测试 RRF 融合"""
    # 准备测试数据 - 使用更明显的分数差异
    sop_1 = {"Title": "SOP 1", "Overview": "Test 1", "Module": "Container"}
    sop_2 = {"Title": "SOP 2", "Overview": "Test 2", "Module": "Container"}
    
    # 修改查询结果，确保 SOP 2 在两个查询中都有更高排名
    query_results_1 = [
        (sop_2, 0.95, 'both'),     # SOP 2 排名第一，分数更高
        (sop_1, 0.70, 'vector')    # SOP 1 排名第二，分数较低
    ]
    query_results_2 = [
        (sop_2, 0.90, 'both'),     # SOP 2 继续保持高分
        (sop_1, 0.65, 'bm25')      # SOP 1 分数仍然较低
    ]
    
    agent = HybridRagAgent(
        vector_store_interface=mock_vector_store,
        bm25_retriever=mock_bm25_retriever,
        use_llm=False
    )
    
    # 执行 RRF
    rrf_results = agent._reciprocal_rank_fusion(
        [query_results_1, query_results_2],
        k=60
    )
    
    # 增加更详细的验证
    assert len(rrf_results) == 2, "应该返回两个结果"
    assert rrf_results[0][0]["Title"] == "SOP 2", "SOP 2 应该排名第一(在两个查询中都有更高分数)"
    assert rrf_results[1][0]["Title"] == "SOP 1", "SOP 1 应该排名第二"
    # 验证 RRF 分数
    assert rrf_results[0][1] > rrf_results[1][1], "第一个结果的 RRF 分数应该更高"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])