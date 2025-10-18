"""
语义 Reranker：使用 LLM 对检索结果进行重新排序
"""

import os
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


class SemanticReranker:
    """
    使用 LLM 对候选 SOPs 进行语义相关性重排序
    """
    
    def __init__(
        self,
        api_key: str = None,
        azure_endpoint: str = None,
        deployment: str = None,
        api_version: str = None
    ):
        """初始化 Reranker"""
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION")
        
        self.llm = AzureChatOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            azure_deployment=self.deployment,
            api_version=self.api_version,
            temperature=0.0  # 确定性输出
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at evaluating the relevance of Standard Operating Procedures (SOPs) to technical incidents.

Given an incident query and a list of candidate SOP titles/overviews, rank them by relevance.

Output format: Only return the indices of the SOPs in order of relevance (most relevant first), separated by commas.
Example: 2,0,4,1,3

Do NOT include explanations, only the comma-separated indices."""),
            ("human", """Incident Query:
{query}

Candidate SOPs:
{candidates}

Rank by relevance (output indices only):""")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        重排序候选 SOPs
        
        Args:
            query: 查询字符串
            candidates: SOP 字典列表
            top_k: 返回 Top-K（None 则返回全部）
        
        Returns:
            [(SOP, rerank_score), ...] 按相关性降序排列
        """
        if not candidates:
            return []
        
        try:
            # 构建候选列表文本
            candidates_text = ""
            for idx, sop in enumerate(candidates):
                title = sop.get("Title", "Unknown")
                overview = sop.get("Overview", "")[:200]  # 限制长度
                candidates_text += f"{idx}. {title}\n   Overview: {overview}\n\n"
            
            # 调用 LLM
            response = self.chain.invoke({
                "query": query,
                "candidates": candidates_text
            })
            
            # 解析排序结果
            ranked_indices = [int(x.strip()) for x in response.strip().split(",") if x.strip().isdigit()]
            
            # 验证索引有效性
            ranked_indices = [i for i in ranked_indices if 0 <= i < len(candidates)]
            
            # 如果解析失败，保持原顺序
            if not ranked_indices:
                ranked_indices = list(range(len(candidates)))
            
            # 为缺失的索引补充（保持原顺序）
            missing_indices = [i for i in range(len(candidates)) if i not in ranked_indices]
            ranked_indices.extend(missing_indices)
            
            # 计算 Rerank 分数（基于排名）
            results = []
            for rank, idx in enumerate(ranked_indices):
                sop = candidates[idx]
                # Rerank score: 1.0 / (rank + 1)，最相关的为 1.0
                rerank_score = 1.0 / (rank + 1)
                results.append((sop, rerank_score))
            
            # 返回 Top-K
            if top_k:
                results = results[:top_k]
            
            return results
            
        except Exception as e:
            print(f"Warning: Reranking failed: {e}")
            # 失败时保持原顺序，分数递减
            return [
                (sop, 1.0 / (i + 1)) 
                for i, sop in enumerate(candidates[:top_k] if top_k else candidates)
            ]


# 简化版本（无 LLM，基于标题匹配）
class SimpleReranker:
    """
    基于关键词匹配的简单 Reranker
    """
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        基于标题和 Overview 的关键词匹配进行重排序
        """
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        
        scored_candidates = []
        
        for sop in candidates:
            title = sop.get("Title", "").lower()
            overview = sop.get("Overview", "").lower()
            
            # 计算匹配分数
            title_tokens = set(title.split())
            overview_tokens = set(overview.split())
            
            # Jaccard 相似度
            title_overlap = len(query_tokens & title_tokens) / max(len(query_tokens | title_tokens), 1)
            overview_overlap = len(query_tokens & overview_tokens) / max(len(query_tokens | overview_tokens), 1)
            
            # 加权组合（Title 权重更高）
            score = 0.7 * title_overlap + 0.3 * overview_overlap
            
            scored_candidates.append((sop, score))
        
        # 按分数降序排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 Top-K
        if top_k:
            scored_candidates = scored_candidates[:top_k]
        
        return scored_candidates