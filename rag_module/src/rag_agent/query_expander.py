"""
Multi-Query 生成器：从多个角度重写问题
"""

import os
from typing import List
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


class QueryExpander:
    """
    使用 LLM 生成多个查询变体
    """
    
    def __init__(
        self,
        api_key: str = None,
        azure_endpoint: str = None,
        deployment: str = None,
        api_version: str = None
    ):
        """
        初始化 Query Expander
        
        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure endpoint
            deployment: Chat model deployment name
            api_version: API version
        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        # 初始化 LLM
        self.llm = AzureChatOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            azure_deployment=self.deployment,
            api_version=self.api_version,
            temperature=0.3  # 保持一定创造性但不过度发散
        )
        
        # Multi-Query Prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at generating multiple search query variations for technical incident reports.

Given an incident query, generate {num_variants} different search queries that:
1. Use synonyms and alternative technical terms
2. Expand with related concepts and scenarios
3. Remove redundant words while preserving key information
4. Correct potential errors and standardize expressions
5. Rephrase from different troubleshooting angles

Focus on technical accuracy and relevance to SOP (Standard Operating Procedure) documentation.

Output ONLY the queries, one per line, without numbering or explanation."""),
            ("human", """Original incident query:
{original_query}

Generate {num_variants} search query variations:""")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def expand_query(self, original_query: str, num_variants: int = 3) -> List[str]:
        """
        生成查询变体
        
        Args:
            original_query: 原始查询
            num_variants: 生成变体数量
        
        Returns:
            包含原始查询和变体的列表
        """
        try:
            # 调用 LLM 生成变体
            response = self.chain.invoke({
                "original_query": original_query,
                "num_variants": num_variants
            })
            
            # 解析响应（每行一个查询）
            variants = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            # 去重并限制数量
            unique_variants = list(dict.fromkeys(variants))[:num_variants]
            
            # 返回：原始查询 + 变体
            all_queries = [original_query] + unique_variants
            
            return all_queries
            
        except Exception as e:
            print(f"Warning: Query expansion failed: {e}")
            # 失败时返回原始查询
            return [original_query]
    
    def expand_from_report(self, report, num_variants: int = 3) -> List[str]:
        """
        从 IncidentReport 生成查询变体
        
        Args:
            report: IncidentReport 对象
            num_variants: 变体数量
        
        Returns:
            查询列表
        """
        # 构建初始查询
        query_parts = []
        
        if report.error_code:
            query_parts.append(f"Error code: {report.error_code}")
        
        query_parts.append(report.problem_summary)
        
        if report.affected_module:
            query_parts.append(f"Module: {report.affected_module}")
        
        original_query = " | ".join(query_parts)
        
        return self.expand_query(original_query, num_variants)


# 简化版本（无 LLM，使用规则）
class RuleBasedQueryExpander:
    """
    基于规则的查询扩展（无需 LLM）
    """
    
    def expand_query(self, original_query: str, num_variants: int = 2) -> List[str]:
        """
        使用简单规则生成变体
        """
        queries = [original_query]
        
        # 变体 1: 提取关键词
        keywords = self._extract_keywords(original_query)
        if keywords:
            queries.append(" ".join(keywords))
        
        # 变体 2: 简化版（只保留核心术语）
        simplified = self._simplify_query(original_query)
        if simplified and simplified != original_query:
            queries.append(simplified)
        
        return queries[:num_variants + 1]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 移除常见停用词
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'been', 'be'}
        
        words = query.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _simplify_query(self, query: str) -> str:
        """简化查询"""
        # 移除 "Error code:", "Module:" 等前缀
        parts = query.split("|")
        
        # 只保留最核心的部分
        core_parts = []
        for part in parts:
            cleaned = part.strip()
            if ":" in cleaned:
                cleaned = cleaned.split(":", 1)[1].strip()
            if cleaned:
                core_parts.append(cleaned)
        
        return " ".join(core_parts) if core_parts else query
    
    def expand_from_report(self, report, num_variants: int = 2) -> List[str]:
        """从报告生成变体"""
        query_parts = []
        
        if report.error_code:
            query_parts.append(f"Error code: {report.error_code}")
        
        query_parts.append(report.problem_summary)
        
        if report.affected_module:
            query_parts.append(f"Module: {report.affected_module}")
        
        original_query = " | ".join(query_parts)
        
        return self.expand_query(original_query, num_variants)