"""
Pydantic models for RAG-based SOP retrieval with hybrid search.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# Import IncidentReport from parsing_agent
parsing_module_path = Path(__file__).parent.parent.parent.parent / "parsing_module" / "src"
sys.path.insert(0, str(parsing_module_path))
from parsing_agent.models import IncidentReport


class SopSnippet(BaseModel):
    """
    检索到的 SOP 片段（支持混合检索）
    """
    content: str = Field(..., description="SOP 文本内容")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="元数据 (sop_title, module, source, chunk_type, etc.)"
    )
    
    # 多种分数类型
    vector_score: Optional[float] = Field(
        None, 
        description="向量相似度分数 (0-1, 余弦相似度)"
    )
    bm25_score: Optional[float] = Field(
        None,
        description="BM25 分数（已归一化到 0-1）"
    )
    hybrid_score: Optional[float] = Field(
        None,
        description="混合分数（向量 + BM25 加权组合）"
    )
    rrf_score: Optional[float] = Field(
        None,
        description="RRF (Reciprocal Rank Fusion) 分数"
    )
    rerank_score: Optional[float] = Field(
        None,
        description="语义 Rerank 后的分数"
    )
    
    # 原始完整 SOP 数据
    full_sop_json: Optional[Dict[str, Any]] = Field(
        None,
        description="完整的 SOP JSON 数据（从 metadata 中提取）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Title: VAS: VESSEL_ERR_4...",
                "metadata": {
                    "sop_title": "VAS: VESSEL_ERR_4",
                    "module": "Vessel",
                    "chunk_type": "header"
                },
                "vector_score": 0.89,
                "bm25_score": 0.75,
                "hybrid_score": 0.82,
                "rrf_score": 0.0156,
                "rerank_score": 0.92
            }
        }


class RetrievalMetrics(BaseModel):
    """
    检索过程的评估指标
    """
    num_expanded_queries: int = Field(..., description="Multi-Query 生成的查询数量")
    num_bm25_candidates: int = Field(..., description="BM25 检索的候选数量")
    num_vector_candidates: int = Field(..., description="向量检索的候选数量")
    num_merged_candidates: int = Field(..., description="合并后的唯一候选数量")
    num_after_rrf: int = Field(..., description="RRF 后保留的文档数")
    num_final_results: int = Field(..., description="最终返回的文档数")
    
    bm25_weight: float = Field(default=0.4, description="BM25 权重")
    vector_weight: float = Field(default=0.6, description="向量检索权重")
    rrf_k: int = Field(default=60, description="RRF 参数 k")


class EnrichedContext(BaseModel):
    """
    RAG 模块的完整输出（混合检索版本）
    """
    original_report: IncidentReport = Field(
        ...,
        description="原始事件报告（来自 Agent 1）"
    )
    
    expanded_queries: List[str] = Field(
        default_factory=list,
        description="Multi-Query 生成的查询变体"
    )
    
    retrieved_sops: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="检索到的完整 SOP（原始 JSON 格式）"
    )
    
    retrieval_summary: str = Field(
        ...,
        description="检索过程摘要"
    )
    
    retrieval_metrics: Optional[RetrievalMetrics] = Field(
        None,
        description="检索评估指标"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_report": {
                    "incident_id": "ALR-861631",
                    "problem_summary": "Unable to create vessel advice..."
                },
                "expanded_queries": [
                    "Error code: VESSEL_ERR_4...",
                    "Duplicate system vessel name issue...",
                    "Unable to create vessel advice troubleshooting..."
                ],
                "retrieved_sops": [
                    {
                        "Title": "VAS: VESSEL_ERR_4...",
                        "Overview": "...",
                        "Resolution": "...",
                        "Verification": "...",
                        "Module": "Vessel"
                    }
                ],
                "retrieval_summary": "Retrieved 3 SOPs using hybrid search...",
                "retrieval_metrics": {
                    "num_expanded_queries": 3,
                    "num_bm25_candidates": 5,
                    "num_vector_candidates": 5,
                    "num_merged_candidates": 8,
                    "num_after_rrf": 5,
                    "num_final_results": 3
                }
            }
        }